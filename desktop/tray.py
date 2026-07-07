"""TokenScope desktop app: a NATIVE window (pywebview) + system-tray icon.

The dashboard renders in its own application window (not a browser tab). Closing the
window minimizes it to the tray; "Quit" from the tray exits. Falls back to a browser
window only if pywebview is unavailable.
"""
import os
import sys
import threading
import time

from server import get_theme, serve_background

_INSTANCE_MUTEX = None

# ----- "Start with Windows" (HKCU Run key, launches minimized to tray) -----
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "TokenScope"


def _startup_command():
    """Command Windows runs at login: the exe (frozen) or python + this script, minimized."""
    exe = sys.executable
    if getattr(sys, "frozen", False):
        return f'"{exe}" --minimized'
    return f'"{exe}" "{os.path.abspath(__file__)}" --minimized'


def _startup_enabled():
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            val, _ = winreg.QueryValueEx(k, _APP_NAME)
            return bool(val)
    except (OSError, ImportError):
        return False


def _set_startup(enable):
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enable:
                winreg.SetValueEx(k, _APP_NAME, 0, winreg.REG_SZ, _startup_command())
            else:
                try:
                    winreg.DeleteValue(k, _APP_NAME)
                except OSError:
                    pass
    except (OSError, ImportError):
        pass


def _mac_startup_plist():
    return os.path.expanduser("~/Library/LaunchAgents/com.stealthy.tokenscope.plist")


def _mac_startup_command():
    if getattr(sys, "frozen", False):
        return [sys.executable, "--minimized"]
    return [sys.executable, os.path.abspath(__file__), "--minimized"]


def _mac_startup_enabled():
    import plistlib

    try:
        with open(_mac_startup_plist(), "rb") as f:
            data = plistlib.load(f)
        return data.get("ProgramArguments") == _mac_startup_command()
    except (OSError, ValueError, TypeError):
        return False


def _set_mac_startup(enable):
    import plistlib

    path = _mac_startup_plist()
    if not enable:
        try:
            os.remove(path)
        except OSError:
            pass
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {
        "Label": "com.stealthy.tokenscope",
        "ProgramArguments": _mac_startup_command(),
        "RunAtLoad": True,
        "KeepAlive": False,
    }
    with open(path, "wb") as f:
        plistlib.dump(data, f)


def _icon_image():
    from icon import make_icon

    return make_icon(64)


def _mac_status_icon_path():
    import os
    import tempfile

    from PIL import Image, ImageDraw

    path = os.path.join(tempfile.gettempdir(), "tokenscope_status_template.png")
    size = 36
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bars = [(8, 20, 12, 28), (14, 15, 18, 28), (20, 10, 24, 28), (26, 6, 30, 28)]
    for rect in bars:
        d.rounded_rectangle(rect, radius=1, fill=(0, 0, 0, 255))
    img.save(path)
    return path


