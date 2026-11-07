"""MotionCode rendering pipeline, script checks and shared constants.

The window and widgets live in UI.py. This file has no window code, so it can be
used from export scripts and tests without starting the UI.
"""
import copy
import math
import re
import sys
import time
import tempfile
import traceback

import numpy as np
from PySide6.QtCore import Qt, QPointF, QRectF, QRect
from PySide6.QtGui import (
    QBrush, QColor, QFont, QFontDatabase, QFontMetrics, QImage, QPainter, QPen, QPolygonF,
)
from PySide6.QtWidgets import QApplication

from engine import Scene, Circle, Text, Rect, Line, MeshObject, Polygon, ImageAsset
import FeaturesPro as pro
from optimization import cached_image, remember, pixel_grid

# FeaturesPro now holds the effects and motion helpers, so both names point at it.
fx = pro
motion_fx = pro


# ------------------------------------------------------------ constants

# Inspector limits per property. A value outside these widens the range instead of being clamped.
INSPECTOR_RANGES = {
    "opacity": (0.0, 1.0), "motion_blur": (0.0, 1.0),
    "scale": (0.0, 10.0), "scale_x": (0.0, 10.0), "scale_y": (0.0, 10.0),
    "blur": (0.0, 200.0), "backdrop_blur": (0.0, 200.0),
}
INSPECTOR_STEPS = {"opacity": 0.05, "motion_blur": 0.05}
INSPECTOR_DEFAULT_RANGE = (-20000.0, 20000.0)

VIDEO_FILE = "<MotionCode script>"
AUDIO_FILE = "<MotionCode audio script>"
ERROR_COLOR = "#FF4D4D"

# Highest resolution is 2K (2560x1440). "1440p" and "2K" are the same size.
RESOLUTIONS = [
    ("4K (2160p)", 3840, 2160),
    ("2K (1440p)", 2560, 1440),
    ("1080p", 1920, 1080),
    ("1K", 1024, 576),
    ("720p", 1280, 720),
    ("480p", 854, 480),
    ("360p", 640, 360),
]
FPS_MIN = 15
FPS_MAX = 120
VOLUME_MIN = 0
VOLUME_MAX = 150

# Quality changes only the heavy effects (motion blur, blur, frosted glass, lights).
# Every object is always drawn, and every script runs the same way at every level.
#   motion_cap:          most motion-blur sub-frames for fast movement
#   blur_half_above:     blurs at or above this many scene pixels run at half resolution
#   backdrop_half_above: frosted glass at or above this runs at half resolution
#   light_scale:         resolution of the lighting map (1.0 = full)
#   supersample:         effects are drawn at this multiple and scaled down (2 = sharper)
QUALITY_PRESETS = {
    "very_low": {"label": "Very low", "motion_cap": 1, "blur_half_above": 2,
                 "backdrop_half_above": 2, "light_scale": 0.125, "supersample": 1},
    "low": {"label": "Low", "motion_cap": 2, "blur_half_above": 2,
            "backdrop_half_above": 2, "light_scale": 0.25, "supersample": 1},
    "medium": {"label": "Medium", "motion_cap": 4, "blur_half_above": 6,
               "backdrop_half_above": 6, "light_scale": 0.5, "supersample": 1},
    "balanced": {"label": "Balanced", "motion_cap": 6, "blur_half_above": 12,
                 "backdrop_half_above": 12, "light_scale": 1.0, "supersample": 1},
    "high": {"label": "High", "motion_cap": 8, "blur_half_above": 1e9,
             "backdrop_half_above": 1e9, "light_scale": 1.0, "supersample": 1},
    "ultra": {"label": "Ultra", "motion_cap": 8, "blur_half_above": 1e9,
              "backdrop_half_above": 1e9, "light_scale": 1.0, "supersample": 2},
}
DEFAULT_QUALITY = "balanced"
# Order shown in the menus: highest first.
QUALITY_ORDER = ("ultra", "high", "balanced", "medium", "low", "very_low")

# The render reads these. Changed in place by the Quality box, so never reassign them.
RENDER_OPTS = dict(QUALITY_PRESETS[DEFAULT_QUALITY])

