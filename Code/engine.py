"""MotionCode scene model. 2D primitives plus lightweight 3D meshes (wireframe or solid).

Features in this module:
  - parent=...        child objects follow their parent's position, rotation, scale and opacity
  - keyframes()       interpolate a property between (time, value) points, applied after animate()
  - bring_to_front()  and send_to_back()  change draw order
  - measure_text()    real text width and height in pixels (needs the app to be running)
  - Text(max_width=)  word-wrapped text inside a fixed width
  - add_wireframe()   custom 3D wireframe from your own vertices and edges
  - curve()           custom easing graph for keyframes
"""
import math
import os


def _ease_fn(name):
    if callable(name):
        return name
    key = str(name or "ease_in_out").lower()
    table = {
        "linear": lambda u: u,
        "ease_in": lambda u: u * u * u,
        "ease_out": lambda u: 1.0 - (1.0 - u) ** 3,
        "ease_in_out": lambda u: 4.0 * u ** 3 if u < 0.5 else 1.0 - ((-2.0 * u + 2.0) ** 3) / 2.0,
    }
    if key not in table:
        raise ValueError("Unknown ease %r. Use one of: %s" % (name, ", ".join(table)))
    return table[key]


def curve(points):
    """Custom easing graph. points is a list of (x, y) pairs, x and y from 0 to 1.
    The curve runs from (0, 0) to (1, 1) through your points. Use it as ease=curve(...)."""
    pts = sorted((float(x), float(y)) for x, y in points)
    if len(pts) < 2:
        raise ValueError("curve needs at least two points")
    # Remove duplicate x values, keeping the last y for each x.
    unique = {}
    for x, y in pts:
        unique[x] = y
    pts = sorted(unique.items())
    if pts[0] != (0.0, 0.0):
        pts.insert(0, (0.0, 0.0))
    if pts[-1] != (1.0, 1.0):
        pts.append((1.0, 1.0))

    def ease(u):
        u = max(0.0, min(1.0, u))
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= u <= x1:
                k = 0.0 if x1 == x0 else (u - x0) / (x1 - x0)
                return y0 + (y1 - y0) * k
        return 1.0
    return ease


class Track:
    """One keyframed property. Points are (time_seconds, value) pairs."""

    def __init__(self, name, prop, points, ease):
        pts = sorted((float(t), float(v)) for t, v in points)
        if not pts:
            raise ValueError("keyframes() needs at least one (time, value) point")
        self.name = str(name)
        self.prop = str(prop)
        self.points = pts
        self.ease = _ease_fn(ease)

    def value(self, t):
        pts = self.points
        if t <= pts[0][0]:
            return pts[0][1]
        if t >= pts[-1][0]:
            return pts[-1][1]
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            if t0 <= t <= t1:
                if t1 <= t0:
                    return v1
                return v0 + (v1 - v0) * self.ease((t - t0) / (t1 - t0))
        return pts[-1][1]


