"""MotionCode window and widgets.

Rendering, script checks and constants live in features.py. This file only
builds the window and connects it to them. Start the app with features.run().

Look and feel: one neutral palette, one muted accent, and plain text labels.
All colours are in THEME, and one stylesheet (app_stylesheet) applies them.
"""
import html
import math
import os
import re
import shutil
import tempfile
import time
import traceback
from pathlib import Path

from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QCompleter, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFileDialog, QFormLayout,
    QFrame, QGroupBox, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressDialog, QPushButton, QSlider, QSpinBox,
    QSplitter, QTextBrowser, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)
from PySide6.QtCore import (
    QPointF, QRect, QRectF, QSize, QStringListModel, Qt, QTimer, QUrl, Signal,
)
from PySide6.QtGui import (
    QColor, QFont, QGuiApplication, QPainter, QPolygonF, QSyntaxHighlighter,
    QTextCharFormat, QTextCursor,
)

from engine import Scene
from optimization import EtaTracker, format_eta, remember, _remove_quietly
from export import (
    ExportJob, VIDEO_FORMATS, AUDIO_FORMATS, CRF_LEVELS, EXTRA_SIZES,
    probe_ffmpeg, available_audio_formats, build_video_command, render_audio_temp,
    export_audio_file, file_type_choices, AUTO_AUDIO,
)
import projects_fonts as pf
import FeaturesPro as pro
from features import (
    ANIM_ERRORS, AUDIO_FILE, AUDIO_WORDS, DEFAULT_QUALITY, ERROR_COLOR, EXPORT_STATS,
    FPS_MAX, FPS_MIN, INSPECTOR_DEFAULT_RANGE, INSPECTOR_RANGES, INSPECTOR_STEPS,
    PROFILE, QUALITY_ORDER, QUALITY_PRESETS, RENDER_ERRORS, RENDER_OPTS, RESOLUTIONS, SCRIPT_WORDS_ALL,
    STARTER, STARTER_AUDIO, VIDEO_FILE, VOLUME_MAX, VOLUME_MIN,
    draw_frame, error_lines_for, list_font_families, make_export_render, measure_text_px,
    render_frame, safe_animate, safe_render_audio, scan_script_mistakes,
)

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


# Storage folders resolve next to the app (or the exe when packaged).
ASSETS_DIR = pf.storage_dir("assets")
AUTOSAVE_DIR = pf.storage_dir("cache")
AUTOSAVE_VIDEO = os.path.join(AUTOSAVE_DIR, "video.py")
AUTOSAVE_AUDIO = os.path.join(AUTOSAVE_DIR, "audio.py")


# ------------------------------------------------------------ theme

PALETTES = {
    "dark": {
        "ui": {
            "window": "#2E3240", "panel": "#383D4C", "field": "#262A36",
            "border": "#525A6E", "text": "#F5F7FB", "muted": "#C3CAD9",
            "accent": "#7CC4FF", "marker": "#9AA3B8", "button": "#444B5C",
            "button_hover": "#525B6F", "gutter": "#21242E", "gutter_text": "#8A93A8",
            "error_bg": "#4A2328",
        },
        "code": {
            "keyword": "#FF7EB6", "builtin": "#66D9FF", "constant": "#FFB86B",
            "number": "#FFD479", "decorator": "#B48EFF", "string": "#9EFF8F",
            "comment": "#8C97AD",
        },
    },
    "light": {
        "ui": {
            "window": "#F3F5F9", "panel": "#FFFFFF", "field": "#FFFFFF",
            "border": "#C9D0DE", "text": "#1B2030", "muted": "#4D5566",
            "accent": "#1F6FE5", "marker": "#7B8496", "button": "#FFFFFF",
            "button_hover": "#E6EBF4", "gutter": "#EEF1F6", "gutter_text": "#8B93A3",
            "error_bg": "#FDE2E4",
        },
        "code": {
            "keyword": "#C2185B", "builtin": "#0277BD", "constant": "#B45309",
            "number": "#A16207", "decorator": "#6D28D9", "string": "#15803D",
            "comment": "#6B7280",
        },
    },
    "oled": {
        "ui": {
            "window": "#000000", "panel": "#0B0B0D", "field": "#000000",
            "border": "#26262B", "text": "#FFFFFF", "muted": "#A3A3AD",
            "accent": "#5CC8FF", "marker": "#6A6A74", "button": "#111114",
            "button_hover": "#1C1C22", "gutter": "#000000", "gutter_text": "#5E5E68",
            "error_bg": "#3A1116",
        },
        "code": {
            "keyword": "#FF7EB6", "builtin": "#66D9FF", "constant": "#FFB86B",
            "number": "#FFD479", "decorator": "#B48EFF", "string": "#9EFF8F",
            "comment": "#7A7A86",
        },
    },
}
THEME_CYCLE = ("dark", "light", "oled")
THEME_LABELS = {"dark": "Dark", "light": "Bright", "oled": "OLED"}
ACTIVE = {"name": "dark"}
THEME = dict(PALETTES["dark"]["ui"])   # updated in place by Main._apply_theme
MONO_FONT = "Consolas"