class Win32Tray:
    """Custom system-tray icon (Shell_NotifyIcon) with NO native menu.

    pystray draws a native Windows context menu on right-click and gives no hook for a
    fully custom one. Owning the icon ourselves lets both mouse buttons open the styled
    HTML popup instead — Windows never renders a menu. Runs its own message loop thread.
    """

    _CALLBACK = 0x8000 + 1  # WM_APP + 1

    def __init__(self, image, tip, on_left, on_right):
        self._image = image
        self._tip = (tip or "")[:127]
        self._on_left = on_left
        self._on_right = on_right
        self._hwnd = 0
        self._nid = None
        self._u = None
        self._shell = None
        self._wndproc_ref = None  # keep the WNDPROC callback alive

    @property
    def title(self):
        return self._tip

    @title.setter
    def title(self, value):
        self._tip = (value or "")[:127]
        self._update_tip()

    def run_detached(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _hicon(self):
        import ctypes
        import os
        import tempfile
        from ctypes import wintypes

        try:
            path = os.path.join(tempfile.gettempdir(), "tokenscope_tray.ico")
            self._image.save(path, format="ICO", sizes=[(16, 16), (32, 32), (64, 64)])
            u = ctypes.windll.user32
            u.LoadImageW.restype = wintypes.HANDLE
            u.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                                     ctypes.c_int, ctypes.c_int, wintypes.UINT]
            IMAGE_ICON, LR_LOADFROMFILE, LR_DEFAULTSIZE = 1, 0x00000010, 0x00000040
            return u.LoadImageW(None, path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
        except Exception:
            return 0

    def _run(self):
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32
        shell = ctypes.windll.shell32
        kernel = ctypes.windll.kernel32
        self._u, self._shell = u, shell

        LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
        WNDPROCTYPE = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                                         wintypes.WPARAM, LRESULT)

        class WNDCLASS(ctypes.Structure):
            _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROCTYPE),
                        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                        ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

        class NOTIFYICONDATA(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                        ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
                        ("uCallbackMessage", wintypes.UINT), ("hIcon", wintypes.HICON),
                        ("szTip", wintypes.WCHAR * 128), ("dwState", wintypes.DWORD),
                        ("dwStateMask", wintypes.DWORD), ("szInfo", wintypes.WCHAR * 256),
                        ("uVersion", wintypes.UINT), ("szInfoTitle", wintypes.WCHAR * 64),
                        ("dwInfoFlags", wintypes.DWORD), ("guidItem", ctypes.c_byte * 16),
                        ("hBalloonIcon", wintypes.HICON)]

        WM_DESTROY = 0x0002
        # Broadcast sent by the shell when the taskbar is (re)created — e.g. explorer.exe
        # restarts. Our icon is gone at that point and must be re-added or it vanishes.
        WM_TASKBARCREATED = u.RegisterWindowMessageW("TaskbarCreated")
        # Events that should open the popup. Win11's tray delivers right-click as
        # WM_CONTEXTMENU (not WM_RBUTTONUP), so we listen for both; left covers the rest.
        WM_LBUTTONUP, WM_RBUTTONUP, WM_LBUTTONDBLCLK = 0x0202, 0x0205, 0x0203
        WM_CONTEXTMENU, NIN_SELECT, NIN_KEYSELECT = 0x007B, 0x0400, 0x0401
        LEFT = {WM_LBUTTONUP, WM_LBUTTONDBLCLK, NIN_SELECT, NIN_KEYSELECT}
        RIGHT = {WM_RBUTTONUP, WM_CONTEXTMENU}

        def wndproc(hwnd, msg, wparam, lparam):
            if msg == self._CALLBACK:
                event = lparam & 0xFFFF
                try:
                    if event in LEFT:
                        self._on_left()
                    elif event in RIGHT:
                        self._on_right()
                except Exception:
                    pass
                return 0
            if msg == WM_TASKBARCREATED and self._nid is not None:
                try:
                    shell.Shell_NotifyIconW(0, ctypes.byref(self._nid))  # NIM_ADD again
                except Exception:
                    pass
                return 0
            if msg == WM_DESTROY:
                u.PostQuitMessage(0)
                return 0
            return u.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc_ref = WNDPROCTYPE(wndproc)
        u.DefWindowProcW.restype = LRESULT
        u.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, LRESULT]
        u.CreateWindowExW.restype = wintypes.HWND
        u.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                      wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                      wintypes.HINSTANCE, wintypes.LPVOID]
        u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, LRESULT]
        kernel.GetModuleHandleW.restype = wintypes.HMODULE

        hinst = kernel.GetModuleHandleW(None)
        wc = WNDCLASS()
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinst
        wc.lpszClassName = "TokenScopeTrayWnd"
        u.RegisterClassW(ctypes.byref(wc))
        self._hwnd = u.CreateWindowExW(0, "TokenScopeTrayWnd", "TokenScope", 0,
                                       0, 0, 0, 0, None, None, hinst, None)

        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = 0x01 | 0x02 | 0x04  # NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = self._CALLBACK
        nid.hIcon = self._hicon()
        nid.szTip = self._tip
        self._nid = nid
        shell.Shell_NotifyIconW(0, ctypes.byref(nid))  # NIM_ADD

        msg = wintypes.MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            u.TranslateMessage(ctypes.byref(msg))
            u.DispatchMessageW(ctypes.byref(msg))

    def set_icon(self, image):
        """Swap the tray icon at runtime (quota badge)."""
        import ctypes

        self._image = image
        if self._nid is None or self._shell is None:
            return
        try:
            h = self._hicon()
            if h:
                self._nid.hIcon = h
                self._shell.Shell_NotifyIconW(1, ctypes.byref(self._nid))  # NIM_MODIFY
        except Exception:
            pass

    def notify(self, title, msg):
        """Show a Windows balloon/toast notification from the tray icon."""
        import ctypes

        if self._nid is None or self._shell is None:
            return
        try:
            NIF_INFO = 0x10
            self._nid.uFlags |= NIF_INFO
            self._nid.szInfoTitle = (title or "")[:63]
            self._nid.szInfo = (msg or "")[:255]
            self._nid.dwInfoFlags = 1  # NIIF_INFO
            self._shell.Shell_NotifyIconW(1, ctypes.byref(self._nid))  # NIM_MODIFY
            self._nid.uFlags &= ~NIF_INFO
        except Exception:
            pass

    def _update_tip(self):
        import ctypes

        if self._nid is None or self._shell is None:
            return
        try:
            self._nid.szTip = self._tip
            self._shell.Shell_NotifyIconW(1, ctypes.byref(self._nid))  # NIM_MODIFY
        except Exception:
            pass

    def stop(self):
        import ctypes

        try:
            if self._nid is not None and self._shell is not None:
                self._shell.Shell_NotifyIconW(2, ctypes.byref(self._nid))  # NIM_DELETE
        except Exception:
            pass
        try:
            if self._hwnd and self._u is not None:
                self._u.PostMessageW(self._hwnd, 0x0002, 0, 0)  # WM_DESTROY -> ends loop
        except Exception:
            pass


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