PYTHON_WORDS = [
    "and", "as", "assert", "break", "class", "continue", "def", "elif", "else",
    "except", "False", "finally", "for", "from", "if", "import", "in", "is",
    "lambda", "None", "not", "or", "pass", "raise", "return", "True", "try",
    "while", "with", "yield", "math", "print", "len", "range", "enumerate", "zip",
]
SCENE_WORDS = [
    "scene", "build", "animate", "add_circle", "add_rect", "add_rounded_rect",
    "add_ellipse", "add_star", "add_polygon", "add_polyline", "add_line", "add_text",
    "add_image", "add_obj", "add_cube", "add_sphere", "add_pyramid", "add_cone",
    "add_cylinder", "add_torus", "add_plane", "get", "get_optional", "keyframes",
    "clear_keyframes", "bring_to_front", "send_to_back", "measure_text", "list_fonts",
    "background", "background_gradient", "duration", "fps", "width", "height",
    "camera_x", "camera_y", "camera_z", "camera_fov", "lights", "ambient",
    "motion_blur_samples", "x", "y", "z", "x2", "y2", "color", "radius", "size",
    "width", "height", "text", "font", "bold", "align", "max_width", "parent",
    "points", "closed", "filled", "stroke", "opacity", "scale", "scale_x", "scale_y",
    "rotation", "rotation_x", "rotation_y", "rotation_z", "skew_x", "blur",
    "backdrop_blur", "motion_blur", "gradient", "lit", "segments", "rings",
    "import FeaturesPro as pro", "import transitions as tr",
    "FeaturesPro", "transitions", "Gradient", "Light", "Burst", "Trail",
    "ease_out_cubic", "ease_in_out_cubic", "ease_out_back", "ease_out_elastic",
    "ease_out_bounce", "progress", "spring", "squash_stretch", "shake", "wobble",
    "flash", "typed", "word_reveal", "enter", "exit", "fade_in", "fade_out",
    "slide_offset", "pop_scale", "zoom_scale", "visible_between",
]
AUDIO_WORDS = [
    "build_audio", "audio", "duration", "sample_rate", "master_volume", "add_tone",
    "add_noise", "add_click", "add_clip", "freq", "start", "length", "volume",
    "fade_in", "fade_out", "wave", "pan", "at", "name", "path",
    "sine", "square", "triangle", "saw", "add_mood", "mood", "base_freq",
]

STARTER = '''import math

def build(scene):
    scene.background = "#080D18"
    scene.duration = 10
    scene.fps = 24
    scene.add_circle("Blue ring", x=960, y=540, radius=180, color="#35B9FF", stroke=8)
    scene.add_text("Title", "MOTIONCODE", x=960, y=540, color="#FFFFFF", size=76)
    scene.add_cube("Wireframe cube", x=1450, y=540, size=180, color="#70D6FF")

def animate(scene, t):
    ring = scene.get("Blue ring")
    ring.rotation = t * 45
    ring.scale = 1 + 0.12 * math.sin(t * 2)
    ring.opacity = 0.75 + 0.25 * math.sin(t * 1.5)
    title = scene.get("Title")
    title.y = 540 + math.sin(t * 2) * 18
    title.opacity = min(1, t / 1.5)
    cube = scene.get("Wireframe cube")
    cube.rotation_y = t * 55
    cube.rotation_x = t * 32
    cube.opacity = 0.9
'''

STARTER_AUDIO = '''import math

def build_audio(audio):
    audio.duration = 10          # match the video length in seconds
    audio.sample_rate = 44100
    audio.master_volume = 0.8

    # A soft pad that fades in and out
    audio.add_tone("pad", freq=220, start=0, length=8, volume=0.12, fade_in=1.5, fade_out=2.0)

    # A click on each beat
    for t in [0, 2, 4, 6, 8]:
        audio.add_click(f"click_{t}", at=t, volume=0.35)
'''

SCRIPT_WORDS_ALL = PYTHON_WORDS + SCENE_WORDS

# Errors collected while running. Each one is logged once and then kept quietly.
ANIM_ERRORS = {}     # "ErrorType: message" -> {"count": int, "lines": set()}
RENDER_ERRORS = {}   # object name -> "ErrorType: message"

# Caches for work that repeats on every frame.
FONT_CACHE = {}       # (family, size, bold) -> QFont
TEXT_SIZE_CACHE = {}  # (text, size, font, bold, max_width) -> (w, h)
BG_CACHE = {}         # (gradient id, background, w, h) -> background QImage

PROFILE = {}          # seconds spent per stage during an export
EXPORT_STATS = {"frames": 0, "seconds": 0.0}


# ------------------------------------------------------------ script checks

ROTATION_ADD = re.compile(r"\.rotation(?:_[xyz])?\s*[-+*/]=")
RADIAN_USE = re.compile(r"\bmath\.pi\b|\bradians\s*\(")
ADD_NAME = re.compile(r"\badd_\w+\(\s*(['\"])(.+?)\1")
GET_NAME = re.compile(r"\bscene\.get(?:_optional)?\(\s*(['\"])(.+?)\1")


