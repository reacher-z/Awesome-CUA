import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalog
import build

SCHEMA = catalog.read_json(ROOT / "schemas/candidate-review.schema.json")
SOURCE = [{"source_id": "fixture"}]
RECEIPT = {"url": "https://github.com/example/trainer", "sha256": "c" * 64, "retrieved_at": "2026-10-18T09:00:00Z"}


def record(rid, url):
    return {"id": rid, "name": rid, "kind": "tool", "url": url, "review_status": "curated", "scope": "core", "environments": ["web"], "topics": [],
        "evidence": [{"retrieved_at": "2026-10-01T00:00:00Z", "sha256": "a" * 64}], "licenses": dict.fromkeys(("code", "data", "weights", "document")), "details": {}}


def candidate(rid, url):
    return {"id": rid, "url": url, "provider": rid.split(":", 1)[0], "discovered_in": SOURCE}


def out_of_scope(rid="github:example/trainer", url="https://github.com/example/trainer", **changes):
    entry = {"id": rid, "url": url, "decision": "out_of_scope", "reason": "General LLM post-training library; no computer, browser or mobile interface.",
        "reviewed_at": "2026-10-18T10:00:00Z", "evidence": dict(RECEIPT)}
    for key, value in changes.items():
        if value is None:
            entry.pop(key)
        else:
            entry[key] = value
    return entry


def receipt(**changes):
    return {key: value for key, value in {**RECEIPT, **changes}.items() if value is not None}


# Each entry is rejected by both the build and the published schema.
INVALID = {
    "missing reviewed_at": out_of_scope(reviewed_at=None),
    "missing evidence": out_of_scope(evidence=None),
    "receipt without url": out_of_scope(evidence=receipt(url=None)),
    "receipt without sha256": out_of_scope(evidence=receipt(sha256=None)),
    "receipt without retrieved_at": out_of_scope(evidence=receipt(retrieved_at=None)),
    "receipt with an extra field": out_of_scope(evidence=receipt(status=200)),
    "http receipt url": out_of_scope(evidence=receipt(url="http://github.com/example/trainer")),
    "upper-case digest": out_of_scope(evidence=receipt(sha256="C" * 64)),
    "short digest": out_of_scope(evidence=receipt(sha256="c" * 63)),
    "date-only retrieved_at": out_of_scope(evidence=receipt(retrieved_at="2026-10-18")),
    "reviewed_at without offset": out_of_scope(reviewed_at="2026-10-18T10:00:00"),
    "blank reason": out_of_scope(reason="  "),
    "alias target on a scope decision": out_of_scope(target_id="url:indexed"),
    "unknown field": out_of_scope(note="x"),
    "url prefix": {"url_prefix": "https://github.com/example", "decision": "out_of_scope", "reason": "x", "reviewed_at": "2026-10-18T10:00:00Z", "evidence": dict(RECEIPT)},
    "arXiv identity": out_of_scope("arxiv:2401.00001", "https://arxiv.org/abs/2401.00001"),
    "receipt on a non-resource": {**out_of_scope(), "decision": "not_a_resource"},
}


class OutOfScopeCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        for name, value in (("DATA", self.data), ("ROOT", self.root)):
            patcher = mock.patch.object(build, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.rows = [record("url:indexed", "https://example.org/tool")]
        self.candidates = [candidate("url:indexed", "https://example.org/tool"), candidate("github:example/trainer", "https://github.com/example/trainer"),
            candidate("url:badge", "https://badges.example.net/svg"), candidate("url:file", "https://example.org/tool/blob/main/README.md"),
            candidate("url:open", "https://example.org/agent")]
        self.reviews = [out_of_scope(), {"url_prefix": "https://badges.example.net", "decision": "not_a_resource", "reason": "Badge image."},
            {"id": "url:file", "url": "https://example.org/tool/blob/main/README.md", "decision": "alias", "target_id": "url:indexed", "reason": "File in the indexed repository."}]
        self.write("sources.json", [{"id": "fixture", "name": "Fixture", "homepage": "https://example.org/collection"}])

    def write(self, name, value):
        (self.data / name).write_text(json.dumps(value) + "\n" if name.endswith(".json") else "".join(json.dumps(row) + "\n" for row in value))

    def report(self):
        self.write("candidates.jsonl", self.candidates)
        self.write("candidate-reviews.json", self.reviews)
        return build.coverage(self.rows, [], [])

    def test_coverage_counts_out_of_scope_candidates_separately(self):
        report = self.report()
        counts = ("unindexed_candidates", "non_resource_candidates", "alias_candidates", "out_of_scope_candidates")
        self.assertEqual(tuple(report[key] for key in counts), (1, 1, 1, 1))
        source = report["sources"][0]
        self.assertEqual((source["discovered"], source["indexed"], source["set_aside"], source["out_of_scope"], source["unindexed"]), (5, 1, 2, 1, 1))

    def test_without_the_entry_the_candidate_is_unresolved(self):
        self.reviews = self.reviews[1:]
        report = self.report()
        self.assertEqual((report["unindexed_candidates"], report["out_of_scope_candidates"], report["sources"][0]["out_of_scope"]), (2, 0, 0))

    def test_indexing_takes_precedence(self):
        self.rows.append(record("github:example/trainer", "https://github.com/example/trainer"))
        report = self.report()
        self.assertEqual((report["out_of_scope_candidates"], report["unindexed_candidates"], report["sources"][0]["indexed"]), (0, 1, 2))
        self.assertNotIn("github:example/trainer", build.candidate_reviews(self.candidates, {r["id"] for r in self.rows}, set(), {}))

    def test_queue_row_keeps_the_resolution_and_reason(self):
        self.write("candidates.jsonl", self.candidates)
        self.write("candidate-reviews.json", self.reviews)
        with mock.patch.object(build, "source_records", return_value=(self.rows, [], [])), mock.patch.object(build, "validate_records", return_value=[]), \
                mock.patch.object(build, "documents", return_value={}), mock.patch.object(build, "write_sqlite"), mock.patch.object(build, "write_json"), \
                contextlib.redirect_stdout(io.StringIO()):
            build.build(types.SimpleNamespace(check=False))
        queue = {row["id"]: row for row in map(json.loads, (self.data / "review-queue.jsonl").read_text().splitlines())}
        row = queue["github:example/trainer"]
        self.assertEqual((row["resolution"], row["reason"], row["review_status"]), ("out_of_scope", out_of_scope()["reason"], "candidate"))
        self.assertNotIn("alias_of", row)
        self.assertNotIn("evidence", row)
        self.assertNotIn("resolution", queue["url:open"])
        coverage = json.loads((self.data / "coverage.json").read_text())
        self.assertEqual(coverage["out_of_scope_candidates"], 1)

    def test_receipt_may_share_the_review_instant_but_not_follow_it(self):
        self.reviews = [out_of_scope(evidence=receipt(retrieved_at="2026-10-18T10:00:00Z"))]
        self.assertEqual(self.report()["out_of_scope_candidates"], 1)
        self.reviews = [out_of_scope(evidence=receipt(retrieved_at="2026-10-18T10:00:01Z"))]
        with self.assertRaisesRegex(ValueError, "retrieved_at no later than reviewed_at"):
            self.report()

    def test_build_rejects_incomplete_or_misplaced_decisions(self):
        cases = {**INVALID, "URL differs from the candidate": out_of_scope(url="https://github.com/example/other"),
            "duplicate entry": [out_of_scope(), out_of_scope()]}
        for label, entry in cases.items():
            with self.subTest(label):
                self.reviews = entry if isinstance(entry, list) else [entry]
                with self.assertRaises(ValueError):
                    self.report()

    def test_missing_receipt_names_the_identity_and_the_receipt_fields(self):
        self.reviews = [out_of_scope(evidence=None)]
        with self.assertRaisesRegex(ValueError, r"github:example/trainer: an out_of_scope candidate review needs reviewed_at and an evidence receipt \(https url, sha256"):
            self.report()
        self.reviews = [INVALID["arXiv identity"]]
        with self.assertRaisesRegex(ValueError, "data/exclusions.json"):
            self.report()


class OutOfScopeSchemaTests(unittest.TestCase):
    def setUp(self):
        self.validator = jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker())

    def test_schema_accepts_the_committed_ledger_and_a_complete_decision(self):
        jsonschema.Draft202012Validator.check_schema(SCHEMA)
        self.assertEqual(list(self.validator.iter_errors(catalog.read_json(catalog.DATA / "candidate-reviews.json", []))), [])
        self.assertEqual(list(self.validator.iter_errors([out_of_scope()])), [])

    def test_schema_rejects_what_the_build_rejects(self):
        for label, entry in INVALID.items():
            with self.subTest(label):
                self.assertTrue(list(self.validator.iter_errors([entry])))

    def test_validate_reports_the_schema_error(self):
        osworld = copy.deepcopy(next(r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl") if r["id"] == "arxiv:2404.07972"))
        osworld["relations"] = []
        with tempfile.TemporaryDirectory() as directory:
            catalog.write_jsonl(Path(directory) / "catalog.jsonl", [osworld])
            catalog.write_json(Path(directory) / "candidate-reviews.json", [out_of_scope(evidence=receipt(sha256=None))])
            with mock.patch.object(build, "DATA", Path(directory)), self.assertRaises(ValueError) as raised:
                build.validate(types.SimpleNamespace())
        self.assertIn("Candidate reviews: 'sha256' is a required property", str(raised.exception).splitlines())


class OutOfScopeReportingTests(unittest.TestCase):
    report = {"total_records": 10, "curated_records": 4, "bibliographic_records": 3, "sources": [{}] * 2, "as_of_utc": "2026-10-18T00:00:00Z",
        "metadata_only_records": 6, "unindexed_candidates": 11, "non_resource_candidates": 5, "alias_candidates": 2, "out_of_scope_candidates": 13, "excluded_records": 1}

    def test_readme_stats_name_the_out_of_scope_count_in_both_languages(self):
        self.assertIn("not counting 7 links reviewed as non-resources or other addresses of indexed resources and 13 resources reviewed as outside the computer-use scope", build.stats_block(self.report))
        self.assertIn("13 个资源经审阅确认不属于计算机使用智能体范围", build.stats_block(self.report, "zh"))

    def test_coverage_ledger_has_an_out_of_scope_column(self):
        ledger = (ROOT / "docs/coverage.md").read_text(encoding="utf-8")
        self.assertIn("| Source | Discovered | Indexed | Curated | Excluded | Set aside | Out of scope | Unresolved | Fetch |", ledger)
        self.assertIn("resources reviewed as outside the computer-use scope", ledger)


if __name__ == "__main__":
    unittest.main()
