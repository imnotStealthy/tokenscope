# PyInstaller spec for the TokenScope desktop app (native window + tray).
# Build:  pyinstaller --noconfirm tokenscope-tray.spec   (run from desktop/)
# Output: dist/TokenScope.exe  (single-file, no console window)

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
    'pystray._win32',      # Windows tray backend
    'webview',
    'webview.platforms.winforms',
    'webview.platforms.edgechromium',
    'clr',                 # pythonnet (winforms/edgechromium backend)
]

# Bundle pywebview's data/binaries/hidden imports (JS bridge, platform backends).
for _pkg in ('webview', 'clr_loader'):
    try:
        d, b, h = collect_all(_pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    ['tray.py'],
    pathex=['.', '../backend'],          # so `local_sources` and `web` resolve
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'motor', 'fastapi', 'pandas', 'numpy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TokenScope',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                       # GUI app: no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='tokenscope.ico',              # brands the exe, taskbar and app window
)
