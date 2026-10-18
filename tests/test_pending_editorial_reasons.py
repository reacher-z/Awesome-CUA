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
DEAD = {"github:thudm/autoglm": "THUDM/AutoGLM", "url:932ab3ba304c8564bb9f": "403", "github:agiresearch/litecua": "Cerebrum"}


def entry(name, **extra):
    return {"name": name, "kind": "agent", "url": f"https://github.com/example/{name}", "summary": f"{name} summary.",
        "environments": ["web"], "topics": [], "editorial_reviewed": False, **extra}


def receipt(name, **extra):
    return {"id": f"github:example/{name.lower()}", "url": f"https://github.com/example/{name}", "retrieved_at": "2026-10-01T00:00:00Z", **extra}


class PendingEditorialReasonTests(unittest.TestCase):
    def pending(self, entries, evidence):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(build, "DATA", Path(directory)):
            data = Path(directory)
            (data / "editorial.json").write_text(json.dumps(entries))
            (data / "primary-evidence.jsonl").write_text("".join(json.dumps(row) + "\n" for row in evidence))
            for name in ("enrichment.jsonl", "papers.jsonl", "publications.jsonl", "metadata-updates.jsonl"):
                (data / name).write_text("")
            rows, pending = build.source_records()
        self.assertEqual(rows, [])
        return {row["name"]: (row["reason"], row["cause"]) for row in pending}

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
        self.assertEqual(build.pending_breakdown(pending), "3 proposals: 1 with unresolved primary evidence, 0 whose current source snapshot awaits review, "
            "2 held by a reviewer after reading the current source, and 0 awaiting another scope review.")

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
