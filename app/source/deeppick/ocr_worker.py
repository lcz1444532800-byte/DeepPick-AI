from __future__ import annotations

import contextlib
import json
import os
import sys
import traceback
import time
import queue
import threading
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path


def run_worker(paths):
    if sys.stdin is None or sys.stdout is None:
        # Windowed PyInstaller executables intentionally have no Python stdio.
        # QProcess supplies Windows pipe handles; attach them explicitly.
        import ctypes
        import msvcrt
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetStdHandle.argtypes = [ctypes.c_ulong]
        kernel.GetStdHandle.restype = ctypes.c_void_p
        for index, number, mode, flags in ((0,-10,"r",os.O_RDONLY),(1,-11,"w",os.O_WRONLY),(2,-12,"w",os.O_WRONLY)):
            handle = kernel.GetStdHandle(ctypes.c_ulong(number & 0xffffffff))
            if handle is None or handle == ctypes.c_void_p(-1).value:
                return 2
            descriptor = msvcrt.open_osfhandle(handle,flags)
            if descriptor != index:
                os.dup2(descriptor,index)
                os.close(descriptor)
            setattr(sys,("stdin","stdout","stderr")[index],os.fdopen(os.dup(index),mode,encoding="utf-8",buffering=1))
    sys.stdin.reconfigure(encoding="utf-8")
    # The protocol owns stdout; native library diagnostics go to a bounded D log.
    protocol = os.fdopen(os.dup(1), "w", encoding="utf-8", buffering=1)
    log = paths.logs / "ocr.log"
    if log.exists() and log.stat().st_size > 4*1024*1024:
        log.unlink()
    with log.open("a", encoding="utf-8", buffering=1) as diagnostics:
        os.dup2(diagnostics.fileno(), 1)
        os.dup2(diagnostics.fileno(), 2)
        with contextlib.redirect_stdout(diagnostics), contextlib.redirect_stderr(diagnostics):
            try:
                from .ocr_engine import PaddleEngine
                engine = PaddleEngine(paths.models)
                engine.warmup()
                protocol.write(json.dumps({"ready":True})+"\n")
            except Exception:
                traceback.print_exc()
                protocol.write(json.dumps({"error":"离线 OCR 启动失败。请检查模型与运行库是否完整。"}, ensure_ascii=False)+"\n")
                return 1
            requests = queue.Queue(maxsize=4)
            def read_requests():
                try:
                    for line in sys.stdin:
                        requests.put(line)
                finally:
                    requests.put(None)
            threading.Thread(target=read_requests,daemon=True,name='OCR requests').start()
            while True:
                try:
                    line = requests.get(timeout=1)
                except queue.Empty:
                    try:
                        engine.release_scratch()
                    except Exception:
                        traceback.print_exc()
                    line = requests.get()
                if line is None:
                    break
                request = {}
                image = None
                try:
                    request = json.loads(line)
                    started = time.perf_counter()
                    name = request['shared_memory']
                    identity = request['id']
                    if len(identity)!=32 or any(c not in '0123456789abcdef' for c in identity) or name!='DeepPickAI_'+identity:
                        raise ValueError('invalid shared image name')
                    width,height,stride = (int(request[k]) for k in ('width','height','stride'))
                    if width<=0 or height<=0 or width*height>40_000_000 or stride<width*3 or stride>width*3+3:
                        raise ValueError('invalid shared image size')
                    import cv2
                    import numpy as np
                    memory = SharedMemory(name=name)
                    try:
                        if memory.size<height*stride: raise ValueError('short image')
                        rgb = np.ndarray((height,stride),dtype=np.uint8,buffer=memory.buf)[:,:width*3].reshape(height,width,3)
                        image = cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
                        del rgb
                    finally:
                        memory.close()
                    blocks = engine.recognize_array(image)
                    protocol.write(json.dumps({"id":identity, "blocks":blocks,
                                               "timings":{"worker_seconds":time.perf_counter()-started}}, ensure_ascii=False)+"\n")
                except Exception:
                    traceback.print_exc()
                    protocol.write(json.dumps({"id":request.get("id", ""),
                                                "error":"本次 OCR 失败，请重新截图或缩小识别区域。"}, ensure_ascii=False)+"\n")
                finally:
                    image = None
    return 0
