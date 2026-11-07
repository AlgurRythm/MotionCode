"""MotionCode motion helpers: transforms, easing, shake, particles, trails, typing,
and 3D mesh projection. Qt is used only for drawing helpers.

Used in two ways:
  1. main.py calls apply_transform(painter, obj) for every 2D object, so an
     object can stretch (scale_x / scale_y) and skew (skew_x).
  2. Animation scripts call the helpers below from animate(scene, t).

Nothing here depends on Qt except apply_transform, which only uses the
painter methods translate / rotate / scale / shear.
"""
import copy
import math
import random

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QPolygonF


# ----------------------------------------------------------------- transforms

def apply_transform(p, obj):
    """Position, rotate, stretch and skew a 2D object before it is drawn.
    scale_x and scale_y stretch independently; skew_x slants the shape (degrees)."""
    p.translate(obj.x, obj.y)
    p.rotate(obj.rotation_z)
    sx = getattr(obj, "scale_x", 1.0)
    sy = getattr(obj, "scale_y", 1.0)
    p.scale(obj.scale * sx, obj.scale * sy)
    skew = getattr(obj, "skew_x", 0.0)
    if skew:
        p.shear(math.tan(math.radians(skew)), 0.0)


# -------------------------------------------------------------------- easing

def clamp01(k):
    return max(0.0, min(1.0, k))


def ease_out_cubic(k):
    k = clamp01(k)
    return 1.0 - (1.0 - k) ** 3


def ease_in_out_cubic(k):
    k = clamp01(k)
    return 4 * k ** 3 if k < 0.5 else 1 - ((-2 * k + 2) ** 3) / 2


def ease_out_back(k, overshoot=1.70158):
    """Overshoots its target and settles. Good for pop-ins."""
    k = clamp01(k)
    c3 = overshoot + 1
    return 1 + c3 * (k - 1) ** 3 + overshoot * (k - 1) ** 2


def ease_out_elastic(k):
    """Springy wobble that settles on the target."""
    k = clamp01(k)
    if k == 0 or k == 1:
        return k
    return 2 ** (-10 * k) * math.sin((k * 10 - 0.75) * (2 * math.pi) / 3) + 1


def ease_out_bounce(k):
    k = clamp01(k)
    n1, d1 = 7.5625, 2.75
    if k < 1 / d1:
        return n1 * k * k
    if k < 2 / d1:
        k -= 1.5 / d1
        return n1 * k * k + 0.75
    if k < 2.5 / d1:
        k -= 2.25 / d1
        return n1 * k * k + 0.9375
    k -= 2.625 / d1
    return n1 * k * k + 0.984375


def progress(t, start, duration, ease=ease_out_cubic):
    """0..1 progress of an eased move that begins at start and lasts duration seconds."""
    if duration <= 0:
        return 1.0 if t >= start else 0.0
    return ease((t - start) / duration)


# ------------------------------------------------------- stretch and squash

def spring(t, start, freq=2.5, damping=3.5):
    """Damped spring that starts at 1 at time start and rings down to 0."""
    if t < start:
        return 0.0
    x = t - start
    return math.exp(-damping * x) * math.cos(2 * math.pi * freq * x)


def squash_stretch(t, start, amount=0.25, freq=2.5, damping=3.5):
    """Returns (scale_x, scale_y) for a squash-and-stretch impulse.
    Positive amount stretches tall and squashes wide, which reads as bounce."""
    s = spring(t, start, freq, damping) * amount
    return 1.0 - s, 1.0 + s


def shake(t, amplitude=10.0, frequency=14.0, decay=4.0, start=0.0):
    """Returns (dx, dy) for a shake that fades out over time."""
    if t < start:
        return 0.0, 0.0
    x = t - start
    env = math.exp(-decay * x) * amplitude
    return env * math.sin(2 * math.pi * frequency * x), env * math.cos(2 * math.pi * frequency * 1.31 * x)


def wobble(t, amplitude=6.0, frequency=1.2, start=0.0):
    """Returns a rotation angle in degrees that gently sways."""
    if t < start:
        return 0.0
    return amplitude * math.sin(2 * math.pi * frequency * (t - start))


def flash(t, start, duration=0.25):
    """Opacity that spikes at start and fades to 0 over duration."""
    if t < start or t > start + duration:
        return 0.0
    return 1.0 - (t - start) / duration


# -------------------------------------------------------------------- text

def typed(text, t, start, chars_per_second=18.0):
    """The part of text visible at time t, for a typewriter reveal."""
    if t < start:
        return ""
    count = int((t - start) * chars_per_second)
    return text[:max(0, min(len(text), count))]


def word_reveal(words, t, start, per_word=0.12):
    """Opacity for each word so they appear one after another.
    Returns a list of (word, opacity) pairs."""
    out = []
    for i, word in enumerate(words):
        local = (t - (start + i * per_word)) / 0.25
        out.append((word, ease_out_cubic(local)))
    return out


