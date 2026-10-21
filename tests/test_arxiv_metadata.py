import contextlib
import copy
import datetime as dt
import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock
import urllib.parse
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import arxiv_metadata
import build
import catalog
import scan
from scope_review import metadata_fingerprint


ATOM = "{http://www.w3.org/2005/Atom}"
OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
RETRIEVED = "2026-10-17T12:00:00Z"


def entry(aid="2610.00001", version=1, published="2026-10-04T10:00:00Z",
          updated="2026-10-04T10:00:00Z", abstract="A GUI agent performs browser tasks."):
    root = ET.Element(ATOM + "entry")
    fields = {"id": f"http://arxiv.org/abs/{aid}v{version}", "title": "GUI Agent Test",
              "published": published, "updated": updated, "summary": abstract}
    for name, value in fields.items():
        if value is not None:
            ET.SubElement(root, ATOM + name).text = value
    ET.SubElement(ET.SubElement(root, ATOM + "author"), ATOM + "name").text = "Researcher"
    return root


def feed(entries=(), total=0):
    root = ET.Element(ATOM + "feed")
    if total is not None:
        ET.SubElement(root, OPENSEARCH + "totalResults").text = str(total)
    root.extend(entries)
    return ET.tostring(root, encoding="utf-8")


def paper(**kwargs):
    element = entry(**kwargs)
    body = feed([element], total=1)
    return catalog.arxiv_entry(element, {
        "url": "https://export.arxiv.org/api/query?id_list=2610.00001",
        "retrieved_at": "2026-10-16T06:00:00Z", "sha256": hashlib.sha256(body).hexdigest(),
    })


