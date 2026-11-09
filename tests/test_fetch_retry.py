import datetime as dt
import email.message
import email.utils
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog


URL = "https://export.arxiv.org/api/query?id_list=2404.07972"


def http_error(status, retry_after=None):
    headers = email.message.Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError(URL, status, "error", headers, None)


def response(body=b"<feed/>"):
    result = mock.MagicMock(status=200, url=URL, headers={"Content-Type": "application/atom+xml"})
    result.__enter__.return_value = result
    result.read.return_value = body
    return result


class FetchRetryTests(unittest.TestCase):
    def setUp(self):
        self.cache = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(mock.patch.object(catalog, "CACHE", self.cache))
        self.sleep = self.enterContext(mock.patch("time.sleep"))

    def fetch(self, *outcomes):
        with mock.patch("urllib.request.urlopen", side_effect=list(outcomes) + [AssertionError("too many requests")]) as urlopen:
            info, body = catalog.fetch(URL, refresh=True)
        return info, body, urlopen.call_count

    def test_transient_503_honours_retry_after_then_succeeds(self):
        info, body, calls = self.fetch(http_error(503, "5"), response())
        self.assertTrue(info["ok"])
        self.assertEqual((info["status"], info["request_attempts"], calls, body), (200, 2, 2, b"<feed/>"))
        self.sleep.assert_called_once_with(5)
        self.assertEqual(catalog.fetch(URL)[1], b"<feed/>")
        self.assertEqual(catalog.fetch(URL)[0]["sha256"], hashlib.sha256(b"<feed/>").hexdigest())

    def test_http_date_retry_after_is_converted_to_seconds(self):
        later = email.utils.format_datetime(dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=30), usegmt=True)
        info, _, calls = self.fetch(http_error(429, later), response())
        self.assertTrue(info["ok"])
        self.assertEqual(calls, 2)
        self.assertTrue(20 <= self.sleep.call_args.args[0] <= 30, self.sleep.call_args)

    def test_short_retry_after_keeps_the_arxiv_request_spacing(self):
        past = email.utils.format_datetime(dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=30), usegmt=True)
        for retry_after in ("0", "2", "3", past):
            with self.subTest(retry_after=retry_after):
                self.sleep.reset_mock()
                info, _, calls = self.fetch(http_error(429, retry_after), response())
                self.assertEqual((info["ok"], calls), (True, 2))
                self.sleep.assert_called_once_with(catalog.MIN_RETRY_DELAY)
        self.assertEqual(catalog.MIN_RETRY_DELAY, 3.1)

    def test_client_errors_are_attempted_once(self):
        for status in (400, 403, 404):
            with self.subTest(status=status):
                self.sleep.reset_mock()
                info, body, calls = self.fetch(http_error(status, "1"))
                self.assertEqual((info["ok"], info["status"], info["request_attempts"], calls, body), (False, status, 1, 1, b""))
                self.sleep.assert_not_called()

    def test_persistent_server_errors_stop_after_bounded_backoff(self):
        key = hashlib.sha256(URL.encode()).hexdigest()
        catalog.write_json(self.cache / f"{key}.json", {"ok": True, "url": URL, "sha256": hashlib.sha256(b"old good snapshot").hexdigest()})
        (self.cache / f"{key}.body").write_bytes(b"old good snapshot")
        info, body, calls = self.fetch(*[http_error(503)] * catalog.MAX_ATTEMPTS)
        self.assertEqual((info["ok"], info["status"], info["request_attempts"], calls, body), (False, 503, 3, 3, b""))
        delays = [c.args[0] for c in self.sleep.call_args_list]
        self.assertEqual(len(delays), 2)
        self.assertTrue(3.1 <= delays[0] <= 3.35 and 6.2 <= delays[1] <= 6.45, delays)
        self.assertEqual(catalog.read_json(self.cache / f"{key}.error.json")["status"], 503)
        self.assertEqual(catalog.fetch(URL)[1], b"old good snapshot")

    def test_network_errors_and_timeouts_are_retried(self):
        for error in (urllib.error.URLError("temporary failure in name resolution"), TimeoutError("timed out"), ConnectionResetError("reset")):
            with self.subTest(error=type(error).__name__):
                self.sleep.reset_mock()
                info, _, calls = self.fetch(error, response())
                self.assertTrue(info["ok"])
                self.assertEqual((info["request_attempts"], calls), (2, 2))
                self.assertTrue(3.1 <= self.sleep.call_args.args[0] <= 3.35, self.sleep.call_args)

    def test_retry_after_beyond_the_cap_is_left_to_the_caller(self):
        info, _, calls = self.fetch(http_error(429, str(catalog.MAX_RETRY_AFTER + 1)))
        self.assertEqual((info["ok"], info["status"], info["retry_after"], calls), (False, 429, "61", 1))
        self.assertTrue(info['deferred'])
        self.sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
