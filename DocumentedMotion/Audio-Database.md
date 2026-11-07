# Audio Songs

Source: AudioCode DataBase. The audio rules come from MotionCode-DataBase, Part 10 (Audio Script) and Part 11 (voice), and from `audio_engine.py`. Each song is a separate audio script with `def build_audio(audio):`.

Before applying any song, set the video's duration to the same number of seconds as `audio.duration`.

---

## Song 1: Glass Bells

**File:** `song_01_glass_bells.py`  
**Length:** 24 seconds

### Audio code

```python
"""SONG 1: GLASS BELLS. 24 seconds. Set the video's duration to 24 too.
Pure sine bells, pentatonic notes, each one panned and left to ring out."""


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def build_audio(audio):
    audio.duration = 24
    melody = [(72, 0.0, 0.8), (76, 0.8, 0.8), (79, 1.6, 0.8), (83, 2.4, 1.2),
              (84, 3.6, 0.8), (79, 4.4, 0.8), (76, 5.2, 0.8), (72, 6.0, 1.6)]
    for loop in range(3):
        for i, (note, start, length) in enumerate(melody):
            t = loop * 8.0 + start
            pan = -0.6 if i % 2 == 0 else 0.6
            audio.add_tone("bell %d %d" % (loop, i), freq=midi(note), start=t, length=length + 2.5,
                           volume=0.22, fade_in=0.005, fade_out=2.0, wave="sine", pan=pan)
            audio.add_tone("bell low %d %d" % (loop, i), freq=midi(note - 12), start=t,
                           length=length + 2.5, volume=0.07, fade_in=0.01, fade_out=2.2,
                           wave="sine", pan=-pan)
```

### What it sounds like

Pure sine bells, each one panned and left to ring out over a pentatonic melody. It's bright and calm.

### How it is made

- Tone list: the melody is eight notes (MIDI numbers) with start times and lengths, in one list.
- Loop: the eight-note pattern repeats three times, each loop 8 seconds later, which makes 24 seconds.
- Two voices per note: a sine at the written pitch and a quieter sine an octave lower.
- Panning alternates left and right, with the low voice panned to the opposite side.

### Why it is made this way

- Sine waves have no overtones, so each note sounds clean, like a bell.
- The long fade-out (2 seconds) makes each note ring after the next one starts.
- Alternating pans give a sense of movement without any extra objects.

---

## Song 2: Pulse Engine

**File:** `song_02_pulse_engine.py`  
**Length:** 16 seconds

### Audio code

```python
"""SONG 2: PULSE ENGINE. 16 seconds. Set the video's duration to 16 too.
Fast four-on-the-floor with a square bass, kick, hi-hats and a bright lead."""


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def build_audio(audio):
    audio.duration = 16
    beat = 60.0 / 150.0                        # 150 beats per minute
    bars = int(16 / (beat * 4))
    bass = [36, 36, 43, 41]                    # C, C, G, F
    lead = [72, 75, 79, 75, 72, 79, 82, 79]
    for bar in range(bars):
        for b in range(4):
            t = (bar * 4 + b) * beat
            audio.add_tone("kick %d %d" % (bar, b), freq=60, start=t, length=0.14,
                           volume=0.5, fade_in=0.002, fade_out=0.12, wave="sine")
            audio.add_tone("bass %d %d" % (bar, b), freq=midi(bass[(bar + b) % 4]), start=t,
                           length=beat * 0.8, volume=0.09, fade_in=0.005, fade_out=0.08,
                           wave="square", pan=-0.2)
        for e in range(8):
            t = (bar * 4 + e / 2.0) * beat
            audio.add_noise("hat %d %d" % (bar, e), start=t + beat / 2, length=0.03,
                            volume=0.09 if e % 2 else 0.05, fade_in=0.001, fade_out=0.025,
                            pan=0.5 if e % 2 else -0.5)
        for s in range(8):
            t = (bar * 4 + s / 2.0) * beat
            audio.add_tone("lead %d %d" % (bar, s), freq=midi(lead[s]), start=t,
                           length=beat * 0.4, volume=0.05, fade_in=0.002, fade_out=0.05,
                           wave="square", pan=0.3)
```

### What it sounds like

A fast club beat at 150 BPM: kick on each beat, square-wave bass, hi-hats on the off-beats and a bright lead.

### How it is made