def scan_script_mistakes(source):
    """Find common mistakes in a video script before it runs.
    Returns a list of (line_number_or_None, message)."""
    found = []
    counts = {}
    created = set()
    lines = source.splitlines()
    for n, line in enumerate(lines, 1):
        code = line.split("#", 1)[0]
        if ROTATION_ADD.search(code):
            found.append((n, "rotation changed with += or -=. Assign an absolute value "
                             "(for example rotation_z = t * 45), or the object will keep "
                             "growing when you scrub the timeline."))
        if RADIAN_USE.search(code):
            found.append((n, "math.pi or radians() found. MotionCode rotations are in "
                             "degrees (90 is a quarter turn)."))
        for m in ADD_NAME.finditer(code):
            name = m.group(2)
            counts[name] = counts.get(name, 0) + 1
            created.add(name)
    for name, count in counts.items():
        if count > 1:
            found.append((None, "object name %r is created %d times. Names must be unique."
                                % (name, count)))
    for n, line in enumerate(lines, 1):
        code = line.split("#", 1)[0]
        for m in GET_NAME.finditer(code):
            name = m.group(2)
            if name not in created and "{" not in name:
                found.append((n, "scene.get(%r) but no add_ call creates that name. "
                                 "Check the spelling, or create it in build()." % name))
    return found


# ------------------------------------------------------------ error helpers

def error_lines_for(exc, filename):
    """Line numbers inside the user's script that caused an exception."""
    lines = set()
    if exc is None:
        return lines
    if isinstance(exc, SyntaxError) and exc.filename == filename and exc.lineno:
        lines.add(exc.lineno)
    try:
        for frame in traceback.extract_tb(exc.__traceback__):
            if frame.filename == filename and frame.lineno:
                lines.add(frame.lineno)
    except Exception:
        pass
    return lines


def safe_animate(fn, scene, t):
    """Run the user's animate(). A failure is recorded and the scene keeps its last state."""
    t0 = time.perf_counter()
    try:
        fn(scene, t)
        scene.apply_tracks(t)   # keyframes win over animate() for their properties
        PROFILE["animate"] = PROFILE.get("animate", 0.0) + time.perf_counter() - t0
        return True
    except Exception as exc:
        key = f"{type(exc).__name__}: {exc}"
        info = ANIM_ERRORS.setdefault(key, {"count": 0, "lines": set()})
        info["count"] += 1
        info["lines"] |= error_lines_for(exc, VIDEO_FILE)
        return False


def note_render_error(name, exc):
    RENDER_ERRORS[str(name)] = f"{type(exc).__name__}: {exc}"


# ------------------------------------------------------------ text and font helpers

def text_size(scene, obj):
    """Real text width and height in pixels, cached so it is measured once per text."""
    key = (obj.text, int(obj.size), obj.font, bool(obj.bold), obj.max_width)
    size = TEXT_SIZE_CACHE.get(key)
    if size is None:
        size = remember(TEXT_SIZE_CACHE, key,
                        scene.measure_text(obj.text, size=obj.size, font=obj.font,
                                           bold=obj.bold, max_width=obj.max_width), 512)
    return size


def cached_font(family, size, bold):
    key = (str(family), int(size), bool(bold))
    font = FONT_CACHE.get(key)
    if font is None:
        font = QFont(key[0])
        font.setPixelSize(max(1, key[1]))
        font.setBold(key[2])
        remember(FONT_CACHE, key, font, 128)
    return font


def measure_text_px(text, size, font, bold, max_width):
    """Real text size in pixels, used by scene.measure_text()."""
    f = cached_font(font, size, bold)
    fm = QFontMetrics(f)
    if max_width:
        rect = fm.boundingRect(QRect(0, 0, int(max_width), 1000000),
                               Qt.TextFlag.TextWordWrap.value, text)
    else:
        rect = fm.boundingRect(text)
    return float(rect.width()), float(rect.height())


def list_font_families():
    return list(QFontDatabase.families())


# ------------------------------------------------------------ blur and layer helpers

def fast_blur(arr, radius, use_half):
    """Blur. For large radii the blur runs on a half-size copy. The copy is made by
    averaging 2x2 blocks, so thin text keeps its shape."""
    if radius < 4 or not use_half:
        return fx.gaussian_blur(arr, radius)
    h, w = arr.shape[:2]
    ph, pw = h % 2, w % 2
    padded = np.pad(arr, ((0, ph), (0, pw), (0, 0)), mode="edge") if (ph or pw) else arr
    h2, w2 = padded.shape[0] // 2, padded.shape[1] // 2
    small = padded.reshape(h2, 2, w2, 2, arr.shape[2]).mean(axis=(1, 3)).astype(np.float32)
    blurred = fx.gaussian_blur(small, radius / 2.0)
    up = np.repeat(np.repeat(blurred, 2, axis=0), 2, axis=1)
    return up[:h, :w].astype(np.float32)


