from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Qt, Signal
from PySide6.QtGui import QKeySequence

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def single_instance():
    handle = kernel32.CreateMutexW(None, False, "Local\\DeepPickAI-ChunzeLiu-1")
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    return handle, ctypes.get_last_error() != 183


def hotkey_parts(text):
    seq = QKeySequence(text)
    if seq.isEmpty() or seq.count() != 1:
        raise ValueError("截图快捷键必须是一个组合键。")
    combination = seq[0]
    modifiers = combination.keyboardModifiers()
    key = int(combination.key())
    mods = 0x4000
    for qt_mod, native in ((Qt.KeyboardModifier.ControlModifier, 2),
                            (Qt.KeyboardModifier.AltModifier, 1),
                            (Qt.KeyboardModifier.ShiftModifier, 4),
                            (Qt.KeyboardModifier.MetaModifier, 8)):
        if modifiers & qt_mod:
            mods |= native
    if mods == 0x4000:
        raise ValueError("截图快捷键需包含 Ctrl、Alt、Shift 或 Win。")
    special = {int(Qt.Key.Key_Space): 0x20, int(Qt.Key.Key_Return): 0x0D,
               int(Qt.Key.Key_Enter): 0x0D, int(Qt.Key.Key_Escape): 0x1B,
               int(Qt.Key.Key_Tab): 0x09, int(Qt.Key.Key_Backspace): 0x08}
    if int(Qt.Key.Key_F1) <= key <= int(Qt.Key.Key_F24):
        if key == int(Qt.Key.Key_F12):
            raise ValueError("F12 是 Windows 保留键，请选择其他截图快捷键。")
        vk = 0x70 + key-int(Qt.Key.Key_F1)
    elif 0x30 <= key <= 0x5A:
        vk = key
    elif key in special:
        vk = special[key]
    else:
        raise ValueError("截图快捷键支持字母、数字、F1–F24、空格和回车。")
    return mods, vk


class _EventFilter(QAbstractNativeEventFilter):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam == self.owner.active_id:
            self.owner.activated.emit()
            return True, 0
        return False, 0


class GlobalHotkey(QObject):
    activated = Signal()

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.active_id = 0
        self.sequence = ""
        self.filter = _EventFilter(self)
        app.installNativeEventFilter(self.filter)

    def register(self, text):
        if text == self.sequence and self.active_id:
            return
        mods, vk = hotkey_parts(text)
        next_id = 0xAD01 if self.active_id != 0xAD01 else 0xAD02
        if not user32.RegisterHotKey(None, next_id, mods, vk):
            if ctypes.get_last_error() == 5:
                raise RuntimeError("Windows 拒绝注册全局快捷键。请在普通桌面会话中启动本程序。")
            raise RuntimeError(f"{text} 已被其他程序占用，请在设置中更换截图快捷键。")
        old = self.active_id
        self.active_id, self.sequence = next_id, text
        if old:
            user32.UnregisterHotKey(None, old)

    def close(self):
        if self.active_id:
            user32.UnregisterHotKey(None, self.active_id)
            self.active_id = 0
        self.app.removeNativeEventFilter(self.filter)


def write_shortcut(target: Path, path: Path, arguments=""):
    from .native_windows import write_shortcut as native_write
    native_write(target,path,arguments)


def startup_folder():
    # Query the actual registered Windows folder, before applying cache env vars.
    import winreg
    key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
        folder, _ = winreg.QueryValueEx(handle, "Startup")
    import os
    return Path(os.path.expandvars(folder))


def apply_autostart(enabled, executable, folder):
    # The user explicitly permits a shortcut in Windows' registered Startup
    # folder, including C:. No registry Run entries or system installs.
    if folder.drive.upper() not in ("C:","D:"):
        raise RuntimeError("Windows 启动文件夹路径无效。")
    link = folder / "DeepPick AI.lnk"
    if enabled:
        folder.mkdir(parents=True, exist_ok=True)
        import sys
        arguments = '-B -m deeppick_entry --background' if getattr(sys, '_deeppick_runtime', False) else '--background'
        write_shortcut(executable, link, arguments)
    else:
        link.unlink(missing_ok=True)
