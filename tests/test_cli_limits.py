"""Reject invalid scan limits before any command reads or fetches data."""
import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog

COMMANDS = {
    "discover": "discover",
    "harvest": "harvest",
    "search-arxiv": "search_arxiv",
    "verify": "verify_editorial",
    "enrich": "enrich",
}


class ScanLimitTests(unittest.TestCase):
    def test_negative_limits_fail_before_dispatch(self):
        for command, function in COMMANDS.items():
            with self.subTest(command=command):
                with mock.patch.object(catalog, function) as handler:
                    with contextlib.redirect_stderr(io.StringIO()) as err:
                        with self.assertRaises(SystemExit) as raised:
                            catalog.main([command, "--limit", "-1"])
                    self.assertEqual(raised.exception.code, 2)
                    self.assertIn("must be 0 or greater", err.getvalue())
                    handler.assert_not_called()

    def test_zero_positive_and_default_limits_reach_the_handler(self):
        for command, function in COMMANDS.items():
            for options, expected in (([], 0), (["--limit", "0"], 0), (["--limit", "2"], 2)):
                with self.subTest(command=command, options=options):
                    with mock.patch.object(catalog, function, return_value=0) as handler:
                        self.assertEqual(catalog.main([command, *options]), 0)
                    handler.assert_called_once()
                    self.assertEqual(handler.call_args.args[0].limit, expected)


if __name__ == "__main__":
    unittest.main()
