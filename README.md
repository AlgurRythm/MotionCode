# MotionCode

MotionCode makes motion graphics and animated videos from short Python scripts.
You write the scene and the animation in code, watch it in the preview, and export
it as a video, a GIF, PNG frames, or sound.

## What you can make

- Title cards, logo reveals and lower thirds
- Animated diagrams, charts and explainers
- Looping backgrounds and social media clips (square or vertical)
- Short soundtracks with mood beds, clicks and sound effects
- Frame sequences for other editors

## How it works

1. **Write** a video script (shapes and motion) and an audio script (sound).
2. **Apply Code** to run them. The preview updates at once.
3. **Scrub or play** the timeline to check the motion.
4. **Export** as MP4, MOV, MKV, WebM, GIF, PNG frames, or an audio file.

Every frame is drawn from the same function of time, so the preview and the export match.

---

## Tutorial 1: Your first scene

A video script has two functions. `build` runs once and creates objects.
`animate` runs for every frame, with `t` as the time in seconds.

```python
import math

def build(scene):
    scene.background = "#080D18"
    scene.duration = 6
    scene.fps = 30
    scene.add_circle("Ring", x=960, y=540, radius=180, color="#35B9FF", stroke=8)
    scene.add_text("Title", "HELLO", x=960, y=540, size=76, color="#FFFFFF")

def animate(scene, t):
    ring = scene.get("Ring")
    ring.rotation_z = t * 45          # degrees, clockwise
    ring.scale = 1 + 0.1 * math.sin(t * 2)
    scene.get("Title").opacity = min(1, t / 1.5)
```

Rules to remember:
- Every object needs a unique name.
- In `animate`, set absolute values (`rotation_z = t * 45`), not values added each frame.
- Coordinates start at the top-left. The scene is 1920 × 1080 by default.

---

## Tutorial 2: Shapes and text

```python
def build(scene):
    scene.add_rect("Card", x=960, y=540, width=600, height=340, color="#1E2A44", filled=True)
    scene.add_rounded_rect("Pill", x=960, y=200, width=300, height=80, radius=40, color="#FF7EB6")
    scene.add_star("Star", x=400, y=800, outer_radius=90, inner_radius=40, color="#FFD479", filled=True)
    scene.add_polygon("Tri", points=[(0, -60), (60, 60), (-60, 60)], x=1500, y=800, color="#9EFF8F", filled=True)
    scene.add_text("Label", "Left aligned", x=700, y=540, size=48, align="left", max_width=500)
```

Common properties for every shape: `x`, `y`, `color`, `opacity`, `scale`,
`scale_x`, `scale_y`, `rotation_z`, `skew_x`, `stroke`, `filled`.

---

## Tutorial 3: Keyframes

Keyframes animate one property between points without writing `animate` code.

```python
def build(scene):
    scene.add_circle("Ball", x=200, y=800, radius=40, color="#FF7EB6", filled=True)
    scene.duration = 4
    scene.keyframes("Ball", "x", [(0, 200), (2, 1600)], ease="ease_out")
    scene.keyframes("Ball", "y", [(0, 800), (1, 300), (2, 800)], ease="ease_in_out")
```

Keyframes run after `animate`, so they win for the properties they set.
Easing: `linear`, `ease_in`, `ease_out`, `ease_in_out`.

---

## Tutorial 4: Transitions

`transitions` gives ready-made entrances and exits.

```python
import transitions as tr

def build(scene):
    scene.duration = 6
    scene.add_text("Title", "OPENING", x=960, y=500, size=90, color="#FFFFFF")

def animate(scene, t):
    title = scene.get("Title")
    tr.enter(title, t, start=0.5, duration=0.6, style="slide_up", base=(960, 500), distance=60)
    tr.exit(title, t, start=4.5, duration=0.5, style="fade", base=(960, 500))
```

Styles: `fade`, `slide_left`, `slide_right`, `slide_up`, `slide_down`, `pop`, `zoom`.
Pass `base` every frame so the object returns to the same place.

---

## Tutorial 5: Styles and effects (FeaturesPro)

`FeaturesPro` adds finished looks. Import it as `pro`.

