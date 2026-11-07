"""MotionCode visual effects: gradients, lighting, blur and motion blur.

Most functions work on numpy arrays of shape (height, width, 3 or 4) with float
values in 0..1. The renderer (features.py) converts its QImage to an array, applies
these functions, and converts back. The gradient and image-conversion helpers are
the only part that touches Qt.
"""
import math

import numpy as np
from PySide6.QtCore import QPointF
from PySide6.QtGui import QBrush, QColor, QImage, QLinearGradient, QRadialGradient

from engine import Circle, Rect, ImageAsset, MeshObject, Polygon
from optimization import pixel_grid, remember, LIGHT_CACHE


def hex_to_rgb(text):
    text = text.lstrip("#")
    return np.array([int(text[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


# ------------------------------------------------------------------ gradients

class Gradient:
    """Color gradient for a shape or the background.

    stops:  list of (position 0..1, "#RRGGBB"), e.g. [(0, "#FF8A5B"), (1, "#3A0CA3")]
    kind:   "linear" or "radial"
    angle:  linear direction in degrees. 0 = left to right, 90 = top to bottom.
    center: radial center as fractions of the object's box (0.5, 0.5 = middle).
    radius: radial radius as a fraction of the object's larger side.
    """

    def __init__(self, stops, kind="linear", angle=90.0, center=(0.5, 0.5), radius=0.5):
        if len(stops) < 2:
            raise ValueError("A gradient needs at least two stops")
        self.stops = sorted(((float(p), hex_to_rgb(c)) for p, c in stops), key=lambda s: s[0])
        self.kind = str(kind).lower()
        if self.kind not in ("linear", "radial"):
            raise ValueError("kind must be 'linear' or 'radial'")
        self.angle = float(angle)
        self.center = (float(center[0]), float(center[1]))
        self.radius = float(radius)

    def sample(self, xs, ys, box):
        """Colors for pixel grids xs, ys (same shape). box = (x, y, width, height)
        of the object. Returns an array of shape (..., 3)."""
        bx, by, bw, bh = box
        if self.kind == "radial":
            cx = bx + self.center[0] * bw
            cy = by + self.center[1] * bh
            r = max(1e-6, self.radius * max(bw, bh))
            u = np.hypot(xs - cx, ys - cy) / r
        else:
            a = math.radians(self.angle)
            dx, dy = math.cos(a), math.sin(a)
            cx, cy = bx + bw / 2.0, by + bh / 2.0
            half = max(1e-6, (abs(dx) * bw + abs(dy) * bh) / 2.0)
            u = ((xs - cx) * dx + (ys - cy) * dy) / (2.0 * half) + 0.5
        u = np.clip(u, 0.0, 1.0)
        pos = np.array([p for p, _ in self.stops])
        cols = np.array([c for _, c in self.stops])
        return np.stack([np.interp(u, pos, cols[:, k]) for k in range(3)], axis=-1)


# ------------------------------------------------------------------- lighting

class Light:
    """A soft point light in screen pixels.

    radius:    distance in pixels where the light fades to zero
    intensity: brightness added where the light is strongest (1.0 = full)
    color:     light color, "#RRGGBB"
    """

    def __init__(self, x, y, radius=600.0, intensity=1.0, color="#FFFFFF"):
        self.x, self.y = float(x), float(y)
        self.radius = max(1.0, float(radius))
        self.intensity = float(intensity)
        self.color = hex_to_rgb(color)


def light_map(xs, ys, lights, ambient=0.35):
    """Brightness multiplier per pixel, shape (..., 3). 1.0 leaves colors unchanged.
    Values above 1 brighten; the result is capped at 1.6."""
    total = np.full(xs.shape + (3,), float(ambient))
    for light in lights:
        d = np.hypot(xs - light.x, ys - light.y) / light.radius
        falloff = np.clip(1.0 - d, 0.0, 1.0) ** 2
        total += falloff[..., None] * light.intensity * light.color
    return np.clip(total, 0.0, 1.6)


def lambert(normal, light_dir, ambient=0.25):
    """Diffuse brightness for a 3D face. normal and light_dir are 3-vectors.
    Use it to shade filled OBJ faces with a directional light."""
    n = np.asarray(normal, dtype=float)
    l = np.asarray(light_dir, dtype=float)
    n = n / max(1e-9, np.linalg.norm(n))
    l = l / max(1e-9, np.linalg.norm(l))
    return float(min(1.0, ambient + (1.0 - ambient) * max(0.0, float(np.dot(n, l)))))


# ----------------------------------------------------------------------- blur

def _box_axis(arr, r, axis):
    a = np.moveaxis(arr, axis, 0)
    pad = np.pad(a, [(r, r)] + [(0, 0)] * (a.ndim - 1), mode="edge")
    c = np.cumsum(pad, axis=0)
    c = np.concatenate([np.zeros_like(c[:1]), c], axis=0)
    k = 2 * r + 1
    return np.moveaxis((c[k:] - c[:-k]) / k, 0, axis)


def box_blur(img, radius):
    """Fast box blur. img is (H, W, C). radius in pixels."""
    r = int(round(radius))
    if r <= 0:
        return img
    return _box_axis(_box_axis(img, r, 0), r, 1)


def gaussian_blur(img, sigma):
    """Soft blur approximated by three box passes. sigma is roughly the blur radius in pixels."""
    if sigma <= 0:
        return img
    r = max(1, int(round(sigma)))
    out = img
    for _ in range(3):
        out = box_blur(out, r)
    return out


def blur_region(img, x0, y0, x1, y1, radius):
    """Blur only the rectangle (x0, y0)-(x1, y1). Returns a new array."""
    h, w = img.shape[:2]
    x0, x1 = max(0, int(x0)), min(w, int(x1))
    y0, y1 = max(0, int(y0)), min(h, int(y1))
    if x1 <= x0 or y1 <= y0:
        return img
    out = img.copy()
    out[y0:y1, x0:x1] = gaussian_blur(img[y0:y1, x0:x1], radius)
    return out


def circle_mask(xs, ys, cx, cy, radius, feather=2.0):
    """Soft circle mask, 1 inside and 0 outside, for use with backdrop_blur."""
    d = np.hypot(xs - cx, ys - cy)
    return np.clip((radius - d) / max(feather, 1e-6) + 0.5, 0.0, 1.0)


def backdrop_blur(img, mask, radius):
    """Blur the background where mask is 1. Use it for frosted-glass or focus effects.
    mask has shape (H, W) with values 0..1."""
    blurred = gaussian_blur(img, radius)
    m = mask[..., None]
    return img * (1.0 - m) + blurred * m


# ---------------------------------------------------------------- motion blur

def motion_blur_times(t, fps, shutter=0.5, samples=8):
    """Times to render inside one frame to create motion blur.
    shutter: fraction of a frame the virtual camera stays open (0.5 is typical)."""
    if samples <= 1 or shutter <= 0:
        return [max(0.0, t)]
    span = shutter / float(fps)
    start = t - span / 2.0
    return [max(0.0, start + span * i / (samples - 1)) for i in range(samples)]


def average_frames(frames):
    """Average rendered sub-frames into one motion-blurred frame.
    Accumulates in float32 so memory stays reasonable at 1080p."""
    acc = np.zeros(frames[0].shape, dtype=np.float32)
    for f in frames:
        acc += f
    return acc / len(frames)


def velocity_stretch(vx, vy, amount=0.02, max_stretch=1.6):
    """Stretch a shape along its movement. Returns (rotation_z, scale_x, scale_y).
    Apply rotation_z = angle, scale_x = s, scale_y = 1/sqrt(s) so the area stays
    the same. Note: this replaces the object's own rotation_z while it moves."""
    speed = math.hypot(vx, vy)
    s = min(max_stretch, 1.0 + amount * speed)
    angle = math.degrees(math.atan2(vy, vx))
    return angle, s, 1.0 / math.sqrt(s)


# ------------------------------------------------------- Qt and lighting helpers

def qimage_to_array(img):
    """Premultiplied RGBA QImage to float32 array (H, W, 4), values 0..1."""
    img = img.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
    w, h = img.width(), img.height()
    bpl = img.bytesPerLine()
    raw = bytes(img.constBits())
    buf = np.frombuffer(raw, dtype=np.uint8)
    return buf.reshape(h, bpl // 4, 4)[:, :w, :].astype(np.float32) / 255.0


def array_to_qimage(arr):
    """Float array (H, W, 4), premultiplied, values 0..1, to a QImage."""
    arr = np.clip(arr, 0.0, 1.0)
    arr[..., :3] = np.minimum(arr[..., :3], arr[..., 3:4])
    data = np.ascontiguousarray((arr * 255.0 + 0.5).astype(np.uint8))
    h, w = data.shape[:2]
    buf = data.tobytes()
    img = QImage(buf, w, h, w * 4, QImage.Format.Format_RGBA8888_Premultiplied)
    return img.copy()


def local_extent(obj):
    """Half-width and half-height of a shape in its own coordinates, for gradients."""
    if isinstance(obj, Circle):
        return obj.radius, obj.radius
    if isinstance(obj, Rect):
        return obj.width / 2, obj.height / 2
    if isinstance(obj, ImageAsset):
        return obj.width / 2, obj.height / 2
    if isinstance(obj, MeshObject):
        return obj.size / 2, obj.size / 2
    if isinstance(obj, Polygon) and obj.points:
        return (max(abs(x) for x, _ in obj.points) or 1.0,
                max(abs(y) for _, y in obj.points) or 1.0)
    return 100.0, 100.0


def make_gradient_brush(grad, extent):
    """Qt brush for an effects.Gradient. extent is (half_width, half_height) in local coordinates."""
    hw, hh = extent
    if grad.kind == "radial":
        cx = (grad.center[0] * 2 - 1) * hw
        cy = (grad.center[1] * 2 - 1) * hh
        r = max(1.0, grad.radius * max(2 * hw, 2 * hh))
        g = QRadialGradient(QPointF(cx, cy), r)
    else:
        a = math.radians(grad.angle)
        dx, dy = math.cos(a), math.sin(a)
        half = max(1e-6, (abs(dx) * 2 * hw + abs(dy) * 2 * hh) / 2.0)
        g = QLinearGradient(QPointF(-dx * half, -dy * half), QPointF(dx * half, dy * half))
    for pos, rgb in grad.stops:
        g.setColorAt(float(pos), QColor.fromRgbF(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))
    return QBrush(g)


def apply_lights(arr, scene, rect, sx, sy):
    """Multiply the region's color by the light map, using scene coordinates for each pixel."""
    xx, yy = pixel_grid(rect, sx, sy)
    light_key = (rect.x(), rect.y(), rect.width(), rect.height(), sx, sy, float(scene.ambient),
                 tuple((float(l.x), float(l.y), float(l.radius), float(l.intensity),
                        tuple(float(c) for c in l.color)) for l in scene.lights))
    bright = LIGHT_CACHE.get(light_key)
    if bright is None:
        bright = remember(LIGHT_CACHE, light_key,
                           light_map(xx, yy, scene.lights, scene.ambient).astype(np.float32), 6)
    arr[..., :3] = arr[..., :3] * bright
    arr[..., :3] = np.minimum(arr[..., :3], arr[..., 3:4])
    return arr
