import builtins
import errno
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog


URL = "https://example.org/source"


def response(body):
    result = mock.MagicMock(status=200, url=URL, headers={"Content-Type": "text/plain"})
    result.__enter__.return_value = result
    result.read.return_value = body
    return result


class PartialWriter:
    """Stands in for SIGKILL or ENOSPC part-way through a write."""
    def __init__(self, stream):
        self.stream = stream

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()

    def write(self, data):
        self.stream.write(data[: len(data) // 3])
        self.stream.flush()
        raise OSError(errno.ENOSPC, "No space left on device")

    def fileno(self):
        return self.stream.fileno()


class AtomicDataWriteTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.path = self.directory / "papers.jsonl"
        self.rows = [{"id": f"arxiv:2610.{i:05d}", "name": "x" * 200} for i in range(2000)]
        catalog.write_jsonl(self.path, self.rows)
        self.original = self.path.read_bytes()

    def assert_archive_intact(self):
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(len(catalog.read_jsonl(self.path)), 2000)
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), ["papers.jsonl"])

    def test_failed_write_leaves_previous_archive_readable(self):
        real_open = builtins.open
        def partial(file, mode="r", *args, **kwargs):
            stream = real_open(file, mode, *args, **kwargs)
            return PartialWriter(stream) if "w" in mode else stream
        with mock.patch("builtins.open", partial), mock.patch("io.open", partial), self.assertRaises(OSError):
            catalog.write_jsonl(self.path, self.rows + [{"id": "arxiv:2610.99999", "name": "new"}])
        self.assert_archive_intact()

    def test_failure_before_replace_leaves_previous_archive(self):
        for target in ("os.fsync", "os.replace"):
            with self.subTest(target), mock.patch(target, side_effect=OSError(errno.ENOSPC, "No space left on device")), self.assertRaises(OSError):
                catalog.write_json(self.path, {"replaced": True})
            self.assert_archive_intact()

    def test_replacement_keeps_existing_mode_and_new_files_follow_umask(self):
        self.path.chmod(0o640)
        catalog.write_jsonl(self.path, self.rows[:1])
        self.assertEqual((self.path.stat().st_mode & 0o777, len(catalog.read_jsonl(self.path))), (0o640, 1))
        previous = os.umask(0o022)
        try:
            catalog.write_json(self.directory / "new" / "report.json", {"ok": True})
        finally:
            os.umask(previous)
        self.assertEqual((self.directory / "new" / "report.json").stat().st_mode & 0o777, 0o644)
        self.assertEqual(catalog.read_json(self.directory / "new" / "report.json"), {"ok": True})
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), ["new", "papers.jsonl"])

    def test_windows_writes_open_binary_and_keep_the_mode_without_fchmod(self):
        # On Windows os.open defaults to text mode (LF becomes CRLF), and os.fchmod is missing before Python 3.13.
        self.path.chmod(0o640)
        real_open, flags = os.open, []
        def recording_open(path, flag, mode=0o777):
            flags.append(flag)
            return real_open(path, flag & ~0x8000, mode)
        with mock.patch.object(os, "O_BINARY", 0x8000, create=True), mock.patch("os.open", recording_open), \
                mock.patch.object(os, "fchmod", side_effect=AssertionError("os.fchmod is unavailable on Windows before 3.13")):
            catalog.write_jsonl(self.path, self.rows[:1])
        self.assertTrue(flags and all(flag & 0x8000 for flag in flags))
        self.assertEqual((self.path.stat().st_mode & 0o777, len(catalog.read_jsonl(self.path))), (0o640, 1))


class FetchCacheConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.cache = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(mock.patch.object(catalog, "CACHE", self.cache))
        self.enterContext(mock.patch("time.sleep"))
        self.key = hashlib.sha256(URL.encode()).hexdigest()
        with mock.patch("urllib.request.urlopen", return_value=response(b"v1 body")):
            catalog.fetch(URL)

    def fetch(self, *bodies, refresh=False):
        with mock.patch("urllib.request.urlopen", side_effect=[response(b) for b in bodies] + [AssertionError("unexpected request")]) as urlopen:
            info, body = catalog.fetch(URL, refresh=refresh)
        return info, body, urlopen.call_count

    def assert_consistent(self, info, body):
        self.assertTrue(info["ok"])
        self.assertEqual(info["sha256"], hashlib.sha256(body).hexdigest())

    def test_kill_between_body_and_metadata_writes_is_a_cache_miss(self):
        real = catalog.write_json
        def killed(path, value):
            if path.name == f"{self.key}.json":
                raise KeyboardInterrupt
            real(path, value)
        with mock.patch.object(catalog, "write_json", killed), self.assertRaises(KeyboardInterrupt):
            self.fetch(b"v2 body", refresh=True)
        self.assertEqual((self.cache / f"{self.key}.body").read_bytes(), b"v2 body")
        info, body, calls = self.fetch(b"v3 body")
        self.assert_consistent(info, body)
        self.assertEqual((body, calls), (b"v3 body", 1))
        cached, cached_body, calls = self.fetch()
        self.assertEqual((cached_body, calls), (body, 0))
        self.assertEqual(cached, {**info, "request_attempted": False,
                                  "request_attempts": 0, "cache_used": True})
        self.assertEqual(catalog.read_json(self.cache / f"{self.key}.json"), info)

    def test_kill_during_body_write_keeps_previous_cache_entry(self):
        with mock.patch("os.replace", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.fetch(b"v2 body", refresh=True)
        info, body, calls = self.fetch()
        self.assert_consistent(info, body)
        self.assertEqual((body, calls), (b"v1 body", 0))
        self.assertEqual(sorted(p.name for p in self.cache.iterdir()), [f"{self.key}.body", f"{self.key}.json"])

    def test_torn_metadata_is_a_cache_miss(self):
        for torn in ('{"ok": tru', "", "\udcff"):
            with self.subTest(torn=torn):
                (self.cache / f"{self.key}.json").write_text(torn, errors="surrogateescape")
                info, body, calls = self.fetch(b"v2 body")
                self.assert_consistent(info, body)
                self.assertEqual((body, calls), (b"v2 body", 1))
                self.assertEqual(catalog.read_json(self.cache / f"{self.key}.json"), info)


if __name__ == "__main__":
    unittest.main()
