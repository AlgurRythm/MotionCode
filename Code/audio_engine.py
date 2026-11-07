"""MotionCode audio engine.

Audio scripts describe sound on the same timeline as the video, in seconds.
Events are mixed into one stereo track at a fixed sample rate.

Example audio script:

    def build_audio(audio):
        audio.duration = 58
        audio.add_tone("pad", freq=220, start=0, length=8, volume=0.12)
        audio.add_click("tick", at=8, volume=0.3)
        audio.add_clip("sting", "sting.wav", at=50, volume=0.8)

Set sample_rate before calling add_clip, because clips are loaded at that rate.
"""
import os
import subprocess
import tempfile
import wave
import zlib

import numpy as np

MAX_DURATION = 600.0
# No console window for ffmpeg on Windows (the packaged app is windowed).
NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
WAVEFORMS = ("sine", "square", "triangle", "saw")


def _envelope(n, sr, fade_in, fade_out):
    """Linear fade-in and fade-out over n samples."""
    env = np.ones(n)
    fi = min(n, int(max(0.0, fade_in) * sr))
    fo = min(n, int(max(0.0, fade_out) * sr))
    if fi > 0:
        env[:fi] *= np.linspace(0.0, 1.0, fi, endpoint=False)
    if fo > 0:
        env[n - fo:] *= np.linspace(1.0, 0.0, fo)
    return env


def _pan(mono, pan):
    """Constant-power pan: -1 is full left, 0 is centre, 1 is full right."""
    angle = (max(-1.0, min(1.0, float(pan))) + 1.0) * np.pi / 4.0
    return np.stack([mono * np.cos(angle), mono * np.sin(angle)], axis=1)


def _resample(stereo, new_len):
    """Linear resample of a stereo array to new_len samples."""
    if new_len == len(stereo):
        return stereo
    new_len = max(1, int(new_len))
    old_x = np.linspace(0.0, 1.0, len(stereo))
    new_x = np.linspace(0.0, 1.0, new_len)
    return np.stack([np.interp(new_x, old_x, stereo[:, c]) for c in range(2)], axis=1)


# Imported files live here. add_clip() looks here when the path is not found as given.
ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def resolve_asset(path):
    """Return the real file path. Names that are not found as given are looked up in ASSET_DIR."""
    path = str(path)
    if os.path.exists(path):
        return path
    candidate = os.path.join(ASSET_DIR, path)
    if os.path.exists(candidate):
        return candidate
    raise FileNotFoundError(f"Asset {path!r} not found. Import it with the Assets panel, or check the name.")


def convert_to_wav(path, sr):
    """Convert any audio file (mp3, ogg, m4a, flac, ...) to a temporary 16-bit stereo WAV at rate sr.
    Returns the temporary file path. The caller deletes it."""
    import imageio_ffmpeg
    fd, out = tempfile.mkstemp(suffix=".wav", prefix="motioncode_asset_")
    os.close(fd)
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", path, "-vn",
         "-ac", "2", "-ar", str(int(sr)), "-c:a", "pcm_s16le", out],
        capture_output=True, **NO_WINDOW)
    if result.returncode != 0:
        try:
            os.remove(out)
        except OSError:
            pass
        message = result.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise RuntimeError(f"Could not read {os.path.basename(path)} as audio: "
                           + (message[-1] if message else "unknown error"))
    return out


