# MotionCode

## Description

MotionCode turns code into motion graphics. You write the shapes, text, movement and sound
as short Python scripts, watch every frame update in a live preview as you type, and export
the result as a video, a GIF, PNG frames or an audio file.

Nothing is hidden behind a timeline of clicks. Every position, colour, rotation and sound
is a value you can read, change and reuse, so a design that takes an hour to tweak by hand
can be changed in one line and re-applied in a second.

## Creator

**Vince Winter**

## What it is used for

MotionCode can make a wide range of motion graphics, as long as the effect can be described
in code. It is a good fit for:

- Title cards, lower thirds and logo reveals
- Animated diagrams, charts and explainers
- Looping backgrounds and visual loops
- Social media clips in square and vertical formats
- Kinetic type, where letters rise, fade or flip in sequence
- Short films with a matching soundtrack made from tones, moods and clicks
- Frame sequences for another editor

It is not a replacement for a full video editor. It does not edit footage, and it does not
record your screen or camera. Use it to make the graphics and sound, then export them and
combine them in your editor if you need to.

---

## Functions

Each section below is a task you can do in the app, with the steps to do it.

### Start a project

1. Open MotionCode. The starter script draws a ring, a title and a cube.
2. To start fresh, choose **File > New**.

### Update the video code

1. Click in the **Video script** editor (left).
2. Edit the `build(scene)` function to create objects, and the `animate(scene, t)`
   function to move them. `t` is the time in seconds.
3. Press **Apply Code** in the top bar. The preview updates.
4. If something is wrong, the line turns red and the log explains why.

Minimal example:

```python
import math

def build(scene):
    scene.duration = 6
    scene.fps = 30
    scene.background = "#080D18"
    scene.add_circle("Ring", x=960, y=540, radius=180, color="#35B9FF", stroke=8)
    scene.add_text("Title", "HELLO", x=960, y=540, size=76, color="#FFFFFF")

def animate(scene, t):
    scene.get("Ring").rotation_z = t * 45          # degrees, clockwise
    scene.get("Title").opacity = min(1, t / 1.5)
```

Set absolute values in `animate`. Do not add to a value each frame, or it will keep
growing when you scrub the timeline.

### Update the audio code

1. Click in the **Audio script** editor (middle).
2. Edit `build_audio(audio)`. Add a mood bed, a tone, a click or a noise.
3. Press **Apply Audio** (above the audio editor). The audio is ready for preview and export.

```python
def build_audio(audio):
    audio.duration = 6              # keep this equal to the video length
    audio.sample_rate = 44100
    audio.master_volume = 0.8
    audio.add_mood("bed", mood="calm", start=0, length=6, base_freq=220)
    audio.add_click("tick", at=2, volume=0.3)
```

### Play and scrub the preview

- Press **Play** to watch the animation. Press it again to pause.
- Drag the timeline to jump to any moment. Keyframes appear as markers on it.
- Change **Speed** in the Settings box to play faster or slower.

### Change the theme

1. Look at the top-right corner of the menu bar.
2. Click the **Theme** button. It cycles **Dark**, then **Bright**, then **OLED**.
3. The choice is remembered for next time.

### Change the settings

The **Settings** box (bottom of the window) holds the options that affect the preview and export:

| Setting | How to change it |
|---------|------------------|
| **Resolution** | Choose from the list. The preview and the default export size follow it. |
| **Resolution elements** | Choose Ultra, High, Balanced, Medium, Low or Very low. Higher levels draw the heavy effects at higher quality. Every object is always drawn. |
| **FPS** | Type or pick a value from 15 to 120. Your script can also set it with `scene.fps`. |
| **Speed** | Set the playback speed. Exports follow this speed too. |
| **Encoder** | CPU (libx264) or NVIDIA (h264_nvenc, needs an NVIDIA GPU). |
| **Volume** | Set the sound level from 0 to 150 percent. |

### Export a video, GIF, PNG frames or audio

1. Choose **File > Export...**.
2. Pick a **file type**: MP4, MOV, MKV, WebM, GIF, WAV, FLAC, M4A, MP3, OGG, Opus, or PNG frames.
3. Set the **Resolution**, **FPS**, **Resolution elements** and **Compression**.
   - Compression sets quality against file size. The lowest setting is nearly lossless.
4. Press **Export** and choose where to save.
5. A progress window shows the frame count and the time left. **Cancel** stops the export and
   deletes the partial file.

Video files are H.264 (WebM uses VP9) in standard colour, so they play in common players.
The audio track is added automatically. Your choices and the last save folder are remembered.

### Check a script before a long export

