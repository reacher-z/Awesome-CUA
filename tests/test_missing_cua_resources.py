from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog


# Widely cited resources that #104 found missing: curated ID -> (kind, primary receipt URL).
CURATED = {"github:osu-nlp-group/mind2web-2": ("benchmark", "https://raw.githubusercontent.com/OSU-NLP-Group/Mind2Web-2/HEAD/README.md"),
    "github:microsoft/magma": ("model", "https://raw.githubusercontent.com/microsoft/Magma/HEAD/README.md"),
    "url:dec156cbf0cb1181f7b6": ("product", "https://aws.amazon.com/nova/act/")}
# Each reviewed README links its paper; the paper needs a retained bibliography record before a reviewed relation can name it.
PAPERS = {"github:osu-nlp-group/mind2web-2": "arxiv:2506.21506", "github:microsoft/magma": "arxiv:2502.13130"}
MARINER = "url:12d789d450207bd6d5da"


class MissingCuaResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl")}
        cls.enrichment = {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "enrichment.jsonl")}
        cls.queue = {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "review-queue.jsonl")}

    def test_resources_are_curated_from_their_first_party_receipt(self):
        for rid, (kind, url) in CURATED.items():
            with self.subTest(rid):
                record = self.records[rid]
                self.assertEqual((record["review_status"], record["kind"]), ("curated", kind))
                primary = next(ev for ev in record["evidence"] if ev["method"] == "editorial_primary_review")
                self.assertEqual(primary["url"], url)
                self.assertNotIn(rid, self.queue)

    def test_reviewed_readmes_link_their_papers(self):
        for rid, paper in PAPERS.items():
            with self.subTest(rid):
                sha = next(ev for ev in self.records[rid]["evidence"] if ev["method"] == "editorial_primary_review")["sha256"]
                self.assertIn(paper, {ref["target_id"] for ref in self.enrichment[rid]["references"] if ref["source_sha256"] == sha})

    def test_project_mariner_is_curated_from_its_announcement(self):
        # The review reads the Project Mariner section of Google's December 2024 Gemini 2.0 announcement.
        record = self.records[MARINER]
        self.assertEqual((record["review_status"], record["kind"]), ("curated", "product"))
        self.assertNotIn(MARINER, self.queue)
        primary = next(ev for ev in record["evidence"] if ev["method"] == "editorial_primary_review")
        self.assertTrue(primary["url"].startswith("https://blog.google/"))

if __name__ == "__main__":
    unittest.main()