def downsample(arr, ss):
    """Scale an effect layer down by averaging ss x ss blocks (used for supersampling)."""
    if ss <= 1:
        return arr
    h, w = arr.shape[0] // ss, arr.shape[1] // ss
    arr = arr[:h * ss, :w * ss]
    return arr.reshape(h, ss, w, ss, arr.shape[2]).mean(axis=(1, 3)).astype(np.float32)


def apply_lights_quality(arr, scene, rect, sx, sy):
    """Lighting at the quality's light resolution. Full resolution uses the cached path."""
    k = max(1, int(round(1.0 / max(0.05, float(RENDER_OPTS["light_scale"])))))
    if k == 1:
        return fx.apply_lights(arr, scene, rect, sx, sy)
    xs, ys = pixel_grid(rect, sx, sy)
    small = fx.light_map(xs[::k, ::k], ys[::k, ::k], scene.lights, scene.ambient).astype(np.float32)
    bright = np.repeat(np.repeat(small, k, axis=0), k, axis=1)[:arr.shape[0], :arr.shape[1]]
    arr[..., :3] = arr[..., :3] * bright
    arr[..., :3] = np.minimum(arr[..., :3], arr[..., 3:4])
    return arr


def to_rgb32(img):
    if img.format() == QImage.Format.Format_RGB32:
        return img
    return img.convertToFormat(QImage.Format.Format_RGB32)


def object_bounds(obj, scene, sx, sy, width, height):
    """Device-pixel rectangle that contains everything the object can draw,
    including its blur margins. Returns None if it is off screen."""
    if isinstance(obj, Line):
        reach = max(abs(obj.x2), abs(obj.y2)) + obj.stroke * 2 + 4
    elif isinstance(obj, Text):
        tw, th = text_size(scene, obj)
        reach = max(tw, th) + 12
    elif isinstance(obj, MeshObject):
        reach = obj.size * obj.scale * 1.5 + obj.stroke + 4
    else:
        hw, hh = fx.local_extent(obj)
        reach = math.hypot(hw, hh) * obj.scale * max(abs(obj.scale_x), abs(obj.scale_y), 1.0) * 1.25
        reach *= 1.0 + abs(math.tan(math.radians(obj.skew_x)))
        reach += obj.stroke + 4

    reach += 3.0 * (getattr(obj, "blur", 0.0) + getattr(obj, "backdrop_blur", 0.0)) + 4

    x0 = max(0, int(math.floor((obj.x - reach) * sx)))
    y0 = max(0, int(math.floor((obj.y - reach) * sy)))
    x1 = min(width, int(math.ceil((obj.x + reach) * sx)))
    y1 = min(height, int(math.ceil((obj.y + reach) * sy)))
    if x1 <= x0 or y1 <= y0:
        return None
    return QRect(x0, y0, x1 - x0, y1 - y0)


def render_region(obj, scene, rect, sx, sy):
    """Draw one object alone into a transparent layer covering only rect.
    Returns a premultiplied float array of rect's size."""
    layer = QImage(rect.width(), rect.height(), QImage.Format.Format_RGBA8888_Premultiplied)
    layer.fill(QColor(0, 0, 0, 0))
    lp = QPainter(layer)
    try:
        lp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        lp.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        lp.scale(sx, sy)
        lp.translate(-rect.x() / sx, -rect.y() / sy)
        draw_object(lp, obj, scene)
    finally:
        lp.end()
    return fx.qimage_to_array(layer)


# ------------------------------------------------------------- drawing

