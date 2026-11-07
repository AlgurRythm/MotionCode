"""Apply the Fonts-menu change and the audio docstring cleanup for MotionCode.

Run from the folder that holds the MotionCode files:
    python apply_voice_fonts_patch.py

What changes:
  UI.py           the Fonts and Font folder toolbar buttons are removed, and a
                  Fonts menu (built by projects_fonts.build_fonts_menu) is added
                  to the menu bar next to File.
  audio_engine.py the add_mood docstring no longer mentions speech.

features.py is not changed. The voice code was already removed from it.

Safe to run more than once: an edit that is already in place is skipped.
Each file is checked before anything is written. If a block is not found exactly
once, that file is left alone and the script says which block failed.
A backup named <file>.bak is written before each change.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

EDITS = {
    "UI.py": [
        # 1. Remove the old Fonts and Font folder toolbar buttons.
        (
            '        self.font_button = pf.FontLibraryButton(self, self.log, self._fonts_installed)\n'
            '        bar.addWidget(self.font_button)\n'
            '        font_folder_button = QPushButton("Font folder")\n'
            '        font_folder_button.clicked.connect(self._open_font_folder)\n'
            '        bar.addWidget(font_folder_button)\n',
            '',
        ),
        # 2. Add the Fonts menu right after the Export menu is stored.
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


def apply_file(filename, edits):
    path = os.path.join(HERE, filename)
    if not os.path.exists(path):
        print("SKIP %s: not found in %s" % (filename, HERE))
        return False

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    plan = []   # (old, new) pairs that still need applying
    for old, new in edits:
        if new and new in text:
            continue                      # already applied on a previous run
        if not new and text.count(old) == 0:
            continue                      # removal already done
        count = text.count(old)
        if count != 1:
            print("FAIL %s: expected one match, found %d. No changes were written to this file."
                  % (filename, count))
            print("  block starts with: %r" % old[:80])
            return False
        plan.append((old, new))

    if not plan:
        print("OK   %s already up to date" % filename)
        return True

    for old, new in plan:
        text = text.replace(old, new)
    shutil.copyfile(path, path + ".bak")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("OK   %s updated (%d edit%s, backup: %s.bak)"
          % (filename, len(plan), "" if len(plan) == 1 else "s", filename))
    return True


def main():
    ok = True
    for filename, edits in EDITS.items():
        ok = apply_file(filename, edits) and ok
    print("")
    if ok:
        print("Done. Next: delete voice_tts.py and the piper_voices folder if they exist,")
        print("then run main.py. The Fonts menu is in the menu bar.")
    else:
        print("Some files were not changed. Paste this output so the blocks can be checked.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
