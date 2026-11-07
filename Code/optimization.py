"""MotionCode speed-ups: image and lighting caches, the export worker,
and the time-remaining estimate. Nothing here draws objects itself; the export
worker receives the render function from features.py.
"""
import os
import time

import threading

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage


IMAGE_CACHE = {}   # (path, width, height) -> scaled QImage


GRID_CACHE = {}    # region -> pixel coordinate grids for lighting


LIGHT_CACHE = {}   # region + light settings -> brightness map


# Words that usually appear in a real ffmpeg error line.
ERROR_WORDS = ("error", "invalid", "unknown", "could not", "no such", "failed",
               "unrecognized", "cannot", "unable", "not found", "does not", "option")


CACHE_LOCK = threading.RLock()   # every cache write goes through remember(), under this lock


def remember(cache, key, value, limit):
    """Store value in a small cache, dropping the oldest entry when it is full.
    Thread-safe: the export thread and the UI thread may both write caches."""
    with CACHE_LOCK:
        if key not in cache and len(cache) >= limit:
            cache.pop(next(iter(cache)))
        cache[key] = value
    return value


def cached_image(path, width, height):
    """Load and scale an image once. Returns None if the file cannot be read."""
    key = (str(path), width, height)
    img = IMAGE_CACHE.get(key)
    if img is None:
        source = QImage(str(path))
        if source.isNull():
            return None
        img = source.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation)
        remember(IMAGE_CACHE, key, img, 64)
    return img


def pixel_grid(rect, sx, sy):
    key = (rect.x(), rect.y(), rect.width(), rect.height(), sx, sy)
    grid = GRID_CACHE.get(key)
    if grid is None:
        xs = (rect.x() + np.arange(rect.width()) + 0.5) / sx
        ys = (rect.y() + np.arange(rect.height()) + 0.5) / sy
        grid = remember(GRID_CACHE, key, tuple(np.meshgrid(xs, ys)), 6)
    return grid


def format_eta(seconds):
    """Human-readable time, such as '1 second', '1 minute' or '1 hour 5 minutes'."""
    if seconds is None or seconds != seconds or seconds == float("inf"):
        return "calculating…"
    seconds = int(round(max(0.0, seconds)))
    if seconds < 1:
        return "less than 1 second"
    if seconds < 60:
        return f"about {seconds} second" + ("" if seconds == 1 else "s")
    minutes = seconds // 60
    if minutes < 60:
        secs = seconds % 60
        text = f"about {minutes} minute" + ("" if minutes == 1 else "s")
        if minutes < 5 and secs:
            text += f" {secs} second" + ("" if secs == 1 else "s")
        return text
    hours = minutes // 60
    mins = minutes % 60
    text = f"about {hours} hour" + ("" if hours == 1 else "s")
    if mins:
        text += f" {mins} minute" + ("" if mins == 1 else "s")
    return text


class EtaTracker:
    """Estimates remaining time from the speed of recent frames."""

    def __init__(self, total, window=30):
        self.total = max(1, int(total))
        self.window = window
        self.samples = []
        self.start = time.monotonic()

    def update(self, done):
        self.samples.append((done, time.monotonic()))
        if len(self.samples) > self.window:
            self.samples.pop(0)

    def remaining(self, done):
        if done <= 0:
            return None
        if len(self.samples) >= 2:
            d0, t0 = self.samples[0]
            d1, t1 = self.samples[-1]
            if d1 > d0 and t1 > t0:
                rate = (d1 - d0) / (t1 - t0)
                return max(0.0, (self.total - done) / rate)
        elapsed = time.monotonic() - self.start
        return elapsed / done * (self.total - done)

    def elapsed(self):
        return time.monotonic() - self.start


def _remove_quietly(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def ffmpeg_failure_message(text, return_code=None):
    """Pick the real error out of ffmpeg's output. Informational lines such as
    'Qavg' from the AAC encoder are skipped. Returns the error line followed by
    the last few lines of output for context."""
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return f"ffmpeg exited with code {return_code}" if return_code is not None else "unknown error"
    hits = [l for l in lines if any(w in l.lower() for w in ERROR_WORDS)]
    main = hits[-1] if hits else lines[-1]
    tail = lines[-4:]
    context = "\n".join(tail)
    return main + ("\n" + context if context != main else "")
