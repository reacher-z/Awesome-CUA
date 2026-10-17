import contextlib
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
import urllib.parse
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog
from test_arxiv_metadata import entry, feed

AGENT = {"id": "github:o/agent", "review_status": "curated"}
BENCH = {"id": "github:o/bench", "review_status": "curated"}
PENDING = {"id": "arxiv:2401.00001", "review_status": "metadata_verified"}
OLD, NEW = "2026-10-15T00:00:00Z", "2026-10-16T00:00:00Z"


def cite(source, target, at=NEW, relation="mentions"):
    url = "https://github.com/" + source.split(":", 1)[1] if source.startswith("github:") else "https://arxiv.org/abs/" + source.split(":", 1)[1]
    target_url = "https://arxiv.org/abs/" + target.split(":", 1)[1] if target.startswith("arxiv:") else "https://github.com/" + target.split(":", 1)[1]
    return {"id": hashlib.sha256((source + "\0" + target).encode()).hexdigest()[:24], "source_id": source, "target_id": target,
            "target_url": target_url, "relation": relation, "source_url": url, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "retrieved_at": at, "target_in_catalog": False}


class ReferenceCandidateTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(mock.patch.object(catalog, "DATA", self.path))
        self.enterContext(mock.patch.object(catalog, "fetch", side_effect=self.fetch))
        self.enterContext(mock.patch("time.sleep"))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.requests, self.responses = [], []
        catalog.write_json(self.path / "sources.json", [])
        catalog.write_jsonl(self.path / "catalog.jsonl", [AGENT, BENCH, PENDING])
        catalog.write_jsonl(self.path / "candidates.jsonl", [{"id": "arxiv:2502.13130", "url": "https://arxiv.org/abs/2502.13130", "provider": "arxiv",
            "first_discovered_at": "2026-10-01T00:00:00Z", "discovered_in": [{"source_id": "hf-search-web", "line": None, "section": "web agents", "snapshot_sha256": "a" * 64}]}])

    def fetch(self, url, refresh=False):
        self.requests.append(url)
        self.assertTrue(self.responses, "Unexpected network request: " + url)
        body = self.responses.pop(0)
        return {"url": url, "ok": True, "status": 200, "sha256": hashlib.sha256(body).hexdigest(), "retrieved_at": "2026-10-17T00:00:00Z"}, body

    def discover(self, references):
        catalog.write_jsonl(self.path / "references.jsonl", references)
        catalog.discover(types.SimpleNamespace(refresh=True, limit=0))
        return {row["id"]: row for row in catalog.read_jsonl(self.path / "candidates.jsonl")}

    def cited(self, row):
        return [(o["section"], o["evidence"]["url"]) for o in row["discovered_in"] if o["source_id"] == "curated-references"]

    def test_arxiv_papers_cited_by_curated_sources_join_the_discovery_population(self):
        refs = [cite(AGENT["id"], "arxiv:2506.21506"), cite(BENCH["id"], "arxiv:2506.21506", at=OLD), cite(AGENT["id"], "arxiv:2502.13130"),
                cite(AGENT["id"], "github:x/tool"), cite(PENDING["id"], "arxiv:2311.12022"), cite("github:o/gone", "arxiv:2206.04615")]
        candidates = self.discover(refs)
        # Only arXiv targets cited by a curated record enter, and reading the committed references makes no request.
        self.assertEqual(self.requests, [])
        self.assertEqual(sorted(candidates), ["arxiv:2502.13130", "arxiv:2506.21506"])
        new = candidates["arxiv:2506.21506"]
        self.assertEqual({key: new[key] for key in ("url", "provider", "first_discovered_at")}, {"url": "https://arxiv.org/abs/2506.21506", "provider": "arxiv", "first_discovered_at": OLD})
        self.assertEqual(self.cited(new), [("Cited by github:o/agent; relevance awaits review", "https://github.com/o/agent"),
                                           ("Cited by github:o/bench; relevance awaits review", "https://github.com/o/bench")])
        occurrence = new["discovered_in"][0]
        evidence = {"url": "https://github.com/o/agent", "sha256": refs[0]["source_sha256"], "retrieved_at": NEW}
        self.assertEqual((occurrence["evidence"], occurrence["snapshot_sha256"], occurrence["line"]), (evidence, evidence["sha256"], None))
        self.assertEqual(occurrence["receipt_id"], catalog.discovery_occurrence("curated-references", evidence)["receipt_id"])
        # A known candidate gains the provenance without losing its earlier discovery.
        known = candidates["arxiv:2502.13130"]
        self.assertEqual([o["source_id"] for o in known["discovered_in"]], ["curated-references", "hf-search-web"])
        self.assertEqual(known["first_discovered_at"], "2026-10-01T00:00:00Z")

    def test_a_rerun_replaces_only_the_reference_occurrences(self):
        self.discover([cite(AGENT["id"], "arxiv:2506.21506"), cite(AGENT["id"], "arxiv:2502.13130")])
        candidates = self.discover([cite(BENCH["id"], "arxiv:2506.21506")])
        # A citation that is gone keeps its candidate row and other provenance but no longer counts as cited.
        self.assertEqual(self.cited(candidates["arxiv:2502.13130"]), [])
        self.assertEqual([o["source_id"] for o in candidates["arxiv:2502.13130"]["discovered_in"]], ["hf-search-web"])
        self.assertEqual(self.cited(candidates["arxiv:2506.21506"]), [("Cited by github:o/bench; relevance awaits review", "https://github.com/o/bench")])

    def test_harvest_verifies_a_cited_paper_as_metadata_only(self):
        self.discover([cite(AGENT["id"], "arxiv:2506.21506")])
        catalog.write_jsonl(self.path / "papers.jsonl", [{"id": "arxiv:2502.13130", "name": "Known"}])
        self.responses = [feed([entry(aid="2506.21506")], total=1)]
        catalog.harvest(types.SimpleNamespace(refresh=False, limit=500))
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.requests[0]).query)
        self.assertEqual((len(self.requests), query["id_list"]), (1, ["2506.21506"]))
        record = {row["id"]: row for row in catalog.read_jsonl(self.path / "papers.jsonl")}["arxiv:2506.21506"]
        self.assertEqual((record["review_status"], record["summary"], record["topics"]), ("metadata_verified", None, []))
        self.assertEqual(catalog.read_jsonl(self.path / "harvest-failures.jsonl"), [])


if __name__ == "__main__":
    unittest.main()