- Tempo: one beat = 60 / 150 seconds. Four beats make a bar, and 16 seconds fits about 4 bars.
- Kick: a low sine (60 Hz) at every beat, with a short fade-out.
- Bass: a square wave that follows the chord pattern, one note per beat.
- Hi-hats: short noise bursts on every half beat, alternating volume and pan.
- Lead: a square-wave phrase of eight short notes per bar.

### Why it is made this way

- Square waves are rich and buzzy, which suits a bass and a lead in dance music.
- Short noise bursts with fast fades sound like hi-hats; very short length keeps them crisp.
- Everything is placed by beat time, so the groove stays locked to the tempo.

---

## Song 3: Warm Sunrise

**File:** `song_03_warm_sunrise.py`  
**Length:** 24 seconds

### Audio code

```python
"""SONG 3: WARM SUNRISE. 24 seconds. Set the video's duration to 24 too.
Soft chord pads that bloom in, with a slow triangle melody on top."""


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def build_audio(audio):
    audio.duration = 24
    chords = [(60, 64, 67), (57, 60, 64), (65, 69, 72), (67, 71, 74)]   # C, Am, F, G
    for i, chord in enumerate(chords):
        start = i * 6.0
        for j, note in enumerate(chord):
            audio.add_tone("pad %d %d" % (i, j), freq=midi(note - 12), start=start,
                           length=6.5, volume=0.07, fade_in=2.0, fade_out=2.5,
                           wave="sine", pan=-0.3 + 0.3 * j)
    melody = [76, 74, 72, 74, 76, 79, 76, 72, 69, 72, 74, 76, 79, 81, 79, 76]
    for i, note in enumerate(melody):
        audio.add_tone("melody %d" % i, freq=midi(note), start=1.0 + i * 1.4, length=1.2,
                       volume=0.14, fade_in=0.4, fade_out=0.9, wave="triangle", pan=0.2)
    audio.add_noise("air", start=0.0, length=24, volume=0.008, fade_in=4.0, fade_out=4.0)
```

### What it sounds like

Soft, slow chords that fade in and out, with a gentle triangle melody on top and faint air underneath.

### How it is made

- Four chords (C, Am, F, G), each lasting 6 seconds, with three sine notes per chord.
- Each chord note fades in over 2 seconds, so the pads bloom rather than start suddenly.
- Melody: sixteen triangle notes, 1.4 seconds apart, with long fades.
- Air: a very quiet noise layer that runs under the whole song.

### Why it is made this way

- Long fade-ins hide the start of each chord, which makes the pad sound warm and smooth.
- Triangle waves are softer than squares, so the melody sits well over the pads.
- The quiet noise layer adds air and space without a clear pitch.

---

## Song 4: Retro Arcade

**File:** `song_04_retro_arcade.py`  
**Length:** 16 seconds

### Audio code

```python
"""SONG 4: RETRO ARCADE. 16 seconds. Set the video's duration to 16 too.
Chiptune: a square-wave arpeggio over a triangle bass, with a click on each bar."""


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def build_audio(audio):
    audio.duration = 16
    beat = 0.25
    progression = [(57, 60, 64), (53, 57, 60), (55, 59, 62), (52, 55, 59)]   # Am F G Em
    for bar in range(16):
        chord = progression[bar % 4]
        bar_start = bar * 4 * beat
        audio.add_click("bar click %d" % bar, at=bar_start, volume=0.2, freq=2400, pan=0.0)
        audio.add_tone("bass %d" % bar, freq=midi(chord[0] - 12), start=bar_start,
                       length=4 * beat, volume=0.18, fade_in=0.005, fade_out=0.05,
                       wave="triangle")
        for s in range(16):
            note = chord[s % 3] + (12 if s >= 8 else 0)
            audio.add_tone("arp %d %d" % (bar, s), freq=midi(note), start=bar_start + s * beat / 4,
                           length=beat / 4 * 0.8, volume=0.06, fade_in=0.001, fade_out=0.02,
                           wave="square", pan=-0.4 if s % 2 else 0.4)
```

### What it sounds like

Chiptune: a fast square-wave arpeggio over a triangle bass, with a short click at the start of every bar.

### How it is made

- Four chords (Am, F, G, Em) repeat, one per bar, for 16 bars.
- Each bar has a triangle bass note and sixteen short square notes (a sixteenth-note arpeggio).
- The arpeggio moves through the chord and then goes up an octave halfway through the bar.
- A click at the start of each bar marks the bar line.

