"""MotionCode projects and fonts.

Projects: a project is one file (.mcp). The video script comes first, then a
separator line that starts with the pattern 000111000 and dashes, then the audio
script. Saves are crash-safe: the new file is written to a temporary name, flushed to
disk, and only then swapped in. The previous version is kept as <name>.mcp.bak.

Storage: when packaged as an exe or app, projects, cache and assets live in folders
created next to the app. When run from source, they live next to this file.

Fonts: every .ttf or .otf file in the fonts folder is loaded when MotionCode
starts, so scripts can use the family name directly:
    scene.add_text("Title", "HELLO", font="Oswald")
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

PROJECT_EXT = ".mcp"
PROJECT_FILTER = "MotionCode project (*.mcp)"
SEPARATOR_PATTERN = "000111000"
SEPARATOR_LINE = SEPARATOR_PATTERN + "-" * 40
FONT_EXTS = (".ttf", ".otf")

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


# ------------------------------------------------------------- storage

def app_dir():
    """Folder the app lives in. For a packaged exe this is the exe's folder."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    """The Data folder. It holds settings, the cache, projects, fonts, assets, OBJ models
    and the credits and licence text files.
    Packaged: Data next to MotionCode.exe. From source: a Data folder beside the code folder
    if one exists, otherwise Data inside the code folder. Created on first use."""
    base = app_dir()
    if not getattr(sys, "frozen", False):
        parent = os.path.dirname(base)
        if os.path.isdir(os.path.join(parent, "Data")) and not os.path.isdir(os.path.join(base, "Data")):
            base = parent
    folder = os.path.join(base, "Data")
    os.makedirs(folder, exist_ok=True)
    return folder


def find_data_file(name):
    """Full path of a file in the Data folder, or in the app folder as a fallback. None if missing."""
    for folder in (data_dir(), app_dir()):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    return None


def storage_dir(name):
    """A writable folder inside the Data folder, created on first use.
    Used for 'projects', 'cache', 'assets' and 'fonts'."""
    folder = os.path.join(data_dir(), name)
    os.makedirs(folder, exist_ok=True)
    return folder


def _settings():
    """Settings stored in a fixed file next to the app, so the remembered folder
    survives moving or re-running the app."""
    return QSettings(os.path.join(data_dir(), "motioncode_settings.ini"),
                     QSettings.Format.IniFormat)


def last_project_dir():
    """The folder used last time, or the projects folder if none is remembered."""
    folder = _settings().value("project/last_dir", "", type=str)
    return folder if folder and os.path.isdir(folder) else storage_dir("projects")


def remember_project_dir(folder):
    _settings().setValue("project/last_dir", os.path.abspath(folder))


def get_setting(key, default=""):
    """A remembered preference (for example the colour theme), or default."""
    return _settings().value(key, default, type=str)


def set_setting(key, value):
    _settings().setValue(key, value)


# ------------------------------------------------------------- crash-safe writes

def atomic_write_text(path, text):
    """Write text so a crash cannot leave a half-written file. The old file stays
    in place until the new one is fully on disk. The previous version is kept as
    <path>.bak."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".mc_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            shutil.copyfile(path, path + ".bak")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


# ------------------------------------------------------------- projects

def save_project_file(path, video_text, audio_text):
    """Write one project file: video script, separator line, audio script. Crash-safe."""
    if not path.lower().endswith(PROJECT_EXT):
        path += PROJECT_EXT
    body = video_text.rstrip("\n") + "\n" + SEPARATOR_LINE + "\n" + audio_text
    atomic_write_text(path, body)
    remember_project_dir(os.path.dirname(os.path.abspath(path)))
    return os.path.abspath(path)


def load_project_file(path):
    """Return (video_text, audio_text). The separator line marks where audio starts.
    A file with no separator is returned as video only, with audio None."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    remember_project_dir(os.path.dirname(os.path.abspath(path)))
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith(SEPARATOR_PATTERN):
            video = "\n".join(lines[:i]).rstrip("\n") + "\n"
            audio = "\n".join(lines[i + 1:])
            return video, audio
    return text, None


# ---------------------------------------------------------------- fonts

def ensure_font_folder():
    return storage_dir("fonts")


def load_project_fonts():
    """Load every font file in the fonts folder into the app. Returns the family names found.
    Call this after QApplication exists."""
    folder = ensure_font_folder()
    families = []
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(FONT_EXTS):
            font_id = QFontDatabase.addApplicationFont(os.path.join(folder, name))
            if font_id >= 0:
                families += QFontDatabase.applicationFontFamilies(font_id)
    return sorted(set(families))


def installed_names():
    """Font family names currently available to the app."""
    return set(QFontDatabase.families())


def font_files():
    """Font files in the fonts folder, as file names."""
    folder = ensure_font_folder()
    return sorted(n for n in os.listdir(folder) if n.lower().endswith(FONT_EXTS))


def _unique_font_path(base, ext):
    """A path in the fonts folder that is not already taken: Name.ttf, Name_2.ttf, ..."""
    folder = ensure_font_folder()
    target = os.path.join(folder, base + ext)
    counter = 2
    while os.path.exists(target):
        target = os.path.join(folder, "%s_%d%s" % (base, counter, ext))
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
    folder = ensure_font_folder()
    try:
        if sys.platform.startswith("win"):
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
        return None
    except (OSError, AttributeError) as exc:
        return "Could not open the fonts folder (%s). It is at: %s" % (exc, folder)


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
    """A Fonts menu for the menu bar. Items: default fonts and licenses, import a font,
    open the fonts folder. Returns the QMenu.
    Keep a reference to it so Qt does not drop it."""
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
    """Button that opens the Fonts and licenses dialog."""

    def __init__(self, parent, log, installed_cb):
        super().__init__("Fonts", parent)
        self._log = log
        self._installed_cb = installed_cb
        self.setToolTip("Default fonts, their licenses, and Import font")
        self.clicked.connect(self._open)

    def _open(self):
        FontsDialog(self.window(), self._log, self._installed_cb).exec()
