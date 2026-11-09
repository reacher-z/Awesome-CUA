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
import build
import catalog
from test_catalog import paper

REPO = "https://github.com/xlang-ai/OSWorld"
RID = "github:xlang-ai/osworld"
PRIMARY = "https://github.com/xlang-ai/OSWorld"
AT = "2026-10-17T00:00:00Z"
RAW = "https://raw.githubusercontent.com/xlang-ai/OSWorld/HEAD/"
README = b"""<html><header><a href="https://github.com/nav/menu">menu</a></header><article class="markdown-body">
<a href="https://arxiv.org/abs/2404.07972v2">paper</a> <a href="https://huggingface.co/papers/2404.07972">HF paper</a>
<a href="https://github.com/xlang-ai/OSWorld/tree/main/docs">docs</a> <a href="https://github.com/xlang-ai/OSWorld-G">grounding</a>
<a href="https://huggingface.co/datasets/xlangai/ubuntu_osworld">VM image</a> <a href="https://github.com/xlang-ai/osworld-g.git">again</a>
<a href="https://twitter.com/osworld">twitter</a> <a href="https://example.org/osworld">site</a> <img src="https://img.shields.io/badge/x-blue">
</article><footer><a href="https://huggingface.co/footer/model">footer</a></footer></html>"""
LICENSES = {
    "MIT": (b"MIT License\n\nCopyright (c) 2024 Example\n", "MIT"),
    "Apache-2.0": (b"                                 Apache License\n                           Version 2.0, January 2004\n", "Apache-2.0"),
    "BSD-3-Clause": (b"BSD 3-Clause License\n\nCopyright (c) 2024 Example\n", "BSD-3-Clause"),
    "BSD-2-Clause": (b"BSD 2-Clause License\n\nCopyright (c) 2024 Example\n", "BSD-2-Clause"),
    "custom": (b"Custom Research License\n\nFor non-commercial evaluation only.\n", None),
}


def sha(body):
    return hashlib.sha256(body).hexdigest()


def response(url, body, status=200):
    if status != 200:
        return {"url": url, "ok": False, "status": status, "error": f"HTTP {status}", "retrieved_at": AT}, b""
    return {"url": url, "ok": True, "status": status, "sha256": sha(body), "retrieved_at": AT}, body


class EnrichGitHubTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(mock.patch.object(catalog, "DATA", self.directory))

    def enrich(self, rows, bodies, licenses):
        """rows: (editorial row, primary URL); bodies: cached primary bodies; licenses: LICENSE URL -> (status, body)."""
        catalog.write_json(self.directory / "editorial.json", [row for row, _ in rows])
        catalog.write_jsonl(self.directory / "primary-evidence.jsonl", [{"id": catalog.canonical(row["url"])[0], "url": primary,
            "content_matched": True, "sha256": sha(bodies[primary]), "retrieved_at": AT} for row, primary in rows])
        self.requests = []

        def fetch(url, refresh=False):
            self.requests.append(url)
            status, body = licenses.get(url, (404, b""))
            return response(url, body, status)
        with mock.patch.object(catalog, "cached_body", side_effect=bodies.__getitem__), mock.patch.object(catalog, "fetch", side_effect=fetch), \
                contextlib.redirect_stdout(io.StringIO()):
            catalog.enrich(types.SimpleNamespace(refresh=False))
        return {row["id"]: row for row in catalog.read_jsonl(self.directory / "enrichment.jsonl")}

    def test_license_headers_map_to_spdx_ids_with_their_receipt(self):
        row = {"url": REPO, "kind": "benchmark", "name": "OSWorld"}
        for label, (body, expected) in LICENSES.items():
            with self.subTest(label):
                result = self.enrich([(row, PRIMARY)], {PRIMARY: README}, {RAW + "LICENSE": (200, body)})[RID]
                # The first LICENSE file that answers decides, even when its text is not recognised.
                self.assertEqual(self.requests, [RAW + "LICENSE"])
                receipts = [e for e in result["evidence"] if e["method"] == "license_header"]
                if expected is None:
                    self.assertNotIn("code", result["licenses"])
                    self.assertEqual(receipts, [])
                    continue
                self.assertEqual(result["licenses"], {"code": {"declared": expected, "url": RAW + "LICENSE", "retrieved_at": AT, "basis": "repository LICENSE header"}})
                self.assertEqual(receipts, [{"role": "primary", "method": "license_header", "supports": ["licenses.code"], "url": RAW + "LICENSE", "sha256": sha(body), "retrieved_at": AT}])

    def test_missing_license_file_falls_through_to_the_next_name(self):
        row = {"url": REPO, "kind": "benchmark", "name": "OSWorld"}
        result = self.enrich([(row, PRIMARY)], {PRIMARY: README}, {RAW + "LICENSE.md": (200, LICENSES["MIT"][0]), RAW + "LICENSE.txt": (200, LICENSES["Apache-2.0"][0])})[RID]
        self.assertEqual(self.requests, [RAW + "LICENSE", RAW + "LICENSE.md"])
        self.assertEqual((result["licenses"]["code"]["declared"], result["licenses"]["code"]["url"]), ("MIT", RAW + "LICENSE.md"))
        result = self.enrich([(row, PRIMARY)], {PRIMARY: README}, {})[RID]
        self.assertEqual(self.requests, [RAW + name for name in catalog.LICENSE_FILES])
        self.assertEqual((result["licenses"], result["evidence"]), ({}, []))

    def test_references_keep_arxiv_github_and_hub_targets_from_the_readme_once(self):
        row = {"url": REPO, "kind": "benchmark", "name": "OSWorld"}
        result = self.enrich([(row, PRIMARY)], {PRIMARY: README}, {})[RID]
        receipt = {"relation": "mentions", "source_url": PRIMARY, "source_sha256": sha(README), "retrieved_at": AT}
        # Navigation and footer links lie outside <article>; the self-link, a repeated identity, twitter, a badge and other sites are dropped.
        self.assertEqual(result["references"], [
            {"target_id": "arxiv:2404.07972", "target_url": "https://arxiv.org/abs/2404.07972", **receipt},
            {"target_id": "github:xlang-ai/osworld-g", "target_url": "https://github.com/xlang-ai/OSWorld-G", **receipt},
            {"target_id": catalog.canonical("https://huggingface.co/datasets/xlangai/ubuntu_osworld")[0], "target_url": "https://huggingface.co/datasets/xlangai/ubuntu_osworld", **receipt},
        ])

    def test_arxiv_sources_yield_no_references(self):
        url = "https://arxiv.org/abs/2404.07972"
        primary = "https://export.arxiv.org/api/query?id_list=2404.07972"
        body = b"<feed><entry>https://github.com/xlang-ai/OSWorld https://arxiv.org/abs/2501.00001</entry></feed>"
        result = self.enrich([({"url": url, "kind": "paper", "name": "OSWorld"}, primary)], {primary: body}, {})["arxiv:2404.07972"]
        self.assertEqual((result["references"], self.requests), ([], []))


