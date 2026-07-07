# PyInstaller spec for the TokenScope macOS app (native WebKit window, no tray).
# Build (on macOS only): pyinstaller --noconfirm tokenscope-macos.spec   (run from desktop/)
# Output: dist/TokenScope.app — built in CI by .github/workflows/build-macos.yml,
# which also generates tokenscope.icns from icon.py before invoking PyInstaller.

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = []
binaries = []
hiddenimports = [
    'local_sources',
    'web',
    'icon',
    'requests',
    'jwt',                 # pyjwt (imported lazily inside local_sources)
    'webview',
    'webview.platforms.cocoa',
]

# Bundle pywebview's data/binaries/hidden imports (JS bridge, platform backends).
try:
    d, b, h = collect_all('webview')
    datas += d
    binaries += b
    hiddenimports += h
except Exception:
    pass

a = Analysis(
    ['macos.py'],
    pathex=['.', '../backend'],          # so `local_sources` and `web` resolve
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'motor', 'fastapi', 'pandas', 'numpy'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,               # onedir: the .app bundle carries the libs
    name='TokenScope',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                       # GUI app: no terminal window
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
    upx=False,
    name='TokenScope',
)

app = BUNDLE(
    coll,
    name='TokenScope.app',
    icon='tokenscope.icns',
    bundle_identifier='eu.stealthylabs.tokenscope',
    info_plist={
        'CFBundleName': 'TokenScope',
        'CFBundleDisplayName': 'TokenScope',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
    },
)
