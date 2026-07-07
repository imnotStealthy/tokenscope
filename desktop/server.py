"""Lightweight stdlib HTTP server for the TokenScope tray app.

Serves the embedded dashboard at / and the live local endpoints under /api/local/*,
reusing backend/local_sources.py. No FastAPI, no MongoDB, no Node — so it packages
cleanly into a single PyInstaller .exe (deps: requests, pyjwt, pystray, pillow).
"""
import json
import os
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# Make backend/local_sources importable both in dev (../backend) and when bundled
# (PyInstaller includes it as a top-level module via the spec's pathex).
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(os.path.dirname(_HERE), "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import local_sources as ls  # noqa: E402
from web import INDEX_HTML, TRAY_HTML  # noqa: E402

PREFERRED_PORT = 8765
_VALID_TOOLS = ("claude_api", "codex", "antigravity")
if sys.platform == "darwin":
    _STATE_DIR = os.path.expanduser("~/Library/Application Support/TokenScope")
elif os.name == "nt":
    _STATE_DIR = os.path.join(os.getenv("LOCALAPPDATA") or _HERE, "TokenScope")
else:
    _STATE_DIR = os.path.join(os.getenv("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "TokenScope")
_THEME_FILE = os.path.join(_STATE_DIR, "theme.json")
_THEME_LOCK = threading.Lock()


def _load_theme():
    try:
        with open(_THEME_FILE, "r", encoding="utf-8") as f:
            theme = json.load(f).get("theme")
            if theme in ("dark", "light"):
                return theme
    except Exception:
        pass
    return "dark"


def _save_theme(theme):
    try:
        os.makedirs(_STATE_DIR, exist_ok=True)
        with open(_THEME_FILE, "w", encoding="utf-8") as f:
            json.dump({"theme": theme}, f)
    except Exception:
        pass


_THEME = _load_theme()


def set_theme(theme):
    global _THEME
    if theme not in ("dark", "light"):
        return _THEME
    with _THEME_LOCK:
        _THEME = theme
        _save_theme(theme)
        return _THEME


def get_theme():
    with _THEME_LOCK:
        return _THEME


class Handler(BaseHTTPRequestHandler):
    server_version = "TokenScopeTray/1.0"

    def log_message(self, *args):  # keep the tray quiet
        pass

    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        q = parse_qs(u.query)
        try:
            if path in ("/", "/index.html"):
                self._send(200, INDEX_HTML, "text/html; charset=utf-8")
            elif path == "/tray":
                self._send(200, TRAY_HTML, "text/html; charset=utf-8")
            elif path == "/api/local/status":
                self._json(ls.read_local_status())
            elif path == "/api/local/summary":
                try:
                    days = int(q.get("days", ["30"])[0])
                except ValueError:
                    days = 30
                days = max(1, min(days, 100000))  # 100000 ~ lifetime (all sessions)
                tool = q.get("tool", [None])[0]
                tool = tool if tool in _VALID_TOOLS else None
                self._json(ls.read_local_summary(days=days, tool=tool))
            elif path == "/api/local/utilization":
                self._json(ls.read_local_utilization())
            elif path == "/api/theme":
                th = q.get("theme", [None])[0]  # GET without a value just reads (tray popup)
                self._json({"theme": set_theme(th) if th else get_theme()})
            else:
                self._send(404, "not found", "text/plain; charset=utf-8")
        except Exception as e:  # never take the server down on one bad request
            self._json({"error": str(e)}, 500)


def make_server(preferred=PREFERRED_PORT):
    last = None
    for port in (preferred, 0):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            return httpd, httpd.server_address[1]
        except OSError as e:
            last = e
    raise RuntimeError(f"could not bind a local port: {last}")


def _warm_cache():
    """Pre-parse the whole history in the background so switching the range (incl. lifetime)
    is instant. Runs after a short delay to let the initial 30D paint finish first."""
    try:
        time.sleep(4)
        ls.read_local_summary(100000)  # ~lifetime: warms every session file once
    except Exception:
        pass


def serve_background(preferred=PREFERRED_PORT):
    httpd, port = make_server(preferred)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    threading.Thread(target=_warm_cache, daemon=True).start()
    return httpd, port


if __name__ == "__main__":
    httpd, port = make_server()
    url = f"http://127.0.0.1:{port}/"
    print(f"TokenScope dashboard -> {url}  (Ctrl+C to stop)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()
