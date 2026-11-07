import sys
import copy
import shutil
import math
import html
import traceback
import os
import re
import time
import tempfile
import subprocess
from pathlib import Path

import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QPlainTextEdit, QLabel, QPushButton, QSlider,
    QTreeWidget, QTreeWidgetItem, QDoubleSpinBox, QFormLayout,
    QGroupBox, QFileDialog, QMessageBox, QProgressDialog,
    QComboBox, QSpinBox, QTextEdit, QCompleter, QAbstractItemView, QListWidget, QCheckBox
)
from PySide6.QtCore import (
    Qt, QTimer, QPointF, QRectF, QRect, QSize, QUrl, Signal, QStringListModel, QThread
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QFont, QImage, QPolygonF, QGuiApplication,
    QBrush, QLinearGradient, QRadialGradient, QTextCharFormat, QTextCursor,
    QSyntaxHighlighter, QFontMetrics, QFontDatabase
)

from engine import Scene, Circle, Text, Rect, Line, MeshObject, Polygon, ImageAsset

try:
    from audio_engine import AudioScene, write_wav
    AUDIO_ENGINE_OK = True
    AUDIO_IMPORT_ERROR = ""
except Exception as _audio_error:
    AUDIO_ENGINE_OK = False
    AUDIO_IMPORT_ERROR = str(_audio_error)

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    MULTIMEDIA_OK = True
except Exception:
    MULTIMEDIA_OK = False

import motion_fx
import effects as fx
import projects_fonts as pf
import FeaturesPro as pro
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
from optimization import (ExportJob, EtaTracker, format_eta, cached_image, remember,
                          _remove_quietly, IMAGE_CACHE, pixel_grid)


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
    "low": {"label": "Low (Barely Seen)", "motion_cap": 2, "blur_half_above": 2,
            "backdrop_half_above": 2, "light_scale": 0.25, "supersample": 1},
    "medium": {"label": "Medium (Visible)", "motion_cap": 4, "blur_half_above": 6,
               "backdrop_half_above": 6, "light_scale": 0.5, "supersample": 1},
    "balanced": {"label": "Balanced (Normal)", "motion_cap": 6, "blur_half_above": 12,
                 "backdrop_half_above": 12, "light_scale": 1.0, "supersample": 1},
    "high": {"label": "High (4K Effect)", "motion_cap": 8, "blur_half_above": 1e9,
             "backdrop_half_above": 1e9, "light_scale": 1.0, "supersample": 2},
}
DEFAULT_QUALITY = "balanced"

# The render reads these. Changed by the Quality box.
RENDER_OPTS = dict(QUALITY_PRESETS[DEFAULT_QUALITY])

AUTOSAVE_DIR = os.path.join(tempfile.gettempdir(), "motioncode_autosave")
AUTOSAVE_VIDEO = os.path.join(AUTOSAVE_DIR, "video.py")
AUTOSAVE_AUDIO = os.path.join(AUTOSAVE_DIR, "audio.py")

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
    "import motion_fx as fx", "import effects as ex", "import transitions as tr",
    "motion_fx", "effects", "transitions", "Gradient", "Light", "Burst", "Trail",
    "ease_out_cubic", "ease_in_out_cubic", "ease_out_back", "ease_out_elastic",
    "ease_out_bounce", "progress", "spring", "squash_stretch", "shake", "wobble",
    "flash", "typed", "word_reveal", "enter", "exit", "fade_in", "fade_out",
    "slide_offset", "pop_scale", "zoom_scale", "visible_between",
]
AUDIO_WORDS = [
    "build_audio", "audio", "duration", "sample_rate", "master_volume", "add_tone",
    "add_noise", "add_click", "add_clip", "freq", "start", "length", "volume",
    "fade_in", "fade_out", "wave", "pan", "at", "name", "path",
    "sine", "square", "triangle", "saw", "add_speech", "add_dialogue", "voice",
    "emotion", "speed", "rate", "pitch", "piper:en_US-ryan-medium", "piper:en_US-amy-medium",
    "import voice_tts", "from voice_tts import add_speech, add_dialogue, list_voices",
]

# Errors collected while running. Each one is logged once and then kept quietly.
ANIM_ERRORS = {}     # "ErrorType: message" -> {"count": int, "lines": set()}
RENDER_ERRORS = {}   # object name -> "ErrorType: message"

# Caches for work that repeats on every frame.
FONT_CACHE = {}      # (family, size, bold) -> QFont
TEXT_SIZE_CACHE = {} # (text, size, font, bold, max_width) -> (w, h)
BG_CACHE = {}        # (gradient id, background, w, h) -> background QImage

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



# ------------------------------------------------------------ mistake scanner

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


# ------------------------------------------------------------ speed helpers

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


def frame_signature(scene):
    """Everything that affects the picture. If it is the same as the last frame, the
    picture is the same, so the last frame can be reused."""
    rows = []
    for o in scene.objects:
        op = float(getattr(o, "opacity", 1.0))
        if op <= 0:
            continue
        rows.append((
            o.name, round(op, 3), round(o.x, 2), round(o.y, 2), round(getattr(o, "z", 0.0), 2),
            round(o.scale, 3), round(getattr(o, "scale_x", 1.0), 3), round(getattr(o, "scale_y", 1.0), 3),
            round(getattr(o, "skew_x", 0.0), 2), round(o.rotation_x, 2), round(o.rotation_y, 2),
            round(o.rotation_z, 2), round(getattr(o, "blur", 0.0), 1),
            round(getattr(o, "backdrop_blur", 0.0), 1), round(getattr(o, "motion_blur", 0.0), 2),
            getattr(o, "text", None), getattr(o, "radius", None),
            getattr(o, "width", None), getattr(o, "height", None), getattr(o, "color", None),
        ))
    lights = tuple((round(l.x, 1), round(l.y, 1), round(l.radius, 1), round(l.intensity, 3))
                   for l in scene.lights)
    camera = (round(scene.camera_x, 2), round(scene.camera_y, 2),
              round(scene.camera_z, 2), round(scene.camera_fov, 2))
    return (tuple(rows), lights, round(scene.ambient, 3), camera)


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
    if grad is not None and fx is not None and not getattr(obj, "filled", False) and not isinstance(obj, Text):
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

    if motion_fx is not None:
        motion_fx.apply_transform(p, obj)
    else:
        p.translate(obj.x, obj.y)
        p.rotate(obj.rotation_z)
        p.scale(obj.scale, obj.scale)

    if isinstance(obj, Circle):
        p.drawEllipse(QPointF(0, 0), obj.radius, obj.radius)
    elif isinstance(obj, Rect):
        p.drawRect(QRectF(-obj.width / 2, -obj.height / 2, obj.width, obj.height))
    elif isinstance(obj, Line):
        p.drawLine(QPointF(0, 0), QPointF(obj.x2, obj.y2))
    elif isinstance(obj, Text):
        p.setFont(cached_font(obj.font, obj.size, obj.bold))
        grad = getattr(obj, "gradient", None)
        if grad is not None and fx is not None:
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


def _draw_one_before_masks(p, obj, scene, target):
    """Previous version of draw_one, kept only for reference. Not called anymore."""
    """Draw one object. Plain objects go straight to the painter. Objects with effects
    are rendered into a layer covering only their bounding box, composited over what
    is already drawn there, and written back. The rest of the frame is untouched."""
    backdrop = getattr(obj, "backdrop_blur", 0.0) > 0
    lit = getattr(obj, "lit", False)
    blur = getattr(obj, "blur", 0.0)

    if fx is None or not (backdrop or lit or blur > 0):
        draw_object(p, obj, scene)
        return

    sx = target.width() / scene.width
    sy = target.height() / scene.height
    rect = object_bounds(obj, scene, sx, sy, target.width(), target.height())
    if rect is None:
        return

    # Supersampling draws the effect layer at a multiple of the screen size, then scales it down.
    ss = int(RENDER_OPTS["supersample"])
    big = QRect(rect.x() * ss, rect.y() * ss, rect.width() * ss, rect.height() * ss)
    arr = render_region(obj, scene, big, sx * ss, sy * ss)
    mask = arr[..., 3:4].copy()

    if lit:
        apply_lights_quality(arr, scene, big, sx * ss, sy * ss)
    if blur > 0:
        arr = fast_blur(arr, blur * sx * ss, blur >= RENDER_OPTS["blur_half_above"])

    arr = downsample(arr, ss)
    mask = downsample(mask, ss)

    # Everything already drawn in this region, including the background.
    base = fx.qimage_to_array(target.copy(rect))
    if backdrop:
        half = obj.backdrop_blur >= RENDER_OPTS["backdrop_half_above"]
        blurred = fast_blur(base, obj.backdrop_blur * sx, half)
        base = base * (1.0 - mask) + blurred * mask

    out = base * (1.0 - arr[..., 3:4]) + arr

    p.save()
    try:
        p.resetTransform()
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.drawImage(rect.x(), rect.y(), fx.array_to_qimage(out))
    finally:
        p.restore()


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
    if shadow and fx is not None and not blur_only:
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

    if fx is None:
        if not blur_only:
            draw_object(p, obj, scene)
        return
    if not (backdrop or lit or blur > 0 or blur_only or color_masks or blend != "normal"):
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
    if fx is None:
        return image
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
        bright = np.clip(rgb - float(scene.bloom_threshold), 0.0, None)
        glow = fast_blur(bright, float(scene.bloom_radius), True)
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
    if grad is None or fx is None:
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


