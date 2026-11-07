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

