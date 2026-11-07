# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/fonts', 'fonts'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/assets', 'assets'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/LICENSE-Creator', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/NOTICE', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Third-Party-Notice.md', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/CREDITS.md', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Data/logo.ico', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/transitions.py', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/motion_fx.py', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/effects.py', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/FeaturesPro.py', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/engine.py', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/optimization.py', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/projects_fonts.py', '.'), ('C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Code/audio_engine.py', '.')]
binaries = []
hiddenimports = ['transitions', 'motion_fx', 'effects', 'FeaturesPro', 'engine', 'optimization', 'projects_fonts', 'audio_engine']
binaries += collect_dynamic_libs('PySide6')
hiddenimports += collect_submodules('PySide6.QtMultimedia')
tmp_ret = collect_all('imageio_ffmpeg')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick', 'PySide6.QtWebView', 'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtQuick', 'PySide6.QtQuick3D', 'PySide6.QtQml', 'PySide6.QtPdf', 'PySide6.QtNetwork', 'PySide6.QtSql', 'tkinter', 'matplotlib', 'scipy', 'pandas', 'IPython', 'notebook'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MotionCode',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/Users/winto/Music/PythonCode/MotionPython Studio - Series/MotionCodeV10/Data/logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MotionCode',
)
