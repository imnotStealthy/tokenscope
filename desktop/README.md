# TokenScope — Desktop app

A lightweight desktop app that shows your **live local token usage** (Claude Code +
Codex) and **subscription utilization** (5h / weekly / Sonnet / Spark / credits) in
a dark dashboard — no MongoDB, no Node, no cloud.

It reuses the verified backend reader `../backend/local_sources.py` and reads only
local files: `~/.claude`, `~/.codex`, `~/.claude-rpc`. Nothing is sent anywhere; the
only network call is the optional Anthropic OAuth *usage* read (same as claude-rpc).

## Use the prebuilt Windows exe

```
desktop\dist\TokenScope.exe
```

Double-click it:
- it opens as a **native application window** (not a browser tab),
- a tray icon appears (tooltip shows live `C 5h %` / `X 5h %`),
- **closing the window** minimizes it to the tray; **right-click the tray → Show / Quit**.

The dashboard auto-refreshes every 30s; use the 7d / 30d / 90d buttons to change the
range. (On the rare host without the WebView2 runtime it falls back to opening the
default browser.)

## Build it yourself on Windows

```bat
cd desktop
build.bat
```

This creates a venv, installs `requirements.txt` + PyInstaller, and produces
`dist\TokenScope.exe` (single file, no console window).

## Build it yourself on macOS

```bash
cd desktop
./build_macos.sh
open dist/TokenScope.app
```

This creates a venv, installs `requirements.txt` + PyInstaller, and produces
`dist/TokenScope.app`.

The macOS app opens the same native dashboard window and local-only server, adds a
menu bar status item, and shows the same styled usage popup as Windows. Closing the
window hides it to the menu bar item.

## Run without building (dev)

```bat
cd desktop
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python tray.py          REM  or:  python server.py  (server only)
```

On macOS:

```bash
cd desktop
./run-dev-macos.sh
```

## Files

| File | Role |
|---|---|
| `tray.py` | native window (pywebview) + system-tray icon + menu |
| `server.py` | stdlib HTTP server: `/` (dashboard) + `/api/local/{summary,utilization,status}` |
| `web.py` | embedded single-file HTML/JS dashboard |
| `tokenscope-tray.spec` | PyInstaller build config |
| `tokenscope-macos.spec` | macOS PyInstaller app bundle config |
| `build.bat` / `run-dev.bat` | Windows build / dev-run helpers |
| `build_macos.sh` / `run-dev-macos.sh` | macOS build / dev-run helpers |

## Notes

- Port: prefers `8765`, falls back to a random free port if taken.
- It binds to `127.0.0.1` only (not reachable from other machines).
- The full React web app (stored-mode UI, manual import, thresholds) lives in
  `../frontend`; this tray exe is the standalone *local* view.
- Antigravity (Google) usage will appear here automatically once added to
  `local_sources.py`.
