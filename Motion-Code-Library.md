# Motion Code Animation Library

This document combines the animation reference files into one place: physics and simulation, character articulation, camera and cinematic examples, motion examples, transitions and kinetic typography, audio songs, and the MotionCode reference.

---



# Source: MotionCode-DataBase.txt

MOTIONCODE REFERENCE (current version)
======================================
Use this file to write video scripts and audio scripts that run in MotionCode
without guessing. Where a rule is exact, it is stated exactly.


PART 0. FILES
-------------
main.py            Launcher. Starts features.py.
features.py        The app: editors, preview, settings, exports.
engine.py          Scene and object classes (add_* methods, Base attributes).
motion_fx.py       Transforms, easing, shake, particles, trails, 3D projection.
effects.py         Gradients, lights, blur, motion blur helpers.
transitions.py     tr.enter / tr.exit entrance and exit styles.
FeaturesPro.py     Visual styles (imported as pro), quality-controlled, plus helpers.
audio_engine.py    Audio scene: tones, noise, clicks, clips, moods.
voice_tts.py       Text to voice (Piper and Windows voices).
projects_fonts.py  Project folders and the font library (imported as pf).
optimization.py    Caches and the export worker.
FeaturesPro_Showcase.py   Example showcase video script.
claude_spark.obj   Example 3D model (optional).
fonts/             Installed fonts (.ttf / .otf) and font_library.json.
assets/            Imported audio and other files.


PART 1. VIDEO SCRIPT BASICS
---------------------------
A video script is a Python file with two functions:

    def build(scene):          # runs once when you click Apply Code
        ...                     # create every object here

    def animate(scene, t):     # runs every frame; t = seconds, from 0 to duration
        ...                     # change properties here (absolute values)

Scene settings (set inside build):
    scene.width = 1920          # authoring size in pixels
    scene.height = 1080
    scene.fps = 30              # sets the FPS box when you apply the script
    scene.duration = 10.0       # seconds
    scene.background = "#050812"          # colour, "#RRGGBB"
    scene.background_gradient = ex.Gradient(...)   # optional, replaces background colour
    scene.lights = [ex.Light(...)]        # optional, see Part 6
    scene.ambient = 0.35        # base brightness when lights are used (default 0.35)
    scene.motion_blur_samples = 8         # maximum motion-blur sub-frames (quality caps it)
    scene.camera_fov = 700      # perspective strength for 3D meshes (see Part 4)
    scene.camera_x = 0.0        # camera offset for 3D meshes
    scene.camera_y = 0.0

Scene helpers:
    scene.get(name)                  # object by name; raises KeyError if missing
    scene.get_optional(name)         # object or None
    scene.bring_to_front(name)       # draw in front of everything
    scene.send_to_back(name)         # draw behind everything
    scene.measure_text(text, size=64, font="Arial", bold=True, max_width=None)
                                     # returns (width, height) in pixels
    scene.list_fonts()               # font family names available
    scene.define_preset(name, **props)   # save settings (see below)
    scene.apply_preset(name)         # apply saved settings, call in build()

Rules that prevent errors:
- Every object needs a unique name. Duplicate names raise an error.
- Coordinates are pixels with the origin at the top-left. x grows to the right,
  y grows downward.
- In animate(), assign absolute values (for example rotation_z = t * 45). Do not
  add to the old value each frame, because the value would keep growing when you
  scrub the timeline.
- Scripts run the same way in preview and export. Keep animate() a pure function of t.


PART 2. ROTATION, SCALE AND POSITION (EXACT RULES)
--------------------------------------------------
This part is the source of most mistakes. Read it fully.

2D OBJECTS (circle, rect, rounded_rect, ellipse, star, polygon, polyline, line,
text, image)
  Attribute: rotation_z, or the alias rotation (both are the same value).
  Units: DEGREES. rotation_z = 90 turns the object a quarter turn.
  Direction: POSITIVE = CLOCKWISE on screen.
             NEGATIVE = counter-clockwise on screen.
  Pivot: the object's own x, y position. The object spins around its centre.
         Exception: a line pivots around its START point (x, y), and its end
         point is at (x + x2, y + y2).
  Polygons: points are relative to the object's x, y. The pivot is x, y.

  The order applied to a 2D object (exact):
    1. Move to (x, y)
    2. Rotate by rotation_z
    3. Scale by scale × scale_x (horizontal) and scale × scale_y (vertical)
       in the object's rotated axes
    4. Skew horizontally by skew_x (degrees), using the rotated axes
  So a stretched shape stretches along its own tilted edges, not the screen.

  Scale: scale is uniform (1.0 = normal). scale_x and scale_y stretch along the
  object's own axes. Use scale_x = 1.5 for 50% wider, scale_y = 0.5 for half height.

  Skew: skew_x is in DEGREES. Positive moves the TOP edge to the LEFT and the BOTTOM to the
        right (verified from the shear math). Negative slants the top to the right.