def _acquire_file_instance_lock():
    """Return False when another portable TokenScope process owns the lock file."""
    global _INSTANCE_MUTEX
    try:
        import fcntl

        if sys.platform == "darwin":
            state_dir = os.path.expanduser("~/Library/Application Support/TokenScope")
        else:
            state_dir = os.path.join(os.path.expanduser("~/.local/state"), "tokenscope")
        os.makedirs(state_dir, exist_ok=True)
        lock_file = open(os.path.join(state_dir, "tokenscope.lock"), "w", encoding="utf-8")
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _INSTANCE_MUTEX = lock_file
    except BlockingIOError:
        return False
    except Exception:
        return True
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


def _native_hwnd(window):
    """HWND of a pywebview window via its native handle only (no title fallback)."""
    import ctypes  # noqa: F401

    try:
        h = getattr(window.native, "Handle", None)
        if h is not None:
            return int(h.ToInt64()) if hasattr(h, "ToInt64") else int(h)
    except Exception:
        pass
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
    """Refresh the tray tooltip, fire quota alerts, and badge the icon by pressure.

    Alerts use hysteresis (alert at >=90% used / <=10% left, re-arm below 85% / above 15%)
    so a window hovering at the threshold does not spam notifications."""
    import local_sources as ls
    from icon import make_icon

    alerted = set()
    badge_last = "unset"
    while True:
        try:
            u = ls.read_local_utilization()
            parts = ["TokenScope"]
            worst = 0.0
            for limit in (u.get("claude") or {}).get("limits", []):
                p = limit.get("used_percent")
                if p is None:
                    continue
                lbl = limit.get("label") or "?"
                if lbl == "5h":
                    parts.append(f"C 5h {round(p)}%")
                worst = max(worst, p)
                key = f"claude:{lbl}"
                if p >= 90 and key not in alerted:
                    alerted.add(key)
                    icon.notify("TokenScope — Claude", f"'{lbl}' window at {round(p)}% used")
                elif p < 85:
                    alerted.discard(key)
            cx = u.get("codex") or {}
            for key, lbl in (("primary", "5h"), ("secondary", "weekly"),
                             ("spark_primary", "Spark 5h"), ("spark_secondary", "Spark weekly")):
                lim = cx.get(key)
                if not lim or lim.get("used_percent") is None:
                    continue
                used = lim["used_percent"]
                rem = 100 - used
                if key == "primary":
                    parts.append(f"X 5h {round(used)}%")
                worst = max(worst, used)
                akey = f"codex:{key}"
                if rem <= 10 and akey not in alerted:
                    alerted.add(akey)
                    icon.notify("TokenScope — Codex", f"'{lbl}' window: {round(rem)}% left")
                elif rem > 15:
                    alerted.discard(akey)
            icon.title = " · ".join(parts)[:127]
            badge = "bad" if worst >= 90 else "warn" if worst >= 75 else None
            if badge != badge_last:
                badge_last = badge
                icon.set_icon(make_icon(64, badge=badge))
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
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        httpd.shutdown()


