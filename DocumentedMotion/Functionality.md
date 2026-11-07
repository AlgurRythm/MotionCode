# MotionCode Function Guide

Each entry gives a short description, then a detailed one, then what the function specializes in. Paste any script into the matching editor and click Apply Code. Set the video duration to the length listed for that script.

---

## Part 1: Physics and Simulation

Each physics script simulates once, from t = 0, inside `build()`. Frames are stored 120 times per second, and `animate()` reads them back, so scrubbing, playback and export match.

### Rigid Collisions (`example_physics_collisions.py`, 9 s)

**`RigidCircles(left, top, right, bottom, gravity, restitution, friction, iterations)`**
Creates the box and the physics settings.
Sets the box edges, how hard gravity pulls, how bouncy circles are (`restitution`), how much they grip (`friction`), and how many correction passes run each step. More passes keep stacks from sinking.
*Specializes in:* the box and the rules that every circle in it follows.

**`add(x, y, r, vx, vy)`**
Adds one circle.
Mass is set by area, so bigger circles are heavier. Starting velocity is optional.
*Specializes in:* placing circles with their size and starting motion.

**`run(seconds)`**
Runs the whole simulation.
Steps forward at 1/240 second each, stores frames, and does the work up front so the preview never stutters.
*Specializes in:* turning the setup into a stored timeline.

**`sample(t)`**
Returns where each circle is at time t.
Gives x, y and spin angle for every circle, blended between the two nearest stored frames.
*Specializes in:* reading the timeline smoothly at any moment.

**`_walls` and `_pair`**
Handle contact with the box, and contact between two circles.
`_walls` bounces circles off the floor and sides, and `_pair` pushes overlapping circles apart and exchanges momentum. Both apply friction at the contact point, which is what makes circles roll.
*Specializes in:* bounce, stacking and rolling.

### Cloth (`example_physics_cloth.py`, 10 s)

**`Cloth(cols, rows, spacing, origin, gravity, iterations, damping, pin)`**
Creates a grid of points joined by springs.
Sets the grid size, the spacing, gravity, how stiff the cloth is (`iterations`), how quickly swinging dies out (`damping`), and the function that moves the top edge.
*Specializes in:* fabric that hangs and sways.

**`run(seconds)`**
Simulates the cloth.
Uses Verlet integration, which means each point's velocity is implied by where it was last step. Springs are pushed back to their rest length each pass, and the top row follows the `pin` function.
*Specializes in:* stable motion of a stretchy grid.

**`sample(t)`**
Returns the position of every point at time t.
*Specializes in:* reading the cloth at any moment.

**`index(c, r)`**
Converts a column and row into a point number.
Use it to find a point in the list `sample()` returns.
*Specializes in:* finding points by position in the grid.

**`pin(t)`**
Returns how far the top edge has moved at time t.
Here it is a gentle side-to-side sway that starts from rest.
*Specializes in:* driving the cloth from its top edge.

### Fluid Particles (`example_physics_fluid.py`, 8 s)

**`Fluid(wall, radius, gravity, restitution)`**
Creates the particle system and tank.
Sets the tank edges, particle size, gravity, and how bouncy the floor is.
*Specializes in:* a container of particles that falls and splashes.

**`add_block(x, y, cols, rows, vx, vy, spacing, jitter)`**
Adds a rectangular block of particles.
Each particle gets a random sideways push from a fixed seed, so the splash repeats exactly every run. `jitter` sets how wide that push is.
*Specializes in:* making a splash spread out instead of sliding as one slab.

**`run(seconds)`**
Steps the particles forward and stores their positions.
*Specializes in:* producing the splash timeline in one pass.

**`_collide`**
Pushes overlapping particles apart and reduces their approach speed.
It sorts particles into grid cells, so each particle only checks its nine neighbouring cells instead of every other particle.
*Specializes in:* keeping a large particle count fast.

**`_walls`**
Keeps particles inside the tank and bounces them off the edges.
*Specializes in:* containing the splash.

This is a particle approximation that gives a liquid look. It does not model pressure or surface tension.

---

## Part 2: Transitions Showcase (`transitions_showcase.py`, 40 s)

Ten full-frame colour plates are stacked. Each transition moves one plate away, or grows a new shape over the current one. The reference does not document true masks, so every reveal is a moved or morphed plate.

**`prog(t, start, dur)`**
Converts time into a 0 to 1 value over a window.
Returns 0 before the window, 1 after it, and a steady rise in between.
*Specializes in:* timing every transition from one shared function.

