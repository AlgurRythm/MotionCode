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