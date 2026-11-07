import contextlib
import copy
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build
import catalog
from test_catalog import paper


def row(rid, name, kind="benchmark", status="curated", relations=()):
    return {"id": rid, "name": name, "kind": kind, "review_status": status, "url": "https://example.com/" + rid, "environments": ["web"], "topics": [],
        "summary": name + " summary." if status == "curated" else None, "published_at": None, "relations": [{"type": t, "target_id": target, "evidence_url": "https://example.com/readme"} for t, target in relations],
        "licenses": {"code": None, "data": None, "weights": None, "document": None},
        "evidence": [{"method": "editorial_primary_review", "url": "https://example.com/readme", "retrieved_at": "2026-10-16T00:00:00Z"}]}


REPORT = {"as_of_utc": "2026-10-16T00:00:00Z", "total_records": 0, "curated_records": 0, "metadata_only_records": 0, "bibliographic_records": 0,
    "arxiv_archive_records": 0, "excluded_records": 0, "discovery_identifiers": 0, "unindexed_candidates": 0, "pending_editorial": [], "sources": [],
    "primary_search": {}, "license_declarations_by_scope": {}, "exclusion_revalidation_pending": 0, "curated_by_kind_and_environment": {}}


class UncuratedLinkedPaperTests(unittest.TestCase):
    rows = [row("arxiv:2401.00001", "Pending paper", "paper", "metadata_verified"), row("arxiv:2401.00002", "Reviewed paper", "paper"),
        row("arxiv:2401.00003", "Cited paper", "paper", "metadata_verified"), row("arxiv:2401.00004", "Unlinked paper", "paper", "metadata_verified"),
        row("github:a/bench", "Bench", relations=[("documented_by", "arxiv:2401.00001"), ("documented_by", "arxiv:2401.00002")]),
        row("github:a/model", "Model", "model", relations=[("introduced_by", "arxiv:2401.00001"), ("variant_of", "arxiv:2401.00003")]),
        row("github:a/draft", "Draft", status="metadata_verified", relations=[("documented_by", "arxiv:2401.00004")])]

    def test_lists_uncurated_papers_behind_curated_resources_only(self):
        self.assertEqual(build.uncurated_linked_papers(self.rows), [{"id": "arxiv:2401.00001", "name": "Pending paper",
            "url": "https://example.com/arxiv:2401.00001", "linked_from": ["github:a/bench", "github:a/model"]}])

    def test_coverage_ledger_lists_the_gap_or_states_there_is_none(self):
        page = build.documents(self.rows, {**REPORT, "uncurated_linked_papers": build.uncurated_linked_papers(self.rows)})["docs/coverage.md"]
        section = page.split("## Uncurated papers behind curated resources", 1)[1].split("\n## ", 1)[0]
        self.assertIn("| [Pending paper](https://example.com/arxiv:2401.00001) | [Bench](https://example.com/github:a/bench), [Model](https://example.com/github:a/model) |", section)
        self.assertNotIn("Unlinked paper", section)
        empty = build.documents(self.rows, {**REPORT, "uncurated_linked_papers": []})["docs/coverage.md"]
        self.assertIn("None: every paper linked from a curated resource is curated.", empty.split("## Uncurated papers behind curated resources", 1)[1].split("\n## ", 1)[0])

    def test_committed_coverage_matches_the_catalog(self):
        rows = catalog.read_jsonl(catalog.DATA / "catalog.jsonl")
        self.assertEqual(catalog.read_json(catalog.DATA / "coverage.json")["uncurated_linked_papers"], build.uncurated_linked_papers(rows))
        self.assertIn("## Uncurated papers behind curated resources", (catalog.ROOT / "docs/coverage.md").read_text(encoding="utf-8"))


class ValidateReportTests(unittest.TestCase):
    def test_validate_reports_an_uncurated_linked_paper_without_failing(self):
        benchmark = copy.deepcopy(next(r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl") if r["id"] == "github:xlang-ai/osworld"))
        self.assertIn("arxiv:2404.07972", {rel["target_id"] for rel in benchmark["relations"] if rel["type"] == "documented_by"})
        benchmark["relations"] = [rel for rel in benchmark["relations"] if rel["target_id"] == "arxiv:2404.07972"]
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(build, "DATA", Path(directory)):
            catalog.write_jsonl(Path(directory) / "catalog.jsonl", [paper(), benchmark])
            catalog.write_json(Path(directory) / "task-classes.json", catalog.read_json(catalog.DATA / "task-classes.json"))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                build.validate(types.SimpleNamespace())
        self.assertEqual(paper()["review_status"], "metadata_verified")
        self.assertIn("Uncurated linked paper: arxiv:2404.07972 is the paper of curated github:xlang-ai/osworld; curate it or record a scope decision.", out.getvalue().splitlines())


if __name__ == "__main__":
    unittest.main()
