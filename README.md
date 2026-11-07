# MotionCode Reference

## Description

MotionCode is a motion graphics application. A motion graphic is written as two short
scripts: a video script that creates and animates shapes, text and 3D objects, and an audio
script that builds the sound. The app runs both on the same timeline, shows the result in a
live preview, and exports finished video, GIF, image sequence or audio files.

## Owner

**Vince Winter** and **Claude By Anthropic**

## The Tutorial

If you want to understand the app without code, open [Basic.md](Basic.md). It explains every task
in plain language: changing the motion and sound, the theme, settings, export, saving,
opening projects, fonts, credits and the Data folder.

---

## How the software works

1. **Two scripts, one timeline.** The video script has a `build` step that runs once to
   create objects, and an `animate` step that runs for every frame with the time `t` in
   seconds. The audio script has a `build_audio` step that places sounds on the same timeline.
2. **Every frame is a function of time.** The app calls `animate` with a time and draws what
   it sees. Because nothing depends on the previous frame, scrubbing, previewing and exporting
   give the same picture.
3. **Layers.** Objects are drawn in list order. Later objects sit in front. Layer motion can move
   an object up or down the list over time.
4. **Quality levels.** The Resolution elements setting only changes heavy effects (blur,
   lighting, motion blur, supersampling). Every object is always drawn.
5. **Export.** The export worker renders each frame with the same function the preview uses,
   sends frames to ffmpeg, and writes the file. The sound is mixed at the same speed as the picture.
6. **Files.** Projects are `.mcp` files holding both scripts. Settings, cache, fonts, assets and
   3D models live in the Data folder next to the program.

---

## Full understanding needs an AI

This document describes the software and the kinds of work it suits. It does not explain how to
combine the tools into a good animation, or how the parts interact in a real project.

To learn the whole system, download the code library here:

**[Download Motion-Code-Library.md](PASTE-YOUR-CODE-LINK-HERE)**

Give that file and this reference to an AI assistant that can read them together.

**Why it is needed.** This reference is an outline. The library holds the working code and the
exact rules behind it. An AI that reads both can explain how a part works, write a script that
uses it correctly, and find the cause when a script fails.

**What the library contains:**

- **The MotionCode database.** Every public part of the app, with the exact rules for rotation,
  layers, timing, shapes, effects, sound and export.
- **Physics and simulation.** Rigid collisions, cloth simulation and fluid particles, each with
  its code and an explanation of how it is made.
- **Character articulation.** A mug grab, a punch with a physical fall, and two-bone inverse
  kinematics for stick figures.
- **Motion examples.** Path motion, layout motion and character motion, with settings to change.
- **Transitions and kinetic typography.** Two complete scripts, each explained part by part.
- **Camera and cinematic examples.** A camera moving along a spline at constant speed, and real
  shadows from a moving light.
- **Audio songs.** Five complete audio scripts, each with an explanation of its sound.

**A note on the database.** The MotionCode database in the library is the first reference and
the basic one. It is not the most complete version, but it is enough for an AI to learn
MotionCode from. Treat its answers as a starting point, and run any script in the app to check it.

---

## Specialisations

MotionCode suits these kinds of motion work. Each uses the parts listed above.

- **Kinetic typography.** Letters and words that rise, fade, flip or type on: `kinetic`,
  `word_reveal`, `typed`, `caption`, `split_flap`.
- **Title and logo reveals.** Entrances and exits with overshoot, stroke drawing and glow:
  `enter`, `exit`, `pop`, `zoom`, `stroke_draw`, `bloom`.
- **Explainers and diagrams.** Lines, arrows, measurements and progressive drawing: `add_line`,
  `dimension`, `stroke_draw`, `layer`, `bring_to_front`.
- **Retro and pixel graphics.** Grids, pixel sprites and palette colours: `pixel_sprite`, `grid`,
  `set_pixel_palette`, the `pixel` style.
- **Stylised 2D looks.** Neon, brutal, paper, Art Deco, holographic and blueprint: `Styled`,
  `deco_frame`, `paper_sheet`, `gradient`.
- **3D product and object spins.** Built-in shapes, OBJ models and wireframes with lighting:
  `add_cube`, `add_obj`, `add_wireframe`, `Light`, `rotation_x/y/z`.
- **Particles and energy.** Bursts, emitters, trails and glow: `Burst`, `emitter`, `Trail`, `blend="add"`,
  `bloom`.
- **Motion with physics feel.** Bounce, spring, squash and stretch, shake: `bounce`, `spring`,
  `squash_stretch`, `shake`, `velocity_stretch`.
- **Liquid and organic shapes.** Blobs and morphing outlines: `liquid`, `Gradient`.
- **Masks and reveals.** Hide, blur or tint parts of the picture behind a shape: `mask`,
  `backdrop_blur`, `Mask`.
- **Sound-led motion.** Animation timed to a soundtrack built from moods, tones, clicks and noise:
  `add_mood`, `add_click`, `add_noise`, `add_clip`.
- **Social and square formats.** Square and vertical exports with fast, short motion, using
  the export presets and resolution list.
- **Explainer characters and figures.** Parent-and-child rigs: `parent`, rotation of children
  relative to parents, `add_ellipse`, `add_polygon`.
