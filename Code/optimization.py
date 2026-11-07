"""MotionCode speed-ups: image and lighting caches, the export worker,
and the time-remaining estimate. Nothing here draws objects itself; the export
worker receives the render function from features.py.
"""
import os
import subprocess
import tempfile
import time
import traceback
from pathlib import Path

import threading

import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
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


class ExportJob(QThread):
    """Renders frames from a scene and writes them out. Runs on a background
    thread when started with start(), or on the calling thread with run()."""
    progress = Signal(int)
    succeeded = Signal(str)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, scene, animate_fn, width, height, fps, speed, total, out_path,
                 mode, cmd=None, temp_paths=(), render_fn=None):
        super().__init__()
        self.scene = scene
        self.animate_fn = animate_fn
        self.width = width
        self.height = height
        self.fps = fps
        self.speed = speed
        self.total = total
        self.out_path = out_path
        self.mode = mode
        self.cmd = cmd
        self.temp_paths = list(temp_paths)
        self.render_fn = render_fn
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            if self.mode == "png":
                self._run_png()
            else:
                self._run_video()
        finally:
            for path in self.temp_paths:
                _remove_quietly(path)

    def _time_for(self, index):
        return index * self.speed / self.fps

    def _run_png(self):
        skipped = 0
        first_error = None
        for index in range(self.total):
            if self._cancel:
                self.cancelled.emit()
                return
            try:
                frame = self.render_fn(self.scene, self.animate_fn, self.width, self.height,
                                       self._time_for(index), self.fps)
                frame.save(str(Path(self.out_path) / f"frame_{index:05d}.png"))
            except Exception as exc:
                skipped += 1
                if first_error is None:
                    first_error = f"frame {index}: {type(exc).__name__}: {exc}"
            self.progress.emit(index + 1)
        note = f" ({skipped} frames skipped; first problem: {first_error})" if skipped else ""
        self.succeeded.emit(f"PNG export finished: {self.total} frames{note}")

    def _run_video(self):
        frame_size = self.width * self.height * 4
        row_bytes = self.width * 4
        last_good = bytes(frame_size)
        failed_frames = 0
        first_error = None
        error = None
        cancelled = False

        # Created before Popen so it is closed on every path.
        stderr_log = tempfile.TemporaryFile()
        try:
            proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stderr=stderr_log)
        except OSError as exc:
            stderr_log.close()
            self.failed.emit(f"could not start ffmpeg: {exc}")
            return

        try:
            for index in range(self.total):
                if self._cancel:
                    cancelled = True
                    break
                try:
                    frame = self.render_fn(self.scene, self.animate_fn, self.width, self.height,
                                           self._time_for(index), self.fps)
                    # Copy row by row: Qt may pad each row beyond width * 4 bytes.
                    stride = frame.bytesPerLine()
                    raw = bytes(frame.constBits())
                    if stride == row_bytes:
                        data = raw[:frame_size]
                    else:
                        data = b"".join(raw[r * stride:r * stride + row_bytes]
                                        for r in range(self.height))
                    last_good = data
                except Exception as exc:
                    # A broken frame repeats the last good one, so the video still finishes.
                    failed_frames += 1
                    if first_error is None:
                        first_error = f"frame {index}: {type(exc).__name__}: {exc}"
                    data = last_good
                proc.stdin.write(data)
                self.progress.emit(index + 1)
        except BrokenPipeError:
            error = "ffmpeg stopped reading frames."
        except Exception:
            error = traceback.format_exc()
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            # No return here: a return in finally would swallow exceptions.
            return_code = proc.wait()
            stderr_log.seek(0)
            ffmpeg_output = stderr_log.read().decode("utf-8", errors="replace")[-4000:]
            stderr_log.close()

        if cancelled:
            _remove_quietly(self.out_path)
            self.cancelled.emit()
            return
        if error or return_code != 0:
            _remove_quietly(self.out_path)
            if error:
                message = error + "\n" + ffmpeg_failure_message(ffmpeg_output, return_code)
            else:
                message = ffmpeg_failure_message(ffmpeg_output, return_code)
            self.failed.emit(message)
            return
        note = f", {failed_frames} frames repeated after errors ({first_error})" if failed_frames else ""
        self.succeeded.emit(f"Video saved: {Path(self.out_path).name} ({self.total} frames, "
                            f"{self.width}×{self.height}, {self.fps} fps{note})")
