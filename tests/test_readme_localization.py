from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build


def row(rid, name, kind="benchmark"):
    return {"id": rid, "name": name, "kind": kind, "review_status": "curated", "url": "https://example.com/" + name, "environments": ["web"],
        "summary": name + " summary.", "relations": [], "licenses": {"code": {"declared": "MIT", "url": "https://example.com/LICENSE"}, "data": None, "weights": None, "document": None}}


class ReadmeLocalizationTests(unittest.TestCase):
    report = {"total_records": 2545, "curated_records": 996, "bibliographic_records": 2164, "sources": [{}] * 44, "as_of_utc": "2026-10-17T07:57:59Z",
        "metadata_only_records": 1549, "unindexed_candidates": 1402, "excluded_records": 100}

    def test_both_languages_share_one_set_of_label_keys(self):
        en, zh = build.README_TEXT["en"], build.README_TEXT["zh"]
        self.assertEqual(en.keys(), zh.keys())
        for key in ("labels", "kinds", "scopes"):
            self.assertEqual(en[key].keys(), zh[key].keys())

    def test_chinese_stats_keep_every_figure(self):
        zh = build.stats_block(self.report, "zh")
        for figure in ("2,545", "996", "2,164", "44", "2026-10-17T07:57:59Z", "1,549", "1,402", "100"):
            self.assertIn(figure, zh)
        self.assertIn("条资源记录", zh)
        self.assertTrue(build.stats_block(self.report).startswith("\n\n**2,545 resource records**"))

    def test_chinese_tables_translate_labels_but_not_resources(self):
        rows = [row("github:a/b", "Bench"), row("arxiv:2401.00001", "Paper", kind="paper")]
        edges = [{"source_id": "x", "target_id": "github:a/b", "target_in_catalog": True}]
        explore = build.explore(rows, self.report, "zh")
        self.assertIn("[基准](docs/benchmarks.md) · **1**", explore)
        self.assertIn("**1** 篇已审阅论文", explore)
        highlights = build.highlights(rows, edges, lang="zh")
        self.assertIn("**基准** · [全部 1 项 →](docs/benchmarks.md)", highlights)
        # Paper and licence sit under the name; the platform uses its Chinese display label.
        self.assertIn("| [Bench](https://example.com/Bench)<br>代码 MIT | 1 | 网页 |", highlights)
        self.assertIn("代码 MIT", highlights)
        recent = build.recently_reviewed(rows, {"github:a/b": "2026-10-17T00:00:00Z"}, lang="zh")
        self.assertIn("| 基准 | web | Bench summary. |", recent)


if __name__ == "__main__":
    unittest.main()
