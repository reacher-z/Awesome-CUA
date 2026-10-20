from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build

NB = "‑"  # non-breaking hyphen, as build.nowrap uses for dates


def row(rid, name, environments, licenses=None, relations=()):
    return {"id": rid, "name": name, "kind": "benchmark", "review_status": "curated", "url": "https://example.com/" + name,
        "environments": environments, "summary": name + " summary.", "relations": list(relations),
        "licenses": {"code": licenses, "data": None, "weights": None, "document": None}}


class ReadmeHighlightLayoutTests(unittest.TestCase):
    def setUp(self):
        paper = {"id": "arxiv:2404.07972", "name": "Paper", "kind": "paper", "review_status": "curated", "url": "https://arxiv.org/abs/2404.07972",
                 "environments": ["desktop"], "summary": "", "relations": [], "licenses": {}, "published_at": "2024-04-11"}
        self.rows = [row("github:a/b", "Bench", ["cross-platform", "macos"], {"declared": "Apache-2.0", "url": "https://example.com/L"},
                         [{"type": "introduced_by", "target_id": "arxiv:2404.07972"}]),
                     row("github:c/d", "Bare", ["unspecified"]), paper]
        self.edges = [{"source_id": "x", "target_id": rid, "target_in_catalog": True} for rid in ("github:a/b", "github:c/d")]

    def test_highlight_tables_keep_four_columns_with_paper_and_licence_under_the_name(self):
        text = build.highlights(self.rows, self.edges)
        self.assertIn("| Resource | Mentions | Environments | Description |\n| --- | ---: | --- | --- |", text)
        self.assertIn(f"| [Bench](https://example.com/Bench)<br>[2404.07972](https://arxiv.org/abs/2404.07972) (2024) · code Apache{NB}2.0 | 1 | Cross{NB}platform, macOS | Bench summary. |", text)

    def test_missing_facts_and_unspecified_platforms_read_plainly(self):
        text = build.highlights(self.rows, self.edges)
        self.assertIn("| [Bare](https://example.com/Bare)<br>— | 1 | Not specified | Bare summary. |", text)
        self.assertIn("| 1 | 未注明 |", build.highlights(self.rows, self.edges, lang="zh"))


if __name__ == "__main__":
    unittest.main()
