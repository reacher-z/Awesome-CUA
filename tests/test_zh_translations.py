import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build import FACET_TEMPLATE, validate_translations  # noqa: E402

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

    def test_rejects_a_summary_assembled_from_facet_labels(self):
        for text in ("Chrome Faithful：面向网页（Web）环境的工具，支持网页浏览与交互、界面自动化执行。",
                     "DeskForge：面向桌面端、Linux环境的框架，支持轨迹与数据合成、强化学习。"):
            self.assertTrue(validate_translations(ROWS, {"arxiv:1": {"summary": text}}), text)
        self.assertEqual(validate_translations(ROWS, {"arxiv:1": {"summary": "面向网页环境的智能体基准，支持多步任务评测。"}}), [])

    def test_committed_translations_hold_no_facet_template(self):
        path = Path(__file__).resolve().parents[1] / "data/translations.zh-CN.json"
        table = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        templated = sorted(rid for rid, entry in table.items() if FACET_TEMPLATE.search(entry["summary"]))
        self.assertEqual(templated, [])

    def test_rejects_non_object_file(self):
        self.assertTrue(validate_translations(ROWS, []))


if __name__ == "__main__":
    unittest.main()
