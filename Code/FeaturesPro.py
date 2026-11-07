"""FeaturesPro: visual styles for MotionCode.

Style detail follows the Quality box in the app. Call set_quality() from the app
when the Quality box changes (features.py does this for you).

Quality:   low -> base look only
           medium -> 1 extra layer per styled object
           balanced -> 2 extra layers
           high -> 3 extra layers, smoother liquid and finer grid

Use it from a video script:

    import FeaturesPro as pro

    def build(scene):
        scene.duration = 10
        pro.Styled(scene, "Sign", "text", style="neon", text="OPEN",
                   x=960, y=540, size=160, font="Arial", bold=True)
        pro.liquid(scene, "Blob", cx=400, cy=600, radius=140, color="#FF8A5B")
        pro.kinetic(scene, "Hello", "KINETIC TYPE", cx=960, cy=250, size=90)
        pro.grid(scene, "Grid", step=60, color="#1E3A66")

    def animate(scene, t):
        scene.get("Sign").rotation_z = math.sin(t) * 3   # your own animation
        pro.update_all(scene, t)                         # always last

Styles: neon, brutal, paper, deco, holo, blueprint, isometric, handdrawn, pixel, none
Other helpers: kinetic, split_flap, liquid, bounce, grid

Properties FeaturesPro sets each frame. Do not set these yourself on the same object:
  - Mask shapes: opacity (hidden in hide and tint modes) and backdrop_blur.
  - Emitter particles: opacity and scale.
  - Styled objects in the handdrawn style: x, y and rotation_z (they wobble).
  - Styled objects in the isometric style: skew_x (fixed at -30).
"""
import colorsys
import copy
import math
import random

import numpy as np

import engine as _engine
import motion_fx
from engine import Circle, Rect, Polygon

QUALITY = {"key": "balanced", "read": False}   # "read": a build() used a quality-dependent helper
QUALITY_LEVELS = ("low", "medium", "balanced", "high")

# Only these four styles change with Quality. Listed from least to most render cost:
#   Pixel Art: one flat shadow, no blur (cheapest)
#   Isometric: one blurred shadow, then a side layer
#   Holographic: three colour-shifting layers, one blurred
#   Neon Glow: three glow layers, the widest blur (most expensive)
# Every other style always draws its full look.
STYLE_BUDGET = {
    "pixel":     {"low": 0, "medium": 1, "balanced": 1, "high": 1},
    "isometric": {"low": 0, "medium": 1, "balanced": 2, "high": 3},
    "holo":      {"low": 0, "medium": 1, "balanced": 2, "high": 4},
    "neon":      {"low": 0, "medium": 1, "balanced": 2, "high": 3},
}
# Liquid outline detail and grid density per quality.
LIQUID_POINTS = {"low": 16, "medium": 24, "balanced": 36, "high": 64}
GRID_STEP_BOOST = {"low": 2.0, "medium": 1.5, "balanced": 1.0, "high": 0.67}
PIXEL_STEP = 8


def _quality_key():
    """Quality level for a helper that builds layers. Records that build() depends on it."""
    QUALITY["read"] = True
    return QUALITY["key"]


def set_quality(key):
    QUALITY["key"] = key if key in QUALITY_LEVELS else "balanced"


def _hue_hex(h):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, 0.65, 1.0)
    return "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255))


def _window(t, a, b, fade=0.3):
    if t < a or t > b:
        return 0.0
    return max(0.0, min(1.0, (t - a) / fade, (b - t) / fade))


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def _ease_out(k):
    k = _clamp(k)
    return 1.0 - (1.0 - k) ** 3


def _register(scene, item):
    items = getattr(scene, "_pro_items", None)
    if items is None:
        items = []
        scene._pro_items = items
    items.append(item)
    return item


def update_all(scene, t):
    """Update every FeaturesPro object in the scene. Call it last in animate()."""
    scene._pro_layer_values = {}
    for item in getattr(scene, "_pro_items", []):
        item.update(scene, t)
    _sort_layers(scene)


# ------------------------------------------------------------------ styles

# Layer fields: dx, dy offset; color (None = base color); filled; stroke_w;
# blur; opacity (multiplied by the base opacity); hue (cycle colours); flicker.
STYLES = {
    "none": {"layers": []},
    "neon": {
        "color": "#FFFFFF", "filled": False, "stroke_w": 3,
        "layers": [
            {"color": "#FF2E9A", "stroke_w": 10, "blur": 16, "opacity": 0.7, "flicker": True},
            {"color": "#FF7AC0", "stroke_w": 6, "blur": 6, "opacity": 0.6, "flicker": True},
            {"color": "#FF2E9A", "stroke_w": 14, "blur": 30, "opacity": 0.35},
        ],
    },
    # P2: the old second shadow layer had opacity 0 and never drew, so it is removed.
    "brutal": {
        "color": "#FFE14D", "filled": True, "stroke_w": 7,
        "layers": [
            {"dx": 10, "dy": 10, "color": "#000000", "filled": True, "stroke_w": 0, "opacity": 1.0},
        ],
    },
    "paper": {
        "color": "#FFF8EC", "filled": True, "stroke_w": 0,
        "layers": [
            {"dx": 12, "dy": 16, "color": "#000000", "filled": True, "stroke_w": 0, "blur": 14, "opacity": 0.35},
            {"dx": 4, "dy": 6, "color": "#000000", "filled": True, "stroke_w": 0, "blur": 4, "opacity": 0.25},
        ],
    },
    "deco": {
        "color": "#D4AF37", "filled": False, "stroke_w": 4,
        "layers": [
            {"color": "#D4AF37", "stroke_w": 12, "opacity": 0.35},
            {"color": "#1A1206", "stroke_w": 10, "opacity": 1.0},
        ],
    },
    "holo": {
        "color": "#FFFFFF", "filled": True, "stroke_w": 0,
        "layers": [
            {"dx": -4, "dy": 0, "hue": True, "filled": True, "stroke_w": 0, "opacity": 0.45},
            {"dx": 4, "dy": 0, "hue": True, "filled": True, "stroke_w": 0, "opacity": 0.45},
            {"dx": 0, "dy": 0, "color": "#FFFFFF", "filled": True, "stroke_w": 0, "opacity": 0.35, "sweep": True},
            {"dx": 0, "dy": 3, "hue": True, "filled": True, "stroke_w": 0, "opacity": 0.3, "blur": 6},
        ],
    },
    "blueprint": {
        "color": "#7FD1FF", "filled": False, "stroke_w": 2,
        "layers": [
            {"dx": 3, "dy": 3, "color": "#2C5D8A", "stroke_w": 2, "opacity": 0.6},
        ],
    },
    "isometric": {
        "color": "#35B9FF", "filled": True, "stroke_w": 3,
        "layers": [
            {"dx": 14, "dy": 14, "color": "#000000", "filled": True, "stroke_w": 0, "blur": 6, "opacity": 0.35},
            {"dx": -6, "dy": 0, "color": "#1B7FB0", "filled": True, "stroke_w": 0, "opacity": 0.8},
            {"dx": 0, "dy": -8, "color": "#8FDCFF", "filled": True, "stroke_w": 0, "opacity": 0.9},
        ],
    },
    "handdrawn": {
        "color": "#FFFFFF", "filled": False, "stroke_w": 4,
        "layers": [
            {"dx": 2, "dy": -2, "color": "#FF8A5B", "stroke_w": 4, "opacity": 0.6},
            {"dx": -2, "dy": 1, "color": "#FFFFFF", "stroke_w": 1, "opacity": 0.7},
        ],
    },
    "pixel": {
        "color": "#06D6A0", "filled": True, "stroke_w": 0,
        "layers": [
            {"dx": PIXEL_STEP, "dy": PIXEL_STEP, "color": "#0B3D2E", "filled": True, "stroke_w": 0, "opacity": 1.0},
        ],
    },
}


