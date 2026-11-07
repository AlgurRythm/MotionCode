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