def _install_macos_status_item(window, popup, state, popup_state, icon_box):
    try:
        import AppKit
        from AppKit import (
            NSImage,
            NSStatusBar,
            NSVariableStatusItemLength,
            NSApp,
            NSScreen,
        )
        from Foundation import NSObject
        from PyObjCTools import AppHelper
    except Exception:
        return

    class MacStatusBarController(NSObject):
        """Status-item click handler. Runs on the AppKit main thread, so it drives the
        popup through its native NSWindow directly — pywebview's evaluate_js/show block
        on the main runloop and would deadlock if called from here."""

        def _popup_frame(self):
            """Popup NSRect (Cocoa coords, origin bottom-left) right-aligned under the
            status item, clamped to that screen's visible frame."""
            width = float(popup_state.get("w") or 304)
            height = float(popup_state.get("h") or 470)
            button_window = icon_box["icon"]._item.button().window()
            bf = button_window.frame()
            screen = button_window.screen() or NSScreen.mainScreen()
            vf = screen.visibleFrame()
            x = bf.origin.x + bf.size.width - width
            x = max(vf.origin.x + 4, min(x, vf.origin.x + vf.size.width - width - 4))
            top = bf.origin.y - 6  # just below the menu bar
            bottom = max(vf.origin.y + 4, top - height)
            return AppKit.NSMakeRect(x, bottom, width, height)

        def showDashboard_(self, sender):
            self.dismiss_(None)
            try:
                window.show()  # thread-safe: orders front + activates via callAfter
            except Exception:
                pass

        def togglePopup_(self, sender):
            try:
                if popup_state.get("shown"):
                    self.dismiss_(None)
                    return
                # Clicking the icon while the popup is open first blurs it (JS dismiss),
                # then this action fires — do not instantly reopen it.
                if time.monotonic() - popup_state.get("dismissed_at", 0.0) < 0.4:
                    return
                native = popup.native  # NSWindow — safe, we are on the main thread
                native.setFrame_display_(self._popup_frame(), True)
                native.makeKeyAndOrderFront_(None)
                native.invalidateShadow()  # recompute from the rounded card's shape
                NSApp.activateIgnoringOtherApps_(True)
                popup_state["shown"] = True
                # refresh the popup data; evaluate_js blocks, so never from this thread
                threading.Thread(
                    target=lambda: popup.evaluate_js("window.refreshTray&&refreshTray()"),
                    daemon=True,
                ).start()
            except Exception:
                pass

        def dismiss_(self, sender):
            if popup_state.get("shown"):
                popup_state["dismissed_at"] = time.monotonic()
            popup_state["shown"] = False
            try:
                AppHelper.callAfter(popup.native.orderOut_, None)
            except Exception:
                pass

        def quitApp_(self, sender):
            state["quit"] = True
            self.dismiss_(None)
            try:
                if icon_box.get("icon") is not None:
                    icon_box["icon"].stop()
            except Exception:
                pass
            for w in (popup, window):  # destroy BOTH windows so webview.start() returns
                try:
                    w.destroy()
                except Exception:
                    pass

    class MacStatusBar:
        def __init__(self):
            self._controller = MacStatusBarController.alloc().init()
            self._item = NSStatusBar.systemStatusBar().statusItemWithLength_(
                NSVariableStatusItemLength
            )
            self._title = "TokenScope"
            image = NSImage.alloc().initWithContentsOfFile_(_mac_status_icon_path())
            if image is not None:
                image.setTemplate_(True)
                button = self._item.button()
                button.setImage_(image)
                button.setToolTip_(self._title)
                button.setTarget_(self._controller)
                button.setAction_("togglePopup:")
                try:
                    # both mouse buttons open the popup, matching the Windows tray
                    button.sendActionOn_(
                        AppKit.NSEventMaskLeftMouseUp | AppKit.NSEventMaskRightMouseUp
                    )
                except Exception:
                    pass

        @property
        def title(self):
            return self._title

        @title.setter
        def title(self, value):
            self._title = (value or "TokenScope")[:127]

            def apply_title():
                try:
                    self._item.button().setToolTip_(self._title)
                except Exception:
                    pass

            AppHelper.callAfter(apply_title)

        def set_icon(self, image):
            pass

        def notify(self, title, msg):
            pass

        def stop(self):
            def remove_item():
                try:
                    NSStatusBar.systemStatusBar().removeStatusItem_(self._item)
                except Exception:
                    pass

            AppHelper.callAfter(remove_item)

    def create_item():
        try:
            # Drop the titled mask: macOS paints a light 1px edge highlight around
            # titled windows (even transparent ones). Borderless removes it; the
            # shadow is re-enabled so it follows the rounded card's alpha shape.
            n = popup.native
            n.setStyleMask_(AppKit.NSWindowStyleMaskBorderless)
            n.setHasShadow_(True)
        except Exception:
            pass
        icon_box["icon"] = MacStatusBar()
        threading.Thread(target=_title_loop, args=(icon_box["icon"],), daemon=True).start()

    AppHelper.callAfter(create_item)