_ADDERS = {
    "circle": "add_circle",
    "rect": "add_rect",
    "rounded_rect": "add_rounded_rect",
    "ellipse": "add_ellipse",
    "star": "add_star",
    "text": "add_text",
}
_COPY_FIELDS = ("x", "y", "rotation_z", "scale", "scale_x", "scale_y", "skew_x")


class Styled:
    """A shape or text with a visual style. Its style layers are created behind it.
    Give the base object its normal properties; the style is added automatically."""

    def __init__(self, scene, name, shape, style="none", text=None, **kw):
        if style not in STYLES:
            raise ValueError("Unknown style %r. Use one of: %s" % (style, ", ".join(STYLES)))
        if shape not in _ADDERS:
            raise ValueError("Unknown shape %r. Use one of: %s" % (shape, ", ".join(_ADDERS)))
        self.name = name
        self.shape = shape
        self.style = style
        self.spec = STYLES[style]
        self.layers = []
        self.layer_specs = []
        # P1: the wobble applied on the last frame, removed before the next one is added.
        self._last = (0.0, 0.0, 0.0)

        base_kw = dict(kw)
        if "color" in self.spec:
            base_kw.setdefault("color", self.spec["color"])
        if "filled" in self.spec:
            base_kw.setdefault("filled", self.spec["filled"])
        if "stroke_w" in self.spec:
            base_kw.setdefault("stroke", self.spec["stroke_w"])
        if style == "isometric":
            base_kw.setdefault("skew_x", -30.0)
        if style == "pixel" and "color" in base_kw:
            base_kw["color"] = quantize_color(base_kw["color"])   # limited palette

        # Layers are added first so they draw behind the base object.
        if style in STYLE_BUDGET:
            count = STYLE_BUDGET[style][_quality_key()]
        else:
            count = len(self.spec["layers"])
        for i, layer in enumerate(self.spec["layers"][:count]):
            lname = "%s fx%d" % (name, i)
            lkw = {k: v for k, v in base_kw.items() if k not in ("x", "y")}
            lkw["x"] = base_kw.get("x", 960)
            lkw["y"] = base_kw.get("y", 540)
            if "color" in layer and layer["color"] is not None:
                lkw["color"] = layer["color"]
            if "filled" in layer:
                lkw["filled"] = layer["filled"]
            if "stroke_w" in layer:
                lkw["stroke"] = layer["stroke_w"]
            lkw["opacity"] = layer.get("opacity", 1.0)
            self._create(scene, lname, text, lkw)
            obj = scene.get(lname)
            obj.blur = float(layer.get("blur", 0.0))
            self.layers.append(lname)
            self.layer_specs.append(layer)

        self._create(scene, name, text, base_kw)
        _register(scene, self)

    def _create(self, scene, name, text, kw):
        adder = getattr(scene, _ADDERS[self.shape])
        if self.shape == "text":
            adder(name, text if text is not None else "", **kw)
        else:
            adder(name, **kw)

    def update(self, scene, t):
        base = scene.get(self.name)
        style = self.style
        if style == "handdrawn":
            jx = 1.6 * math.sin(t * 23.0)
            jy = 1.6 * math.sin(t * 29.0 + 1.0)
            jr = 0.8 * math.sin(t * 7.0)
            # Move by the change since the last frame only, so the wobble never accumulates.
            base.x += jx - self._last[0]
            base.y += jy - self._last[1]
            base.rotation_z += jr - self._last[2]
            self._last = (jx, jy, jr)
        elif style == "pixel":
            base.x = round(base.x / PIXEL_STEP) * PIXEL_STEP
            base.y = round(base.y / PIXEL_STEP) * PIXEL_STEP
        elif style == "isometric":
            base.skew_x = -30.0
        elif style == "holo":
            base.skew_x = 14.0 * math.sin(t * 0.9)   # the angle changes the reflected colour
            try:
                import effects as ex
                stops = [(0.0, _hue_hex(t * 0.12)), (0.5, _hue_hex(t * 0.12 + 0.33)),
                         (1.0, _hue_hex(t * 0.12 + 0.66))]
                base.gradient = ex.Gradient(stops, kind="linear", angle=(t * 35.0) % 360.0)
            except Exception:
                pass   # without the effects module the holo keeps its plain fill

        for i, (lname, layer) in enumerate(zip(self.layers, self.layer_specs)):
            obj = scene.get(lname)
            for field in _COPY_FIELDS:
                setattr(obj, field, getattr(base, field))
            obj.x += layer.get("dx", 0.0)
            obj.y += layer.get("dy", 0.0)
            if self.shape == "text":
                obj.text = base.text
            opacity = base.opacity * layer.get("opacity", 1.0)
            if layer.get("flicker"):
                opacity *= 0.85 + 0.15 * math.sin(t * 17.0 + i)
            if layer.get("sweep"):
                obj.x += 160.0 * math.sin(t * 0.9 + i)   # reflective highlight that sweeps across
            if layer.get("hue"):
                hue = (t * 0.15 + i * 0.33) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 0.7, 1.0)
                obj.color = "#%02X%02X%02X" % (int(r * 255), int(g * 255), int(b * 255))
            obj.opacity = _clamp(opacity)


