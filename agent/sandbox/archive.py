"""Bounded, binary-safe archives; also executed inside E2B with Python's stdlib."""
import hashlib
import base64
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import zipfile

MAX_FILES = 250
MAX_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE = 10 * 1024 * 1024
EXCLUDED = {'.git', '.env', '.venv', 'node_modules', 'dist', '.next', '.cache', '__pycache__'}


def allowed(path):
    return not any(p in EXCLUDED or p.startswith('.env.') for p in PurePosixPath(path).parts)


def safe_path(name):
    p = PurePosixPath(name)
    if (not name or len(name) > 512 or p.is_absolute() or '..' in p.parts
            or '\\' in name or ':' in name or any(ord(c) < 32 for c in name)
            or str(p) != name or not allowed(name)):
        raise ValueError('Unsafe archive path')
    return name


def manifest(archive):
    """Validate before serving/extracting. Never trust ZIP size or path metadata alone."""
    if len(archive) > MAX_ARCHIVE:
        raise ValueError('Project archive exceeds 10 MiB')
    entries, total = {}, 0
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        if len(z.infolist()) > MAX_FILES:
            raise ValueError('Project exceeds 250 files')
        for item in z.infolist():
            name = safe_path(item.filename)
            mode = item.external_attr >> 16
            if name in entries or item.is_dir() or (stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                raise ValueError('Archive contains duplicate or non-regular files')
            if item.flag_bits & 1 or item.file_size > MAX_BYTES - total:
                raise ValueError('Project exceeds 32 MiB or is encrypted')
            digest, size = hashlib.sha256(), 0
            with z.open(item) as stream:
                while chunk := stream.read(64 * 1024):
                    size += len(chunk)
                    if total + size > MAX_BYTES:
                        raise ValueError('Project exceeds 32 MiB')
                    digest.update(chunk)
            total += size
            entries[name] = {'size': size, 'sha256': digest.hexdigest()}
    for name in entries:
        if any(str(p) in entries for p in PurePosixPath(name).parents if str(p) != '.'):
            raise ValueError('File and directory paths conflict')
    return dict(sorted(entries.items()))


def content_hash(files, template):
    return hashlib.sha256(json.dumps({'files': files, 'template': template}, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def workspace_files(root):
    files, total = {}, 0
    for folder, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if allowed(str((Path(folder) / d).relative_to(root))))
        for name in sorted(dirs + names):
            path = Path(folder) / name
            relative = path.relative_to(root).as_posix()
            if not allowed(relative):
                continue
            safe_path(relative)
            if path.is_symlink():
                raise ValueError('Project symlinks cannot be checkpointed')
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError('Project contains a non-regular file')
            size = path.stat().st_size
            total += size
            if total > MAX_BYTES or len(files) >= MAX_FILES:
                raise ValueError('Project exceeds persistence limits')
            with path.open('rb') as source:
                digest = hashlib.file_digest(source, 'sha256').hexdigest()
            files[relative] = {'size': size, 'sha256': digest}
    return dict(sorted(files.items()))


def pack(root, target):
    before = workspace_files(root)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in before:
            z.write(root / name, name)
            if Path(target).stat().st_size > MAX_ARCHIVE:
                raise ValueError('Project archive exceeds 10 MiB')
    if Path(target).stat().st_size > MAX_ARCHIVE:
        raise ValueError('Project archive exceeds 10 MiB')
    # Detect concurrent background writers, including deletes/renames during collection.
    if manifest(Path(target).read_bytes()) != before or workspace_files(root) != before:
        raise ValueError('Workspace changed during checkpoint; stop background writers')


def restore(root, source):
    manifest(Path(source).read_bytes())
    # E2B is disposable. Clear template sources so deleted files never reappear.
    # Keep only installed dependencies; npm ci below refreshes them from the lockfile.
    for path in root.iterdir():
        if path.name == 'node_modules' and path.is_dir() and not path.is_symlink():
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    with zipfile.ZipFile(source) as z:
        z.extractall(root)  # Validated above; destination contains no source symlinks.


if __name__ == '__main__':
    mode, root, target = sys.argv[1:]
    try:
        (pack if mode == 'pack' else restore)(Path(root), target)
        if mode == 'pack':
            # E2B's file "stream" API currently buffers the entire response. Return a
            # bounded payload from our own process instead, even if another process grows the ZIP.
            with open(target, 'rb') as source:
                data = source.read(MAX_ARCHIVE + 1)
            if len(data) > MAX_ARCHIVE:
                raise ValueError('Archive grew after packaging')
            print(base64.b64encode(data).decode('ascii'))
    except Exception:
        # Generated filenames or command output must not expose secrets in host logs.
        sys.exit('Project archive operation failed: invalid, oversized, or changing workspace')