class FrozenDateTime(dt.datetime):
    current = dt.datetime(2026, 10, 17, 12, tzinfo=dt.timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.current.astimezone(tz) if tz else cls.current.replace(tzinfo=None)


class SnapshotTests(unittest.TestCase):
    def test_entry_retains_exact_utc_facts_without_storing_abstract(self):
        abstract = "GUI agents\n  read café screens."
        row = paper(version=3, published="2026-10-02T23:30:00-02:00",
                    updated="2026-10-04T10:00:00.5Z", abstract=abstract)
        snapshot = row["details"]["arxiv_snapshot"]
        self.assertEqual(snapshot["version"], 3)
        self.assertEqual(snapshot["versioned_url"], "https://arxiv.org/abs/2610.00001v3")
        self.assertEqual(snapshot["submitted_at"], "2026-10-03T01:30:00Z")
        self.assertEqual(snapshot["updated_at"], "2026-10-04T10:00:00.500000Z")
        self.assertEqual(snapshot["abstract_sha256"], hashlib.sha256("GUI agents read café screens.".encode()).hexdigest())
        self.assertEqual(snapshot["abstract_hash_method"], arxiv_metadata.ABSTRACT_HASH_METHOD)
        self.assertIsNone(row["summary"])
        self.assertNotIn("abstract", snapshot)
        self.assertIn("details.arxiv_snapshot", row["evidence"][0]["supports"])

    def test_same_day_version_and_same_date_abstract_changes_are_queued(self):
        old = paper()
        cases = [
            (paper(version=2, updated="2026-10-04T12:00:00Z"), "version"),
            (paper(abstract="A different GUI method."), "abstract_sha256"),
        ]
        for observed, field in cases:
            with self.subTest(field=field):
                records, proposals = {old["id"]: copy.deepcopy(old)}, {}
                arxiv_metadata.consider_paper(observed, records, proposals, RETRIEVED)
                self.assertEqual(records[old["id"]], old)
                self.assertEqual(proposals[old["id"]]["review_status"], "metadata_change_pending")
                self.assertIn("details.arxiv_snapshot." + field, proposals[old["id"]]["changes"])
                self.assertEqual(proposals[old["id"]]["evidence"], observed["evidence"])

    def test_batch_digest_and_abstract_whitespace_do_not_create_changes(self):
        old = paper()
        different_batch = copy.deepcopy(old)
        different_batch["evidence"][0]["sha256"] = "f" * 64
        for observed in [different_batch, paper(abstract="A GUI agent\n performs   browser tasks.")]:
            records, proposals = {old["id"]: copy.deepcopy(old)}, {}
            arxiv_metadata.consider_paper(observed, records, proposals, RETRIEVED)
            self.assertEqual(proposals, {})
            self.assertEqual(records[old["id"]], old)

    def test_missing_or_incomplete_snapshots_remain_explicitly_unverified(self):
        full = paper()
        missing = copy.deepcopy(full)
        missing["details"] = {}
        incomplete = copy.deepcopy(full)
        incomplete["details"]["arxiv_snapshot"]["abstract_sha256"] = None
        for old, observed in [(missing, full), (missing, missing), (incomplete, incomplete), (full, incomplete)]:
            with self.subTest(old=old["details"], observed=observed["details"]):
                records, proposals = {old["id"]: copy.deepcopy(old)}, {}
                arxiv_metadata.consider_paper(observed, records, proposals, RETRIEVED)
                self.assertEqual(records[old["id"]], old)
                self.assertEqual(proposals[old["id"]]["review_status"], "metadata_revalidation_pending")
                self.assertIn(proposals[old["id"]]["reason"], {
                    "snapshot_baseline_requires_review", "observed_snapshot_missing", "observed_snapshot_incomplete"})

    def test_hashes_with_different_or_unsupported_methods_require_review(self):
        for observed_method in [arxiv_metadata.ABSTRACT_HASH_METHOD, "sha256-raw-text", None]:
            with self.subTest(observed_method=observed_method):
                old, observed = paper(), paper(abstract="A different GUI method.")
                old["details"]["arxiv_snapshot"]["abstract_hash_method"] = "sha256-raw-text"
                observed["details"]["arxiv_snapshot"]["abstract_hash_method"] = observed_method
                records, proposals = {old["id"]: copy.deepcopy(old)}, {}
                arxiv_metadata.consider_paper(observed, records, proposals, RETRIEVED)
                self.assertEqual(proposals[old["id"]]["review_status"], "metadata_revalidation_pending")
                self.assertEqual(proposals[old["id"]]["reason"], "snapshot_baseline_requires_review")

    def test_equivalent_timestamp_offsets_do_not_report_a_revision(self):
        current = paper()["details"]["arxiv_snapshot"]
        observed = copy.deepcopy(current)
        observed["submitted_at"] = "2026-10-04T12:00:00+02:00"
        observed["updated_at"] = "2026-10-04T12:00:00+02:00"
        self.assertEqual(arxiv_metadata.snapshot_differences(current, observed), ({}, None))

    def test_fractional_timestamp_order_and_supporting_receipt_are_validated(self):
        valid = paper(updated="2026-10-04T10:00:00.5Z")
        self.assertEqual(arxiv_metadata.validate_snapshot(valid), [])
        invalid = paper(published="2026-10-04T10:00:00.5Z", updated="2026-10-04T10:00:00Z")
        self.assertTrue(any("precedes" in error for error in arxiv_metadata.validate_snapshot(invalid)))
        valid["evidence"] = []
        self.assertTrue(any("receipt" in error for error in arxiv_metadata.validate_snapshot(valid)))


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.path = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.responses, self.calls = [], []
        FrozenDateTime.current = dt.datetime(2026, 10, 17, 12, tzinfo=dt.timezone.utc)
        clock = types.SimpleNamespace(datetime=FrozenDateTime, timezone=dt.timezone, timedelta=dt.timedelta)
        for module in (catalog, scan, build):
            self.stack.enter_context(mock.patch.object(module, "DATA", self.path))
        for module in (catalog, scan):
            self.stack.enter_context(mock.patch.object(module, "fetch", side_effect=self.fetch))
            self.stack.enter_context(mock.patch.object(module, "dt", clock))
        self.stack.enter_context(mock.patch("time.sleep"))
        self.stack.enter_context(mock.patch("urllib.request.urlopen", side_effect=AssertionError("Network access forbidden in tests")))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))

    def fetch(self, url, refresh=False):
        self.assertTrue(self.responses, "Unexpected extra API call")
        body = self.responses.pop(0)
        self.calls.append((url, refresh))
        info = {"url": url, "retrieved_at": FrozenDateTime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")}
        if body is None:
            return {**info, "ok": False, "error": "Simulated API failure"}, b""
        return {**info, "ok": True, "sha256": hashlib.sha256(body).hexdigest()}, body

    def seed(self, old=None, protection=None):
        for path in self.path.iterdir():
            path.unlink()
        self.responses.clear()
        self.calls.clear()
        old = copy.deepcopy(old or paper())
        catalog.write_jsonl(self.path / "papers.jsonl", [old])
        catalog.write_jsonl(self.path / "candidates.jsonl", [{
            "id": old["id"], "url": old["url"], "provider": "arxiv", "discovered_in": []}])
        if protection == "curated":
            source = old["evidence"][0]
            catalog.write_json(self.path / "editorial.json", [{
                "name": old["name"], "url": old["url"], "kind": "paper", "summary": "Reviewed GUI research.",
                "environments": ["web"], "topics": ["evaluation"], "editorial_reviewed": True,
                "reviewed_sha256": source["sha256"],
            }])
            catalog.write_jsonl(self.path / "primary-evidence.jsonl", [{"id": old["id"], **source, "content_matched": True}])
        elif protection == "excluded":
            catalog.write_json(self.path / "exclusions.json", [{
                "id": old["id"], "name": old["name"], "url": old["url"], "decision": "out_of_scope",
                "basis": "primary_abstract_review", "reason": "Synthetic exclusion fixture.",
                "reviewed_at": "2026-10-16T07:00:00Z", "metadata_fingerprint": metadata_fingerprint(old),
                "evidence": {key: old["evidence"][0][key] for key in ("url", "sha256", "retrieved_at")},
            }])
        return old

    def ingest(self, name):
        if name == "harvest":
            return catalog.harvest(types.SimpleNamespace(refresh=True, limit=100))
        if name == "search":
            return catalog.search_arxiv(types.SimpleNamespace(refresh=True, limit=100))
        return scan.recent_papers({"recent_lookback_days": 14, "recent_max_results": 100})

    def reusable(self):
        report = catalog.read_json(self.path / "recent-paper-search.json")
        return bool(scan.reusable_recent_snapshot(report, report["query"], report["since_utc"], report["cutoff_utc"], "2026-10-17"))

    def test_all_entrypoints_preserve_curated_snapshots_for_version_and_abstract_changes(self):
        observations = [entry(version=2, updated="2026-10-04T12:00:00Z"), entry(abstract="A different GUI method.")]
        for name in ("harvest", "search", "recent"):
            for observed in observations:
                with self.subTest(entrypoint=name, version=observed.findtext(ATOM + "id")):
                    old = self.seed(protection="curated")
                    self.responses = [feed([observed], total=1)]
                    self.ingest(name)
                    self.assertEqual(catalog.read_jsonl(self.path / "papers.jsonl"), [old])
                    proposal = catalog.read_jsonl(self.path / "metadata-updates.jsonl")[0]
                    self.assertEqual(proposal["review_status"], "metadata_change_pending")
                    self.assertEqual(proposal["evidence"][0]["sha256"], hashlib.sha256(feed([observed], total=1)).hexdigest())
                    rows, _ = build.source_records()
                    self.assertEqual(rows[0]["review_status"], "curated")
                    self.assertEqual(rows[0]["details"]["arxiv_snapshot"], old["details"]["arxiv_snapshot"])

    def test_all_entrypoints_reopen_exclusions_without_replacing_raw_records(self):
        for name in ("harvest", "search", "recent"):
            with self.subTest(entrypoint=name):
                old = self.seed(protection="excluded")
                self.responses = [feed([entry(version=2)], total=1)]
                self.ingest(name)
                self.assertEqual(catalog.read_jsonl(self.path / "papers.jsonl"), [old])
                rows, pending, decisions = build.source_records(with_scope=True)
                self.assertEqual(decisions[0]["status"], "revalidation_pending")
                self.assertEqual(rows[0]["review_status"], "metadata_verified")
                self.assertEqual(rows[0]["details"]["arxiv_snapshot"], old["details"]["arxiv_snapshot"])
                self.assertEqual(len(pending), 1)

    def test_all_entrypoints_queue_missing_baselines_without_adopting_them(self):
        for name in ("harvest", "search", "recent"):
            with self.subTest(entrypoint=name):
                old = paper()
                old["details"] = {}
                self.seed(old)
                self.responses = [feed([entry()], total=1)]
                self.ingest(name)
                self.assertEqual(catalog.read_jsonl(self.path / "papers.jsonl"), [old])
                proposal = catalog.read_jsonl(self.path / "metadata-updates.jsonl")[0]
                self.assertEqual(proposal["review_status"], "metadata_revalidation_pending")
                self.assertEqual(proposal["reason"], "snapshot_baseline_requires_review")

    def test_successful_zero_result_query_reuses_only_the_same_utc_cycle(self):
        self.responses = [feed(total=0)]
        first = self.ingest("recent")
        self.assertTrue(first["ok"] and first["complete"])
        self.assertTrue(self.reusable())
        second = self.ingest("recent")
        self.assertTrue(second["cache_used"])
        self.assertEqual(second["source_retrieved_at"], RETRIEVED)
        self.assertEqual(len(self.calls), 1)
        FrozenDateTime.current = dt.datetime(2026, 10, 18, 12, tzinfo=dt.timezone.utc)
        self.responses = [feed(total=0)]
        third = self.ingest("recent")
        self.assertFalse(third["cache_used"])
        self.assertEqual(len(self.calls), 2)
        report = catalog.read_json(self.path / "recent-paper-search.json")
        self.assertEqual((report["since_utc"], report["cutoff_utc"]), ("202610040000", "202610180000"))

    def test_successful_zero_result_full_search_remains_complete(self):
        self.responses = [feed(total=0)]
        self.ingest("search")
        report = catalog.read_json(self.path / "arxiv-search.json")
        self.assertEqual(report["reported_total"], 0)
        self.assertEqual(report["unique_returned"], 0)
        self.assertTrue(report["complete"])

    def test_expanded_recent_query_replaces_same_day_narrow_cache_without_approval(self):
        narrow = (
            'ti:"computer use"', 'ti:"computer-use"', 'ti:"GUI agent"',
            'ti:"GUI agents"', 'ti:"GUI grounding"', 'ti:"web agent"',
            'ti:"browser agent"',
        )
        self.responses = [feed(total=0)]
        with mock.patch.object(scan, "RECENT_ARXIV_TERMS", narrow):
            self.assertTrue(self.ingest("recent")["complete"])
        old_query = catalog.read_json(self.path / "recent-paper-search.json")["query"]
        observed = entry(aid="2610.00002", abstract="A memory method for GUI agents.")
        observed.find(ATOM + "title").text = "Recursive History Compression"
        self.responses = [feed([observed], total=1)]
        result = self.ingest("recent")
        self.assertFalse(result["cache_used"])
        self.assertTrue(result["complete"])
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.calls[-1][0]).query)["search_query"][0]
        self.assertNotEqual(query, old_query)
        self.assertIn('abs:"GUI agents"', query)
        self.assertIn('abs:"web navigation"', query)
        self.assertIn('abs:AndroidWorld', query)
        self.assertIn('abs:Mind2Web', query)
        self.assertIn('ti:GUI', query)
        self.assertIn('ti:"Android agent"', query)
        self.assertIn("submittedDate:[202610030000 TO 202610170000]", query)
        row = catalog.read_jsonl(self.path / "papers.jsonl")[0]
        self.assertEqual(row["review_status"], "metadata_verified")
        self.assertIsNone(row["summary"])
        self.assertEqual(row["topics"], [])
        occurrence = catalog.read_jsonl(self.path / "candidates.jsonl")[0]["discovered_in"][0]
        self.assertIn("title and abstract", occurrence["section"])
        self.assertTrue(self.ingest("recent")["cache_used"])
        self.assertEqual(len(self.calls), 2)

    def test_both_searches_reject_false_empty_successes(self):
        error = ET.Element(ATOM + "entry")
        ET.SubElement(error, ATOM + "id").text = "http://arxiv.org/api/errors#bad_query"
        bodies = [b"<html><body>Unavailable</body></html>", feed(total=None), feed(total=-1), feed([error], total=1)]
        for name in ("search", "recent"):
            for body in bodies:
                with self.subTest(entrypoint=name, response=body[:80]):
                    old = self.seed()
                    self.responses = [body]
                    self.ingest(name)
                    path = "arxiv-search.json" if name == "search" else "recent-paper-search.json"
                    report = catalog.read_json(self.path / path)
                    self.assertFalse(report["complete"])
                    self.assertFalse(report["pages"][0]["ok"])
                    self.assertEqual(catalog.read_jsonl(self.path / "papers.jsonl"), [old])
                    if name == "recent":
                        self.assertFalse(self.reusable())

    def test_both_searches_keep_partial_or_changed_populations_incomplete(self):
        for name in ("search", "recent"):
            for second in (None, feed(total=1), feed(total=2), feed([entry()], total=2)):
                with self.subTest(entrypoint=name, second=second):
                    self.seed()
                    self.responses = [feed([entry()], total=2), second]
                    self.ingest(name)
                    report = catalog.read_json(self.path / ("arxiv-search.json" if name == "search" else "recent-paper-search.json"))
                    self.assertFalse(report["complete"])
                    if name == "recent":
                        self.assertFalse(self.reusable())

    def test_recent_window_uses_utc_instants_including_midnight_boundaries(self):
        timestamps = {
            "2610.00001": "2026-10-03T00:59:59+01:00",  # Before the UTC lower bound.
            "2610.00002": "2026-10-02T22:00:00-02:00",  # Exactly the lower bound.
            "2610.00003": "2026-10-02T23:30:00-02:00",  # Inside, despite the displayed date.
            "2610.00004": "2026-10-17T02:00:00+02:00",  # Exactly the midnight cutoff.
            "2610.00005": "2026-10-17T11:00:00Z",       # Same day, beyond the cutoff.
            "2610.00006": "2026-10-18T00:00:00Z",       # Future day.
        }
        entries = [entry(aid=aid, published=value, updated=value) for aid, value in timestamps.items()]
        entries.append(entry(aid="2610.00007", published="2026-09-01T10:00:00Z", updated="2026-10-16T10:00:00Z"))
        self.responses = [feed(entries, total=7)]
        result = self.ingest("recent")
        self.assertEqual({row["id"] for row in catalog.read_jsonl(self.path / "papers.jsonl")},
                         {"arxiv:2610.00002", "arxiv:2610.00003", "arxiv:2610.00004"})
        self.assertFalse(result["complete"])
        self.assertFalse(self.reusable())

    def test_arxiv_cache_does_not_skip_other_sources_on_repeated_scans(self):
        catalog.write_json(self.path / "scan-config.json", {
            "recent_lookback_days": 14, "recent_max_results": 100, "harvest_limit": 50,
            "history_limit": 5, "timezone": "UTC", "scan_times_local": ["06:00", "18:00"], "policy": "Fixture",
        })
        catalog.write_json(self.path / "discovery-runs.json", [{"id": str(index), "ok": True} for index in range(36)])
        stages = []

        def stage(name, command, timeout=600):
            stages.append((name, command))
            return {"name": name, "ok": True}

        with mock.patch.object(scan, "stage", side_effect=stage), \
                mock.patch.object(scan, "recent_papers", return_value={"name": "recent_arxiv", "ok": True, "complete": True, "cache_used": True}), \
                mock.patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""}):
            self.assertEqual(scan.run_scan(), 0)
            self.assertEqual(scan.run_scan(), 0)
        discovery = [command for name, command in stages if name == "discovery"]
        hub = [command for name, command in stages if name == "huggingface"]
        self.assertEqual(len(discovery), 2)
        self.assertEqual(len(hub), 2)
        self.assertTrue(all("--refresh" in command for command in discovery + hub))
        self.assertEqual(catalog.read_json(self.path / "scan-status.json")["source_fetches"], {"successful": 36, "total": 36})