class ReferenceEdgeTests(unittest.TestCase):
    def build(self, enrichment):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        data = root / "data"
        data.mkdir()
        self.enterContext(mock.patch.object(build, "ROOT", root))
        self.enterContext(mock.patch.object(build, "DATA", data))
        catalog.write_jsonl(data / "papers.jsonl", [paper()])
        catalog.write_json(data / "editorial.json", [{"name": "OSWorld", "kind": "benchmark", "url": REPO, "environments": ["desktop"], "topics": ["evaluation"],
            "summary": "A desktop benchmark.", "editorial_reviewed": True, "reviewed_sha256": sha(README)}])
        catalog.write_jsonl(data / "primary-evidence.jsonl", [{"id": RID, "url": PRIMARY, "content_matched": True, "sha256": sha(README), "retrieved_at": AT}])
        catalog.write_jsonl(data / "enrichment.jsonl", enrichment)
        with contextlib.redirect_stdout(io.StringIO()):
            build.build(types.SimpleNamespace(check=False))
        return catalog.read_jsonl(data / "references.jsonl")

    def enrichment(self, rid, digest):
        receipt = {"relation": "mentions", "source_url": PRIMARY, "source_sha256": digest, "retrieved_at": AT}
        return {"id": rid, "evidence_sha256": digest, "licenses": {}, "details": {}, "evidence": [], "references": [
            {"target_id": "github:xlang-ai/osworld-g", "target_url": "https://github.com/xlang-ai/OSWorld-G", **receipt},
            {"target_id": "arxiv:2404.07972", "target_url": "https://arxiv.org/abs/2404.07972", **receipt}]}

    def test_edges_need_a_current_receipt_and_mark_catalog_targets(self):
        current = self.enrichment(RID, sha(README))
        edges = self.build([current, self.enrichment("github:not/in-catalog", sha(README))])
        self.assertEqual(edges, sorted([{"id": hashlib.sha256((RID + "\0" + ref["target_id"]).encode()).hexdigest()[:24], "source_id": RID, **ref,
            "target_in_catalog": ref["target_id"] == "arxiv:2404.07972"} for ref in current["references"]], key=lambda edge: edge["id"]))
        self.assertEqual(self.build([self.enrichment(RID, sha(b"an older README"))]), [])


if __name__ == "__main__":
    unittest.main()
