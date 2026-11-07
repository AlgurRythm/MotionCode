"""MotionCode projects and fonts.

Projects: a project is a folder holding video.py and audio.py. The last folder
used is remembered between sessions.

Fonts: every .ttf or .otf file in the fonts folder is loaded when MotionCode
starts, so scripts can use the family name directly:
    scene.add_text("Title", "HELLO", font="Oswald")

The Fonts menu lists the default fonts with their licenses, the other fonts in
the fonts folder, and an Import font action that copies a font file into the
fonts folder and loads it.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from urllib.parse import urlparse

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget, QMenu, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(APP_DIR, "fonts")
FONT_EXTS = (".ttf", ".otf")
VIDEO_NAME = "video.py"
AUDIO_NAME = "audio.py"

OFL = "SIL Open Font License 1.1"
OFL_URL = "https://openfontlicense.org"

# Default fonts shown in the Fonts menu. Check each license on the font's own page
# before you publish work that uses it. Fill in "url" with a direct link to the
# .ttf file to make the Install button work; an empty url shows "No link set".
DEFAULT_FONTS = [
    {"name": "Oswald", "license": OFL, "license_url": OFL_URL, "url": ""},
    {"name": "Roboto", "license": "Apache License 2.0",
     "license_url": "https://www.apache.org/licenses/LICENSE-2.0", "url": ""},
    {"name": "Montserrat", "license": OFL, "license_url": OFL_URL, "url": ""},
    {"name": "Bebas Neue", "license": OFL, "license_url": OFL_URL, "url": ""},
    {"name": "Playfair Display", "license": OFL, "license_url": OFL_URL, "url": ""},
    {"name": "Source Code Pro", "license": OFL, "license_url": OFL_URL, "url": ""},
]


# ------------------------------------------------------------- settings

def _settings():
    return QSettings("MotionCode", "MotionCode")


def last_project_dir():
    folder = _settings().value("project/last_dir", "", type=str)
    return folder if folder and os.path.isdir(folder) else ""


def remember_project_dir(folder):
    _settings().setValue("project/last_dir", os.path.abspath(folder))


# ------------------------------------------------------------- projects

def save_project(folder, video_text, audio_text):
    """Write video.py and audio.py into folder. Creates the folder if needed."""
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, VIDEO_NAME), "w", encoding="utf-8") as f:
        f.write(video_text)
    with open(os.path.join(folder, AUDIO_NAME), "w", encoding="utf-8") as f:
        f.write(audio_text)
    remember_project_dir(folder)
    return os.path.abspath(folder)


LOAD_WARNINGS = []


def _read_text(path):
    """Read a project file. Bytes that are not UTF-8 are replaced, and a warning is kept
    so the user knows to save the file again."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    if "\ufffd" in text:
        LOAD_WARNINGS.append(
            "%s has bytes that are not UTF-8. They were replaced; save the file again to fix it."
            % os.path.basename(path))
    return text


def load_project(folder):
    """Return (video_text, audio_text). A missing file is returned as None.
    Warnings about the files are kept in LOAD_WARNINGS."""
    LOAD_WARNINGS.clear()
    texts = []
    for name in (VIDEO_NAME, AUDIO_NAME):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            texts.append(_read_text(path))
        else:
            texts.append(None)
    remember_project_dir(folder)
    return texts[0], texts[1]


# ---------------------------------------------------------------- fonts

def ensure_font_folder():
    os.makedirs(FONT_DIR, exist_ok=True)
    return FONT_DIR


def load_project_fonts():
    """Load every font file in the fonts folder into the app. Returns the family names found.
    Call this after QApplication exists."""
    ensure_font_folder()
    families = []
    for name in sorted(os.listdir(FONT_DIR)):
        if name.lower().endswith(FONT_EXTS):
            font_id = QFontDatabase.addApplicationFont(os.path.join(FONT_DIR, name))
            if font_id >= 0:
                families += QFontDatabase.applicationFontFamilies(font_id)
    return sorted(set(families))


def installed_names():
    """Font family names currently available to the app."""
    return set(QFontDatabase.families())