3D MESHES (cube, sphere, pyramid, cone, cylinder, torus, plane, OBJ with filled)
  Attributes: rotation_x, rotation_y, rotation_z (DEGREES), and z (depth).
  rotation (alias) = rotation_z.
  The rotations are applied in this order: first X, then Y, then Z.
  Pivot: the mesh's own centre, which is at x, y.

  Exact directions (checked against the app's formulas):
    rotation_x = 90:  the FRONT face (the side toward the viewer) tips DOWN.
                      A point at the front moves DOWN on screen (verified from the rotation math).
    rotation_y = 90:  the FRONT face turns LEFT.
                      A point at the front moves LEFT on screen (verified from the rotation math).
    rotation_z = 90:  the object turns CLOCKWISE on screen, the same as 2D.
  Negative values reverse each direction.

  Depth z: positive z moves the mesh AWAY from the viewer (it gets smaller).
           Negative z moves it toward the viewer (it gets bigger).
  Projection: the perspective uses scene.camera_fov (default 700) as the camera
  distance. A higher value flattens the perspective. Lower values exaggerate it.

  Mesh size: size is the overall width for cube, sphere, torus and plane.
  radius and height set cone and cylinder size. segments (3 to 64) and rings
  (2 to 32) set mesh detail.

PARENTING (child follows parent)
  Set child.parent = "Parent Name" (or the object).
  The child's x, y are RELATIVE to the parent:
    - the child's offset is rotated by the parent's rotation_z
    - the child's offset is scaled by the parent's scale
    - the child's rotation_z is ADDED to the parent's rotation_z
    - the child's opacity is multiplied by the parent's opacity
  Parents can have parents; the chain is limited to 32 levels.

KEYFRAMES (automatic timeline values)
  scene.keyframes(target, prop, [(time, value), ...], ease="ease_in_out")
    target: object or name.   prop: any numeric attribute, e.g. "x", "rotation_z".
    ease: "linear", "ease_in", "ease_out", "ease_in_out", or a function of 0 to 1.
  Keyframes are applied AFTER animate() on every frame, so they override
  animate() for that property.
  Example: scene.keyframes("Ball", "x", [(0, 200), (2, 1600)], ease="ease_out")
  scene.clear_keyframes(target=None, prop=None) removes keyframes.


PART 3. COMMON OBJECTS (scene.add_...)
--------------------------------------
Every 2D object accepts these keyword arguments:
    x, y          position, default 960, 540
    z             depth (3D only), default 0
    color         "#RRGGBB", default "#FFFFFF"
    rotation_z    degrees, clockwise positive (see Part 2)
    rotation      same as rotation_z
    scale         uniform scale, default 1.0
    scale_x, scale_y   stretch, default 1.0
    skew_x        slant in degrees, default 0
    opacity       0 to 1, default 1.0
    stroke        outline width in pixels, default 3
    filled        True fills with color, default False
    blur          blur radius in scene pixels, default 0 (see Part 5)
    backdrop_blur blur of what is behind the object, inside its shape
    motion_blur   0 to 1 shutter, default 0 (see Part 5)
    gradient      effects.Gradient for filled shapes (see Part 6)
    lit           True to be affected by scene.lights (see Part 6)
    parent        object or name to follow (see Part 2)

scene.add_circle(name, radius=100, stroke=6, ...)
scene.add_rect(name, width=200, height=120, ...)
scene.add_rounded_rect(name, width=200, height=120, radius=18, segments=8, ...)
scene.add_ellipse(name, radius_x=100, radius_y=60, segments=48, ...)
scene.add_star(name, points=5, outer_radius=100, inner_radius=45, ...)
scene.add_polygon(name, points=[(x, y), ...], closed=True, ...)
    points are relative to x, y.
scene.add_polyline(name, points=[...], ...)     open shape
scene.add_line(name, x2=100, y2=0, ...)         from (x, y) to (x + x2, y + y2)
scene.add_image(name, path, width=400, height=300, ...)   PNG or JPG
scene.add_text(name, text, size=64, font="Arial", bold=True, align="center",
               max_width=None, ...)
    size is the font height in pixels.
    align: "center" (x is the middle), "left" (x is the left edge),
           "right" (x is the right edge).
    max_width wraps the text to that many pixels.
    Change text during animation: scene.get(name).text = "new words"

Text rotation, scale and skew use the same rules as Part 2.


PART 4. 3D OBJECTS
------------------
scene.add_cube(name, size=180, ...)
scene.add_sphere(name, size=180, rings=10, segments=16, ...)
scene.add_pyramid(name, size=180, ...)
scene.add_cone(name, radius=90, height=180, segments=16, ...)
scene.add_cylinder(name, radius=90, height=180, segments=16, ...)
scene.add_torus(name, size=180, segments=16, rings=10, ...)
scene.add_plane(name, size=180, ...)
scene.add_obj(name, path="model.obj", scale=1.0, filled=True, ...)
    The OBJ file must be in the working folder, or give a full path.
    filled=True draws solid faces. filled=False draws wireframe.
    Faces are shaded with a fixed light from the upper left.


PART 5. EFFECTS ON OBJECTS
--------------------------
blur: a Gaussian blur, in scene pixels. Use 0 for none. Values from about 2 to 20 are common.
backdrop_blur: blurs what is behind the object, inside its shape (frosted glass).
motion_blur: shutter fraction. 0 turns it off. Values near 0.5 to 0.8 are typical.
    It only blurs when the object is visible. Quality caps the sample count.

Blur and quality:
    Large blurs (at or above the quality threshold) use a half-size copy,
    which averages 2×2 blocks so thin text keeps its shape.
    The threshold is listed in Part 8.

IMPORTANT: set blur to exactly 0 when it is not needed.
Values like 0.1 still cost a full blur pass.


PART 6. LIGHTS AND GRADIENTS (effects.py)
-----------------------------------------
Import at the top of the script:  import effects as ex

ex.Gradient(stops, kind="linear", angle=90, center=(0.5, 0.5), radius=0.5)
    stops:  [(position 0 to 1, "#RRGGBB"), ...], at least two stops.
    kind:   "linear" or "radial".
    angle:  linear direction in DEGREES. 0 = left to right, 90 = top to bottom.
    center: radial centre as a fraction of the object's box (0.5, 0.5 = middle).
    radius: radial radius as a fraction of the larger side.
    Use it as obj.gradient = ex.Gradient(...) on a FILLED shape (not text).
    Scene background: scene.background_gradient = ex.Gradient(...)

ex.Light(x, y, radius=600, intensity=1.0, color="#FFFFFF")
    A soft point light in pixels. radius is where it fades to zero.
    Objects only receive light when obj.lit = True.
    scene.lights = [ex.Light(...), ...]
    scene.ambient = 0.35 is the base brightness.

Light cost: every lit object is redrawn in its own layer. Keep lit objects few.


PART 7. TRANSITIONS (transitions.py)
------------------------------------
Import:  import transitions as tr

tr.enter(obj, t, start, duration=0.6, style="fade", base=(x, y), distance=120)
tr.exit(obj,  t, start, duration=0.5, style="fade", base=(x, y), distance=120)

Styles: fade, slide_left, slide_right, slide_up, slide_down, pop, zoom
  - enter: hidden before start, then arrives and rests at base.
  - exit:  rests at base until start, then leaves and is hidden after start + duration.
  - base: the resting position. Pass it every frame so the object returns exactly there.
  - distance: pixels for slides.

Example (call in animate):
    tr.enter(title, t, start=1.0, duration=0.6, style="slide_up", base=(960, 500), distance=60)
    tr.exit(title, t, start=6.0, duration=0.5, style="fade", base=(960, 500))


PART 8. QUALITY (the Quality box)
---------------------------------
Quality changes ONLY the effects below. Every object is always drawn at every level.

Level                 Motion blur max   Blur/frosted glass   Light map    Effects extra sharpness
Low (Barely Seen)     2 sub-frames      half for blur >= 2   1/4          none
Medium (Visible)      4                 half for blur >= 6   1/2          none
Balanced (Normal)     6                 half for blur >= 12  full         none
High (4K Effect)      8                 full resolution      full         drawn at 2x, scaled down

Pixel Art, Isometric, Holographic and Neon Glow (FeaturesPro) also change with
Quality; see Part 9.

Export speed: the Quality box does not change the encoder. Export always uses
the same encoder settings.


PART 9. FEATURESPRO (FeaturesPro.py)
------------------------------------
Import:  import FeaturesPro as pro

Call from build():
    pro.Styled(scene, name, shape, style, text=None, **kw)
    shape:  "circle", "rect", "rounded_rect", "ellipse", "star", "text"
    style:  "neon", "brutal", "paper", "deco", "holo", "blueprint",
            "isometric", "handdrawn", "pixel", "none"
    The style layers are created automatically behind the base object.
    Give the base object normal properties (x, y, width, height, radius, text...).

Quality-controlled styles (number of extra layers at each level):
    Pixel Art:    Low 0 | Medium 1 | Balanced 1 | High 1      (cheapest)
    Isometric:    Low 0 | Medium 1 | Balanced 2 | High 3
    Holographic:  Low 0 | Medium 1 | Balanced 2 | High 4
    Neon Glow:    Low 0 | Medium 1 | Balanced 2 | High 3      (most expensive)
Other styles always draw their full look.

Style notes:
    neon        pink glow with bloom and flicker
    brutal      thick outline, hard shadow, flat colour
    paper       soft drop shadow with a second layer
    deco        gold outline with dark inner line
    holo        gradient that shifts colour with the angle, plus a sweeping highlight
    blueprint   thin outline with an offset line
    isometric   skewed shape with a shadow and side faces
    handdrawn   wobble and jitter, two stroke weights
    pixel       snaps position to an 8-pixel grid, with a shadow, palette colours

Helpers (call from build; update them from animate):
    pro.update_all(scene, t)            ALWAYS call last in animate()
    pro.set_quality(key)                "low", "medium", "balanced", "high" (the app does this)

    pro.iso_box(scene, name, cx, cy, size=160, depth=120, top=, left=, right=)
        A true isometric box with three shaded faces. Returns the face names.
        Static. Rebuild or fade it with opacity to change it over time.

    pro.paper_sheet(scene, name, cx, cy, w, h, color="#FFF8EC", seed=3)
        Cut-paper sheet with irregular edges, soft shadow and grain (grain follows Quality).

    pro.deco_frame(scene, name, cx, cy, width, height, color=, dark=, stroke=4)
        Symmetric Art Deco frame: stepped corners, dark inner line, sunburst (count follows Quality).

    pro.dimension(scene, name, x1, y1, x2, y2, offset=40, label=None)
        Dimension line with ticks and a label. Horizontal or vertical edges only.
        Positive offset is above a horizontal edge and left of a vertical edge.

    pro.grid(scene, name, step=60, color=, width=1, area=(0, 0, 1920, 1080))
        Blueprint grid. Density follows Quality.

    pro.stroke_draw(scene, name, points, t_start, duration, color=, stroke=3, closed=True)
        Outline drawn progressively. Points are absolute screen coordinates.
        Call its update automatically through update_all.

    pro.pixel_sprite(scene, name, bitmap, cx, cy, cell=8, palette=None, shadow=True)
        bitmap: list of text rows. "." is empty, digits 0 to 5 pick palette colours.
    pro.set_pixel_palette("mint" | "retro" | "mono")

    pro.liquid(scene, name, cx, cy, radius, color=, wobble=0.12, speed=1.0)
        Morphing blob outline. Point count follows Quality. This approximates liquid motion.

    pro.kinetic(scene, name, text, cx, cy, size=90, color=, font=, bold=True,
                start=0.0, stagger=0.06, duration=0.5)
        Letters rise and fade in one after another.

    pro.split_flap(scene, name, [(time, text), ...], cx, cy, size=96, color=, font="Consolas")
        Letters flip to each new text at the given times. Texts should be equal length.

    pro.bounce(scene, name, shape, x, drop_y, floor_y, radius=40, start=0.0,
               gravity=2200, restitution=0.6, **shape_kwargs)
        Drops an object and bounces it. radius is how far above the floor it rests.
        Example: shape "rect" with width=140, height=140, radius=70.

    pro.caption(scene, name, text, cx, y, start, end, size=34, color=)
        Text that fades in, holds, and fades out between start and end seconds.

    pro.selftest(scene, duration, fps=30)
        Runs every FeaturesPro object across the whole timeline. Returns None or the first error.


PART 10. AUDIO SCRIPT
---------------------
An audio script defines:
    def build_audio(audio):
        ...

Settings:
    audio.duration = 10.0          # MUST match the video length in seconds
    audio.sample_rate = 44100      # set before add_clip
    audio.master_volume = 0.8      # 0 to 1

Sounds (times are seconds on the video timeline):
    audio.add_tone(name, freq=440, start=0, length=1, volume=0.3,
                   fade_in=0.01, fade_out=0.05, wave="sine", pan=0.0)
        wave: "sine", "square", "triangle", "saw"
        pan: -1 is left, 0 is centre, 1 is right.
    audio.add_noise(name, start=0, length=1, volume=0.1, fade_in=0.01, fade_out=0.05, pan=0)
    audio.add_click(name, at=0, volume=0.3, freq=1800, pan=0)
    audio.add_clip(name, path, at=0, volume=1.0)
        path: WAV, MP3, OGG, M4A, FLAC and others (converted automatically).
        Names are looked up in the assets/ folder, or give a full path.
    audio.add_mood(name, mood="neutral", start=0, length=1, base_freq=220,
                   volume=None, fade_in=None, fade_out=None, pan=0)
        Moods: happy, sad, calm, quiet, soft, loud, excited, tense, neutral.

Rules:
- Each name must be unique.
- Keep the total of overlapping volumes below about 0.9.
- If audio is shorter than the video, the rest of the video is exported with silence.
  If audio is longer, it is trimmed to the video length.

Export and audio: the audio is placed on the same timeline as the video. At Speed
2.0x, both the picture and the sound run twice as fast.


PART 11. TEXT TO VOICE (voice_tts.py)
-------------------------------------
Import:  from voice_tts import add_speech, add_dialogue, list_voices

add_speech(audio, name, text, at=0.0, voice=None, emotion="neutral",
           volume=0.9, rate=0, pitch=0, speed=1.0)
    Returns the clip length in seconds.
add_dialogue(audio, [ {"at": 0.5, "voice": "...", "text": "...", "emotion": "calm"}, ... ])
    Returns the end time of the last line.
list_voices()        Prints the voices available to MotionCode.

Voices:
    "piper:NAME"     Piper voice. Files must be in piper_voices/ (NAME.onnx and NAME.onnx.json).
    "Zira", "David"  Windows voices. Any part of the installed name works.
    None             The default Windows voice.

Emotions: neutral, happy, excited, sad, angry, calm, whisper, question, mystery, robot
Tags in text:  {happy}Hello. [pause 0.5] {calm}Goodbye.
Speed: 1.0 is normal, 1.2 faster, 0.85 slower (Piper). rate and pitch apply to Windows voices (-10 to 10).


PART 12. PROJECTS AND FONTS
---------------------------
Projects: File > Save Project saves video.py and audio.py into one folder.
  The last folder is remembered. Save Project As chooses a new folder.
  Open Project loads both files from a folder.

Fonts: the Fonts button opens a library. Hover, then click an entry to install it.
  Installed fonts go in the fonts/ folder and load on startup.
  Use a family name in text: scene.add_text(..., font="Oswald").
  Font Folder opens the folder. fonts/font_library.json lists the library entries
  (name and a direct .ttf or .otf download link).


PART 13. EXPORT
---------------
Resolution: 2K (2560×1440) is the largest. Others: 1080p, 1K (1024×576), 720p, 480p, 360p.
FPS box: 15 to 120. Set by the script's scene.fps when you apply code.
Speed: 1.0 is real time. 2.0 exports half as long.
Encoder: CPU (libx264) or NVIDIA (h264_nvenc, needs an NVENC GPU).
Formats: MP4, WebM, GIF, PNG frames, WAV audio.
Export draws the same live scene as the preview.


PART 14. CHECKLIST BEFORE APPLYING A SCRIPT
-------------------------------------------
1. Every name is unique.
2. Every rotation is in DEGREES. 2D rotation_z is clockwise-positive.
   3D rotation_x tips the front down, rotation_y turns the front left (see Part 2).
3. Animate sets absolute values (not values added each frame).
4. pro.update_all(scene, t) is the last line of animate() if you use FeaturesPro.
5. Blur is 0 unless you need it.
6. audio.duration equals scene.duration.
7. Use Check script in the File menu before a long export.


PART 15. MOTION HELPERS (motion_fx.py)
--------------------------------------
Import:  import motion_fx as fx

Easing (input k is clamped to 0..1; output goes 0..1, except ease_out_back overshoots):
    fx.ease_out_cubic(k)
    fx.ease_in_out_cubic(k)
    fx.ease_out_back(k, overshoot=1.70158)     overshoots then settles
    fx.ease_out_elastic(k)                     springy wobble that settles
    fx.ease_out_bounce(k)                      bounces at the end

fx.progress(t, start, duration, ease=fx.ease_out_cubic)
    Eased 0..1 between start and start+duration seconds. Returns 0 before start, 1 after.
    Example:  x = 200 + 1400 * fx.progress(t, 1.0, 2.0, ease=fx.ease_out_back)

fx.spring(t, start, freq=2.5, damping=3.5)
    Damped ring: 1 at start, then oscillates and fades to 0.
fx.squash_stretch(t, start, amount=0.25, freq=2.5, damping=3.5)
    Returns (scale_x, scale_y) for a bounce impulse. Assign them to scale_x and scale_y.
    Example:  sx, sy = fx.squash_stretch(t, 2.0, amount=0.3)
              ball.scale_x, ball.scale_y = sx, sy

fx.shake(t, amplitude=10, frequency=14, decay=4, start=0)
    Returns (dx, dy) in pixels, decaying after start. Add them to x and y.
fx.wobble(t, amplitude=6, frequency=1.2, start=0)
    Returns an angle in degrees that sways. Assign it to rotation_z.
fx.flash(t, start, duration=0.25)
    1 at start, falling to 0 over duration. Use it as an opacity.

fx.typed(text, t, start, chars_per_second=18.0)
    The part of text visible at time t. Assign it to scene.get(name).text.
    Example:  obj.text = fx.typed("Hello", t, 1.0, chars_per_second=12)
fx.word_reveal(words, t, start, per_word=0.12)
    Returns a list of (word, opacity) pairs, one word after another.

fx.Burst(prefix, x, y, t0, count=24, speed=320, life=1.0, color="#FFFFFF",
         size=6, gravity=500, seed=1, stroke=2)
    Particles from one point. In build(): burst.build(scene).
    In animate(): burst.update(scene, t).
    Each particle is a circle named "<prefix>_<index>".
fx.Trail(prefix, pos_fn, count=8, delay=0.04, fade=0.8, color=, radius=10, stroke=2)
    Ghost copies that follow pos_fn(t) -> (x, y) with a delay.
    build(scene) in build(), update(scene, t) in animate().

Example (a bouncing ball with squash, particles and a trail):
    import math
    import motion_fx as fx

    BURST = fx.Burst("hit", 960, 800, t0=2.0, count=24, speed=300,
                     life=0.8, color="#FFD166", size=5, gravity=600, seed=3)
    TRAIL = fx.Trail("ghost", lambda tt: (960 + 400 * math.sin(tt), 500),
                     count=8, delay=0.04, fade=0.8, color="#35B9FF", radius=12)

    def build(scene):
        scene.duration = 6
        scene.add_circle("Ball", x=960, y=500, radius=60, color="#FF8A5B", filled=True)
        BURST.build(scene)
        TRAIL.build(scene)

    def animate(scene, t):
        ball = scene.get("Ball")
        ball.x = 960 + 400 * math.sin(t)
        ball.scale_x, ball.scale_y = fx.squash_stretch(t, 2.0, amount=0.25)
        BURST.update(scene, t)
        TRAIL.update(scene, t)


PART 16. KEYFRAMES AND THE TIMELINE
-----------------------------------
scene.keyframes(target, prop, [(time, value), ...], ease="ease_in_out")
    ease: "linear", "ease_in", "ease_out", "ease_in_out" (or a function of 0..1).
    Example:
        scene.keyframes("Ball", "x", [(0, 200), (2, 1600), (4, 200)], ease="ease_out")
        scene.keyframes("Ball", "y", [(0, 300), (1, 700)])
scene.clear_keyframes(target=None, prop=None)
    Removes keyframes for one object, one property, both, or (with no arguments) all.

Keyframes apply after animate(), so they override the same property set in animate().
The timeline shows an orange diamond at every keyframe time.


PART 17. PRESETS
----------------
Presets save a group of scene settings under one name.
Allowed keys: background, background_gradient, lights, ambient, camera_x, camera_y,
camera_z, camera_fov, motion_blur_samples.

    def build(scene):
        scene.define_preset("night", background="#050812", ambient=0.2, camera_fov=700)
        scene.define_preset("day", background="#F4F1EA", ambient=0.9)
        scene.apply_preset("night")          # call inside build()

apply_preset raises an error naming the presets that exist if the name is wrong.


PART 18. TEXT IN DETAIL
-----------------------
Width and height before you place text:
    w, h = scene.measure_text("MOTIONCODE", size=120, font="Arial", bold=True)
    scene.add_text("Title", "MOTIONCODE", x=960 - w / 2, y=540, size=120,
                   align="left", font="Arial")
Wrapped paragraph (max_width in pixels):
    scene.add_text("Body", "Long text that wraps onto several lines inside a fixed width.",
                   x=960, y=700, size=36, max_width=900, align="center", bold=False)
Font families available to scripts:
    print(scene.list_fonts())            # run from build() to see the names
Installed fonts appear in list_fonts() and can be used directly with font="Name".
Text align: "center" uses x as the middle, "left" uses x as the left edge,
"right" uses x as the right edge.


PART 19. PARENTING EXAMPLE
--------------------------
    def build(scene):
        scene.add_circle("Planet", x=960, y=540, radius=120, color="#35B9FF", filled=True)
        scene.add_circle("Moon", x=260, y=0, radius=30, color="#FFD166", filled=True,
                         parent="Planet")       # 260 px to the right of the planet's centre

    def animate(scene, t):
        scene.get("Planet").rotation_z = t * 30     # the moon swings around with it


PART 20. ASSETS (audio and other files)
---------------------------------------
Assets panel (right of the preview):
    Import...  copies any file into assets/ (names are kept, duplicates get _2, _3).
    Double-click an asset to hear it (audio files).
In the audio script:
    audio.add_clip("Sting", "sting.mp3", at=50)     # found in assets/
    audio.add_clip("Sting", "C:/Music/sting.wav", at=50)   # full path also works
Non-WAV formats are converted automatically with the bundled ffmpeg.


PART 21. THE APP (features.py)
------------------------------
Top bar:     Apply Code (video and audio), Fonts (hover to browse), Font Folder.
File menu:   New, Open Project, Save Project, Save Project As, Check script,
             Export > PNG frames / WAV audio / MP4 video.
Editors:     Video script (left), Audio script (middle). Ctrl+Space or two typed
             letters show autocomplete. Failing lines turn red.
Preview:     Play/Pause, time slider with keyframe diamonds, time readout.
             Playback speed is the Speed setting. The preview draws the same scene as export.
Scene objects (left):   drag rows to change layer order. The top of the list is in front.
Object Inspector:       edit x, y, rotation, scale, skew, opacity, blur, motion_blur and others
                        live. These edits are lost when you click Apply Code. To keep a
                        value, write it in the script.
Settings:    Resolution, Quality, FPS, Speed, Encoder (CPU or NVIDIA), Volume (0 to 150%).
Log (bottom left): every error and export message, with times. Red lines are errors.
Autosave:    your scripts are saved every 5 seconds. If the app closes unexpectedly,
             it offers to restore them next time.

Check script (File menu): runs build and animate at start, middle and end, and reports
errors without exporting. Use it before a long export.

Save Project remembers its folder. Save Project saves video.py and audio.py together.


PART 22. EXPORTS IN DETAIL
--------------------------
PNG frames:  choose a folder. Writes frame_00000.png, frame_00001.png, ...
MP4 video:   H.264 (CPU or NVIDIA), with AAC audio when an audio script is applied.
WebM video:  VP9 with Opus audio.
GIF:         no audio; uses a palette for better colours.
WAV audio:   the mixed soundtrack only.

Export settings used:  resolution, FPS, Speed, Quality (effects only), Volume, Encoder.
Export always draws the live scene, the same as the paused preview.
Progress dialog: shows frame count, percent and time left. Cancel stops the export and deletes
the partial file. The window stays usable while exporting.

If a frame fails to draw, the export keeps going and repeats the last good frame. The
log then says how many frames were repeated and the first error.

If the audio ends before the video, the rest of the video is silent. If the audio is longer,
it is trimmed to the video length.

Common export errors:
  ffmpeg stopped reading frames: the audio or video encoder stopped early. Check the
      audio length, and try the CPU encoder.
  AAC "Qavg" lines: normal information, not an error.
  The real error is the line in red, above the ffmpeg output.


PART 23. PITFALLS (wrong vs right)
----------------------------------
Wrong:  animate() adds each frame:    ball.x += 5
Right:  animate() sets an absolute value:  ball.x = 100 + t * 300

Wrong:  rotation in radians:          obj.rotation_z = math.pi / 2
Right:  rotation in degrees:          obj.rotation_z = 90

Wrong:  two objects with one name:    add_circle("Dot") twice
Right:  unique names:                 add_circle("Dot 1") and add_circle("Dot 2")

Wrong:  FeaturesPro without update:   pro.liquid(...) and no pro.update_all in animate()
Right:  call pro.update_all(scene, t) last in animate()

Wrong:  gradient on text:             scene.get("Title").gradient = ex.Gradient(...)
Right:  gradient on a filled shape:   scene.get("Panel").gradient = ex.Gradient(...)

Wrong:  audio shorter than video:     audio.duration = 10, video 60 seconds
Right:  matching lengths:             audio.duration = 60

Wrong:  blur 0.1 "to be safe":        obj.blur = 0.1 still costs a full blur pass
Right:  blur 0 when not needed:       obj.blur = 0

Wrong:  parent pointing to a missing name
Right:  create the parent first, in build(), before any child that uses it.


PART 24. OBJECT DETAIL CARDS (direction, pivot and size for every type)
-----------------------------------------------------------------------
Each card lists what the parameters mean and which way things move.
Screen coordinates: x grows right, y grows DOWN. "Clockwise" means as on a clock face.
All 2D rotation_z values are clockwise for positive numbers.

CIRCLE  add_circle(name, radius=100)
  Pivot: centre (x, y). Size: radius, so the diameter is 2 x radius.
  Rotation: a plain circle looks the same at any angle. Rotation only shows when the circle
            is stretched (scale_x, scale_y), skewed, or has a gradient.

RECT  add_rect(name, width=200, height=120)
  Pivot: centre. Size: width and height are the FULL sizes, not half.
  Rotation: clockwise. scale_x stretches the width, scale_y the height (in the rect's own axes).

ROUNDED RECT  add_rounded_rect(name, width, height, radius=18)
  Pivot: centre. Same size and rotation rules as rect. radius is the corner rounding in pixels,
  limited to half the smaller side.

ELLIPSE  add_ellipse(name, radius_x=100, radius_y=60)
  Pivot: centre. radius_x is the horizontal half-width, radius_y the vertical half-height,
  both before rotation. Rotation is clockwise, so radius_x = 200, radius_y = 60 with
  rotation_z = 90 makes a tall ellipse.

STAR  add_star(name, points=5, outer_radius=100, inner_radius=45)
  Pivot: centre. The first point faces straight UP at rotation 0. Rotation is clockwise.
  points is the number of tips (2 to 64).

POLYGON  add_polygon(name, points=[(x, y), ...], closed=True)
  Pivot: the object's x, y. Each point is relative to x, y, so (0, -100) is 100 px ABOVE
  the pivot (negative y is up). Rotation turns the whole shape clockwise around x, y.

POLYLINE  add_polyline(name, points=[...])
  Same as polygon with an open path: the last point is not joined back to the first.

LINE  add_line(name, x2=100, y2=0)
  Pivot: the START point (x, y). The end is at (x + x2, y + y2). Default x2=100 points RIGHT.
  Rotation swings the end around the start, clockwise. Use it for arrows, rays, and ticks.

TEXT  add_text(name, text, size=64, align="center")
  Pivot: x, y. size is the font height in pixels (the text is drawn with its middle near y).
  align="center": x is the middle of the text. align="left": x is the LEFT edge, so text grows
  right. align="right": x is the RIGHT edge, so text grows left.
  Rotation: clockwise around the pivot.

IMAGE  add_image(name, path, width=400, height=300)
  Pivot: centre. The picture is scaled to fit inside width x height and KEEPS its proportions,
  so a wide photo leaves empty space top and bottom. Rotation is clockwise.

CUBE  add_cube(name, size=180)
  Pivot: centre. size is the full edge length. Default rotation view: the front face is toward you.
  rotation_x = +45 brings the TOP toward you and moves the front face DOWN (see Part 2).

PYRAMID  add_pyramid(name, size=180)
  Pivot: centre. The APEX (tip) points UP at rotation 0. The base is a square at the bottom,
  the base width equals size.

SPHERE  add_sphere(name, size=180, rings=10, segments=16)
  Pivot: centre. size is the diameter. rings are the horizontal latitude lines, segments the
  vertical meridian lines. Rotation_y spins it around the vertical axis.

CONE  add_cone(name, radius=90, height=180, segments=16)
  Pivot: centre. The TIP points UP at rotation 0, the round base is at the bottom.
  radius is the base radius, height the full height.

CYLINDER  add_cylinder(name, radius=90, height=180, segments=16)
  Pivot: centre. Two rings: top and bottom, standing upright at rotation 0.
  radius is the half-width of the rings, height the full height.

TORUS  add_torus(name, size=180, segments=16, rings=10)
  Pivot: centre. Lies FLAT (like a ring on a table) at rotation 0. To stand it up, use
  rotation_x = 90. size sets the overall width.

PLANE  add_plane(name, size=180)
  Pivot: centre. A flat square lying flat at rotation 0, seen edge-on from the side
  it looks like a line. Use rotation_x = 60 to see it as a tilted square.

CUSTOM WIREFRAME  add_wireframe(name, vertices, edges, size=180)
  Pivot: centre. Your vertices are rescaled so the largest coordinate becomes size / 2.
  Rotation works the same as the built-in 3D shapes. Coordinates: (x right, y DOWN, z away from you),
  so (0, -1, 0) is the TOP of the shape.

OBJ MODEL  add_obj(name, path, scale=1.0, filled=True)
  Pivot: the model's origin, not its centre. The model is NOT auto-sized: a large model is
  huge. Use scale=0.01 style values to shrink it. filled=True solid, filled=False wireframe.

SHAPE EFFECTS BY DIRECTION
  blur: spreads the edges evenly in every direction. It has no direction.
  motion_blur: smears along the direction of motion (use with moving objects).
  backdrop_blur: blurs what is behind the object, inside its shape.

FEATURESPRO DIRECTION RULES
  brutal: hard black shadow offset 10 px RIGHT and 10 px DOWN.
  paper: soft shadow offset 12 px right, 16 px down.
  isometric: shadow offset 14 px right and 14 px down; side faces to the left and right.
  pixel: shadow offset 8 px right and 8 px down; positions snap to an 8 px grid.
  holo: colour bands sweep LEFT and RIGHT by up to 160 px.
  handdrawn: small random-looking wobble, about 2 px, in all directions.
  neon: glow only, no offset.
  kinetic: each letter rises from 40 px BELOW its final spot into place.
  caption: fades in while rising from 14 px below to its position.
  bounce: falls straight down from drop_y and lands at floor_y minus radius.
  dimension: the line sits offset ABOVE a horizontal edge and LEFT of a vertical edge.
  stroke_draw: traces the points in the order given. closed=True returns to the first point.
  liquid: a blob whose edge wobbles outward and inward around its centre.

TRANSITIONS: WHICH SIDE THE OBJECT COMES FROM
  slide_left: enters from the LEFT, moving right. exits to the left.
  slide_right: enters from the RIGHT, moving left. exits to the right.
  slide_up: enters from ABOVE, moving DOWN. exits upward.
  slide_down: enters from BELOW, moving UP. exits downward.
  pop: grows from nothing with a small overshoot. zoom: starts large and settles to normal size.

PARENTING: DIRECTION OF THE CHILD OFFSET
  The child's x, y is an offset from the parent's centre. The offset turns with the parent's
  rotation_z (clockwise). Example: parent rotation_z = 90, child x = 100, y = 0 puts the child
  BELOW the parent (the offset turned clockwise to point down).

AUDIO PAN
  pan = -1: full LEFT speaker. pan = 0: centre. pan = +1: full RIGHT speaker.


PART 25. CHARACTER BODY DATA (stick figures and two-bone IK)
------------------------------------------------------------
Use these conventions for any figure. They match example_character_ik.py.

BODY LAYOUT (a figure facing RIGHT)
  Hip: the body's root. Torso goes UP from the hip to the shoulder line.
  Shoulders: at the top of the torso. The head sits above them on the torso.
  Legs: attach at the hip. Feet point RIGHT (forward) and stay horizontal.
  Arms: attach at the shoulders. Hands hang below them.

JOINT BEND DIRECTION (most important rule)
  Knees bend FORWARD (toward the facing direction, right). Knee x is greater than hip x.
  Elbows bend BACKWARD (away from the facing direction, left). Elbow x is less than shoulder x.
  Both come from the same two-bone solver. Legs use flip=False, arms use flip=True.
  Using the same bend for arms and legs makes the elbows point forward, which looks flipped.

TWO-BONE SOLVER (copy this exactly)
  solve_two_bone(sx, sy, tx, ty, l1, l2, flip=False) returns (root_deg, bend_deg).
  root_deg: absolute angle of the upper bone. bend_deg: angle of the lower bone RELATIVE to it.
  Set upper.rotation_z = root_deg, and lower.rotation_z = bend_deg (the child adds to the parent).
  The solver clamps targets to reach, so an out-of-range target never produces a NaN.

BONE CHAIN SETUP
  Upper bone: a line at the root, x2 = length, y2 = 0.
  Lower bone: a line with parent = upper bone, x = upper length, y = 0, x2 = lower length.
  Joint dot: a circle parented to the lower bone at x = lower length.
  Foot: a short line parented to the lower bone. Keep it horizontal by setting
        foot.rotation_z = -(root_deg + bend_deg).
  Set the upper bone's x and y to the root every frame, so the chain follows a moving hip or shoulder.

PROPORTIONS USED IN THE EXAMPLE (pixels)
  Torso 200 (hip to shoulder). Thigh 200, shin 190. Upper arm 150, forearm 140.
  Head radius 42, placed 55 px above the shoulder line.
  Feet: stance phase is 60% of the cycle, swing is 40%.

WALK CYCLE RULES
  One cycle = two steps. The second leg is offset by half a cycle (0.5).
  Stance: foot on the ground, sliding from forward to back at constant speed.
  Swing: foot lifts in an arc (sine) and moves forward with smooth easing.
  Hip dips at each step, so the hip dips twice per cycle.
  Torso sways a few degrees with the cycle. The head is parented to the torso, so it follows.
  Each arm swings OPPOSITE its leg: left arm uses the left leg's phase plus half a cycle.
  Arm swing: each arm swings forward and back, about 40 degrees from straight down.
        Back of the swing: arm nearly straight (reach about 99 percent of arm length, bend about 6 degrees).
        Front of the swing: hand closer to the shoulder (reach about 87 percent), elbow bends about 60 degrees.
        Reach is computed from the swing each frame: reach = arm_length * (1 - 0.13 * (1 + swing) / 2).
        Never let a hand fall close to the shoulder while straight down, or the elbow folds sharply.

VERIFY A FIGURE (run after any change)
  Max reach error should be 0.000 px (targets are reached exactly).
  Lowest ankle y should equal the ground y (feet plant exactly on the ground).
  Foot tilt should be 0 degrees (feet stay horizontal).
  Elbow x should be less than shoulder x. Knee x should be greater than hip x.

---


# Source: Physics-Database.md

# Physics and Simulation Scripts

Source: Motion-Examples: Physics and Simulation, with the scene rules from MotionCode-DataBase (Parts 1, 2 and 3). Each script is self-contained: the solver is inside the file, so nothing else needs to be imported.

Before applying a script, set the video's duration to match the simulation length (`SIM_SECONDS`).

---

## Rigid Collisions

**File:** `example_physics_collisions.py`  
**Length:** 9 seconds

### Physics code

```python
"""PHYSICS: circles fall into a box, collide, stack and spin. Simulated once from t = 0."""
import math

DT = 1.0 / 240.0        # fixed simulation step, seconds
STORE_FPS = 120         # frames kept per second of simulated time


def _sample_frames(frames, t):
    """Interpolate each item in the two frames nearest to time t."""
    if not frames:
        raise RuntimeError("run() must be called before sample()")
    f = min(max(0.0, t * STORE_FPS), len(frames) - 1)
    i = int(f)
    j = min(i + 1, len(frames) - 1)
    k = f - i
    return [tuple(p + (q - p) * k for p, q in zip(u, v))
            for u, v in zip(frames[i], frames[j])]


class RigidCircles:
    """Circles in a rectangular box, with gravity, bounce, friction and spin."""

    def __init__(self, left, top, right, bottom, gravity=1500.0, restitution=0.4,
                 friction=0.6, iterations=10):
        self.box = (float(left), float(top), float(right), float(bottom))
        self.gravity = float(gravity)
        self.restitution = float(restitution)
        self.friction = float(friction)
        self.iterations = int(iterations)
        self.bodies = []      # initial state; stays unchanged after run()
        self.frames = []

    def add(self, x, y, r, vx=0.0, vy=0.0):
        r = float(r)
        m = r * r                       # mass proportional to area
        self.bodies.append({"x": float(x), "y": float(y), "r": r,
                            "vx": float(vx), "vy": float(vy),
                            "w": 0.0,                 # spin, radians per second
                            "m": m, "I": 0.5 * m * r * r, "angle": 0.0})
        return len(self.bodies) - 1

    def run(self, seconds):
        st = [dict(b) for b in self.bodies]     # working copies
        self.frames = []
        steps = int(round(seconds / DT))
        store_every = int(round(1.0 / (DT * STORE_FPS)))
        self._store(st)
        for step in range(1, steps + 1):
            for b in st:
                b["vy"] += self.gravity * DT
                b["x"] += b["vx"] * DT
                b["y"] += b["vy"] * DT
                b["angle"] += math.degrees(b["w"]) * DT
            for _ in range(self.iterations):
                for b in st:
                    self._walls(b)
                for i in range(len(st)):
                    for j in range(i + 1, len(st)):
                        self._pair(st[i], st[j])
            if step % store_every == 0:
                self._store(st)

    def sample(self, t):
        """List of (x, y, angle_degrees), one per body, at time t."""
        return _sample_frames(self.frames, t)

    def _store(self, st):
        self.frames.append([(b["x"], b["y"], b["angle"]) for b in st])

    def _walls(self, b):
        left, top, right, bottom = self.box
        r = b["r"]
        # Each wall: inward normal (nx, ny) and the gap between the circle and the wall
        walls = (
            ((0.0, -1.0), (bottom - b["y"]) - r),   # floor
            ((0.0, 1.0), (b["y"] - top) - r),       # ceiling
            ((1.0, 0.0), (b["x"] - left) - r),      # left wall
            ((-1.0, 0.0), (right - b["x"]) - r),    # right wall
        )
        for (nx, ny), gap in walls:
            if gap >= 0:
                continue
            b["x"] -= gap * nx
            b["y"] -= gap * ny
            vn = b["vx"] * nx + b["vy"] * ny
            if vn >= 0:
                continue
            m, inertia = b["m"], b["I"]
            J = -(1.0 + self.restitution) * vn * m
            b["vx"] += J * nx / m
            b["vy"] += J * ny / m
            # Friction acts at the contact point c = -r * n, so it changes spin
            cx, cy = -r * nx, -r * ny
            tx, ty = -ny, nx
            u = (b["vx"] - b["w"] * cy) * tx + (b["vy"] + b["w"] * cx) * ty
            ct = cx * ty - cy * tx
            kt = 1.0 / m + ct * ct / inertia
            limit = self.friction * J
            P = max(-limit, min(limit, -u / kt))
            b["vx"] += P * tx / m
            b["vy"] += P * ty / m
            b["w"] += ct * P / inertia

    def _pair(self, a, b):
        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
        d = math.hypot(dx, dy)
        reach = a["r"] + b["r"]
        if d >= reach:
            return
        if d < 1e-9:
            dx, dy, d = 1.0, 0.0, 1.0
        nx, ny = dx / d, dy / d                 # normal from a to b
        pen = reach - d
        ma, mb = a["m"], b["m"]
        # Push apart in proportion to mass: the lighter circle moves more
        a["x"] -= nx * pen * mb / (ma + mb)
        a["y"] -= ny * pen * mb / (ma + mb)
        b["x"] += nx * pen * ma / (ma + mb)
        b["y"] += ny * pen * ma / (ma + mb)

        ra, rb = a["r"], b["r"]
        ca = (ra * nx, ra * ny)                 # contact offset from a's centre
        cb = (-rb * nx, -rb * ny)               # contact offset from b's centre
        Ia, Ib = a["I"], b["I"]
        ima, imb = 1.0 / ma, 1.0 / mb

        def rel_velocity():
            ua = (a["vx"] - a["w"] * ca[1], a["vy"] + a["w"] * ca[0])
            ub = (b["vx"] - b["w"] * cb[1], b["vy"] + b["w"] * cb[0])
            return ub[0] - ua[0], ub[1] - ua[1]

        ux, uy = rel_velocity()
        vn = ux * nx + uy * ny
        if vn >= 0:
            return                              # already separating
        J = -(1.0 + self.restitution) * vn / (ima + imb)
        b["vx"] += J * nx * imb
        b["vy"] += J * ny * imb
        a["vx"] -= J * nx * ima
        a["vy"] -= J * ny * ima

        # Friction along the contact tangent
        tx, ty = -ny, nx
        ux, uy = rel_velocity()
        u = ux * tx + uy * ty
        cat = ca[0] * ty - ca[1] * tx
        cbt = cb[0] * ty - cb[1] * tx
        kt = ima + imb + cat * cat / Ia + cbt * cbt / Ib
        limit = self.friction * abs(J)
        P = max(-limit, min(limit, -u / kt))
        b["vx"] += P * tx * imb
        b["vy"] += P * ty * imb
        b["w"] += cbt * P / Ib
        a["vx"] -= P * tx * ima
        a["vy"] -= P * ty * ima
        a["w"] -= cat * P / Ia



WALL = (300, 60, 1620, 1020)          # left, top, right, bottom of the box
SIM_SECONDS = 9
SIM = None
COUNT = 14
COLORS = ["#FF8A5B", "#FFD166", "#70D6FF", "#35B9FF", "#7CFFB2", "#E0457B"]


def build(scene):
    global SIM
    scene.background = "#080D18"
    scene.duration = SIM_SECONDS
    scene.fps = 30
    scene.add_rect("Box", x=960, y=540, width=1320, height=960, color="#1B2A44",
                   filled=False, stroke=4)

    SIM = RigidCircles(*WALL, gravity=1500, restitution=0.4, friction=0.6, iterations=10)
    for i in range(COUNT):
        r = 42 + (i % 3) * 8
        x = 420 + (i * 137) % 1000       # spread the drops across the box
        y = 120 + (i % 4) * 30
        SIM.add(x, y, r)
    SIM.run(SIM_SECONDS)

    for i, body in enumerate(SIM.bodies):
        color = COLORS[i % len(COLORS)]
        scene.add_circle("Ball %02d" % i, x=body["x"], y=body["y"], radius=body["r"],
                         color=color, filled=True, stroke=2)
        # The spoke shows the spin: it turns with the ball
        scene.add_line("Spoke %02d" % i, x=body["x"], y=body["y"],
                       x2=body["r"] * 0.75, y2=0, color="#0B1020", stroke=5)


def animate(scene, t):
    for i, (x, y, angle) in enumerate(SIM.sample(t)):
        ball = scene.get("Ball %02d" % i)
        ball.x, ball.y = x, y
        spoke = scene.get("Spoke %02d" % i)
        spoke.x, spoke.y = x, y
        spoke.rotation_z = angle
```

### What it shows

Fourteen circles of different sizes fall into a box, bounce off the walls and each other, stack, and roll. A spoke on each circle shows its spin.

### How it is made

- Fixed-step simulation in steps of 1/240 second. Each step applies gravity and moves every circle by its velocity.
- Position correction pushes overlapping circles apart along the line between their centres, in proportion to mass. This runs ten times per step.
- Impulse response: when two circles approach, an impulse reverses their normal velocity, scaled by restitution (bounciness).
- Friction at the contact point reduces sliding speed and changes each circle's spin, so rolling is real.
- Walls and floor use the same friction rule, so a ball that lands with forward speed begins to roll.
- Motion is simulated once in build(). Frames are stored at 120 per second, and sample(t) interpolates between them.

### Why it is made this way

- Several correction passes per step keep stacks close to their true height; one pass lets circles sink.
- Friction at the contact point (not the centre) is what produces spin, so a rolling ball's speed matches its spin.
- Simulating once makes scrubbing, playback and export show the same result.

---

## Cloth Simulation

**File:** `example_physics_cloth.py`  
**Length:** 10 seconds

### Physics code

```python
"""PHYSICS: a cloth hangs from a pinned top edge, and the pin sways. Simulated once from t = 0."""
import math
DT = 1.0 / 240.0        # fixed simulation step, seconds
STORE_FPS = 120         # frames kept per second of simulated time


def _sample_frames(frames, t):
    """Interpolate each item in the two frames nearest to time t."""
    if not frames:
        raise RuntimeError("run() must be called before sample()")
    f = min(max(0.0, t * STORE_FPS), len(frames) - 1)
    i = int(f)
    j = min(i + 1, len(frames) - 1)
    k = f - i
    return [tuple(p + (q - p) * k for p, q in zip(u, v))
            for u, v in zip(frames[i], frames[j])]


class Cloth:
    """A grid of points joined by springs, held by a moving pinned top row (Verlet)."""

    def __init__(self, cols, rows, spacing, origin, gravity=1400.0, iterations=14,
                 damping=0.996, pin=None):
        self.cols, self.rows = int(cols), int(rows)
        self.spacing = float(spacing)
        self.origin = (float(origin[0]), float(origin[1]))
        self.gravity = float(gravity)
        self.iterations = int(iterations)
        self.damping = float(damping)
        self.pin = pin                          # pin(t) -> (dx, dy) offset of the top row
        self.home = [(self.origin[0] + c * self.spacing, self.origin[1] + r * self.spacing)
                     for r in range(self.rows) for c in range(self.cols)]
        self.frames = []

    def index(self, c, r):
        return r * self.cols + c

    def run(self, seconds):
        n = len(self.home)
        pinned = [False] * n
        for c in range(self.cols):
            pinned[self.index(c, 0)] = True
        springs = []
        for r in range(self.rows):
            for c in range(self.cols):
                i = self.index(c, r)
                if c + 1 < self.cols:
                    springs.append((i, self.index(c + 1, r)))
                if r + 1 < self.rows:
                    springs.append((i, self.index(c, r + 1)))

        pos = list(self.home)
        old = list(self.home)
        g = self.gravity * DT * DT
        rest = self.spacing
        steps = int(round(seconds / DT))
        store_every = int(round(1.0 / (DT * STORE_FPS)))
        self.frames = [list(pos)]

        for step in range(1, steps + 1):
            t = step * DT
            dx, dy = self.pin(t) if self.pin else (0.0, 0.0)
            for i in range(n):
                if pinned[i]:
                    hx, hy = self.home[i]
                    old[i] = pos[i]
                    pos[i] = (hx + dx, hy + dy)
                    continue
                x, y = pos[i]
                ox, oy = old[i]
                old[i] = (x, y)
                pos[i] = (x + (x - ox) * self.damping,
                          y + (y - oy) * self.damping + g)

            for _ in range(self.iterations):
                for a, b in springs:
                    ax, ay = pos[a]
                    bx, by = pos[b]
                    sx, sy = bx - ax, by - ay
                    d = math.hypot(sx, sy) or 1e-9
                    diff = (d - rest) / d
                    if pinned[a] and pinned[b]:
                        continue
                    if pinned[a]:
                        pos[b] = (bx - sx * diff, by - sy * diff)
                    elif pinned[b]:
                        pos[a] = (ax + sx * diff, ay + sy * diff)
                    else:
                        h = 0.5 * diff
                        pos[a] = (ax + sx * h, ay + sy * h)
                        pos[b] = (bx - sx * h, by - sy * h)

            if step % store_every == 0:
                self.frames.append(list(pos))

    def sample(self, t):
        """List of (x, y), one per point, indexed with index(c, r)."""
        return _sample_frames(self.frames, t)



COLS, ROWS, SPACING = 22, 14, 30
ORIGIN = (560, 180)
SIM_SECONDS = 10
SIM = None


def pin(t):
    """The top edge moves side to side, starting still. Returns (dx, dy) in pixels."""
    return (60 * math.sin(t * 1.6) * min(1.0, t), 0.0)


def build(scene):
    global SIM
    scene.background = "#080D18"
    scene.duration = SIM_SECONDS
    scene.fps = 30
    SIM = Cloth(COLS, ROWS, SPACING, ORIGIN, gravity=1400, iterations=14,
                damping=0.996, pin=pin)
    SIM.run(SIM_SECONDS)

    for r in range(ROWS):
        scene.add_polyline("Row %02d" % r, points=[(0, 0)] * COLS, x=0, y=0,
                           color="#70D6FF", stroke=3)
    for c in range(COLS):
        scene.add_polyline("Col %02d" % c, points=[(0, 0)] * ROWS, x=0, y=0,
                           color="#35B9FF", stroke=3)


def animate(scene, t):
    pts = SIM.sample(t)
    for r in range(ROWS):
        scene.get("Row %02d" % r).points = [pts[SIM.index(c, r)] for c in range(COLS)]
    for c in range(COLS):
        scene.get("Col %02d" % c).points = [pts[SIM.index(c, r)] for r in range(ROWS)]
```

### What it shows

A 22 by 14 grid of points joined by springs hangs from its top edge. The top edge sways side to side and the cloth follows.

### How it is made

- Every point is joined to its right and lower neighbour by a spring. The top row is pinned.
- Verlet integration: each point's new position comes from its previous position, so velocity is implicit. Damping (0.996 per step) stops endless swinging.
- After gravity, every spring is pushed back toward its rest length. This runs 14 times per step.
- The pinned row moves to its home position plus a sine offset, so the cloth starts still and then sways.
- Each row and column is one polyline, so the whole cloth uses 36 objects instead of one per spring.
- Motion is simulated once in build() and sampled by time.

### Why it is made this way

- Verlet with constraints stays stable on stiff springs at this step size.
- Polylines keep the object count low, which keeps the build and preview fast.
- The pin path is part of the stored simulation, so the sway is the same on every playback.

---

## Fluid Particles

**File:** `example_physics_fluid.py`  
**Length:** 8 seconds

### Physics code

```python
"""PHYSICS: a block of particles drops, splashes on the floor and spreads.
Simulated once from t = 0. This is a particle liquid look, not an exact fluid solver."""
import math
import random

DT = 1.0 / 240.0        # fixed simulation step, seconds
STORE_FPS = 120         # frames kept per second of simulated time


def _sample_frames(frames, t):
    """Interpolate each item in the two frames nearest to time t."""
    if not frames:
        raise RuntimeError("run() must be called before sample()")
    f = min(max(0.0, t * STORE_FPS), len(frames) - 1)
    i = int(f)
    j = min(i + 1, len(frames) - 1)
    k = f - i
    return [tuple(p + (q - p) * k for p, q in zip(u, v))
            for u, v in zip(frames[i], frames[j])]


class Fluid:
    """Particles that push apart, fall, splash and bounce in a box.
    This is a liquid look, not an exact fluid solver."""

    def __init__(self, wall, radius=12.0, gravity=1400.0, restitution=0.2):
        self.box = tuple(float(v) for v in wall)     # left, top, right, bottom
        self.radius = float(radius)
        self.gravity = float(gravity)
        self.restitution = float(restitution)
        self.particles = []                          # [x, y, vx, vy]
        self.frames = []

    def add_block(self, x, y, cols, rows, vx=0.0, vy=0.0, spacing=None, jitter=0.0):
        s = spacing if spacing else self.radius * 2.0 * 1.02
        rng = random.Random(7)                  # fixed seed: the same splash every run
        for r in range(rows):
            for c in range(cols):
                jx = rng.uniform(-jitter, jitter)   # each particle gets its own sideways kick
                self.particles.append([x + c * s, y + r * s, float(vx) + jx, float(vy)])

    def run(self, seconds):
        state = [list(p) for p in self.particles]
        self.frames = [[(p[0], p[1]) for p in state]]
        steps = int(round(seconds / DT))
        store_every = int(round(1.0 / (DT * STORE_FPS)))
        for step in range(1, steps + 1):
            for p in state:
                p[3] += self.gravity * DT
                p[0] += p[2] * DT
                p[1] += p[3] * DT
            self._collide(state)
            self._walls(state)
            if step % store_every == 0:
                self.frames.append([(p[0], p[1]) for p in state])

    def sample(self, t):
        """List of (x, y), one per particle, at time t."""
        return _sample_frames(self.frames, t)

    def _collide(self, state):
        d_min = 2.0 * self.radius
        cell = d_min
        grid = {}
        for i, p in enumerate(state):
            grid.setdefault((int(p[0] // cell), int(p[1] // cell)), []).append(i)
        for i, p in enumerate(state):
            cx, cy = int(p[0] // cell), int(p[1] // cell)
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    for j in grid.get((cx + ox, cy + oy), ()):
                        if j <= i:
                            continue
                        q = state[j]
                        dx, dy = q[0] - p[0], q[1] - p[1]
                        d2 = dx * dx + dy * dy
                        if d2 >= d_min * d_min or d2 == 0.0:
                            continue
                        d = math.sqrt(d2)
                        nx, ny = dx / d, dy / d
                        pen = d_min - d
                        p[0] -= nx * pen / 2.0
                        p[1] -= ny * pen / 2.0
                        q[0] += nx * pen / 2.0
                        q[1] += ny * pen / 2.0
                        approach = (q[2] - p[2]) * nx + (q[3] - p[3]) * ny
                        if approach < 0:
                            I = -(1.0 + self.restitution) * approach / 2.0
                            p[2] -= I * nx
                            p[3] -= I * ny
                            q[2] += I * nx
                            q[3] += I * ny

    def _walls(self, state):
        left, top, right, bottom = self.box
        rad = self.radius
        e = self.restitution
        for p in state:
            if p[0] < left + rad:
                p[0] = left + rad
                if p[2] < 0:
                    p[2] = -p[2] * e
            if p[0] > right - rad:
                p[0] = right - rad
                if p[2] > 0:
                    p[2] = -p[2] * e
            if p[1] < top + rad:
                p[1] = top + rad
                if p[3] < 0:
                    p[3] = -p[3] * e
            if p[1] > bottom - rad:
                p[1] = bottom - rad
                if p[3] > 0:
                    p[3] = -p[3] * e



WALL = (200, 60, 1720, 1020)
SIM_SECONDS = 8
RADIUS = 12
SIM = None
COUNT = 0


def build(scene):
    global SIM, COUNT
    scene.background = "#080D18"
    scene.duration = SIM_SECONDS
    scene.fps = 30
    scene.add_rect("Tank", x=960, y=540, width=1520, height=960, color="#1B2A44",
                   filled=False, stroke=4)
    SIM = Fluid(WALL, radius=RADIUS, gravity=1400, restitution=0.35)
    SIM.add_block(330, 150, 14, 9, vx=120, jitter=80)   # block moves right, particles scatter
    SIM.run(SIM_SECONDS)
    COUNT = len(SIM.frames[0])
    for i in range(COUNT):
        x, y = SIM.frames[0][i]
        scene.add_circle("Drop %03d" % i, x=x, y=y, radius=RADIUS, color="#35B9FF", filled=True,
                         stroke=1)


def animate(scene, t):
    for i, (x, y) in enumerate(SIM.sample(t)):
        drop = scene.get("Drop %03d" % i)
        drop.x, drop.y = x, y
```

### What it shows

A block of 126 particles falls into a tank, lands, and splashes outward with a random sideways kick on each particle. It looks like a liquid, but it is a particle approximation, not an exact fluid solver.

### How it is made

- Particles start in a 14 by 9 block with a shared sideways speed of 120 px/s.
- Each particle gets a random extra sideways speed between -80 and +80 px/s, from a fixed seed, so the splash is the same every run.
- Short-range push: particles closer than their diameter are pushed apart and their approaching velocity is reduced.
- Neighbour grid: particles are sorted into cells the size of one diameter, so each one only checks nine cells.
- Walls: particles that reach an edge are pushed back and bounce with restitution 0.35.
- Motion is simulated once in build() and sampled by time.

### Why it is made this way

- The random sideways kick is what makes the block spread. Without it the block slid as one slab, which looked frozen.
- A grid keeps the check fast; checking every pair would take about 16,000 comparisons per step.
- A slightly bouncier floor (0.35) makes the particles lift off as they splash.

---


---


# Source: Character-Interaction.md

# Character Articulation: Interaction Examples

Source: MotionCode-DataBase, Character & Articulation. Two self-contained scripts: paste each into the Video script editor and click Apply Code. No other file is needed.

## Mug Grab and Shock Drop

**File:** `example_mug_drop_shock.py`

### Code

```python
"""MUG GRAB AND SHOCK DROP: a character reaches for a mug on a table, grabs it, and at 2.5 s
it slips out of the hand. The mug slides off the table edge and falls to the floor. The
character jerks back in shock: arms fly up, the torso leans back, the eyes widen and the mouth
opens into an "O". The arm solver is the same two-bone IK used in the full-body script.
The mug's motion is simulated once from t = 0, then sampled."""
import math

DT = 1.0 / 240.0
STORE_FPS = 120
SIM_SECONDS = 6.0
GROUND_Y = 900.0
G = 1500.0                       # gravity, px/s^2

LEG1, LEG2 = 200, 190
TORSO = 200
ARM1, ARM2 = 150, 140
HEAD_OFFSET = 55
FEET_X = (630.0, 730.0)
HIP_X = (FEET_X[0] + FEET_X[1]) / 2.0          # 680
HIP_Y = GROUND_Y - 0.90 * (LEG1 + LEG2)        # 549

TABLE_TOP = 660.0                # top surface of the table
TABLE_X = (735.0, 1085.0)
MUG_R = 25.0
MUG_X = 790.0
MUG_REST_Y = TABLE_TOP - 11 - MUG_R            # mug centre sitting on the table
GRAB_TIME = 1.2                  # hand arrives and closes on the mug
DROP_TIME = 2.2                  # one second after the grab, the mug slips
SLIDE_SPEED = 120.0              # px/s, the push that sends it off the edge

REST_R = (HIP_X + 45, HIP_Y - TORSO + 275)     # right hand resting at the side, arm relaxed
REST_L = (HIP_X - 45, HIP_Y - TORSO + 275)     # left hand resting at the side, arm relaxed
HOLD_R = (MUG_X, MUG_REST_Y)                   # right hand on the mug
HEAD_Y = HIP_Y - TORSO - HEAD_OFFSET           # centre of the head
SHOCK_R = (HIP_X + 30, HEAD_Y - 50)            # right hand on top of the head
SHOCK_L = (HIP_X - 30, HEAD_Y - 50)            # left hand on top of the head
RIGHT_START_FLIP = False                       # resting/reaching right arm: elbow goes out
LEFT_START_FLIP = True                         # resting left arm: elbow goes out
RIGHT_FLIP = True                              # shock pose, right arm: elbow goes out
LEFT_FLIP = False                              # shock pose, left arm: elbow goes out
REACT_TIME = 0.7                               # seconds the reaction takes to build

MUG = None                       # frames of mug (x, y), sampled by time
MUG_FRAMES = []


def _sample_frames(frames, t):
    f = min(max(0.0, t * STORE_FPS), len(frames) - 1)
    i = int(f)
    j = min(i + 1, len(frames) - 1)
    k = f - i
    return [tuple(p + (q - p) * k for p, q in zip(u, v))
            for u, v in zip(frames[i], frames[j])]


def smooth(k):
    k = min(max(k, 0.0), 1.0)
    return k * k * (3 - 2 * k)


def shock(t):
    """Reaction strength: ramps up over REACT_TIME (no jump), peaks, then settles to half."""
    if t < DROP_TIME:
        return 0.0
    dt = t - DROP_TIME
    rise = smooth(dt / 0.3)
    return rise * (0.5 + 0.5 * math.exp(-1.5 * dt))


def right_hand_target(t):
    if t < GRAB_TIME:
        k = smooth(t / GRAB_TIME)
        return (REST_R[0] + (HOLD_R[0] - REST_R[0]) * k, REST_R[1] + (HOLD_R[1] - REST_R[1]) * k)
    if t < DROP_TIME:
        return HOLD_R
    k = smooth((t - DROP_TIME) / REACT_TIME)
    return (HOLD_R[0] + (SHOCK_R[0] - HOLD_R[0]) * k, HOLD_R[1] + (SHOCK_R[1] - HOLD_R[1]) * k)


def left_hand_target(t):
    k = smooth((t - DROP_TIME) / REACT_TIME)
    return (REST_L[0] + (SHOCK_L[0] - REST_L[0]) * k, REST_L[1] + (SHOCK_L[1] - REST_L[1]) * k)


def simulate_mug():
    """The mug follows the hand until the drop, then falls under gravity with a sideways slide.
    It bounces on the table or floor and loses speed each time."""
    x, y, vx, vy = MUG_X, MUG_REST_Y, 0.0, 0.0
    frames = [[(x, y)]]
    steps = int(round(SIM_SECONDS / DT))
    store_every = int(round(1.0 / (DT * STORE_FPS)))
    dropped = False
    for step in range(1, steps + 1):
        t = step * DT
        if t < DROP_TIME:
            x, y = HOLD_R
        else:
            if not dropped:
                vx, vy = SLIDE_SPEED, 0.0
                dropped = True
            vy += G * DT
            x += vx * DT
            y += vy * DT
            on_table = TABLE_X[0] <= x <= TABLE_X[1]
            surface = (TABLE_TOP - 11) if on_table else GROUND_Y
            if y + MUG_R >= surface and vy > 0:
                y = surface - MUG_R
                if vy > 40:                 # a real impact: bounce and lose some speed
                    vy = -vy * 0.3
                    vx *= 0.8
                else:                       # resting on the surface: keep sliding
                    vy = 0.0
        if step % store_every == 0:
            frames.append([(x, y)])
    return frames


def solve_two_bone(sx, sy, tx, ty, l1, l2, flip=False):
    dx, dy = tx - sx, ty - sy
    d = math.hypot(dx, dy)
    d = max(abs(l1 - l2) + 1e-6, min(l1 + l2 - 1e-6, d))
    base = math.atan2(dy, dx)
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    a = math.acos(max(-1.0, min(1.0, cos_a)))
    root = base + a if flip else base - a
    ex = sx + l1 * math.cos(root)
    ey = sy + l1 * math.sin(root)
    child = math.atan2(ty - ey, tx - ex)
    return math.degrees(root), math.degrees(child - root)


def set_chain(scene, prefix, target, root, l1, l2, flip=False, foot_line=False):
    root_deg, bend_deg = solve_two_bone(root[0], root[1], target[0], target[1], l1, l2, flip)
    upper = scene.get(prefix + " upper")
    upper.x, upper.y = root[0], root[1]
    upper.rotation_z = root_deg
    scene.get(prefix + " lower").rotation_z = bend_deg
    if foot_line:
        scene.get(prefix + " foot").rotation_z = -(root_deg + bend_deg)


def make_chain(scene, prefix, root, l1, l2, color, stroke, foot_line=False):
    scene.add_line(prefix + " upper", x=root[0], y=root[1], x2=l1, y2=0, color=color, stroke=stroke)
    scene.add_line(prefix + " lower", x=l1, y=0, x2=l2, y2=0, color=color, stroke=stroke,
                   parent=prefix + " upper")
    if foot_line:
        scene.add_line(prefix + " foot", x=l2, y=0, x2=40, y2=0, color=color, stroke=stroke,
                       parent=prefix + " lower")


def wrap(deg):
    """Shortest signed angle difference, in degrees."""
    return (deg + 180.0) % 360.0 - 180.0


def build(scene):
    global MUG_FRAMES
    MUG_FRAMES = simulate_mug()
    scene.background = "#080D18"
    scene.duration = SIM_SECONDS
    scene.fps = 30
    # Table: a top with two legs
    scene.add_rect("Table top", x=(TABLE_X[0] + TABLE_X[1]) / 2, y=TABLE_TOP,
                   width=TABLE_X[1] - TABLE_X[0], height=22, color="#8A5A3B", filled=True, stroke=0)
    scene.add_line("Table leg L", x=TABLE_X[0] + 25, y=TABLE_TOP + 11, x2=0, y2=GROUND_Y - TABLE_TOP - 11,
                   color="#6B4429", stroke=10)
    scene.add_line("Table leg R", x=TABLE_X[1] - 25, y=TABLE_TOP + 11, x2=0, y2=GROUND_Y - TABLE_TOP - 11,
                   color="#6B4429", stroke=10)
    scene.add_line("Floor", x=100, y=GROUND_Y, x2=1800, y2=0, color="#1B2A44", stroke=3)
    scene.add_circle("Mug", x=MUG_X, y=MUG_REST_Y, radius=MUG_R, color="#FFD166", filled=True, stroke=0)
    # Figure: torso leans from the hip, the head and mouth are children of the torso
    make_chain(scene, "Left leg", (HIP_X, HIP_Y), LEG1, LEG2, "#70D6FF", 12, foot_line=True)
    make_chain(scene, "Right leg", (HIP_X, HIP_Y), LEG1, LEG2, "#35B9FF", 12, foot_line=True)
    make_chain(scene, "Left arm", (HIP_X, HIP_Y - TORSO), ARM1, ARM2, "#FFD166", 10)
    make_chain(scene, "Right arm", (HIP_X, HIP_Y - TORSO), ARM1, ARM2, "#FFB454", 10)
    scene.add_line("Torso", x=HIP_X, y=HIP_Y, x2=0, y2=-TORSO, color="#FFFFFF", stroke=14)
    scene.add_circle("Head", x=0, y=-TORSO - HEAD_OFFSET, radius=42, color="#FFFFFF", stroke=8,
                     parent="Torso")
    scene.add_circle("Eye", x=-16, y=-6, radius=6, color="#1B2A44", filled=True, stroke=0, parent="Head")
    scene.add_circle("Mouth", x=0, y=18, radius=4, color="#8A2B3B", filled=True, stroke=0, parent="Head")
    scene.add_text("Shock", "!", x=-5000, y=-5000, size=90, color="#FF6B6B")
    scene.add_text("Status", "", x=960, y=980, size=30, color="#9FB4FF")


def animate(scene, t):
    s = shock(t)
    torso = scene.get("Torso")
    torso.rotation_z = -8.0 * s                  # lean back, away from the table
    scene.get("Head").rotation_z = -4.0 * s
    scene.get("Eye").radius = 6 + 4 * s
    scene.get("Mouth").radius = 4 + 10 * s       # "O" mouth on shock

    rt = right_hand_target(t)
    lt = left_hand_target(t)
    shoulder = (HIP_X, HIP_Y - TORSO)
    f = smooth((t - DROP_TIME) / REACT_TIME) if t > DROP_TIME else 0.0
    arms = (("Right arm", rt, RIGHT_START_FLIP, RIGHT_FLIP, HOLD_R, SHOCK_R),
            ("Left arm", lt, LEFT_START_FLIP, LEFT_FLIP, REST_L, SHOCK_L))
    for prefix, hand, start_flip, flip, start, final in arms:
        if t <= DROP_TIME:
            root, bend = solve_two_bone(shoulder[0], shoulder[1], hand[0], hand[1], ARM1, ARM2, start_flip)
        else:
            # Sweep from the start pose to the shock pose, each solved with its own elbow side
            r0, b0 = solve_two_bone(shoulder[0], shoulder[1], start[0], start[1], ARM1, ARM2, start_flip)
            r1, b1 = solve_two_bone(shoulder[0], shoulder[1], final[0], final[1], ARM1, ARM2, flip)
            c0, c1 = r0 + b0, r1 + b1
            root = r0 + wrap(r1 - r0) * f
            child = c0 + wrap(c1 - c0) * f
            bend = wrap(child - root)
        up = scene.get(prefix + " upper")
        up.x, up.y = shoulder
        up.rotation_z = root
        scene.get(prefix + " lower").rotation_z = bend

    lx, ly = FEET_X[0], GROUND_Y
    rx, ry = FEET_X[1], GROUND_Y
    for prefix, foot in (("Left leg", (lx, ly)), ("Right leg", (rx, ry))):
        set_chain(scene, prefix, foot, (HIP_X, HIP_Y), LEG1, LEG2, foot_line=True)

    mx, my = _sample_frames(MUG_FRAMES, t)[0]
    mug = scene.get("Mug")
    mug.x, mug.y = mx, my

    shock_text = scene.get("Shock")
    if s > 0.4:
        shock_text.x, shock_text.y = HIP_X + 40, HIP_Y - TORSO - 200
    else:
        shock_text.x, shock_text.y = -5000, -5000
    scene.get("Status").text = "mug at %.0f, %.0f   shock %.2f" % (mx, my, s)
```

### What it shows

A character reaches for a mug on a table, grabs it, and one second later the mug slips out of the hand. It slides off the table edge and falls to the floor. The character reacts over about 0.7 s, like the reference pose: both hands go to the top of the head, the elbows flare wide out to the sides, the torso leans back, the eyes widen, the mouth opens into an "O", and a "!" appears and fades.

### How it is made

The arms start relaxed at the sides, with the hands about 280 px from the shoulders so each elbow has a slight natural bend. The right hand reaches to the mug, then holds it. After the drop, the arm changes from its reach pose to its shock pose over 0.7 s with a smoothstep. The upper arm angle and the forearm's absolute angle are both interpolated between the two valid IK poses, so the elbow swings outward and up, not under the arm, and the forearm keeps its full length. The shock pose puts both hands on top of the head with the elbows about 150 px out from the shoulders at shoulder height. The reaction strength rises over 0.3 s, peaks and settles to half, driving the torso lean, eye and mouth size. The mug is simulated once: it follows the hand until the drop, then falls under gravity (1500 px/s^2) with a sideways slide of 120 px/s, and bounces on the table or floor.

### Why it is made this way

Interpolating the hand position and re-solving each frame let the elbow swing under the arm, because the solver picked the long way round. Interpolating the two joint angles keeps the elbow on its outward path. Each frame is a real arm of full length, the worst change is about 19 degrees per frame, and the pose lands exactly on the shock target.

## Punch and Physical Fall

**File:** `example_punch_fall.py`

### Code

```python
"""PUNCH AND PHYSICAL FALL: an attacker holds a fighting guard, throws a punch at 1.4 s, and the
defender is knocked over. The defender is a rigid body that pivots about its feet: the punch
gives it an angular kick, and gravity pulls it over until it hits the floor and bounces once.
Its arm is a damped spring that goes limp on the hit. Simulated once from t = 0."""
import math

DT = 1.0 / 240.0
STORE_FPS = 120
SIM_SECONDS = 4.0
GROUND_Y = 900.0
G = 1500.0

LEG = 351.0                     # defender's straight leg length (0.9 of the figure's leg pair)
TORSO = 200.0
ARM1, ARM2 = 150.0, 140.0
HEAD_OFFSET = 55.0

# Attacker: a standing figure on the left, hip height as in the IK script
A_FEET = (630.0, 730.0)
A_HIP = ((A_FEET[0] + A_FEET[1]) / 2.0, GROUND_Y - 0.9 * (200 + 190))
A_SHOULDER = (A_HIP[0], A_HIP[1] - TORSO)
DEF_X = 1000.0                 # defender's pivot (feet) x; the head is directly above it
TP = 1.4                       # the moment the punch lands
PUNCH_WINDUP = 0.25
PUNCH_RECOVER = 0.6
CONTACT_CHEST_LOCAL = LEG + 120.0          # distance up from the pivot to the chest, local
HIT_OMEGA = 2.0                # rad/s angular kick from the punch
PHI_GUARD = -150.0             # defender's guard arm, degrees relative to torso
PHI_HANG = 0.0                 # hanging, limp arm, degrees relative to torso
ARM_K, ARM_C, ARM_KICK = 40.0, 3.0, 4.0

FALL = None


def smooth(k):
    k = min(max(k, 0.0), 1.0)
    return k * k * (3 - 2 * k)


def _sample_frames(frames, t):
    f = min(max(0.0, t * STORE_FPS), len(frames) - 1)
    i = int(f)
    j = min(i + 1, len(frames) - 1)
    k = f - i
    return [tuple(p + (q - p) * k for p, q in zip(u, v))
            for u, v in zip(frames[i], frames[j])]


FIST_Y = 300.0                 # the punch lands at the defender's head height
GUARD_REACH = math.sqrt(ARM1 ** 2 + ARM2 ** 2)   # 205 px: a fully folded 90 degree elbow
ARM_REACH = ARM1 + ARM2                          # 290 px: a fully straight arm


def guard_point(angle_deg):
    """A fist position for a bent 90 degree arm, at the given angle from the shoulder."""
    a = math.radians(angle_deg)
    return (A_SHOULDER[0] + GUARD_REACH * math.cos(a), A_SHOULDER[1] + GUARD_REACH * math.sin(a))


GUARD_LEAD = guard_point(-10)   # lead fist, out in front of the chest
GUARD_REAR = guard_point(-25)   # rear fist, close by the chin; elbows drop down like the lead
PUNCH_TARGET = (A_SHOULDER[0] + math.sqrt(ARM_REACH ** 2 - (FIST_Y - A_SHOULDER[1]) ** 2), FIST_Y)


def punch_target(t):
    """Lead fist: guard, then straightens to PUNCH_TARGET over the windup, retracts after the hit."""
    if t < TP - PUNCH_WINDUP:
        return GUARD_LEAD, 0.0
    if t < TP:
        k = smooth((t - (TP - PUNCH_WINDUP)) / PUNCH_WINDUP)
    else:
        k = 1.0 - smooth((t - TP) / PUNCH_RECOVER)
    return (GUARD_LEAD[0] + (PUNCH_TARGET[0] - GUARD_LEAD[0]) * k,
            GUARD_LEAD[1] + (PUNCH_TARGET[1] - GUARD_LEAD[1]) * k), k


def simulate_defender():
    """Rigid body pivoted at the feet (theta, clockwise degrees) plus a damped arm (phi)."""
    k_fall = 1.5 * G / (LEG + TORSO)       # rod pivoted at one end: theta'' = (3g/2L) sin theta
    th, om = 0.0, 0.0
    ph, dph = PHI_GUARD, 0.0
    hit = False
    frames = []
    steps = int(round(SIM_SECONDS / DT))
    store_every = int(round(1.0 / (DT * STORE_FPS)))
    for step in range(1, steps + 1):
        t = step * DT
        if t >= TP and not hit:
            hit = True
            om = HIT_OMEGA
            dph += ARM_KICK
        if hit:
            om += k_fall * math.sin(th) * DT
            th += om * DT
            if th >= math.pi / 2:              # the body reaches the floor
                th = math.pi / 2
                if om > 0:
                    om = -0.2 * om              # one small bounce, then it settles
        rest = PHI_HANG if hit else PHI_GUARD
        ddph = -ARM_K * (ph - rest) - ARM_C * dph
        dph += ddph * DT
        ph += dph * DT
        if step % store_every == 0:
            frames.append([(math.degrees(th), ph)])
    return frames


def solve_two_bone(sx, sy, tx, ty, l1, l2, flip=False):
    dx, dy = tx - sx, ty - sy
    d = math.hypot(dx, dy)
    d = max(abs(l1 - l2) + 1e-6, min(l1 + l2 - 1e-6, d))
    base = math.atan2(dy, dx)
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    a = math.acos(max(-1.0, min(1.0, cos_a)))
    root = base + a if flip else base - a
    ex = sx + l1 * math.cos(root)
    ey = sy + l1 * math.sin(root)
    child = math.atan2(ty - ey, tx - ex)
    return math.degrees(root), math.degrees(child - root)


def make_chain(scene, prefix, root, l1, l2, color, stroke, foot_line=False):
    scene.add_line(prefix + " upper", x=root[0], y=root[1], x2=l1, y2=0, color=color, stroke=stroke)
    scene.add_line(prefix + " lower", x=l1, y=0, x2=l2, y2=0, color=color, stroke=stroke,
                   parent=prefix + " upper")
    if foot_line:
        scene.add_line(prefix + " foot", x=l2, y=0, x2=40, y2=0, color=color, stroke=stroke,
                       parent=prefix + " lower")


def set_chain(scene, prefix, target, root, l1, l2, flip=False, foot_line=False):
    root_deg, bend_deg = solve_two_bone(root[0], root[1], target[0], target[1], l1, l2, flip)
    upper = scene.get(prefix + " upper")
    upper.x, upper.y = root[0], root[1]
    upper.rotation_z = root_deg
    scene.get(prefix + " lower").rotation_z = bend_deg
    if foot_line:
        scene.get(prefix + " foot").rotation_z = -(root_deg + bend_deg)


def build(scene):
    global FALL
    FALL = simulate_defender()
    scene.background = "#080D18"
    scene.duration = SIM_SECONDS
    scene.fps = 30
    scene.add_line("Floor", x=100, y=GROUND_Y, x2=1800, y2=0, color="#1B2A44", stroke=3)
    # Attacker: legs with planted feet, two arms by IK
    make_chain(scene, "A Left leg", (A_HIP[0], A_HIP[1]), 200, 190, "#70D6FF", 12, foot_line=True)
    make_chain(scene, "A Right leg", (A_HIP[0], A_HIP[1]), 200, 190, "#35B9FF", 12, foot_line=True)
    scene.add_line("A Torso", x=A_HIP[0], y=A_HIP[1], x2=0, y2=-TORSO, color="#FFFFFF", stroke=14)
    scene.add_circle("A Head", x=0, y=-TORSO - HEAD_OFFSET, radius=42, color="#FFFFFF", stroke=8,
                     parent="A Torso")
    make_chain(scene, "A Guard arm", A_SHOULDER, ARM1, ARM2, "#FFD166", 10)
    make_chain(scene, "A Punch arm", A_SHOULDER, ARM1, ARM2, "#FFB454", 10)
    # Defender: one rigid body pivoted at the feet, with a child torso, head and arm
    scene.add_line("D Body", x=DEF_X, y=GROUND_Y, x2=0, y2=-LEG, color="#FF8A5B", stroke=16)
    scene.add_line("D Torso", x=0, y=-LEG, x2=0, y2=-TORSO, color="#FF8A5B", stroke=14, parent="D Body")
    scene.add_circle("D Head", x=0, y=-TORSO - HEAD_OFFSET, radius=42, color="#FFD166", stroke=8,
                     parent="D Torso")
    scene.add_line("D Arm", x=0, y=-TORSO, x2=0, y2=150, color="#FFD166", stroke=10, parent="D Torso")
    scene.add_text("Status", "", x=960, y=980, size=30, color="#9FB4FF")


def animate(scene, t):
    # Rear arm: held at a 90 degree bend by the chin
    rd, rb = solve_two_bone(A_SHOULDER[0], A_SHOULDER[1], GUARD_REAR[0], GUARD_REAR[1], ARM1, ARM2, flip=True)
    scene.get("A Guard arm upper").x, scene.get("A Guard arm upper").y = A_SHOULDER
    scene.get("A Guard arm upper").rotation_z = rd
    scene.get("A Guard arm lower").rotation_z = rb

    # Lead arm: 90 degree guard, then the punch straightens it at the fist height
    target, p = punch_target(t)
    pd, pb = solve_two_bone(A_SHOULDER[0], A_SHOULDER[1], target[0], target[1], ARM1, ARM2, flip=True)
    scene.get("A Punch arm upper").x, scene.get("A Punch arm upper").y = A_SHOULDER
    scene.get("A Punch arm upper").rotation_z = pd
    scene.get("A Punch arm lower").rotation_z = pb

    for prefix, foot in (("A Left leg", (A_FEET[0], GROUND_Y)), ("A Right leg", (A_FEET[1], GROUND_Y))):
        set_chain(scene, prefix, foot, A_HIP, 200, 190, foot_line=True)

    # Defender: the rigid body and limp arm come from the simulation
    theta, phi = _sample_frames(FALL, t)[0]
    scene.get("D Body").rotation_z = theta
    scene.get("D Arm").rotation_z = phi
    scene.get("Status").text = "fall %.0f deg   punch extension %.2f" % (theta, p)
```

### What it shows

An attacker stands in a fighting guard with both arms bent at 90 degrees, both elbows pointing down, and throws a straight punch at 1.4 s. The lead arm straightens at the height of the defender's head. The defender is knocked over: it tips backwards about its feet, hits the floor and bounces once. Its arm swings limp after the hit.

### How it is made

Both guard arms are IK chains with their fists placed 205 px from the shoulder, which is the length at which a 150 px upper arm and a 140 px forearm meet at exactly 90 degrees. Both use the elbow-down solution, so the arms match. The lead fist is at -10 degrees and the rear fist at -25 degrees, close by the chin. The punch moves the lead fist to a point 290 px from the shoulder at the defender's head height, so the arm is fully straight at contact, then retracts. The attacker's torso stays still, so the arms stay attached to it. The defender is one rigid body pivoted at its feet. At the hit, its angular velocity is set to 2 rad/s, and gravity acts as theta'' = (3g / 2L) sin(theta), the equation for a rod pivoted at one end. It stops at 90 degrees, bounces to 20% of its speed, and settles. Its arm is a damped spring (stiffness 40, damping 3) that goes from the guard angle to a hanging angle, with a small kick on impact.

### Why it is made this way

A 90 degree guard and a fully straight punch are the two shapes a fight reads by, so the fist distances come from the arm lengths rather than guesses. Forcing both guard arms to the same elbow-down solution stops one arm looking different from the other. Leaving the torso still keeps the arms joined to the body. A rigid rod pivoted at the feet, with real gravity, gives the fall physical weight, and the limp arm is a damped spring that settles like loose limbs. The legs do not bend: a rigid fall from the feet is simpler and reads well for a short clip, but it does not show a body folding at the hips or knees.



---


# Source: Motion-Database.md

# Motion-Examples

Three working MotionCode examples, one per motion family. Each one is a complete video script: paste it into the Video script editor and click Apply Code. Each section explains how the motion is made, why it is built that way, and the rules to keep when developing more motion in the same family.

---

## 1. Path Motion: `example_path_motion.py`

### What it shows

- Letters travelling around a circular ring, each letter turning to follow the ring.
- A ball moving along a curved path at a constant speed, with a heading line that always points forward.

### How it is made

1. **Curve as a Bezier.** The curve is a cubic Bezier defined by four control points. `bezier(p, u)` returns the position for a fraction `u` from 0 to 1.
2. **Arc-length table.** At start-up, the curve is sampled 400 times and the distance between samples is summed. This gives `TABLE`, which maps a fraction along the curve to a distance in pixels.
3. **Distance to position.** `point_at_distance(s)` finds the piece of the table that contains distance `s`, then interpolates to the matching point on the curve. It wraps with `%`, so the ball loops forever.
4. **Letters on a ring.** `build()` measures every letter width with `scene.measure_text`. `animate()` places each letter at its cumulative position around the ring: `x = CX + R·sin(angle)`, `y = CY − R·cos(angle)`.
5. **Letters turn with the ring.** `rotation_z` is set to the same angle in degrees, so each letter's baseline follows the tangent.
6. **Heading.** The heading line is aimed at a point 2 px further along the curve, which gives the travel direction.

### Why it is built this way

- **Constant speed needs distance, not time.** A Bezier curve’s parameter `u` does not move at a steady speed along the curve. Without the arc-length table, the ball would speed up and slow down.
- **Measured widths keep the spacing even.** Letters are spaced by their real widths, so narrow letters such as `I` do not leave the same gap as wide ones such as `M`.
- **Modulo gives a seamless loop.** Using `%` on the distance means the marquee and the ball never run out of path.

### Rules to remember

- Measure widths in `build()` and store them. Do not measure every frame.
- Set every position in `animate()` from `t`, as an absolute value. Never add to the previous frame.
- Rotation is in degrees and clockwise-positive. A letter at the top of the ring has rotation 0, and one at the right has 90.
- Keep the arc-length table. Any new path that must move at a steady speed needs one.
- Guide shapes are added with `x=0, y=0` when their points are absolute screen coordinates.

### Script

```python
"""PATH MOTION: letters marching around a ring, and a ball moving at constant speed along a curve."""
import math

# ---- settings you can change
CX, CY, RING_R = 960, 540, 330      # ring centre and radius (pixels)
TEXT = "MOTIONCODE PATHS  "
TEXT_SIZE = 56
RING_SPEED = 140                    # pixels per second around the ring
BALL_SPEED = 380                    # pixels per second along the curve
CURVE = [(160, 900), (500, 150), (1400, 1000), (1780, 200)]   # cubic Bezier control points

WIDTHS = []                         # letter widths, measured in build()


def bezier(p, u):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = p
    m = 1.0 - u
    x = m**3 * x0 + 3 * m * m * u * x1 + 3 * m * u * u * x2 + u**3 * x3
    y = m**3 * y0 + 3 * m * m * u * y1 + 3 * m * u * u * y2 + u**3 * y3
    return x, y


# Arc-length table: lets the ball move at constant speed along the curve.
SAMPLES = 400
TABLE = [(0.0, 0.0)]
_prev, _total = bezier(CURVE, 0.0), 0.0
for _i in range(1, SAMPLES + 1):
    _p = bezier(CURVE, _i / SAMPLES)
    _total += math.dist(_prev, _p)
    _prev = _p
    TABLE.append((_i / SAMPLES, _total))
CURVE_LENGTH = _total


def point_at_distance(s):
    """Position on the curve after travelling s pixels. Wraps around at the end."""
    s = s % CURVE_LENGTH
    for (u0, s0), (u1, s1) in zip(TABLE, TABLE[1:]):
        if s0 <= s <= s1:
            k = 0.0 if s1 == s0 else (s - s0) / (s1 - s0)
            return bezier(CURVE, u0 + (u1 - u0) * k)
    return bezier(CURVE, 1.0)


def build(scene):
    scene.background = "#080D18"
    scene.duration = 10
    scene.fps = 30

    # Faint guides: the ring and the curve
    scene.add_circle("Ring guide", x=CX, y=CY, radius=RING_R, color="#1B2A44", filled=False, stroke=2)
    guide = [bezier(CURVE, i / 60) for i in range(61)]
    scene.add_polyline("Curve guide", points=guide, x=0, y=0, color="#1B2A44", stroke=2)

    # One text object per letter. animate() places each letter on the ring.
    WIDTHS.clear()
    for i, ch in enumerate(TEXT):
        w, _h = scene.measure_text(ch if ch.strip() else " ", size=TEXT_SIZE, font="Arial", bold=True)
        WIDTHS.append(w)
        scene.add_text("Letter %02d" % i, ch, x=CX, y=CY, size=TEXT_SIZE, color="#FFD166", align="center")

    # The ball and a heading line that always points where the ball is going
    start = CURVE[0]
    scene.add_circle("Curve ball", x=start[0], y=start[1], radius=20, color="#FF8A5B", filled=True)
    scene.add_line("Heading", x=start[0], y=start[1], x2=70, y2=0, color="#FF8A5B", stroke=4)


def animate(scene, t):
    # Letters: each one moves around the ring. Rotation 0 at the top, clockwise positive.
    circumference = 2 * math.pi * RING_R
    offset = 0.0
    for i, w in enumerate(WIDTHS):
        s = (offset + w / 2 + t * RING_SPEED) % circumference
        angle = s / RING_R                          # radians from the top, clockwise
        letter = scene.get("Letter %02d" % i)
        letter.x = CX + RING_R * math.sin(angle)
        letter.y = CY - RING_R * math.cos(angle)
        letter.rotation_z = math.degrees(angle)     # the letter turns with the ring
        offset += w

    # Ball: constant speed along the curve, heading taken from a point just ahead
    bx, by = point_at_distance(t * BALL_SPEED)
    ax, ay = point_at_distance(t * BALL_SPEED + 2.0)
    heading = math.degrees(math.atan2(ay - by, ax - bx))
    ball = scene.get("Curve ball")
    ball.x, ball.y = bx, by
    line = scene.get("Heading")
    line.x, line.y = bx, by
    line.rotation_z = heading
```

---

## 2. Layout Motion: `example_layout_motion.py`

### What it shows

- A flow diagram that builds itself: boxes slide in one after another.
- Arrows that grow from the start box to the end box, with arrowheads that appear once the arrow is complete.
- A token that travels the route from box to box, then loops.

### How it is made

1. **Nodes as data.** `NODES` holds each box's centre and label. `EDGES` holds the connections. `ROUTE` holds the order the token travels.
2. **Edge points on box sides.** `edge_points(a, b)` decides whether the connection is mostly sideways or mostly vertical, then starts and ends the arrow on the matching box edge.
3. **Arrow as a line.** The arrow is a line whose start point is the edge point and whose `rotation_z` is the direction angle. Its length is set with `x2`, so the line grows along its own direction.
4. **Arrowhead.** Two short lines start at the arrow tip, each 28 degrees either side of the direction pointing back along the arrow.
5. **Build-in with the transitions module.** `tr.enter(..., style="slide_up")` makes each box arrive from above. Boxes and labels share the same `base`, so they stay together.
6. **Arrows grow after both ends are visible.** `tr.progress` gives 0 to 1 over the grow time, and `x2` is set to the full length times that fraction.
7. **Token on the route.** The route is split into hops. The token's time picks a hop, and it is placed by linear interpolation along that hop's edge points.

### Why it is built this way

- **Data first, drawing second.** Keeping the nodes and edges in a table means you change the layout in one place, and the arrows, heads and token all follow.
- **Arrows grow from their start.** Growing `x2` keeps the start point fixed, so the arrow appears to be drawn from its source.
- **Heads appear last.** Showing the arrowhead only when the arrow is complete avoids a head floating in mid-air.
- **Shared base points.** Passing the same `base` to a box and its label stops them drifting apart during the slide.

### Rules to remember

- Every `EDGES` pair and every `ROUTE` name must exist in `NODES`. Check spelling first.
- Box size is in `BOX_W` and `BOX_H`. Keep nodes far enough apart that arrows are longer than the arrowhead (16 px).
- Use `edge_points` for every new arrow so the start and end sit on box edges.
- Animate arrows with `x2` growth, not by re-creating them.
- Keep `ROUTE_START` after the build finishes, so the token does not appear before its boxes exist.

### Script

```python
"""LAYOUT MOTION: a flow diagram builds itself, arrows grow between boxes, and a token travels the route."""
import math
import transitions as tr

BOX_W, BOX_H = 260, 110
NODES = {                                   # name: (centre x, centre y, label)
    "Input":   (320, 540, "Input"),
    "Process": (760, 360, "Process"),
    "Check":   (760, 720, "Check"),
    "Output":  (1200, 540, "Output"),
    "Done":    (1640, 540, "Done"),
}
EDGES = [("Input", "Process"), ("Input", "Check"), ("Process", "Output"),
         ("Check", "Output"), ("Output", "Done")]
ROUTE = ["Input", "Process", "Output", "Done"]    # the token follows these hops
BUILD_STEP = 0.35          # seconds between boxes appearing
ARROW_GROW = 0.5           # seconds for an arrow to grow
ROUTE_START = 3.5          # seconds before the token starts moving
ROUTE_SECONDS = 6.0        # one full trip along the route

ARROW_LEN = {}             # filled in build()


def edge_points(a, b):
    """Start and end points on the box edges for a hop from box a to box b."""
    ax, ay, _ = NODES[a]
    bx, by, _ = NODES[b]
    dx, dy = bx - ax, by - ay
    if abs(dx) * BOX_H >= abs(dy) * BOX_W:          # mostly sideways: leave by the side
        sx = ax + math.copysign(BOX_W / 2, dx)
        ex = bx - math.copysign(BOX_W / 2, dx)
        sy, ey = ay, by
    else:                                           # mostly up or down: leave by top or bottom
        sy = ay + math.copysign(BOX_H / 2, dy)
        ey = by - math.copysign(BOX_H / 2, dy)
        sx, ex = ax, bx
    return sx, sy, ex, ey


def head_name(a, b, side):
    return "Head %s to %s %d" % (a, b, side)


def build(scene):
    scene.background = "#080D18"
    scene.duration = 10
    scene.fps = 30
    ARROW_LEN.clear()

    for name, (x, y, label) in NODES.items():
        scene.add_rect("Box " + name, x=x, y=y, width=BOX_W, height=BOX_H,
                       color="#70D6FF", stroke=4, filled=False)
        scene.add_text("Label " + name, label, x=x, y=y, size=40, color="#FFFFFF")

    for a, b in EDGES:
        sx, sy, ex, ey = edge_points(a, b)
        length = math.hypot(ex - sx, ey - sy)
        angle = math.degrees(math.atan2(ey - sy, ex - sx))
        ARROW_LEN[(a, b)] = length
        # The arrow body starts at (sx, sy) and points along its rotation
        scene.add_line("Arrow %s to %s" % (a, b), x=sx, y=sy, x2=length, y2=0,
                       rotation_z=angle, color="#FFD166", stroke=4)
        # Two arrowhead lines at the tip, 28 degrees either side of the back direction
        for side in (-1, 1):
            head = math.radians(angle + 180 + side * 28)
            scene.add_line(head_name(a, b, side), x=ex, y=ey,
                           x2=16 * math.cos(head), y2=16 * math.sin(head),
                           color="#FFD166", stroke=4)

    scene.add_circle("Token", x=0, y=0, radius=14, color="#FF8A5B", filled=True)


def animate(scene, t):
    order = list(NODES)

    # Boxes appear one after another
    for i, name in enumerate(order):
        x, y, _label = NODES[name]
        start = 0.3 + i * BUILD_STEP
        tr.enter(scene.get("Box " + name), t, start, duration=0.6,
                 style="slide_up", base=(x, y), distance=50)
        tr.enter(scene.get("Label " + name), t, start, duration=0.6,
                 style="slide_up", base=(x, y), distance=50)

    # Arrows grow once both boxes they join are in place
    for a, b in EDGES:
        start = 0.3 + max(order.index(a), order.index(b)) * BUILD_STEP + 0.4
        k = tr.progress(t, start, ARROW_GROW)
        arrow = scene.get("Arrow %s to %s" % (a, b))
        arrow.x2 = ARROW_LEN[(a, b)] * k
        for side in (-1, 1):
            scene.get(head_name(a, b, side)).opacity = 1.0 if k >= 1.0 else 0.0

    # Token travels along the route, hop by hop, then loops
    hops = list(zip(ROUTE, ROUTE[1:]))
    token = scene.get("Token")
    if t < ROUTE_START:
        token.opacity = 0.0
        return
    token.opacity = 1.0
    progress = ((t - ROUTE_START) % ROUTE_SECONDS) / ROUTE_SECONDS * len(hops)
    i = min(int(progress), len(hops) - 1)
    k = progress - i
    sx, sy, ex, ey = edge_points(*hops[i])
    token.x = sx + (ex - sx) * k
    token.y = sy + (ey - sy) * k
```

---

## 3. Character Motion: `example_character_ik.py`

### What it shows

- A stick figure that walks in place with weight, timing and balance.
- Legs and arms that bend naturally: knees bend forward, elbows bend backward.
- Feet that plant on the ground, slide during stance, lift in an arc during swing, and stay level.
- Arms that swing opposite the legs, straight at the back and bent at the front.

### How it is made

1. **Two-bone inverse kinematics.** `solve_two_bone` takes a root point and a target point and returns two angles. The law of cosines gives the bend at the joint. `flip=False` bends joints forward (knees), and `flip=True` bends them backward (elbows).
2. **Bone chains.** Each limb is an upper line at the root, a lower line parented to it, and a joint dot parented to the lower line. Legs also get a foot line.
3. **Parenting does the rest.** The lower bone is placed at the upper bone's length along the x axis. Because the child's offset turns with the parent, the lower bone lands at the elbow or knee automatically.
4. **Keep the root moving.** Each frame, `set_chain` writes the root x and y, so a bobbing hip or moving shoulder drags its limb with it.
5. **Walk cycle.** One cycle runs from 0 to 1. Each foot follows `foot_target`: a stance phase (60% of the cycle) where it slides on the ground, and a swing phase (40%) where it lifts in a sine arc and moves forward with easing.
6. **Body motion.** The hip dips twice per cycle, and the torso sways a few degrees. The head is parented to the torso, so it follows the sway.
7. **Arms.** Each arm’s target sits on an arc. At the back of its swing the hand is almost at full arm length, and at the front it is about 13% closer, so the elbow bends.
8. **Feet stay level.** The foot line's rotation is set to `-(root + bend)`, which cancels the shin angle.
9. **Self-check.** The status line shows the largest reach error across all limbs, so a broken solve is visible at once.

### Why it is built this way

- **Two-bone IK is exact and cheap.** It reaches a target every frame with no iteration, which is why the reach error is 0.000 px.
- **Flip is what makes arms look natural.** Knees and elbows bend in opposite directions. Using the knee direction for elbows is the most common error, and it looks as though the arms are folded backward.
- **Stance and swing match real walking.** A foot that slides on the ground while the body moves over it looks planted. A foot that lifts in an arc looks like a step.
- **Reach depends on the swing.** Keeping the arm straight at the back and bent at the front gives the bend when it looks natural. A fixed length either folds too sharply or looks stiff.
- **Parenting avoids duplicate maths.** The lower bone and foot need no separate position calculation.

### Rules to remember

- Legs use `flip=False`. Arms use `flip=True`. Do not swap them.
- Set the root x and y in `set_chain` every frame, not only at build time.
- Keep the hand reach between about 85% and 100% of the arm length. Closer than that folds the elbow.
- Keep each foot's target within reach: hip to ground distance must be less than `LEG1 + LEG2`, and horizontal swing must stay within `STEP`.
- Arms swing opposite their leg. The left arm uses the left leg's phase plus half a cycle, and the right arm uses the right leg's phase plus half a cycle.
- Check the four numbers after any change: reach error 0.000 px, lowest ankle equal to the ground, foot tilt 0 degrees, and elbows behind the shoulder.

### Script

```python
"""CHARACTER MOTION: a stick figure walks in place with natural weight and timing.
Legs and arms use two-bone inverse kinematics (IK): each hand and foot reaches a target,
and the bones bend to get there."""
import math

# ---- settings you can change
HIP_X, HIP_Y = 960, 540      # resting hip position
TORSO = 200                  # hip to shoulder line
LEG1, LEG2 = 200, 190        # thigh and shin
ARM1, ARM2 = 150, 140        # upper arm and forearm
GROUND_Y = 900               # where the feet touch the ground
STEP = 85                    # foot reach forward and back from the hip
LIFT = 55                    # how high a foot lifts during its swing
STANCE = 0.6                 # share of each cycle a foot stays on the ground (0.5 to 0.7)
CYCLES_PER_SECOND = 0.9      # one full walk cycle is two steps
BOB = 10                     # how far the hip dips at each step (pixels)
LEAN = 3.0                   # torso sway in degrees
ARM_SWING_DEG = 40           # how far each arm swings forward and back, in degrees from straight down
ARM_FWD_SHORTEN = 0.13       # arm is this fraction shorter at the front of the swing (elbow bends there)


def smooth(k):
    """Ease in and out, 0 to 1."""
    return k * k * (3 - 2 * k)


def solve_two_bone(sx, sy, tx, ty, l1, l2, flip=False):
    """Angles that reach (tx, ty) from the root (sx, sy) with two bones.
    Returns (root_degrees, bend_degrees). The bend is the child's angle relative to the root.
    flip=False bends the joint forward (knees, facing right). flip=True bends it backward
    (elbows). Degrees, clockwise positive, as in MotionCode."""
    dx, dy = tx - sx, ty - sy
    d = math.hypot(dx, dy)
    d = max(abs(l1 - l2) + 1e-6, min(l1 + l2 - 1e-6, d))    # stay in reach
    base = math.atan2(dy, dx)
    cos_a = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)
    a = math.acos(max(-1.0, min(1.0, cos_a)))
    root = base + a if flip else base - a
    ex = sx + l1 * math.cos(root)
    ey = sy + l1 * math.sin(root)
    child = math.atan2(ty - ey, tx - ex)
    return math.degrees(root), math.degrees(child - root)


def reach_error(root, l1, l2, root_deg, bend_deg, target):
    """Distance between where the chain ends up and where it was asked to go."""
    r = math.radians(root_deg)
    c = math.radians(root_deg + bend_deg)
    fx = root[0] + l1 * math.cos(r) + l2 * math.cos(c)
    fy = root[1] + l1 * math.sin(r) + l2 * math.sin(c)
    return math.hypot(fx - target[0], fy - target[1])


def foot_target(u, offset):
    """Foot position for cycle fraction u (0 to 1). Stance: the foot slides on the ground.
    Swing: the foot lifts in an arc and moves forward to plant again."""
    v = (u + offset) % 1.0
    if v < STANCE:
        k = v / STANCE
        return HIP_X + STEP * (1 - 2 * k), GROUND_Y
    k = (v - STANCE) / (1 - STANCE)
    return HIP_X - STEP + 2 * STEP * smooth(k), GROUND_Y - LIFT * math.sin(math.pi * k)


def make_chain(scene, prefix, root, l1, l2, color, stroke, foot=False):
    scene.add_line(prefix + " upper", x=root[0], y=root[1], x2=l1, y2=0,
                   color=color, stroke=stroke)
    scene.add_line(prefix + " lower", x=l1, y=0, x2=l2, y2=0,
                   color=color, stroke=stroke, parent=prefix + " upper")
    scene.add_circle(prefix + " joint", x=l2, y=0, radius=stroke * 1.4,
                     color=color, filled=True, parent=prefix + " lower")
    if foot:
        # The foot is a short line that is kept horizontal, pointing forward
        scene.add_line(prefix + " foot", x=l2, y=0, x2=40, y2=0,
                       color=color, stroke=stroke, parent=prefix + " lower")


def set_chain(scene, prefix, target, root, l1, l2, foot=False, flip=False):
    root_deg, bend_deg = solve_two_bone(root[0], root[1], target[0], target[1], l1, l2, flip)
    upper = scene.get(prefix + " upper")
    upper.x, upper.y = root[0], root[1]
    upper.rotation_z = root_deg
    scene.get(prefix + " lower").rotation_z = bend_deg     # the child adds to its parent
    if foot:
        # Cancel the shin's angle so the foot stays horizontal
        scene.get(prefix + " foot").rotation_z = -(root_deg + bend_deg)
    return root_deg, bend_deg


def build(scene):
    scene.background = "#080D18"
    scene.duration = 8
    scene.fps = 30
    scene.add_line("Ground", x=200, y=GROUND_Y, x2=1520, y2=0, color="#1B2A44", stroke=3)
    scene.add_line("Torso", x=HIP_X, y=HIP_Y, x2=0, y2=-TORSO, color="#FFFFFF", stroke=14)
    scene.add_circle("Head", x=0, y=-TORSO - 55, radius=42, color="#FFFFFF", stroke=8,
                     parent="Torso")
    make_chain(scene, "Left leg", (HIP_X, HIP_Y), LEG1, LEG2, "#70D6FF", 12, foot=True)
    make_chain(scene, "Right leg", (HIP_X, HIP_Y), LEG1, LEG2, "#35B9FF", 12, foot=True)
    make_chain(scene, "Left arm", (HIP_X, HIP_Y - TORSO), ARM1, ARM2, "#FFD166", 10)
    make_chain(scene, "Right arm", (HIP_X, HIP_Y - TORSO), ARM1, ARM2, "#FFB454", 10)
    scene.add_text("Status", "", x=960, y=980, size=30, color="#9FB4FF")


def animate(scene, t):
    u = (t * CYCLES_PER_SECOND) % 1.0

    # Body: the hip dips twice per cycle (once per step), and the torso sways
    hip_y = HIP_Y + BOB * (1 - math.cos(4 * math.pi * u)) / 2
    hip = (HIP_X, hip_y)
    sway = LEAN * math.sin(2 * math.pi * u)
    torso = scene.get("Torso")
    torso.x, torso.y = hip
    torso.rotation_z = sway
    rad = math.radians(sway)
    shoulder = (hip[0] + TORSO * math.sin(rad), hip[1] - TORSO * math.cos(rad))

    errors = []

    # Legs: each foot plants, slides, lifts and swings
    for prefix, offset in (("Left leg", 0.0), ("Right leg", 0.5)):
        target = foot_target(u, offset)
        rd, bd = set_chain(scene, prefix, target, hip, LEG1, LEG2, foot=True)
        errors.append(reach_error(hip, LEG1, LEG2, rd, bd, target))

    # Arms: swing opposite to the legs. Back of the swing = straight arm,
    # front of the swing = hand closer to the shoulder, so the elbow bends.
    for prefix, p in (("Left arm", 2 * math.pi * u + math.pi), ("Right arm", 2 * math.pi * u)):
        swing = math.cos(p)                                   # +1 forward, -1 back
        angle = math.radians(ARM_SWING_DEG * swing)           # from straight down, forward positive
        reach = (ARM1 + ARM2) * (1.0 - ARM_FWD_SHORTEN * (1 + swing) / 2)
        target = (shoulder[0] + reach * math.sin(angle),
                  shoulder[1] + reach * math.cos(angle))
        rd, bd = set_chain(scene, prefix, target, shoulder, ARM1, ARM2, flip=True)
        errors.append(reach_error(shoulder, ARM1, ARM2, rd, bd, target))

    scene.get("Status").text = "max reach error %.2f px" % max(errors)
```

---

## Rules for the whole family

- **Absolute values only.** Set every position and rotation in `animate()` from `t`. Adding to last frame's value makes the motion drift when scrubbing.
- **Degrees, clockwise-positive.** Rotation works the same way for every object type.
- **Build once, animate many times.** Measure text, create objects and store lookups in `build()`. Only change values in `animate()`.
- **Verify the numbers, not just the look.** Each example prints or computes something you can check (reach error, arc length, token position).
- **Use the database.** Part 2 (rotation rules), Part 24 (object detail cards) and Part 25 (character body data) describe the conventions these examples follow.

---


# Source: MotionCode-Transitions-and-Kinetic-Typography.md

# MotionCode: Transitions and Kinetic Typography

Two standalone MotionCode scripts. Each runs on its own: paste it into the Video script editor and click Apply Code. Neither needs the other or any extra file.

| Script | File | Length | What it demonstrates |
|---|---|---|---|
| Transitions showcase | `transitions_showcase.py` | 40 s | Nine plate-based transitions: wipes, shape morphs, fragmentation, a wavy edge, layered bars, and a rotation exit |
| Kinetic typography | `kinetic_typography.py` | 40 s | Five 8-second sections: characters, words, lines, transformations, and alignment |

**Status.** Both scripts were tested with a mock scene that records every call and runs every frame. They compile, produce no non-finite values, and pass the checks listed under each part. They have **not** been run inside MotionCode, and no frame has been rendered or inspected. Check the points under "Not yet verified in MotionCode" before relying on either script.

**Limits of the reference.** The MotionCode reference documents no masks, blend modes, or distortion of rendered images. The transitions therefore work by moving solid plates and polygon outlines. Text is handled one object per letter or word, because no per-character object is documented.

---

## Part 1: Transitions showcase

**File:** `transitions_showcase.py`

### What it shows

Ten full-frame colour plates are stacked in a sequence. Each transition moves one plate away to reveal the plate beneath it, or grows a new plate over the current one. The nine transitions run in order, and each has its own technique:

| Slot | Time (s) | Technique |
|---|---|---|
| 0 | 2.0 to 6.0 | Horizontal exit, with anticipation |
| 1 | 6.0 to 10.0 | Vertical exit |
| 2 | 10.0 to 14.0 | Diagonal exit with rotation |
| 3 | 14.0 to 18.0 | Contracting outline: the plate morphs to a small disc |
| 4 | 18.0 to 22.0 | Expanding outline: a star morphs into a full plate |
| 5 | 22.0 to 26.0 | Fragmentation: the plate splits into six strips |
| 6 | 26.0 to 30.0 | Directional distortion: a wavy edge sweeps across |
| 7 | 30.0 to 34.0 | Layered bars: three bars leave at staggered times, one with reduced opacity |
| 8 | 34.0 to 38.0 | Rotation and scale exit |

### Code

```python
"""TRANSITIONS SHOWCASE. Standalone. 40 seconds, 1920 x 1080, 30 fps.

Ten full-frame colour plates. Each transition either slides the current plate away
to reveal the plate beneath it, or grows a new plate over the current one.

Techniques, one per transition:
    0  horizontal exit, with anticipation (ease_in_back pulls back before moving)
    1  vertical exit
    2  diagonal exit with rotation
    3  contracting shape: the plate's outline morphs to a small disc
    4  expanding shape: a small star outline morphs into a full plate
    5  fragmentation: the plate splits into six strips that move apart
    6  directional distortion: a wavy edge sweeps across the plate
    7  layered bars: three bars leave at staggered times, one with reduced opacity
    8  rotation and scale exit

What this file cannot do, because MotionCode's reference documents no API for it:
    - True masks. Reveals are done by moving plates and shapes, not by clipping.
    - Blend modes. Layers draw normally; no blend mode is set.
    - Distortion of a rendered image. Distortion here changes the outlines of plates.
    - Circular masks. The contracting shape is a morphed outline, not a circular mask.
Each transition uses the scene's own geometry, so it works without any other file.
"""
import math
from bisect import bisect_right

CONTROL = {
    "start": 2.0,        # seconds before the first transition
    "section": 4.0,      # seconds per transition slot
    "lead": 0.3,         # pause before each transition moves
    "move": 3.0,         # seconds each transition's motion takes
    "wave_amp": 60.0,    # px amplitude of the wavy edge in transition 6
    "shards": 6,         # strips in transition 5
}

W, H = 1920, 1080
CX, CY = 960.0, 540.0
DURATION = 40.0
BG = "#0B0F1A"

PLATE_COLOURS = ["#FF6B4A", "#70D6FF", "#F5C451", "#8BE28B", "#B38CFF",
                 "#FF8FC7", "#5AD1C4", "#E0457B", "#3A4A6B", "#F5F1E8"]
PLATES = ["Plate %d" % i for i in range(10)]
OFF = -6000.0


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def prog(t, start, dur):
    return clamp((t - start) / dur)


def ease_in_out(p):
    p = clamp(p)
    return 4 * p * p * p if p < 0.5 else 1 - ((-2 * p + 2) ** 3) / 2.0


def ease_in_back(p, s=1.70158):
    p = clamp(p)
    return (s + 1) * p ** 3 - s * p ** 2


def rect_pts(w, h):
    return [(-w / 2.0, -h / 2.0), (w / 2.0, -h / 2.0), (w / 2.0, h / 2.0), (-w / 2.0, h / 2.0)]


def circle_pts(radius, n):
    return [(radius * math.cos(math.radians(-90 + 360.0 * k / n)),
             radius * math.sin(math.radians(-90 + 360.0 * k / n))) for k in range(n)]


def star_pts(tips, outer, inner):
    pts = []
    for k in range(2 * tips):
        r = outer if k % 2 == 0 else inner
        a = math.radians(-90 + 180.0 * k / tips)
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def resample(points, n):
    """n points spaced evenly by arc length on a closed outline."""
    m = len(points)
    seg, cum = [], [0.0]
    for i in range(m):
        L = math.dist(points[i], points[(i + 1) % m])
        seg.append(L)
        cum.append(cum[-1] + L)
    total = cum[-1]
    out = []
    for k in range(n):
        d = total * k / float(n)
        j = min(max(bisect_right(cum, d) - 1, 0), m - 1)
        f = 0.0 if seg[j] <= 0 else (d - cum[j]) / seg[j]
        a, b = points[j], points[(j + 1) % m]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


def align_closed(ref, pts):
    """Start point and direction that keep each point closest to its partner."""
    n = len(ref)
    best = None
    for cand in (list(pts), list(reversed(pts))):
        for s in range(n):
            sh = cand[s:] + cand[:s]
            c = sum((ax - bx) ** 2 + (ay - by) ** 2 for (ax, ay), (bx, by) in zip(ref, sh))
            if best is None or c < best[0]:
                best = (c, sh)
    return best[1]


def morph(a, b, p):
    return [(ax + (bx - ax) * p, ay + (by - ay) * p) for (ax, ay), (bx, by) in zip(a, b)]


RECT4 = rect_pts(W, H)
RECT96 = resample(RECT4, 96)
SMALL96 = align_closed(RECT96, resample(circle_pts(2.0, 96), 96))
STAR96 = align_closed(RECT96, resample(star_pts(5, 60, 26), 96))

STRIP_W = W / float(CONTROL["shards"])
STRIPS = ["Strip %d" % i for i in range(CONTROL["shards"])]
BARS = ["Bar %d" % i for i in range(3)]
ALL_NAMES = PLATES + STRIPS + BARS

LABELS = [
    "0  Horizontal exit with anticipation",
    "1  Vertical exit",
    "2  Diagonal exit with rotation",
    "3  Contracting shape reveal",
    "4  Expanding shape reveal",
    "5  Fragmentation into strips",
    "6  Directional wave wipe",
    "7  Layered bars with opacity",
    "8  Rotation and scale exit",
]


def place(scene, name, x, y, points=None, rot=0.0, scale=1.0, opacity=1.0):
    o = scene.get(name)
    o.x, o.y = x, y
    o.rotation_z = rot
    o.scale = scale
    o.opacity = opacity
    if points is not None:
        o.points = points


def wave_points(p):
    """Outline of a plate whose left edge is wavy and sweeps from left to right."""
    n = 40
    amp = CONTROL["wave_amp"]
    pts = []
    for j in range(n + 1):
        y = -H / 2.0 + H * j / float(n)
        edge = -0.2 * W + 1.5 * W * p + amp * math.sin(2 * math.pi * 2 * j / n + 6 * p)
        pts.append((edge - CX, y))
    pts.append((W / 2.0 + 200.0, H / 2.0))
    pts.append((W / 2.0 + 200.0, -H / 2.0))
    return pts


def sec0(scene, tl):
    e = ease_in_back(prog(tl, 0.0, CONTROL["move"]))
    place(scene, "Plate 1", CX, CY, points=RECT4)
    place(scene, "Plate 0", CX + W * e, CY, points=RECT4)
    return "Plate 1", ["Plate 0"]


def sec1(scene, tl):
    e = ease_in_out(prog(tl, 0.0, CONTROL["move"]))
    place(scene, "Plate 2", CX, CY, points=RECT4)
    place(scene, "Plate 1", CX, CY - H * e, points=RECT4)
    return "Plate 2", ["Plate 1"]


def sec2(scene, tl):
    e = ease_in_out(prog(tl, 0.0, CONTROL["move"]))
    place(scene, "Plate 3", CX, CY, points=RECT4)
    place(scene, "Plate 2", CX + 0.9 * W * e, CY - 0.9 * H * e, rot=30.0 * e, points=RECT4)
    return "Plate 3", ["Plate 2"]


def sec3(scene, tl):
    e = ease_in_out(prog(tl, 0.0, CONTROL["move"]))
    place(scene, "Plate 4", CX, CY, points=RECT4)
    place(scene, "Plate 3", CX, CY, points=morph(RECT96, SMALL96, e))
    return "Plate 4", ["Plate 3"]


def sec4(scene, tl):
    e = ease_in_out(prog(tl, 0.0, CONTROL["move"]))
    place(scene, "Plate 4", CX, CY, points=RECT4)
    place(scene, "Plate 5", CX, CY, points=morph(STAR96, RECT96, e))
    return "Plate 4", ["Plate 5"]


def sec5(scene, tl):
    e = ease_in_out(prog(tl, 0.0, CONTROL["move"]))
    place(scene, "Plate 6", CX, CY, points=RECT4)
    strip_pts = rect_pts(STRIP_W, H)
    for i, name in enumerate(STRIPS):
        sx = CX - W / 2.0 + STRIP_W / 2.0 + i * STRIP_W
        direction = -1.0 if i % 2 == 0 else 1.0
        place(scene, name, sx, CY + direction * H * e, points=strip_pts)
    return "Plate 6", list(STRIPS)


def sec6(scene, tl):
    e = prog(tl, 0.0, CONTROL["move"])
    e = ease_in_out(e)
    place(scene, "Plate 7", CX, CY, points=RECT4)
    place(scene, "Plate 6", CX, CY, points=wave_points(e))
    return "Plate 7", ["Plate 6"]


def sec7(scene, tl):
    place(scene, "Plate 8", CX, CY, points=RECT4)
    bar_pts = rect_pts(W / 3.0, H)
    for i, name in enumerate(BARS):
        delay = i * 0.25
        e = ease_in_out(prog(tl, delay, CONTROL["move"] - delay))
        direction = -1.0 if i % 2 == 0 else 1.0
        opacity = 1.0 - 0.35 * math.sin(math.pi * e) if i == 1 else 1.0
        place(scene, name, W / 6.0 + i * W / 3.0, CY + direction * H * e,
              points=bar_pts, opacity=opacity)
    return "Plate 8", list(BARS)


def sec8(scene, tl):
    e = ease_in_out(prog(tl, 0.0, CONTROL["move"]))
    place(scene, "Plate 9", CX, CY, points=RECT4)
    place(scene, "Plate 8", CX, CY, points=RECT4, rot=90.0 * e, scale=max(0.001, 1.0 - e))
    return "Plate 9", ["Plate 8"]


SECTIONS = [sec0, sec1, sec2, sec3, sec4, sec5, sec6, sec7, sec8]


def build(scene):
    scene.width, scene.height = W, H
    scene.fps = 30
    scene.duration = DURATION
    scene.background = BG
    for i, name in enumerate(PLATES):
        scene.add_polygon(name, points=RECT4, x=CX, y=CY, color=PLATE_COLOURS[i],
                          filled=True, stroke=0)
    for i, name in enumerate(STRIPS):
        scene.add_polygon(name, points=rect_pts(STRIP_W, H), x=OFF, y=OFF,
                          color=PLATE_COLOURS[5], filled=True, stroke=0)
    for i, name in enumerate(BARS):
        scene.add_polygon(name, points=rect_pts(W / 3.0, H), x=OFF, y=OFF,
                          color=PLATE_COLOURS[7], filled=True, stroke=0)
    scene.add_text("Label", "", x=960, y=1040, size=30, color="#F5F1E8", align="center")


def animate(scene, t):
    rel = t - CONTROL["start"]
    if rel < 0:
        k = -1
    else:
        k = min(int(rel // CONTROL["section"]), len(SECTIONS) - 1)

    if k < 0:
        place(scene, "Plate 0", CX, CY, points=RECT4)
        under, moving = "Plate 0", []
        label = ""
    else:
        tl = rel - k * CONTROL["section"] - CONTROL["lead"]
        under, moving = SECTIONS[k](scene, tl)
        label = LABELS[k]
    scene.get("Label").text = label

    active = [under] + moving
    for name in ALL_NAMES:
        if name not in active:
            o = scene.get(name)
            o.x, o.y = OFF, OFF
    # Draw order: the revealed plate first, the moving pieces on top.
    for name in active:
        scene.bring_to_front(name)
```

### Part by part

#### 1. The header docstring

**What it is.** The text at the top: a summary of the nine techniques, and a list of what the reference cannot do.

**Why it's needed.** Anyone who copies this script needs to know which effects are real and which are emulated. The reference documents no masks, so every "reveal" here is a moved plate. The header says so.

**How it works.** It is only a docstring. Python ignores it at run time.

#### 2. `CONTROL`: the timing dictionary

**What it contains.** `start` (2.0 s before the first transition), `section` (4.0 s per transition slot), `lead` (0.3 s pause before each motion), `move` (3.0 s motion length), `wave_amp` (60 px wave height), and `shards` (6 strips).

**Why it's needed.** Every transition reads its timing from here. Changing one number changes the whole show consistently. The 0.3 s lead gives the viewer a moment to see the still frame before it moves. The 4 s slot is the 3 s motion plus that lead and a 0.7 s hold.

**How it works.** `animate()` computes the slot from `t` with `(t - start) // section`, then local time within the slot as `t - slot_start - lead`. A negative local time means the motion has not started, and the progress helper returns 0.

**Rules.**
- Keep `move` shorter than `section - lead`, or a transition runs into the next slot.
- Keep `wave_amp` below about 120 px. A larger wave makes the edge fold back on itself.

#### 3. `PLATE_COLOURS`, `PLATES`, and `OFF`

**What it contains.** Ten hex colours, the names `Plate 0` to `Plate 9`, and `OFF = -6000.0`.

**Why it's needed.** Each plate needs a unique name, because MotionCode raises an error on duplicates. `OFF` is the offscreen position used to hide objects that are not in use.

**How it works.** `build()` creates each plate with its colour. `park()` moves inactive objects to `OFF`.

**Rules.**
- Use a different colour for each adjacent pair of plates. Two plates in the same colour make a transition look like nothing happened.
- Use `OFF` for hiding. Do not change `opacity` to hide an object here, because a transition that uses opacity would then conflict with it.

#### 4. Math helpers

**What they contain.** `clamp`, `prog`, `ease_in_out`, and `ease_in_back`.

- `clamp(v)` limits a value to 0 to 1.
- `prog(t, start, dur)` converts time into a 0 to 1 progress value over a window.
- `ease_in_out(p)` is a cubic curve: slow at both ends, fast in the middle.
- `ease_in_back(p)` starts slightly negative, then accelerates forward. It makes the plate pull back a little before it moves.

**Why they're needed.** Linear motion looks mechanical. Each transition is shaped by one of these curves. `ease_in_back` is the anticipation: the plate moves against its direction before it leaves.

**How they work.** `prog` is the basis of every motion. It returns 0 before the window and 1 after it. The easing functions then reshape that value.

**Rules.**
- Feed time through `prog` before easing. Do not ease raw time.
- Use `ease_in_back` only for an exit that should look like it is gathering force. It produces a small negative value at the start, which is the anticipation.

#### 5. Shape generators: `rect_pts`, `circle_pts`, `star_pts`

**What they contain.** Three functions that return a list of `(x, y)` points relative to the centre of a shape.

**Why they're needed.** Morphs need outlines. These three cover the shapes used: a full plate (a rectangle), a small disc, and a five-point star.

**How they work.** `rect_pts` returns the four corners. `circle_pts` and `star_pts` return evenly spaced points around a circle or star, starting at the top.

**Rules.**
- Keep all points relative to the centre. The shape is then positioned with `x` and `y`.
- Use the same point order for shapes that will morph. A reversed order produces a twisted morph.

#### 6. `resample`, `align_closed`, `morph`

**What they contain.** The correspondence machinery, the same as the shape-morph reference.

- `resample(points, n)` spaces `n` points evenly along the outline's length, so shapes with different vertex counts can be paired.
- `align_closed(ref, pts)` picks the start point and direction that keep each point closest to its partner.
- `morph(a, b, p)` interpolates paired points at progress `p`.

**Why they're needed.** A morph between outlines with different point counts, or with a bad start point, produces twisted geometry. These steps prevent that.

**How they work.** `align_closed` tests every cyclic shift and both directions, and keeps the one with the lowest total squared distance. It is exhaustive, so its cost grows with the square of the point count.

**Rules.**
- Always align after resampling, never before.
- Keep point counts equal before pairing. Here all three outlines use 96 points.
- Keep `n` near 96 to 120. Higher values make the alignment search slow.

#### 7. Precomputed outlines: `RECT96`, `SMALL96`, `STAR96`

**What they contain.** Three 96-point outlines computed once when the script loads.

- `RECT96`: the full-frame rectangle.
- `SMALL96`: a 2 px disc at the centre, aligned to `RECT96`.
- `STAR96`: a five-point star, aligned to `RECT96`.

**Why they're needed.** Computing alignments every frame would be slow. These are computed once and reused in slots 3 and 4.

**How they work.** Each outline is resampled to 96 points, then aligned to `RECT96` so that point *k* of one pairs with point *k* of the other.

**Rules.**
- Compute these once, outside `animate()`.
- If you change the star size or disc size, recompute the aligned outline. Do not edit the points by hand.

#### 8. Strip and bar names

**What they contain.** `STRIPS` (six names for the fragmentation slot), `BARS` (three names for the bars slot), and `ALL_NAMES` (every plate, strip, and bar name).

**Why it's needed.** `animate()` parks every name that is not active. `ALL_NAMES` is the list it checks, so every object must be listed there.

**How it works.** At each frame, `animate()` loops over `ALL_NAMES`, and any name not in the active set moves to `OFF`.

**Rules.**
- Add any new object's name to `ALL_NAMES`, or it will never be parked.

#### 9. `LABELS`

**What it contains.** One caption per slot, shown at the bottom of the frame.

**Why it's needed.** Each transition is named, so a viewer or a developer can see which technique is playing.

**How it works.** `animate()` writes `LABELS[k]` to the `Label` text object. During the hold before slot 0, the label is empty.

**Rules.**
- Keep one label per slot. A label that is missing for a slot is not an error, but the caption will be blank.

#### 10. `place()`

**What it does.** Sets a shape's position, rotation, scale, opacity, and outline in one call.

**Why it's needed.** Every transition sets the same properties. Routing them through one helper keeps the set of properties the same in every slot, so a transition cannot forget to reset one of them.

**How it works.** It writes `x`, `y`, `rotation_z`, `scale`, and `opacity` to the named object, and sets `points` only when an outline is given.

**Rules.**
- Pass `points` only when the outline changes. Setting the same points every frame is wasted work.
- Pass `rot` and `scale` explicitly. The defaults are 0 and 1, so a transition that omits them resets the plate to rest.

#### 11. `wave_points(p)`: directional distortion

**What it does.** Builds the outline of a plate whose left edge is a wave. The wave sweeps from left to right as `p` increases.

**Why it's needed.** This is the directional distortion of slot 6. The edge is an actual geometric change to the plate's outline, not a replacement of one plate by another.

**How it works.** The function samples 41 points down the left edge. Each point's x-position is a base edge that moves across the frame, plus a sine wave that gives it the wave shape. The sine's phase also changes with `p`, so the wave travels as well as sweeps. The right side of the outline extends past the frame, so the plate always fills its visible part.

**Rules.**
- Keep the outline closed and in the same point order each frame.
- Keep the wave amplitude small enough that the edge does not fold back. About 60 px works.
- Start the base edge off-screen to the left, and end it well past the right edge. Otherwise a sliver of the next plate shows at the start or end.

#### 12. The nine slot functions: `sec0` to `sec8`

**What they do.** Each function sets the positions and outlines for one slot, and returns the name of the plate that is underneath and a list of the moving objects.

**Why they're needed.** Every transition is different, so each needs its own motion code. Returning the underneath plate and the moving objects gives `animate()` what it needs to order the layers and park the rest.

| Function | Moving object | Underneath | Motion |
|---|---|---|---|
| `sec0` | Plate 0 | Plate 1 | Horizontal slide with `ease_in_back` |
| `sec1` | Plate 1 | Plate 2 | Vertical slide up |
| `sec2` | Plate 2 | Plate 3 | Diagonal slide with 30 degree rotation |
| `sec3` | Plate 3 | Plate 4 | Outline morphs from rectangle to small disc |
| `sec4` | Plate 5 | Plate 4 | Outline morphs from star to rectangle (grows over Plate 4) |
| `sec5` | Strips 0 to 5 | Plate 6 | Six strips move up and down alternately |
| `sec6` | Plate 6 | Plate 7 | Wavy left edge sweeps right |
| `sec7` | Bars 0 to 2 | Plate 8 | Three bars move up and down with staggered delays |
| `sec8` | Plate 8 | Plate 9 | Rotation to 90 degrees and scale to zero |

**How they work.** Each function first computes an eased progress value from its local time `tl`. It then calls `place()` for the underneath plate, which is set to rest at the centre, and for each moving object.

- **`sec0`** uses `ease_in_back`. The first part of the move pulls back slightly, then the plate leaves to the right.
- **`sec3`** calls `morph(RECT96, SMALL96, e)`. At `e = 0` the outline is the full frame. At `e = 1` it is a small disc at the centre, so the plate shrinks inward and reveals Plate 4 from the edges.
- **`sec4`** is the reverse: the star grows into the full frame while Plate 4 stays underneath. This is the "enter" case, because the moving object comes in over the current plate.
- **`sec5`** places six strips. Each strip is one sixth of the frame width. Even strips move up and odd strips move down. At rest, the six strips cover the frame exactly, in the same colour as Plate 5, so the fragmentation begins from a seamless state.
- **`sec7`** gives bar 1 an opacity dip: `1 - 0.35 * sin(pi * e)`. The dip peaks in the middle of its move and returns to 1, so the opacity change is visible only while the bar is moving.
- **`sec8`** uses `max(0.001, 1 - e)` for scale. A scale of exactly zero could break the object, so the floor keeps it valid.

**Rules.**
- Every slot function must set the underneath plate to rest at the centre. If it does not, a plate from an earlier slot may be visible in the wrong position.
- Every slot must return the underneath plate and the complete list of moving objects. A missing name means that object is parked while it should be moving.
- Use `ease_in_back` only for the first slot's exit. Anticipation on every slot would look repetitive.

#### 13. `SECTIONS`

**What it contains.** The list of the nine slot functions in order.

**Why it's needed.** `animate()` uses the slot index to choose the function. Keeping the list in order keeps slot numbers and functions aligned.

**How it works.** `animate()` calls `SECTIONS[k](scene, tl)` where `k` is the slot index.

**Rules.**
- Append new slots to the end. Inserting one in the middle shifts the labels out of step with the transitions.

#### 14. `build()`

**What it does.** Creates the ten plates, the six strips, the three bars, and the label object.

**Why it's needed.** Every object must exist before `animate()` runs, because `scene.get()` raises an error for a name that does not exist.

**How it works.** Plates are created as full-frame rectangles in their colours. Strips and bars are created offscreen, with the strip and bar colours. The label is created at the bottom of the frame.

**Rules.**
- Create every name listed in `ALL_NAMES`. A missing object raises an error the first time it is parked.
- Keep `scene.duration` equal to `DURATION`, so the video length matches the script.

#### 15. `animate()`

**What it does.** Chooses the slot for the current time, runs its function, parks everything else, and orders the layers.

**Why it's needed.** This is the control loop. It keeps one slot active at a time, and it makes sure the right plate is on top.

**How it works, step by step.**

1. Compute `rel = t - start`. If `rel < 0`, the script is in the opening hold: `k = -1`, and Plate 0 is placed full-frame as the only visible plate.
2. Otherwise compute `k = min(rel // section, 8)`, the slot index, and `tl = rel - k * section - lead`, the local time.
3. Run `SECTIONS[k](scene, tl)`, which returns the underneath plate and the moving list. Set the label.
4. Build the active list as the underneath plate plus the moving objects.
5. Park every name in `ALL_NAMES` that is not active.
6. Call `bring_to_front` on each active name, in order: underneath first, moving objects last.

**Why the layer ordering works.** All plates are full-frame, so their draw order decides what is visible. Bringing the underneath plate forward first, then the moving objects, puts the moving objects on top. This assumes `bring_to_front` puts an object on top of all others, which is documented but not yet verified in MotionCode.

**Rules.**
- Never change the order of the `bring_to_front` calls. The underneath plate must come first.
- Park every inactive object. An object left at a visible position can show through in a later slot.
- Keep the opening hold and the slot logic in `animate()`. Do not spread them across the slot functions.

### Rules for transitions in general

1. **One moving layer at a time.** Each slot moves one plate, or one set of pieces, over one plate that is already at rest.
2. **Every transition ends at rest.** The underneath plate ends at the centre. The moving objects end off-screen or at their final shape.
3. **Plates always cover the frame.** Every plate is full-frame, so the visible area is always one of the plates.
4. **Name every object.** `ALL_NAMES` is the single list of everything the script can park.
5. **Vary the technique between slots.** Consecutive slots use different motions. Slots 0 to 2 are wipes; 3 and 4 morph outlines; 5 to 8 break up or rotate the plate.
6. **Use the lead.** The 0.3 s pause before each motion gives the still frame time to register.
7. **Keep outlines in matching point order.** Morphs and waves depend on it.

### What this is designed for

A reusable reference for reveal transitions between full-frame compositions. Each slot is a self-contained function, so a single transition can be copied into another project. To use it with real content, replace each solid plate with a composition (its objects can be moved together with `parent`), keep the plate's position and outline logic, and leave the parking and layer-ordering code unchanged.

It is not designed for true masked reveals, circular iris transitions, or transitions between layers that already contain text and images. Those need features the reference does not document.

### Known limits

- **No true masks.** Every reveal is a moved or morphed plate. A plate that is not full-frame, or that sits over moving content, will show its edges.
- **Circular reveal is approximated.** Slot 3 contracts a rectangle into a disc. It is not an iris mask, so the reveal edge is a shrinking outline, not a circle cut out of the next plate.
- **Plate 8 is not parked after its slot.** Slot 8 leaves Plate 8 at a scale of 0.001 at the centre. It is invisible, but it remains an active object and is never parked. It is harmless here, but a longer sequence should park it.
- **Layer order depends on `bring_to_front`.** The script calls it every frame. If it does not order objects as documented, the moving plate may be hidden under the underneath plate.
- **Opacity dip on bar 1 is a design choice.** Opacity is set per object. Other objects in the same slot are not affected.

### Checks run

Across all 1,201 frames: no non-finite values in any object. The opening hold shows Plate 0 at the centre. After slot 0 finishes, Plate 0 is parked and Plate 1 is in place. At the end, Plate 9 is at the centre. Plate 8 is active at a scale of 0.001, as described above.

### Not yet verified in MotionCode

- `bring_to_front` places an object on top of all others, as the layer-ordering code assumes.
- `scale` and `opacity` on a polygon behave as documented when set every frame.
- Assigning `.points` on a polygon redraws it each frame. Slots 3, 4, and 6 depend on this.
- Rotation of a full-frame plate about its centre keeps it centred. Slot 2 and slot 8 depend on this.

---

## Part 2: Kinetic typography

**File:** `kinetic_typography.py`

### What it shows

Five 8-second sections, each with its own font style, composition, and motion vocabulary. The sections do not overlap, and each one parks its objects before the next begins.

| Section | Time (s) | Font style | Composition | Techniques |
|---|---|---|---|---|
| Characters | 0 to 8 | Heavy sans, `MOTION` | Centred row | Rise from below, spread, scatter and rotate, curved travel |
| Words | 8 to 16 | Wide sans, mixed weights | Asymmetric | Sequential entry, expand, separate and regroup, spacing change, vertical stack |
| Lines | 16 to 24 | Serif, three sizes | Centred stack, then asymmetric | Entry from three sides, uneven separation, asymmetric placement |
| Transformations | 24 to 32 | Condensed heavy | Centred row | EXPAND spread and contract; BREAK to BUILD letter reconstruction |
| Alignment | 32 to 40 | Neutral sans | Centred, then left-aligned | Left-edge movement, consistent spacing, final caption |

### Code

```python
"""KINETIC TYPOGRAPHY REFERENCE (upgraded). Standalone. 40 seconds, 1920 x 1080, 30 fps.

Five sections, each 8 seconds, with no overlap. Each section finishes, and its
objects are parked offscreen, before the next one begins.

    0 to 8 s    CHARACTERS (heavy sans, MOTION)
                rise from below, spread apart, scatter and rotate in, travel along curved paths
    8 to 16 s   WORDS (wide sans, asymmetric composition)
                sequential entry from alternating sides, expand from centre, separate and
                regroup, spacing change, vertical stack and back
    16 to 24 s  LINES (serif, three sizes)
                entry from three directions, separation by different distances, asymmetric
                placement, and return to a symmetric stack
    24 to 32 s  TRANSFORMATIONS (condensed heavy)
                EXPAND: spreads from centre and contracts toward a focal point.
                BREAK to BUILD: letters separate, travel, rotate and scale, change while
                scattered, and reassemble.
    32 to 40 s  ALIGNMENT (neutral sans)
                three lines move from a centred stack to a precise left edge, with a
                consistent line spacing and a readable final arrangement.

Measurement and rendering: each text object is created with the same font, size and
bold setting that it is measured with, through one helper, make_text(). Positions use
the measured widths, and every text object uses align="center", so its position is its
centre and rotation and scale pivot about that centre.

Only documented properties are used: text x, y, size, font, bold, align, color,
rotation_z, scale and opacity, plus scene.measure_text, scene.list_fonts, scene.get,
and the text attribute. Font availability is checked with scene.list_fonts(). A font
that is not installed falls back to Arial.

Limits: each letter and word is its own text object, because the reference documents
no per-character or per-word text object. Character spacing is the sum of the measured
glyph widths, so kerning between letters is not applied.
"""
import math

W, H = 1920, 1080
CX, CY = 960.0, 540.0
DURATION = 40.0
BG = "#0B0F1A"
INK = "#F5F1E8"
ACCENT = "#FF6B4A"
COOL = "#70D6FF"
MUTED = "#3A4A6B"
OFF = -6000.0

SECTIONS = {
    "chars": (0.0, 8.0),
    "words": (8.0, 16.0),
    "lines": (16.0, 24.0),
    "transform": (24.0, 32.0),
    "align": (32.0, 40.0),
}

FONT_PICKS = {
    "heavy": ["Arial Black", "Impact", "Arial"],
    "wide": ["Verdana", "Arial"],
    "serif": ["Georgia", "Times New Roman", "Arial"],
    "condensed": ["Arial Narrow", "Oswald", "Arial"],
    "neutral": ["Helvetica", "Arial"],
}

META = {}     # name -> dict(text, font, bold, size, w, section)
LAYOUT = {}   # name -> final (x, y) centre
FONTS = {}    # style key -> resolved font name


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def prog(t, start, dur):
    return clamp((t - start) / dur)


def ease_in_out(p):
    p = clamp(p)
    return 4 * p * p * p if p < 0.5 else 1 - ((-2 * p + 2) ** 3) / 2.0


def ease_out_cubic(p):
    p = clamp(p)
    return 1 - (1 - p) ** 3


def ease_out_expo(p):
    p = clamp(p)
    return 1.0 if p >= 1.0 else 1 - 2 ** (-10 * p)


def ease_out_back(p, s=1.70158):
    p = clamp(p)
    return 1 + (s + 1) * (p - 1) ** 3 + s * (p - 1) ** 2


def bump(t, start, dur):
    """0 at start, 1 at the midpoint, 0 at start + dur. Smooth in and out."""
    half = dur / 2.0
    return ease_in_out(prog(t, start, half)) - ease_in_out(prog(t, start + half, half))


def in_section(name, t):
    s, e = SECTIONS[name]
    return s <= t < e


def pick_font(scene, style):
    """First installed font from the style's list, else Arial."""
    if style in FONTS:
        return FONTS[style]
    try:
        installed = set(scene.list_fonts())
    except Exception:
        installed = set()
    chosen = "Arial"
    for cand in FONT_PICKS[style]:
        if cand in installed or cand == "Arial":
            chosen = cand
            break
    FONTS[style] = chosen
    return chosen


def measure(scene, text, size, style, bold):
    return scene.measure_text(text, size=size, font=pick_font(scene, style), bold=bold)[0]


def make_text(scene, name, text, size, style, bold, color, section):
    """Create a text object and record the metrics used for layout.

    The same font, size and bold setting are used for measurement and creation.
    """
    font = pick_font(scene, style)
    w = scene.measure_text(text, size=size, font=font, bold=bold)[0]
    scene.add_text(name, text, x=OFF, y=OFF, size=size, font=font, bold=bold,
                   color=color, align="center")
    META[name] = dict(text=text, font=font, bold=bold, size=size, w=w, section=section)
    return w


def set_pose(scene, name, x, y, rot=0.0, scale=1.0, op=1.0, text=None):
    o = scene.get(name)
    o.x, o.y = x, y
    o.rotation_z = rot
    o.scale = scale
    o.opacity = op
    if text is not None and o.text != text:
        o.text = text


def park_names(scene, names):
    for n in names:
        o = scene.get(n)
        o.x, o.y = OFF, OFF


def park_section(scene, section):
    park_names(scene, [n for n, m in META.items() if m["section"] == section])


# -------------------------------------------------------------- build

def build(scene):
    scene.width, scene.height = W, H
    scene.fps = 30
    scene.duration = DURATION
    scene.background = BG

    # Section 0: MOTION, heavy sans. Spacing is the sum of measured glyph widths.
    letters = "MOTION"
    widths = [measure(scene, c, 230, "heavy", True) for c in letters]
    x = CX - sum(widths) / 2.0
    for i, c in enumerate(letters):
        name = "CH%d" % i
        make_text(scene, name, c, 230, "heavy", True, INK, "chars")
        LAYOUT[name] = (x + widths[i] / 2.0, 500.0)
        x += widths[i]

    # Section 1: wide sans, asymmetric composition.
    make_text(scene, "W_MAKE", "MAKE", 200, "wide", True, INK, "words")
    make_text(scene, "W_IT", "IT", 96, "wide", False, ACCENT, "words")
    make_text(scene, "W_MOVE", "MOVE", 200, "wide", True, INK, "words")
    make_text(scene, "W_CLEAR", "CLEAR", 96, "wide", False, COOL, "words")
    w_make = META["W_MAKE"]["w"]
    w_it = META["W_IT"]["w"]
    w_move = META["W_MOVE"]["w"]
    w_clear = META["W_CLEAR"]["w"]
    LAYOUT["W_MAKE"] = (200 + w_make / 2.0, 300.0)
    LAYOUT["W_IT"] = (200 + w_make + 60 + w_it / 2.0, 300.0)
    LAYOUT["W_MOVE"] = (200 + w_move / 2.0, 560.0)
    LAYOUT["W_CLEAR"] = (1200 + w_clear / 2.0, 780.0)

    # Section 2: serif lines in three sizes, centred stack.
    make_text(scene, "L_KIN", "KINETIC", 200, "serif", True, INK, "lines")
    make_text(scene, "L_TYPE", "TYPE", 120, "serif", False, ACCENT, "lines")
    make_text(scene, "L_ENG", "ENGINE", 170, "serif", True, INK, "lines")
    LAYOUT["L_KIN"] = (CX, 360.0)
    LAYOUT["L_TYPE"] = (CX, 560.0)
    LAYOUT["L_ENG"] = (CX, 760.0)

    # Section 3: condensed heavy. EXPAND letters, then BREAK/BUILD letters.
    expand = "EXPAND"
    ex_w = [measure(scene, c, 230, "condensed", True) for c in expand]
    x = CX - sum(ex_w) / 2.0
    for i, c in enumerate(expand):
        name = "EX%d" % i
        make_text(scene, name, c, 230, "condensed", True, INK, "transform")
        LAYOUT[name] = (x + ex_w[i] / 2.0, CY)
        x += ex_w[i]

    before, after = "BREAK", "BUILD"
    cell = [max(measure(scene, before[i], 230, "condensed", True),
                measure(scene, after[i], 230, "condensed", True))
            for i in range(len(before))]
    x = CX - sum(cell) / 2.0
    for i in range(len(before)):
        name = "BK%d" % i
        make_text(scene, name, before[i], 230, "condensed", True, INK, "transform")
        LAYOUT[name] = (x + cell[i] / 2.0, CY)
        x += cell[i]

    # Section 4: neutral sans lines, centred then left-aligned.
    for name, text, size, bold, y in [("AL0", "ALIGN", 150, True, 330.0),
                                      ("AL1", "CHANGES", 110, False, 540.0),
                                      ("AL2", "SHAPE", 190, True, 750.0)]:
        make_text(scene, name, text, size, "neutral", bold, INK, "align")
        LAYOUT[name] = (CX, y)
    make_text(scene, "AL_CAP", "Left edge at x = 200, line spacing 210 px", 36,
              "neutral", False, MUTED, "align")


# -------------------------------------------------------------- section 0: characters

SCATTER = [(-260.0, -200.0), (180.0, 160.0), (-140.0, 220.0),
           (300.0, -170.0), (-220.0, 140.0), (120.0, -230.0)]
TRAJ = [(-200.0, 180.0), (160.0, -220.0), (-120.0, -160.0),
        (220.0, 140.0), (-240.0, -60.0), (140.0, 200.0)]
BULGE = [(60.0, -140.0), (-80.0, 120.0), (100.0, 90.0),
         (-120.0, -100.0), (80.0, -120.0), (-60.0, 140.0)]


def section_chars(scene, t):
    if not in_section("chars", t):
        park_section(scene, "chars")
        return
    lt = t - SECTIONS["chars"][0]
    for i in range(6):
        name = "CH%d" % i
        fx, fy = LAYOUT[name]
        dx = dy = 0.0
        rot = 0.0
        scale = 1.0

        # Stage 1 (0.0 to 2.2): rise from below, staggered.
        t0 = 0.3 + i * 0.18
        e = ease_out_cubic(prog(lt, t0, 1.0))
        dy += 320.0 * (1 - e)
        scale *= 0.6 + 0.4 * e
        op = 1.0 if lt >= t0 else 0.0

        # Stage 2 (2.2 to 4.2): spread apart, then return to exact spacing.
        dx += (i - 2.5) * 130.0 * bump(lt, 2.2, 2.0)

        # Stage 3 (4.2 to 6.2): scatter and rotate, then return.
        sc = bump(lt, 4.2, 2.0)
        dx += SCATTER[i][0] * sc
        dy += SCATTER[i][1] * sc
        rot += (540.0 if i % 2 == 0 else -540.0) * sc

        # Stage 4 (6.2 to 7.6): travel along a curved path, then return.
        g = bump(lt, 6.2, 1.4)
        dx += TRAJ[i][0] * g + BULGE[i][0] * math.sin(math.pi * g)
        dy += TRAJ[i][1] * g + BULGE[i][1] * math.sin(math.pi * g)

        set_pose(scene, name, fx + dx, fy + dy, rot=rot, scale=scale, op=op)


# -------------------------------------------------------------- section 1: words

def section_words(scene, t):
    if not in_section("words", t):
        park_section(scene, "words")
        return
    lt = t - SECTIONS["words"][0]
    names = ["W_MAKE", "W_IT", "W_MOVE", "W_CLEAR"]
    enter_dir = [-1.0, 1.0, -1.0, 1.0]
    enter_delay = [0.0, 0.35, 0.7, 1.05]
    spread_dir = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    stack_y = [240.0, 420.0, 600.0, 780.0]
    spacing_dx = [0.0, 90.0, 0.0, -60.0]

    for i, name in enumerate(names):
        fx, fy = LAYOUT[name]
        w = META[name]["w"]
        dx = dy = 0.0
        rot = 0.0
        scale = 1.0

        # Entry (0 to 2.0): slide in from alternating sides, fast settle.
        d = enter_delay[i]
        e = ease_out_expo(prog(lt, d, 1.0))
        dx += enter_dir[i] * 900.0 * (1 - e)
        rot += -10.0 * enter_dir[i] * (1 - e)
        scale *= 0.6 + 0.4 * e
        op = 1.0 if lt >= d else 0.0

        # Expand outward from the centre (2.0 to 3.2).
        ex = bump(lt, 2.0, 1.2)
        dx += (fx - CX) * 0.25 * ex
        dy += (fy - CY) * 0.25 * ex

        # Separate and regroup into the corners (3.2 to 4.6).
        sg = bump(lt, 3.2, 1.4)
        dx += spread_dir[i][0] * 160.0 * sg
        dy += spread_dir[i][1] * 110.0 * sg

        # Change spacing (4.6 to 5.6).
        dx += spacing_dx[i] * bump(lt, 4.6, 1.0)

        # Vertical stack and back (5.6 to 6.8).
        k = bump(lt, 5.6, 1.2)
        dx += (200 + w / 2.0 - fx) * k
        dy += (stack_y[i] - fy) * k

        set_pose(scene, name, fx + dx, fy + dy, rot=rot, scale=scale, op=op)


# -------------------------------------------------------------- section 2: lines

def section_lines(scene, t):
    if not in_section("lines", t):
        park_section(scene, "lines")
        return
    lt = t - SECTIONS["lines"][0]
    names = ["L_KIN", "L_TYPE", "L_ENG"]
    entry = [(-1200.0, 0.0, 0.0), (0.0, -600.0, 0.6), (1200.0, 0.0, 1.2)]
    sep_dy = [-140.0, 0.0, 170.0]
    asym_dx = [-360.0, 260.0, -120.0]

    for i, name in enumerate(names):
        fx, fy = LAYOUT[name]
        ex_dx, ex_dy, d = entry[i]
        e = ease_out_cubic(prog(lt, d, 1.0))
        dx = ex_dx * (1 - e)
        dy = ex_dy * (1 - e)
        if i == 0:
            scale, rot = 0.8 + 0.2 * e, -6.0 * (1 - e)
        elif i == 2:
            scale, rot = 1.2 - 0.2 * e, 8.0 * (1 - e)
        else:
            scale, rot = 1.0, 0.0
        op = 1.0 if lt >= d else 0.0

        # Separation by different distances (2.0 to 3.4).
        dy += sep_dy[i] * bump(lt, 2.0, 1.4)

        # Asymmetric placement (3.4 to 4.8), then back to the symmetric stack.
        dx += asym_dx[i] * bump(lt, 3.4, 1.4)

        set_pose(scene, name, fx + dx, fy + dy, rot=rot, scale=scale, op=op)


# -------------------------------------------------------------- section 3: transformations

EX_FOCAL = (CX, 300.0)
BK_TRAVEL = [(-40.0, -260.0), (120.0, 180.0), (-160.0, 220.0), (180.0, -200.0), (60.0, -120.0)]
BK_ROT = [-70.0, 40.0, -30.0, 60.0, -50.0]


def section_transform(scene, t):
    if not in_section("transform", t):
        park_section(scene, "transform")
        return
    lt = t - SECTIONS["transform"][0]

    # EXPAND (0 to 2.0): spread from the centre (0 to 1.0), contract toward a focal point (1.0 to 2.0).
    ex_names = ["EX%d" % i for i in range(6)]
    if lt < 2.0:
        spread = bump(lt, 0.0, 1.0) * 0.55
        contract = bump(lt, 1.0, 1.0)
        for name in ex_names:
            fx, fy = LAYOUT[name]
            px = CX + (fx - CX) * (1 + spread)
            py = CY + (fy - CY) * (1 + spread)
            px += (EX_FOCAL[0] - px) * 0.6 * contract
            py += (EX_FOCAL[1] - py) * 0.6 * contract
            set_pose(scene, name, px, py, scale=1.0 - 0.35 * contract)
    else:
        park_names(scene, ex_names)

    # BREAK to BUILD (2.6 to 8.0).
    bk_names = ["BK%d" % i for i in range(5)]
    if lt < 2.6:
        park_names(scene, bk_names)
        return
    # Stages, local to this section:
    #   separate 3.0 to 3.8, travel 3.8 to 4.4, hold scattered to 5.2,
    #   text changes at 4.9 while scattered, reposition 5.2 to 6.2.
    sep = ease_in_out(prog(lt, 3.0, 0.8)) - ease_in_out(prog(lt, 5.2, 1.0))
    traj = ease_in_out(prog(lt, 3.8, 0.6)) - ease_in_out(prog(lt, 5.2, 1.0))
    for i, name in enumerate(bk_names):
        fx, fy = LAYOUT[name]
        dx = (i - 2) * 170.0 * sep + BK_TRAVEL[i][0] * traj
        dy = BK_TRAVEL[i][1] * traj
        text = "BREAK"[i] if lt < 4.9 else "BUILD"[i]
        set_pose(scene, name, fx + dx, fy + dy, rot=BK_ROT[i] * traj,
                 scale=1.0 - 0.25 * traj, text=text)


# -------------------------------------------------------------- section 4: alignment

def section_align(scene, t):
    if not in_section("align", t):
        park_section(scene, "align")
        return
    lt = t - SECTIONS["align"][0]
    delays = [0.6, 0.8, 1.0]
    for i, name in enumerate(["AL0", "AL1", "AL2"]):
        w = META[name]["w"]
        _, fy = LAYOUT[name]
        left_centre = 200 + w / 2.0
        a = ease_in_out(prog(lt, delays[i], 1.4))
        set_pose(scene, name, CX + (left_centre - CX) * a, fy)
    # Caption appears once the left edge has settled.
    cap_w = META["AL_CAP"]["w"]
    set_pose(scene, "AL_CAP", 200 + cap_w / 2.0, 900.0, op=1.0 if lt >= 2.4 else 0.0)


# -------------------------------------------------------------- animate

def animate(scene, t):
    section_chars(scene, t)
    section_words(scene, t)
    section_lines(scene, t)
    section_transform(scene, t)
    section_align(scene, t)
```

### Part by part

#### 1. The header docstring

**What it is.** The summary of the five sections, the measurement rule, and the limits.

**Why it's needed.** It states the two rules the whole script depends on: measurement and rendering must match, and every text object uses `align="center"`. Anyone changing the script needs these rules first.

**How it works.** It is a docstring and does nothing at run time.

#### 2. Constants

**What they contain.** Frame size, the frame centre, the duration, colours (`INK`, `ACCENT`, `COOL`, `MUTED`), and `OFF = -6000.0`.

**Why they're needed.** Colours are named once, so a palette change happens in one place. `OFF` hides text that is not in use.

**How they work.** `OFF` is the offscreen position. The park functions move objects there.

**Rules.**
- Use no more than about three accent colours on screen at once. This script uses one accent (`ACCENT`) and one secondary (`COOL`), and the rest is ink on dark.

#### 3. `SECTIONS`: the section windows

**What it contains.** A dictionary of five `(start, end)` pairs, each 8 seconds long.

**Why it's needed.** Every section checks its own window. A section that is outside its window parks its objects. Because the windows are contiguous and do not overlap, a text object belongs to exactly one section at a time.

**How it works.** `in_section(name, t)` returns `True` when `start <= t < end`. Each section function uses that check first.

**Rules.**
- Keep the windows contiguous. A gap leaves the screen empty, and an overlap makes two sections draw at once.
- Keep each window at least as long as the motions inside it. The characters section, for example, runs its four stages in 7.6 seconds, so it has 8 seconds in total.

#### 4. `FONT_PICKS`: the font fallbacks

**What it contains.** For each style, a list of candidate font names, ending in Arial.

| Style | Candidates |
|---|---|
| `heavy` | Arial Black, Impact, Arial |
| `wide` | Verdana, Arial |
| `serif` | Georgia, Times New Roman, Arial |
| `condensed` | Arial Narrow, Oswald, Arial |
| `neutral` | Helvetica, Arial |

**Why it's needed.** Each section should look different, and the font is the main carrier of that difference. But a font that is not installed on the machine would fail, so each style falls back through a list.

**How it works.** `pick_font` returns the first candidate that `scene.list_fonts()` reports as installed. Arial is accepted as the final fallback without a check.

**Rules.**
- Always end a list with a font that is always installed. Here that is Arial.
- Choose candidates with similar proportions. A fallback from a condensed font to a wide one changes the layout, not just the look.

#### 5. `META`, `LAYOUT`, `FONTS`

**What they contain.**
- `META` records, for each text object: its text, font, bold setting, size, measured width, and section.
- `LAYOUT` records each object's final centre position.
- `FONTS` caches the chosen font for each style.

**Why they're needed.** Positions are calculated from measurements, and they must be stored somewhere the animation can read. `META` also lets the park functions find every object in a section.

**How they work.** `make_text` fills `META` as each object is created. `build` fills `LAYOUT` from `META` widths. `FONTS` ensures each style is resolved once.

**Rules.**
- Look up widths from `META`, not by measuring again. A second measurement could use different settings and drift.
- Store layout positions as centres, because every text object is centred.

#### 6. Easing functions

**What they contain.** `ease_in_out`, `ease_out_cubic`, `ease_out_expo`, `ease_out_back`, and `bump`.

- `ease_out_cubic` decelerates smoothly. It is used for rising letters and line entries.
- `ease_out_expo` decelerates quickly, then settles. It is used for word entries, where a fast arrival looks crisp.
- `ease_out_back` overshoots its target and settles back. It is used for the character entry and the line entries.
- `bump(t, start, dur)` rises from 0 to 1 at the midpoint, then falls back to 0 at the end.

**Why they're needed.** Each section uses a different curve so that the motion vocabularies differ.

**How they work.** `bump` is the most important one. It is built from two `ease_in_out` ramps, one rising and one falling, so an offset that uses `bump` always starts at rest and ends at rest. That is what makes it safe for a motion to return to its exact final position.

**Rules.**
- Use `bump` for any offset that must return to rest. Using a single ramp leaves the object displaced at the end.
- Use `ease_out_back` for entries only. Overshoot in the middle of a motion looks like an error.
- Use `ease_out_expo` for quick, crisp arrivals.

#### 7. `in_section`, `pick_font`, `measure`, `make_text`

**What they do.**
- `in_section` checks the section window.
- `pick_font` resolves a style to an installed font, and caches it.
- `measure` returns a width using the resolved font and the given bold setting.
- `make_text` creates a text object and records its metrics.

**Why they're needed.** These four functions are the measurement fix. The earlier version measured with one font and created the object with another. `make_text` now takes one set of settings, measures with them, and creates the object with the same settings.

**How they work.** `make_text` calls `pick_font` once, uses the result for both `measure_text` and `add_text`, and stores the same values in `META`. The object is created offscreen, with `align="center"`.

**Rules.**
- Create every text object through `make_text`. Calling `add_text` directly would bypass the measurement record.
- Never change `bold` or `font` on an object after creation. The layout was calculated for the original settings.

#### 8. `set_pose`, `park_names`, `park_section`

**What they do.**
- `set_pose` sets position, rotation, scale, opacity, and optionally the text.
- `park_names` moves named objects offscreen.
- `park_section` parks every object that belongs to a section.

**Why they're needed.** Every section sets the same properties on each object. Routing them through one helper keeps the set consistent, and parking through one helper keeps the rule that a section cleans up after itself.

**How they work.** `set_pose` writes the text only when it differs from the current value, to avoid reassigning every frame. `park_section` looks up each name in `META` and parks those whose section matches.

**Rules.**
- Set the text only when it actually changes. The BREAK-to-BUILD switch is the only place that changes text during a section.
- Park with `park_section` at the start of a section's inactive time, not only at its end. This guarantees no leftover objects.

#### 9. `build()`

**What it does.** Creates every text object. It works in five parts, one per section.

**Section 0: characters.** `MOTION` is set in the heavy style at size 230. Each letter is measured individually, and the row is centred by summing the widths. Each letter's final centre is its left edge plus half its width.

**Section 1: words.** `MAKE` and `MOVE` are large (size 200) and bold. `IT` and `CLEAR` are small (size 96) and regular, in accent and cool colours. The composition is asymmetric: the large words sit on the left, and `IT` sits to the right of `MAKE`, while `CLEAR` sits low on the right side.

**Section 2: lines.** `KINETIC`, `TYPE`, and `ENGINE` are serif, in sizes 200, 120, and 170. They form a centred stack at x = 960, with spacing of 200 px.

**Section 3: transformations.** `EXPAND` is laid out letter by letter in the condensed style. `BREAK` is laid out using the wider of each pair of letters from `BREAK` and `BUILD` as the cell width, so that when the letters change, neither overlaps its neighbour.

**Section 4: alignment.** Three neutral sans lines (`ALIGN`, `CHANGES`, `SHAPE`) of different sizes, plus a small caption.

**Why the cell widths matter.** Without them, changing `BREAK` to `BUILD` would move letters into each other's space, because the glyph widths differ. Using the larger width for each position means every glyph has room.

**Rules.**
- Create the objects for a section in one block, with its layout in `LAYOUT` at the same time.
- Keep the layout in `LAYOUT` as centres. A left edge stored by mistake would shift every letter by half its width.

#### 10. `SCATTER`, `TRAJ`, `BULGE`, `EX_FOCAL`, `BK_TRAVEL`, `BK_ROT`

**What they contain.** Fixed offsets, one per letter, that define the scattered, travelling, and rotated positions.

- `SCATTER` and `TRAJ` are offsets in pixels for each of the six letters in `MOTION`.
- `BULGE` is an extra sideways bend for each letter's curved path.
- `EX_FOCAL` is the point that EXPAND contracts toward.
- `BK_TRAVEL` and `BK_ROT` are the travel offsets and rotations for the five letters of `BREAK`.

**Why they're needed.** Each letter needs its own path so the scatter does not look like a uniform blast. Fixed offsets keep the motion the same every time the script runs.

**How they work.** Each stage multiplies its offset by a `bump` or a ramp, so a letter moves along its own vector and returns.

**Rules.**
- Keep the offsets in the same order as the letters. `SCATTER[2]` belongs to the third letter.
- Keep the scatter and travel offsets inside the frame. A letter that travels off-screen and does not return is lost.

#### 11. `section_chars`: characters (0 to 8 s)

**What it does.** Moves the six letters of `MOTION` through four stages, then leaves them at rest.

**Stage 1 (0 to 2.2 s): rise from below.** Each letter starts 320 px below its final position and rises with `ease_out_cubic`. Letters begin in sequence, 0.18 s apart, from 0.3 s. Scale starts at 60 percent and reaches 100 percent. Opacity is 0 until the letter's start time, so letters do not appear early.

**Stage 2 (2.2 to 4.2 s): spread.** Each letter moves sideways by 130 px times its position from the centre, then returns. The spread is largest for the outer letters.

**Stage 3 (4.2 to 6.2 s): scatter and rotate.** Each letter moves by its `SCATTER` offset and turns 540 degrees, clockwise for even letters and anticlockwise for odd ones. Both use `bump`, so the letters return to rest at the end.

**Stage 4 (6.2 to 7.6 s): curved travel.** Each letter moves along its `TRAJ` offset and a sine bulge `BULGE`. The sine adds a curve to the straight line, so each letter follows its own arc. Both return to rest at 7.6 s.

**Why these four stages.** Each one uses a different kind of movement: entry, spacing, scattering with rotation, and curved travel. That gives the section four distinct techniques while keeping one word.

**Rules.**
- Stage windows must not overlap. Here each one starts after the previous one has returned.
- Every stage uses a term that is zero at its start and end: `bump`, or a ramp that is restored by the next stage. A stage that ends with a displacement leaves the word out of place.
- Keep the word centred at the end of stage 4. The section ends at 8 s, with a 0.4 s hold.

#### 12. `section_words`: words (8 to 16 s)

**What it does.** Moves four words through five motions, then returns them to their asymmetric layout.

**Entry (0 to 2 s).** Each word slides in from the left or right, with a rotation that settles to zero. The words start 0.35 s apart. `ease_out_expo` gives a fast arrival.

**Expand (2 to 3.2 s).** Each word moves outward from the centre, 25 percent of its distance from the centre, and returns.

**Separate and regroup (3.2 to 4.6 s).** Each word moves toward one of the four corners, then returns.

**Spacing change (4.6 to 5.6 s).** `IT` moves 90 px to the right and `CLEAR` 60 px to the left, then both return. This changes the gap between words.

**Vertical stack and back (5.6 to 6.8 s).** All four words move into a left-aligned column, then return. The column's x-position is computed from each word's width, so the left edges align.

**Why these motions.** Each one uses a different movement: slide, radial spread, corner separation, spacing change, and column stacking. None of them repeats the horizontal-to-vertical move of the previous version.

**Rules.**
- Compute the column's x-position from the word's width. A fixed x-position would not align the left edges of words with different widths.
- Each offset is multiplied by `bump`, so the layout returns exactly to its asymmetric arrangement.

#### 13. `section_lines`: lines (16 to 24 s)

**What it does.** Moves three serif lines in from different sides, separates them, and moves them into an asymmetric placement and back to the centred stack.

**Entry (0 to 2.2 s).** `KINETIC` slides in from the left, `TYPE` drops from above with a 0.6 s delay, and `ENGINE` slides in from the right with a 1.2 s delay. `KINETIC` also scales from 80 to 100 percent and turns slightly. `ENGINE` scales down from 120 to 100 percent. `TYPE` has no rotation or scale change.

**Separation (2 to 3.4 s).** The lines move apart vertically by different distances: `KINETIC` up 140 px, `TYPE` not at all, and `ENGINE` down 170 px. The distances are different on purpose, so the separation is uneven.

**Asymmetric placement (3.4 to 4.8 s).** The lines move sideways by different amounts: `KINETIC` 360 px to the left, `TYPE` 260 px to the right, and `ENGINE` 120 px to the left. The composition becomes asymmetric, then returns to the centred stack.

**Why these motions.** The entry uses three directions. The separation is uneven. The asymmetric placement makes the difference between centred and staggered compositions clear, which was a requirement of the brief.

**Rules.**
- Use a different entry direction for each line, so the entries do not look like one repeated move.
- Keep the centred stack as the final state of the section. The alignment section depends on this state.

#### 14. `section_transform`: transformations (24 to 32 s)

This section has two parts, EXPAND and BREAK to BUILD. Their times are local to the section.

**EXPAND (0 to 2 s).** Two stages on the six letters of `EXPAND`:

- **Spread (0 to 1 s).** Each letter moves outward from the centre by up to 55 percent of its distance.
- **Contract (1 to 2 s).** Each letter moves 60 percent of the way toward the focal point `EX_FOCAL` (960, 300), and shrinks to 65 percent of its size.

After 2 s, all six letters are parked, and the word is gone. The letters return to their original spacing during the spread, because the spread is 0 at both ends.

**Why this sequence.** The brief asks for expansion from the centre and contraction toward a point, with the spacing returning to normal. The spread is radial, and the contraction is toward a point above the word, so the two motions are visibly different.

**BREAK to BUILD (2.6 to 8 s).** Five letters of `BREAK` form a readable word, then follow four stages:

| Stage | Local time (s) | What happens |
|---|---|---|
| Separate | 3.0 to 3.8 | Letters spread apart horizontally by 170 px each |
| Travel | 3.8 to 4.4 | Each letter moves along its `BK_TRAVEL` path and turns by its `BK_ROT` |
| Scattered hold | 4.4 to 5.2 | Letters stay scattered and turned. The text changes at 4.9 s |
| Reposition | 5.2 to 6.2 | Letters return to their positions, and `BUILD` is left in place |

**The text change happens while scattered.** The letter values change at 4.9 s, when both `sep` and `traj` are at their peak. The letters are not in their original positions, so the change is visible as a rebuild, not as a text swap in place.

**Why this structure.** The brief requires separation, trajectories, rotation and scaling, repositioning, and then a transformation into the new word, as separate stages. The stages above are those stages, in that order.

**Rules.**
- Change text only while the letters are scattered. The switch at 4.9 s depends on both ramps being at their peak.
- Keep `sep` and `traj` returning to zero by the end of the reposition stage. Otherwise `BUILD` would not sit in its layout position.
- Keep the scale floor (here 0.75 at full travel). Letters that shrink further are hard to read while scattered.

#### 15. `section_align`: alignment (32 to 40 s)

**What it does.** Moves three lines from a centred stack to a left edge at x = 200, and shows a caption once the move has finished.

**The formula.** Each line's centre position is `200 + width / 2`. Its x-position moves from `960` (the centre) to that value, with `ease_in_out` and a delay per line of 0.6, 0.8, and 1.0 s. The lines have different widths, so their centres end at different x-positions, but their left edges all sit at x = 200.

**The caption.** It appears at 2.4 s, after the lines have settled, and sits at the same left edge.

**Why this works.** Because every text object is centred, the left edge is the centre minus half the width. Using the measured width gives an exact left edge.

**Rules.**
- Compute the left-aligned centre from the same measurement used to create the object. A width measured separately would put the edge off by a few pixels.
- Keep the line spacing at a fixed value (here 210 px). Spacing that changes between lines makes the arrangement look unplanned.

#### 16. `animate()`

**What it does.** Calls each section function in order with the current time.

**Why it's needed.** Each section function parks its own objects when it is outside its window. Calling all five each frame lets every section decide for itself, so there is no shared state between them.

**How it works.** It runs `section_chars`, `section_words`, `section_lines`, `section_transform`, and `section_align` at every frame.

**Rules.**
- Keep the call order. The sections do not share objects, so the order does not change the result, but the listing should match the timeline.
- Do not add logic here. Put it in the section it belongs to.

### Rules for kinetic typography in general

1. **Measure and create with the same settings.** Use `make_text`. Never call `add_text` directly for layout text.
2. **Center every text object.** A centre pivot makes rotation and scale behave predictably.
3. **Every offset returns to rest.** Use `bump` or a matching ramp, so the layout is exact at the end of every stage.
4. **Park every section.** An object outside its window is moved to `OFF`, so no leftover text is visible.
5. **Change text only while scattered.** Changing a letter value in its original position looks like a cut, not a rebuild.
6. **Vary the easing.** Each section uses a different curve, so the motion vocabulary changes from section to section.
7. **Keep the final state readable.** Every section must end with its text at rest and in a clear layout.

### What this is designed for

A reference for kinetic typography techniques. Each section is one technique family: character-level assembly, word-level composition, line-level stacking, letter-level transformation, and alignment change. Each is a separate function, so one can be copied into a project without the others.

It is not designed for body text, long passages, or text that must be edited at run time. Each letter and word is its own object, so a long paragraph would need many more objects and a different layout approach.

### Known limits

- **Each letter and word is its own object.** No per-character object is documented, so a word with many letters creates many objects.
- **Kerning is not applied.** Letter spacing is the sum of the measured glyph widths. Some letter pairs will look slightly looser or tighter than normal.
- **Font availability depends on the machine.** A style falls back to Arial when its preferred font is not installed. The variety in the video then depends on what is available.
- **Alignment is shown by moving centres.** The `align` setting is fixed when an object is created, so the left-aligned state is produced by positioning, not by changing the alignment property.
- **The caption is a separate object.** It is not part of the alignment, so it does not move with the lines.

### Checks run

- Every text object's font, bold setting, and size match the values recorded when it was created.
- No non-finite values in any object across 1,201 frames.
- Objects are parked at each section boundary: characters after 8 s, words before 8 s, lines after 24 s, EXPAND letters after 26 s, BREAK letters before 26.6 s, alignment lines before 32 s.
- The final left edges of the three alignment lines are exactly 200 px, and the caption's left edge is 200 px.
- BREAK changes to BUILD as expected: the second letter switches from R to U at 5.0 s, after the letters have moved apart.

### Not yet verified in MotionCode

- `list_fonts()` returns the names used in `FONT_PICKS`, so the intended fonts are actually used.
- `align="center"` makes rotation and scale pivot about the glyph centre.
- `measure_text` returns the same width as the rendered text.
- Setting `.text` on an existing object changes its rendered text without recreating it.
- Opacity on text behaves as documented.

---

## Shared rules for both scripts

1. **One script, one file.** Each script runs alone. Neither refers to the other or to any helper file.
2. **Absolute values in `animate()`.** Each frame sets positions from `t`. Nothing is added to the previous frame.
3. **Hide with position, not opacity.** Inactive objects move to `OFF`. Opacity is reserved for deliberate layer effects.
4. **Name everything uniquely.** Duplicate names raise an error.
5. **Test before presenting.** Compile the script and run it across every frame before a long export.



---


# Source: Camera-Cinematic.md

# Camera & Cinematic Examples

Source: MotionCode-DataBase, Camera & Cinematic. Two self-contained scripts: paste each into the Video script editor and click Apply Code. No other file is needed.

## Camera on a Spline with Constant Speed

**File:** `example_camera_spline.py`

### Code

```python
"""CAMERA ON A SPLINE: a 3D camera flies a closed loop at constant speed, looks ahead along
the path and rolls gently. The path is a Catmull-Rom spline, arc-length parameterised,
so the camera covers equal distance in equal time. Simulated once from t = 0."""
import math
import bisect

FOCAL = 900.0          # focal length in px
CX, CY = 960.0, 540.0  # screen centre
WORLD_UP = (0.0, 1.0, 0.0)
SPEED = 260.0          # arc length per second, px
LOOK_AHEAD = 350.0     # the camera looks this far ahead along the path
ROLL_DEG = 6.0         # maximum roll, degrees
SIM_SECONDS = 10

ROUTE = [(-600, 260, -900), (0, 320, -300), (700, 260, -100), (500, 420, 500),
         (-200, 300, 700), (-800, 240, 300), (-900, 280, -400)]   # closed loop

SPHERES = [((-300, 60, 200), 60, "#FF8A5B"), ((300, 40, -200), 40, "#FFD166"),
           ((650, 70, 250), 70, "#70D6FF"), ((-600, 50, -300), 50, "#7CFFB2"),
           ((100, 35, 500), 35, "#E0457B"), ((0, 80, -700), 80, "#35B9FF")]

_ARC_U = []    # parameter at each arc sample
_ARC_S = []    # cumulative arc length at each sample
ARC_TOTAL = 0.0


def _catmull(p0, p1, p2, p3, u):
    u2, u3 = u * u, u * u * u
    return tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * u
                        + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * u2
                        + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * u3) for k in range(3))


def route_point(u):
    """Point on the closed spline at parameter u (segment index plus fraction)."""
    n = len(ROUTE)
    i = int(math.floor(u))
    f = u - i
    return _catmull(ROUTE[(i - 1) % n], ROUTE[i % n], ROUTE[(i + 1) % n], ROUTE[(i + 2) % n], f)


def build_arc(per_segment=80):
    """Sample the spline densely and record cumulative length, to map distance to parameter."""
    global ARC_TOTAL
    n = len(ROUTE)
    _ARC_U[:] = [k * n / float(n * per_segment) for k in range(n * per_segment + 1)]
    _ARC_S[:] = [0.0]
    prev = route_point(0.0)
    for u in _ARC_U[1:]:
        p = route_point(u)
        _ARC_S.append(_ARC_S[-1] + math.dist(prev, p))
        prev = p
    ARC_TOTAL = _ARC_S[-1]


def u_at_arc(s):
    """Parameter where the path has travelled arc length s (wraps around the loop)."""
    s = s % ARC_TOTAL
    k = bisect.bisect_right(_ARC_S, s) - 1
    k = min(max(k, 0), len(_ARC_S) - 2)
    span = _ARC_S[k + 1] - _ARC_S[k]
    f = 0.0 if span <= 0 else (s - _ARC_S[k]) / span
    return _ARC_U[k] + (_ARC_U[k + 1] - _ARC_U[k]) * f


def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a):
    l = math.sqrt(dot(a, a)) or 1e-9
    return (a[0] / l, a[1] / l, a[2] / l)


def camera_at(t):
    """Camera position, look-at basis (forward, right, up) with roll, at time t."""
    s = SPEED * t
    pos = route_point(u_at_arc(s))
    target = route_point(u_at_arc(s + LOOK_AHEAD))
    fwd = norm(sub(target, pos))
    right = norm(cross(fwd, WORLD_UP))
    up = cross(right, fwd)
    roll = math.radians(ROLL_DEG * math.sin(t * 0.7))
    c, sn = math.cos(roll), math.sin(roll)
    right, up = (tuple(c * right[k] + sn * up[k] for k in range(3)),
                 tuple(-sn * right[k] + c * up[k] for k in range(3)))
    return pos, fwd, right, up


def project(p, cam):
    """Perspective projection to the screen. Returns (x, y, depth)."""
    pos, fwd, right, up = cam
    d = sub(p, pos)
    z = max(dot(d, fwd), 0.5)
    return (CX + FOCAL * dot(d, right) / z, CY - FOCAL * dot(d, up) / z, z)


def build(scene):
    build_arc()
    scene.background = "#080D18"
    scene.duration = SIM_SECONDS
    scene.fps = 30
    # Ground grid: each line is a 3D segment drawn as a 2-point polyline
    for i, g in enumerate(range(-1000, 1001, 200)):
        scene.add_polyline("Grid X %02d" % i, points=[(0, 0), (0, 0)], x=0, y=0, color="#1B2A44", stroke=2)
        scene.add_polyline("Grid Z %02d" % i, points=[(0, 0), (0, 0)], x=0, y=0, color="#1B2A44", stroke=2)
    scene.add_polyline("Path", points=[(0, 0)] * 120, x=0, y=0, color="#2F4A7A", stroke=3)
    for i, (p, r, color) in enumerate(SPHERES):
        scene.add_circle("Sphere %02d" % i, x=0, y=0, radius=r, color=color, filled=True, stroke=2)
    scene.add_text("Status", "", x=960, y=980, size=30, color="#9FB4FF")


def animate(scene, t):
    cam = camera_at(t)
    grid = range(-1000, 1001, 200)
    for i, g in enumerate(grid):
        a = project((g, 0, -1000), cam)
        b = project((g, 0, 1000), cam)
        scene.get("Grid Z %02d" % i).points = [(a[0], a[1]), (b[0], b[1])]
        a = project((-1000, 0, g), cam)
        b = project((1000, 0, g), cam)
        scene.get("Grid X %02d" % i).points = [(a[0], a[1]), (b[0], b[1])]
    path = []
    for k in range(120):
        p = project(route_point(k * len(ROUTE) / 120.0), cam)
        path.append((p[0], p[1]))
    scene.get("Path").points = path
    for i, (p, r, _) in enumerate(SPHERES):
        x, y, z = project(p, cam)
        s = scene.get("Sphere %02d" % i)
        s.x, s.y = x, y
        s.radius = max(2.0, FOCAL * r / z)
    s_now = SPEED * t
    scene.get("Status").text = "arc length %.0f px of %.0f   speed %.0f px/s" % (s_now % ARC_TOTAL, ARC_TOTAL, SPEED)
```

### What it shows

A camera flies a closed 3D loop past six spheres and a ground grid. It moves at a steady 260 px per second of arc length, looks ahead along the path, and rolls gently. A faint line shows the path, and the status line reports the distance travelled.

### How it is made

The route is a closed Catmull-Rom spline through seven points. build_arc() samples it densely and stores the cumulative length. u_at_arc(s) uses bisection on that table to turn a distance into a spline parameter, so equal time means equal distance. The camera position is the spline at s, and the look-at target is the spline at s + 350 px. The forward, right and up vectors are built from the target, and roll rotates right and up around forward. project() is a perspective projection to screen space.

### Why it is made this way

Constant speed is the point of the arc-length table: a spline indexed by a raw parameter speeds up in tight corners and slows on long straights, which makes a camera look wrong. The measured speed stays within about 1% of 260 px/s. Looking ahead along the path, and rolling a few degrees, is what makes the move feel like a real camera rather than a sliding cursor.


## Real Shadows from a Moving Light

**File:** `example_real_shadows.py`

### Code

```python
"""REAL SHADOWS: a point light moves in a circle above the ground. Each frame, every ground
sample point casts a ray toward the light and is tested against each sphere. Points whose
ray is blocked are dark. The spheres bob, so the shadows move with them. Ray tests on the
ground only; spheres do not shadow each other. Simulated per frame, no shadow map."""
import math

CX, CY = 960.0, 540.0
FOCAL = 900.0
CAM_Z = -1400.0              # the camera sits in front, looking down the z axis
SIM_SECONDS = 8
GROUND_Y = 0.0
GX = range(-600, 601, 60)    # ground samples
GZ = range(200, 1001, 70)
LIGHT_RADIUS = 700.0
LIGHT_HEIGHT = 900.0
SPHERES = [((-300, 0, 500), 90, "#FF8A5B"), ((220, 0, 700), 120, "#FFD166"),
           ((-60, 0, 900), 60, "#70D6FF")]
BOB = 40.0                   # how far each sphere bobs up and down
OFF = -6000


def light_at(t):
    return (LIGHT_RADIUS * math.cos(t * 0.7), LIGHT_HEIGHT, 500 + LIGHT_RADIUS * math.sin(t * 0.7))


def sphere_centre(i, t):
    (x, _, z), r, _ = SPHERES[i]
    y = r + BOB * max(0.0, math.sin(t * 1.3 + i))   # bob above the ground, never below it
    return (x, y, z), r


def shadowed(p, light, t):
    """True if the segment from ground point p to the light passes through any sphere."""
    dx, dy, dz = light[0] - p[0], light[1] - p[1], light[2] - p[2]
    for i in range(len(SPHERES)):
        c, r = sphere_centre(i, t)
        fx, fy, fz = p[0] - c[0], p[1] - c[1], p[2] - c[2]
        a = dx * dx + dy * dy + dz * dz
        b = 2 * (fx * dx + fy * dy + fz * dz)
        cc = fx * fx + fy * fy + fz * fz - r * r
        disc = b * b - 4 * a * cc
        if disc < 0:
            continue
        s = math.sqrt(disc)
        t1 = (-b - s) / (2 * a)
        t2 = (-b + s) / (2 * a)
        if 0.0 < t1 < 1.0 or 0.0 < t2 < 1.0:    # hit between the ground point and the light
            return True
    return False


def screen(p):
    z = max(p[2] - CAM_Z, 1.0)
    return CX + FOCAL * p[0] / z, CY + FOCAL * (p[1] - 500) / z, z


def build(scene):
    scene.background = "#080D18"
    scene.duration = SIM_SECONDS
    scene.fps = 30
    for i, gx in enumerate(GX):
        for j, gz in enumerate(GZ):
            scene.add_circle("Lit %02d %02d" % (i, j), x=OFF, y=OFF, radius=6, color="#2F4A7A",
                             filled=True, stroke=0)
            scene.add_circle("Dark %02d %02d" % (i, j), x=OFF, y=OFF, radius=6, color="#02050B",
                             filled=True, stroke=0)
    for i, (_, _, color) in enumerate(SPHERES):
        scene.add_circle("Sphere %02d" % i, x=OFF, y=OFF, radius=10, color=color, filled=True, stroke=2)
    scene.add_circle("Light", x=OFF, y=OFF, radius=14, color="#FFFFFF", filled=True, stroke=0)
    scene.add_text("Status", "", x=960, y=980, size=30, color="#9FB4FF")


def animate(scene, t):
    light = light_at(t)
    lx, ly, lz = screen(light)
    light_dot = scene.get("Light")
    light_dot.x, light_dot.y, light_dot.radius = lx, ly, 14
    blocked = 0
    total = 0
    for i, gx in enumerate(GX):
        for j, gz in enumerate(GZ):
            p = (gx, GROUND_Y, gz)
            sx, sy, sz = screen(p)
            r = FOCAL * 30 / sz
            dark = scene.get("Dark %02d %02d" % (i, j))
            lit = scene.get("Lit %02d %02d" % (i, j))
            total += 1
            if shadowed(p, light, t):
                blocked += 1
                dark.x, dark.y, dark.radius = sx, sy, r
                lit.x, lit.y, lit.radius = OFF, OFF, 6
            else:
                lit.x, lit.y, lit.radius = sx, sy, r
                dark.x, dark.y, dark.radius = OFF, OFF, 6
    for i in range(len(SPHERES)):
        c, r = sphere_centre(i, t)
        sx, sy, sz = screen(c)
        s = scene.get("Sphere %02d" % i)
        s.x, s.y, s.radius = sx, sy, FOCAL * r / sz
    scene.get("Status").text = "ground in shadow: %d of %d points" % (blocked, total)
```

### What it shows

A point light circles above the ground, and three spheres bob up and down. Each ground sample point is either lit (blue) or in shadow (near black), so the shadows move with the light and the spheres every frame.

### How it is made

Each ground sample (a 21 by 11 grid) casts a ray toward the light. shadowed() solves the ray-sphere intersection for each sphere and reports a hit when the entry or exit point lies between the ground and the light. Sample points in shadow are drawn as dark dots and lit ones as blue dots, with the unused set parked off screen. The spheres bob with max(0, sin(...)) so they never go below the ground.

### Why it is made this way

The ray test is exact for spheres and needs no shadow map, which keeps the code self-contained and works without a 3D renderer. The trade-off is that shadows fall only on the ground: spheres do not shadow each other, and dots are a coarse sample of a shadow edge. A shadow map would give smoother edges but needs a depth buffer that this scene API does not provide.



---


# Source: Audio-Database.md

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


---
