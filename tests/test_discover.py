import contextlib
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog

LIST = {"id": "list", "name": "List", "url": "https://raw.githubusercontent.com/o/awesome-list/main/README.md", "homepage": "https://github.com/o/awesome-list/"}
OTHER = {"id": "other", "name": "Other", "url": "https://raw.githubusercontent.com/p/other-list/main/README.md", "homepage": "https://github.com/p/other-list"}
README = """# Awesome list
[![Stars](https://img.shields.io/github/stars/o/awesome-list)](https://github.com/o/awesome-list) [tree](https://github.com/O/Awesome-List/tree/main)
## Web *agents*
- [SeeAct](https://github.com/OSU-NLP-Group/SeeAct) ([paper](https://arxiv.org/abs/2401.01614v2))
- Mirror: https://github.com/osu-nlp-group/seeact/tree/main and https://arxiv.org/pdf/2401.01614
## Benchmarks
- [OSWorld](https://github.com/xlang-ai/OSWorld) https://twitter.com/osworld https://example.org/logo.png
"""


def sha(body):
    return hashlib.sha256(body).hexdigest()


class DiscoverTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(mock.patch.object(catalog, "DATA", self.path))
        self.enterContext(mock.patch.object(catalog, "fetch", side_effect=self.fetch))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        catalog.write_json(self.path / "sources.json", [LIST, OTHER])
        self.bodies = {OTHER["url"]: b"## Mentions\n- https://github.com/xlang-ai/OSWorld\n"}
        self.requests = []

    def fetch(self, url, refresh=False):
        self.requests.append((url, refresh))
        body = self.bodies[url]
        if body is None:
            return {"url": url, "ok": False, "status": 503, "error": "HTTP 503", "retrieved_at": self.at}, b""
        return {"url": url, "ok": True, "status": 200, "sha256": sha(body), "retrieved_at": self.at}, body

    def discover(self, body, at):
        self.bodies[LIST["url"]], self.at = body, at
        catalog.discover(types.SimpleNamespace(refresh=True, limit=0))
        runs = {run["id"]: run for run in catalog.read_json(self.path / "discovery-runs.json")}
        return {row["id"]: row for row in catalog.read_jsonl(self.path / "candidates.jsonl")}, runs

    def occurrences(self, candidates, source_id):
        return {rid: [o for o in row["discovered_in"] if o["source_id"] == source_id] for rid, row in candidates.items()}

    def test_links_are_filtered_deduplicated_and_located(self):
        candidates, runs = self.discover(README.encode(), "2026-10-17T00:00:00Z")
        self.assertEqual(self.requests, [(LIST["url"], True), (OTHER["url"], True)])
        # The homepage self-link (in any spelling), the badge image, the image file, twitter and the second SeeAct/arXiv links are not candidates.
        self.assertEqual(sorted(candidates), ["arxiv:2401.01614", "github:osu-nlp-group/seeact", "github:xlang-ai/osworld"])
        found = {rid: [(o["line"], o["section"]) for o in occurrences] for rid, occurrences in self.occurrences(candidates, "list").items()}
        self.assertEqual(found, {"github:osu-nlp-group/seeact": [(4, "Web agents")], "arxiv:2401.01614": [(4, "Web agents")], "github:xlang-ai/osworld": [(7, "Benchmarks")]})
        evidence = {"url": LIST["url"], "sha256": sha(README.encode()), "retrieved_at": "2026-10-17T00:00:00Z"}
        occurrence = candidates["arxiv:2401.01614"]["discovered_in"][0]
        self.assertEqual(occurrence["evidence"], evidence)
        self.assertEqual(occurrence["snapshot_sha256"], evidence["sha256"])
        self.assertEqual(occurrence["receipt_id"], catalog.discovery_occurrence("list", evidence)["receipt_id"])
        self.assertEqual({key: candidates["arxiv:2401.01614"][key] for key in ("url", "provider", "first_discovered_at")},
            {"url": "https://arxiv.org/abs/2401.01614", "provider": "arxiv", "first_discovered_at": "2026-10-17T00:00:00Z"})
        self.assertEqual([o["source_id"] for o in candidates["github:xlang-ai/osworld"]["discovered_in"]], ["list", "other"])
        self.assertEqual({key: runs["list"][key] for key in ("ok", "state", "unique_resources", "request_attempted", "provider_host", "sha256")},
            {"ok": True, "state": "success", "unique_resources": 3, "request_attempted": True, "provider_host": "raw.githubusercontent.com", "sha256": sha(README.encode())})
        self.assertEqual((runs["other"]["state"], runs["other"]["unique_resources"]), ("success", 1))

    def test_refresh_replaces_only_that_sources_occurrences(self):
        self.discover(README.encode(), "2026-10-17T00:00:00Z")
        removed = README.replace("- [OSWorld](https://github.com/xlang-ai/OSWorld) https://twitter.com/osworld https://example.org/logo.png\n", "")
        candidates, runs = self.discover(removed.encode(), "2026-10-18T00:00:00Z")
        # A deleted link keeps its candidate row and other sources' occurrences, but no longer counts for this source.
        osworld = candidates["github:xlang-ai/osworld"]
        self.assertEqual([o["source_id"] for o in osworld["discovered_in"]], ["other"])
        self.assertEqual(osworld["first_discovered_at"], "2026-10-17T00:00:00Z")
        self.assertEqual(runs["list"]["unique_resources"], 2)
        refreshed = candidates["arxiv:2401.01614"]["discovered_in"]
        self.assertEqual(len(refreshed), 1)
        self.assertEqual((refreshed[0]["evidence"]["retrieved_at"], refreshed[0]["evidence"]["sha256"]), ("2026-10-18T00:00:00Z", sha(removed.encode())))
        self.assertEqual(candidates["arxiv:2401.01614"]["first_discovered_at"], "2026-10-17T00:00:00Z")

    def test_failed_fetch_records_the_failure_and_keeps_prior_occurrences(self):
        before, _ = self.discover(README.encode(), "2026-10-17T00:00:00Z")
        candidates, runs = self.discover(None, "2026-10-18T00:00:00Z")
        self.assertEqual({key: runs["list"][key] for key in ("ok", "state", "unique_resources", "request_attempted", "status", "error", "retrieved_at")},
            {"ok": False, "state": "failed", "unique_resources": 0, "request_attempted": True, "status": 503, "error": "HTTP 503", "retrieved_at": "2026-10-18T00:00:00Z"})
        self.assertNotIn("sha256", runs["list"])
        self.assertEqual(self.occurrences(candidates, "list"), self.occurrences(before, "list"))
        self.assertEqual(runs["other"]["state"], "success")
        self.assertEqual(candidates["github:xlang-ai/osworld"]["discovered_in"][1]["evidence"]["retrieved_at"], "2026-10-18T00:00:00Z")

    def test_retired_source_is_not_requested_and_keeps_its_last_snapshot_provenance(self):
        before, _ = self.discover(README.encode(), "2026-10-17T00:00:00Z")
        retired = {**LIST, "retired": {"date": "2026-10-18", "reason": "The upstream document now returns HTTP 404 for every request."}}
        catalog.write_json(self.path / "sources.json", [retired, OTHER])
        self.requests.clear()
        candidates, runs = self.discover(None, "2026-10-18T00:00:00Z")
        self.assertEqual(self.requests, [(OTHER["url"], True)])
        self.assertEqual({key: runs["list"][key] for key in ("ok", "state", "retired_on", "request_attempted", "unique_resources", "error")},
            {"ok": False, "state": "retired", "retired_on": "2026-10-18", "request_attempted": False, "unique_resources": 0,
             "error": "Retired source: The upstream document now returns HTTP 404 for every request."})
        self.assertEqual(self.occurrences(candidates, "list"), self.occurrences(before, "list"))
        self.assertEqual(runs["other"]["state"], "success")

    def test_registry_rejects_an_undocumented_retirement(self):
        import build
        ok = {**LIST, "retired": {"date": "2026-10-18", "reason": "The upstream document now returns HTTP 404 for every request."}}
        self.assertEqual(build.validate_sources([ok]), [])
        for retired in [True, {"date": "2026-10-18"}, {"date": "18 Oct 2026", "reason": ok["retired"]["reason"]},
                        {"date": "2026-10-18", "reason": "gone"}, {**ok["retired"], "by": "someone"}]:
            with self.subTest(retired=retired):
                self.assertEqual(build.validate_sources([{**LIST, "retired": retired}]),
                                 ["list: a retired discovery source needs exactly an ISO 'date' and a documented 'reason'"])


if __name__ == "__main__":
    unittest.main()
