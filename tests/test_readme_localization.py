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
        for figure_block in (build.stats_block(self.report, "zh", 812), build.stats_detail(self.report, "zh", 812)):
            self.assertTrue(figure_block.strip())
        headline = build.stats_block(self.report, "zh", 812)
        detail = build.stats_detail(self.report, "zh", 812)
        for figure in ("996", "812", "44"):
            self.assertIn(figure, headline)
        for figure in ("2026-10-17T07:57:59Z", "1,549", "1,402", "100"):
            self.assertIn(figure, detail)
        self.assertIn("条已审阅资源", headline)
        self.assertTrue(build.stats_block(self.report, reviewed_papers=812).startswith("\n\n**996 curated resources** · **812 reviewed papers and surveys**"))

    def test_readme_carries_one_line_of_counts_and_the_detail_goes_to_the_coverage_ledger(self):
        for lang in ("en", "zh"):
            with self.subTest(lang):
                block = build.stats_block(self.report, lang, 812)
                self.assertEqual(len(block.strip().splitlines()), 1)
                self.assertNotIn("1,549", block)
                self.assertNotIn("2,545", block)
                self.assertIn("**1,549", build.stats_detail(self.report, lang, 812))
                self.assertIn("**1,402", build.stats_detail(self.report, lang, 812))

    def test_chinese_tables_translate_labels_but_not_resources(self):
        rows = [row("github:a/b", "Bench"), row("arxiv:2401.00001", "Paper", kind="paper")]
        edges = [{"source_id": "x", "target_id": "github:a/b", "target_in_catalog": True}]
        explore = build.explore(rows, self.report, "zh")
        self.assertRegex(explore, r"\| \[基准\]\(docs/benchmarks.md\) +\| .+ \| +1 \|")
        self.assertRegex(explore, r"\| \[按主题浏览研究\]\(docs/topics.md\) +\| .+ \| +1 \|")
        highlights = build.highlights(rows, edges, lang="zh")
        self.assertIn("**基准** · 目录中共 1 项", highlights)
        self.assertRegex(highlights, r"\| \[Bench\]\(https://example.com/Bench\) +\| +1 \| Web +\|")
        self.assertIn("代码 MIT", highlights)
        recent = build.recently_reviewed(rows, {"github:a/b": "2026-10-17T00:00:00Z"}, lang="zh")
        self.assertRegex(recent, r"\| 基准 +\| Web +\| Bench summary. +\|")

    def test_badges_are_at_most_six_and_end_with_license(self):
        badges = build.badges([row("arxiv:2401.00001", "Paper", kind="paper")], {**self.report, "as_of_utc": "2026-10-17T07:57:59Z"})
        self.assertLessEqual(badges.count("[!["), 6)
        self.assertIn("assets/brand/badges/huggingface.svg", badges)
        self.assertIn("](https://huggingface.co/datasets/AgPerry/awesome-cua)", badges)
        self.assertTrue(badges.strip().endswith("(https://github.com/reacher-z/Awesome-CUA)"))

    def test_explore_table_pipes_line_up_in_both_languages(self):
        rows = [row("github:a/b", "Bench"), row("arxiv:2401.00001", "Paper", kind="paper")]
        for lang in ("en", "zh"):
            table = [line for line in build.explore(rows, self.report, lang).splitlines() if line.startswith("|")]
            self.assertEqual(len({tuple(i for i, c in enumerate(line) if c == "|") for line in table}), 1, table)


if __name__ == "__main__":
    unittest.main()
