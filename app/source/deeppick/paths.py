from __future__ import annotations

import os
import sys
from pathlib import Path


class Paths:
    names = ("app", "models", "config", "logs", "cache", "temp", "history", "output")

    def __init__(self, root: Path):
        self.root = root.resolve()
        if self.root.drive.upper() != "D:":
            raise RuntimeError("DeepPick AI 必须放在 D 盘，建议使用 D:\\DeepPickAI。")
        for name in self.names:
            folder = self.root / name
            # Refuse redirected directories: cleanup must never follow junctions.
            if folder.exists() and (folder.is_symlink() or folder.resolve().parent != self.root):
                raise RuntimeError(f"目录不能是指向其他位置的链接：{folder}")
            folder.mkdir(parents=True, exist_ok=True)
            setattr(self, name, folder)

    def configure_environment(self):
        folders = {
            "TEMP": self.temp, "TMP": self.temp, "TMPDIR": self.temp,
            "USERPROFILE": self.cache,
            "APPDATA": self.cache / "roaming", "LOCALAPPDATA": self.cache / "local",
            "XDG_CACHE_HOME": self.cache, "PADDLE_HOME": self.cache / "paddle",
            "PADDLEOCR_HOME": self.models, "PADDLE_PDX_CACHE_HOME": self.cache / "paddlex",
            "HF_HOME": self.cache / "huggingface", "MPLCONFIGDIR": self.cache / "matplotlib",
        }
        for key, value in folders.items():
            value.mkdir(parents=True, exist_ok=True)
            os.environ[key] = str(value)
        os.environ.update(PYTHONDONTWRITEBYTECODE="1", QT_LOGGING_RULES="qt.qpa.*=false",
                          FLAGS_use_mkldnn="0", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
        sys.dont_write_bytecode = True


def application_root():
    if getattr(sys, "frozen", False) or getattr(sys, '_deeppick_runtime', False):
        return Path(sys.executable).parent
    return Path(os.environ.get("DEEPPICK_ROOT", "D:/DeepPickAI"))