def font_files():
    """Font files in the fonts folder, as file names."""
    ensure_font_folder()
    return sorted(n for n in os.listdir(FONT_DIR) if n.lower().endswith(FONT_EXTS))


def _unique_font_path(base, ext):
    """A path in the fonts folder that is not already taken: Name.ttf, Name_2.ttf, ..."""
    target = os.path.join(FONT_DIR, base + ext)
    counter = 2
    while os.path.exists(target):
        target = os.path.join(FONT_DIR, "%s_%d%s" % (base, counter, ext))
        counter += 1
    return target


def _safe_base(name):
    return "".join(c for c in name if c.isalnum() or c in " -_").strip().replace(" ", "")


def _load_into_app(target, label):
    """Register a font file with the app. On failure the copied file is removed."""
    font_id = QFontDatabase.addApplicationFont(target)
    if font_id < 0:
        try:
            os.remove(target)
        except OSError:
            pass
        raise RuntimeError("%s is not a valid font file." % label)
    return sorted(set(QFontDatabase.applicationFontFamilies(font_id)))


def import_font_file(source):
    """Copy a .ttf or .otf file the user picked into the fonts folder and load it.
    Returns the family names added. Raises RuntimeError with a readable message."""
    base, ext = os.path.splitext(os.path.basename(source))
    ext = ext.lower()
    if ext not in FONT_EXTS:
        raise RuntimeError("Choose a .ttf or .otf font file.")
    safe = _safe_base(base)
    if not safe:
        raise RuntimeError("The file name %r cannot be used." % base)
    ensure_font_folder()
    target = _unique_font_path(safe, ext)
    try:
        shutil.copyfile(source, target)
    except OSError as exc:
        raise RuntimeError("Could not copy the font: %s" % exc)
    return _load_into_app(target, os.path.basename(source))


def install_font(name, url):
    """Download a default font into the fonts folder and load it. Returns the family names added.
    Raises RuntimeError with a readable message on failure."""
    if not url:
        raise RuntimeError("No download link is set for %s." % name)
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext not in FONT_EXTS:
        raise RuntimeError("The link for %s must point to a .ttf or .otf file." % name)
    ensure_font_folder()
    target = _unique_font_path(_safe_base(name), ext)
    fd, temp = tempfile.mkstemp(suffix=ext, prefix="motioncode_font_")
    os.close(fd)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "MotionCode"})
        with urllib.request.urlopen(request, timeout=30) as response, open(temp, "wb") as out:
            shutil.copyfileobj(response, out)
        if os.path.getsize(temp) < 1024:
            raise RuntimeError("The download for %s is too small to be a font file." % name)
        shutil.move(temp, target)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError("Download failed for %s: %s" % (name, exc))
    finally:
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except OSError:
                pass
    return _load_into_app(target, name)


def open_font_folder():
    """Open the fonts folder. Returns None on success, or a message if it could not be opened.
    Never raises, so a menu action can show the message in the log."""
    ensure_font_folder()
    try:
        if sys.platform.startswith("win"):
            os.startfile(FONT_DIR)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", FONT_DIR])
        else:
            subprocess.Popen(["xdg-open", FONT_DIR])
        return None
    except (OSError, AttributeError) as exc:
        return "Could not open the fonts folder (%s). It is at: %s" % (exc, FONT_DIR)


def import_font_at(path, log, installed_cb):
    """Import a picked font file, log the result, and tell the app about the new families."""
    try:
        families = import_font_file(path)
    except RuntimeError as exc:
        log(str(exc), error=True)
        return None
    name = families[0] if families else os.path.splitext(os.path.basename(path))[0]
    log("Imported %s into the fonts folder. Use font=\"%s\" in your text."
        % (os.path.basename(path), name))
    installed_cb(families)
    return families


# ------------------------------------------------------------ dialog

def _default_stems():
    """Lower-case file stems that default fonts are saved under once installed."""
    return {_safe_base(e["name"]).lower() for e in DEFAULT_FONTS}