PROFILE = {}   # seconds spent per stage during an export: animate, draw, average


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
    if fx is None or not allow_motion:
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


EXPORT_STATS = {"frames": 0, "seconds": 0.0}


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


# ------------------------------------------------------------ widgets

class ScriptHighlighter(QSyntaxHighlighter):
    """Colours Python keywords, strings, numbers, decorators and comments."""

    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        def fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Weight.Bold)
            f.setFontItalic(italic)
            return f

        keywords = (r"\b(?:and|as|assert|break|class|continue|def|del|elif|else|except|"
                    r"finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|"
                    r"raise|return|try|while|with|yield)\b")
        constants = r"\b(?:True|False|None)\b"
        builtins = r"\b(?:abs|len|range|min|max|print|int|float|str|list|dict|round|sum|sorted|enumerate|zip|open)\b"
        self.rules.append((re.compile(builtins), fmt("#82AAFF")))
        self.rules.append((re.compile(constants), fmt("#F78C6C")))
        self.rules.append((re.compile(keywords), fmt("#C792EA", bold=True)))
        self.rules.append((re.compile(r"\b\d+(?:\.\d+)?\b"), fmt("#F78C6C")))
        self.rules.append((re.compile(r"@\w+"), fmt("#FFCB6B")))
        self.rules.append((re.compile(r"\"[^\"\\]*(?:\\.[^\"\\]*)*\"|'[^'\\]*(?:\\.[^'\\]*)*'"), fmt("#C3E88D")))
        self.rules.append((re.compile(r"#[^\n]*"), fmt("#546E7A", italic=True)))

    def highlightBlock(self, text):
        for pattern, form in self.rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), form)


class ObjectTree(QTreeWidget):
    """Scene object list. Dragging rows reorders layers."""
    reordered = Signal()

    def mousePressEvent(self, event):
        if self.itemAt(event.position().toPoint()) is None:
            self.clearSelection()
            self.setCurrentItem(None)
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.clearSelection()
            self.setCurrentItem(None)
            return
        super().keyPressEvent(event)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.reordered.emit()


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Plain text editor with line numbers and red highlighting for failing lines."""

    def __init__(self):
        super().__init__()
        self._gutter = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_margin)
        self.updateRequest.connect(self._update_gutter)
        self._update_margin(0)
        self._highlighter = ScriptHighlighter(self.document())
        self._completer = QCompleter(self)
        self._completer.setModel(QStringListModel(self))
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.activated.connect(self._insert_completion)

    def line_number_width(self):
        digits = max(3, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margin(self, _count):
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_gutter(self, rect, dy):
        if dy:
            self._gutter.scroll(0, dy)
        else:
            self._gutter.update(0, rect.y(), self._gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_margin(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._gutter.setGeometry(QRect(cr.left(), cr.top(), self.line_number_width(), cr.height()))

    def paint_line_numbers(self, event):
        painter = QPainter(self._gutter)
        try:
            painter.fillRect(event.rect(), QColor("#11151d"))
            block = self.firstVisibleBlock()
            number = block.blockNumber()
            top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
            bottom = top + round(self.blockBoundingRect(block).height())
            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    painter.setPen(QColor("#5d6679"))
                    painter.drawText(0, top, self._gutter.width() - 6, self.fontMetrics().height(),
                                     Qt.AlignmentFlag.AlignRight, str(number + 1))
                block = block.next()
                top = bottom
                bottom = top + round(self.blockBoundingRect(block).height())
                number += 1
        finally:
            painter.end()

    def set_error_lines(self, lines):
        """Show the given 1-based line numbers in red."""
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(ERROR_COLOR))
        fmt.setBackground(QColor("#3a1116"))
        selections = []
        doc = self.document()
        for number in sorted(lines):
            block = doc.findBlockByNumber(number - 1)
            if not block.isValid():
                continue
            cursor = QTextCursor(block)
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = fmt
            selections.append(selection)
        self.setExtraSelections(selections)

    # ---- autocomplete: type two letters or press Ctrl+Space -------------

    def set_completion_words(self, words):
        self._completer.model().setStringList(sorted(set(words), key=str.lower))

    def _text_under_cursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.SelectionType.WordUnderCursor)
        return tc.selectedText()

    def _insert_completion(self, completion):
        if self._completer.widget() is not self:
            return
        prefix_len = len(self._completer.completionPrefix())
        extra = len(completion) - prefix_len
        if extra <= 0:
            return
        tc = self.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.Left)
        tc.movePosition(QTextCursor.MoveOperation.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def keyPressEvent(self, event):
        popup = self._completer.popup()
        if popup.isVisible() and event.key() in (
                Qt.Key.Key_Enter, Qt.Key.Key_Return, Qt.Key.Key_Escape,
                Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            event.ignore()
            return

        ctrl_space = (event.key() == Qt.Key.Key_Space
                      and bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
        if not ctrl_space:
            super().keyPressEvent(event)

        typed = event.text() or ""
        typing_word = typed.isalnum() or typed == "_"
        if not (ctrl_space or typing_word):
            popup.hide()
            return
        prefix = self._text_under_cursor()
        if not ctrl_space and len(prefix) < 2:
            popup.hide()
            return
        self._completer.setCompletionPrefix(prefix)
        model_index = self._completer.completionModel().index(0, 0)
        if not model_index.isValid():
            popup.hide()
            return
        popup.setCurrentIndex(model_index)
        rect = self.cursorRect()
        rect.setWidth(popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width())
        self._completer.complete(rect)


class Preview(QWidget):
    """Shows the scene. It renders at the size of the box it is shown in (never larger
    than the chosen resolution), so a small preview costs less."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = Scene()
        self.render_w, self.render_h = 1280, 720
        self.render_fn = None
        self._cache = None
        self._cache_key = None
        self.setMinimumSize(320, 180)

    def set_resolution(self, width, height):
        self.render_w, self.render_h = width, height
        self._cache = None
        self.update()

    def set_scene(self, scene):
        self.scene = scene
        self._cache = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.fillRect(self.rect(), QColor("#11141b"))
            if not self.scene:
                return
            dpr = self.devicePixelRatioF()
            box_w = max(1, int(self.width() * dpr))
            box_h = max(1, int(self.height() * dpr))
            k = min(box_w / self.render_w, box_h / self.render_h, 1.0)
            rw = max(2, int(self.render_w * k) & ~1)
            rh = max(2, int(self.render_h * k) & ~1)
            key = (rw, rh)
            if self._cache is None or self._cache_key != key:
                if self.render_fn is not None:
                    self._cache = self.render_fn(rw, rh)
                else:
                    self._cache = draw_frame(self.scene, rw, rh)
                self._cache_key = key
            frame = self._cache
            scale = min(self.width() / frame.width(), self.height() / frame.height())
            w, h = frame.width() * scale, frame.height() * scale
            ox = (self.width() - w) / 2
            oy = (self.height() - h) / 2
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawImage(QRectF(ox, oy, w, h), frame)
        except Exception:
            # The preview can never take the app down; fall back to an empty frame.
            self.render_fn = None
            self._cache = None
            traceback.print_exc()
        finally:
            if painter.isActive():
                painter.end()