# ------------------------------------------------------------- liquid morph

class Liquid:
    """A soft blob whose outline keeps moving. Detail follows the Quality setting."""

    def __init__(self, scene, name, cx, cy, radius, color="#FFFFFF", wobble=0.12, speed=1.0):
        self.name = name
        self.cx, self.cy = float(cx), float(cy)
        self.radius = float(radius)
        self.wobble = float(wobble)
        self.speed = float(speed)
        self.n = LIQUID_POINTS[_quality_key()]
        pts = [(self.radius, 0.0)] * self.n
        scene.add_polygon(name, points=pts, x=self.cx, y=self.cy, color=color,
                          filled=True, stroke=2, closed=True)
        _register(scene, self)

    def update(self, scene, t):
        obj = scene.get(self.name)
        s = t * self.speed
        pts = []
        for i in range(self.n):
            th = 2.0 * math.pi * i / self.n
            k = (math.sin(3 * th + 2.1 * s) + 0.6 * math.sin(5 * th - 1.7 * s)
                 + 0.3 * math.sin(2 * th + 0.8 * s)) / 1.9
            r = self.radius * (1.0 + self.wobble * k)
            pts.append((r * math.cos(th), r * math.sin(th)))
        obj.points = pts


def liquid(scene, name, cx, cy, radius, color="#FFFFFF", wobble=0.12, speed=1.0):
    return Liquid(scene, name, cx, cy, radius, color, wobble, speed)


# ------------------------------------------------------------ kinetic type

def _char_cells(scene, text, size, font, bold):
    widths = []
    for ch in text:
        w, _h = scene.measure_text(ch if ch.strip() else " ", size=size, font=font, bold=bold)
        widths.append(max(w, size * 0.3))
    return widths


class Kinetic:
    """Each letter rises and fades in one after another."""

    def __init__(self, scene, name, text, cx, cy, size=90, color="#FFFFFF", font="Arial",
                 bold=True, start=0.0, stagger=0.06, duration=0.5):
        self.name = name
        self.text = text
        self.start = float(start)
        self.stagger = float(stagger)
        # P5: a zero duration would divide by zero on the first frame.
        self.duration = max(1e-3, float(duration))
        widths = _char_cells(scene, text, size, font, bold)
        x = float(cx) - sum(widths) / 2.0
        self.letters = []
        self.base_y = float(cy)
        for i, ch in enumerate(text):
            lname = "%s %d" % (name, i)
            scene.add_text(lname, ch, x=x + widths[i] / 2.0, y=cy, size=size, color=color,
                           font=font, bold=bold, align="center", opacity=0.0)
            self.letters.append(lname)
            x += widths[i]
        _register(scene, self)

    def update(self, scene, t):
        for i, lname in enumerate(self.letters):
            k = (t - self.start - i * self.stagger) / self.duration
            p = _ease_out(k)
            obj = scene.get(lname)
            obj.opacity = _clamp(p)
            obj.y = self.base_y + 40.0 * (1.0 - p)


def kinetic(scene, name, text, cx, cy, size=90, color="#FFFFFF", font="Arial", bold=True,
            start=0.0, stagger=0.06, duration=0.5):
    return Kinetic(scene, name, text, cx, cy, size, color, font, bold, start, stagger, duration)


# --------------------------------------------------------------- split-flap

class SplitFlap:
    """Departure-board letters. Each change flips the letters one after another.
    states: list of (time_seconds, text). Texts should be the same length."""

    def __init__(self, scene, name, states, cx, cy, size=96, color="#FFD166",
                 font="Consolas", bold=True, flip=0.32, stagger=0.05):
        self.name = name
        self.states = sorted((float(t), str(s)) for t, s in states)
        self.flip = max(1e-3, float(flip))      # P5: guard against division by zero
        self.stagger = float(stagger)
        width_len = max(len(s) for _, s in self.states)
        cell = scene.measure_text("M", size=size, font=font, bold=bold)[0] * 1.05
        x0 = float(cx) - cell * width_len / 2.0
        self.cells = []
        for i in range(width_len):
            cname = "%s %d" % (name, i)
            scene.add_text(cname, " ", x=x0 + cell * (i + 0.5), y=cy, size=size, color=color,
                           font=font, bold=bold, align="center")
            self.cells.append(cname)
        self.width = width_len
        _register(scene, self)

    def update(self, scene, t):
        latest = [j for j, (st, _) in enumerate(self.states) if st <= t]
        if not latest:
            for cname in self.cells:
                scene.get(cname).text = " "
            return
        j = latest[-1]
        st, new_text = self.states[j]
        old_text = self.states[j - 1][1] if j > 0 else " " * len(new_text)
        new_text = new_text.ljust(self.width)
        old_text = old_text.ljust(self.width)
        for i, cname in enumerate(self.cells):
            k = (t - st - i * self.stagger) / self.flip
            obj = scene.get(cname)
            if k < 0.0:
                obj.text = old_text[i]
                obj.scale_y = 1.0
            elif k >= 1.0:
                obj.text = new_text[i]
                obj.scale_y = 1.0
            else:
                obj.text = old_text[i] if k < 0.5 else new_text[i]
                obj.scale_y = max(0.05, abs(math.cos(math.pi * k)))


def split_flap(scene, name, states, cx, cy, size=96, color="#FFD166", font="Consolas",
               bold=True, flip=0.32, stagger=0.05):
    return SplitFlap(scene, name, states, cx, cy, size, color, font, bold, flip, stagger)


# ------------------------------------------------------------------ bounce

class Bounce:
    """An object dropped from the top that bounces on a floor. Physics is simulated
    from the start time, so scrubbing and export give the same result.

    The simulation is stored step by step. Going back in time reads the stored
    steps, so motion-blur samples just before the current time cost nothing extra."""

    _DT = 1.0 / 240.0

    def __init__(self, scene, name, shape, x, drop_y, floor_y, radius=40.0, start=0.0,
                 gravity=2200.0, restitution=0.6, **kw):
        self.name = name
        self.x = float(x)
        self.drop_y = float(drop_y)
        self.rest_y = float(floor_y) - float(radius)
        self.start = float(start)
        self.gravity = float(gravity)
        self.restitution = float(restitution)
        # states[n] = (y, velocity) after n steps. Filled in as time moves forward.
        self._states = [(self.drop_y, 0.0)]
        adder = getattr(scene, _ADDERS[shape])
        if shape == "text":
            adder(name, kw.pop("text", ""), x=self.x, y=self.drop_y, **kw)
        else:
            adder(name, x=self.x, y=self.drop_y, **kw)
        _register(scene, self)

    def _step(self, y, v):
        if v == 0.0 and y >= self.rest_y:
            return y, 0.0                       # settled on the floor: no jitter
        v += self.gravity * self._DT
        y += v * self._DT
        if y >= self.rest_y:
            y = self.rest_y
            v = -abs(v) * self.restitution
            if abs(v) < 25.0:
                v = 0.0
        return y, v

    def _state(self, n):
        while len(self._states) <= n:
            y, v = self._states[-1]
            self._states.append(self._step(y, v))
        return self._states[n]

    def update(self, scene, t):
        obj = scene.get(self.name)
        tau = max(0.0, t - self.start)
        y, _v = self._state(int(tau / self._DT))
        obj.y = y
        obj.x = self.x


def bounce(scene, name, shape, x, drop_y, floor_y, radius=40.0, start=0.0,
           gravity=2200.0, restitution=0.6, **kw):
    return Bounce(scene, name, shape, x, drop_y, floor_y, radius, start, gravity,
                  restitution, **kw)


# ------------------------------------------------------------------- grid

def grid(scene, name, step=60, color="#1E3A66", width=1, area=(0, 0, 1920, 1080)):
    """Blueprint grid. Density follows the Quality setting: finer grids at higher quality."""
    x0, y0, x1, y1 = area
    step = max(8, int(step * GRID_STEP_BOOST[_quality_key()]))
    count = 0
    x = x0
    while x <= x1:
        scene.add_line("%s v%d" % (name, count), x=x, y=y0, x2=x, y2=y1,
                       color=color, stroke=width)
        x += step
        count += 1
    y = y0
    row = 0
    while y <= y1:
        scene.add_line("%s h%d" % (name, row), x=x0, y=y, x2=x1, y2=y,
                       color=color, stroke=width)
        y += step
        row += 1
    return count + row


# =========================================================== Art Deco ornaments

# Sunburst rays per quality level (symmetry and ornament density).
DECO_RAYS = {"low": 8, "medium": 12, "balanced": 16, "high": 24}


def deco_frame(scene, name, cx, cy, width, height, color="#D4AF37", dark="#1A1206", stroke=4):
    """Symmetric Art Deco frame: stepped corners, a dark inner line, and a sunburst behind it.
    Everything is built from the centre, so the design is symmetric by construction."""
    hw, hh = width / 2.0, height / 2.0
    s = min(width, height) * 0.04
    rays = DECO_RAYS[_quality_key()]
    radius_in = max(hw, hh) * 1.05
    radius_out = max(hw, hh) * 1.55
    for i in range(rays):
        a = 2.0 * math.pi * i / rays
        x0, y0 = cx + radius_in * math.cos(a), cy + radius_in * math.sin(a)
        x1, y1 = cx + radius_out * math.cos(a), cy + radius_out * math.sin(a)
        scene.add_line("%s ray %d" % (name, i), x=x0, y=y0, x2=x1 - x0, y2=y1 - y0,
                       color=color, stroke=2)

    def stepped(hw_, hh_, step):
        return [
            (-hw_, -hh_ + 3 * step), (-hw_ + step, -hh_ + 3 * step), (-hw_ + step, -hh_ + 2 * step),
            (-hw_ + 2 * step, -hh_ + 2 * step), (-hw_ + 2 * step, -hh_ + step),
            (-hw_ + 3 * step, -hh_ + step), (-hw_ + 3 * step, -hh_), (hw_ - 3 * step, -hh_),
            (hw_ - 3 * step, -hh_ + step), (hw_ - 2 * step, -hh_ + step), (hw_ - 2 * step, -hh_ + 2 * step),
            (hw_ - step, -hh_ + 2 * step), (hw_ - step, -hh_ + 3 * step), (hw_, -hh_ + 3 * step),
            (hw_, hh_ - 3 * step), (hw_ - step, hh_ - 3 * step), (hw_ - step, hh_ - 2 * step),
            (hw_ - 2 * step, hh_ - 2 * step), (hw_ - 2 * step, hh_ - step), (hw_ - 3 * step, hh_ - step),
            (hw_ - 3 * step, hh_), (-hw_ + 3 * step, hh_), (-hw_ + 3 * step, hh_ - step),
            (-hw_ + 2 * step, hh_ - step), (-hw_ + 2 * step, hh_ - 2 * step), (-hw_ + step, hh_ - 2 * step),
            (-hw_ + step, hh_ - 3 * step), (-hw_, hh_ - 3 * step),
        ]

    scene.add_polyline("%s frame" % name, points=stepped(hw, hh, s), x=cx, y=cy,
                       color=color, stroke=stroke)
    scene.add_polyline("%s inner" % name, points=stepped(hw * 0.92, hh * 0.92, s * 0.92), x=cx, y=cy,
                       color=dark, stroke=max(2, stroke - 1))


# =========================================================== Blueprint dimensions

def dimension(scene, name, x1, y1, x2, y2, offset=40.0, color="#7FD1FF", size=24,
              label=None, font="Consolas"):
    """A dimension line with end ticks and a label, for horizontal or vertical edges.
    The line sits offset pixels away from the measured edge, and the label sits on the
    outside of the dimension line, away from the object."""
    horizontal = abs(y2 - y1) < abs(x2 - x1)
    if horizontal:
        ya = min(y1, y2) - offset if offset >= 0 else max(y1, y2) - offset
        length = abs(x2 - x1)
        xa, xb = min(x1, x2), max(x1, x2)
        scene.add_line("%s dim" % name, x=xa, y=ya, x2=xb - xa, y2=0, color=color, stroke=2)
        scene.add_line("%s ext a" % name, x=x1, y=y1, x2=0, y2=ya - y1, color=color, stroke=1)
        scene.add_line("%s ext b" % name, x=x2, y=y2, x2=0, y2=ya - y2, color=color, stroke=1)
        for i, x in enumerate((xa, xb)):
            scene.add_line("%s tick %d" % (name, i), x=x - 7, y=ya + 7, x2=14, y2=-14,
                           color=color, stroke=2)
        # P8: put the label on the side of the line that faces away from the object.
        side = -1.0 if ya < min(y1, y2) else 1.0
        mx, my = (xa + xb) / 2.0, ya + side * size * 0.6
    else:
        xa = min(x1, x2) - offset
        length = abs(y2 - y1)
        ya, yb = min(y1, y2), max(y1, y2)
        scene.add_line("%s dim" % name, x=xa, y=ya, x2=0, y2=yb - ya, color=color, stroke=2)
        scene.add_line("%s ext a" % name, x=x1, y=y1, x2=xa - x1, y2=0, color=color, stroke=1)
        scene.add_line("%s ext b" % name, x=x2, y=y2, x2=xa - x2, y2=0, color=color, stroke=1)
        for i, y in enumerate((ya, yb)):
            scene.add_line("%s tick %d" % (name, i), x=xa - 7, y=y + 7, x2=14, y2=-14,
                           color=color, stroke=2)
        side = -1.0 if xa < min(x1, x2) else 1.0
        mx, my = xa + side * size * 1.8, (ya + yb) / 2.0
    text = label if label is not None else "%d px" % round(length)
    scene.add_text("%s label" % name, text, x=mx, y=my, size=size, font=font, bold=False,
                   align="center", color=color)
    return length


# =============================================================== Hand-drawn strokes

class StrokeDraw:
    """Draws an outline progressively, like a pen moving along it. Points are absolute
    screen coordinates. Use closed=True to draw back to the first point."""

    def __init__(self, scene, name, points, t_start, duration, color="#FFFFFF", stroke=3,
                 closed=True):
        self.name = name
        self.points = [(float(x), float(y)) for x, y in points]
        if closed and self.points:
            self.points.append(self.points[0])
        self.t0 = float(t_start)
        self.duration = max(1e-6, float(duration))
        self.lengths = [math.hypot(b[0] - a[0], b[1] - a[1])
                        for a, b in zip(self.points, self.points[1:])]
        self.total = sum(self.lengths) or 1.0
        scene.add_polyline(name, points=[(0.0, 0.0), (0.0, 0.0)], x=0.0, y=0.0,
                           color=color, stroke=stroke)
        _register(scene, self)

    def update(self, scene, t):
        obj = scene.get(self.name)
        p = _clamp((t - self.t0) / self.duration)
        target = p * self.total
        drawn = [self.points[0]]
        for (a, b), seg in zip(zip(self.points, self.points[1:]), self.lengths):
            if target >= seg:
                drawn.append(b)
                target -= seg
            else:
                k = target / seg if seg else 0.0
                drawn.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
                break
        if len(drawn) < 2:
            drawn.append(drawn[0])
        obj.points = drawn
        obj.opacity = 1.0 if p > 0 else 0.0


def stroke_draw(scene, name, points, t_start, duration, color="#FFFFFF", stroke=3, closed=True):
    return StrokeDraw(scene, name, points, t_start, duration, color, stroke, closed)


# ============================================================ Pixel Art palettes

PIXEL_PALETTES = {
    "retro": ["#0B0B1E", "#2D1B4E", "#7B2D8E", "#E0457B", "#F9A03F", "#FFF6D5"],
    "mint": ["#0B1F1A", "#0B3D2E", "#06D6A0", "#A7F3D0", "#FFFFFF", "#FFD166"],
    "mono": ["#000000", "#3A3A3A", "#8A8A8A", "#E6E6E6", "#FFFFFF"],
}
ACTIVE_PALETTE = {"name": "mint"}


def set_pixel_palette(name):
    if name in PIXEL_PALETTES:
        ACTIVE_PALETTE["name"] = name


def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def quantize_color(color, palette=None):
    """Snap a colour to the nearest colour in the palette (limited palette)."""
    colors = PIXEL_PALETTES[palette or ACTIVE_PALETTE["name"]]
    r, g, b = _hex_rgb(color)
    best = min(colors, key=lambda c: sum((x - y) ** 2 for x, y in zip(_hex_rgb(c), (r, g, b))))
    return best


def pixel_sprite(scene, name, bitmap, cx, cy, cell=8, palette=None, shadow=True):
    """Build a sprite from text rows. '.' is empty; digits 0-5 pick palette colours.
    Each filled cell is one rectangle, so the sprite is made of pixel clusters."""
    colors = PIXEL_PALETTES[palette or ACTIVE_PALETTE["name"]]
    rows = len(bitmap)
    cols = max(len(r) for r in bitmap)
    x0 = cx - cols * cell / 2.0
    y0 = cy - rows * cell / 2.0
    count = 0
    if shadow:
        for r, row in enumerate(bitmap):
            for c, ch in enumerate(row):
                if ch != ".":
                    scene.add_rect("%s shadow %d %d" % (name, r, c),
                                   x=x0 + c * cell + cell / 2.0 + cell,
                                   y=y0 + r * cell + cell / 2.0 + cell,
                                   width=cell, height=cell, color="#000000",
                                   filled=True, stroke=0, opacity=0.35)
                    count += 1
    for r, row in enumerate(bitmap):
        for c, ch in enumerate(row):
            if ch == "." or not ch.isdigit():
                continue
            idx = min(int(ch), len(colors) - 1)
            scene.add_rect("%s px %d %d" % (name, r, c),
                           x=x0 + c * cell + cell / 2.0, y=y0 + r * cell + cell / 2.0,
                           width=cell, height=cell, color=colors[idx],
                           filled=True, stroke=0)
            count += 1
    return count


# ============================================================== Isometric box

def iso_box(scene, name, cx, cy, size=160.0, depth=120.0, top="#8FDCFF",
            left="#35B9FF", right="#1B7FB0"):
    """A true isometric box: three visible faces (top, left, right) at 30 degrees.
    Shading makes the faces read as 3D. Returns the three face names.

    P3: each face sits at (cx, cy) with points relative to that centre, so effects such as
    blur or light position the face correctly."""
    s = size / 2.0
    c = math.cos(math.radians(30))
    sn = 0.5

    def P(x, y, z):
        return ((x - y) * s * c, (x + y) * s * sn - z)

    d = depth
    faces = {
        "top": ([P(-s, -s, d), P(s, -s, d), P(s, s, d), P(-s, s, d)], top),
        "left": ([P(-s, s, 0), P(s, s, 0), P(s, s, d), P(-s, s, d)], left),
        "right": ([P(s, -s, 0), P(s, s, 0), P(s, s, d), P(s, -s, d)], right),
    }
    names = []
    for key, (pts, color) in faces.items():
        n = "%s %s" % (name, key)
        scene.add_polygon(n, points=pts, x=float(cx), y=float(cy), color=color, filled=True,
                          stroke=2, closed=True)
        names.append(n)
    return names


# ============================================================ Paper cutout sheet

PAPER_GRAIN = {"low": 0, "medium": 40, "balanced": 120, "high": 240}


def paper_sheet(scene, name, cx, cy, w, h, color="#FFF8EC", seed=3):
    """A cut-paper sheet: irregular cut edges, a soft drop shadow, and paper grain.
    Grain density follows the Quality setting.

    P4: the cut edge is computed once. The shadow is the same edge shifted down and right,
    so the two shapes match."""
    rnd = random.Random(seed)

    def jagged_rect(hw, hh):
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        pts = []
        for i in range(4):
            x0, y0 = corners[i]
            x1, y1 = corners[(i + 1) % 4]
            for k in range(8):
                f = k / 8.0
                x = x0 + (x1 - x0) * f
                y = y0 + (y1 - y0) * f
                jitter = rnd.uniform(-3.0, 3.0)
                nx, ny = (y1 - y0), -(x1 - x0)
                length = math.hypot(nx, ny) or 1.0
                pts.append((x + jitter * nx / length, y + jitter * ny / length))
        return pts

    hw, hh = w / 2.0, h / 2.0
    edge = jagged_rect(hw, hh)
    scene.add_polygon(name + " shadow", points=[(x + 12, y + 16) for x, y in edge],
                      x=cx, y=cy, color="#000000", filled=True, stroke=0, closed=True,
                      opacity=0.35)
    scene.get(name + " shadow").blur = 14.0
    scene.add_polygon(name, points=edge, x=cx, y=cy, color=color,
                      filled=True, stroke=0, closed=True)

    grain = PAPER_GRAIN[_quality_key()]
    for i in range(grain):
        gx = cx + rnd.uniform(-hw, hw) * 0.95
        gy = cy + rnd.uniform(-hh, hh) * 0.95
        scene.add_circle("%s grain %d" % (name, i), x=gx, y=gy, radius=rnd.uniform(0.8, 2.0),
                         color="#8A7A60", filled=True, stroke=0, opacity=0.12)
    return name


# ============================================================= Captions

class Caption:
    """A short explanation that fades and rises in, holds, then fades out."""

    def __init__(self, scene, name, text, cx, y, start, end, size=34, color="#9FB4FF"):
        self.name = name
        self.y = float(y)
        self.start = float(start)
        self.end = float(end)
        scene.add_text(name, text, x=cx, y=y, size=size, font="Arial", bold=False,
                       color=color, align="center", opacity=0.0)
        _register(scene, self)

    def update(self, scene, t):
        obj = scene.get(self.name)
        obj.opacity = _window(t, self.start, self.end, 0.35)
        rise = _clamp((t - self.start) / 0.35)
        obj.y = self.y + 14.0 * (1.0 - rise)


def caption(scene, name, text, cx, y, start, end, size=34, color="#9FB4FF"):
    return Caption(scene, name, text, cx, y, start, end, size, color)


# ============================================================ Self-test

def selftest(scene, duration, fps=30):
    """Run every FeaturesPro object through every frame. Returns the first problem, or None.
    Use it from a test script to catch errors before exporting."""
    t = 0.0
    step = 1.0 / fps
    while t <= duration + 1e-9:
        try:
            update_all(scene, t)
        except Exception as exc:
            return "t=%.2fs: %s: %s" % (t, type(exc).__name__, exc)
        t += step
    return None


# ================================================================= Masks

MASK_MODES = ("hide", "blur", "tint")
BLUR_MAX_PX = 60.0       # blur mode: strength 1.0 = this many pixels of blur


def _hex01(color):
    h = color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


