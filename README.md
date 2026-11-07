# MotionCode

## Description

MotionCode is a motion graphics app for people who want results without hours of keyframing.
You describe a motion in a few simple lines, see it play back instantly, and export it as a
finished video, a GIF, a set of PNG frames, or a sound file.

You do not need to be a programmer. You only need to be willing to write a line or two and
press a button to see what happens. Every change shows up in the preview the moment you apply it,
so experimenting is quick.

## Creator

**Vince Winter**

## What it is for

MotionCode is for making motion graphics that are clean, repeatable and easy to change:

- Title cards, lower thirds and logo reveals
- Animated diagrams and explainers
- Looping backgrounds
- Social media clips in square and vertical sizes
- Text that rises, fades or flips in sequence
- Short pieces with a matching soundtrack

It does not edit footage, record your screen, or replace a full video editor. Make the
graphics and sound here, export them, and finish the edit in your usual editor.

---

## How to use it

### Start a new project

Open MotionCode. A starter animation is already loaded so you can see how it works.
To begin with an empty project, choose **File**, then **New**.

### Change the motion

Every animation has two parts, and you edit them in the left panel:

- The **video** part sets up what appears on screen and how it moves.
- The **audio** part sets up the sound.

Change a number, such as a colour, a size or a timing, then press **Apply Code** at the top.
The preview updates straight away. If a line turns red, the log at the bottom explains the
mistake. Fix the line and apply again.

### Add sound

Edit the **audio** part, then press **Apply Audio** above the audio panel. You can add a background
mood, a single tone, a click, or a sound effect. The sound plays in the preview and goes into your export.

### Preview the animation

- Press **Play** to watch it, and press it again to pause.
- Drag the timeline to jump to any moment.
- Change **Speed** to watch it slower or faster.

### Change the theme

Look at the top-right corner. Click the **Theme** button to switch between **Dark**, **Bright**
and **OLED**. Your choice is remembered.

### Change the settings

The **Settings** box below the preview holds the options:

- **Resolution** sets the picture size.
- **Resolution elements** sets how heavy the visual effects are. Higher settings look better and
  take longer. Choose from Ultra, High, Balanced, Medium, Low and Very low.
- **FPS** sets how smooth the motion is. Higher values need more work.
- **Speed** sets how fast the animation plays.
- **Encoder** chooses CPU, or NVIDIA if your graphics card supports it.
- **Volume** sets the sound level.

### Export your work

1. Choose **File**, then **Export**.
2. Pick a file type: a video (MP4, MOV, MKV, WebM or GIF), a sound file (WAV, FLAC, M4A, MP3, OGG
   or Opus), or a folder of PNG images.
3. Set the resolution, frame rate, resolution elements and compression.
   Compression trades quality for file size, and the lowest setting is nearly lossless.
4. Press **Export**, then choose where to save.
5. A progress window shows how much is done and how long is left. Press **Cancel** to stop.

Video files play in common players. The sound is added to the video automatically.
MotionCode remembers your last export settings and the folder you saved to.

### Save a project

1. Choose **File**, then **Save Project**.
2. The first time, pick a name and a place. Your video and sound parts are saved together in one file.
3. To keep a separate copy, choose **Save Project As**.

### Open a project

1. Choose **File**, then **Open Project**.
2. Select the project file. Both the video and sound parts load, and the preview updates.

### Recover unsaved work

MotionCode saves a backup of your work every few seconds. If the app closes unexpectedly,
it offers to restore your last work the next time you open it.

### Check before a long export

Choose **File**, then **Check Script**. It runs through the whole animation and reports any problems
without exporting anything. Use it before a long export.

### Add fonts

1. Open the **Fonts** menu.
2. Choose **Import font** and pick a `.ttf` or `.otf` file.
3. To see what is available, choose **Default fonts and licenses**.
4. To find your fonts on disk, choose **Open fonts folder**.

Once a font is installed, you can pick it by name in the text settings.

### Add your own 3D models

Put a `.obj` file in the **Data** folder next to the app. Then use it by its file name in the video part.
MotionCode finds it there, so you do not need to type the full path.

### Add sound and image files

1. In the **Assets** panel, click **Import** and pick your files.
2. Double-click an audio file in the list to hear it.
3. Use the file in the audio part by its name, and choose when it starts.

### Add your credits and licences

1. Open the **Data** folder next to the app.
2. Put your text in a file called `CREDITS.md`. Optional files: `LICENSE`, `NOTICE` and
   `THIRD_PARTY_NOTICES.md`.
3. Open the **Credits** menu. **Credits** shows your credits. **License**, **Notice** and
   **Third-party notices** show the other files.
4. If a file is missing, the log tells you its name.

### Understand the Data folder

Everything the app keeps is in one **Data** folder next to the program:

- **CREDITS.md** and the licence files, for the Credits menu
- **export_settings.json**, your remembered export choices (created by the app)
- **motioncode_settings.ini**, remembered preferences such as the theme (created by the app)
- **cache**, the automatic backups (created by the app)
- **projects**, your saved projects
- **fonts** and **assets**, the fonts and sound or image files you import
- your **3D models**

### Move objects and change layers

- Drag items in the **Scene list** to change their order. The item at the top is drawn in front.
- Select an item to see its **Inspector**. Change its position, rotation, size or opacity, and watch the preview.
- Inspector changes are lost when you press **Apply Code**. Once you like a value, write it into the animation.

### Fix a problem

- A red line in the editor means something is wrong there.
- The log at the bottom explains what it is and which line to check.
- Press **Ctrl+Space** in an editor to see the words the app understands.

---

## Tips for getting good results

- Start with one or two objects and add more once the first one behaves.
- Use **Check Script** after each big change.
- Preview at a lower resolution while you work, and export at full size at the end.
- Keep the sound length the same as the video length so they finish together.