```python
import math
import FeaturesPro as pro

def build(scene):
    pro.Styled(scene, "Sign", "text", style="neon", text="OPEN", x=960, y=540, size=160)
    pro.Styled(scene, "Badge", "rounded_rect", style="brutal", x=960, y=800,
               width=420, height=120, color="#FFE14D")
    scene.add_circle("Dot", x=400, y=300, radius=60, color="#35B9FF", filled=True, blur=0)
    scene.bloom = 0.6                  # glow on bright pixels
    scene.bloom_threshold = 0.7

def animate(scene, t):
    scene.get("Sign").rotation_z = math.sin(t) * 3
    pro.update_all(scene, t)           # always last in animate
```

Other styles include `paper`, `deco`, `holo`, `blueprint`, `isometric`, `handdrawn`, `pixel`.
Other helpers include `pro.Burst` (particles), `pro.Trail` (ghost copies),
`pro.liquid`, `pro.kinetic` (letters rising in turn), `pro.caption`, and `pro.grid`.

Colour gradients and lights:

```python
scene.get("Card").gradient = pro.Gradient([(0, "#FF7EB6"), (1, "#35B9FF")], angle=45)
scene.lights = [pro.Light(960, 540, radius=700, intensity=1.2)]
```

Set `obj.lit = True` for an object that should react to lights.

---

## Tutorial 6: Sound

The audio script runs separately, on the same timeline as the video.

```python
def build_audio(audio):
    audio.duration = 6
    audio.sample_rate = 44100
    audio.master_volume = 0.8

    audio.add_mood("bed", mood="calm", start=0, length=6, base_freq=220)
    audio.add_tone("chime", freq=660, start=0.5, length=0.8, volume=0.15, wave="sine")
    audio.add_click("tick", at=2, volume=0.3)
    audio.add_noise("whoosh", start=4, length=1.2, volume=0.05, fade_in=0.4, fade_out=0.8)
```

- Moods: `happy`, `sad`, `calm`, `quiet`, `soft`, `loud`, `excited`, `tense`, `neutral`.
- Waveforms for tones: `sine`, `square`, `triangle`, `saw`.
- `pan` moves a sound left (-1) or right (+1).
- `audio.add_clip("Name", "file.mp3", at=5)` plays a file from the assets folder.

Keep the audio `duration` equal to the video `duration`.

---

## Tutorial 7: Export

Choose **File > Export...** and pick:

| Setting | What it does |
|---------|--------------|
| File type | MP4, MOV, MKV, WebM, GIF, WAV, FLAC, M4A, MP3, OGG, Opus, or PNG frames |
| Resolution | Up to 4K. Vertical and square sizes are included |
| FPS | Frames per second (15 to 120) |
| Resolution elements | Ultra, High, Balanced, Medium, Low or Very low. Changes only the heavy effects |
| Compression | Quality versus file size. Lowest setting is near lossless |

The audio track is chosen automatically for each video type. Your last choices and
the last save folder are remembered.

Video files are H.264 (WebM uses VP9) in standard colour, so they play in common players.

---

## Tutorial 8: Working in the app

- **Editors:** video script on the left, audio script in the middle. Failing lines turn red.
  Press **Ctrl+Space** for autocomplete.
- **Preview:** Play/Pause, the timeline with keyframe markers, and the playback speed.
- **Scene list:** drag rows to change layer order. The top of the list is in front.
- **Inspector:** edit an object's position, rotation, scale and opacity live.
  These edits are lost on Apply, so write final values into the script.
- **File menu:** Save Project, Open Project and Check script. Check script runs your
  code at the start, middle and end without exporting, so you can find errors first.
- **Theme button (top right):** switch between Dark, Bright and OLED.
- **Autosave:** scripts are saved every few seconds. If the app closes unexpectedly, it offers to restore them.

---

## Quick reference

```
scene.duration = 10          scene.fps = 30
scene.background = "#050812" scene.width / scene.height
scene.get(name)              scene.get_optional(name)
scene.keyframes(obj, "x", [(0, 0), (2, 500)], ease="ease_out")
scene.bring_to_front(name)   scene.send_to_back(name)

tr.enter(obj, t, start, duration, style, base=(x, y))
tr.exit(obj, t, start, duration, style, base=(x, y))
pro.update_all(scene, t)     # last line of animate, when using FeaturesPro
```