class TimelineSlider(QSlider):
    """Thin timeline line. Keyframe times are drawn as diamonds on the line."""
    MARGIN = 9

    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)
        self._times = []
        self._duration = 1.0
        self.setFixedHeight(22)

    def set_keyframes(self, times, duration):
        self._times = sorted(set(float(t) for t in times))
        self._duration = max(1e-6, float(duration))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            m = self.MARGIN
            span = max(1, self.width() - 2 * m)
            cy = self.height() / 2
            span_range = max(1, self.maximum() - self.minimum())
            frac = (self.value() - self.minimum()) / span_range
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#2a3142"))
            painter.drawRoundedRect(QRectF(m, cy - 2, span, 4), 2, 2)
            painter.setBrush(QColor("#5aa9ff"))
            painter.drawRoundedRect(QRectF(m, cy - 2, span * frac, 4), 2, 2)
            painter.setBrush(QColor("#FFB454"))
            d = 4.5
            for t in self._times:
                if 0 <= t <= self._duration:
                    x = m + t / self._duration * span
                    painter.drawPolygon(QPolygonF([QPointF(x, cy - d), QPointF(x + d, cy),
                                                   QPointF(x, cy + d), QPointF(x - d, cy)]))
            painter.setBrush(QColor("#e8eef9"))
            painter.drawEllipse(QPointF(m + frac * span, cy), 6, 6)
        finally:
            painter.end()


class TimelineMarkers(QWidget):
    """Small triangles above the time slider, one for each keyframe time."""
    HANDLE = 8

    def __init__(self):
        super().__init__()
        self._times = []
        self._duration = 1.0
        self.setFixedHeight(10)
        self.setToolTip("Keyframe times")

    def set_times(self, times, duration):
        self._times = sorted(set(float(t) for t in times))
        self._duration = max(1e-6, float(duration))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#FFB454"))
            span = max(1, self.width() - 2 * self.HANDLE)
            for t in self._times:
                if 0 <= t <= self._duration:
                    x = self.HANDLE + t / self._duration * span
                    painter.drawPolygon(QPolygonF([QPointF(x - 4, 10), QPointF(x + 4, 10), QPointF(x, 3)]))
        finally:
            painter.end()



def keyframe_summary(scene):
    """Text listing every keyframed property and its times, for the timeline tooltip."""
    if not scene.tracks:
        return "No keyframes"
    lines = ["Keyframes:"]
    for track in scene.tracks:
        times = ", ".join("%.2fs" % t for t, _ in track.points)
        lines.append("%s.%s at %s" % (track.name, track.prop, times))
    return "\n".join(lines)


# ------------------------------------------------------------ text windows