def draw_object(p, obj, scene):
    """Draw one object in scene coordinates. The painter already has the scene scale applied."""
    p.setOpacity(max(0.0, min(1.0, float(obj.opacity))))
    color = QColor(obj.color)

    if isinstance(obj, MeshObject):
        pen = QPen(color, max(.5, float(getattr(obj, "stroke", 3))))
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        if getattr(obj, "filled", False) and getattr(obj, "faces", None):
            motion_fx.draw_filled_mesh(p, obj, scene)
        else:
            pts, edges = motion_fx.project_mesh(obj, scene)
            for i, j in edges:
                if 0 <= i < len(pts) and 0 <= j < len(pts):
                    p.drawLine(pts[i], pts[j])
        return

    pen = QPen(color, max(.5, float(getattr(obj, "stroke", 3))))
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    grad = getattr(obj, "gradient", None)
    if grad is not None and not getattr(obj, "filled", False) and not isinstance(obj, Text):
        pen.setBrush(fx.make_gradient_brush(grad, fx.local_extent(obj)))   # gradient outline
    p.setPen(pen)

    if getattr(obj, "filled", False):
        grad = getattr(obj, "gradient", None)
        if grad is not None and not isinstance(obj, Text):
            p.setBrush(fx.make_gradient_brush(grad, fx.local_extent(obj)))
        else:
            p.setBrush(QBrush(color))
    else:
        p.setBrush(Qt.BrushStyle.NoBrush)

    motion_fx.apply_transform(p, obj)

    if isinstance(obj, Circle):
        p.drawEllipse(QPointF(0, 0), obj.radius, obj.radius)
    elif isinstance(obj, Rect):
        p.drawRect(QRectF(-obj.width / 2, -obj.height / 2, obj.width, obj.height))
    elif isinstance(obj, Line):
        p.drawLine(QPointF(0, 0), QPointF(obj.x2, obj.y2))
    elif isinstance(obj, Text):
        p.setFont(cached_font(obj.font, obj.size, obj.bold))
        grad = getattr(obj, "gradient", None)
        if grad is not None:
            p.setPen(QPen(fx.make_gradient_brush(grad, fx.local_extent(obj)), 1))   # gradient text
        else:
            p.setPen(color)
        fm = p.fontMetrics()
        max_w = getattr(obj, "max_width", None)
        if max_w:
            align_flag = {"left": Qt.AlignmentFlag.AlignLeft,
                          "right": Qt.AlignmentFlag.AlignRight}.get(obj.align, Qt.AlignmentFlag.AlignHCenter)
            flags = align_flag.value | Qt.AlignmentFlag.AlignVCenter.value | Qt.TextFlag.TextWordWrap.value
            block_h = fm.boundingRect(QRect(0, 0, int(max_w), 1000000), flags, obj.text).height()
            left = {"left": 0.0, "right": -max_w}.get(obj.align, -max_w / 2)
            p.drawText(QRectF(left, -block_h / 2, max_w, block_h), flags, obj.text)
        else:
            tw = fm.horizontalAdvance(obj.text)
            if obj.align == "center":
                tx = -tw / 2
            elif obj.align == "right":
                tx = -tw
            else:
                tx = 0
            p.drawText(QPointF(tx, obj.size / 3), obj.text)
    elif isinstance(obj, Polygon):
        pts = [QPointF(x, y) for x, y in obj.points]
        if len(pts) >= 2:
            poly = QPolygonF(pts)
            if obj.closed:
                p.drawPolygon(poly)
            else:
                p.drawPolyline(poly)
    elif isinstance(obj, ImageAsset):
        scaled = cached_image(obj.path, int(obj.width), int(obj.height))
        if scaled is not None:
            p.drawImage(int(-scaled.width() / 2), int(-scaled.height() / 2), scaled)


def draw_one(p, obj, scene, target, ctx=None):
    """Draw one object with its effects, and with any masks that cover it.
    Plain objects go straight to the painter. Objects with effects are rendered into
    a layer covering only their bounding box, composited over what is already drawn
    there, and written back. The rest of the frame is untouched."""
    backdrop = getattr(obj, "backdrop_blur", 0.0) > 0
    lit = getattr(obj, "lit", False)
    blur = getattr(obj, "blur", 0.0)
    blur_only = getattr(obj, "mask_blur_only", False)
    blend = getattr(obj, "blend", "normal")

    shadow = getattr(obj, "shadow", None)
    if shadow and not blur_only:
        # Drop shadow: a blurred, offset, recoloured copy drawn underneath the object.
        sh = copy.copy(obj)
        sh.shadow = None
        sh.x = obj.x + float(shadow.get("dx", 8.0))
        sh.y = obj.y + float(shadow.get("dy", 8.0))
        sh.color = shadow.get("color", "#000000")
        sh.gradient = None
        sh.opacity = obj.opacity * float(shadow.get("opacity", 0.4))
        sh.blur = max(float(shadow.get("blur", 10.0)), 0.01)
        sh.backdrop_blur = 0.0
        sh.lit = False
        sh.blend = "normal"
        draw_one(p, sh, scene, target, None)
    color_masks = ctx.for_object(obj) if ctx is not None else []

    if not (backdrop or lit or blur > 0 or blur_only or color_masks or blend != "normal"):
        if not blur_only:
            draw_object(p, obj, scene)
        return

    sx = target.width() / scene.width
    sy = target.height() / scene.height
    rect = object_bounds(obj, scene, sx, sy, target.width(), target.height())
    if rect is None:
        return

    ss = int(RENDER_OPTS["supersample"])
    big = QRect(rect.x() * ss, rect.y() * ss, rect.width() * ss, rect.height() * ss)

    if blur_only:
        # A blur mask is never drawn itself. It only blurs what is already under its shape.
        if obj.backdrop_blur <= 0:
            return
        cover = render_region(pro.coverage_copy(obj), scene, big, sx * ss, sy * ss)
        mask = downsample(cover[..., 3:4].copy(), ss)
        feather = float(getattr(obj, "mask_feather", 0.0))
        if feather > 0:
            mask = fx.gaussian_blur(mask, feather * sx)   # soft edge on the blur mask
        base = fx.qimage_to_array(target.copy(rect))
        half = obj.backdrop_blur >= RENDER_OPTS["backdrop_half_above"]
        blurred = fast_blur(base, obj.backdrop_blur * sx, half)
        _write_back(p, rect, base * (1.0 - mask) + blurred * mask)
        return

    arr = render_region(obj, scene, big, sx * ss, sy * ss)
    mask = arr[..., 3:4].copy()
    if lit:
        apply_lights_quality(arr, scene, big, sx * ss, sy * ss)
    if blur > 0:
        arr = fast_blur(arr, blur * sx * ss, blur >= RENDER_OPTS["blur_half_above"])

    arr = downsample(arr, ss)
    mask = downsample(mask, ss)

    # Hide and tint masks that cover this object change its pixels before it is composited.
    for cover, strength, mode, color, feather in color_masks:
        cov = downsample(render_region(cover, scene, big, sx * ss, sy * ss)[..., 3:4], ss)
        if feather > 0:
            cov = fx.gaussian_blur(cov, feather * sx)     # soft edge
        arr = pro.composite_color_mask(arr, cov, strength, mode, color)

    # Everything already drawn in this region, including the background.
    base = fx.qimage_to_array(target.copy(rect))
    if backdrop:
        half = obj.backdrop_blur >= RENDER_OPTS["backdrop_half_above"]
        blurred = fast_blur(base, obj.backdrop_blur * sx, half)
        base = base * (1.0 - mask) + blurred * mask

    out = blend_layers(base, arr, blend)
    _write_back(p, rect, out)