# --------------------------------------------------------------- particles

class Burst:
    """A burst of particles from one point. Call build(scene) once, then
    update(scene, t) every frame from animate()."""

    def __init__(self, prefix, x, y, t0, count=24, speed=320.0, life=1.0,
                 color="#FFFFFF", size=6.0, gravity=500.0, seed=1, stroke=2):
        self.prefix = prefix
        self.x, self.y = float(x), float(y)
        self.t0 = float(t0)
        self.life = float(life)
        self.gravity = float(gravity)
        self.color = color
        self.size = float(size)
        self.stroke = float(stroke)
        rng = random.Random(seed)
        self.particles = []
        for i in range(count):
            angle = rng.uniform(0, 2 * math.pi)
            v = speed * rng.uniform(0.5, 1.0)
            self.particles.append((i, math.cos(angle) * v, math.sin(angle) * v))
        self.names = ["%s_%d" % (prefix, i) for i, _, _ in self.particles]

    def build(self, scene):
        for name in self.names:
            scene.add_circle(name, x=self.x, y=self.y, radius=self.size,
                             color=self.color, stroke=self.stroke, filled=True)

    def update(self, scene, t):
        age = t - self.t0
        for (i, vx, vy), name in zip(self.particles, self.names):
            obj = scene.get_optional(name)
            if obj is None:
                continue
            if age < 0 or age > self.life:
                obj.opacity = 0.0
                continue
            x = self.x + vx * age
            y = self.y + vy * age + 0.5 * self.gravity * age * age
            obj.x, obj.y = x, y
            obj.opacity = clamp01(1.0 - age / self.life)
            obj.scale = max(0.1, 1.0 - age / self.life)


class Trail:
    """Ghost copies that follow a moving point with a delay, for motion trails.
    Pass pos_fn(t) -> (x, y) returning the point's position at any time."""

    def __init__(self, prefix, pos_fn, count=8, delay=0.04, fade=0.8,
                 color="#35B9FF", radius=10.0, stroke=2):
        self.prefix = prefix
        self.pos_fn = pos_fn
        self.count = int(count)
        self.delay = float(delay)
        self.fade = float(fade)
        self.color = color
        self.radius = float(radius)
        self.stroke = float(stroke)
        self.names = ["%s_%d" % (prefix, i) for i in range(self.count)]

    def build(self, scene):
        for name in self.names:
            scene.add_circle(name, x=0, y=0, radius=self.radius, color=self.color,
                             stroke=self.stroke, filled=True)

    def update(self, scene, t):
        for i, name in enumerate(self.names):
            obj = scene.get_optional(name)
            if obj is None:
                continue
            x, y = self.pos_fn(max(0.0, t - i * self.delay))
            obj.x, obj.y = x, y
            obj.opacity = clamp01(self.fade ** i)
            obj.scale = max(0.2, 1.0 - 0.08 * i)


# ------------------------------------------------------------------ meshes

def mesh_data(obj):
    n = obj.segments
    s = obj.size / 2
    verts, edges = [], []
    if obj.shape == "cube":
        verts = [(-s,-s,-s),(s,-s,-s),(s,s,-s),(-s,s,-s),(-s,-s,s),(s,-s,s),(s,s,s),(-s,s,s)]
        edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    elif obj.shape == "pyramid":
        verts = [(-s,s,-s),(s,s,-s),(s,s,s),(-s,s,s),(0,-s,0)]
        edges = [(0,1),(1,2),(2,3),(3,0),(0,4),(1,4),(2,4),(3,4)]
    elif obj.shape in ("cone", "cylinder"):
        h = obj.height / 2
        for yy in (-h, h):
            for i in range(n):
                a = 2 * math.pi * i / n
                verts.append((obj.radius * math.cos(a), yy, obj.radius * math.sin(a)))
        for i in range(n):
            j = (i + 1) % n
            edges += [(i,j),(i+n,j+n),(i,i+n)]
        if obj.shape == "cone":
            verts.append((0,-h,0)); tip = len(verts)-1
            edges = [(i,(i+1)%n) for i in range(n)] + [(i,tip) for i in range(n)]
    elif obj.shape == "sphere":
        for r in range(1, obj.rings):
            phi = math.pi * r / obj.rings
            start = len(verts)
            for i in range(n):
                theta = 2 * math.pi * i / n
                verts.append((s*math.sin(phi)*math.cos(theta), s*math.cos(phi), s*math.sin(phi)*math.sin(theta)))
            for i in range(n): edges.append((start+i, start+(i+1)%n))
        for i in range(n):
            for r in range(obj.rings-1): edges.append((r*n+i, (r+1)*n+i))
    elif obj.shape == "torus":
        major, minor = obj.size * .36, obj.size * .12
        m = n
        # A torus needs at least 6 rings to read as a torus. Smaller values
        # are raised to 6 instead of failing.
        rr = max(6, obj.rings)
        for i in range(m):
            u = 2*math.pi*i/m
            for j in range(rr):
                v = 2*math.pi*j/rr
                verts.append(((major+minor*math.cos(v))*math.cos(u), minor*math.sin(v), (major+minor*math.cos(v))*math.sin(u)))
        for i in range(m):
            for j in range(rr):
                a=i*rr+j
                edges += [(a,i*rr+(j+1)%rr),(a,((i+1)%m)*rr+j)]
    elif obj.shape == "plane":
        verts=[(-s,0,-s),(s,0,-s),(s,0,s),(-s,0,s)]
        edges=[(0,1),(1,2),(2,3),(3,0),(0,2),(1,3)]
    elif obj.shape == "custom":
        verts = list(obj.vertices)
        edges = list(obj.edges)
    return verts, edges