def app_stylesheet():
    """One stylesheet for the whole window. Widgets pick up their colours from here,
    so the look can be changed in THEME without touching the layout code."""
    t = THEME
    return f"""
    QWidget {{ background: {t['window']}; color: {t['text']}; font-size: 12px; }}
    QWidget#root {{ background: {t['window']}; }}
    QGroupBox {{ background: {t['panel']}; border: 1px solid {t['border']};
                 border-radius: 4px; margin-top: 14px; padding: 10px 8px 8px 8px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 8px; top: 2px;
                        color: {t['muted']}; padding: 0 4px; }}
    QLabel {{ background: transparent; color: {t['muted']}; }}
    QLabel#status {{ color: {t['text']}; }}
    QPushButton {{ background: {t['button']}; border: 1px solid {t['border']};
                   border-radius: 3px; padding: 4px 12px; color: {t['text']}; }}
    QPushButton:hover {{ background: {t['button_hover']}; }}
    QPushButton:pressed {{ background: {t['field']}; }}
    QPushButton:disabled {{ color: {t['muted']}; }}
    QComboBox, QSpinBox, QDoubleSpinBox {{ background: {t['field']}; border: 1px solid {t['border']};
                   border-radius: 3px; padding: 3px 6px; color: {t['text']}; }}
    QComboBox QAbstractItemView {{ background: {t['field']}; border: 1px solid {t['border']};
                   selection-background-color: {t['button_hover']}; }}
    QPlainTextEdit#code {{ background: {t['field']}; color: {t['text']};
                   border: 1px solid {t['border']}; border-radius: 3px;
                   selection-background-color: {t['button_hover']}; }}
    QPlainTextEdit#log {{ background: {t['field']}; color: {t['muted']};
                   border: 1px solid {t['border']}; border-radius: 3px;
                   font-family: {MONO_FONT}; font-size: 11px; }}
    QTreeWidget, QListWidget {{ background: {t['field']}; border: 1px solid {t['border']};
                   border-radius: 3px; outline: 0; }}
    QTreeWidget::item, QListWidget::item {{ padding: 3px 4px; }}
    QTreeWidget::item:selected, QListWidget::item:selected {{
                   background: {t['button_hover']}; color: {t['text']}; }}
    QHeaderView::section {{ background: {t['panel']}; color: {t['muted']};
                   border: none; padding: 4px; }}
    QSplitter::handle {{ background: {t['window']}; }}
    QSplitter::handle:horizontal {{ width: 6px; }}
    QSplitter::handle:vertical {{ height: 6px; }}
    QMenuBar {{ background: {t['window']}; color: {t['text']}; }}
    QMenuBar::item:selected {{ background: {t['button']}; }}
    QMenu {{ background: {t['panel']}; border: 1px solid {t['border']}; color: {t['text']}; }}
    QMenu::item:selected {{ background: {t['button_hover']}; }}
    QSlider::groove:horizontal {{ background: {t['border']}; height: 2px; }}
    QSlider::handle:horizontal {{ background: {t['text']}; width: 10px; height: 10px;
                   margin: -4px 0; border-radius: 5px; }}
    QToolTip {{ background: {t['panel']}; color: {t['text']}; border: 1px solid {t['border']}; }}
    """


# ------------------------------------------------------------ widgets

