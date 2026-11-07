"""MotionCode export: formats, presets, audio files and the render pipeline.

Pipeline (video and PNG):
  render thread   renders frame N with the same function the preview uses
  writer thread   sends frame N-1 to ffmpeg (or saves a PNG) at the same time
A small bounded queue joins the two threads, so memory stays bounded and no
frame is dropped. The pixels match a single-threaded export. Only timing changes.
"""
import os
import queue
import subprocess
import tempfile
import threading
import traceback
import wave
from pathlib import Path

import numpy as np
from PySide6.QtCore import QThread, Signal

from optimization import ffmpeg_failure_message, _remove_quietly


# ------------------------------------------------------------ formats

# needs: the ffmpeg encoder that must exist in this build (checked at start-up)
VIDEO_FORMATS = {
    "mp4_h264": {"label": "MP4",  "ext": ".mp4",  "needs": "libx264",    "nvenc": True},
    "mov_h264": {"label": "MOV",  "ext": ".mov",  "needs": "libx264",    "nvenc": True},
    "mkv_h264": {"label": "MKV",  "ext": ".mkv",  "needs": "libx264",    "nvenc": True},
    "webm_vp9": {"label": "WebM", "ext": ".webm", "needs": "libvpx-vp9", "nvenc": False},
    "gif":      {"label": "GIF",  "ext": ".gif",  "needs": "gif",        "nvenc": False},
}

AUDIO_FORMATS = {
    "wav16":    {"label": "WAV",  "ext": ".wav",  "needs": None,
                 "args": ["-c:a", "pcm_s16le"]},
    "flac":     {"label": "FLAC", "ext": ".flac", "needs": "flac",
                 "args": ["-c:a", "flac"]},
    "aac_256":  {"label": "M4A",  "ext": ".m4a",  "needs": "aac",
                 "args": ["-c:a", "aac", "-b:a", "256k"]},
    "mp3_320":  {"label": "MP3",  "ext": ".mp3",  "needs": "libmp3lame",
                 "args": ["-c:a", "libmp3lame", "-b:a", "320k"]},
    "ogg_q6":   {"label": "OGG",  "ext": ".ogg",  "needs": "libvorbis",
                 "args": ["-c:a", "libvorbis", "-q:a", "6"]},
    "opus_160": {"label": "Opus", "ext": ".opus", "needs": "libopus",
                 "args": ["-c:a", "libopus", "-b:a", "160k"]},
}

# Which audio formats each video container can hold.
CONTAINER_AUDIO = {
    "mp4":  {"aac_256"},
    "mov":  {"aac_256"},
    "mkv":  {"aac_256", "mp3_320", "ogg_q6", "opus_160", "flac"},
    "webm": {"opus_160", "ogg_q6"},
    "gif":  set(),
}

# The audio track used for each video file type. Chosen automatically, so the
# export dialog only asks for the file type.
AUTO_AUDIO = {
    "mp4_h264": "aac_256",
    "mov_h264": "aac_256",
    "mkv_h264": "aac_256",
    "webm_vp9": "opus_160",
    "gif":      None,
}


# Quality by CRF: lower is better and larger. 0 is lossless.
CRF_LEVELS = [
    ("Lossless", 0),
    ("Master (CRF 12)", 12),
    ("High (CRF 18)", 18),
    ("Standard (CRF 22)", 22),
    ("Small (CRF 26)", 26),
    ("Tiny (CRF 30)", 30),
]

EXTRA_SIZES = [
    ("Square (1080×1080)", (1080, 1080)),
    ("Vertical (1080×1920)", (1080, 1920)),
]

# ------------------------------------------------------------ ffmpeg detection

