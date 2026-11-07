# MotionCode Reference

## Description

MotionCode is a motion graphics application. A motion graphic is written as two short
scripts: a video script that creates and animates shapes, text and 3D objects, and an audio
script that builds the sound. The app runs both on the same timeline, shows the result in a
live preview, and exports finished video, GIF, image sequence or audio files.

## Owner

**Vince Winter**

## Start here

If you want to understand the app without code, open **Basic.md**. It explains every task
in plain language: changing the motion and sound, the theme, settings, export, saving,
opening projects, fonts, credits and the Data folder.

This document is the detailed reference. It lists every public name a script can use.

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

This reference lists the names, arguments and rules. It does not explain how to combine them into
a good animation. To understand the whole system, including how the parts interact, how an
animation is built step by step, and how to debug it, use an AI assistant that can read the
MotionCode source files and this document together.

---

## Reference: scene and objects

### Scene settings (set in `build`)

| Name | Meaning |
|------|---------|
| `duration` | Length in seconds |
| `fps` | Frames per second |
| `width`, `height` | Picture size in pixels (default 1920 × 1080) |
| `background` | Background colour, `#RRGGBB` |
| `background_gradient` | A gradient for the background |
| `lights`, `ambient` | Point lights and base brightness |
| `motion_blur_samples` | Maximum motion blur sub-frames |
| `camera_x`, `camera_y`, `camera_z`, `camera_fov` | Camera for 3D objects |
| `bloom`, `bloom_threshold`, `bloom_radius` | Glow on bright areas |
| `vignette`, `grain`, `aberration` | Dark edges, film grain, colour fringing |
| `grade`, `grade_strength` | Colour tint over the whole frame |

### Scene methods

| Name | Meaning |
|------|---------|
| `get(name)` | The object with this name. Fails if it does not exist |
| `get_optional(name)` | The object, or nothing |
| `keyframes(target, property, points, ease)` | Animate a number between timed points |
| `clear_keyframes(target, property)` | Remove keyframes |
| `bring_to_front(name)`, `send_to_back(name)` | Change the layer |
| `measure_text(text, size, font, bold, max_width)` | Width and height of text in pixels |
| `list_fonts()` | Installed font family names |
| `define_preset(name, **settings)` | Save a group of scene settings under a name |
| `apply_preset(name)` | Apply a saved group |

### Shapes (adding objects)

| Name | Meaning |
|------|---------|
| `add_circle` | Circle, with `radius` |
| `add_rect` | Rectangle, with `width` and `height` |
| `add_rounded_rect` | Rectangle with rounded corners, with `radius` |
| `add_ellipse` | Ellipse, with `radius_x` and `radius_y` |
| `add_star` | Star, with `points`, `outer_radius`, `inner_radius` |
| `add_polygon` | Closed shape from a list of points |
| `add_polyline` | Open path from a list of points |
| `add_line` | Line from its start point, with `x2` and `y2` for the end |
| `add_text` | Text, with `size`, `font`, `bold`, `align`, `max_width` |
| `add_image` | Picture file, with `width` and `height` |
| `add_cube`, `add_sphere`, `add_pyramid`, `add_cone`, `add_cylinder`, `add_torus`, `add_plane` | 3D shapes, with `size` (cone and cylinder use `radius` and `height`) |
| `add_obj` | 3D model file, with `scale` and `filled` |
| `add_wireframe(vertices, edges)` | Your own 3D wireframe |

### Object properties

| Name | Meaning |
|------|---------|
| `x`, `y`, `z` | Position. `z` is depth for 3D |
| `color`, `stroke`, `filled` | Colour, outline width, solid or outline |
| `opacity` | 0 to 1 |
| `scale`, `scale_x`, `scale_y` | Size, uniform or per axis |
| `rotation_z` (also `rotation`) | Turn in degrees, clockwise positive |
| `rotation_x`, `rotation_y` | Tilt for 3D objects, in degrees |
| `skew_x` | Slant in degrees |
| `parent` | Follow another object |
| `blur`, `backdrop_blur`, `motion_blur` | Soft edge, frosted background, motion smear |
| `blend` | `normal`, `add`, `screen` or `multiply` |
| `shadow` | Drop shadow settings |
| `gradient` | Colour gradient on a filled shape |
| `lit` | Receives light from `lights` |

### Easing names

Used by `keyframes`, `ease=`: `linear`, `ease_in`, `ease_out`, `ease_in_out`, or your own curve
built with `curve(points)`.

---

## Reference: transitions

Import as `transitions`.

| Name | Meaning |
|------|---------|
| `enter(obj, t, start, duration, style, base, distance)` | Bring an object in |
| `exit(obj, t, start, duration, style, base, distance)` | Take an object out |
| `visible_between(t, a, b, fade)` | Fade in and out between two times |
| `fade_in`, `fade_out` | Opacity over time |
| `slide_offset`, `pop_scale`, `zoom_scale` | Single values for custom motion |

Styles: `fade`, `slide_left`, `slide_right`, `slide_up`, `slide_down`, `pop`, `zoom`.

---

## Reference: effects and styles (FeaturesPro)

Import as `pro` (module `FeaturesPro`).

### Styles

`Styled(scene, name, shape, style, text, **settings)`. Shapes: `circle`, `rect`, `rounded_rect`,
`ellipse`, `star`, `text`. Styles: `none`, `neon`, `brutal`, `paper`, `deco`, `holo`, `blueprint`,
`isometric`, `handdrawn`, `pixel`.