class ScriptHighlighter(QSyntaxHighlighter):
    """Colours Python keywords, builtins, numbers, strings, decorators and comments.
    Colours come from the active palette; set_colors() re-applies them after a theme change."""

    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        self.set_colors()

    def set_colors(self):
        c = PALETTES[ACTIVE["name"]]["code"]

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
        builtins = (r"\b(?:abs|len|range|min|max|print|int|float|str|list|dict|round|sum|"
                    r"sorted|enumerate|zip|open|math)\b")
        strings = r"\"[^\"\\]*(?:\\.[^\"\\]*)*\"|'[^'\\]*(?:\\.[^'\\]*)*'"
        self.rules = [
            (re.compile(keywords), fmt(c["keyword"], bold=True)),
            (re.compile(builtins), fmt(c["builtin"])),
            (re.compile(constants), fmt(c["constant"], bold=True)),
            (re.compile(r"\b\d+(?:\.\d+)?\b"), fmt(c["number"])),
            (re.compile(r"@\w+"), fmt(c["decorator"])),
            (re.compile(strings), fmt(c["string"])),
            (re.compile(r"#[^\n]*"), fmt(c["comment"], italic=True)),   # last: wins inside comments
        ]
        self.rehighlight()

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
        self.setObjectName("code")
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setUndoRedoEnabled(True)
        font = QFont(MONO_FONT)
        font.setPixelSize(13)
        self.setFont(font)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
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
            painter.fillRect(event.rect(), QColor(THEME["gutter"]))
            block = self.firstVisibleBlock()
            number = block.blockNumber()
            top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
            bottom = top + round(self.blockBoundingRect(block).height())
            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    painter.setPen(QColor(THEME["gutter_text"]))
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
        fmt.setBackground(QColor(THEME["error_bg"]))
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
            painter.fillRect(self.rect(), QColor(THEME["field"]))
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
    """Thin timeline. The played part uses the accent colour. Keyframe times are small ticks."""
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
            painter.setBrush(QColor(THEME["border"]))
            painter.drawRoundedRect(QRectF(m, cy - 1.5, span, 3), 1.5, 1.5)
            painter.setBrush(QColor(THEME["accent"]))
            painter.drawRoundedRect(QRectF(m, cy - 1.5, span * frac, 3), 1.5, 1.5)
            painter.setBrush(QColor(THEME["marker"]))
            for t in self._times:
                if 0 <= t <= self._duration:
                    x = m + t / self._duration * span
                    painter.drawRect(QRectF(x - 1, cy - 5, 2, 10))
            painter.setBrush(QColor(THEME["text"]))
            painter.drawEllipse(QPointF(m + frac * span, cy), 4.5, 4.5)
        finally:
            painter.end()


class TimelineMarkers(QWidget):
    """Keyframe times above the timeline. Kept for scripts that want a separate row."""
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
            painter.setBrush(QColor(THEME["marker"]))
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


class AdaptiveTextWindow(QWidget):
    """A text window that fits its text to the window size. Markdown is rendered by Qt,
    so tables, lists and links show properly. Plain text is escaped. When the text
    would become too small to read, it stops at MIN_PX and the window scrolls."""

    MIN_PX = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(760, 520)
        self.browser = QTextBrowser(self)
        self.browser.setOpenExternalLinks(True)
        self.browser.setFrameShape(QFrame.Shape.NoFrame)
        self.browser.setStyleSheet(f"QTextBrowser{{background:{THEME['field']};color:{THEME['text']};}}")
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


# ------------------------------------------------------------ main window

def _same_size(value, size):
    """True if a combo item's data equals (w, h). Qt may return tuples as lists."""
    try:
        return value is not None and tuple(value) == tuple(size)
    except TypeError:
        return False


def _find_size_index(box, size):
    """Index of the combo item whose data is (w, h), or 0 if none matches."""
    for i in range(box.count()):
        if _same_size(box.itemData(i), size):
            return i
    return 0