_CAPS = None   # (ffmpeg path, set of encoder names), filled once
_PROBE_LOCK = threading.Lock()
# On Windows, a packaged (windowed) app would flash a console window for every ffmpeg call.
NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def warm_up_ffmpeg():
    """Find ffmpeg and read its encoder list on a background thread, so the Export dialog
    opens at once instead of freezing the window while ffmpeg runs."""
    def run():
        try:
            probe_ffmpeg()
        except Exception:
            pass   # the export dialog reports the problem when it is opened
    threading.Thread(target=run, name="ffmpeg-probe", daemon=True).start()


def probe_ffmpeg():
    """Return (ffmpeg path, encoder names). Raises RuntimeError if ffmpeg is missing.
    Safe to call from any thread; the result is kept after the first call."""
    global _CAPS
    with _PROBE_LOCK:
        if _CAPS is None:
            _CAPS = _read_encoders()
        return _CAPS


def _read_encoders():
    """Ask ffmpeg which encoders it has. Returns (ffmpeg path, set of encoder names)."""
    try:
        import imageio_ffmpeg
    except ImportError:
        raise RuntimeError("imageio-ffmpeg is not installed")
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run([exe, "-hide_banner", "-encoders"],
                            capture_output=True, text=True, **NO_WINDOW)
    names = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 6:
            names.add(parts[1])
    return (exe, names)


def available_video_formats(names):
    return [k for k, v in VIDEO_FORMATS.items() if v["needs"] in names]


def available_audio_formats(names):
    return [k for k, v in AUDIO_FORMATS.items() if v["needs"] is None or v["needs"] in names]


def file_type_choices(names):
    """(label, kind, key) for every file type this ffmpeg build can write, in display order.
    kind is "video", "audio" or "png"; key is the format key (None for PNG frames)."""
    out = [(VIDEO_FORMATS[k]["label"], "video", k) for k in available_video_formats(names)]
    out += [(AUDIO_FORMATS[k]["label"], "audio", k) for k in available_audio_formats(names)]
    out.append(("PNG frames (folder of images)", "png", None))
    return out


# ------------------------------------------------------------ video command

# Colour tags for HD video (BT.709). Without them, players guess the colour space.
COLOR_TAGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
              "-color_range", "tv"]
# Video sizes must be even for 4:2:0 playback. Odd sizes are trimmed by one pixel.
EVEN_SIZE = "scale=trunc(iw/2)*2:trunc(ih/2)*2"


def video_codec_args(fmt, crf, nvenc=False):
    """Encoder options for a video format. CRF sets quality; lower is better. 0 is lossless."""
    crf = str(int(crf)) if crf is not None else "18"
    if fmt in ("mp4_h264", "mov_h264", "mkv_h264") and int(crf) < 1:
        crf = "1"   # H.264 High profile cannot be truly lossless; CRF 1 is visually lossless and plays everywhere
    if fmt == "gif":
        return ["-filter_complex",
                "[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer",
                "-loop", "0"]
    if fmt == "webm_vp9":
        return ["-vf", EVEN_SIZE, "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", crf,
                "-row-mt", "1", "-pix_fmt", "yuv420p"] + COLOR_TAGS
    if nvenc and VIDEO_FORMATS[fmt]["nvenc"]:
        return ["-vf", EVEN_SIZE, "-c:v", "h264_nvenc", "-preset", "p5", "-cq", crf,
                "-profile:v", "high", "-pix_fmt", "yuv420p"] + COLOR_TAGS + \
               (["-movflags", "+faststart"] if fmt in ("mp4_h264", "mov_h264") else [])
    extra = ["-movflags", "+faststart"] if fmt in ("mp4_h264", "mov_h264") else []
    return ["-vf", EVEN_SIZE, "-c:v", "libx264", "-preset", "medium", "-crf", crf,
            "-profile:v", "high", "-pix_fmt", "yuv420p"] + COLOR_TAGS + extra