class AdaptiveTextWindow(QWidget):
    """A text window that fits its text to the window size. Markdown is rendered by Qt,
    so tables, lists and links show properly. Plain text is escaped. When the text
    would become too small to read, it stops at MIN_PX and the window scrolls."""

    MIN_PX = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QTextBrowser, QFrame
        self.resize(760, 520)
        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        self.browser.setFrameShape(QFrame.Shape.NoFrame)
        self.browser.setStyleSheet("QTextBrowser{background:#11151d;color:#e8eef9;}")
        self.browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser)
        self._source = ""
        self._is_md = False

    def show_file(self, path, title):
        self.setWindowTitle(title)
        self._is_md = path.lower().endswith(".md")
        self.browser.setSearchPaths([os.path.dirname(path)])
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                self._source = f.read()
        except OSError:
            self._source = f"{os.path.basename(path)} could not be read."
            self._is_md = False
        self._fit()

    def _set_content(self, px):
        """Load the text into the browser at base size px."""
        doc = self.browser.document()
        if self._is_md:
            self.browser.setMarkdown(self._source)
        else:
            escaped = html.escape(self._source).replace("\n", "<br>")
            self.browser.setHtml(f"<pre style='font-size:{px}px; white-space:pre-wrap;'>{escaped}</pre>")
        font = self.browser.font()
        font.setPixelSize(px)
        self.browser.setFont(font)
        doc.setDefaultFont(font)

    def _fit(self):
        """Largest base font size where the text fits this window. Never below MIN_PX."""
        if not self._source:
            return
        doc = self.browser.document()
        doc.setDocumentMargin(0)
        avail_w = max(40, self.browser.viewport().width() - 20)
        avail_h = max(40, self.browser.viewport().height() - 20)

        def height_at(px):
            self._set_content(px)
            doc.setTextWidth(avail_w)
            return doc.size().height()

        lo, hi, best = self.MIN_PX, 120, self.MIN_PX
        while lo <= hi:
            mid = (lo + hi) // 2
            if height_at(mid) <= avail_h:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        self._set_content(best)
        doc.setTextWidth(avail_w)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MotionCode")
        self._fit_window_to_screen()
        self.scene = Scene()
        self.t = 0.0
        self.playing = False
        self.speed = 1.0
        self._last_tick = None
        self.animate_fn = lambda s, t: None
        self._quality_dependent = False   # True if the script's build() read Quality

        self.audio_scene = None
        self._player = None
        self._audio_out = None
        self._has_track = False
        self._preview_path = None
        self._wav_counter = 0
        self._logged = set()
        self._video_lines = set()
        self._audio_lines = set()
        self._preview_scale = 1.0      # adaptive preview size while playing (0.25 to 1.0)

        # Settings controls are created first so the preview can read them.
        self.res_combo = QComboBox()
        for name, w, h in RESOLUTIONS:
            self.res_combo.addItem(f"{name} ({w}×{h})", (w, h))
        self.res_combo.setCurrentIndex(3)      # 720p
        self.res_combo.currentIndexChanged.connect(self.resolution_changed)

        self.quality_combo = QComboBox()
        for key, preset in QUALITY_PRESETS.items():
            self.quality_combo.addItem(preset["label"], key)
        self.quality_combo.setCurrentIndex(list(QUALITY_PRESETS).index(DEFAULT_QUALITY))
        self.quality_combo.setToolTip(
            "Changes only the heavy effects: motion blur, blur, frosted glass and lights. "
            "Every object is always drawn.")
        self.quality_combo.currentIndexChanged.connect(self.quality_changed)

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(FPS_MIN, FPS_MAX)
        self.fps_spin.setValue(24)
        self.fps_spin.setToolTip(f"Frames per second ({FPS_MIN}–{FPS_MAX}), used for export")
        self.fps_spin.valueChanged.connect(self.fps_changed)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 10.0)
        self.speed_spin.setDecimals(2)
        self.speed_spin.setSingleStep(0.25)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setToolTip("Playback speed. 1.0 is real time. Exports follow this speed too.")
        self.speed_spin.valueChanged.connect(self.speed_changed)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(VOLUME_MIN, VOLUME_MAX)
        self.volume_slider.setValue(100)
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(VOLUME_MIN, VOLUME_MAX)
        self.volume_spin.setValue(100)
        self.volume_spin.setSuffix("%")
        self.volume_spin.setToolTip("Volume from 0% to 150%. Above 100% can clip.")
        self.volume_slider.valueChanged.connect(self._volume_slider_moved)
        self.volume_spin.valueChanged.connect(self._volume_spin_changed)
        self._volume_timer = QTimer(self)
        self._volume_timer.setSingleShot(True)
        self._volume_timer.timeout.connect(self._reload_audio_preview)

        self.encoder_combo = QComboBox()
        self.encoder_combo.addItem("CPU (libx264)", "cpu")
        self.encoder_combo.addItem("NVIDIA GPU (h264_nvenc)", "nvenc")
        self.encoder_combo.setToolTip("Encoder for MP4 export. NVIDIA needs an NVENC-capable GPU.")


        self._setup_player()
        self.fonts_loaded = pf.load_project_fonts()

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        bar = QHBoxLayout()
        apply_button = QPushButton("Apply Code")
        apply_button.clicked.connect(self.apply_all)
        bar.addWidget(apply_button)
        self.font_button = pf.FontLibraryButton(self, self.log, self._fonts_installed)
        bar.addWidget(self.font_button)
        font_folder_button = QPushButton("Font Folder")
        font_folder_button.clicked.connect(self._open_font_folder)
        bar.addWidget(font_folder_button)
        self._build_file_menu()
        self._build_credits_menu()
        bar.addStretch()
        self.status = QLabel("Ready")
        bar.addWidget(self.status)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(6)
        layout.addLayout(bar, 0)

        split = QSplitter(Qt.Orientation.Horizontal)

        editors = QSplitter(Qt.Orientation.Horizontal)

        video_panel = QWidget()
        vp = QVBoxLayout(video_panel)
        vp.setContentsMargins(0, 0, 0, 0)
        vp.addWidget(QLabel("Video script"))
        self.editor = CodeEditor()
        self.editor.setPlainText(STARTER)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setTabStopDistance(4 * self.editor.fontMetrics().horizontalAdvance(" "))
        self.editor.setUndoRedoEnabled(True)
        self.editor.setStyleSheet("QPlainTextEdit{background:#171b24;color:#d9e2f2;font-family:Consolas;font-size:13px;}")
        vp.addWidget(self.editor, 1)
        editors.addWidget(video_panel)

        audio_panel = QWidget()
        ap = QVBoxLayout(audio_panel)
        ap.setContentsMargins(0, 0, 0, 0)
        audio_head = QHBoxLayout()
        audio_head.addWidget(QLabel("Audio script"))
        audio_head.addStretch()
        apply_audio_button = QPushButton("Apply Audio")
        apply_audio_button.clicked.connect(self.apply_audio)
        audio_head.addWidget(apply_audio_button)
        ap.addLayout(audio_head)
        self.audio_editor = CodeEditor()
        self.audio_editor.setPlainText(STARTER_AUDIO)
        self.audio_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.audio_editor.setTabStopDistance(4 * self.audio_editor.fontMetrics().horizontalAdvance(" "))
        self.audio_editor.setUndoRedoEnabled(True)
        self.audio_editor.setStyleSheet("QPlainTextEdit{background:#171b24;color:#d9e2f2;font-family:Consolas;font-size:13px;}")
        ap.addWidget(self.audio_editor, 1)
        editors.addWidget(audio_panel)
        editors.setSizes([330, 330])
        split.addWidget(editors)

        right = QSplitter(Qt.Orientation.Vertical)
        self.preview = Preview()
        self.preview.set_resolution(*self.res_combo.currentData())
        self.preview.render_fn = self._render_preview
        right.addWidget(self.preview)
        lower = QWidget()
        lv = QVBoxLayout(lower)
        controls = QHBoxLayout()
        self.play = QPushButton("▶ Play")
        self.play.clicked.connect(self.toggle)
        controls.addWidget(self.play)
        self.time_label = QLabel("0.00s / 0.00s")
        controls.addWidget(self.time_label)
        self.slider = TimelineSlider()
        self.slider.setRange(0, 1000)
        self.slider.valueChanged.connect(self.scrub)
        controls.addWidget(self.slider)
        lv.addLayout(controls)

        bottom = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.tree = ObjectTree()
        self.tree.setHeaderLabels(["Scene objects (top = front)"])
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.setToolTip("Drag to change layer order. Top of the list is drawn in front.")
        self.tree.itemSelectionChanged.connect(self.select_object)
        self.tree.reordered.connect(self._tree_reordered)
        self._tree_key = None
        self._scene_gen = 0            # bumped whenever the scene changes
        self._frame_cache = {}         # (scene generation, time, size) -> preview frame
        self._animated_key = None      # (time, scene generation) the scene is animated to
        self._export_job = None
        self._export_dialog = None
        self._export_tracker = None
        self._export_title = ""
        self._export_total = 1
        left_layout.addWidget(self.tree, 1)
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(300)
        self.log_box.setMaximumHeight(64)
        self.log_box.setFont(QFont("Consolas", 8))
        self.log_box.setStyleSheet("QPlainTextEdit{background:#0f1218;color:#8d98ab;border:1px solid #232938;}")
        left_layout.addWidget(self.log_box)
        bottom.addWidget(left)

        self.settings = QGroupBox("Settings")
        settings_form = QFormLayout(self.settings)
        settings_form.addRow("Resolution", self.res_combo)
        settings_form.addRow("Quality", self.quality_combo)
        settings_form.addRow("FPS", self.fps_spin)
        settings_form.addRow("Speed", self.speed_spin)
        settings_form.addRow("Encoder", self.encoder_combo)
        volume_row = QWidget()
        volume_layout = QHBoxLayout(volume_row)
        volume_layout.setContentsMargins(0, 0, 0, 0)
        volume_layout.addWidget(self.volume_slider, 1)
        volume_layout.addWidget(self.volume_spin)
        settings_form.addRow("Volume", volume_row)
        bottom.addWidget(self.settings)

        self.inspector = QGroupBox("Object Inspector")
        self.form = QFormLayout(self.inspector)
        bottom.addWidget(self.inspector)
        lv.addWidget(bottom)
        right.addWidget(lower)
        right.setStretchFactor(0, 1)
        right.setStretchFactor(1, 0)
        right.setSizes([640, 230])
        # Assets panel, to the right of the preview.
        os.makedirs(ASSETS_DIR, exist_ok=True)
        assets_panel = QWidget()
        av = QVBoxLayout(assets_panel)
        assets_head = QHBoxLayout()
        assets_head.addWidget(QLabel("Assets"))
        assets_head.addStretch(1)
        import_button = QPushButton("Import…")
        import_button.clicked.connect(self.import_assets)
        assets_head.addWidget(import_button)
        av.addLayout(assets_head)
        self.asset_list = QListWidget()
        self.asset_list.setToolTip("Double-click to preview. In the audio script use "
                                   "audio.add_clip(\"Name\", \"file.mp3\", at=0.0)")
        self.asset_list.itemDoubleClicked.connect(self.preview_asset)
        av.addWidget(self.asset_list, 1)
        self.asset_hint = QLabel("Imported files go in the assets folder.")
        self.asset_hint.setWordWrap(True)
        av.addWidget(self.asset_hint)
        preview_area = QSplitter(Qt.Orientation.Horizontal)
        preview_area.addWidget(right)
        preview_area.addWidget(assets_panel)
        preview_area.setSizes([900, 260])
        split.addWidget(preview_area)
        self.refresh_assets()
        split.setSizes([640, 640])
        layout.addWidget(split, 1)

        self.log("MotionCode started")
        if self.fonts_loaded:
            self.log("Fonts loaded: " + ", ".join(self.fonts_loaded))
        if not AUDIO_ENGINE_OK:
            self.log("Audio engine unavailable: " + AUDIO_IMPORT_ERROR, error=True)
        elif not MULTIMEDIA_OK:
            self.log("Audio preview unavailable: PySide6.QtMultimedia could not be loaded", error=True)
        if motion_fx is None:
            self.log("motion_fx.py not found: stretch and skew are disabled", error=True)
        if fx is None:
            self.log("effects.py not found: gradients, lights and blur are disabled", error=True)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start(5000)
        self.apply_all()
        QTimer.singleShot(0, self._offer_recovery)

    # ------------------------------------------------------------------ helpers

    def _build_file_menu(self):
        file_menu = self.menuBar().addMenu("File")
        for label, fn in [("New", self.new), ("Open Project…", self.open_project),
                          ("Save Project", self.save_project),
                          ("Save Project As…", self.save_project_as)]:
            action = file_menu.addAction(label)
            action.triggered.connect(fn)
        file_menu.addSeparator()
        check = file_menu.addAction("Check script")
        check.triggered.connect(self.check_video)
        export_menu = file_menu.addMenu("Export")
        png = export_menu.addAction("PNG frames…")
        png.triggered.connect(self.export_png)
        wav = export_menu.addAction("WAV audio…")
        wav.triggered.connect(self.export_wav)
        mp4 = export_menu.addAction("MP4 video…")
        mp4.triggered.connect(lambda: self.export_video(".mp4"))
        self._export_menu = export_menu

    def _build_credits_menu(self):
        credits_menu = self.menuBar().addMenu("Credits")
        credits_menu.addAction("Credits", self._show_credits)
        credits_menu.addSeparator()
        credits_menu.addAction("My License", lambda: self._open_legal_file("LICENSE"))
        credits_menu.addSeparator()
        credits_menu.addAction("Notice", lambda: self._open_legal_file("NOTICE"))
        credits_menu.addSeparator()
        credits_menu.addAction("Third Party Notices",
                               lambda: self._open_legal_file("THIRD_PARTY_NOTICES.md"))
        self._credits_menu = credits_menu

    def _show_credits(self):
        self._show_text_window("_credits_window", "CREDITS.md", "MotionCode Credits")

    def _open_legal_file(self, filename):
        self._show_text_window("_legal_window", filename, f"MotionCode Legal - {filename}")

    def _show_text_window(self, attr, filename, title):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        if not os.path.exists(path):
            self.log(f"{filename} was not found in the MotionCode folder.", error=True)
            return
        window = getattr(self, attr, None)
        if window is None:
            window = AdaptiveTextWindow()
            setattr(self, attr, window)
        window.show_file(path, title)
        window.show()
        window.raise_()
        window.activateWindow()
        self.log(f"Showing {filename}")

    def _fit_window_to_screen(self):
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(1200, 760)
            return
        area = screen.availableGeometry()
        w = min(1280, int(area.width() * 0.85))
        h = min(800, int(area.height() * 0.85))
        self.resize(w, h)
        self.move(area.x() + (area.width() - w) // 2, area.y() + (area.height() - h) // 2)

    def log(self, message, error=False):
        stamp = time.strftime('%H:%M:%S')
        if error:
            self.log_box.appendHtml(
                f'<span style="color:{ERROR_COLOR}">[{stamp}] {html.escape(message)}</span>')
        else:
            self.log_box.appendPlainText(f"[{stamp}] {message}")

    def current_resolution(self):
        return self.res_combo.currentData()

    def current_fps(self):
        return int(self.fps_spin.value())

    def current_quality(self):
        return self.quality_combo.currentData() or DEFAULT_QUALITY

    def volume_gain(self):
        return max(VOLUME_MIN, min(VOLUME_MAX, int(self.volume_spin.value()))) / 100.0

    def refresh_assets(self):
        self.asset_list.clear()
        if os.path.isdir(ASSETS_DIR):
            for name in sorted(os.listdir(ASSETS_DIR), key=str.lower):
                if os.path.isfile(os.path.join(ASSETS_DIR, name)):
                    self.asset_list.addItem(name)

    def import_assets(self):
        """Copy any file the user picks into the assets folder. Nothing is filtered out."""
        paths, _ = QFileDialog.getOpenFileNames(self, "Import assets", "", "All files (*)")
        if not paths:
            return
        os.makedirs(ASSETS_DIR, exist_ok=True)
        imported = []
        for source in paths:
            base = os.path.basename(source)
            stem, ext = os.path.splitext(base)
            target = os.path.join(ASSETS_DIR, base)
            counter = 2
            while os.path.exists(target) and os.path.abspath(target) != os.path.abspath(source):
                target = os.path.join(ASSETS_DIR, f"{stem}_{counter}{ext}")
                counter += 1
            try:
                if os.path.abspath(target) != os.path.abspath(source):
                    shutil.copy2(source, target)
                imported.append(os.path.basename(target))
            except OSError as exc:
                self.log(f"Import failed for {base}: {exc}", error=True)
        self.refresh_assets()
        for name in imported:
            self.log(f"Imported {name}. In the audio script: audio.add_clip(\"{name}\", \"{name}\", at=0.0)")

    def preview_asset(self, item):
        """Double-click an asset to hear it. Audio files only; other files are ignored."""
        if not MULTIMEDIA_OK:
            self.log("Asset preview needs Qt Multimedia, which is not available here", error=True)
            return
        path = os.path.join(ASSETS_DIR, item.text())
        if not hasattr(self, "_asset_player") or self._asset_player is None:
            self._asset_player = QMediaPlayer(self)
            self._asset_output = QAudioOutput(self)
            self._asset_player.setAudioOutput(self._asset_output)
        self._asset_player.setSource(QUrl.fromLocalFile(path))
        self._asset_player.play()
        self.log(f"Playing {item.text()}")

    def _edited(self, target, key, value):
        setattr(target, key, value)
        self._scene_gen += 1
        self._frame_cache.clear()

    def _render_preview(self, w, h):
        """Preview frame at the size the preview box needs. While playing, the size
        adapts so each frame finishes in time. Every object is always drawn."""
        animated = self._animated_key == (self.t, self._scene_gen)
        if self.playing:
            pw = max(160, int(w * self._preview_scale) & ~1)
            ph = max(90, int(h * self._preview_scale) & ~1)
            t0 = time.perf_counter()
            frame = render_frame(self.scene, self.animate_fn, pw, ph,
                                 self.t, self.current_fps(), allow_motion=False, animated=animated)
            ms = (time.perf_counter() - t0) * 1000.0
            if ms > 30:
                self._preview_scale = max(0.25, self._preview_scale * 0.85)
            elif ms < 12:
                self._preview_scale = min(1.0, self._preview_scale * 1.05)
            return frame
        key = (self._scene_gen, round(self.t, 4), w, h)
        frame = self._frame_cache.get(key)
        if frame is None:
            frame = render_frame(self.scene, self.animate_fn, w, h, self.t, self.current_fps(),
                                 animated=animated)
            remember(self._frame_cache, key, frame, 12)
        return frame

    def resolution_changed(self, _index=None):
        w, h = self.current_resolution()
        self.preview.set_resolution(w, h)
        self.log(f"Preview resolution set to {w}×{h}")
        self.update_at(self.t)

    def quality_changed(self, _index=None):
        if self._export_job is not None:
            return
        key = self.current_quality()
        RENDER_OPTS.update(QUALITY_PRESETS[key])
        pro.set_quality(key)
        self._frame_cache.clear()
        self.log(f"Quality set to {QUALITY_PRESETS[key]['label']}")
        if self._quality_dependent:
            self.apply_all()   # the script built layers at the old quality, so rebuild
        else:
            self.update_at(self.t)   # effects read Quality at render time: just redraw

    def fps_changed(self, value):
        self.log(f"Export frame rate set to {value} fps")

    def speed_changed(self, value):
        self.speed = float(value)
        self.log(f"Playback speed set to {self.speed:.2f}x")
        self._reload_audio_preview()

    def _volume_slider_moved(self, value):
        self.volume_spin.blockSignals(True)
        self.volume_spin.setValue(value)
        self.volume_spin.blockSignals(False)
        self._volume_timer.start(250)

    def _volume_spin_changed(self, value):
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(value)
        self.volume_slider.blockSignals(False)
        self._volume_timer.start(250)

    def _flush_errors(self):
        """Log each new error once, and highlight the script lines that caused it."""
        for key, info in list(ANIM_ERRORS.items()):
            tag = "anim:" + key
            if tag not in self._logged:
                self._logged.add(tag)
                self.log(f"Animation error: {key}. The rest of the scene keeps running.", error=True)
            new_lines = info["lines"] - self._video_lines
            if new_lines:
                self._video_lines |= new_lines
                self.editor.set_error_lines(self._video_lines)
        for name, message in list(RENDER_ERRORS.items()):
            tag = "render:" + name + message
            if tag not in self._logged:
                self._logged.add(tag)
                self.log(f"Object '{name}' could not be drawn: {message}", error=True)

    def _script_failed(self, kind, exc):
        """A script could not run. The previous working version stays in use."""
        filename = VIDEO_FILE if kind == "video" else AUDIO_FILE
        lines = error_lines_for(exc, filename)
        if kind == "video":
            self._video_lines = lines
            self.editor.set_error_lines(lines)
        else:
            self._audio_lines = lines
            self.audio_editor.set_error_lines(lines)
        self.log(f"{kind.title()} script error: {type(exc).__name__}: {exc}. "
                 f"Keeping the previous {kind} running.", error=True)
        self.status.setText(f"{kind.title()} script error (previous version still running)")

    # ------------------------------------------------------------ audio preview

    def _setup_player(self):
        if not MULTIMEDIA_OK:
            return
        try:
            self._player = QMediaPlayer(self)
            self._audio_out = QAudioOutput(self)
            self._audio_out.setVolume(1.0)   # volume is applied to the rendered track
            self._player.setAudioOutput(self._audio_out)
        except Exception as exc:
            self._player = None
            self.log(f"Audio preview could not start: {exc}. The rest of the app still works.", error=True)

    def _refresh_audio_preview(self):
        self._has_track = False
        if self._player is None:
            return
        self._player.stop()
        if not AUDIO_ENGINE_OK or self.audio_scene is None or not self.audio_scene.events:
            self._player.setSource(QUrl())
            return
        try:
            stereo, problems = safe_render_audio(self.audio_scene, self.speed, self.volume_gain())
            for problem in problems:
                self.log(problem, error=True)
            self._wav_counter += 1
            path = os.path.join(tempfile.gettempdir(),
                                f"motioncode_audio_{os.getpid()}_{self._wav_counter}.wav")
            write_wav(path, stereo, self.audio_scene.sample_rate)
            self._player.setSource(QUrl.fromLocalFile(path))
            self._has_track = True
            old = self._preview_path
            self._preview_path = path
            if old:
                try:
                    os.remove(old)
                except OSError:
                    pass
        except Exception as exc:
            self.log(f"Audio preview error: {type(exc).__name__}: {exc}. Playing without sound.", error=True)
            try:
                self._player.setSource(QUrl())
            except Exception:
                pass

    def _reload_audio_preview(self):
        was_playing = self.playing
        self._refresh_audio_preview()
        self._sync_audio(force=True)
        if self._has_track and was_playing:
            self._player.play()

    def _sync_audio(self, force=False):
        if not self._has_track or self._player is None:
            return
        try:
            if self._player.source().isEmpty():
                return
            target = int(self.t / self.speed * 1000)
            if force or abs(self._player.position() - target) > 200:
                self._player.setPosition(target)
        except Exception:
            pass

    # -------------------------------------------------------------- script run

    def apply_all(self):
        if self._export_job is not None:
            self.log("Finish the export before applying code", error=True)
            return
        self.apply()
        self.apply_audio()

    def apply(self):
        source = self.editor.toPlainText()
        cleaned, ignored = [], []
        for line_no, line in enumerate(source.splitlines(), 1):
            if re.match(r"^\s*(?:@echo\s+off|color\s+[0-9a-fA-F]{2}|title\s+.+|pause)\s*$", line, re.I):
                ignored.append(line_no)
                cleaned.append("# MotionCode ignored Windows batch command: " + line.strip())
            else:
                cleaned.append(line)
        source = "\n".join(cleaned)

        namespace = {"math": math, "__name__": "__motioncode__"}
        try:
            exec(compile(source, VIDEO_FILE, "exec"), namespace, namespace)
        except Exception as exc:
            self._script_failed("video", exc)
            return

        build = namespace.get("build")
        if not callable(build):
            self._script_failed("video", RuntimeError("Your script must define build(scene)."))
            return

        candidate = Scene()
        candidate.text_measurer = measure_text_px
        candidate.font_lister = list_font_families
        pro.QUALITY["read"] = False
        build_error = None
        try:
            build(candidate)
        except Exception as exc:
            build_error = exc
        if build_error is not None and not candidate.objects:
            self._script_failed("video", build_error)
            return

        self._quality_dependent = bool(pro.QUALITY.get("read"))
        # Fix settings that would stop playback, instead of refusing the whole script.
        if candidate.duration <= 0:
            self.log("Scene duration must be positive. Using 10 seconds.", error=True)
            candidate.duration = 10.0
        if candidate.fps <= 0:
            self.log("Scene fps must be positive. Using 24 fps.", error=True)
            candidate.fps = 24

        for obj in candidate.objects:
            raw_name = str(getattr(obj, "name", ""))
            aliases = {raw_name, raw_name.lower()}
            normalized = re.sub(r"[^0-9a-zA-Z_]+", "_", raw_name).strip("_").lower()
            if normalized:
                aliases.add(normalized)
            for alias in aliases:
                if alias.isidentifier() and alias not in namespace:
                    namespace[alias] = obj

        animate = namespace.get("animate")
        if not callable(animate):
            self.log("No animate(scene, t) found. Objects will stay still.", error=True)
            animate = lambda scene, t: None

        ANIM_ERRORS.clear()
        RENDER_ERRORS.clear()
        self._logged.clear()
        self.scene = candidate
        self.animate_fn = animate
        self._scene_gen += 1
        self._frame_cache.clear()
        self.t = min(max(0.0, self.t), candidate.duration)
        self._refresh_completions()
        self.slider.set_keyframes([t for track in candidate.tracks for t, _ in track.points],
                                  candidate.duration)
        self.slider.setToolTip(keyframe_summary(candidate))

        self._video_lines = error_lines_for(build_error, VIDEO_FILE) if build_error else set()
        self.editor.set_error_lines(self._video_lines)

        self.fps_spin.blockSignals(True)
        self.fps_spin.setValue(max(FPS_MIN, min(FPS_MAX, int(round(candidate.fps)))))
        self.fps_spin.blockSignals(False)

        self.update_at(self.t)
        note = (" | ignored batch lines " + ", ".join(map(str, ignored))) if ignored else ""
        self.log(f"Video script applied: {len(candidate.objects)} objects, {candidate.duration}s duration")
        if build_error is not None:
            self.log(f"Build error: {type(build_error).__name__}: {build_error}. "
                     f"Showing everything that was built before the error.", error=True)
            self.status.setText("Applied with errors (see log)")
        else:
            self.status.setText("Code applied | {} objects{}".format(len(candidate.objects), note))
        if ignored:
            self.log("Ignored batch lines: " + ", ".join(map(str, ignored)))

    def apply_audio(self):
        if not AUDIO_ENGINE_OK:
            self.log("Audio not applied: audio engine unavailable", error=True)
            return
        source = self.audio_editor.toPlainText()
        namespace = {"math": math, "__name__": "__motioncode_audio__"}
        try:
            exec(compile(source, AUDIO_FILE, "exec"), namespace, namespace)
        except Exception as exc:
            self._script_failed("audio", exc)
            return

        build_audio = namespace.get("build_audio")
        if not callable(build_audio):
            self._script_failed("audio", RuntimeError("Your audio script must define build_audio(audio)."))
            return

        scene = AudioScene()
        build_error = None
        try:
            build_audio(scene)
        except Exception as exc:
            build_error = exc

        # Keep everything that was built, even if a later line failed.
        self.audio_scene = scene
        self._audio_lines = error_lines_for(build_error, AUDIO_FILE) if build_error else set()
        self.audio_editor.set_error_lines(self._audio_lines)
        self._refresh_audio_preview()
        self._sync_audio(force=True)
        self.log(f"Audio script applied: {len(scene.events)} sound events, {scene.duration}s duration")
        if build_error is not None:
            self.log(f"Audio build error: {type(build_error).__name__}: {build_error}. "
                     f"Keeping the sounds built before it.", error=True)

    def update_at(self, t):
        if self._export_job is not None:
            return   # the export thread is rendering the scene; leave it alone
        self.t = max(0.0, min(float(self.scene.duration), float(t)))
        safe_animate(self.animate_fn, self.scene, self.t)
        self._animated_key = (self.t, self._scene_gen)
        self.preview.set_scene(self.scene)
        self.time_label.setText(f"{self.t:.2f}s / {self.scene.duration:.2f}s")
        self.slider.blockSignals(True)
        self.slider.setValue(int(self.t / max(.001, self.scene.duration) * 1000))
        self.slider.blockSignals(False)
        self.refresh_tree()
        self._sync_audio(force=not self.playing)
        self._flush_errors()

    def _parent_name(self, obj):
        p = getattr(obj, "parent", None)
        if p is None:
            return None
        return p if isinstance(p, str) else getattr(p, "name", None)

    def refresh_tree(self):
        key = [(o.name, self._parent_name(o)) for o in self.scene.objects]
        if key == self._tree_key:
            return
        self._tree_key = key
        current = self.tree.currentItem()
        selected = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        self.tree.blockSignals(True)
        self.tree.clear()
        # Top of the list = front, so show the scene list in reverse.
        for name, parent_name in reversed(key):
            label = name if not parent_name else f"{name}   ↳ {parent_name}"
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.ItemDataRole.UserRole, name)
            self.tree.addTopLevelItem(item)
            if name == selected:
                self.tree.setCurrentItem(item)
        self.tree.blockSignals(False)
        self.select_object()

    def _tree_reordered(self):
        names = [self.tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)
                 for i in range(self.tree.topLevelItemCount())]
        names.reverse()
        ordered = [self.scene.get_optional(n) for n in names]
        ordered = [o for o in ordered if o is not None]
        rest = [o for o in self.scene.objects if o not in ordered]
        self.scene.objects = rest + ordered
        self._tree_key = None
        self._scene_gen += 1
        self._frame_cache.clear()
        self.update_at(self.t)
        self.log("Layer order changed")

    def _clear_inspector(self):
        while self.form.count():
            item = self.form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def select_object(self):
        self._clear_inspector()
        selected = self.tree.selectedItems()
        if not selected:
            return
        obj = self.scene.get_optional(selected[0].data(0, Qt.ItemDataRole.UserRole))
        if obj is None:
            return
        keyed = {track.prop for track in self.scene.tracks if track.name == obj.name}
        for key in ("x", "y", "z", "rotation", "rotation_x", "rotation_y", "rotation_z",
                    "scale", "scale_x", "scale_y", "skew_x", "opacity",
                    "blur", "backdrop_blur", "motion_blur"):
            if not hasattr(obj, key):
                continue
            value = float(getattr(obj, key))
            low, high = INSPECTOR_RANGES.get(key, INSPECTOR_DEFAULT_RANGE)
            spin = QDoubleSpinBox()
            spin.setRange(min(low, value), max(high, value))   # widen, never clamp the real value
            spin.setDecimals(2)
            if key in INSPECTOR_STEPS:
                spin.setSingleStep(INSPECTOR_STEPS[key])
            spin.setValue(value)
            label = key
            if key in keyed:
                label = key + " (keyframed)"
                spin.setToolTip("A keyframe sets this value on every frame, so an edit here "
                                "is overwritten. Change the keyframe in the script instead.")
            spin.valueChanged.connect(lambda v, k=key, target=obj: self._edited(target, k, v))
            self.form.addRow(label, spin)

    def scrub(self, value):
        if self.scene.duration:
            self.update_at(value / 1000 * self.scene.duration)

    def toggle(self):
        self.playing = not self.playing
        self._last_tick = None
        self.play.setText("Ⅱ Pause" if self.playing else "▶ Play")
        if self._has_track and self._player is not None:
            if self.playing:
                self._sync_audio(force=True)
                self._player.play()
            else:
                self._player.pause()

    def tick(self):
        # Nothing to draw while the window is hidden or minimized.
        if not self.isVisible() or self.isMinimized():
            self._last_tick = None
            return
        if self._export_job is not None:
            return
        now = time.monotonic()
        if self._last_tick is None:
            self._last_tick = now
        dt = now - self._last_tick
        self._last_tick = now
        if not self.playing:
            return
        next_time = self.t + dt * self.speed
        if next_time >= self.scene.duration:
            next_time = 0.0
        self.update_at(next_time)

    # ------------------------------------------------------------- file actions

    def new(self):
        self.editor.setPlainText(STARTER)
        self.audio_editor.setPlainText(STARTER_AUDIO)
        self.t = 0.0
        self.log("New scripts loaded")
        self.apply_all()

    def save_project(self):
        if not pf.last_project_dir():
            return self.save_project_as()
        self._write_project(pf.last_project_dir())

    def save_project_as(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose project folder", pf.last_project_dir())
        if folder:
            self._write_project(folder)

    def _write_project(self, folder):
        try:
            where = pf.save_project(folder, self.editor.toPlainText(), self.audio_editor.toPlainText())
            self.status.setText(f"Saved project: {os.path.basename(where)}")
            self.log(f"Saved video.py and audio.py to {where}")
        except OSError as exc:
            self.log(f"Save failed: {exc}", error=True)

    def open_project(self):
        folder = QFileDialog.getExistingDirectory(self, "Open project folder", pf.last_project_dir())
        if not folder:
            return
        video, audio = pf.load_project(folder)
        if video is None and audio is None:
            self.log(f"No video.py or audio.py in {folder}", error=True)
            return
        if video is not None:
            self.editor.setPlainText(video)
        if audio is not None:
            self.audio_editor.setPlainText(audio)
        self.log(f"Opened project {folder}")
        self.apply_all()

    def _fonts_installed(self, families):
        self._scene_gen += 1
        self._frame_cache.clear()
        self._refresh_completions()
        self.update_at(self.t)

    def _open_font_folder(self):
        pf.open_font_folder()
        self.log("Opened the fonts folder")

    def closeEvent(self, event):
        if self._player is not None:
            try:
                self._player.stop()
            except Exception:
                pass
        if self._preview_path:
            try:
                os.remove(self._preview_path)
            except OSError:
                pass
        job = self._export_job
        if job is not None and job.isRunning():
            job.cancel()
            job.wait(5000)
        self._clear_autosave()
        super().closeEvent(event)

    # ------------------------------------------------------------------ exports

    def _progress_label(self, title, done, total, tracker):
        remaining = tracker.remaining(done)
        pct = 100.0 * done / total if total else 100.0
        return (f"{title}\n"
                f"Frame {done} of {total} ({pct:.0f}%)\n"
                f"Estimated time left: {format_eta(remaining)}")

    def _scene_snapshot(self):
        # Export draws the same live scene the preview draws, so the results match.
        return self.scene

    def export_png(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose PNG frame folder")
        if not folder:
            return
        w, h = self.current_resolution()
        fps = self.current_fps()
        total = max(1, int(round(self.scene.duration / self.speed * fps)) + 1)
        try:
            snapshot = self._scene_snapshot()
        except Exception as exc:
            self.log(f"PNG export skipped: could not copy the scene ({type(exc).__name__}: {exc})", error=True)
            return
        job = ExportJob(snapshot, self.animate_fn, w, h, fps, self.speed, total, folder, "png",
                        render_fn=make_export_render())
        self.log(f"PNG export started: {total} frames at {w}×{h}, {fps} fps, speed {self.speed:.2f}x, "
                 f"effects {QUALITY_PRESETS[self.current_quality()]['label']}")
        self._run_export_job(job, "Exporting PNG frames…", total)

    def export_video(self, preferred=".mp4"):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export video", "animation" + preferred,
            "MP4 video (*.mp4);;WebM video (*.webm);;GIF animation (*.gif)")
        if not path:
            return
        ext = Path(path).suffix.lower()
        if ext not in (".mp4", ".webm", ".gif"):
            ext = preferred
            path += preferred
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            self.log("Video export failed: imageio-ffmpeg is not installed", error=True)
            return
        w, h = self.current_resolution()
        fps = self.current_fps()
        total = max(1, int(round(self.scene.duration / self.speed * fps)))

        # Audio is optional: if it fails, the video still exports.
        audio_path = None
        if AUDIO_ENGINE_OK and self.audio_scene is not None and self.audio_scene.events and ext != ".gif":
            try:
                stereo, problems = safe_render_audio(self.audio_scene, self.speed, self.volume_gain())
                for problem in problems:
                    self.log(problem, error=True)
                fd, audio_path = tempfile.mkstemp(suffix=".wav", prefix="motioncode_export_")
                os.close(fd)
                write_wav(audio_path, stereo, self.audio_scene.sample_rate)
            except Exception as exc:
                self.log(f"Audio skipped for this export: {type(exc).__name__}: {exc}", error=True)
                _remove_quietly(audio_path)
                audio_path = None

        # Frames are sent as RGB32 (4 bytes per pixel, no alpha), which is what bgr0 expects.
        cmd = [ffmpeg, "-y",
               "-f", "rawvideo", "-pix_fmt", "bgr0", "-s", f"{w}x{h}", "-r", str(fps),
               "-i", "-"]
        if audio_path:
            cmd += ["-i", audio_path, "-map", "0:v:0", "-map", "1:a:0",
                    "-af", "apad", "-t", f"{total / fps:.6f}"]
            if ext == ".webm":
                cmd += ["-c:a", "libopus", "-b:a", "160k"]
            else:
                cmd += ["-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-an"]
        cmd += self._video_codec_args(ext)
        cmd += [path]

        try:
            snapshot = self._scene_snapshot()
        except Exception as exc:
            _remove_quietly(audio_path)
            self.log(f"Video export skipped: could not copy the scene ({type(exc).__name__}: {exc})", error=True)
            return
        audio_note = "with audio" if audio_path else "no audio"
        self.log(f"{ext[1:].upper()} export started: {total} frames at {w}×{h}, {fps} fps, "
                 f"speed {self.speed:.2f}x, {audio_note}, effects {QUALITY_PRESETS[self.current_quality()]['label']}")
        job = ExportJob(snapshot, self.animate_fn, w, h, fps, self.speed, total, path, "video",
                        cmd=cmd, temp_paths=[audio_path] if audio_path else [],
                        render_fn=make_export_render())
        self._run_export_job(job, f"Exporting {ext[1:].upper()} ({w}×{h}, {fps} fps)", total)

    def _run_export_job(self, job, title, total):
        self._export_job = job
        self._export_title = title
        self._export_total = total
        self._export_tracker = EtaTracker(total)
        dialog = QProgressDialog("", "Cancel", 0, total, self)
        dialog.setWindowTitle(title)
        # Non-modal, so the rest of the window stays usable during export.
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setMinimumDuration(0)
        dialog.setLabelText(self._progress_label(title, 0, total, self._export_tracker))
        dialog.canceled.connect(job.cancel)
        self._export_dialog = dialog
        job.progress.connect(self._on_export_progress)
        job.succeeded.connect(self._on_export_succeeded)
        job.failed.connect(self._on_export_failed)
        job.cancelled.connect(self._on_export_cancelled)
        job.finished.connect(self._on_export_thread_done)
        self.status.setText("Exporting…")
        EXPORT_STATS.update(frames=0, seconds=0.0)
        PROFILE.clear()
        self.preview.setUpdatesEnabled(False)   # the preview would otherwise redraw during export
        self._set_busy(True)
        job.start()   # runs on a background thread; signals bring results back to this thread

    def _set_busy(self, busy):
        """Lock the controls that change the scene or settings while an export runs."""
        for widget in (self.quality_combo, self.res_combo, self.fps_spin, self.speed_spin,
                       self.encoder_combo, self.tree, self.inspector, self.play, self.slider):
            widget.setEnabled(not busy)

    def _on_export_progress(self, done):
        if self._export_dialog is None:
            return
        self._export_tracker.update(done)
        self._export_dialog.setValue(done)
        self._export_dialog.setLabelText(
            self._progress_label(self._export_title, done, self._export_total, self._export_tracker))

    def _finish_export_ui(self):
        if self._export_dialog is not None:
            self._export_dialog.close()
            self._export_dialog = None

    def _on_export_succeeded(self, message):
        self._finish_export_ui()
        self.status.setText("Export finished")
        self._flush_errors()
        self.log(message)
        if EXPORT_STATS["frames"]:
            n = EXPORT_STATS["frames"]
            ms = 1000.0 * EXPORT_STATS["seconds"] / n
            self.log(f"Average render time: {ms:.0f} ms per frame "
                     f"({n} frames, {EXPORT_STATS['seconds']:.1f} s total)")
            parts = ", ".join(f"{k} {1000.0 * v / n:.0f} ms"
                              for k, v in sorted(PROFILE.items(), key=lambda kv: -kv[1]))
            if parts:
                self.log("Per frame: " + parts)

    def _on_export_failed(self, message):
        self._finish_export_ui()
        self.status.setText("Export failed")
        self._flush_errors()
        self.log("Export failed: " + message, error=True)

    def _on_export_cancelled(self):
        self._finish_export_ui()
        self.status.setText("Export cancelled")
        self.log("Export cancelled")

    def _on_export_thread_done(self):
        self._export_job = None
        self._set_busy(False)
        self.preview.setUpdatesEnabled(True)
        self.update_at(self.t)

    def _refresh_completions(self):
        names = []
        for obj in self.scene.objects:
            alias = re.sub(r"[^0-9a-zA-Z_]+", "_", obj.name).strip("_").lower()
            if alias.isidentifier():
                names.append(alias)
        self.editor.set_completion_words(SCRIPT_WORDS_ALL + names)
        self.audio_editor.set_completion_words(AUDIO_WORDS)

    def check_video(self):
        namespace = {"math": math, "__name__": "__motioncheck__"}
        problems = []
        summary = None
        source = self.editor.toPlainText()
        for line_no, message in scan_script_mistakes(source):
            where = f"line {line_no}: " if line_no else ""
            problems.append(where + message)
        try:
            exec(compile(source, VIDEO_FILE, "exec"), namespace, namespace)
            build = namespace.get("build")
            animate = namespace.get("animate")
            if not callable(build):
                raise RuntimeError("Your script must define build(scene).")
            candidate = Scene()
            candidate.text_measurer = measure_text_px
            candidate.font_lister = list_font_families
            build(candidate)
            for obj in candidate.objects:
                alias = re.sub(r"[^0-9a-zA-Z_]+", "_", obj.name).strip("_").lower()
                if alias.isidentifier() and alias not in namespace:
                    namespace[alias] = obj
            if not callable(animate):
                problems.append("No animate(scene, t) found.")
            else:
                for t in [candidate.duration * i / 30.0 for i in range(31)]:
                    try:
                        animate(candidate, t)
                        candidate.apply_tracks(t)
                    except Exception as exc:
                        problems.append(f"animate at t={t:.2f}s: {type(exc).__name__}: {exc}")
                        break
            summary = (f"{len(candidate.objects)} objects, {candidate.duration}s, "
                       f"{len(candidate.tracks)} keyframe tracks")
        except Exception as exc:
            problems.append(f"{type(exc).__name__}: {exc}")
            self.editor.set_error_lines(error_lines_for(exc, VIDEO_FILE))
        if problems:
            for p in problems:
                self.log("Check: " + p, error=True)
            self.status.setText("Check found problems (see log)")
        else:
            self.log(f"Check passed: {summary}")
            self.status.setText("Check passed")

    def _video_codec_args(self, ext):
        """Encoder settings. Quality does not change these, so every level is encoded the same way."""
        if ext == ".gif":
            return ["-filter_complex",
                    "[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer",
                    "-loop", "0"]
        if ext == ".webm":
            return ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-row-mt", "1",
                    "-pix_fmt", "yuv420p"]
        if self.encoder_combo.currentData() == "nvenc":
            return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart"]

    def export_wav(self):
        if self.audio_scene is None or not self.audio_scene.events:
            self.log("WAV export skipped: no sounds applied yet", error=True)
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export WAV", "soundtrack.wav", "WAV audio (*.wav)")
        if not path:
            return
        if not path.lower().endswith(".wav"):
            path += ".wav"
        try:
            stereo, problems = safe_render_audio(self.audio_scene, self.speed, self.volume_gain())
            for problem in problems:
                self.log(problem, error=True)
            write_wav(path, stereo, self.audio_scene.sample_rate)
            self.status.setText("WAV exported")
            self.log(f"WAV saved: {Path(path).name}")
        except Exception as exc:
            self.log(f"WAV export failed: {type(exc).__name__}: {exc}", error=True)

    def _autosave(self):
        try:
            os.makedirs(AUTOSAVE_DIR, exist_ok=True)
            Path(AUTOSAVE_VIDEO).write_text(self.editor.toPlainText(), encoding="utf-8")
            Path(AUTOSAVE_AUDIO).write_text(self.audio_editor.toPlainText(), encoding="utf-8")
        except OSError:
            pass

    def _offer_recovery(self):
        if not os.path.exists(AUTOSAVE_VIDEO):
            return
        try:
            video = Path(AUTOSAVE_VIDEO).read_text(encoding="utf-8")
            audio = (Path(AUTOSAVE_AUDIO).read_text(encoding="utf-8")
                     if os.path.exists(AUTOSAVE_AUDIO) else STARTER_AUDIO)
        except OSError:
            return
        if video == self.editor.toPlainText() and audio == self.audio_editor.toPlainText():
            return
        answer = QMessageBox.question(
            self, "Recover unsaved work",
            "MotionCode found unsaved scripts from a previous session. Restore them?")
        if answer == QMessageBox.StandardButton.Yes:
            self.editor.setPlainText(video)
            self.audio_editor.setPlainText(audio)
            self.log("Recovered autosaved scripts")
            self.apply_all()
        else:
            self._clear_autosave()

    def _clear_autosave(self):
        for p in (AUTOSAVE_VIDEO, AUTOSAVE_AUDIO):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                pass

    def _remove_file(self, path):
        if not path:
            return
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec())