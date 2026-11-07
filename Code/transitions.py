"""Reusable entrance and exit motions for MotionCode scripts.

Import in a script with:   import transitions as tr

Every function is a pure function of time, so it is safe to call from animate().
Pass the object's resting position as base=(x, y) so the offset is always measured
from where the object belongs, not from wherever it was last frame.

Example:
    tr.enter(scene.get("Title"), t, start=1.0, duration=0.6,
             style="slide_up", base=(960, 500), distance=60)
    tr.exit(scene.get("Title"), t, start=6.0, duration=0.5, style="fade")

Styles for enter() and exit():
    fade, slide_left, slide_right, slide_up, slide_down, pop, zoom
"""
import math


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


def progress(t, start, duration):
    """Linear 0..1 progress from start over duration seconds."""
    if duration <= 0:
        return 1.0 if t >= start else 0.0
    return clamp((t - start) / duration)


def ease_out(k):
    k = clamp(k)
    return 1.0 - (1.0 - k) ** 3


def ease_in_out(k):
    k = clamp(k)
    if k < 0.5:
        return 4.0 * k * k * k
    return 1.0 - ((-2.0 * k + 2.0) ** 3) / 2.0


def ease_out_back(k, overshoot=1.70158):
    k = clamp(k)
    c3 = overshoot + 1.0
    return 1.0 + c3 * (k - 1.0) ** 3 + overshoot * (k - 1.0) ** 2


# ----------------------------------------------------- single-property values

def fade_in(t, start, duration=0.5):
    """Opacity that rises from 0 to 1."""
    return ease_out(progress(t, start, duration))


def fade_out(t, start, duration=0.5):
    """Opacity that falls from 1 to 0."""
    return 1.0 - ease_out(progress(t, start, duration))


def slide_offset(t, start, duration=0.6, distance=120.0):
    """Offset that moves from +distance to 0. Multiply by -1 to come from the other side."""
    return distance * (1.0 - ease_out(progress(t, start, duration)))


def pop_scale(t, start, duration=0.5, overshoot=1.70158):
    """Scale that grows from 0 to 1 with a small overshoot."""
    return max(0.0, ease_out_back(progress(t, start, duration), overshoot))


def zoom_scale(t, start, duration=0.6, from_scale=1.6):
    """Scale that settles from from_scale down to 1."""
    return from_scale + (1.0 - from_scale) * ease_out(progress(t, start, duration))


# ----------------------------------------------------------- whole objects

_DIRECTIONS = {
    "slide_left": (-1.0, 0.0),
    "slide_right": (1.0, 0.0),
    "slide_up": (0.0, -1.0),
    "slide_down": (0.0, 1.0),
}


def enter(obj, t, start, duration=0.6, style="fade", base=None, distance=120.0):
    """Set opacity, position and scale of obj for an entrance at time start.
    Before start the object is hidden. After start + duration it rests at base."""
    if base is None:
        base = (obj.x, obj.y)
    bx, by = base
    if style == "fade":
        obj.opacity = fade_in(t, start, duration)
        obj.x, obj.y = bx, by
        return obj
    if style in _DIRECTIONS:
        dx, dy = _DIRECTIONS[style]
        off = slide_offset(t, start, duration, distance)
        # slide_left comes in from the left, slide_up from above, and so on.
        obj.opacity = fade_in(t, start, duration * 0.6)
        obj.x, obj.y = bx + dx * off, by + dy * off
        return obj
    if style == "pop":
        obj.opacity = 1.0 if t >= start else 0.0
        obj.scale = pop_scale(t, start, duration)
        obj.x, obj.y = bx, by
        return obj
    if style == "zoom":
        obj.opacity = fade_in(t, start, duration * 0.5)
        obj.scale = zoom_scale(t, start, duration)
        obj.x, obj.y = bx, by
        return obj
    raise ValueError("Unknown style %r. Use: fade, slide_left, slide_right, slide_up, slide_down, pop, zoom" % style)


def exit(obj, t, start, duration=0.5, style="fade", base=None, distance=120.0):
    """Set opacity, position and scale of obj for an exit that begins at start.
    Before start the object rests at base. After start + duration it is hidden."""
    if base is None:
        base = (obj.x, obj.y)
    bx, by = base
    k = progress(t, start, duration)
    if style == "fade":
        obj.opacity = 1.0 - ease_out(k)
        obj.x, obj.y = bx, by
        return obj
    if style in _DIRECTIONS:
        dx, dy = _DIRECTIONS[style]
        off = distance * ease_out(k)
        obj.opacity = 1.0 - ease_out(k)
        obj.x, obj.y = bx + dx * off, by + dy * off
        return obj
    if style == "pop":
        obj.opacity = 1.0 if t < start else (0.0 if k >= 1.0 else 1.0)
        obj.scale = 1.0 - ease_in_out(k)
        obj.x, obj.y = bx, by
        return obj
    if style == "zoom":
        obj.opacity = 1.0 - ease_out(k)
        obj.scale = 1.0 + 0.5 * ease_out(k)
        obj.x, obj.y = bx, by
        return obj
    raise ValueError("Unknown style %r. Use: fade, slide_left, slide_right, slide_up, slide_down, pop, zoom" % style)


def visible_between(t, a, b, fade=0.3):
    """Opacity that fades in at a and out at b. Zero outside that window."""
    if t < a or t > b:
        return 0.0
    return min(1.0, (t - a) / fade if fade > 0 else 1.0, (b - t) / fade if fade > 0 else 1.0)
