"""Application-local startup hook for the official isolated GUI runtime."""
import os
import sys

sys.dont_write_bytecode = True
if len(sys.argv) <= 1 and (not sys.argv or sys.argv[0] not in ('-m', '-c')):
    # Complete Python initialization before Qt owns the event loop. The short
    # launcher exits; the GUI and its OCR worker are the only resident processes.
    try:
        import subprocess
        subprocess.Popen([sys.executable, '-B', '-m', 'deeppick_entry'],
                         cwd=os.path.dirname(sys.executable), close_fds=True,
                         creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as error:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(error), 'DeepPick AI', 0x10)
        os._exit(1)
    os._exit(0)
