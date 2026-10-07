"""Remove our windows from desktop composition before freezing a screen."""
import ctypes


def hide_capture_sources(windows):
    records = []
    delay = 0
    for window in windows:
        if window is None or not window.isVisible():
            continue
        delay = max(delay, 16)
        hwnd = int(window.winId())
        transition = ctypes.c_int(0)
        one = ctypes.c_int(1)
        try:
            dwm = ctypes.windll.dwmapi
            dwm.DwmGetWindowAttribute(ctypes.c_void_p(hwnd), 3, ctypes.byref(transition), 4)
            dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 3, ctypes.byref(one), 4)
            cloaked = dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 13, ctypes.byref(one), 4) == 0
            records.append((hwnd, transition.value, cloaked))
            if not cloaked:
                delay = 180
        except OSError:
            delay = 180
        window.hide()
    return records, delay


def restore_capture_sources(records):
    for hwnd, transition, cloaked in records:
        try:
            if not ctypes.windll.user32.IsWindow(ctypes.c_void_p(hwnd)):
                continue
            if cloaked:
                zero = ctypes.c_int(0)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 13, ctypes.byref(zero), 4)
            original = ctypes.c_int(transition)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 3, ctypes.byref(original), 4)
        except OSError:
            pass


def flush_desktop():
    try:
        ctypes.windll.dwmapi.DwmFlush()
    except OSError:
        pass
