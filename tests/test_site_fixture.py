"""The shared website build is keyed by every input file and rebuilt when any of them changes."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_fixture  # noqa: E402


class InputKeyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for name, text in {"data/a.jsonl": "a\n", "scripts/b.py": "b\n", "web/c.css": "c\n"}.items():
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text(text)
        self.enterContext(mock.patch.object(site_fixture, "ROOT", self.root))

    def test_key_is_stable_and_changes_with_any_input(self):
        key = site_fixture.input_key()
        self.assertEqual(site_fixture.input_key(), key)
        (self.root / "data/a.jsonl").write_text("changed\n")
        changed = site_fixture.input_key()
        self.assertNotEqual(changed, key)
        (self.root / "web/new.js").write_text("new\n")
        self.assertNotEqual(site_fixture.input_key(), changed)

    def test_outputs_caches_and_bytecode_do_not_change_the_key(self):
        key = site_fixture.input_key()
        for name in ("dist/site/index.html", ".cache/test-site/x/site/index.html", "scripts/__pycache__/b.cpython-312.pyc",
                     ".git/index", "data/.a.jsonl.123.tmp"):
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text("x\n")
        self.assertEqual(site_fixture.input_key(), key)

    def test_a_later_modification_time_changes_the_key(self):
        key = site_fixture.input_key()
        path = self.root / "scripts/b.py"
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
        self.assertNotEqual(site_fixture.input_key(), key)


if __name__ == "__main__":
    unittest.main()