def load_wav(path, sr):
    """Load a PCM WAV file as a stereo float array at sample rate sr."""
    with wave.open(path, "rb") as w:
        channels = w.getnchannels()
        width = w.getsampwidth()
        rate = w.getframerate()
        raw = w.readframes(w.getnframes())

    if width == 1:
        data = (np.frombuffer(raw, np.uint8).astype(np.float64) - 128.0) / 128.0
    elif width == 2:
        data = np.frombuffer(raw, "<i2").astype(np.float64) / 32768.0
    elif width == 4:
        data = np.frombuffer(raw, "<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError("Only 8, 16 or 32-bit PCM WAV files are supported: " + path)

    data = data.reshape(-1, channels)
    if channels == 1:
        stereo = np.repeat(data, 2, axis=1)
    else:
        stereo = data[:, :2]

    if rate != sr:
        stereo = _resample(stereo, int(round(len(stereo) * sr / rate)))
    return stereo


class _Event:
    def __init__(self, name, start, volume):
        self.name = str(name)
        self.start = float(start)
        self.volume = float(volume)

    def render(self, sr, speed):
        raise NotImplementedError


class _Tone(_Event):
    def __init__(self, name, start, length, volume, freq, fade_in, fade_out, waveform, pan):
        super().__init__(name, start, volume)
        self.length = float(length)
        self.freq = float(freq)
        self.fade_in = float(fade_in)
        self.fade_out = float(fade_out)
        self.waveform = str(waveform).lower()
        self.pan = float(pan)
        if self.waveform not in WAVEFORMS:
            raise ValueError("Unknown waveform %r. Use one of: %s" % (waveform, ", ".join(WAVEFORMS)))

    def render(self, sr, speed):
        n = max(0, int(round(self.length / speed * sr)))
        if n == 0:
            return np.zeros((0, 2))
        t = np.arange(n) / sr
        phase = 2.0 * np.pi * self.freq * t
        if self.waveform == "square":
            s = np.sign(np.sin(phase))
        elif self.waveform == "triangle":
            s = (2.0 / np.pi) * np.arcsin(np.sin(phase))
        elif self.waveform == "saw":
            s = 2.0 * ((self.freq * t) % 1.0) - 1.0
        else:
            s = np.sin(phase)
        mono = s * _envelope(n, sr, self.fade_in / speed, self.fade_out / speed) * self.volume
        return _pan(mono, self.pan)


class _Noise(_Event):
    def __init__(self, name, start, length, volume, fade_in, fade_out, pan):
        super().__init__(name, start, volume)
        self.length = float(length)
        self.fade_in = float(fade_in)
        self.fade_out = float(fade_out)
        self.pan = float(pan)

    def render(self, sr, speed):
        n = max(0, int(round(self.length / speed * sr)))
        if n == 0:
            return np.zeros((0, 2))
        rng = np.random.default_rng(zlib.crc32(self.name.encode("utf-8")))
        mono = rng.uniform(-1.0, 1.0, n) * _envelope(n, sr, self.fade_in / speed, self.fade_out / speed) * self.volume
        return _pan(mono, self.pan)


class _Click(_Event):
    def __init__(self, name, at, volume, freq, pan):
        super().__init__(name, at, volume)
        self.freq = float(freq)
        self.pan = float(pan)

    def render(self, sr, speed):
        length = 0.03
        n = max(1, int(round(length / speed * sr)))
        t = np.arange(n) / sr
        mono = np.sin(2.0 * np.pi * self.freq * t) * np.exp(-t * 200.0) * self.volume
        return _pan(mono, self.pan)


class _Clip(_Event):
    def __init__(self, name, at, data, volume):
        super().__init__(name, at, volume)
        self.data = data

    def render(self, sr, speed):
        # Clips are stretched by resampling, so their pitch follows the speed.
        new_len = int(round(len(self.data) / speed))
        return _resample(self.data, new_len) * self.volume


# Moods for AudioScene.add_mood(). Layers are (frequency ratio, share of the volume).
# Major chords read as bright, minor as sad, one note as plain, and loud/excited stack more layers.
MOODS = {
    "happy":   {"base": 1.0,  "wave": "triangle", "volume": 0.12, "fade_in": 0.8, "fade_out": 1.2,
                "layers": [(1.0, 0.5), (1.25, 0.3), (1.5, 0.2)]},
    "sad":     {"base": 0.75, "wave": "sine",     "volume": 0.12, "fade_in": 2.0, "fade_out": 3.0,
                "layers": [(1.0, 0.5), (1.19, 0.3), (1.5, 0.2)]},
    "calm":    {"base": 1.0,  "wave": "sine",     "volume": 0.10, "fade_in": 2.0, "fade_out": 3.0,
                "layers": [(1.0, 0.7), (1.5, 0.3)]},
    "quiet":   {"base": 1.0,  "wave": "sine",     "volume": 0.04, "fade_in": 2.0, "fade_out": 3.0,
                "layers": [(1.0, 1.0)]},
    "soft":    {"base": 1.0,  "wave": "sine",     "volume": 0.08, "fade_in": 1.5, "fade_out": 2.0,
                "layers": [(1.0, 0.6), (1.5, 0.4)]},
    "loud":    {"base": 1.0,  "wave": "square",   "volume": 0.30, "fade_in": 0.1, "fade_out": 0.3,
                "layers": [(1.0, 0.4), (1.5, 0.35), (2.0, 0.25)]},
    "excited": {"base": 1.5,  "wave": "saw",      "volume": 0.15, "fade_in": 0.2, "fade_out": 0.6,
                "layers": [(1.0, 0.4), (1.25, 0.35), (1.5, 0.25)]},
    "tense":   {"base": 0.9,  "wave": "saw",      "volume": 0.10, "fade_in": 1.0, "fade_out": 1.5,
                "layers": [(1.0, 0.6), (1.06, 0.4)]},
    "neutral": {"base": 1.0,  "wave": "sine",     "volume": 0.10, "fade_in": 0.5, "fade_out": 1.0,
                "layers": [(1.0, 1.0)]},
}


class AudioScene:
    """The object an audio script receives in build_audio(audio)."""

    def __init__(self):
        self.duration = 10.0
        self.sample_rate = 44100
        self.master_volume = 1.0
        self.events = []

    def add_tone(self, name, freq=440.0, start=0.0, length=1.0, volume=0.3,
                 fade_in=0.01, fade_out=0.05, wave="sine", pan=0.0):
        self.events.append(_Tone(name, start, length, volume, freq,
                                 fade_in, fade_out, wave, pan))

    def add_mood(self, name, mood="neutral", start=0.0, length=1.0, base_freq=220.0,
                 volume=None, fade_in=None, fade_out=None, pan=0.0):
        """Add a background sound that carries a mood. It is built from several tone layers.
        mood: happy, sad, calm, quiet, soft, loud, excited, tense, neutral.
        volume overrides the mood's default level, and fade_in/fade_out override its fades.
        This shapes the background only."""
        if mood not in MOODS:
            raise ValueError("Unknown mood %r. Use one of: %s" % (mood, ", ".join(MOODS)))
        preset = MOODS[mood]
        level = preset["volume"] if volume is None else float(volume)
        fi = preset["fade_in"] if fade_in is None else float(fade_in)
        fo = preset["fade_out"] if fade_out is None else float(fade_out)
        for i, (ratio, share) in enumerate(preset["layers"]):
            self.events.append(_Tone(
                "%s_%d" % (name, i + 1), start, length, level * share,
                base_freq * preset["base"] * ratio, fi, fo, preset["wave"], pan))

    def add_noise(self, name, start=0.0, length=1.0, volume=0.1,
                  fade_in=0.01, fade_out=0.05, pan=0.0):
        self.events.append(_Noise(name, start, length, volume, fade_in, fade_out, pan))

    def add_click(self, name, at=0.0, volume=0.3, freq=1800.0, pan=0.0):
        self.events.append(_Click(name, at, volume, freq, pan))

    def add_clip(self, name, path, at=0.0, volume=1.0):
        """Place an audio file on the timeline. Accepts WAV directly, and other formats
        (mp3, ogg, m4a, flac, ...) are converted first. Names are looked up in the assets folder."""
        real = resolve_asset(path)
        if os.path.splitext(real)[1].lower() == ".wav":
            data = load_wav(real, int(self.sample_rate))
        else:
            temp = convert_to_wav(real, self.sample_rate)
            try:
                data = load_wav(temp, int(self.sample_rate))
            finally:
                try:
                    os.remove(temp)
                except OSError:
                    pass
        self.events.append(_Clip(name, at, data, volume))


def write_wav(path, stereo, sr):
    """Write a stereo float array as 16-bit PCM WAV."""
    pcm = (np.clip(stereo, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(int(sr))
        w.writeframes(pcm.tobytes())
