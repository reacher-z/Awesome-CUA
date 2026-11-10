from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import zh_summaries  # noqa: E402


class ChineseSummaries(unittest.TestCase):
    def test_an_entry_replaces_the_english_and_a_missing_entry_shows_it(self):
        with mock.patch.object(zh_summaries, "table", lambda: {"x": {"summary": "译文。"}}):
            self.assertEqual(zh_summaries.zh_summary({"id": "x", "summary": "English."}), "译文。")
            self.assertEqual(zh_summaries.zh_summary({"id": "y", "summary": "English."}), "English.")
            self.assertEqual(zh_summaries.zh_summary({"id": "y", "summary": "English.", "summary_zh": "手写。"}), "手写。")


if __name__ == "__main__":
    unittest.main()
