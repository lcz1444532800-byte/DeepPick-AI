from __future__ import annotations

import json
import logging
import os
import secrets
import shutil
import time
import uuid
from dataclasses import asdict, dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .native_windows import secure_acl
from .housekeeping import cache_budget, cleanup


@dataclass
class Settings:
    api_key: str = ""
    mode: str = "auto"
    auto_enhance: bool = True
    threshold: float = 0.82
    capture_key: str = "Ctrl+Space"
    cancel_key: str = "Esc"
    copy_key: str = "Ctrl+Return"
    history_enabled: bool = True
    start_hidden: bool = True
    autostart: bool = True
    model: str = "deepseek-flash"
    cache_limit_mb: int = 128
    schema_version: int = 2


def atomic_write(path: Path, data: bytes):
    staging = path.with_name(path.name + ".pending")
    with staging.open("wb") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    os.replace(staging, path)


class ConfigStore:
    def __init__(self, folder: Path):
        self.folder = folder
        self.path = folder / "settings.enc"
        self.keypath = folder / "vault.key"
        self.warning = ""
        self.migrated = False
        secure_acl(folder)
        if not self.keypath.exists():
            if self.path.exists():
                raise RuntimeError("The configuration encryption key is missing. Keep the config folder intact.")
            atomic_write(self.keypath, AESGCM.generate_key(256))
        secure_acl(self.keypath)
        self.cipher = AESGCM(self.keypath.read_bytes())

    def load(self):
        if not self.path.exists():
            return Settings()
        try:
            data = self.path.read_bytes()
            plain = self.cipher.decrypt(data[:12], data[12:], b"DeepPickAI-v1")
            values = json.loads(plain)
            known = Settings.__dataclass_fields__
            settings = Settings(**{k: v for k, v in values.items() if k in known})
            settings.cache_limit_mb = cache_budget(settings.cache_limit_mb)
            if values.get("schema_version", 1) < 2:
                settings.mode = "auto"
                settings.auto_enhance = True
                settings.autostart = True
                settings.schema_version = 2
                self.migrated = True
            if settings.mode not in ("local", "ai", "auto"):
                raise ValueError("invalid mode")
            if not isinstance(settings.api_key, str) or not 0.1 <= settings.threshold <= 1:
                raise ValueError("invalid settings")
            if any(not isinstance(getattr(settings,k),bool) for k in
                   ("auto_enhance","history_enabled","start_hidden","autostart")):
                raise ValueError("invalid settings flags")
            if any(not isinstance(getattr(settings,k),str) or not getattr(settings,k)
                   for k in ("capture_key","copy_key","cancel_key","model")):
                raise ValueError("invalid settings keys")
            return settings
        except Exception:
            self.warning = "Configuration could not be decrypted. Defaults were loaded; save settings to rebuild it."
            logging.warning("Encrypted configuration rejected; defaults loaded")
            return Settings()

    def save(self, settings):
        nonce = secrets.token_bytes(12)
        payload = json.dumps(asdict(settings), ensure_ascii=False).encode("utf-8")
        atomic_write(self.path, nonce + self.cipher.encrypt(nonce, payload, b"DeepPickAI-v1"))
        secure_acl(self.path)


class HistoryStore:
    def __init__(self, folder: Path):
        self.path = folder / "recent.json"

    def load(self):
        try:
            records = json.loads(self.path.read_text("utf-8"))
            return [record for record in records if isinstance(record,dict)
                    and isinstance(record.get("text"),str)][:20] if isinstance(records,list) else []
        except FileNotFoundError:
            return []
        except (ValueError, OSError):
            logging.warning("History could not be read")
            return []

    def add(self, text, blocks, source="local"):
        records = self.load()
        records.insert(0, {"id": uuid.uuid4().hex, "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                           "text": text[:200000], "source": source, "blocks": blocks[:3000]})
        self.replace(records[:20])

    def replace(self, records):
        atomic_write(self.path, json.dumps(records, ensure_ascii=False).encode("utf-8"))

    def clear(self):
        self.path.unlink(missing_ok=True)


def _safe_delete(path: Path, folder: Path):
    if path.is_symlink() or path.resolve().parent != folder.resolve():
        return
    # Junctions are deliberately skipped too.
    if path.is_dir():
        for item in path.iterdir():
            _safe_delete(item, path)
        try:
            path.rmdir()
        except OSError:
            pass
    else:
        path.unlink(missing_ok=True)


def setup_logging(folder):
    handler = RotatingFileHandler(folder / "deeppick.log", maxBytes=4*1024*1024,
                                  backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    # HTTP traces can include user content: never enable wire logging.
    logging.getLogger("httpx").setLevel(logging.WARNING)