class ExportDialog(QDialog):
    """Pick a file type, then Export. The audio track is chosen automatically for each
    file type, so there is nothing else to set for sound. Only encoders this ffmpeg build has are offered."""

    def __init__(self, parent, ffmpeg_names, current_fps, current_quality, current_size):
        super().__init__(parent)
        self.setWindowTitle("Export")
        self.setMinimumWidth(440)
        self._audio_ok = set(available_audio_formats(ffmpeg_names))
        form = QFormLayout(self)

        self.file_type = QComboBox()
        for label, kind, key in file_type_choices(ffmpeg_names):
            self.file_type.addItem(label, (kind, key))
        self.size = self._combo([(f"{n} ({w}×{h})", (w, h)) for n, w, h in RESOLUTIONS]
                                + EXTRA_SIZES)
        self.size.setCurrentIndex(_find_size_index(self.size, current_size))
        self.fps = QSpinBox()
        self.fps.setRange(FPS_MIN, FPS_MAX)
        self.fps.setValue(current_fps)
        self.quality = self._combo([(QUALITY_PRESETS[k]["label"], k) for k in QUALITY_ORDER])
        self._select(self.quality, current_quality)
        self.crf = self._combo(CRF_LEVELS)

        form.addRow("File type", self.file_type)
        form.addRow("Resolution", self.size)
        form.addRow("FPS", self.fps)
        form.addRow("Resolution elements", self.quality)
        form.addRow("Compression", self.crf)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.file_type.currentIndexChanged.connect(self._refresh)
        self._refresh()

    @staticmethod
    def _combo(items):
        box = QComboBox()
        for label, data in items:
            box.addItem(label, data)
        return box

    @staticmethod
    def _select(box, value):
        for i in range(box.count()):
            if box.itemData(i) == value:
                box.setCurrentIndex(i)
                return

    def _refresh(self):
        kind, key = self.file_type.currentData()
        is_audio = kind == "audio"
        self.size.setEnabled(not is_audio)
        self.fps.setEnabled(not is_audio)
        self.quality.setEnabled(not is_audio)
        self.crf.setEnabled(kind == "video" and key != "gif")

    def settings(self):
        kind, key = self.file_type.currentData()
        if kind == "video":
            ext = VIDEO_FORMATS[key]["ext"]
            audio = AUTO_AUDIO.get(key)
        elif kind == "audio":
            ext = AUDIO_FORMATS[key]["ext"]
            audio = key
        else:
            ext = ""
            audio = None
        if audio not in self._audio_ok:
            audio = None   # this ffmpeg build cannot write that track: export without sound
        return {"kind": kind, "format": key if kind == "video" else None, "ext": ext,
                "size": self.size.currentData(), "fps": int(self.fps.value()),
                "crf": self.crf.currentData(), "audio_format": audio,
                "quality": self.quality.currentData()}


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MotionCode")
        self._theme_name = pf.get_setting("ui/theme", "dark")
        self._apply_theme(self._theme_name, save=False)
        self._fit_window_to_screen()
        self.scene = Scene()
        self.t = 0.0
        self.playing = False
        self._project_path = None
        self.speed = 1.0
        self._last_tick = None
        self._pending_scrub = None
        self._last_update_key = None
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
        self.res_combo.setCurrentIndex(_find_size_index(self.res_combo, (1280, 720)))   # 720p
        self.res_combo.currentIndexChanged.connect(self.resolution_changed)

        self.quality_combo = QComboBox()
        for key in QUALITY_ORDER:
            self.quality_combo.addItem(QUALITY_PRESETS[key]["label"], key)
        self.quality_combo.setCurrentIndex(self.quality_combo.findData(DEFAULT_QUALITY))
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
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(8)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.apply_all)
        bar.addWidget(apply_button)
        self._build_file_menu()
        self._build_credits_menu()
        bar.addStretch()
        self.status = QLabel("Ready")
        self.status.setObjectName("status")
        bar.addWidget(self.status)
        layout.addLayout(bar, 0)

        split = QSplitter(Qt.Orientation.Horizontal)

        editors = QSplitter(Qt.Orientation.Horizontal)

        video_panel = QWidget()
        vp = QVBoxLayout(video_panel)
        vp.setContentsMargins(0, 0, 0, 0)
        vp.addWidget(QLabel("Video script"))
        self.editor = CodeEditor()
        self.editor.setPlainText(STARTER)
        vp.addWidget(self.editor, 1)
        editors.addWidget(video_panel)

        audio_panel = QWidget()
        ap = QVBoxLayout(audio_panel)
        ap.setContentsMargins(0, 0, 0, 0)
        audio_head = QHBoxLayout()
        audio_head.addWidget(QLabel("Audio script"))
        audio_head.addStretch()
        apply_audio_button = QPushButton("Apply audio")
        apply_audio_button.clicked.connect(self.apply_audio)
        audio_head.addWidget(apply_audio_button)
        ap.addLayout(audio_head)
        self.audio_editor = CodeEditor()
        self.audio_editor.setPlainText(STARTER_AUDIO)
        ap.addWidget(self.audio_editor, 1)
        editors.addWidget(audio_panel)
        editors.setSizes([330, 330])
        split.addWidget(editors)

        right = QSplitter(Qt.Orientation.Vertical)
        self.preview = Preview()
        self.preview.set_resolution(*(self.res_combo.currentData() or (1280, 720)))
        self.preview.render_fn = self._render_preview
        right.addWidget(self.preview)
        lower = QWidget()
        lv = QVBoxLayout(lower)
        lv.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        self.play = QPushButton("Play")
        self.play.setFixedWidth(72)
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
        self.tree.setHeaderLabels(["Objects (top is front)"])
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
        self._restore_quality = None   # quality to put back after an export
        left_layout.addWidget(self.tree, 1)
        self.log_box = QPlainTextEdit()
        self.log_box.setObjectName("log")
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(300)
        self.log_box.setMaximumHeight(72)
        left_layout.addWidget(self.log_box)
        bottom.addWidget(left)

        self.settings = QGroupBox("Settings")
        settings_form = QFormLayout(self.settings)
        settings_form.addRow("Resolution", self.res_combo)
        settings_form.addRow("Resolution elements", self.quality_combo)
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

        self.inspector = QGroupBox("Inspector")
        self.form = QFormLayout(self.inspector)
        bottom.addWidget(self.inspector)
        lv.addWidget(bottom)
        right.addWidget(lower)
        right.setStretchFactor(0, 1)
        right.setStretchFactor(1, 0)
        right.setSizes([640, 230])

        # Assets panel, to the right of the preview.
        assets_panel = QWidget()
        av = QVBoxLayout(assets_panel)
        av.setContentsMargins(0, 0, 0, 0)
        assets_head = QHBoxLayout()
        assets_head.addWidget(QLabel("Assets"))
        assets_head.addStretch(1)
        import_button = QPushButton("Import")
        import_button.clicked.connect(self.import_assets)
        assets_head.addWidget(import_button)
        av.addLayout(assets_head)
        self.asset_list = QListWidget()
        self.asset_list.setToolTip("Double-click to preview. In the audio script use "
                                   "audio.add_clip(\"Name\", \"file.mp3\", at=0.0)")
        self.asset_list.itemDoubleClicked.connect(self.preview_asset)
        av.addWidget(self.asset_list, 1)
        self.asset_hint = QLabel("Imported files are kept in the assets folder.")
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

        self._build_theme_toggle()
        self.log("MotionCode started")
        if self.fonts_loaded:
            self.log("Fonts loaded: " + ", ".join(self.fonts_loaded))
        if not AUDIO_ENGINE_OK:
            self.log("Audio engine unavailable: " + AUDIO_IMPORT_ERROR, error=True)
        elif not MULTIMEDIA_OK:
            self.log("Audio preview unavailable: PySide6.QtMultimedia could not be loaded", error=True)

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
        for label, fn in [("New", self.new), ("Open project…", self.open_project),
                          ("Save project", self.save_project),
                          ("Save project as…", self.save_project_as)]:
            action = file_menu.addAction(label)
            action.triggered.connect(fn)
        file_menu.addSeparator()
        check = file_menu.addAction("Check script")
        check.triggered.connect(self.check_video)
        export_menu = file_menu.addMenu("Export")
        export_menu.addAction("Export…", self.open_export_dialog)
        export_menu.addSeparator()
        export_menu.addAction("PNG frames…", lambda: self.start_export(
            {"kind": "png", "size": self.current_resolution(), "fps": self.current_fps()}))
        self._export_menu = export_menu
        self._fonts_menu = pf.build_fonts_menu(self, self.log, self._fonts_installed)
        self.menuBar().addMenu(self._fonts_menu)

    def _build_theme_toggle(self):
        """Dark / bright switch in the top-right corner of the menu bar."""
        self._theme_button = QPushButton()
        self._theme_button.setToolTip("Click to change theme: Dark, Bright, OLED")
        self._theme_button.clicked.connect(self._toggle_theme)
        self.menuBar().setCornerWidget(self._theme_button, Qt.Corner.TopRightCorner)
        self._apply_theme(ACTIVE["name"], save=False)

    def _toggle_theme(self):
        i = THEME_CYCLE.index(ACTIVE["name"])
        self._apply_theme(THEME_CYCLE[(i + 1) % len(THEME_CYCLE)])

    def _apply_theme(self, name, save=True):
        if name not in PALETTES:
            name = "dark"
        ACTIVE["name"] = name
        THEME.clear()
        THEME.update(PALETTES[name]["ui"])
        self.setStyleSheet(app_stylesheet())
        if hasattr(self, "editor"):
            self.editor._highlighter.set_colors()
            self.audio_editor._highlighter.set_colors()
            self.preview.update()
        if hasattr(self, "_theme_button"):
            self._theme_button.setText("Theme: " + THEME_LABELS[name])
        if save:
            pf.set_setting("ui/theme", name)

    def _build_credits_menu(self):
        credits_menu = self.menuBar().addMenu("Credits")
        credits_menu.addAction("Credits", self._show_credits)
        credits_menu.addSeparator()
        credits_menu.addAction("License", lambda: self._open_legal_file("LICENSE"))
        credits_menu.addAction("Notice", lambda: self._open_legal_file("NOTICE"))
        credits_menu.addAction("Third-party notices",
                               lambda: self._open_legal_file("THIRD_PARTY_NOTICES.md"))
        self._credits_menu = credits_menu

    def _show_credits(self):
        self._show_text_window("_credits_window", "CREDITS.md", "MotionCode credits")

    def _open_legal_file(self, filename):
        self._show_text_window("_legal_window", filename, f"MotionCode - {filename}")

    def _show_text_window(self, attr, filename, title):
        path = os.path.join(pf.app_dir(), filename)
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
                f'<span style="color:{ERROR_COLOR}">{stamp}  {html.escape(message)}</span>')
        else:
            self.log_box.appendPlainText(f"{stamp}  {message}")

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
        if getattr(self, "_asset_player", None) is None:
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
        self._last_update_key = None   # an edit changes the picture even at the same time

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
        self._apply_quality(key)
        self.log(f"Quality set to {QUALITY_PRESETS[key]['label']}")

    def _apply_quality(self, key):
        """Set the render quality. Scripts that read quality at build time are rebuilt."""
        RENDER_OPTS.update(QUALITY_PRESETS[key])   # update in place, features.py reads this dict
        pro.set_quality(key)
        self._frame_cache.clear()
        self._last_update_key = None
        if self._quality_dependent:
            self.apply_all()
        else:
            self.update_at(self.t)

    def _prepare_quality(self, s):
        """Use the export dialog's quality for this export. The previous quality comes back when it ends."""
        self._restore_quality = None
        key = s.get("quality")
        old = self.current_quality()
        if key and key != old:
            self._restore_quality = old
            self._apply_quality(key)

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
        self._last_update_key = None
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
            self.status.setText("Applied · {} objects{}".format(len(candidate.objects), note))
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
        t = max(0.0, min(float(self.scene.duration), float(t)))
        key = (round(t, 4), self._scene_gen)
        if key == self._last_update_key:
            return   # same time and same scene: nothing new to draw
        self._last_update_key = key
        self.t = t
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
            label = name if not parent_name else f"{name}   of {parent_name}"
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
        self._last_update_key = None
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
            # Store the value; tick() applies it on the next timer pass (throttled).
            self._pending_scrub = value / 1000 * self.scene.duration

    def toggle(self):
        self.playing = not self.playing
        self._last_tick = None
        self.play.setText("Pause" if self.playing else "Play")
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
        pending = self._pending_scrub
        if pending is not None and not self.playing:
            self._pending_scrub = None
            self.update_at(pending)
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
        if not self._project_path:
            return self.save_project_as()
        self._write_project(self._project_path)

    def save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save project", os.path.join(pf.last_project_dir(), "project.mcp"), pf.PROJECT_FILTER)
        if path:
            self._project_path = path
            self._write_project(path)

    def _write_project(self, path):
        try:
            where = pf.save_project_file(path, self.editor.toPlainText(), self.audio_editor.toPlainText())
            self._project_path = where
            self.status.setText(f"Saved {os.path.basename(where)}")
            self.log(f"Saved project to {where}")
        except OSError as exc:
            self.log(f"Save failed: {exc}", error=True)

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open project", pf.last_project_dir(), pf.PROJECT_FILTER)
        if not path:
            return
        try:
            video, audio = pf.load_project_file(path)
        except OSError as exc:
            self.log(f"Open failed: {exc}", error=True)
            return
        self._project_path = path
        self.editor.setPlainText(video)
        if audio is not None:
            self.audio_editor.setPlainText(audio)
        self.log(f"Opened project {os.path.basename(path)}")
        self.apply_all()

    def _fonts_installed(self, families):
        self._scene_gen += 1
        self._frame_cache.clear()
        self._last_update_key = None
        self._refresh_completions()
        self.update_at(self.t)

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

    def open_export_dialog(self):
        if self._export_job is not None:
            return
        try:
            _ffmpeg, names = probe_ffmpeg()
        except Exception as exc:
            self.log(f"Export unavailable: {exc}", error=True)
            return
        dlg = ExportDialog(self, names, self.current_fps(), self.current_quality(),
                           self.current_resolution())
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self.start_export(dlg.settings())

    def _pick_save(self, ext, title, stem):
        path, _ = QFileDialog.getSaveFileName(self, title, stem + ext, f"*{ext}")
        if path and not path.lower().endswith(ext):
            path += ext
        return path

    def start_export(self, s):
        if s["kind"] == "png":
            return self._export_png(s)
        if s["kind"] == "audio":
            return self._export_audio_only(s)
        return self._export_video(s)

    def _export_png(self, s):
        folder = QFileDialog.getExistingDirectory(self, "Choose PNG frame folder")
        if not folder:
            return
        w, h = s["size"] or self.current_resolution()
        fps = s["fps"]
        total = max(1, int(round(self.scene.duration / self.speed * fps)) + 1)
        self._prepare_quality(s)
        job = ExportJob(self._scene_snapshot(), self.animate_fn, w, h, fps, self.speed,
                        total, folder, "png", render_fn=make_export_render())
        self.log(f"PNG export started: {total} frames at {w}×{h}, {fps} fps")
        self._run_export_job(job, "Exporting PNG frames", total)

    def _export_audio_only(self, s):
        if self.audio_scene is None or not self.audio_scene.events:
            self.log("Audio export skipped: no sounds applied yet", error=True)
            return
        path = self._pick_save(s["ext"], "Export audio", "soundtrack")
        if not path:
            return
        try:
            stereo, problems = safe_render_audio(self.audio_scene, self.speed, self.volume_gain())
            for problem in problems:
                self.log(problem, error=True)
            export_audio_file(stereo, self.audio_scene.sample_rate, path, s["audio_format"])
            self.status.setText("Audio exported")
            self.log(f"Audio saved: {Path(path).name}")
        except Exception as exc:
            self.log(f"Audio export failed: {exc}", error=True)

    def _export_video(self, s):
        fmt = s["format"]
        path = self._pick_save(s["ext"], "Export video", "animation")
        if not path:
            return
        ffmpeg, _names = probe_ffmpeg()
        w, h = s["size"] or self.current_resolution()
        fps = s["fps"]
        total = max(1, int(round(self.scene.duration / self.speed * fps)))
        akey = s["audio_format"]
        audio_path = None
        if akey and fmt != "gif" and AUDIO_ENGINE_OK and self.audio_scene and self.audio_scene.events:
            try:
                stereo, problems = safe_render_audio(self.audio_scene, self.speed, self.volume_gain())
                for problem in problems:
                    self.log(problem, error=True)
                audio_path = render_audio_temp(stereo, self.audio_scene.sample_rate)
            except Exception as exc:
                self.log(f"Audio skipped for this export: {exc}", error=True)
                audio_path = None
        try:
            cmd = build_video_command(ffmpeg, fmt, w, h, fps, total, path, audio_path, akey,
                                      s["crf"], self.encoder_combo.currentData() == "nvenc")
        except ValueError as exc:
            _remove_quietly(audio_path)
            self.log(str(exc), error=True)
            return
        self.log(f"{VIDEO_FORMATS[fmt]['label']} export started: {total} frames at {w}×{h}, "
                 f"{fps} fps, speed {self.speed:.2f}x")
        self._prepare_quality(s)
        job = ExportJob(self._scene_snapshot(), self.animate_fn, w, h, fps, self.speed, total,
                        path, "video", cmd=cmd, temp_paths=[audio_path] if audio_path else [],
                        render_fn=make_export_render())
        self._run_export_job(job, f"Exporting {VIDEO_FORMATS[fmt]['label']} ({w}×{h}, {fps} fps)",
                             total)

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
        if self._restore_quality:
            old, self._restore_quality = self._restore_quality, None
            self._apply_quality(old)
        self._last_update_key = None
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

    def _autosave(self):
        try:
            os.makedirs(AUTOSAVE_DIR, exist_ok=True)
            pf.atomic_write_text(AUTOSAVE_VIDEO, self.editor.toPlainText())
            pf.atomic_write_text(AUTOSAVE_AUDIO, self.audio_editor.toPlainText())
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
