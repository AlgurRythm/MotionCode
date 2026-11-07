# MotionCode

MotionCode is a Windows app for making motion graphics and animated videos by writing Python. Write a video script and an audio script, press **Apply Code**, and watch the result in the preview. Export to MP4, WebM, GIF, PNG frames, or WAV audio.

Scripts run on your computer, so only run scripts you trust.

---

## Get MotionCode

### Option 1: Download the app (easiest)

1. Go to the **Releases** page of this repo.
2. Download **MotionCode.zip** from the latest release.
3. Unzip it to a folder you can write to, such as `Documents\MotionCode`. Do not use `Program Files`.
4. Keep `MotionCode.exe` and the `_internal` folder together. The app needs both.
5. Double-click **MotionCode.exe** to start.

You do not need Python or Git for this option.

### Option 2: Build it from the source

1. Install [Python 3.10 or newer](https://www.python.org) and [Git](https://git-scm.com).
2. Clone or download this repo.
3. Run `install_motioncode.bat` to install the packages.
4. Run `run_motioncode.bat` to start the app from source.

---

## Quick start

1. Open MotionCode. A starter script is already loaded.
2. Click **Apply Code** to run it.
3. Press **▶ Play** to preview.
4. Edit the script, click **Apply Code** again, and the preview updates.
5. Use **File > Check script** before a long export.
6. Use **File > Export > MP4 video** to render your video.

If audio is silent, check that the **Volume** box in Settings is above 0% and that Windows is not muting the app.

---

## Project layout

| Folder | What is in it |
|---|---|
| `Code` | The Python source: `main.py`, `features.py`, and the engine modules |
| `Data` | Requirements, credits and reference files |
| `Documented Motion` | Reference guides and examples |

---

## Examples

Paste any example into the matching editor and click Apply.

- **Audio songs:** Glass Bells, Pulse Engine, Warm Sunrise, Retro Arcade, Deep Space, Music Box Lullaby
- **Camera and cinematic:** a 3D camera on a spline, and real shadows from a moving light
- **Physics:** rigid collisions, cloth, and fluid particles
- **Motion:** path motion, layout motion, and a walking character
- **Transitions and kinetic typography:** a transitions showcase and a five-part text piece

The reference guides in `Documented Motion` explain what each function does and what it is best for.

---

## Fonts

Scripts can use any font installed on your computer:

```python
scene.add_text("Title", "HELLO", font="Arial")
```

Some examples expect Arial or Verdana. If a font is missing, MotionCode uses a fallback font, and the layout may shift.

---

## Troubleshooting

- **Nothing moves or the timeline stays at 0.00s:** press Play, then check the log box at the bottom left for red error lines.
- **A "No module named" error appears in the log:** the script imports something the app does not include. Remove that import.
- **Windows warns that the app is unknown:** click **More info**, then **Run anyway**. The app is not signed.
- **Audio is silent:** check the Volume box, the Windows volume mixer, and the default output device.

---

## Credits and license

- MotionCode is released under the MIT License. See `LICENSE-Creator`.
- Third-party components and their licenses are listed in `Third-Party-Notice.md`.
- In the app, open **Credits** in the menu bar to see credits and license files.
- Built with Claude by Anthropic and designed with ChatGPT by OpenAI.
