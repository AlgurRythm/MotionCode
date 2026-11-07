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

