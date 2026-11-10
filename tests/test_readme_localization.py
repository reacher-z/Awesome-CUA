import contextlib
from html.parser import HTMLParser
import io
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build


class EmbedParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.ends = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_endtag(self, tag):
        self.ends.append(tag)


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
        zh = build.stats_block(self.report, "zh", 812)
        for figure in ("996", "812", "44", "2026-10-17T07:57:59Z", "1,549", "1,402", "100"):
            self.assertIn(figure, zh)
        self.assertIn("条已审阅资源", zh)
        self.assertTrue(build.stats_block(self.report, reviewed_papers=812).startswith("\n\n**996 curated resources** · **812 reviewed papers and surveys**"))

    def test_headline_counts_only_curated_resources(self):
        for lang in ("en", "zh"):
            with self.subTest(lang):
                block = build.stats_block(self.report, lang, 812)
                headline, detail = block.strip().split("\n\n")
                self.assertNotIn("2,545", block)
                self.assertNotIn("1,549", headline)
                self.assertNotIn("1,402", headline)
                self.assertIn("**1,549", detail)
                self.assertIn("**1,402", detail)

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
        self.assertLessEqual(badges.count("!["), 6)
        self.assertIn("dataset-Hugging%20Face-", badges)
        self.assertNotIn(")](", badges)
        self.assertIn("img.shields.io/endpoint?url=", badges)
        self.assertTrue(badges.strip().endswith("labelColor=1E2233)")

    def test_star_history_has_linked_light_and_dark_sources_and_localized_fallbacks(self):
        chart = "https://api.star-history.com/svg?repos=reacher-z/Awesome-CUA&type=Date"
        link = "https://www.star-history.com/#reacher-z/Awesome-CUA&Date"
        for lang, heading, alt, label in (
            ("en", "Star History", "GitHub star count over time for Awesome-CUA", "View Awesome-CUA on Star History"),
            ("zh", "Star 历史", "Awesome-CUA 的 GitHub Star 数量随时间变化趋势", "在 Star History 查看 Awesome-CUA 的 Star 历史"),
        ):
            with self.subTest(lang=lang):
                block = build.star_history(lang)
                parser = EmbedParser()
                parser.feed(block)
                self.assertEqual(parser.tags, [
                    ("a", {"href": link}),
                    ("picture", {}),
                    ("source", {"media": "(prefers-color-scheme: dark)", "srcset": chart + "&theme=dark"}),
                    ("source", {"media": "(prefers-color-scheme: light)", "srcset": chart}),
                    ("img", {"src": chart, "alt": alt, "width": "100%"}),
                ])
                self.assertEqual(parser.ends, ["picture", "a"])
                self.assertIn(f"## {heading}\n", block)
                self.assertIn(f"[{label}]({link})", block.split("</a>", 1)[1])
                self.assertIn("&amp;type=Date&amp;theme=dark", block)

    def test_star_history_is_generated_once_after_existing_footer(self):
        for filename, lang in (("README.md", "en"), ("README.zh-CN.md", "zh")):
            with self.subTest(lang=lang):
                content = (ROOT / filename).read_text(encoding="utf-8")
                start, end = "<!-- STAR_HISTORY:START -->", "<!-- STAR_HISTORY:END -->"
                self.assertEqual(content.count(start), 1)
                self.assertEqual(content.count(end), 1)
                self.assertTrue(content.endswith(start + build.star_history(lang) + end + "\n"))
                self.assertLess(content.index("[CITATION.cff]"), content.index(start))

    def test_build_restores_star_history_and_preserves_readmes(self):
        originals = {name: (ROOT / name).read_text(encoding="utf-8") for name in ("README.md", "README.zh-CN.md")}
        pattern = r"(?<=<!-- STAR_HISTORY:START -->).*?(?=<!-- STAR_HISTORY:END -->)"
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(build, "ROOT", Path(directory)), \
                contextlib.redirect_stdout(io.StringIO()):
            for name, content in originals.items():
                (Path(directory) / name).write_text(re.sub(pattern, "\nStale chart\n", content, flags=re.S), encoding="utf-8")
            build.build(types.SimpleNamespace(check=False))
            for name, expected in originals.items():
                self.assertEqual((Path(directory) / name).read_text(encoding="utf-8"), expected)
            build.build(types.SimpleNamespace(check=True))

    def test_explore_table_pipes_line_up_in_both_languages(self):
        rows = [row("github:a/b", "Bench"), row("arxiv:2401.00001", "Paper", kind="paper")]
        for lang in ("en", "zh"):
            table = [line for line in build.explore(rows, self.report, lang).splitlines() if line.startswith("|")]
            self.assertEqual(len({tuple(i for i, c in enumerate(line) if c == "|") for line in table}), 1, table)


if __name__ == "__main__":
    unittest.main()