**`ease_in_out(p)`**
A smooth curve that starts slowly, speeds up, then slows at the end.
*Specializes in:* natural-feeling slides.

**`ease_in_back(p)`**
A curve that pulls back slightly before it moves forward.
*Specializes in:* anticipation, used for the first transition's exit.

**`rect_pts`, `circle_pts`, `star_pts`**
Return the outline points for a rectangle, a circle and a five-point star.
The points are relative to the shape's centre.
*Specializes in:* the three shapes the morphs use.

**`resample(points, n)`**
Spaces `n` points evenly along an outline, whatever its original point count.
*Specializes in:* giving two different shapes the same number of points so they can morph.

**`align_closed(ref, pts)`**
Chooses the start point and direction that keep each point closest to its partner.
*Specializes in:* stopping a morph from twisting.

**`morph(a, b, p)`**
Blends two matched outlines at progress `p`.
At 0 you get shape a, at 1 you get shape b.
*Specializes in:* turning a rectangle into a disc or a star into a rectangle.

**`place(scene, name, x, y, points, rot, scale, opacity)`**
Sets position, rotation, scale, opacity and outline for one object in one call.
*Specializes in:* keeping every transition setting the same set of properties.

**`wave_points(p)`**
Builds a plate outline whose left edge is a wave that sweeps across.
*Specializes in:* the directional wipe in slot 6.

**`sec0` to `sec8`**
One function per transition slot. Each sets its plates and returns the plate underneath and the moving objects.
- `sec0`: horizontal exit with anticipation.
- `sec1`: vertical exit.
- `sec2`: diagonal exit with rotation.
- `sec3`: rectangle shrinks into a disc.
- `sec4`: star grows into a full plate.
- `sec5`: plate splits into six strips.
- `sec6`: wavy edge sweeps across.
- `sec7`: three bars leave, one with an opacity dip.
- `sec8`: rotation and scale exit.

**`animate(scene, t)`**
Chooses the slot for the current time, runs its function, moves inactive objects to the offscreen spot, and brings the active plates to the front in order.
*Specializes in:* running one transition at a time with a clean layer order.

**Known limits:** slot 3 is a shrinking outline, not an iris mask. Plate 8 is never parked after slot 8. Layer order depends on `bring_to_front`, which is not yet verified in MotionCode.

---

## Part 3: Kinetic Typography (`kinetic_typography.py`, 40 s)

Five sections of 8 seconds each. Each section parks its own text when it is not active.

**`make_text(scene, name, text, size, style, bold, color, section)`**
Creates a text object and records its font, size and measured width.
Always create layout text through this function, so measuring and creating use the same settings.
*Specializes in:* keeping layout measurements exact.

**`pick_font(scene, style)`**
Returns the first installed font from the style's list, falling back to Arial.
*Specializes in:* giving each section its own look on any machine.

**`measure(scene, text, size, style, bold)`**
Returns the width of text in a given style.
*Specializes in:* sizing letters before they are placed.

**`set_pose(scene, name, x, y, rot, scale, op, text)`**
Sets position, rotation, scale, opacity and, when it changes, the text.
*Specializes in:* updating a text object in one call.

**`park_section` and `park_names`**
Move text objects to the offscreen spot.
*Specializes in:* cleaning up a section when its time window ends.

**`bump(t, start, dur)`**
Rises from 0 to 1 at the midpoint, then falls back to 0.
*Specializes in:* offsets that must return exactly to rest. Use it whenever a motion should end where it began.

**`ease_out_cubic`, `ease_out_expo`, `ease_out_back`**
Settle curves for entries. Cubic eases gently, expo arrives quickly, and back overshoots slightly before settling.
*Specializes in:* giving each section a different arrival feel.

**`section_chars` (0 to 8 s)**
Builds the word MOTION in four stages: rise from below, spread apart, scatter and rotate, then travel along curves. Every letter returns to its spot.
*Specializes in:* letter-by-letter assembly.

**`section_words` (8 to 16 s)**
Moves four words through entry, expansion, separation, spacing change and a vertical stack.
*Specializes in:* asymmetric word composition.

**`section_lines` (16 to 24 s)**
Brings three serif lines in from three directions, separates them unevenly, then places them asymmetrically.
*Specializes in:* line-level stacking and staggered layouts.

**`section_transform` (24 to 32 s)**
EXPAND spreads its letters from the centre, then pulls them toward a focal point. BREAK to BUILD separates its letters, rotates and scales them, changes the text while they are scattered, and reassembles them.
*Specializes in:* letter transformation and text change.

