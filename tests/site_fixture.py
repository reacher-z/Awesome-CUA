"""One website build of the working tree, shared read-only by the test classes that inspect it.

A full build takes 30-60 seconds on a CI runner, and ten test classes only read
the default build. ``shared_site()`` builds it once per set of inputs into
``.cache/test-site/<key>/site`` and every later caller, in this process or another
test worker, reuses it. The key covers every file under the repository except
``.git``, ``dist``, ``.cache`` and bytecode, plus the Python version, so any change
to code, data or templates triggers a fresh build. Callers must not modify the tree.
"""
import hashlib
import os
from pathlib import Path
import shutil
import sys
import time
import unittest

try:
    import fcntl
except ImportError:  # Windows: no shared lock, so each process keeps its own build.
    fcntl = None

ROOT = Path(__file__).resolve().parents[1]
# The scan workflow's quality gate sets CATALOG_SCAN_QUALITY. A scan changes data, never code, so the tests that
# rebuild the site from edited copies of its inputs to check code behaviour run in Catalog quality and publication.
code_only = unittest.skipIf(os.environ.get('CATALOG_SCAN_QUALITY') == '1',
                            'rebuilds edited copies of the inputs to check code; Catalog quality and publication run it')
CACHE = ROOT / '.cache' / 'test-site'
SKIP_DIRS = {'.git', 'dist', '.cache', '__pycache__', 'node_modules', '.venv', 'output'}
_built = {}


def input_key():
    digest = hashlib.sha256(sys.version.encode())
    for directory, names, files in os.walk(ROOT):
        names[:] = sorted(name for name in names if name not in SKIP_DIRS)
        for name in sorted(files):
            if name.endswith(('.pyc', '.tmp')):
                continue
            path = Path(directory, name)
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            digest.update(f'{path.relative_to(ROOT).as_posix()}\0{stat.st_size}\0{stat.st_mtime_ns}\n'.encode())
    return digest.hexdigest()[:24]


def shared_site():
    """Path of a complete default website build of the current working tree."""
    key = input_key()
    if key in _built:
        return _built[key]
    from build_site import build_site
    CACHE.mkdir(parents=True, exist_ok=True)
    with open(CACHE / '.lock', 'w') as lock:
        if fcntl:
            fcntl.flock(lock, fcntl.LOCK_EX)
        entry = CACHE / (key if fcntl else f'{key}-{os.getpid()}')
        if not (entry / 'complete').exists():
            # Builds for other inputs may still be in use by a concurrent run; drop those over an hour old.
            for stale in CACHE.iterdir():
                if stale.is_dir() and stale != entry and time.time() - stale.stat().st_mtime > 3600:
                    shutil.rmtree(stale, ignore_errors=True)
            shutil.rmtree(entry, ignore_errors=True)
            entry.mkdir()
            build_site(entry / 'site')
            (entry / 'complete').write_text(key + '\n')
    _built[key] = entry / 'site'
    return _built[key]