class FontsDialog(QDialog):
    """Default fonts with their licenses, the other fonts in the fonts folder, and an
    Import font button."""

    def __init__(self, parent, log, installed_cb):
        super().__init__(parent)
        self.setWindowTitle("Fonts and licenses")
        self.resize(720, 460)
        self._log = log
        self._installed_cb = installed_cb

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Default fonts"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Font", "License", "Status", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)

        layout.addWidget(QLabel("Other fonts in the fonts folder"))
        self.others = QListWidget()
        self.others.setToolTip("Fonts you imported. Check each font's license before publishing.")
        layout.addWidget(self.others, 1)

        row = QHBoxLayout()
        import_button = QPushButton("Import font…")
        import_button.clicked.connect(self.import_font)
        row.addWidget(import_button)
        open_button = QPushButton("Open fonts folder")
        open_button.clicked.connect(self._open_folder)
        row.addWidget(open_button)
        row.addStretch(1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        row.addWidget(close_button)
        layout.addLayout(row)

        self.refresh()

    def refresh(self):
        have = installed_names()
        self.table.setRowCount(len(DEFAULT_FONTS))
        for row, entry in enumerate(DEFAULT_FONTS):
            name = entry["name"]
            self.table.setItem(row, 0, QTableWidgetItem(name))
            license_item = QTableWidgetItem(entry["license"])
            license_item.setToolTip(entry.get("license_url", ""))
            self.table.setItem(row, 1, license_item)
            installed = name in have
            self.table.setItem(row, 2, QTableWidgetItem("Installed" if installed else "Not installed"))
            if installed:
                self.table.setCellWidget(row, 3, QLabel("✓"))
            elif entry.get("url"):
                button = QPushButton("Install")
                button.clicked.connect(lambda _c=False, e=entry: self._install(e))
                self.table.setCellWidget(row, 3, button)
            else:
                self.table.setCellWidget(row, 3, QLabel("No link set"))
        self.table.resizeColumnsToContents()

        stems = _default_stems()
        self.others.clear()
        for filename in font_files():
            if os.path.splitext(filename)[0].lower() not in stems:
                self.others.addItem(filename)
        if self.others.count() == 0:
            self.others.addItem("No other fonts yet. Use Import font… to add one.")

    def _install(self, entry):
        try:
            families = install_font(entry["name"], entry.get("url", ""))
        except RuntimeError as exc:
            self._log(str(exc), error=True)
            return
        self._log("Installed %s. Use font=\"%s\" in your text."
                  % (entry["name"], families[0] if families else entry["name"]))
        self._installed_cb(families)
        self.refresh()

    def import_font(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import font", "", "Font files (*.ttf *.otf)")
        if path:
            import_font_at(path, self._log, self._installed_cb)
            self.refresh()

    def _open_folder(self):
        message = open_font_folder()
        if message:
            self._log(message, error=True)


def build_fonts_menu(parent, log, installed_cb):
    """A Fonts menu for the menu bar, next to File. Items: show default fonts and their
    licenses, import a font, open the fonts folder. Returns the QMenu.
    Keep a reference to it (features.py stores it on self) so Qt does not drop it."""
    menu = QMenu("Fonts", parent)

    def show_dialog():
        FontsDialog(parent, log, installed_cb).exec()

    def import_action():
        path, _ = QFileDialog.getOpenFileName(parent, "Import font", "", "Font files (*.ttf *.otf)")
        if path:
            import_font_at(path, log, installed_cb)

    def folder_action():
        message = open_font_folder()
        if message:
            log(message, error=True)

    menu.addAction("Default fonts and licenses…", show_dialog)
    menu.addAction("Import font…", import_action)
    menu.addSeparator()
    menu.addAction("Open fonts folder", folder_action)
    return menu



class FontLibraryButton(QPushButton):
    """Compatibility button for older features.py files. Opens the Fonts and licenses dialog."""

    def __init__(self, parent, log, installed_cb):
        super().__init__("Fonts", parent)
        self._log = log
        self._installed_cb = installed_cb
        self.setToolTip("Default fonts, their licenses, and Import font")
        self.clicked.connect(self._open)

    def _open(self):
        FontsDialog(self.window(), self._log, self._installed_cb).exec()