class Mask:
    """Turns an existing 2D shape into a mask. Any filled circle, rect or polygon works,
    including custom points and star shapes. One mask per shape.

    mode:
      "hide"  targets are invisible inside the shape
      "blur"  the shape blurs whatever is under it (targets are not used)
      "tint"  targets inside the shape take on `color`
    targets:  list of object names, or None for every object drawn below the shape
    strength: 0..1. hide = how much is hidden, tint = how much colour, blur = blur amount.
              Read from the shape's mask_strength attribute each frame, so it can be keyframed.
    color:    tint colour, "#RRGGBB"

    The mask shape's opacity is set by the mask every frame (0 in hide and tint modes,
    1 in blur mode). Do not set it yourself."""

    def __init__(self, scene, shape_name, mode="hide", targets=None, strength=1.0, color="#FFFFFF",
                 feather=0.0):
        shape = scene.get(shape_name)
        if getattr(shape, "is_mask", False):
            raise ValueError("%s already has a mask. One mask per shape." % shape_name)
        if not isinstance(shape, (Circle, Rect, Polygon)):
            raise ValueError("%s cannot be a mask. Use a circle, rect, or polygon." % shape_name)
        if mode not in MASK_MODES:
            raise ValueError("Unknown mask mode %r. Use one of: %s" % (mode, ", ".join(MASK_MODES)))
        if targets is not None and shape_name in targets:
            raise ValueError("A mask cannot target itself")
        self.shape_name = shape_name
        self.mode = mode
        self.targets = None if targets is None else list(targets)
        shape.is_mask = True
        shape.mask_strength = float(strength)
        shape.mask_color = str(color)
        shape.mask_blur_only = (mode == "blur")
        shape.mask_feather = max(0.0, float(feather))   # soft edge in pixels; 0 = hard edge
        scene._pro_masks = getattr(scene, "_pro_masks", []) + [self]
        _register(scene, self)

    def update(self, scene, t):
        shape = scene.get(self.shape_name)
        strength = max(0.0, min(1.0, float(shape.mask_strength)))
        shape.mask_blur_only = (self.mode == "blur")
        if self.mode == "blur":
            shape.opacity = 1.0                       # drawn only as a blur, see draw_one
            shape.backdrop_blur = strength * BLUR_MAX_PX
        else:
            shape.opacity = 0.0                       # the shape itself is never drawn
            shape.backdrop_blur = 0.0


def mask(scene, shape_name, mode="hide", targets=None, strength=1.0, color="#FFFFFF", feather=0.0):
    return Mask(scene, shape_name, mode, targets, strength, color, feather)


def coverage_copy(obj):
    """Opaque filled copy of a shape, used to measure where a mask covers the frame."""
    c = copy.copy(obj)
    c.opacity = 1.0
    c.filled = True
    c.stroke = 0
    c.gradient = None
    c.blur = 0.0
    c.backdrop_blur = 0.0
    c.motion_blur = 0.0
    c.lit = False
    c.color = "#FFFFFF"
    return c


def composite_color_mask(arr, cover, strength, mode, color):
    """Apply a hide or tint mask to a premultiplied RGBA layer.
    cover: (H, W, 1) coverage of the mask shape over the layer."""
    m = np.clip(cover * float(strength), 0.0, 1.0)
    if mode == "hide":
        return arr * (1.0 - m)
    tint = np.array(_hex01(color), dtype=np.float32)
    rgb, alpha = arr[..., :3], arr[..., 3:4]
    arr[..., :3] = rgb * (1.0 - m) + tint * alpha * m
    return arr


def _shape_scale(o):
    return abs(o.scale * getattr(o, "scale_x", 1.0)), abs(o.scale * getattr(o, "scale_y", 1.0))


def _loose_box(o):
    """Conservative box (x0, y0, x1, y1) in scene coordinates, or None if unknown."""
    if o.rotation_z % 360 or getattr(o, "skew_x", 0.0):
        return None
    sx, sy = _shape_scale(o)
    if isinstance(o, Rect):
        hw, hh = o.width / 2 * sx, o.height / 2 * sy
    elif isinstance(o, Circle):
        hw = hh = o.radius * max(sx, sy)
    elif isinstance(o, Polygon) and o.closed and o.points:
        xs = [p[0] * sx for p in o.points]
        ys = [p[1] * sy for p in o.points]
        pad = o.stroke + 2
        return (o.x + min(xs) - pad, o.y + min(ys) - pad,
                o.x + max(xs) + pad, o.y + max(ys) + pad)
    else:
        return None
    pad = o.stroke + 2
    return (o.x - hw - pad, o.y - hh - pad, o.x + hw + pad, o.y + hh + pad)


def _opaque_occluder(o):
    """True if o is a solid, unrotated Rect or Circle that fully covers its own area."""
    if not isinstance(o, (Rect, Circle)):
        return False
    if (getattr(o, "is_mask", False) or not o.filled or o.opacity < 1.0
            or o.blur > 0 or o.backdrop_blur > 0 or o.motion_blur > 0):
        return False
    if o.rotation_z % 360 or getattr(o, "skew_x", 0.0):
        return False
    if isinstance(o, Circle):
        sx, sy = _shape_scale(o)
        return abs(sx - sy) < 1e-9
    return True


def _covers(occ, box):
    """True if the solid occluder completely contains the box."""
    x0, y0, x1, y1 = box
    sx, sy = _shape_scale(occ)
    if isinstance(occ, Rect):
        hw, hh = occ.width / 2 * sx, occ.height / 2 * sy
        return (occ.x - hw <= x0 and occ.y - hh <= y0
                and occ.x + hw >= x1 and occ.y + hh >= y1)
    r = occ.radius * sx
    return all(math.hypot(px - occ.x, py - occ.y) <= r
               for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)))


def _hidden_names(scene, resolved, hide_names):
    """Names of objects completely covered by a solid object drawn later.
    Those objects are skipped entirely. Occluders that a hide mask can make
    transparent are never used, because the target would show through them."""
    objs = [resolved[o.name] for o in scene.objects]
    hidden = set()
    for i, o in enumerate(objs):
        if (getattr(o, "is_mask", False) or getattr(o, "mask_blur_only", False)
                or o.blur > 0 or o.backdrop_blur > 0 or o.motion_blur > 0):
            continue
        box = _loose_box(o)
        if box is None:
            continue
        for occ in objs[i + 1:]:
            if occ.name in hide_names:
                continue
            if _opaque_occluder(occ) and _covers(occ, box):
                hidden.add(o.name)
                break
    return hidden