class Scene:
    def __init__(self):
        self.objects = []
        self._index = {}                 # object name -> position in self.objects
        self.background = "#080D18"
        self.duration = 10.0
        self.fps = 24
        self.width = 1920
        self.height = 1080
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.camera_z = -900.0
        self.camera_fov = 700.0
        # Effects (see FeaturesPro.py)
        self.lights = []                 # list of effects.Light
        self.ambient = 0.35              # base brightness with no lights
        self.background_gradient = None  # effects.Gradient for the backdrop
        self.motion_blur_samples = 8     # sub-frames per frame when motion blur is on
        # Whole-frame effects (see features.post_process). 0 means off.
        self.bloom = 0.0
        self.bloom_threshold = 0.8
        self.bloom_radius = 12.0
        self.vignette = 0.0
        self.grain = 0.0
        self.aberration = 0.0
        self.grade = None
        self.grade_strength = 0.0
        # Keyframes (applied after animate() on every frame)
        self.tracks = []
        # Filled in by the app so scripts can measure text and list fonts
        self.text_measurer = None
        self.font_lister = None
        # Presets: named groups of scene settings (see define_preset)
        self.presets = {}

    def _add(self, obj):
        if self.get_optional(obj.name) is not None:
            raise ValueError("An object named %r already exists" % obj.name)
        self.objects.append(obj)
        self._index[obj.name] = len(self.objects) - 1
        return obj

    def _rebuild_index(self):
        self._index = {o.name: i for i, o in enumerate(self.objects)}

    def get_optional(self, name):
        """Object with this name, or None. Uses a name -> position index. Each hit is
        checked against the list, because layer reordering moves objects around; a stale
        or missing entry triggers one rebuild."""
        i = self._index.get(name)
        if i is not None and i < len(self.objects) and self.objects[i].name == name:
            return self.objects[i]
        self._rebuild_index()
        i = self._index.get(name)
        return None if i is None else self.objects[i]

    def get(self, name):
        obj = self.get_optional(name)
        if obj is None:
            raise KeyError(name)
        return obj

    def _resolve(self, target):
        if isinstance(target, str):
            obj = self.get_optional(target)
            if obj is None:
                raise KeyError("No object named %r. Create it in build() before using it." % target)
            return obj
        return target

    # ---- keyframes -------------------------------------------------------
    def keyframes(self, target, prop, points, ease="ease_in_out"):
        """Animate one property between points, e.g.
            scene.keyframes("ball", "x", [(0, 200), (2, 1600)], ease="ease_out")
        Runs after animate() each frame, so it always wins over animate() for that property."""
        obj = self._resolve(target)
        if not hasattr(obj, prop):
            raise AttributeError("%s has no property %r" % (obj.name, prop))
        track = Track(obj.name, prop, points, ease)
        self.tracks.append(track)
        return track

    def clear_keyframes(self, target=None, prop=None):
        name = None if target is None else (target if isinstance(target, str) else target.name)
        self.tracks = [t for t in self.tracks
                       if not ((name is None or t.name == name) and (prop is None or t.prop == prop))]

    def apply_tracks(self, t):
        for track in self.tracks:
            setattr(self.get(track.name), track.prop, track.value(t))

    # ---- layers ----------------------------------------------------------
    def bring_to_front(self, target):
        obj = self._resolve(target)
        self.objects.remove(obj)
        self.objects.append(obj)
        return obj

    def send_to_back(self, target):
        obj = self._resolve(target)
        self.objects.remove(obj)
        self.objects.insert(0, obj)
        return obj

    # ---- text ------------------------------------------------------------
    def measure_text(self, text, size=64, font="Arial", bold=True, max_width=None):
        """Return (width, height) in pixels for text at this font size."""
        if self.text_measurer is not None:
            return self.text_measurer(str(text), int(size), str(font), bool(bold), max_width)
        return (len(str(text)) * size * 0.6, size * 1.2)

    def list_fonts(self):
        return list(self.font_lister()) if self.font_lister is not None else []

    # ---- presets ---------------------------------------------------------
    PRESET_KEYS = ("background", "background_gradient", "lights", "ambient", "camera_x", "camera_y", "camera_z", "camera_fov", "motion_blur_samples",)

    def define_preset(self, name, **props):
        """Store a named group of scene settings, e.g.
            scene.define_preset("night", background="#050812", ambient=0.2, camera_z=-700)
        Allowed keys: background, background_gradient, lights, ambient, camera_x,
        camera_y, camera_z, camera_fov, motion_blur_samples."""
        for key in props:
            if key not in self.PRESET_KEYS:
                raise ValueError("%r cannot be stored in a preset. Allowed: %s"
                                 % (key, ", ".join(self.PRESET_KEYS)))
        self.presets[str(name)] = dict(props)

    def apply_preset(self, name):
        """Apply a preset's settings to the scene. Call it in build()."""
        if name not in self.presets:
            raise KeyError("No preset named %r. Defined: %s"
                           % (name, ", ".join(self.presets) or "none"))
        for key, value in self.presets[name].items():
            setattr(self, key, value)
        return self

    # ---- shapes ----------------------------------------------------------
    def add_circle(self, name, **kw): return self._add(Circle(name, **kw))
    def add_text(self, name, text, **kw): return self._add(Text(name, text, **kw))
    def add_cube(self, name, **kw): return self._add(MeshObject(name, "cube", **kw))
    def add_sphere(self, name, **kw): return self._add(MeshObject(name, "sphere", **kw))
    def add_pyramid(self, name, **kw): return self._add(MeshObject(name, "pyramid", **kw))
    def add_cone(self, name, **kw): return self._add(MeshObject(name, "cone", **kw))
    def add_cylinder(self, name, **kw): return self._add(MeshObject(name, "cylinder", **kw))
    def add_torus(self, name, **kw): return self._add(MeshObject(name, "torus", **kw))
    def add_plane(self, name, **kw): return self._add(MeshObject(name, "plane", **kw))
    def add_rect(self, name, **kw): return self._add(Rect(name, **kw))
    def add_line(self, name, **kw): return self._add(Line(name, **kw))

    def add_wireframe(self, name, vertices, edges, size=180, **kw):
        """Custom 3D wireframe from your own vertices and edges.
        vertices: list of (x, y, z). edges: list of (i, j) vertex index pairs.
        The geometry is scaled so its largest extent is `size` pixels."""
        if not vertices or not edges:
            raise ValueError("add_wireframe needs vertices and edges")
        verts = [tuple(float(c) for c in v) for v in vertices]
        for e in edges:
            if any(i < 0 or i >= len(verts) for i in e):
                raise ValueError("Edge %r points at a vertex that does not exist" % (e,))
        biggest = max(max(abs(c) for c in v) for v in verts) or 1.0
        k = (size / 2.0) / biggest
        mesh = MeshObject(name, shape="custom", size=size, **kw)
        mesh.vertices = [(x * k, y * k, z * k) for x, y, z in verts]
        mesh.edges = [tuple(int(i) for i in e) for e in edges]
        mesh.faces = []
        return self._add(mesh)


class Base:
    def __init__(self, name, x=960, y=540, z=0, color="#FFFFFF", rotation=0,
                 rotation_x=0, rotation_y=0, rotation_z=None, scale=1, opacity=1,
                 stroke=3, filled=False, parent=None,
                 scale_x=1.0, scale_y=1.0, skew_x=0.0, blur=0.0, backdrop_blur=0.0,
                 motion_blur=0.0, gradient=None, lit=False):
        self.name = name
        self.x, self.y, self.z = float(x), float(y), float(z)
        self.color = color
        self._rotation = float(rotation)
        self.rotation_x = float(rotation_x)
        self.rotation_y = float(rotation_y)
        self.rotation_z = float(rotation if rotation_z is None else rotation_z)
        self.scale = float(scale)
        self.opacity = float(opacity)
        self.stroke = float(stroke)
        self.filled = bool(filled)
        # Effects (see FeaturesPro.py). All can be passed as keyword arguments.
        self.scale_x = float(scale_x)           # stretch along the object's own x axis
        self.scale_y = float(scale_y)           # stretch along the object's own y axis
        self.skew_x = float(skew_x)             # slant in degrees
        self.blur = float(blur)                 # blur radius in scene pixels
        self.backdrop_blur = float(backdrop_blur)  # blurs what is behind the object, inside its shape
        self.motion_blur = float(motion_blur)   # shutter fraction 0..1 (0 = off)
        self.gradient = gradient                # effects.Gradient for filled shapes
        self.lit = bool(lit)                    # True = affected by the scene's lights
        # Parenting: x, y, rotation_z, scale and opacity are relative to the parent.
        # Set to an object or an object name.
        self.parent = parent

    @property
    def rotation(self):
        # Legacy scripts animate .rotation; for 3D meshes this is the Z axis.
        return self.rotation_z

    @rotation.setter
    def rotation(self, value):
        self._rotation = float(value)
        if hasattr(self, "rotation_z"):
            self.rotation_z = float(value)


class Circle(Base):
    def __init__(self, name, radius=100, stroke=6, **kw):
        super().__init__(name, stroke=stroke, **kw)
        self.radius = float(radius)


class Text(Base):
    def __init__(self, name, text, size=64, font="Arial", bold=True, align="center",
                 max_width=None, **kw):
        # Text-only properties must be consumed here, not forwarded to Base.
        super().__init__(name, **kw)
        self.text = str(text)
        self.size = int(size)
        self.font = str(font)
        self.bold = bool(bold)
        self.align = str(align)
        # With max_width set, the text wraps onto new lines inside that width.
        self.max_width = float(max_width) if max_width else None


class Rect(Base):
    def __init__(self, name, width=200, height=120, **kw):
        super().__init__(name, **kw)
        self.width, self.height = float(width), float(height)


class Line(Base):
    def __init__(self, name, x2=100, y2=0, **kw):
        super().__init__(name, **kw)
        self.x2, self.y2 = float(x2), float(y2)


class MeshObject(Base):
    def __init__(self, name, shape="cube", size=180, radius=None, height=None,
                 segments=16, rings=10, **kw):
        super().__init__(name, **kw)
        self.shape = shape
        self.size = float(size)
        self.radius = float(radius if radius is not None else size / 2)
        self.height = float(height if height is not None else size)
        self.segments = max(3, min(64, int(segments)))
        self.rings = max(2, min(32, int(rings)))


Cube = MeshObject


# Advanced 2D/custom geometry and OBJ asset support.
class Polygon(Base):
    def __init__(self, name, points=None, closed=True, **kw):
        super().__init__(name, **kw)
        self.points = [(float(x), float(y)) for x, y in (points or [])]
        self.closed = bool(closed)


class ImageAsset(Base):
    def __init__(self, name, path, width=400, height=300, **kw):
        super().__init__(name, **kw)
        self.path = str(path)
        self.width, self.height = float(width), float(height)


def _scene_add_polygon(self, name, points=None, **kw):
    return self._add(Polygon(name, points=points, **kw))

def _scene_add_polyline(self, name, points=None, **kw):
    kw['closed'] = False
    kw.setdefault('filled', False)
    return self._add(Polygon(name, points=points, **kw))

def _scene_add_star(self, name, points=5, outer_radius=100, inner_radius=45, **kw):
    count = max(2, min(64, int(points)))
    coords = []
    for i in range(count * 2):
        angle = -math.pi / 2 + i * math.pi / count
        radius = outer_radius if i % 2 == 0 else inner_radius
        coords.append((math.cos(angle) * radius, math.sin(angle) * radius))
    return self._add(Polygon(name, points=coords, closed=True, **kw))

# Folders searched for image and OBJ files that are not found as given (set by the app).
SEARCH_DIRS = []


def find_asset(path):
    """Return path if it exists. Otherwise look for the file name in SEARCH_DIRS."""
    path = str(path)
    if os.path.exists(path):
        return path
    for folder in SEARCH_DIRS:
        candidate = os.path.join(folder, path)
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"File {path!r} not found. Put it in the Data or assets folder, or give the full path.")


def _scene_add_image(self, name, path, **kw):
    return self._add(ImageAsset(name, find_asset(path), **kw))

def _scene_add_obj(self, name, path, **kw):
    """Load a Wavefront OBJ mesh. Keeps edges for wireframe and faces for solid fill."""
    path = find_asset(path)
    vertices, edges, edge_set, faces = [], [], set(), []
    with open(path, 'r', encoding='utf-8', errors='replace') as source:
        for raw in source:
            parts = raw.strip().split()
            if not parts: continue
            if parts[0] == 'v' and len(parts) >= 4:
                vertices.append(tuple(float(v) for v in parts[1:4]))
            elif parts[0] == 'f' and len(parts) >= 4:
                face = [int(token.split('/')[0]) - 1 for token in parts[1:]]
                # Validate indices against the vertices read so far.
                if any(i < 0 or i >= len(vertices) for i in face):
                    raise ValueError('OBJ face refers to a vertex that does not exist: ' + raw.strip())
                faces.append(tuple(face))
                for a, b in zip(face, face[1:] + face[:1]):
                    edge = tuple(sorted((a, b)))
                    if edge not in edge_set:
                        edge_set.add(edge); edges.append(edge)
    if not vertices:
        raise ValueError('OBJ file contains no vertex data: ' + str(path))
    if not edges:
        raise ValueError('OBJ file contains no polygon faces: ' + str(path))
    mesh = MeshObject(name, shape='custom', **kw)
    mesh.vertices = vertices
    mesh.edges = edges
    mesh.faces = faces
    return self._add(mesh)

Scene.add_polygon = _scene_add_polygon
Scene.add_polyline = _scene_add_polyline
Scene.add_star = _scene_add_star
Scene.add_image = _scene_add_image
Scene.add_obj = _scene_add_obj


def _scene_add_ellipse(self, name, radius_x=100, radius_y=60, segments=48, **kw):
    count = max(8, min(128, int(segments)))
    pts = [(float(radius_x) * math.cos(2 * math.pi * i / count),
            float(radius_y) * math.sin(2 * math.pi * i / count)) for i in range(count)]
    return self._add(Polygon(name, points=pts, closed=True, **kw))

def _scene_add_rounded_rect(self, name, width=200, height=120, radius=18, segments=8, **kw):
    r = max(0.0, min(float(radius), float(width) / 2, float(height) / 2))
    pts = []
    for cx, cy, start in ((width/2 - r, -height/2 + r, -90), (width/2 - r, height/2 - r, 0),
                          (-width/2 + r, height/2 - r, 90), (-width/2 + r, -height/2 + r, 180)):
        for j in range(max(2, int(segments)) + 1):
            a = math.radians(start + j * 90 / max(2, int(segments)))
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return self._add(Polygon(name, points=pts, closed=True, **kw))

Scene.add_ellipse = _scene_add_ellipse
Scene.add_rounded_rect = _scene_add_rounded_rect