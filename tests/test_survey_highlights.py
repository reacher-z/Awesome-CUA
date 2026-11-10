from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build


def survey(rid, name, published_at, status="curated"):
    return {"id": rid, "name": name, "kind": "survey", "review_status": status, "url": "https://arxiv.org/abs/" + rid.split(":")[1],
        "environments": ["cross-platform"], "summary": "Boilerplate.", "published_at": published_at, "relations": [], "identifiers": {},
        "licenses": {"code": None, "data": None, "weights": None, "document": None}}


class SurveyHighlightTests(unittest.TestCase):
    def test_newest_five_reviewed_surveys_lead_the_highlights(self):
        rows = [survey(f"arxiv:250{i}.0000{i}", f"Survey {i}", f"2025-0{i}-01") for i in range(1, 8)] + [survey("arxiv:2509.00009", "Unreviewed", "2025-09-01", "metadata_verified")]
        block = build.highlights(rows, [])
        lines = [line for line in block.splitlines() if line.startswith("| 2025")]
        self.assertEqual([line.split("[")[1].split("]")[0] for line in lines], ["Survey 7", "Survey 6", "Survey 5", "Survey 4", "Survey 3"])
        self.assertTrue(block.lstrip().startswith("**Start with the newest surveys** · 7 in the catalog"))
        self.assertNotIn("Boilerplate", block)
        self.assertIn("**从最新综述入门** · 目录中共 7 项", build.highlights(rows, [], lang="zh"))

    def test_no_surveys_no_table(self):
        self.assertNotIn("surveys", build.highlights([], []).casefold())


if __name__ == "__main__":
    unittest.main()