def _run_windows():
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
        webview.settings["ALLOW_DOWNLOADS"] = True  # needed for the CSV/JSON export buttons
    except Exception:
        pass

    minimized = "--minimized" in sys.argv  # started by the "Start with Windows" entry
    window = webview.create_window(
        "TokenScope",
        url,
        width=1320,
        height=900,
        min_size=(900, 600),
        background_color="#000000",
        hidden=minimized,
    )

    state = {"quit": False}
    hwnd_state = {"hwnd": 0}
    popup_state = {"w": 304, "h": 470, "hwnd": 0, "shown": False, "had_focus": False}
    icon_box = {"icon": None}

    def _quit_app():
        state["quit"] = True
        try:
            _hide_popup()
        except Exception:
            pass
        try:
            popup.destroy()
        except Exception:
            pass
        try:
            window.destroy()
        except Exception:
            pass
        try:
            if icon_box["icon"] is not None:
                icon_box["icon"].stop()
        except Exception:
            pass

    def _user32():
        """user32 with argtypes set so 64-bit HWNDs aren't truncated. Returns (u, wintypes)."""
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32
        u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        u.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetWindowLongW.restype = ctypes.c_long
        u.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
        u.FindWindowW.restype = wintypes.HWND
        return u, wintypes

    def _set_toolwindow(hwnd):
        """Keep the popup out of the taskbar / alt-tab (WS_EX_TOOLWINDOW)."""
        try:
            u, _ = _user32()
            ex = u.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            u.SetWindowLongW(hwnd, -20, ex | 0x00000080)  # WS_EX_TOOLWINDOW
        except Exception:
            pass

    def _popup_rect():
        """(x, y, w, h) in PHYSICAL px: popup placed above-left of the cursor, clamped to the
        work area of the monitor UNDER the cursor, with size DPI-scaled for that monitor.
        popup_state w/h are logical (CSS) px from the page; SetWindowPos needs physical px."""
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32
        u.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
        u.MonitorFromPoint.restype = wintypes.HANDLE

        class MONITORINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

        u.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MONITORINFO)]
        pt = wintypes.POINT()
        u.GetCursorPos(ctypes.byref(pt))
        hmon = u.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if u.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            wa = mi.rcWork
        else:
            wa = wintypes.RECT(0, 0, u.GetSystemMetrics(0), u.GetSystemMetrics(1))
        scale = 1.0
        try:
            dpi_x, dpi_y = wintypes.UINT(), wintypes.UINT()
            shcore = ctypes.windll.shcore
            shcore.GetDpiForMonitor.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                ctypes.POINTER(wintypes.UINT),
                                                ctypes.POINTER(wintypes.UINT)]
            shcore.GetDpiForMonitor(hmon, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))  # MDT_EFFECTIVE
            if dpi_x.value:
                scale = dpi_x.value / 96.0
        except Exception:
            pass
        w = max(1, round(popup_state["w"] * scale))
        h = max(1, round(popup_state["h"] * scale))
        x = min(max(wa.left, pt.x - w), max(wa.left, wa.right - w))
        y = min(max(wa.top, pt.y - h), max(wa.top, wa.bottom - h))
        return x, y, w, h

    def _force_foreground(hwnd):
        """Reliably give a window focus from a background thread (AttachThreadInput trick),
        so clicking elsewhere fires its JS blur and the popup self-dismisses."""
        import ctypes
        from ctypes import wintypes

        try:
            u = ctypes.windll.user32
            for fn in ("SetForegroundWindow", "BringWindowToTop", "SetActiveWindow",
                       "SetFocus", "IsWindow"):
                getattr(u, fn).argtypes = [wintypes.HWND]
            u.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
            u.GetWindowThreadProcessId.restype = wintypes.DWORD
            u.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
            u.GetForegroundWindow.restype = wintypes.HWND
            fg = u.GetForegroundWindow()
            fg_thread = u.GetWindowThreadProcessId(fg, None) if fg else 0
            cur_thread = ctypes.windll.kernel32.GetCurrentThreadId()
            attached = False
            if fg_thread and fg_thread != cur_thread:
                attached = bool(u.AttachThreadInput(cur_thread, fg_thread, True))
            u.BringWindowToTop(hwnd)
            u.SetForegroundWindow(hwnd)
            u.SetActiveWindow(hwnd)
            u.SetFocus(hwnd)
            if attached:
                u.AttachThreadInput(cur_thread, fg_thread, False)
        except Exception:
            pass

    def _hide_popup():
        # Win32 SW_HIDE works from any thread; pywebview.hide() from the tray thread no-ops.
        popup_state["shown"] = False
        popup_state["had_focus"] = False
        try:
            u, _ = _user32()
            u.ShowWindow(popup_state["hwnd"] or _native_hwnd(popup), 0)
        except Exception:
            pass

    def _dismiss_watcher():
        """Hide the popup once it has held the foreground and then lost it (clicked away).
        Win32 polling — WebView2 does not reliably fire a JS blur event for the dismiss."""
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32
        u.GetForegroundWindow.restype = wintypes.HWND
        while True:
            time.sleep(0.12)
            try:
                if not popup_state.get("shown"):
                    continue
                ph = popup_state.get("hwnd") or 0
                fg = u.GetForegroundWindow() or 0
                if ph and int(fg) == int(ph):
                    popup_state["had_focus"] = True
                elif popup_state.get("had_focus"):
                    _hide_popup()  # had focus, now lost it -> dismiss
            except Exception:
                pass

    threading.Thread(target=_dismiss_watcher, daemon=True).start()

    class TrayApi:
        """Callbacks the frameless /tray popup invokes via window.pywebview.api.*"""

        def show_dashboard(self):
            _hide_popup()
            try:
                window.show()
            except Exception:
                pass
            try:
                import ctypes
                from ctypes import wintypes

                u = ctypes.windll.user32
                u.SetForegroundWindow.argtypes = [wintypes.HWND]
                u.SetForegroundWindow(_window_hwnd(window))
            except Exception:
                pass

        def quit_app(self):
            _hide_popup()
            _quit_app()

        def dismiss(self):
            _hide_popup()

        def startup_enabled(self):
            return bool(_startup_enabled())

        def toggle_startup(self):
            _set_startup(not _startup_enabled())
            return bool(_startup_enabled())

        def resize(self, w, h):
            try:
                popup_state["w"], popup_state["h"] = int(w), int(h)
                popup.resize(int(w), int(h))
            except Exception:
                pass

    # The popup is a frameless, always-on-top window holding the styled menu. It is
    # created off-screen and hidden once loaded, so WebView2 fully initializes (and the
    # content paints) before the first real show — otherwise it appears blank.
    popup = webview.create_window(
        "TokenScope Menu",
        url + "tray",
        x=-4000, y=-4000,
        width=popup_state["w"],
        height=popup_state["h"],
        frameless=True,
        easy_drag=False,
        on_top=True,
        background_color="#0A0A0A",
        hidden=False,  # off-screen, not hidden, so WebView2 navigates + paints before first show
        js_api=TrayApi(),
    )
    popup_loaded = {"done": False}

    def _hide_popup_once():
        # Once the off-screen popup has painted, mark it tool-window and tuck it away (Win32).
        if popup_loaded["done"]:
            return
        popup_loaded["done"] = True
        hwnd = _native_hwnd(popup)
        if hwnd:
            popup_state["hwnd"] = hwnd
            _set_toolwindow(hwnd)
        _hide_popup()

    try:
        popup.events.loaded += _hide_popup_once
    except Exception:
        pass

    # Fallback: hide the off-screen popup shortly after the GUI loop starts, in case the
    # 'loaded' event never fires on this backend.
    threading.Thread(
        target=lambda: (time.sleep(2.5), _hide_popup_once()), daemon=True
    ).start()

    def open_popup(icon=None, item=None):
        """Position the popup at the cursor and show it via Win32 (works from the tray thread)."""
        import ctypes

        try:
            u, wintypes = _user32()
            hwnd = _native_hwnd(popup) or u.FindWindowW(None, "TokenScope Menu")
            if not hwnd:
                return
            popup_state["hwnd"] = hwnd
            _set_toolwindow(hwnd)
            x, y, w, h = _popup_rect()  # DPI- and multi-monitor-correct placement
            HWND_TOPMOST, SWP_SHOWWINDOW = -1, 0x0040
            u.SetWindowPos(hwnd, wintypes.HWND(HWND_TOPMOST), x, y, w, h, SWP_SHOWWINDOW)
            popup_state["had_focus"] = False
            popup_state["shown"] = True
            _force_foreground(hwnd)  # take focus so the watcher can detect click-away
            try:
                popup.evaluate_js("window.refreshTray&&refreshTray()")
            except Exception:
                pass
        except Exception:
            pass

    icon = None
    try:
        # Both mouse buttons open the styled popup — Windows never draws a native menu.
        icon = Win32Tray(_icon_image(), "TokenScope", on_left=open_popup, on_right=open_popup)
        icon_box["icon"] = icon
        icon.run_detached()  # tray runs in its own message-loop thread (webview needs the main thread)
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


