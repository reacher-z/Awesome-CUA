import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build import validate_translations  # noqa: E402

ROWS = [{"id": "arxiv:1", "review_status": "curated"}, {"id": "arxiv:2", "review_status": "metadata_verified"}]


class ChineseTranslationTests(unittest.TestCase):
    def test_accepts_a_curated_record_with_chinese_summary(self):
        self.assertEqual(validate_translations(ROWS, {"arxiv:1": {"summary": "提出一个网页智能体基准。"}}), [])

    def test_rejects_unknown_or_uncurated_ids(self):
        self.assertTrue(validate_translations(ROWS, {"arxiv:2": {"summary": "提出一个基准。"}}))
        self.assertTrue(validate_translations(ROWS, {"arxiv:9": {"summary": "提出一个基准。"}}))

    def test_rejects_english_empty_long_or_extra_keys(self):
        for entry in ({"summary": "An English summary."}, {"summary": ""}, {"summary": "长" * 221 + "。"}, {"summary": "提出基准。", "notes": "x"}, "text"):
            self.assertTrue(validate_translations(ROWS, {"arxiv:1": entry}), entry)

    def test_rejects_non_object_file(self):
        self.assertTrue(validate_translations(ROWS, []))


if __name__ == "__main__":
    unittest.main()
