import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build

SOURCE = [{"source_id": "fixture"}]
# Issue #89's examples: badges, local addresses, license and profile pages, a list site, and other addresses of indexed records.
LISTED = ["url:bc04677877723978aa55", "url:db6204c8e3ea8c702b14", "url:dbaf2412f9ca650fb4e6", "url:d9617135d6fdd0a2cde7", "url:65ef38a460c87c37c977",
    "url:7f31f4dc371745e822a6", "url:9432140d59d41c1ef2bd", "url:9c864057b3d88d9d5671", "url:cb4a612ddf3d7a9d778c", "url:f634f9c91acce8064346",
    "url:0a10708d9e6381630590", "url:0a89d3a0f5cfca713697", "url:8a8a446d99c57a071488", "url:8b1d218fe4dc3d1c66c3", "url:4b2046cf6b71eb4ac183",
    "url:60643def1816590a168d", "url:e93fab6deae2e8764bfc", "url:81cca962b2f06d971d01", "url:dc8621e65a7c436e0e5e", "url:644057be347db3e07df4",
    "url:015f1ccf68b10deb933f", "url:516c22c5dba9c1ba70ca", "url:51f11a6608ad5fcb0144", "url:1b973952cbf532111361", "url:4b40edffe1c7b8ebfd23",
    "url:10063d415bf68389a41b", "url:d07857dffca377a06d87", "url:5f93a5192b1aa2f9b7cd", "url:b3ffe248cc4292a5e7f0", "url:5455417a4c0f8a93fccc",
    "url:fef338e4e06ee532de24", "github:mnotgod96/appagent", "github:bytedance/agent-r", "github:eric-ai-lab/screen-point-and-read", "github:gimme1dollar/b-moca"]


def record(rid, url):
    return {"id": rid, "name": rid, "kind": "tool", "url": url, "review_status": "curated", "scope": "core", "environments": ["web"], "topics": [],
        "evidence": [{"retrieved_at": "2026-10-01T00:00:00Z", "sha256": "a" * 64}], "licenses": dict.fromkeys(("code", "data", "weights", "document")), "details": {}}


def candidate(rid, url):
    return {"id": rid, "url": url, "provider": "url", "discovered_in": SOURCE}


class CandidateReviewTests(unittest.TestCase):
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
        self.rows = [record("url:indexed", "https://example.org/tool"), record("url:listed", "https://example.org/list")]
        self.candidates = [candidate("url:indexed", "https://example.org/tool"), candidate("url:listed", "https://example.org/list"),
            candidate("url:badge", "https://badges.example.net/svg?repo=a"), candidate("url:local", "https://127.0.0.1/v1"),
            candidate("url:file", "https://example.org/tool/blob/main/README.md"), candidate("url:open", "https://example.org/agent")]
        self.reviews = [{"url_prefix": "https://badges.example.net", "decision": "not_a_resource", "reason": "Badge image."},
            # A prefix that also covers an indexed record leaves that record indexed.
            {"url_prefix": "https://example.org/list", "decision": "not_a_resource", "reason": "List page."},
            {"id": "url:local", "url": "https://127.0.0.1/v1", "decision": "not_a_resource", "reason": "Local endpoint."},
            {"id": "url:file", "url": "https://example.org/tool/blob/main/README.md", "decision": "alias", "target_id": "url:indexed", "reason": "File in the indexed repository."}]
        self.write("sources.json", [{"id": "fixture", "name": "Fixture", "homepage": "https://example.org/collection"}])

    def write(self, name, value):
        (self.data / name).write_text(json.dumps(value) + "\n" if name.endswith(".json") else "".join(json.dumps(row) + "\n" for row in value))

    def report(self):
        self.write("candidates.jsonl", self.candidates)
        self.write("candidate-reviews.json", self.reviews)
        return build.coverage(self.rows, [], [])

    def test_coverage_subtracts_non_resources_and_aliases(self):
        report = self.report()
        self.assertEqual((report["unindexed_candidates"], report["non_resource_candidates"], report["alias_candidates"]), (1, 2, 1))
        source = report["sources"][0]
        self.assertEqual((source["discovered"], source["indexed"], source["excluded"], source["set_aside"], source["unindexed"]), (6, 2, 0, 3, 1))

    def test_without_a_ledger_every_unindexed_candidate_is_unresolved(self):
        self.reviews = []
        report = self.report()
        self.assertEqual((report["unindexed_candidates"], report["non_resource_candidates"], report["alias_candidates"]), (4, 0, 0))

    def test_queue_keeps_set_aside_links_with_their_reason(self):
        self.write("candidates.jsonl", self.candidates)
        self.write("candidate-reviews.json", self.reviews)
        with mock.patch.object(build, "source_records", return_value=(self.rows, [], [])), mock.patch.object(build, "validate_records", return_value=[]), \
                mock.patch.object(build, "candidate_identity_errors", return_value=[]), \
                mock.patch.object(build, "documents", return_value={}), mock.patch.object(build, "write_sqlite"), mock.patch.object(build, "write_json"), \
                contextlib.redirect_stdout(io.StringIO()):
            build.build(types.SimpleNamespace(check=False))
        queue = {row["id"]: row for row in map(json.loads, (self.data / "review-queue.jsonl").read_text().splitlines())}
        self.assertEqual(sorted(queue), ["url:badge", "url:file", "url:local", "url:open"])
        self.assertNotIn("resolution", queue["url:open"])
        self.assertEqual((queue["url:badge"]["resolution"], queue["url:badge"]["reason"]), ("not_a_resource", "Badge image."))
        self.assertEqual((queue["url:file"]["resolution"], queue["url:file"]["alias_of"]), ("alias", "url:indexed"))
        self.assertEqual({row["review_status"] for row in queue.values()}, {"candidate"})

    def test_invalid_entries_fail_the_build(self):
        cases = {"alias target is not active": {"id": "url:file", "url": "https://example.org/tool/blob/main/README.md", "decision": "alias", "target_id": "url:missing", "reason": "x"},
            "prefix alias": {"url_prefix": "https://example.org/tool", "decision": "alias", "reason": "x"},
            "prefix with a query": {"url_prefix": "https://badges.example.net/svg?repo=a", "decision": "not_a_resource", "reason": "x"},
            "unknown decision": {"id": "url:open", "url": "https://example.org/agent", "decision": "out_of_scope", "reason": "x"},
            "missing reason": {"id": "url:open", "url": "https://example.org/agent", "decision": "not_a_resource", "reason": " "},
            "URL differs from the candidate": {"id": "url:open", "url": "https://example.org/other", "decision": "not_a_resource", "reason": "x"}}
        for label, entry in cases.items():
            with self.subTest(label):
                self.reviews = [entry]
                with self.assertRaises(ValueError):
                    self.report()

    def test_listed_identifiers_no_longer_count_as_unresolved(self):
        queue = [json.loads(line) for line in (ROOT / "data" / "review-queue.jsonl").read_text(encoding="utf-8").splitlines()]
        unresolved = {row["id"] for row in queue if "resolution" not in row}
        migrations = {entry['alias_id']:entry['target_id'] for entry in json.loads((ROOT/'data/url-aliases.json').read_text())}
        self.assertEqual(sorted({migrations.get(rid,rid) for rid in LISTED} & unresolved), [])


if __name__ == "__main__":
    unittest.main()
