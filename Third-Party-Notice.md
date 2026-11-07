# Third-party notices

MotionCode is made with, and can use, the software below. Each item keeps its own
license. The MotionCode code itself is under the MIT License (see LICENSE).

Confirm each license against the files in your installed packages before you publish.
Items marked **[CHECK]** are not verified.

## Libraries

| Component | Used for | License | Notes |
|---|---|---|---|
| PySide6 (Qt for Python) | The app window and Qt Multimedia | LGPL v3 **[CHECK the installed version]** | The Qt libraries can be replaced by users. Include the LGPL text and this notice in any release. |
| numpy | Image and audio maths | BSD 3-Clause | Include the license text in releases. |
| imageio-ffmpeg | Provides the ffmpeg binary for export | BSD 2-Clause (the wrapper) | The bundled ffmpeg binary has its own license, below. |

## Bundled binary

| Component | Used for | License | Notes |
|---|---|---|---|
| ffmpeg (inside imageio-ffmpeg) | Video and audio encoding, GIF export | LGPL v2.1 or later, or GPL **[CHECK the build]** | The license depends on how the binary was built. If it is a GPL build, you must offer its source code and include the GPL text. Qt's startup message reports "LGPL version 2.1 or later" for the FFmpeg it loaded. |

## Fonts

Fonts are not bundled with MotionCode. Users import fonts themselves, or install them
from the Fonts menu. The default fonts listed in the app are shown with these licenses:

| Font | License |
|---|---|
| Oswald | SIL Open Font License 1.1 |
| Montserrat | SIL Open Font License 1.1 |
| Bebas Neue | SIL Open Font License 1.1 |
| Playfair Display | SIL Open Font License 1.1 |
| Source Code Pro | SIL Open Font License 1.1 |
| Roboto | Apache License 2.0 |

If you ever include a font file in a release, include its license text with it.
The SIL Open Font License also says a modified font may not use the original font's
reserved name.

## Not used

Voice engines (Piper, Windows SAPI) have been removed. Their licenses no longer apply.
