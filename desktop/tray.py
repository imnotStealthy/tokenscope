"""TokenScope desktop app: a NATIVE window (pywebview) + system-tray icon.

The dashboard renders in its own application window (not a browser tab). Closing the
window minimizes it to the tray; "Quit" from the tray exits. Falls back to a browser
window only if pywebview is unavailable.
"""
import threading
import time

from server import get_theme, serve_background

_INSTANCE_MUTEX = None


def _icon_image():
    from icon import make_icon

    return make_icon(64)


def _acquire_single_instance():
    """Return False when another TokenScope process already owns the app mutex."""
    global _INSTANCE_MUTEX
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel32.CreateMutexW(None, False, "Local\\TokenScopeDesktopSingleInstance")
        if not handle:
            return True
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(handle)
            return False
        _INSTANCE_MUTEX = handle
    except Exception:
        pass
    return True


def _window_hwnd(window):
    import ctypes

    try:
        native = window.native              # WinForms Form on Windows
        h = getattr(native, "Handle", None)
        if h is not None:
            return int(h.ToInt64()) if hasattr(h, "ToInt64") else int(h)
    except Exception:
        pass
    try:
        return ctypes.windll.user32.FindWindowW(None, "TokenScope")
    except Exception:
        return 0


def _apply_titlebar_theme(hwnd, theme="dark"):
    """Paint the native Windows caption via DWM so it matches the dashboard theme.
    Win 10 20H1+/Win 11 only; silently no-ops elsewhere."""
    import ctypes

    if not hwnd:
        return
    try:
        dwm = ctypes.windll.dwmapi
    except Exception:
        return

    def _set(attr, value):
        val = ctypes.c_int(value)
        dwm.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), ctypes.c_uint(attr),
            ctypes.byref(val), ctypes.sizeof(val))

    is_light = theme == "light"
    values = (
        (20, 0 if is_light else 1),                  # DWMWA_USE_IMMERSIVE_DARK_MODE
        (35, 0x00FFFFFF if is_light else 0x00000000),  # DWMWA_CAPTION_COLOR (0x00BBGGRR)
        (34, 0x00FFFFFF if is_light else 0x00000000),  # DWMWA_BORDER_COLOR
        (36, 0x000B0909 if is_light else 0x00FFFFFF),  # DWMWA_TEXT_COLOR
    )
    for attr, value in values:
        try:
            _set(attr, value)
        except Exception:
            pass


def _title_loop(icon):
    import local_sources as ls

    while True:
        try:
            u = ls.read_local_utilization()
            parts = ["TokenScope"]
            for limit in (u.get("claude") or {}).get("limits", []):
                if limit.get("label") == "5h" and limit.get("used_percent") is not None:
                    parts.append(f"C 5h {round(limit['used_percent'])}%")
            cx = u.get("codex") or {}
            if cx.get("primary") and cx["primary"].get("used_percent") is not None:
                parts.append(f"X 5h {round(cx['primary']['used_percent'])}%")
            icon.title = " · ".join(parts)[:127]
        except Exception:
            pass
        time.sleep(60)


def _theme_loop(hwnd_state):
    last = None
    while True:
        hwnd = hwnd_state.get("hwnd")
        theme = get_theme()
        if hwnd and theme != last:
            _apply_titlebar_theme(hwnd, theme)
            last = theme
        time.sleep(0.5)


def _browser_fallback(httpd, url):
    import webbrowser

    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


def run():
    if not _acquire_single_instance():
        return

    httpd, port = serve_background()
    url = f"http://127.0.0.1:{port}/"

    try:
        import webview  # pywebview -> native WebView2 window on Windows
    except Exception:
        _browser_fallback(httpd, url)
        return

    # External links (e.g. the GitHub profile) open in the system browser,
    # never navigating the dashboard window away.
    try:
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        webview.settings["ALLOW_DOWNLOADS"] = False
    except Exception:
        pass

    window = webview.create_window(
        "TokenScope",
        url,
        width=1320,
        height=900,
        min_size=(900, 600),
        background_color="#000000",
    )

    state = {"quit": False}
    hwnd_state = {"hwnd": 0}
    icon = None
    try:
        import pystray

        def on_show(i, item):
            try:
                window.show()
            except Exception:
                pass

        def on_quit(i, item):
            state["quit"] = True
            try:
                window.destroy()
            except Exception:
                pass
            try:
                i.stop()
            except Exception:
                pass

        icon = pystray.Icon(
            "tokenscope",
            _icon_image(),
            "TokenScope",
            menu=pystray.Menu(
                pystray.MenuItem("Show TokenScope", on_show, default=True),
                pystray.MenuItem("Quit", on_quit),
            ),
        )
        icon.run_detached()  # tray runs in its own thread (webview needs the main thread)
        threading.Thread(target=_title_loop, args=(icon,), daemon=True).start()
    except Exception:
        icon = None

    def on_closing():
        # Minimize to tray instead of quitting (only when a tray icon exists).
        if icon is not None and not state["quit"]:
            window.hide()
            return False
        return True

    try:
        window.events.closing += on_closing
    except Exception:
        pass

    try:
        def apply_window_theme(*args):
            hwnd_state["hwnd"] = _window_hwnd(window)
            _apply_titlebar_theme(hwnd_state["hwnd"], get_theme())

        window.events.before_show += apply_window_theme
        window.events.shown += apply_window_theme
        threading.Thread(target=_theme_loop, args=(hwnd_state,), daemon=True).start()
    except Exception:
        pass

    webview.start()  # blocks on the main thread until the window is destroyed

    # window event loop ended -> full shutdown
    try:
        if icon is not None:
            icon.stop()
    except Exception:
        pass
    httpd.shutdown()


if __name__ == "__main__":
    run()