class FrameContext:
    """Per-frame data for masks and occlusion. Built once per frame by features.py."""

    def __init__(self, scene):
        self.order = {o.name: i for i, o in enumerate(scene.objects)}
        self.resolved = {o.name: motion_fx.resolve_pose(o, scene) for o in scene.objects}
        self.masks = []
        has_blur = False
        hide_names = set()
        for m in getattr(scene, "_pro_masks", []):
            shape = scene.get_optional(m.shape_name)
            if shape is None:
                continue
            if m.mode == "blur":
                has_blur = True          # blur masks can smear hidden pixels, so occlusion is off
                continue
            strength = max(0.0, min(1.0, float(shape.mask_strength)))
            if strength <= 0:
                continue
            if m.mode == "hide":
                if m.targets is None:
                    limit = self.order.get(m.shape_name, -1)
                    hide_names |= {n for n, i in self.order.items() if i < limit}
                else:
                    hide_names |= set(m.targets)
            cover = coverage_copy(self.resolved[m.shape_name])
            self.masks.append((m, cover, strength, shape.mask_color,
                               float(getattr(shape, "mask_feather", 0.0))))
        self.hidden = set() if has_blur else _hidden_names(scene, self.resolved, hide_names)

    def for_object(self, obj):
        """Colour masks (cover, strength, mode, color) that apply to this object."""
        if getattr(obj, "is_mask", False):
            return []
        out = []
        for m, cover, strength, color, feather in self.masks:
            if obj.name == m.shape_name:
                continue
            if m.targets is None:
                applies = self.order.get(obj.name, -1) < self.order.get(m.shape_name, -1)
            else:
                applies = obj.name in m.targets
            if applies:
                out.append((cover, strength, m.mode, color, feather))
        return out


# ============================================================= Layer motion

class LayerMotion:
    """Moves an object up or down the draw order over time.

    keys: [(time, layer), ...]. layer is an absolute stack position: 0 is the back.
    Between keys the value eases with `ease`, which takes a name ("linear",
    "ease_in", "ease_out", "ease_in_out"), a curve() from engine.py, or any function
    from 0..1 to 0..1. The object swaps position when the eased value crosses a whole
    number, so the easing sets the timing of the swap."""

    def __init__(self, scene, name, keys, ease="ease_in_out"):
        if scene.get_optional(name) is None:
            raise KeyError("No object named %r for layer motion" % name)
        pts = sorted((float(t), float(v)) for t, v in keys)
        if not pts:
            raise ValueError("layer() needs at least one (time, layer) key")
        self.name = name
        self.keys = pts
        self.ease = _engine._ease_fn(ease)
        _register(scene, self)

    def value(self, t):
        pts = self.keys
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

    def update(self, scene, t):
        scene._pro_layer_values[self.name] = self.value(t)


def layer(scene, name, keys, ease="ease_in_out"):
    return LayerMotion(scene, name, keys, ease)


def _sort_layers(scene):
    """Reorder scene.objects. Unlayered objects keep their build order, and layered
    objects are inserted at their stack position. Deterministic, so scrubbing works.

    P10: objects added after the first frame get a build position at the end, so they
    are not ignored when the order is worked out."""
    values = getattr(scene, "_pro_layer_values", None)
    if not values:
        return
    base = getattr(scene, "_pro_base_order", None)
    if base is None:
        base = {}
        scene._pro_base_order = base
    for o in scene.objects:
        if o.name not in base:
            base[o.name] = len(base)
    fallback = len(base)
    free = sorted((o for o in scene.objects if o.name not in values),
                  key=lambda o: base.get(o.name, fallback))
    placed = sorted(((values[o.name], base.get(o.name, fallback), o)
                     for o in scene.objects if o.name in values),
                    key=lambda r: (r[0], r[1]))
    for v, _, o in placed:
        pos = max(0, min(len(free), int(round(v))))
        free.insert(pos, o)
    scene.objects[:] = free


# ============================================================= Emitter

class Emitter:
    """Particle sprites that keep spawning over time. Each particle is a soft radial
    glow that fades and shrinks over its life. Use blend="add" so overlapping glows
    brighten each other, like light or sparks.

    Scrub-safe: every particle's path is computed from its spawn index, not stepped
    frame by frame. The pool holds exactly the particles alive at one moment, so
    the object count stays fixed no matter how long the effect runs.
    Note: each sprite is drawn as an effect layer, so keep rate * life modest (under ~150).
    The emitter sets opacity and scale on its particles every frame. Do not set them yourself."""

    def __init__(self, scene, name, x, y, rate=30.0, life=1.5, speed=300.0, gravity=300.0,
                 color="#FFD166", radius=8.0, start=0.0, spread=60.0, angle=-90.0,
                 blend="add", seed=7, sprite=True):
        self.name = name
        self.x, self.y = float(x), float(y)
        self.rate = max(0.1, float(rate))
        self.life = max(0.05, float(life))
        self.speed = float(speed)
        self.gravity = float(gravity)
        self.start = float(start)
        self.spread = float(spread)
        self.angle = float(angle)
        self.seed = int(seed)
        self.pool = int(math.ceil(self.rate * self.life)) + 2
        self.names = []
        for i in range(self.pool):
            pname = "%s %d" % (name, i)
            scene.add_circle(pname, x=self.x, y=self.y, radius=radius, color=color,
                             stroke=0, filled=True, opacity=0.0)
            obj = scene.get(pname)
            obj.blend = blend
            if sprite:
                try:
                    import effects as ex
                    obj.gradient = ex.Gradient([(0.0, color), (1.0, "#000000")],
                                               kind="radial", radius=0.5)
                except Exception:
                    pass   # without effects.py the sprite is a plain disc
            self.names.append(pname)
        _register(scene, self)

    def _velocity(self, k):
        rng = random.Random(self.seed * 1000003 + k)
        a = math.radians(self.angle + rng.uniform(-self.spread / 2.0, self.spread / 2.0))
        v = self.speed * rng.uniform(0.5, 1.0)
        return math.cos(a) * v, math.sin(a) * v

    def update(self, scene, t):
        tau = t - self.start
        newest = int(math.floor(tau * self.rate)) if tau >= 0 else -1
        for slot, pname in enumerate(self.names):
            obj = scene.get(pname)
            obj.opacity = 0.0
            if newest < 0:
                continue
            # The latest particle that maps to this slot and has already spawned.
            k = newest - ((newest - slot) % self.pool)
            if k < 0:
                continue
            age = tau - k / self.rate
            if age < 0 or age > self.life:
                continue
            vx, vy = self._velocity(k)
            obj.x = self.x + vx * age
            obj.y = self.y + vy * age + 0.5 * self.gravity * age * age
            fade = _clamp(1.0 - age / self.life)
            obj.opacity = fade
            obj.scale = max(0.1, fade)


def emitter(scene, name, x, y, **kw):
    return Emitter(scene, name, x, y, **kw)