def build_video_command(ffmpeg, fmt, w, h, fps, total, out_path,
                        audio_path=None, audio_key=None, crf=18, nvenc=False):
    """ffmpeg command that reads raw frames on stdin. Audio is optional."""
    ext = VIDEO_FORMATS[fmt]["ext"][1:]
    cmd = [ffmpeg, "-y", "-hide_banner",
           "-f", "rawvideo", "-pix_fmt", "bgr0", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
    if audio_path and audio_key and fmt != "gif":
        if audio_key not in CONTAINER_AUDIO.get(ext, set()):
            raise ValueError(f"A .{ext} file cannot hold {AUDIO_FORMATS[audio_key]['label']}. "
                             "Choose a different audio format or container.")
        cmd += ["-i", audio_path, "-map", "0:v:0", "-map", "1:a:0",
                "-af", "apad", "-t", f"{total / fps:.6f}"]
        cmd += AUDIO_FORMATS[audio_key]["args"]
    else:
        cmd += ["-an"]
    cmd += ["-threads", "0"]          # let ffmpeg use every core; this does not change pixels
    cmd += video_codec_args(fmt, crf, nvenc)
    cmd.append(out_path)
    return cmd


# ------------------------------------------------------------ audio files

def _write_pcm_wav(path, stereo, sr, width):
    """Write a stereo float array as PCM WAV. width is bytes per sample: 2 or 3."""
    x = np.clip(np.asarray(stereo, dtype=np.float64), -1.0, 1.0)
    if width == 2:
        raw = (x * 32767.0).astype("<i2").tobytes()
    else:
        ints = np.ascontiguousarray((x * 8388607.0).astype("<i4"))
        raw = ints.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()   # keep the low 3 bytes
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(width)
        w.setframerate(int(sr))
        w.writeframes(raw)


def render_audio_temp(stereo, sr):
    """Write the mix to a temporary 24-bit WAV for ffmpeg. The caller deletes it."""
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="motioncode_mix_")
    os.close(fd)
    try:
        _write_pcm_wav(path, stereo, sr, 3)
    except Exception:
        _remove_quietly(path)
        raise
    return path


def export_audio_file(stereo, sr, out_path, key):
    """Save the mix as an audio file. Raises RuntimeError with a readable message on failure."""
    info = AUDIO_FORMATS[key]
    if key == "wav16":
        _write_pcm_wav(out_path, stereo, sr, 2)
        return out_path
    ffmpeg, _names = probe_ffmpeg()
    tmp = render_audio_temp(stereo, sr)
    try:
        result = subprocess.run([ffmpeg, "-y", "-hide_banner", "-i", tmp] + info["args"] + [out_path],
                                capture_output=True, text=True, **NO_WINDOW)
        if result.returncode != 0:
            _remove_quietly(out_path)
            raise RuntimeError(ffmpeg_failure_message(result.stderr, result.returncode))
    finally:
        _remove_quietly(tmp)
    return out_path


# ------------------------------------------------------------ pipeline workers

def _frame_bytes(frame, width, height):
    """Raw RGB32 bytes of a frame, row by row (Qt may pad each row)."""
    row = width * 4
    stride = frame.bytesPerLine()
    raw = bytes(frame.constBits())
    if stride == row:
        return raw[:row * height]
    return b"".join(raw[r * stride:r * stride + row] for r in range(height))


def _video_writer(proc, q, state):
    """Send queued frames to ffmpeg. After an error it keeps draining the queue,
    so the render thread never blocks on a full queue."""
    try:
        while True:
            item = q.get()
            if item is None:
                break
            if state["error"] is None:
                try:
                    proc.stdin.write(item)
                except BrokenPipeError:
                    state["error"] = "ffmpeg stopped reading frames."
                except Exception:
                    state["error"] = traceback.format_exc()
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass


def _png_writer(q, state):
    while True:
        item = q.get()
        if item is None:
            break
        if state["error"] is not None:
            continue
        path, frame = item
        if not frame.save(path):
            state["error"] = f"Could not save {os.path.basename(path)}"


# ------------------------------------------------------------ export job