def _rotate_vertices(obj, verts):
    ax = math.radians(obj.rotation_x); ay = math.radians(obj.rotation_y); az = math.radians(obj.rotation_z)
    out = []
    for x, y, z in verts:
        x *= obj.scale; y *= obj.scale; z *= obj.scale
        y, z = y*math.cos(ax)-z*math.sin(ax), y*math.sin(ax)+z*math.cos(ax)
        x, z = x*math.cos(ay)+z*math.sin(ay), -x*math.sin(ay)+z*math.cos(ay)
        x, y = x*math.cos(az)-y*math.sin(az), x*math.sin(az)+y*math.cos(az)
        out.append((x, y, z))
    return out


def project_mesh(obj, scene):
    verts, edges = mesh_data(obj)
    rot = _rotate_vertices(obj, verts)
    camera_z = max(100.0, float(getattr(scene, "camera_fov", 700)))
    projected = []
    for x, y, z in rot:
        depth = max(30.0, camera_z + z + obj.z)
        factor = camera_z / depth
        projected.append(QPointF((x-scene.camera_x)*factor+obj.x, (y-scene.camera_y)*factor+obj.y))
    return projected, edges


def draw_filled_mesh(p, obj, scene):
    """Solid flat-shaded draw with no outline. Faces are sorted farthest-first."""
    rot = _rotate_vertices(obj, list(obj.vertices))
    camera_z = max(100.0, float(getattr(scene, "camera_fov", 700)))
    screen = []
    for x, y, z in rot:
        depth = max(30.0, camera_z + z + obj.z)
        f = camera_z / depth
        screen.append(QPointF((x - scene.camera_x) * f + obj.x, (y - scene.camera_y) * f + obj.y))

    lx, ly, lz = -0.35, -0.55, -0.76
    ll = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx, ly, lz = lx/ll, ly/ll, lz/ll

    base = QColor(obj.color)
    items = []
    for face in obj.faces:
        if len(face) < 3 or any(i < 0 or i >= len(rot) for i in face):
            continue
        ax_, ay_, az_ = rot[face[0]]
        bx, by, bz = rot[face[1]]
        cx_, cy_, cz_ = rot[face[2]]
        ux, uy, uz = bx-ax_, by-ay_, bz-az_
        vx, vy, vz = cx_-ax_, cy_-ay_, cz_-az_
        nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        nl = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
        dot = abs((nx*lx + ny*ly + nz*lz) / nl)
        shade = 0.6 + 0.4 * dot
        zavg = sum(rot[i][2] for i in face) / len(face)
        items.append((zavg, face, shade))

    items.sort(key=lambda it: -it[0])
    p.setPen(Qt.PenStyle.NoPen)
    for _, face, shade in items:
        col = QColor(int(base.red()*shade), int(base.green()*shade), int(base.blue()*shade))
        p.setBrush(col)
        p.drawPolygon(QPolygonF([screen[i] for i in face]))


def resolve_pose(obj, scene, _depth=0):
    """Return a copy of obj with its parent's transform applied, so children follow parents.
    Objects without a parent are returned unchanged."""
    parent = getattr(obj, "parent", None)
    if parent is None:
        return obj
    if _depth > 32:
        raise ValueError("Parent chain is too deep or loops back on itself")
    if isinstance(parent, str):
        parent = scene.get(parent)
    pw = resolve_pose(parent, scene, _depth + 1)
    s = float(pw.scale)
    a = math.radians(pw.rotation_z)
    lx, ly = float(obj.x), float(obj.y)
    out = copy.copy(obj)
    out.x = pw.x + (lx * math.cos(a) - ly * math.sin(a)) * s
    out.y = pw.y + (lx * math.sin(a) + ly * math.cos(a)) * s
    out.rotation_z = pw.rotation_z + float(obj.rotation_z)
    out.scale = float(obj.scale) * s
    out.opacity = float(obj.opacity) * float(pw.opacity)
    out.parent = None
    return out