def blend_layers(base, src, mode):
    """Mix a premultiplied object layer (src) into what is already drawn (base).
    normal: the usual over blend. add: light sums up. screen: lightens, never darkens.
    multiply: darkens, like overlaid ink. All work on premultiplied RGBA values 0..1."""
    if mode == "normal":
        return base * (1.0 - src[..., 3:4]) + src
    if mode == "add":
        return np.minimum(base + src, 1.0)
    if mode == "screen":
        return base + src - base * src
    if mode == "multiply":
        sa, ba = src[..., 3:4], base[..., 3:4]
        rgb = (src[..., :3] * base[..., :3]
               + src[..., :3] * (1.0 - ba) + base[..., :3] * (1.0 - sa))
        alpha = sa + ba - sa * ba
        return np.concatenate([rgb, alpha], axis=-1)
    raise ValueError("Unknown blend mode %r. Use normal, add, screen or multiply" % mode)


def post_process(image, scene):
    """Whole-frame effects, run once after the objects are drawn: chromatic aberration,
    bloom, colour grade, vignette and grain. Each one is off unless the scene sets it."""
    bloom = float(getattr(scene, "bloom", 0.0))
    vignette = float(getattr(scene, "vignette", 0.0))
    grain = float(getattr(scene, "grain", 0.0))
    grade = getattr(scene, "grade", None)
    grade_strength = float(getattr(scene, "grade_strength", 0.0))
    aberration = float(getattr(scene, "aberration", 0.0))
    if not (bloom > 0 or vignette > 0 or grain > 0 or (grade and grade_strength > 0)
            or aberration >= 0.5):
        return image

    arr = fx.qimage_to_array(image)
    h, w = arr.shape[:2]
    rgb = arr[..., :3].astype(np.float32)

    if aberration >= 0.5:
        s = int(round(aberration))
        rgb = np.stack([np.roll(rgb[..., 0], s, axis=1), rgb[..., 1],
                        np.roll(rgb[..., 2], -s, axis=1)], axis=-1)
    if bloom > 0:
        threshold = float(getattr(scene, "bloom_threshold", 0.8))
        radius = float(getattr(scene, "bloom_radius", 12.0))
        bright = np.clip(rgb - threshold, 0.0, None)
        glow = fast_blur(bright, radius, True)
        rgb = rgb + glow * bloom
    if grade and grade_strength > 0:
        tint = fx.hex_to_rgb(grade).astype(np.float32)
        k = grade_strength
        rgb = rgb * ((1.0 - k) + k * tint)
    if vignette > 0:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        dx = (xx - w / 2.0) / (w / 2.0)
        dy = (yy - h / 2.0) / (h / 2.0)
        d = np.sqrt(dx * dx + dy * dy) / math.sqrt(2.0)     # 0 at the centre, 1 at the corners
        rgb = rgb * (1.0 - vignette * np.clip((d - 0.4) / 0.6, 0.0, 1.0) ** 2)[..., None]
    if grain > 0:
        rng = np.random.default_rng(20240601)              # fixed pattern, same every frame
        rgb = rgb + rng.standard_normal((h, w, 1)).astype(np.float32) * (grain * 0.06)

    out = np.concatenate([np.clip(rgb, 0.0, 1.0), np.ones((h, w, 1), np.float32)], axis=-1)
    return fx.array_to_qimage(out.astype(np.float32)).convertToFormat(QImage.Format.Format_RGB32)