class CacheReceiptTests(unittest.TestCase):
    def report(self, retrieved=RETRIEVED):
        return {"schema_version": 2, "scan_day_utc": "2026-10-17", "query": "q", "since_utc": "s", "cutoff_utc": "c",
                "reported_total": 0, "unique_returned": 0, "complete": True, "warnings": [],
                "pages": [{"ok": True, "retrieved_at": retrieved, "sha256": "a" * 64}]}

    def reusable(self, report):
        return bool(scan.reusable_recent_snapshot(report, "q", "s", "c", "2026-10-17"))

    def test_receipt_day_is_parsed_as_utc_not_as_a_string_prefix(self):
        cases = [(RETRIEVED, True), ("2026-10-16T23:30:00-02:00", True),
                 ("2026-10-17T00:30:00+02:00", False), ("2026-10-17Tnot-a-time", False),
                 ("2026-10-17T12:00:00", False), (None, False)]
        for retrieved, expected in cases:
            with self.subTest(retrieved=retrieved):
                self.assertEqual(self.reusable(self.report(retrieved)), expected)

    def test_failed_partial_mismatched_and_malformed_reports_are_not_reused(self):
        for key, value in [("schema_version", 1), ("scan_day_utc", "2026-10-16"), ("query", "other"),
                           ("since_utc", "other"), ("cutoff_utc", "other"), ("complete", False),
                           ("reported_total", 1), ("unique_returned", False), ("warnings", ["partial"]),
                           ("pages", []), ("pages", [None])]:
            with self.subTest(key=key, value=value):
                report = self.report()
                report[key] = value
                self.assertFalse(self.reusable(report))
        for key, value in [("ok", False), ("sha256", "not-a-hash")]:
            report = self.report()
            report["pages"][0][key] = value
            self.assertFalse(self.reusable(report))


if __name__ == "__main__":
    unittest.main()
