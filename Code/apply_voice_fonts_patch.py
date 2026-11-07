"""Apply the voice-removal and Fonts-menu changes to features.py and audio_engine.py.

Run from the folder that holds the MotionCode files:
    python apply_voice_fonts_patch.py

Each old block must appear exactly once. If one does not, nothing is written
for that file and the script says which block was not found.
A backup named <file>.bak is written before each change.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

EDITS = {
    "features.py": [
        (
            '    "sine", "square", "triangle", "saw", "add_speech", "add_dialogue", "voice",\n'
            '    "emotion", "speed", "rate", "pitch", "piper:en_US-ryan-medium", "piper:en_US-amy-medium",\n'
            '    "import voice_tts", "from voice_tts import add_speech, add_dialogue, list_voices",\n',
            '    "sine", "square", "triangle", "saw",\n',
        ),
        (
            '        self.font_button = pf.FontLibraryButton(self, self.log, self._fonts_installed)\n'
            '        bar.addWidget(self.font_button)\n'
            '        font_folder_button = QPushButton("Font Folder")\n'
            '        font_folder_button.clicked.connect(self._open_font_folder)\n'
            '        bar.addWidget(font_folder_button)\n',
            '',
        ),
        (
            '        self._export_menu = export_menu\n',
            '        self._export_menu = export_menu\n'
            '        self._fonts_menu = pf.build_fonts_menu(self, self.log, self._fonts_installed)\n'
            '        self.menuBar().addMenu(self._fonts_menu)\n',
        ),
    ],
    "audio_engine.py": [
        (
            '        This shapes the background only. Speech emotion comes from the voice clip."""\n',
            '        This shapes the background only."""\n',
        ),
    ],
}


def apply(filename, edits):
    path = os.path.join(HERE, filename)
    if not os.path.exists(path):
        print("SKIP %s: file not found in %s" % (filename, HERE))
        return False
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    for old, new in edits:
        count = text.count(old)
        if count != 1:
            print("FAIL %s: expected one match, found %d. Nothing was changed in this file."
                  % (filename, count))
            print("  block starts with: %r" % old[:70])
            return False
    for old, new in edits:
        text = text.replace(old, new)
    shutil.copyfile(path, path + ".bak")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("OK   %s updated (backup: %s.bak)" % (filename, filename))
    return True


def main():
    ok = True
    for filename, edits in EDITS.items():
        ok = apply(filename, edits) and ok
    if ok:
        print("")
        print("Done. Next: delete voice_tts.py and the piper_voices folder if they exist.")
        print("Then run main.py.")
    else:
        print("")
        print("Some files were not changed. Paste this output and the file's surrounding lines.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
