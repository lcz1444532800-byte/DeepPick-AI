"""Bounded runtime data cleanup; never traverse reparse points or maintenance data."""
from __future__ import annotations

import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path

MIB = 1024 * 1024
LOG_LIMIT = 50 * MIB
DEFAULT_CACHE_MB = 128


@dataclass
class Usage:
    cache: int = 0
    temp: int = 0
    logs: int = 0
    removed: int = 0
    blocked: int = 0

    @property
    def runtime(self):
        return self.cache + self.temp


def cache_budget(value):
    return value if type(value) is int and 32 <= value <= 4096 else DEFAULT_CACHE_MB


def _files(folder: Path, cancel):
    # Validate the root too: a directory could have been redirected after launch.
    if not _safe_root(folder):
        return
    stack = [folder]
    while stack and not cancel():
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if cancel():
                        return
                    try:
                        info = entry.stat(follow_symlinks=False)
                        if getattr(info, 'st_file_attributes', 0) & 0x400 or entry.is_symlink():
                            continue
                        path = Path(entry.path)
                        if not current.resolve().is_relative_to(folder.absolute()) or path.resolve().parent != current.absolute():
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            stack.append(path)
                        elif stat.S_ISREG(info.st_mode):
                            yield path, info.st_size, info.st_mtime
                    except OSError:
                        continue
        except OSError:
            continue


def cleanup(paths, limit_mb=DEFAULT_CACHE_MB, *, startup=False, clear_all=False, cancel=None):
    cancel = cancel or (lambda: False)
    usage = Usage()
    now = time.time()
    files = []
    for kind in ('cache', 'temp', 'logs'):
        folder = getattr(paths, kind)
        for path, size, modified in _files(folder, cancel):
            # Logs stay available until their separate limit is exceeded.
            expired = (kind == 'cache' and modified < now - 7 * 86400 or
                       kind == 'temp' and (startup or modified < now - 3600))
            if kind != 'logs' and (clear_all or expired):
                if _remove(path, folder, cancel):
                    usage.removed += size
                    continue
                usage.blocked += 1
            setattr(usage, kind, getattr(usage, kind) + size)
            files.append((modified, path, size, kind))
    for modified, path, size, kind in sorted(files):
        if cancel():
            break
        over = usage.logs > LOG_LIMIT if kind == 'logs' else usage.runtime > cache_budget(limit_mb) * MIB
        if not over:
            continue
        # Give newly created temporary work files time to finish; locked files
        # are skipped too. Cache files can be regenerated and count immediately.
        if kind == 'temp' and not clear_all and not startup and modified > now - 60:
            continue
        if _remove(path, getattr(paths, kind), cancel,
                   truncate=kind == 'logs' and path.name in ('deeppick.log', 'ocr.log')):
            setattr(usage, kind, getattr(usage, kind) - size)
            usage.removed += size
        else:
            usage.blocked += 1
    return usage


def _remove(path, folder, cancel, truncate=False):
    try:
        if cancel() or not _safe_root(folder) or not path.resolve().is_relative_to(folder.absolute()) or path.is_symlink():
            return False
        if getattr(path.stat(follow_symlinks=False), 'st_file_attributes', 0) & 0x400:
            return False
        if truncate:
            with path.open('wb'):
                pass
        else:
            path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _safe_root(folder):
    try:
        return (folder.resolve() == folder.absolute() and not folder.is_symlink() and
                not getattr(folder.stat(follow_symlinks=False), 'st_file_attributes', 0) & 0x400)
    except OSError:
        return False
