import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build
from catalog import editorial_identity

NOTE = "The repository path returns 404 with no redirect; the paper is cataloged separately."
# Unapproved proposals whose primary source cannot be fetched; each needs a recorded decision.
DEAD = {"github:thudm/autoglm": "THUDM/AutoGLM", "url:df3dc96d9e27b824f6ea": "403", "github:agiresearch/litecua": "Cerebrum"}


def entry(name, **extra):
    return {"name": name, "kind": "agent", "url": f"https://github.com/example/{name}", "summary": f"{name} summary.",
        "environments": ["web"], "topics": [], "editorial_reviewed": False, **extra}


def receipt(name, **extra):
    return {"id": f"github:example/{name.lower()}", "url": f"https://github.com/example/{name}", "retrieved_at": "2026-10-01T00:00:00Z", **extra}


def paper(number, **extra):
    return {"name": f"Paper {number}", "kind": "paper", "url": f"https://arxiv.org/abs/2601.0000{number}", "editorial_reviewed": False, **extra}


def archived(number):
    return {"id": f"arxiv:2601.0000{number}", "name": f"Paper {number}", "kind": "paper", "url": f"https://arxiv.org/abs/2601.0000{number}",
        "aliases": [], "environments": ["unspecified"], "topics": [], "summary": None, "review_status": "metadata_verified",
        "published_at": "2026-01-01", "updated_at": "2026-01-01", "authors": [], "identifiers": {"arxiv": f"2601.0000{number}"},
        "details": {}, "links": [], "relations": [], "licenses": {"code": None, "data": None, "weights": None, "document": None},
        "evidence": [], "last_verified_at": "2026-01-01T00:00:00Z", "notes": ""}


class PendingEditorialReasonTests(unittest.TestCase):
    def pending(self, entries, evidence, papers=()):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(build, "DATA", Path(directory)):
            data = Path(directory)
            (data / "editorial.json").write_text(json.dumps(entries))
            (data / "primary-evidence.jsonl").write_text("".join(json.dumps(row) + "\n" for row in evidence))
            for name in ("enrichment.jsonl", "publications.jsonl", "metadata-updates.jsonl"):
                (data / name).write_text("")
            (data / "papers.jsonl").write_text("".join(json.dumps(row) + "\n" for row in papers))
            rows, pending = build.source_records()
        self.assertEqual([row["review_status"] for row in rows], ["metadata_verified"] * len(papers))
        return {row["name"]: (row["reason"], row["cause"]) for row in pending}

    def test_a_screened_paper_awaits_an_annotation_instead_of_a_scope_decision(self):
        receipts = [{"id": f"arxiv:2601.0000{n}", "url": "https://export.arxiv.org/api/query?id_list=x", "retrieved_at": "2026-10-01T00:00:00Z",
            "content_matched": True, "sha256": "a" * 64} for n in (1, 2, 3, 4)]
        pending = self.pending([
            paper(1, relevance_screen="core", review_note="The abstract trains a web agent.", reviewed_sha256="a" * 64),
            paper(2, relevance_screen="adjacent", scope="adjacent", review_note="The abstract evaluates on WebShop.", reviewed_sha256="a" * 64),
            paper(3, review_note="The abstract does not say whether the interface is graphical.", reviewed_sha256="a" * 64),
            paper(4, relevance_screen="core", review_note="Read another snapshot.", reviewed_sha256="b" * 64)],
            receipts, [archived(n) for n in (1, 2, 3, 4)])
        self.assertEqual(pending["Paper 1"], ("The abstract trains a web agent.", "annotation_pending"))
        self.assertEqual(pending["Paper 2"], ("The abstract evaluates on WebShop.", "annotation_pending"))
        self.assertEqual(pending["Paper 3"], ("The abstract does not say whether the interface is graphical.", "reviewer_hold"))
        self.assertEqual(pending["Paper 4"], ("current source snapshot needs editorial review", "unreviewed_snapshot"))

    def test_invalid_or_contradictory_screens_and_duplicate_entries_stop_the_build(self):
        receipt = [{"id": "arxiv:2601.00001", "url": "https://export.arxiv.org/api/query?id_list=x", "retrieved_at": "2026-10-01T00:00:00Z",
            "content_matched": True, "sha256": "a" * 64}]
        for entries, message in (([paper(1, relevance_screen="out_of_scope")], "relevance_screen must be core or adjacent"),
                                 ([paper(1, relevance_screen="core", scope="adjacent")], "keeps the scope its relevance_screen proposes"),
                                 ([entry("Tool", relevance_screen="core")], "relevance_screen must be core or adjacent"),
                                 ([paper(1), paper(1, review_note="again")], "Duplicate editorial entry: arxiv:2601.00001")):
            with self.subTest(message), self.assertRaisesRegex(ValueError, message):
                self.pending(entries, receipt, [archived(1)])

    def test_failed_fetch_keeps_the_reviewer_note_after_the_error(self):
        pending = self.pending([entry("Gone", review_note=NOTE), entry("Blocked")],
            [receipt("Gone", content_matched=False, error="HTTP Error 404: Not Found"), receipt("Blocked", content_matched=False, error="HTTP Error 403: Forbidden")])
        self.assertEqual(pending["Gone"], ("primary evidence unresolved: HTTP Error 404: Not Found; " + NOTE, "unresolved_evidence"))
        self.assertEqual(pending["Blocked"], ("primary evidence unresolved: HTTP Error 403: Forbidden", "unresolved_evidence"))

    def test_a_note_for_another_snapshot_is_not_shown_and_a_current_one_is(self):
        pending = self.pending([entry("Changed", review_note=NOTE, reviewed_sha256="b" * 64), entry("Held", review_note=NOTE, reviewed_sha256="a" * 64)],
            [receipt("Changed", content_matched=True, sha256="a" * 64), receipt("Held", content_matched=True, sha256="a" * 64)])
        self.assertEqual(pending["Changed"], ("current source snapshot needs editorial review", "unreviewed_snapshot"))
        self.assertEqual(pending["Held"], (NOTE, "reviewer_hold"))

    def test_breakdown_counts_every_cause(self):
        pending = [{"cause": "unresolved_evidence"}, {"cause": "reviewer_hold"}, {"cause": "reviewer_hold"}]
        pending.append({"cause": "annotation_pending"})
        self.assertEqual(build.pending_breakdown(pending), "4 proposals: 1 with unresolved primary evidence, 0 whose current source snapshot awaits review, "
            "2 held by a reviewer after reading the current source, 1 screened as relevant from the current source and awaiting an editorial annotation, "
            "and 0 awaiting another scope review.")

    def test_coverage_ledger_states_the_committed_breakdown(self):
        pending = json.loads((ROOT / "data" / "coverage.json").read_text(encoding="utf-8"))["pending_editorial"]
        self.assertIn("\n" + build.pending_breakdown(pending) + "\n", (ROOT / "docs" / "coverage.md").read_text(encoding="utf-8"))

    def test_unreadable_sources_carry_a_recorded_decision(self):
        entries = {(e.get("id") or editorial_identity(e)[0]): e for e in json.loads((ROOT / "data" / "editorial.json").read_text(encoding="utf-8"))}
        for rid, fact in DEAD.items():
            with self.subTest(rid):
                self.assertIs(entries[rid]["editorial_reviewed"], False)
                self.assertIn(fact, entries[rid]["review_note"])


if __name__ == "__main__":
    unittest.main()
