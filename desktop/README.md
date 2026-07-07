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

## macOS app

A native macOS build (`TokenScope.app`) is produced by the
`.github/workflows/build-macos.yml` GitHub Actions workflow on every `v*` tag and
attached to the release as `TokenScope-macos.zip`. It runs the same server and
dashboard in a native window, adds a menu bar status item showing the same styled
usage popup as Windows (`tray.py` + `tokenscope-macos.spec`), and closing the
window hides it to the menu bar. "Start at Login" installs a user LaunchAgent
(`~/Library/LaunchAgents/com.stealthy.tokenscope.plist`).

### Signing & notarization

If these repository secrets are set, CI signs the app with a **Developer ID
Application** certificate (hardened runtime + `entitlements.plist`), submits it to
Apple for **notarization** and staples the ticket — downloads then pass Gatekeeper
with no malware warning:

| Secret | Value |
|---|---|
| `MACOS_CERT_P12` | base64 of the "Developer ID Application" certificate exported as `.p12` |
| `MACOS_CERT_PASSWORD` | password of that `.p12` |
| `APPLE_TEAM_ID` | 10-char team ID (Apple Developer → Membership) |
| `APPLE_ID` | Apple ID email used for notarization |
| `APPLE_APP_PASSWORD` | app-specific password (appleid.apple.com → Sign-In & Security) |

This requires a paid Apple Developer account. Without the secrets, CI falls back to
an **ad-hoc** signature: the app runs, but on first launch users must right-click
`TokenScope.app` → **Open** (or allow it under *System Settings → Privacy &
Security*).

To build locally on a Mac:

```bash
cd desktop
./build_macos.sh
open dist/TokenScope.app
```

This creates a venv, installs `requirements.txt` + PyInstaller, generates the
`.icns` icon and produces `dist/TokenScope.app`.

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
| `tray.py` | Windows & macOS: native window (pywebview) + tray / menu bar icon + styled popup |
| `macos.py` | legacy macOS window-only entry (superseded by `tray.py`) |
| `server.py` | stdlib HTTP server: `/` (dashboard) + `/api/local/{summary,utilization,status}` |
| `web.py` | embedded single-file HTML/JS dashboard |
| `tokenscope-tray.spec` | PyInstaller build config (Windows .exe) |
| `tokenscope-macos.spec` | PyInstaller build config (macOS .app, also built in CI) |
| `build.bat` / `run-dev.bat` | Windows build / dev-run helpers |
| `build_macos.sh` / `run-dev-macos.sh` | macOS build / dev-run helpers |

## Notes

- Port: prefers `8765`, falls back to a random free port if taken.
- It binds to `127.0.0.1` only (not reachable from other machines).
- The full React web app (stored-mode UI, manual import, thresholds) lives in
  `../frontend`; this tray exe is the standalone *local* view.
- Antigravity (Google) usage will appear here automatically once added to
  `local_sources.py`.
