from __future__ import annotations

import ctypes
import os
import sys


def main():
    sys.dont_write_bytecode = True
    from deeppick.bootstrap import hide_child_consoles
    hide_child_consoles()
    # DPI awareness must be selected before constructing any windows.
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        pass
    from deeppick.paths import Paths, application_root
    paths = Paths(application_root())
    if "--ocr-worker" in sys.argv:
        paths.configure_environment()
        from deeppick.ocr_worker import run_worker
        return run_worker(paths)
    from deeppick.win32 import single_instance, startup_folder, kernel32
    startup = startup_folder()
    mutex, first = single_instance()
    paths.configure_environment()
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtNetwork import QLocalSocket
    app = QApplication(sys.argv[:1])
    app.setApplicationName("DeepPick AI")
    app.setOrganizationName("Chunze Liu")
    app.setQuitOnLastWindowClosed(False)
    if not first:
        socket = QLocalSocket()
        socket.connectToServer("DeepPickAI-ChunzeLiu-1")
        if socket.waitForConnected(1500):
            socket.write(b"quit" if "--quit" in sys.argv else b"show")
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
        else:
            QMessageBox.information(None,"DeepPick AI","DeepPick AI 已在后台运行，请点击系统托盘图标打开。")
        kernel32.CloseHandle(mutex)
        return 0
    if "--quit" in sys.argv:
        kernel32.CloseHandle(mutex)
        return 0
    from deeppick.storage import setup_logging
    setup_logging(paths.logs)
    import logging
    from deeppick.style import STYLE, application_icon
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    icon = application_icon()
    app.setWindowIcon(icon)

    def exception_handler(kind,value,trace):
        logging.error("Unhandled application event",exc_info=(kind,value,trace))
        QMessageBox.warning(None,"DeepPick AI","操作未完成，程序仍在运行。请重试。详细信息保存在 D 盘日志中。")
    sys.excepthook = exception_handler
    from deeppick.controller import Controller
    try:
        controller = Controller(app,paths,startup,icon,"--background" in sys.argv)
    except Exception as error:
        logging.exception("Startup failed")
        QMessageBox.critical(None,"DeepPick AI 启动失败",str(error))
        return 1
    if getattr(sys, '_deeppick_runtime', False):
        # Keep Qt owners alive until the entry point finishes explicit shutdown;
        # Python module teardown must not reorder native widget destruction.
        sys._deeppick_context = (app, controller)
    try:
        return app.exec()
    finally:
        controller.ocr.stop()
        kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        ctypes.windll.user32.MessageBoxW(None,str(error),"DeepPick AI",0x10)
        raise SystemExit(1)
