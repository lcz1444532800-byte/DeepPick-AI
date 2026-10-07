"""DeepPick AI entry point; the signed runtime binaries remain unmodified."""
import ctypes
import os
import sys


def launch():
    sys.dont_write_bytecode = True
    sys._deeppick_runtime = True
    try:
        from pathlib import Path
        from deeppick.paths import Paths
        paths = Paths(Path(sys.executable).parent)
        import faulthandler
        crash_log = paths.logs / 'native.log'
        if crash_log.exists() and crash_log.stat().st_size > 4 * 1024 * 1024:
            with crash_log.open('wb'):
                pass
        sys._deeppick_fault_log = crash_log.open('a', encoding='utf-8')
        faulthandler.enable(file=sys._deeppick_fault_log, all_threads=True)
        from main import main
        return int(main() or 0)
    except Exception as error:
        ctypes.windll.user32.MessageBoxW(None, str(error), 'DeepPick AI', 0x10)
        return 1


if __name__ == '__main__':
    code = launch()
    import logging
    logging.shutdown()
    raise SystemExit(code)