- Choose **File > Check script**.
- The app runs your code at the start, middle and end, without exporting, and reports any errors.

### Save a project

1. Choose **File > Save Project**. The first time, it asks where to save.
2. Your video and audio scripts are saved together in one `.mcp` file.
3. Use **File > Save Project As** to save a copy under a new name.

### Open a project

1. Choose **File > Open Project**.
2. Select a `.mcp` file. Both scripts load and the preview updates.
3. The folder you used last time is remembered.

### Recover unsaved work

- Your scripts are auto-saved every few seconds, in the `Data/cache` folder.
- If the app closes unexpectedly, it offers to restore them the next time you open it.

### Use fonts

1. Open the **Fonts** menu.
2. **Default fonts and licenses...** lists fonts you can use, with their licences.
3. **Import font...** copies a `.ttf` or `.otf` file into your fonts folder.
4. **Open fonts folder** opens that folder.
5. Use the font by its family name:

```python
scene.add_text("Title", "HELLO", x=960, y=540, size=90, font="Oswald")
```

### Use your own 3D models

1. Put a `.obj` file in your **Data** folder.
2. Load it by file name:

```python
scene.add_obj("Model", "your_model.obj", scale=1.0, filled=True)
```

### Use images and sound files

1. Click **Import** in the Assets panel and pick the files. They are copied into your assets folder.
2. Double-click an audio file in the list to hear it.
3. Place a sound on the timeline in the audio script:

```python
audio.add_clip("Sting", "sting.mp3", at=5.0)
```

### Add your credits and licences

1. Put your text in the **Data** folder as `CREDITS.md`.
   Optional: `LICENSE`, `NOTICE` and `THIRD_PARTY_NOTICES.md`.
2. Open the **Credits** menu:
   - **Credits** opens `CREDITS.md`.
   - **License**, **Notice** and **Third-party notices** open the other files.
3. If a file is missing, the log names it.

### Set up the Data folder

Everything the app stores or reads lives in one **Data** folder next to `MotionCode.exe`:

```
MotionCode/
  MotionCode.exe
  Data/
    CREDITS.md                 your credits
    LICENSE, NOTICE            licence files
    export_settings.json       remembered export choices (created by the app)
    motioncode_settings.ini    remembered preferences, such as the theme (created by the app)
    cache/                     auto-saved scripts (created by the app)
    projects/                  project files
    fonts/                     fonts you import
    assets/                    sound and image files you import
    your_model.obj             3D models
```

### Use the effects and styles

Import **FeaturesPro** as `pro` for ready-made looks:

```python
import FeaturesPro as pro

def build(scene):
    pro.Styled(scene, "Sign", "text", style="neon", text="OPEN", x=960, y=540, size=160)
    scene.bloom = 0.6              # glow on bright pixels
    scene.bloom_threshold = 0.7

def animate(scene, t):
    pro.update_all(scene, t)       # always the last line
```

Styles include `neon`, `brutal`, `paper`, `deco`, `holo`, `blueprint`, `isometric`,
`handdrawn` and `pixel`.

### Use transitions

```python
import transitions as tr

def animate(scene, t):
    title = scene.get("Title")
    tr.enter(title, t, start=0.5, duration=0.6, style="slide_up", base=(960, 500), distance=60)
    tr.exit(title, t, start=4.5, duration=0.5, style="fade", base=(960, 500))
```

Styles: `fade`, `slide_left`, `slide_right`, `slide_up`, `slide_down`, `pop`, `zoom`.

### Change layer order

- Drag rows in the **Scene list** (right side of the editor). The top row is drawn in front.
- Or set it in the script with `scene.bring_to_front("Title")` and `scene.send_to_back("Background")`.

### Edit values live

- Select an object in the Scene list. The **Inspector** shows its position, rotation,
  scale and opacity.
- Changes show in the preview at once. They are lost when you press **Apply Code**, so write
  the final value into the script.

### Find and fix errors

- A failing line turns red in the editor. The log below gives the reason.
- Use **Ctrl+Space** in an editor to see names and keywords.

---

## Quick reference

```
scene.duration = 10            scene.fps = 30
scene.background = "#050812"   scene.width / scene.height
scene.get(name)                scene.get_optional(name)
scene.keyframes(obj, "x", [(0, 0), (2, 500)], ease="ease_out")
scene.bring_to_front(name)     scene.send_to_back(name)

import transitions as tr
tr.enter(obj, t, start, duration, style, base=(x, y))
tr.exit(obj, t, start, duration, style, base=(x, y))

import FeaturesPro as pro
pro.update_all(scene, t)       # last line of animate, when you use FeaturesPro
```
