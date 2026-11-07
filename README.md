# MotionCode

**Creator:** Vince Winter

**What it is:** MotionCode is a desktop app for making motion graphics and animated videos
from short Python scripts. You describe the shapes, text, motion and sound in code, watch the
result in a live preview, and export it as a video, GIF, PNG frames or an audio file.

**Who it is for:** anyone who wants precise, repeatable motion graphics, such as title cards,
logo reveals, animated diagrams, looping backgrounds, and social media clips in square or
vertical formats, with a matching soundtrack.

---

## Functions

From easy to hard. Start at the top.

**Easy**
- Draw shapes and text (circles, rectangles, stars, polygons, lines, text).
- Set colours, position, size, opacity and rotation.
- Play and scrub the timeline in the preview.
- Export a video or PNG frames.
- Add background sound with moods, tones and clicks.

**Medium**
- Animate with `animate(scene, t)` or with keyframes.
- Use ready-made entrances and exits (`transitions`).
- Change layer order by dragging in the Scene list.
- Use finished looks from FeaturesPro, such as neon, brutal, paper and holo.
- Use installed fonts by family name.
- Import sound files and play them on the timeline.

**Hard**
- Parent objects so children follow a parent.
- Masks that hide, blur or tint what is behind a shape.
- Gradients and lights, and objects that react to light.
- Motion blur, blend modes (add, screen, multiply) and drop shadows.
- 3D meshes, OBJ models and custom wireframes.
- Particles (`pro.Burst`, `pro.Emitter`) and ghost trails (`pro.Trail`).
- Whole-frame effects: bloom, vignette, grain, colour grade and chromatic aberration.
- Presets that store a group of scene settings.

---

## Getting started

1. Open MotionCode. The starter script draws a ring, a title and a cube.
2. Press **Apply Code** (top bar). The preview updates.
3. Press **Play** or drag the timeline to check the motion.
4. Edit the script and press **Apply Code** again.
5. Choose **File > Export...** when you are happy with it.

Minimal script:

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

Every script has two functions. `build(scene)` runs once and creates objects. `animate(scene, t)`
runs for every frame, with `t` in seconds. In `animate`, set absolute values, not values added
each frame.

---

## The parts of the app

| Part | What it is for |
|------|----------------|
| **Top bar** | Apply Code, the menu bar (File, Fonts, Credits), and the theme button (top right). |
| **File menu** | New, Open and Save Project, Check script, and Export. |
| **Video script editor** | Your `build` and `animate` code. Errors turn the line red. |
| **Audio script editor** | Your `build_audio` code for sound. |
| **Preview** | Shows the scene. Play, pause and scrub. Keyframes show as markers on the timeline. |
| **Scene list** | Every object, top first. Drag rows to change the layer order. |
| **Inspector** | Edit an object's position, rotation, scale and opacity live. |
| **Settings** | Resolution, Resolution elements (quality), FPS, Speed, Encoder and Volume. |
| **Assets panel** | Files you imported for sound and images. Double-click to hear an audio file. |
| **Log** | Every message and error, with the time. Red lines are errors. |

### Settings explained

- **Resolution:** the size of the preview and the default export size.
- **Resolution elements:** how heavy the effects are. Ultra, High, Balanced, Medium, Low and
  Very low. Only effects change; every object is always drawn.
- **FPS:** frames per second for the export. Your script can set it with `scene.fps`.
- **Speed:** playback speed. Exports follow this speed too.
- **Encoder:** CPU (libx264) or NVIDIA (h264_nvenc, needs an NVIDIA GPU).
- **Volume:** the sound level, 0 to 150 percent.

---

## Set it up for your own use

Everything the app stores or reads lives in one **Data** folder next to `MotionCode.exe`.

```
MotionCode/
  MotionCode.exe
  Data/
    CREDITS.md                 your credits text (or CREDITS.txt)
    LICENSE                    licence text (opened from Credits > License)
    NOTICE                     notice text (opened from Credits > Notice)
    THIRD_PARTY_NOTICES.md     third-party notices
    export_settings.json       remembered export choices and the last folder (created by the app)
    motioncode_settings.ini    remembered preferences such as the theme (created by the app)
    cache/                     auto-saved scripts (created by the app)
    projects/                  project files
    fonts/                     fonts you install
    assets/                    sound and image files you import
    your_model.obj             3D models, loaded by name
```

- **Your own credits:** put your text in `Data/CREDITS.md`, then open **Credits > Credits**.
- **Your own models:** put a `.obj` file in `Data/` and load it with
  `scene.add_obj("Model", "your_model.obj")`. No full path is needed.
- **Your own fonts:** use **Fonts > Import font...** to copy a `.ttf` or `.otf` file in.
  Then use its family name: `scene.add_text("T", "HELLO", font="Oswald")`.
- **Your own theme:** click the top-right button to cycle Dark, Bright and OLED. The choice is remembered.

---

## Save your work

- **File > Save Project** saves your video and audio scripts into one `.mcp` file.
- **File > Save Project As** chooses a new file.
- **File > Open Project** loads a `.mcp` file.
- The last project folder is remembered.
- Scripts are also **auto-saved** every few seconds to `Data/cache`. If the app closes
  unexpectedly, it offers to restore them next time.

---

## Export

1. Choose **File > Export...**.
2. Pick a **file type**: MP4, MOV, MKV, WebM, GIF, WAV, FLAC, M4A, MP3, OGG, Opus, or PNG frames.
3. Set **Resolution** (up to 4K, plus square and vertical sizes), **FPS**,
   **Resolution elements** and **Compression**.
4. Press **Export**. A progress window shows the frame count and the time left. Cancel stops it
   and deletes the partial file.

Video is H.264 (WebM uses VP9) in standard colour, so it plays in common players. The audio track
is chosen for you. Your settings and the last save folder are remembered in
`Data/export_settings.json`.

**Check script** (File menu) runs your code at the start, middle and end without exporting. Use it
before a long export.

---

## Credits and licences

**Credits > Credits** opens `Data/CREDITS.md`.
**Credits > License**, **Notice** and **Third-party notices** open the licence files in `Data/`.
If a file is missing, the log says which file to add to the Data folder.

---

## Hidden features

- **Autocomplete:** type two letters, or press **Ctrl+Space**, to see names and keywords.
- **Live Inspector:** change a value while watching the preview. Changes are lost on
  Apply Code, so write the final value into the script.
- **Keyframe markers:** hover over the timeline to see which properties are keyframed and when.
- **Errors on the line:** a failing line is red in the editor, and the log shows the reason.
- **Batch lines are ignored:** lines such as `@echo off` or `pause` in a script are skipped,
  so scripts copied from a `.bat` file still run.
- **Preview reuse:** the preview keeps recent frames, so scrubbing back is fast.
- **Quality rebuild:** changing Resolution elements rebuilds scripts that depend on it.
- **Sound preview:** double-click an imported audio file in the Assets panel to hear it.
- **Fonts by name:** every font in `Data/fonts` loads at startup. Use its family name.
- **Named presets:** `scene.define_preset("night", background="#050812")` saves scene settings
  under a name. Apply them with `scene.apply_preset("night")` in `build`.
- **Pixel palettes:** `pro.set_pixel_palette("retro")` changes the colours used by pixel-art styles.
- **Clear selection:** press **Esc** in the Scene list to clear the selection.
- **Recovery:** if the app closes unexpectedly, your last scripts come back on the next launch.

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