class ExportJob(QThread):
    """Renders frames on this thread and writes them on a second thread."""
    progress = Signal(int)
    succeeded = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, scene, animate_fn, width, height, fps, speed, total, out_path,
                 mode, cmd=None, temp_paths=(), render_fn=None, queue_size=4):
        super().__init__()
        self.scene = scene
        self.animate_fn = animate_fn
        self.width = width
        self.height = height
        self.fps = fps
        self.speed = speed
        self.total = total
        self.out_path = out_path
        self.mode = mode
        self.cmd = cmd
        self.temp_paths = list(temp_paths)
        self.render_fn = render_fn
        self.queue_size = max(1, int(queue_size))
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            if self.mode == "png":
                self._run_png()
            else:
                self._run_video()
        except Exception:
            self.failed.emit(traceback.format_exc())
        finally:
            for path in self.temp_paths:
                _remove_quietly(path)

    def _time(self, index):
        return index * self.speed / self.fps

    def _render(self, index):
        return self.render_fn(self.scene, self.animate_fn, self.width, self.height,
                              self._time(index), self.fps)

    def _run_png(self):
        q = queue.Queue(maxsize=self.queue_size)
        state = {"error": None}
        writer = threading.Thread(target=_png_writer, args=(q, state), daemon=True)
        writer.start()
        skipped = 0
        first_error = None
        for index in range(self.total):
            if self._cancel or state["error"]:
                break
            path = str(Path(self.out_path) / f"frame_{index:05d}.png")
            try:
                q.put((path, self._render(index)))
            except Exception as exc:
                skipped += 1
                if first_error is None:
                    first_error = f"frame {index}: {type(exc).__name__}: {exc}"
            self.progress.emit(index + 1)
        q.put(None)
        writer.join()
        if self._cancel:
            self.cancelled.emit()
            return
        if state["error"]:
            self.failed.emit(state["error"])
            return
        note = f" ({skipped} frames skipped; first problem: {first_error})" if skipped else ""
        self.succeeded.emit(f"PNG export finished: {self.total} frames{note}")

    def _run_video(self):
        frame_size = self.width * self.height * 4
        q = queue.Queue(maxsize=self.queue_size)
        state = {"error": None}
        stderr_log = tempfile.TemporaryFile()
        try:
            proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stderr=stderr_log, **NO_WINDOW)
        except OSError as exc:
            stderr_log.close()
            self.failed.emit(f"could not start ffmpeg: {exc}")
            return
        writer = threading.Thread(target=_video_writer, args=(proc, q, state), daemon=True)
        writer.start()

        last_good = bytes(frame_size)
        failed_frames = 0
        first_error = None
        for index in range(self.total):
            if self._cancel or state["error"]:
                break
            try:
                data = _frame_bytes(self._render(index), self.width, self.height)
                last_good = data
            except Exception as exc:
                # A broken frame repeats the last good one, so the video still finishes.
                failed_frames += 1
                if first_error is None:
                    first_error = f"frame {index}: {type(exc).__name__}: {exc}"
                data = last_good
            q.put(data)
            self.progress.emit(index + 1)
        q.put(None)
        writer.join()
        return_code = proc.wait()
        stderr_log.seek(0)
        ffmpeg_output = stderr_log.read().decode("utf-8", errors="replace")[-4000:]
        stderr_log.close()

        if self._cancel:
            _remove_quietly(self.out_path)
            self.cancelled.emit()
            return
        if state["error"] or return_code != 0:
            _remove_quietly(self.out_path)
            detail = ffmpeg_failure_message(ffmpeg_output, return_code)
            message = (state["error"] + "\n" if state["error"] else "") + detail
            self.failed.emit(message)
            return
        note = f", {failed_frames} frames repeated after errors ({first_error})" if failed_frames else ""
        self.succeeded.emit(f"Video saved: {Path(self.out_path).name} ({self.total} frames, "
                            f"{self.width}×{self.height}, {self.fps} fps{note})")
