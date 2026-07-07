"""macOS entry point for the TokenScope desktop app.

Runs the same local server + embedded dashboard as the Windows tray app, in a
native WebKit window (pywebview / Cocoa). The Win32 tray icon, quota toasts and
custom tray popup in tray.py are Windows-only and intentionally not ported —
this is a plain windowed app. If the native window cannot start, the dashboard
opens in the default browser instead.
"""
import sys
import time
import webbrowser

from server import serve_background


def run():
    httpd, port = serve_background()
    url = f"http://127.0.0.1:{port}/"

    try:
        import webview  # pywebview -> native WKWebView window on macOS
    except Exception:
        _browser_fallback(httpd, url)
        return

    # External links (e.g. the GitHub profile) open in the system browser,
    # never navigating the dashboard window away.
    try:
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        webview.settings["ALLOW_DOWNLOADS"] = True  # CSV/JSON export buttons
    except Exception:
        pass

    webview.create_window(
        "TokenScope",
        url,
        width=1320,
        height=900,
        min_size=(900, 600),
        background_color="#000000",
    )
    try:
        webview.start()  # blocks until the window is closed
    except Exception:
        _browser_fallback(httpd, url)
        return

    httpd.shutdown()


def _browser_fallback(httpd, url):
    """No native window available: serve in the default browser until Ctrl+C."""
    print(f"TokenScope dashboard -> {url}  (Ctrl+C to stop)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    httpd.shutdown()


if __name__ == "__main__":
    sys.exit(run())