### Why it is made this way

- Square waves and short notes are the classic sound of old arcade and console music.
- Short notes with quick fades keep the arpeggio clear and punchy.
- Alternating left and right pan makes the arpeggio move across the stereo field.

---

## Song 5: Deep Space

**File:** `song_05_deep_space.py`  
**Length:** 30 seconds

### Audio code

```python
"""SONG 5: DEEP SPACE. 30 seconds. Set the video's duration to 30 too.
A slow sawtooth drone, shimmering sine tones that move across the stereo field,
and soft noise swells."""


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def build_audio(audio):
    audio.duration = 30
    audio.add_tone("drone", freq=midi(28), start=0.0, length=30, volume=0.07,
                   fade_in=3.0, fade_out=4.0, wave="saw")
    audio.add_tone("drone fifth", freq=midi(35), start=0.0, length=30, volume=0.03,
                   fade_in=3.0, fade_out=4.0, wave="sine")
    shimmer = [79, 74, 83, 76, 81, 72]
    for i, note in enumerate(shimmer):
        start = 2.0 + i * 4.5
        pan = -0.9 + 1.8 * i / (len(shimmer) - 1)      # slides from left to right
        audio.add_tone("shimmer %d" % i, freq=midi(note), start=start, length=6.0,
                       volume=0.05, fade_in=1.5, fade_out=3.0, wave="sine", pan=pan)
    for k, start in enumerate((0.0, 10.0, 20.0)):
        audio.add_noise("swell %d" % k, start=start, length=6.0, volume=0.02,
                        fade_in=3.0, fade_out=3.0, pan=-0.6 + 0.6 * k)
```

### What it sounds like

A slow, low sawtooth drone with a quiet fifth above it, shimmering sine tones that move across the stereo field, and soft noise swells.

### How it is made

- Drone: a sawtooth at a low note for the full 30 seconds, with long fades in and out.
- Fifth: a quiet sine a fifth above the drone, adding weight.
- Shimmer: six sine tones, one every 4.5 seconds, with the pan moving from far left to far right.
- Swells: three soft noise layers, at 0, 10 and 20 seconds, each panned a different way.

### Why it is made this way

- A sawtooth is rich in harmonics, so it makes a deep, full drone for space sounds.
- Gradual pan changes make the shimmer seem to travel around the listener.
- Long noise fades give the swells a slow, breathing feel.

---

## Song 6: Music Box Lullaby

**File:** `song_06_music_box.py`  
**Length:** 20 seconds

### Audio code

```python
"""SONG 6: MUSIC BOX LULLABY. 20 seconds. Set the video's duration to 20 too.
Sparse triangle plucks, each with a soft ring, like a small wind-up music box."""


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12.0)


def build_audio(audio):
    audio.duration = 20
    tune = [(72, 0.0), (74, 0.7), (76, 1.4), (74, 2.4), (72, 3.1), (69, 3.8),
            (67, 4.9), (69, 5.6), (72, 6.6), (76, 7.7), (79, 8.4), (76, 9.5)]
    for loop in range(2):
        for i, (note, start) in enumerate(tune):
            t = loop * 10.0 + start
            audio.add_tone("pluck %d %d" % (loop, i), freq=midi(note), start=t, length=1.6,
                           volume=0.2, fade_in=0.003, fade_out=1.4, wave="triangle",
                           pan=-0.25 if i % 2 else 0.25)
            audio.add_tone("pluck harmony %d %d" % (loop, i), freq=midi(note + 12), start=t,
                           length=1.2, volume=0.05, fade_in=0.003, fade_out=1.0,
                           wave="sine", pan=0.0)
```

### What it sounds like

Sparse, gentle plucks like a small wind-up music box, each with a soft harmony an octave above.

### How it is made

- Twelve notes make one tune, repeated twice with a 10-second gap between repeats.
- Each note is a triangle pluck that rings for about 1.6 seconds, with a soft fade-out.
- Each pluck has a quiet sine an octave higher, which adds a bell-like shimmer.
- Plucks alternate slightly left and right.

### Why it is made this way

- Triangle waves are soft and mellow, which suits a lullaby.
- Uneven timing between notes leaves space, like a hand-wound music box.
- The octave-up sine adds brightness without making the sound harsh.

---