def _run_macos():
    if not _acquire_file_instance_lock():
        return

    httpd, port = serve_background()
    url = f"http://127.0.0.1:{port}/"

    try:
        import webview
    except Exception:
        _browser_fallback(httpd, url)
        return

    try:
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
        webview.settings["ALLOW_DOWNLOADS"] = True
    except Exception:
        pass

    minimized = "--minimized" in sys.argv
    window = webview.create_window(
        "TokenScope",
        url,
        width=1320,
        height=900,
        min_size=(900, 600),
        background_color="#000000",
        hidden=minimized,
    )
    state = {"quit": False}
    icon_box = {"icon": None}
    popup_state = {"w": 304, "h": 470, "shown": False}

    class MacTrayApi:
        def show_dashboard(self):
            try:
                if icon_box["icon"] is not None:
                    icon_box["icon"]._controller.showDashboard_(None)
            except Exception:
                pass

        def quit_app(self):
            try:
                if icon_box["icon"] is not None:
                    icon_box["icon"]._controller.quitApp_(None)
            except Exception:
                state["quit"] = True
                try:
                    window.destroy()
                except Exception:
                    pass

        def dismiss(self):
            try:
                if icon_box["icon"] is not None:
                    icon_box["icon"]._controller.dismiss_(None)
            except Exception:
                popup_state["shown"] = False
                try:
                    popup.hide()
                except Exception:
                    pass

        def startup_label(self):
            return "Start at Login"

        def startup_enabled(self):
            return bool(_mac_startup_enabled())

        def toggle_startup(self):
            _set_mac_startup(not _mac_startup_enabled())
            return bool(_mac_startup_enabled())

        def resize(self, w, h):
            try:
                popup_state["w"], popup_state["h"] = int(w), int(h)
                popup.resize(int(w), int(h))
            except Exception:
                pass

    # NOTE: unlike Windows, do NOT create this off-screen (x=-4000): moving a window
    # fully off-screen makes window.screen() None and crashes pywebview's cocoa init.
    # hidden=True is enough on macOS — WKWebView still loads /tray while hidden.
    popup = webview.create_window(
        "TokenScope Menu",
        url + "tray",
        width=popup_state["w"],
        height=popup_state["h"],
        frameless=True,
        easy_drag=False,
        on_top=True,
        background_color="#0A0A0A",
        transparent=True,  # only the rounded HTML card shows — no native window edge
        hidden=True,
        js_api=MacTrayApi(),
    )

    def on_closing():
        if not state["quit"]:
            window.hide()
            return False
        return True

    try:
        window.events.closing += on_closing
    except Exception:
        pass

    try:
        webview.start(
            func=_install_macos_status_item,
            args=(window, popup, state, popup_state, icon_box),
        )
    finally:
        try:
            if icon_box["icon"] is not None:
                icon_box["icon"].stop()
        except Exception:
            pass
        httpd.shutdown()


def _run_portable():
    if not _acquire_file_instance_lock():
        return

    httpd, port = serve_background()
    url = f"http://127.0.0.1:{port}/"
    _browser_fallback(httpd, url)


def run():
    if sys.platform == "win32":
        _run_windows()
    elif sys.platform == "darwin":
        _run_macos()
    else:
        _run_portable()


if __name__ == "__main__":
    run()
