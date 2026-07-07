# PyInstaller spec for the TokenScope macOS app bundle.
# Build: ./build_macos.sh
# Output: dist/TokenScope.app

import os

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = []
binaries = []
hiddenimports = [
    "local_sources",
    "web",
    "icon",
    "requests",
    "jwt",
    "webview",
    "webview.platforms.cocoa",
    "PyObjCTools.AppHelper",
]

for _pkg in ("webview",):
    try:
        d, b, h = collect_all(_pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    ["tray.py"],
    pathex=[".", "../backend"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "motor", "fastapi", "pandas", "numpy", "clr"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TokenScope",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TokenScope",
)

app = BUNDLE(
    coll,
    name="TokenScope.app",
    icon="tokenscope.icns" if os.path.exists("tokenscope.icns") else None,
    bundle_identifier="com.stealthy.tokenscope",
    info_plist={
        "CFBundleName": "TokenScope",
        "CFBundleDisplayName": "TokenScope",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
    },
)
