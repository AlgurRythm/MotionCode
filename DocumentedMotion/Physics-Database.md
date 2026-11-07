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