def _write_back(p, rect, out):
    p.save()
    try:
        p.resetTransform()
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.drawImage(rect.x(), rect.y(), fx.array_to_qimage(out))
    finally:
        p.restore()


def draw_error_marker(p, obj):
    """Shown in place of an object that could not be drawn. Text is drawn in red."""
    p.save()
    try:
        p.setOpacity(1.0)
        p.translate(obj.x, obj.y)
        red = QColor(ERROR_COLOR)
        if isinstance(obj, Text):
            p.setFont(cached_font("Arial", max(8, int(obj.size)), True))
            p.setPen(red)
            text = obj.text if obj.text else "?"
            width = p.fontMetrics().horizontalAdvance(text)
            p.drawText(QPointF(-width / 2, obj.size / 3), text)
        else:
            p.setPen(QPen(red, 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(0, 0), 14, 14)
    except Exception:
        pass
    finally:
        p.restore()


def draw_background(p, scene):
    grad = getattr(scene, "background_gradient", None)
    if grad is None:
        p.fillRect(0, 0, scene.width, scene.height, QColor(scene.background))
    else:
        brush = fx.make_gradient_brush(grad, (scene.width / 2, scene.height / 2))
        p.save()
        p.translate(scene.width / 2, scene.height / 2)
        p.fillRect(QRectF(-scene.width / 2, -scene.height / 2, scene.width, scene.height), brush)
        p.restore()


def background_image(scene, width, height):
    """The static background at this size, drawn once and reused for every frame."""
    grad = getattr(scene, "background_gradient", None)
    key = (id(grad), scene.background, width, height, scene.width, scene.height)
    img = BG_CACHE.get(key)
    if img is None:
        img = QImage(width, height, QImage.Format.Format_RGB32)
        img.fill(QColor(scene.background))
        bp = QPainter(img)
        try:
            bp.scale(width / scene.width, height / scene.height)
            draw_background(bp, scene)
        finally:
            bp.end()
        remember(BG_CACHE, key, img, 4)
    return img


def draw_frame(scene, width, height):
    t0 = time.perf_counter()
    img = post_process(_draw_frame_impl(scene, width, height), scene)
    PROFILE["draw"] = PROFILE.get("draw", 0.0) + time.perf_counter() - t0
    return img


def _draw_frame_impl(scene, width, height):
    """Render the scene's current state at the requested size (RGB32, opaque).
    A failing object is skipped and marked; the rest of the frame still draws."""
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(QColor(scene.background))
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        try:
            painter.drawImage(0, 0, background_image(scene, width, height))
        except Exception as exc:
            note_render_error("background", exc)
        painter.scale(width / scene.width, height / scene.height)
        ctx = pro.FrameContext(scene)   # masks and occlusion, computed once per frame
        for raw in list(scene.objects):
            try:
                obj = motion_fx.resolve_pose(raw, scene)
            except Exception as exc:
                note_render_error(getattr(raw, "name", "object"), exc)
                continue
            if float(getattr(obj, "opacity", 1.0)) <= 0:
                continue
            if obj.name in ctx.hidden:
                continue    # fully covered by a solid object drawn later: costs nothing
            # Skip objects entirely off screen. Custom OBJ meshes are not culled,
            # because their size is not known from the scene settings.
            if not (isinstance(obj, MeshObject) and obj.shape == "custom"):
                if object_bounds(obj, scene, width / scene.width, height / scene.height,
                                 width, height) is None:
                    continue
            painter.save()
            try:
                draw_one(painter, obj, scene, image, ctx)
            except Exception as exc:
                note_render_error(getattr(obj, "name", "object"), exc)
                draw_error_marker(painter, obj)
            finally:
                painter.restore()
    finally:
        if painter.isActive():
            painter.end()
    return image


def _rgb32_pixels(img):
    """Raw pixels of an RGB32 image as uint8 (h, w, 4). No float conversion."""
    w, h = img.width(), img.height()
    bpl = img.bytesPerLine()
    raw = np.frombuffer(bytes(img.constBits()), dtype=np.uint8)
    return raw.reshape(h, bpl // 4, 4)[:, :w, :]


def average_rgb32(images):
    t0 = time.perf_counter()
    img = _average_rgb32_impl(images)
    PROFILE["average"] = PROFILE.get("average", 0.0) + time.perf_counter() - t0
    return img


def _average_rgb32_impl(images):
    """Average several RGB32 frames with integer math. Much faster than float arrays,
    and the same result for display."""
    first = to_rgb32(images[0])
    w, h = first.width(), first.height()
    acc = np.zeros((h, w, 3), dtype=np.uint32)
    for img in images:
        acc += _rgb32_pixels(to_rgb32(img))[..., :3]
    out = np.empty((h, w, 4), dtype=np.uint8)
    out[..., :3] = (acc // len(images)).astype(np.uint8)
    out[..., 3] = 255
    return QImage(out.tobytes(), w, h, w * 4, QImage.Format.Format_RGB32).copy()


def motion_samples_for(scene, animate_fn, t, fps):
    """How many motion-blur sub-frames this frame needs. Slow movement needs few,
    fast movement uses the quality level's maximum."""
    cap = int(RENDER_OPTS["motion_cap"])
    moving = [o for o in scene.objects if getattr(o, "motion_blur", 0.0) > 0 and o.opacity > 0]
    if not moving or cap <= 1:
        return 1
    if int(getattr(scene, "motion_blur_samples", 4)) <= 1:
        return 1
    dt = 1.0 / fps
    now = {o.name: (o.x, o.y) for o in moving}
    safe_animate(animate_fn, scene, max(0.0, t - dt))
    before = {o.name: (o.x, o.y) for o in moving if o.name in now}
    safe_animate(animate_fn, scene, t)
    speed = 0.0
    for name, (x1, y1) in now.items():
        if name in before:
            x0, y0 = before[name]
            speed = max(speed, math.hypot(x1 - x0, y1 - y0) / dt)
    if speed < 800:
        want = min(2, cap)
    elif speed < 2000:
        want = min(4, cap)
    else:
        want = cap
    return max(1, min(want, cap))


def render_frame(scene, animate_fn, width, height, t, fps, allow_motion=True, animated=False):
    """Animate to time t and render. Motion blur only counts visible objects, and its
    sample count follows the quality level and how fast things move. Pass animated=True
    when the scene is already animated to t."""
    if not animated:
        safe_animate(animate_fn, scene, t)
    if not allow_motion:
        return to_rgb32(draw_frame(scene, width, height))
    shutter = max((getattr(o, "motion_blur", 0.0) for o in scene.objects
                   if float(getattr(o, "opacity", 1.0)) > 0), default=0.0)
    if shutter <= 0:
        return to_rgb32(draw_frame(scene, width, height))
    samples = motion_samples_for(scene, animate_fn, t, fps)
    if samples <= 1:
        return to_rgb32(draw_frame(scene, width, height))
    times = fx.motion_blur_times(t, fps, shutter=shutter, samples=samples)
    frames = []
    for tt in times:
        safe_animate(animate_fn, scene, tt)
        frames.append(draw_frame(scene, width, height))
    safe_animate(animate_fn, scene, t)
    return average_rgb32(frames)


def make_export_render():
    """Render function for export. It makes the same call the paused preview makes,
    so every exported frame matches what the preview shows at that time."""
    def render(scene, animate_fn, width, height, t, fps):
        t0 = time.perf_counter()
        img = render_frame(scene, animate_fn, width, height, t, fps)
        EXPORT_STATS["seconds"] += time.perf_counter() - t0
        EXPORT_STATS["frames"] += 1
        return img

    return render


# ------------------------------------------------------------------ audio

def safe_render_audio(audio_scene, speed, gain):
    """Mix every sound that works. A broken sound is skipped and listed in the returned
    problem list. Returns (stereo_array, problems)."""
    problems = []
    speed = max(0.05, float(speed))
    sr = int(audio_scene.sample_rate)
    duration = float(audio_scene.duration)
    if not (0.0 < duration <= 600.0):
        problems.append(f"Audio duration {duration} is invalid; using 10 seconds")
        duration = 10.0
    out_len = max(1, int(round(duration / speed * sr)))
    buf = np.zeros((out_len, 2))
    for ev in audio_scene.events:
        try:
            seg = ev.render(sr, speed)
            start = int(round(ev.start / speed * sr))
            if len(seg) == 0 or start < 0 or start >= out_len:
                continue
            end = min(out_len, start + len(seg))
            buf[start:end] += seg[:end - start]
        except Exception as exc:
            problems.append(f"Sound '{getattr(ev, 'name', '?')}' skipped: {type(exc).__name__}: {exc}")
    buf *= float(audio_scene.master_volume) * float(gain)
    return np.clip(buf, -1.0, 1.0), problems


# ------------------------------------------------------------------ app entry

def run():
    """Start the MotionCode window. The UI is imported here so that UI.py can
    import this module without a circular import."""
    from UI import Main
    app = QApplication.instance() or QApplication(sys.argv)
    window = Main()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