### Building helpers

| Name | Meaning |
|------|---------|
| `Gradient(stops, kind, angle, center, radius)` | Colour gradient, `linear` or `radial` |
| `Light(x, y, radius, intensity, color)` | Soft point light |
| `liquid(scene, name, cx, cy, radius, ...)` | Wobbling blob |
| `kinetic(scene, name, text, cx, cy, ...)` | Letters that rise in turn |
| `split_flap(scene, name, states, cx, cy, ...)` | Departure-board letters |
| `bounce(scene, name, shape, x, drop_y, floor_y, ...)` | Object that falls and bounces |
| `grid(scene, name, step, color, width, area)` | Blueprint grid |
| `deco_frame(scene, name, cx, cy, width, height, ...)` | Art Deco frame with sunburst |
| `dimension(scene, name, x1, y1, x2, y2, ...)` | Measurement line with label |
| `stroke_draw(scene, name, points, t_start, duration, ...)` | Outline drawn progressively |
| `pixel_sprite(scene, name, bitmap, cx, cy, ...)` | Pixel art from text rows |
| `iso_box(scene, name, cx, cy, ...)` | Isometric box |
| `paper_sheet(scene, name, cx, cy, w, h, ...)` | Cut-paper sheet |
| `caption(scene, name, text, cx, y, start, end, ...)` | Text that fades in and out |
| `emitter(scene, name, x, y, ...)` | Continuous particles |
| `Burst(prefix, x, y, t0, ...)` | One-off particle burst |
| `Trail(prefix, pos_fn, ...)` | Ghost copies following a point |
| `mask(scene, shape_name, mode, targets, strength, color, feather)` | Hide, blur or tint what is behind a shape |
| `layer(scene, name, keys, ease)` | Move an object through the layer order over time |

### Per-frame helpers

| Name | Meaning |
|------|---------|
| `update_all(scene, t)` | Update all FeaturesPro objects. Call last in `animate` |
| `set_quality(key)` | Set Resolution elements: `very_low`, `low`, `medium`, `balanced`, `high`, `ultra` |
| `set_pixel_palette(name)` | `mint`, `retro` or `mono` |
| `ease_out_cubic`, `ease_in_out_cubic`, `ease_out_back`, `ease_out_elastic`, `ease_out_bounce` | Easing curves |
| `progress(t, start, duration, ease)` | Eased 0 to 1 progress |
| `spring`, `squash_stretch` | Springy motion and squash |
| `shake`, `wobble`, `flash` | Shake, sway and flash |
| `typed(text, t, start, chars_per_second)` | Typewriter text |
| `word_reveal(words, t, start, per_word)` | Word-by-word reveal |
| `velocity_stretch(vx, vy, amount, max_stretch)` | Stretch along movement |

---

## Reference: sound (audio script)

The audio script receives one object, `audio`, in `build_audio(audio)`.

### Audio settings

| Name | Meaning |
|------|---------|
| `duration` | Length in seconds. Keep equal to the video |
| `sample_rate` | Sample rate, default 44100 |
| `master_volume` | Overall level |

### Audio methods

| Name | Meaning |
|------|---------|
| `add_tone(name, freq, start, length, volume, fade_in, fade_out, wave, pan)` | A pure tone |
| `add_mood(name, mood, start, length, base_freq, volume, fade_in, fade_out, pan)` | A background bed with a mood |
| `add_noise(name, start, length, volume, fade_in, fade_out, pan)` | Hiss or texture |
| `add_click(name, at, volume, freq, pan)` | Short click |
| `add_clip(name, path, at, volume)` | Sound file from the Data or assets folder |

Moods: `happy`, `sad`, `calm`, `quiet`, `soft`, `loud`, `excited`, `tense`, `neutral`.
Waves: `sine`, `square`, `triangle`, `saw`. Pan: -1 is full left, 0 centre, +1 full right.

---

## Reference: export

| Setting | Options |
|---------|---------|
| File type (video) | MP4, MOV, MKV, WebM, GIF |
| File type (audio) | WAV, FLAC, M4A, MP3, OGG, Opus |
| File type (images) | PNG frames |
| Resolution | 4K, 2K, 1080p, 1K, 720p, 480p, 360p, square 1080, vertical 1080 × 1920 |
| FPS | 15 to 120 |
| Resolution elements | Ultra, High, Balanced, Medium, Low, Very low |
| Compression | Lossless, High, Standard, Small, Tiny (lower CRF is better) |
| Encoder | CPU (libx264) or NVIDIA (h264_nvenc) |

Video is H.264 (WebM uses VP9) in 4:2:0 with BT.709 colour tags. The audio track is chosen
automatically for each file type. Export settings and the last save folder are saved to
`export_settings.json` in the Data folder.

---

## Reference: files and folders

| Item | Meaning |
|------|---------|
| `.mcp` | Project file with both scripts |
| `Data/` | Settings, cache, projects, fonts, assets, 3D models, credits and licences |
| `Data/CREDITS.md` | Credits text, opened from the Credits menu |
| `Data/LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md` | Licence files |
| `Data/cache/` | Automatic backups of scripts |
| `Data/fonts/` | Installed fonts (`.ttf`, `.otf`) |
| `Data/assets/` | Imported sound and image files |

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
