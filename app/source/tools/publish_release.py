"""Publish the current approved runtime as a clean, private-data-free ZIP.

No dependency installation or binary patching. Run with Python 3.11+ from D:.
The installed application need not be rebuilt for documentation/source changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from pathlib import Path

PRIVATE = {'config', 'history', 'cache', 'temp', 'logs', 'output'}
SOURCE_EXCLUDED = {'AGENTS.md', 'DEVELOPMENT.md', 'DeepPickAI.spec', 'requirements.txt', 'tools'}
VERSION = '1.2.3'


def digest(file):
    result = hashlib.sha256()
    with file.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def collect(root):
    files = {}
    for prefix in ('app/source', 'app/runtime', 'app/licenses', 'models'):
        anchor = root / prefix
        if not anchor.is_dir() or anchor.resolve() != anchor:
            raise RuntimeError('Required directory missing or redirected: ' + str(anchor))
        for current, folders, names in os.walk(anchor, followlinks=False):
            current = Path(current)
            folders[:] = sorted(name for name in folders
                                if name not in ('__pycache__', 'test', 'tests')
                                and not (prefix == 'app/source' and name in SOURCE_EXCLUDED)
                                and not ((current / name).lstat().st_file_attributes & 0x400))
            for name in sorted(names):
                file = current / name
                if (file.lstat().st_file_attributes & 0x400 or file.suffix in ('.pyc', '.pdb')
                        or prefix == 'app/source' and name in SOURCE_EXCLUDED):
                    continue
                files[file.relative_to(root).as_posix()] = file
    for name in ('DeepPickAI.exe', 'DeepPickAI._pth', 'python3.dll', 'python311.dll',
                 'User-Guide.html', 'User-Guide.md', 'Getting-Started.txt', 'Third-Party-Notices.txt'):
        file = root / name
        if not file.is_file() or file.lstat().st_file_attributes & 0x400:
            raise RuntimeError('Required file missing or redirected: ' + str(file))
        files[name] = file
    return dict(sorted(files.items()))


def publish(root, outputs):
    root = root.resolve()
    outputs = outputs.resolve()
    if root.drive.upper() != 'D:' or outputs.drive.upper() != 'D:':
        raise RuntimeError('Distribution work must stay on D:.')
    outputs.mkdir(parents=True, exist_ok=True)
    files = collect(root)
    hashes = {name: digest(file) for name, file in files.items()}
    manifest = {'application': 'DeepPick AI', 'version': VERSION,
                'developer': 'Chunze Liu', 'platform': 'Windows x64',
                'install_path': 'D:\\DeepPickAI', 'files': hashes}
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')
    (outputs / 'File-Checksums.json').write_bytes(serialized)
    archive = outputs / ('DeepPickAI-' + VERSION + '-Windows-x64.zip')
    pending = archive.with_suffix('.zip.pending')
    with zipfile.ZipFile(pending, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipped:
        for folder in sorted(PRIVATE):
            zipped.writestr('DeepPickAI/' + folder + '/', b'')
        for name, file in files.items():
            zipped.write(file, 'DeepPickAI/' + name)
        zipped.writestr('DeepPickAI/File-Checksums.json', serialized)
    with zipfile.ZipFile(pending) as zipped:
        assert zipped.testzip() is None, 'ZIP integrity failed'
        names = zipped.namelist()
        assert len(names) == len(set(names)), 'Duplicate archive paths'
        assert all(name.startswith('DeepPickAI/') and '..' not in Path(name).parts for name in names)
        assert not any(name.startswith('DeepPickAI/' + folder + '/') and not name.endswith('/')
                       for folder in PRIVATE for name in names), 'Private data included'
        assert not any('/development/' in name or name.endswith('.lnk') for name in names)
        for name, expected in hashes.items():
            assert hashlib.sha256(zipped.read('DeepPickAI/' + name)).hexdigest() == expected, name
    os.replace(pending, archive)
    checksum = digest(archive)
    (outputs / 'SHA256.txt').write_text(checksum + '  ' + archive.name + '\n', 'utf-8')
    (root / 'File-Checksums.json').write_bytes(serialized)
    report = {'archive': archive.name, 'version': VERSION, 'sha256': checksum,
              'archive_bytes': archive.stat().st_size,
              'uncompressed_bytes': sum(file.stat().st_size for file in files.values()) + len(serialized),
              'files': len(hashes) + 1, 'zip_crc_and_sha256': 'PASS',
              'no_private_configuration_or_history': True,
              'no_machine_shortcuts_or_development_files': True}
    (outputs / 'Release-Check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(report, ensure_ascii=True), flush=True)
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('D:/DeepPickAI'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    publish(args.root, args.output)