**`section_align` (32 to 40 s)**
Moves three lines from a centred stack to a shared left edge at x = 200, then shows a caption.
*Specializes in:* alignment changes made by moving centres.

Known limits: each letter and word is its own object, kerning is not applied, and the look depends on installed fonts.

---

## Part 4: Motion-Examples

**`bezier(p, u)`**
Returns a point on a cubic Bezier curve at fraction `u`.
*Specializes in:* smooth curves defined by four control points.

**Arc-length table (`TABLE`, `CURVE_LENGTH`)**
Maps distance along the curve to a position.
*Specializes in:* constant-speed motion. A Bezier parameter alone does not move at a steady speed.

**`point_at_distance(s)`**
Returns the position after `s` pixels along the curve, wrapping at the end.
*Specializes in:* looping a ball along a path at a steady speed.

**Path motion: `build()` and `animate()`**
`build()` measures each letter and creates the ring guide, the curve guide and the ball. `animate()` places each letter around a ring, turns it to follow the ring, and aims the heading line along the curve.
*Specializes in:* text that follows a circle with correct spacing.

**`edge_points(a, b)`**
Returns the start and end points on the box edges for an arrow between two boxes.
*Specializes in:* arrows that leave and enter boxes cleanly, whichever way they point.

**Layout motion: `build()` and `animate()`**
`build()` creates boxes, labels, arrows and arrowheads. `animate()` builds the boxes in sequence, grows each arrow once both ends are in place, and moves a token along the route.
*Specializes in:* flow diagrams that build themselves.

**`solve_two_bone(sx, sy, tx, ty, l1, l2, flip)`**
Returns the two angles that reach a target from a root with two bones.
`flip=False` bends forward (knees), and `flip=True` bends backward (elbows).
*Specializes in:* natural limb bending.

**`reach_error(...)`**
Returns how far a limb ends from its target.
*Specializes in:* checking that a limb actually reaches where it should.

**`foot_target(u, offset)`**
Returns where a foot should be during a walk cycle. It slides on the ground for 60 percent of the cycle, then lifts in an arc for the other 40 percent.
*Specializes in:* walking feet that plant and step.

**`make_chain(...)` and `set_chain(...)`**
Build a limb from an upper bone, lower bone and joint, then drive it toward a target each frame. Feet stay level.
*Specializes in:* stick-figure limbs that follow a moving root.

**Character motion: `animate()`**
Drives the hip bob, torso sway, legs and arms. Arms swing opposite the legs, and the status line shows the largest reach error.
*Specializes in:* a walk cycle with weight and timing.

---

## Part 5: Audio and Camera (earlier examples)

**Audio songs.** Each song is a `build_audio(audio)` function that sets `audio.duration` and adds tones, noise and clicks.
- Glass Bells (24 s): sine bells, panned, ringing over a pentatonic melody. Specializes in clean, bright tones.
- Pulse Engine (16 s): 150 BPM beat with a kick, square bass, hi-hats and a lead. Specializes in rhythm.
- Warm Sunrise (24 s): slow chord pads with a triangle melody. Specializes in soft fades.
- Retro Arcade (16 s): square-wave arpeggio over a triangle bass. Specializes in chiptune sound.
- Deep Space (30 s): sawtooth drone with moving shimmer and noise swells. Specializes in space textures.
- Music Box Lullaby (20 s): triangle plucks with an octave shimmer. Specializes in gentle, sparse tunes.

**`example_camera_spline.py` (10 s).** A 3D camera follows a closed Catmull-Rom spline at constant speed. `build_arc()` measures the path length, `u_at_arc(s)` converts distance to a path position, `camera_at(t)` builds the camera's view, and `project(p, cam)` projects 3D points to the screen. Specializes in smooth fly-throughs with look-ahead and roll.

**`example_real_shadows.py` (8 s).** A point light circles above a ground grid. `shadowed(p, light, t)` tests whether each ground point's ray to the light hits a sphere. Specializes in shadows that move with the light and the spheres, without a shadow map. Shadows fall only on the ground and edges are coarse.

---

## Notes

- Transitions and kinetic typography were tested with a mock scene. Run them in MotionCode and check Check script before relying on them.
- Rotation is in degrees, clockwise-positive. Coordinates start at the top-left.
- The MotionCode Reference (Parts 2, 3, 24 and 25) defines the object rules these scripts use.