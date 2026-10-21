import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest import mock
import urllib.error
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog
import build


DATAVERSE_URL = "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/WX8PCK"
DATAVERSE_API = "https://dataverse.harvard.edu/api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/WX8PCK"


def dataverse_dataset():
    # Reduced from the reviewed VideoCAD API response; files count archive units.
    return {"status": "OK", "data": {
        "datasetType": "dataset", "publisher": "Harvard Dataverse",
        "persistentUrl": "https://doi.org/10.7910/DVN/WX8PCK", "publicationDate": "2025-05-15",
        "latestVersion": {
            "datasetType": "dataset", "versionNumber": 5, "versionMinorNumber": 0,
            "versionState": "RELEASED", "releaseTime": "2026-03-11T01:35:02Z", "fileAccessRequest": True,
            "license": {"name": "CC0 1.0", "uri": "http://creativecommons.org/publicdomain/zero/1.0",
                        "rightsIdentifier": "CC0-1.0", "rightsIdentifierScheme": "SPDX"},
            "metadataBlocks": {"citation": {"fields": []}},
            "files": [{"dataFile": {"filename": f"{index:04d}.zip"}} for index in range(261)],
        },
    }}


def paper():
    element = ET.fromstring('''<entry xmlns="http://www.w3.org/2005/Atom">
      <id>http://arxiv.org/abs/2404.07972v3</id>
      <title>OSWorld: Benchmarking\n Multimodal Agents</title>
      <published>2024-04-11T00:00:00Z</published><updated>2024-05-01T00:00:00Z</updated>
      <author><name>A Researcher</name></author><summary>This must not become a reviewed summary.</summary>
    </entry>''')
    row = catalog.arxiv_entry(element, {"url": "https://export.arxiv.org/api/query?id_list=2404.07972", "retrieved_at": "2026-10-16T00:00:00Z", "sha256": "a" * 64})
    row.update(scope="relevance_pending", details={})
    return row


class IdentityTests(unittest.TestCase):
    def test_arxiv_versions_and_mirrors_share_identity(self):
        expected = ("arxiv:2404.07972", "https://arxiv.org/abs/2404.07972", "arxiv")
        for url in ["http://arxiv.org/pdf/2404.07972v3.pdf", "https://arxiv.org/html/2404.07972v2", "https://huggingface.co/papers/2404.07972"]:
            self.assertEqual(catalog.canonical(url), expected)

    def test_repository_case_and_paths_fold(self):
        for url in ["https://github.com/Xlang-AI/OSWorld.git", "https://github.com/xlang-ai/OSWorld/tree/main", "https://github.com/xlang-ai/OSWorld/blob/main/README.md"]:
            self.assertEqual(catalog.canonical(url)[0], "github:xlang-ai/osworld")

    def test_incidental_urls_are_not_resources(self):
        for url in ["https://github.com/topics/gui", "https://github.com/user-attachments/assets/123", "https://github.com/xlang-ai/OSWorld/issues/1", "https://img.shields.io/badge/test-blue", "javascript:alert(1)"]:
            self.assertIsNone(catalog.canonical(url))

    def test_host_spoof_does_not_become_arxiv(self):
        self.assertEqual(catalog.canonical("https://notarxiv.org/abs/2404.07972")[2], "url")

    def test_tracking_and_anchor_do_not_create_new_resource(self):
        self.assertEqual(catalog.canonical("https://example.org/item/?utm_source=test#intro"), catalog.canonical("https://example.org/item"))


class SourceTests(unittest.TestCase):
    def _enrich_source(self, kind, url, primary, content):
        body = content.encode() if isinstance(content, str) else json.dumps(content).encode()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(catalog, "DATA", Path(directory)):
            rid = catalog.canonical(url)[0]
            catalog.write_json(Path(directory) / "editorial.json", [{"url": url, "kind": kind}])
            catalog.write_jsonl(Path(directory) / "primary-evidence.jsonl", [{"id": rid, "url": primary,
                "content_matched": True, "sha256": hashlib.sha256(body).hexdigest(), "retrieved_at": "2026-10-17T02:03:20Z"}])
            with mock.patch.object(catalog, "cached_body", return_value=body), \
                    mock.patch.object(catalog, "fetch", side_effect=AssertionError("Unexpected network request")), \
                    contextlib.redirect_stdout(io.StringIO()):
                catalog.enrich(types.SimpleNamespace(refresh=False))
            return catalog.read_jsonl(Path(directory) / "enrichment.jsonl")[0]

    def test_metadata_verification_does_not_imply_editorial_review(self):
        row = paper()
        self.assertEqual(row["review_status"], "metadata_verified")
        self.assertEqual(row["name"], "OSWorld: Benchmarking Multimodal Agents")
        self.assertIsNone(row["summary"])
        self.assertTrue(all(v is None for v in row["licenses"].values()))

    def test_api_error_entry_is_not_a_paper(self):
        entry = ET.fromstring('<entry xmlns="http://www.w3.org/2005/Atom"><id>http://arxiv.org/api/errors#bad</id><title>Error</title></entry>')
        self.assertIsNone(catalog.arxiv_entry(entry, {}))

    def test_failed_refresh_keeps_good_cache_but_reports_failure(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(catalog, "CACHE", Path(directory)):
            url = "https://example.org/source"
            key = hashlib.sha256(url.encode()).hexdigest()
            catalog.write_json(Path(directory) / f"{key}.json", {"ok": True, "url": url, "sha256": hashlib.sha256(b"old good snapshot").hexdigest()})
            (Path(directory) / f"{key}.body").write_bytes(b"old good snapshot")
            error = urllib.error.HTTPError(url, 429, "rate limited", {}, None)
            with mock.patch("urllib.request.urlopen", side_effect=error), mock.patch("time.sleep"):
                info, body = catalog.fetch(url, refresh=True)
            self.assertFalse(info["ok"])
            self.assertEqual(body, b"")
            cached_info, cached_body = catalog.fetch(url)
            self.assertTrue(cached_info["ok"])
            self.assertEqual(cached_body, b"old good snapshot")

    def test_changed_source_cannot_keep_curated_status(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(build, "DATA", Path(directory)):
            row = {"name": "Example", "kind": "framework", "url": "https://example.org/", "environments": ["web"], "topics": [], "summary": "Example.", "editorial_reviewed": True, "reviewed_sha256": "a" * 64}
            catalog.write_json(Path(directory) / "editorial.json", [row])
            rid = catalog.canonical(row["url"])[0]
            ev = {"id": rid, "url": row["url"], "content_matched": True, "sha256": "b" * 64, "retrieved_at": "2026-10-16T00:00:00Z"}
            catalog.write_jsonl(Path(directory) / "primary-evidence.jsonl", [ev])
            rows, pending = build.source_records()
            self.assertEqual(rows, [])
            self.assertIn("snapshot", pending[0]["reason"])
            ev["sha256"] = "a" * 64
            catalog.write_jsonl(Path(directory) / "primary-evidence.jsonl", [ev])
            rows, pending = build.source_records()
            self.assertEqual(len(rows), 1)
            self.assertEqual(pending, [])

    def test_hub_card_licenses_are_scoped_and_require_a_metadata_declaration(self):
        cases = [
            ("dataset", "https://huggingface.co/datasets/example/data", "---\nlicense: cc-by-4.0\n---\nDataset card", {"data": "cc-by-4.0"}),
            ("model", "https://huggingface.co/example/model", "---\nlicense: apache-2.0\n---\nModel card", {"weights": "apache-2.0"}),
            ("framework", "https://huggingface.co/example/framework", "---\nlicense: mit\n---\nFramework", {}),
            ("dataset", "https://huggingface.co/datasets/example/prose", "# Card\nRelated code has license: MIT", {}),
        ]
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(catalog, "DATA", Path(directory)):
            rows, evidence, bodies = [], [], {}
            for kind, url, content, expected in cases:
                rid = catalog.canonical(url)[0]
                primary = url + "/raw/main/README.md"
                bodies[primary] = content.encode()
                rows.append({"url": url, "kind": kind})
                evidence.append({"id": rid, "url": primary, "content_matched": True, "sha256": hashlib.sha256(content.encode()).hexdigest(), "retrieved_at": "2026-10-16T00:00:00Z"})
            catalog.write_json(Path(directory) / "editorial.json", rows)
            catalog.write_jsonl(Path(directory) / "primary-evidence.jsonl", evidence)
            with mock.patch.object(catalog, "cached_body", side_effect=lambda url: bodies[url]), contextlib.redirect_stdout(io.StringIO()):
                catalog.enrich(types.SimpleNamespace(refresh=False))
            enriched = {r["id"]: r for r in catalog.read_jsonl(Path(directory) / "enrichment.jsonl")}
            for kind, url, content, expected in cases:
                result = enriched[catalog.canonical(url)[0]]
                self.assertEqual({scope: value["declared"] for scope, value in result["licenses"].items()}, expected)
                for receipt in result["evidence"]:
                    self.assertEqual(receipt["url"], url + "/raw/main/README.md")

    def test_hub_api_preserves_dataset_and_model_metadata(self):
        cases = [
            ("dataset", "datasets/example/data", "datasets/example/data", "data", "cc-by-4.0"),
            ("model", "example/model", "models/example/model", "weights", "apache-2.0"),
        ]
        for kind, path, api_path, slot, license_name in cases:
            with self.subTest(kind=kind):
                url = "https://huggingface.co/" + path
                primary = "https://huggingface.co/api/" + api_path
                payload = {"id": "example/resource", "gated": False, "disabled": False, "tags": ["modality:image"],
                    "cardData": {"license": license_name, "language": ["en"], "size_categories": ["1K<n<10K"]}}
                result = self._enrich_source(kind, url, primary, payload)
                self.assertEqual(set(result["licenses"]), {slot})
                self.assertEqual(result["licenses"][slot]["declared"], license_name)
                self.assertEqual(result["details"]["hub_id"], "example/resource")
                self.assertEqual(result["details"]["download_url"], url + "/tree/main")
                self.assertEqual(result["details"]["modalities"], ["image"])
                self.assertEqual(result["details"]["size_category_reported"], ["1K<n<10K"])
                self.assertNotIn("sample_count", result["details"])
                self.assertEqual(result["evidence"][0]["method"], "huggingface_api")
                self.assertEqual(result["evidence"][0]["url"], primary)

    def test_hub_parsing_requires_the_real_host_and_url_path(self):
        api_payload = {"id": "example/data", "cardData": {"license": "mit"}}
        card = "---\nlicense: mit\n---\nDataset card"
        cases = [
            ("https://example.org/api/datasets/example/data", api_payload),
            ("https://huggingface.co.example.org/api/models/example/model", api_payload),
            ("https://huggingface.co/datasets/example/data?source=/api/datasets/example/data", api_payload),
            ("https://example.org/datasets/example/data/raw/main/README.md", card),
            ("https://huggingface.co/datasets/example/data?source=/raw/main/README.md", card),
        ]
        for primary, content in cases:
            with self.subTest(primary=primary):
                result = self._enrich_source("dataset", "https://example.org/data", primary, content)
                self.assertEqual(result["licenses"], {})
                self.assertEqual(result["details"], {})
                self.assertEqual(result["evidence"], [])

    def test_dataverse_preserves_declared_license_and_release_metadata(self):
        import jsonschema
        payload = dataverse_dataset()
        result = self._enrich_source("dataset", DATAVERSE_URL, DATAVERSE_API, payload)
        metadata = result["details"]["dataverse"]
        self.assertEqual(metadata["license"], payload["data"]["latestVersion"]["license"])
        self.assertEqual(metadata["publisher"], "Harvard Dataverse")
        self.assertEqual(metadata["persistent_url"], "https://doi.org/10.7910/DVN/WX8PCK")
        self.assertEqual(metadata["publication_date"], "2025-05-15")
        self.assertEqual((metadata["version_number"], metadata["version_minor_number"]), (5, 0))
        self.assertEqual(metadata["version_state"], "RELEASED")
        self.assertEqual(metadata["released_at"], "2026-03-11T01:35:02Z")
        self.assertEqual(metadata["file_count"], 261)
        self.assertEqual(set(result["licenses"]), {"data"})
        self.assertEqual(result["licenses"]["data"]["declared"], "CC0 1.0")
        self.assertEqual(result["licenses"]["data"]["url"], DATAVERSE_API)
        for field in ("hub_id", "download_url", "gated", "sample_count"):
            self.assertNotIn(field, result["details"])
            self.assertNotIn(field, metadata)
        receipt = result["evidence"][0]
        self.assertEqual(receipt["method"], "dataverse_api")
        self.assertEqual(receipt["url"], DATAVERSE_API)
        self.assertEqual(receipt["sha256"], hashlib.sha256(json.dumps(payload).encode()).hexdigest())
        self.assertEqual(receipt["retrieved_at"], "2026-10-17T02:03:20Z")
        self.assertEqual(receipt["supports"], ["details.dataverse", "licenses.data"])
        schema = catalog.read_json(catalog.ROOT / "schemas/resource.schema.json")
        jsonschema.Draft202012Validator(schema["properties"]["evidence"]["items"], format_checker=jsonschema.FormatChecker()).validate(receipt)
        jsonschema.Draft202012Validator(schema["properties"]["licenses"]["properties"]["data"], format_checker=jsonschema.FormatChecker()).validate(result["licenses"]["data"])

    def test_dataverse_without_license_does_not_inherit_linked_code_terms(self):
        payload = dataverse_dataset()
        del payload["data"]["latestVersion"]["license"]
        payload["data"]["latestVersion"]["metadataBlocks"]["citation"]["fields"] = [
            {"typeName": "dsDescription", "value": "Related code https://github.com/example/code is MIT licensed."}]
        result = self._enrich_source("dataset", DATAVERSE_URL, DATAVERSE_API, payload)
        self.assertEqual(result["licenses"], {})
        self.assertIsNone(result["details"]["dataverse"]["license"])
        self.assertEqual(result["details"]["dataverse"]["version_state"], "RELEASED")
        self.assertNotIn("licenses.data", result["evidence"][0]["supports"])

    def test_dataverse_requires_dataset_kind_host_and_structure(self):
        cases = [
            ("model", DATAVERSE_API, dataverse_dataset()),
            ("dataset", DATAVERSE_API.replace("dataverse.harvard.edu", "example.org"), dataverse_dataset()),
            ("dataset", DATAVERSE_API, {"status": "OK", "data": {"license": {"name": "CC0 1.0"}}}),
            ("dataset", DATAVERSE_API, {"status": "ERROR", "data": dataverse_dataset()["data"]}),
            ("dataset", DATAVERSE_API, "<html>Service unavailable</html>"),
        ]
        for kind, primary, content in cases:
            with self.subTest(kind=kind, primary=primary, content_type=type(content).__name__):
                result = self._enrich_source(kind, DATAVERSE_URL, primary, content)
                self.assertEqual(result["licenses"], {})
                self.assertEqual(result["details"], {})
                self.assertEqual(result["evidence"], [])

    def test_supporting_source_change_revokes_primary_review_match(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(catalog, "DATA", Path(directory)):
            primary = "https://example.org/primary"
            supporting = "https://example.org/description"
            row = {"name": "Example", "url": primary, "additional_evidence": [{"url": supporting, "sha256": "b" * 64}]}
            catalog.write_json(Path(directory) / "editorial.json", [row])
            for support_digest, expected in [("b" * 64, True), ("c" * 64, False)]:
                def fake_fetch(url, refresh=False):
                    return {"url": url, "ok": True, "status": 200, "sha256": "a" * 64 if url == primary else support_digest}, b"Example"
                with mock.patch.object(catalog, "fetch", side_effect=fake_fetch), contextlib.redirect_stdout(io.StringIO()):
                    catalog.verify_editorial(types.SimpleNamespace(refresh=True))
                result = catalog.read_jsonl(Path(directory) / "primary-evidence.jsonl")[0]
                self.assertEqual(result["content_matched"], expected)
                if not expected:
                    self.assertIn("supporting source", result["error"])


class QualityTests(unittest.TestCase):
    def test_confirmed_duplicate_remains_provenance_not_an_extra_reviewed_work(self):
        original = paper()
        duplicate = copy.deepcopy(original)
        duplicate.update(id="arxiv:2505.13887", url="https://arxiv.org/abs/2505.13887")
        duplicate["identifiers"] = {"arxiv": "2505.13887", "preferred_arxiv": original["identifiers"]["arxiv"]}
        self.assertEqual(build.validate_records([original, duplicate]), [])
        duplicate.update(review_status="curated", scope="core", summary="A duplicate publication.")
        self.assertTrue(any("known duplicate" in e for e in build.validate_records([original, duplicate])))

    def test_duplicate_and_dangling_relationship_rejected(self):
        row = paper()
        row["relations"] = [{"type": "uses", "target_id": "missing", "evidence_url": row["url"]}]
        errors = build.validate_records([row, copy.deepcopy(row)])
        self.assertTrue(any("duplicate" in e for e in errors))
        self.assertTrue(any("dangling" in e for e in errors))
        self.assertTrue(any("retained primary evidence" in e for e in errors))

    def test_future_publication_and_unscoped_license_rejected(self):
        row = paper()
        row["published_at"] = "2099-01-01"
        row["licenses"] = {"code": "MIT"}
        errors = build.validate_records([row])
        self.assertTrue(any("after" in e for e in errors))
        self.assertTrue(any("license" in e for e in errors))

    def test_sqlite_preserves_json_and_search(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.sqlite"
            row = paper()
            build.write_sqlite([row], path)
            con = sqlite3.connect(path)
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("SELECT id FROM resource_search WHERE resource_search MATCH ?", ("OSWorld",)).fetchone()[0], row["id"])
            self.assertEqual(json.loads(con.execute("SELECT record_json FROM resources").fetchone()[0]), row)
            con.close()

    def test_published_schema_accepts_real_catalog(self):
        import jsonschema
        validator = jsonschema.Draft202012Validator(catalog.read_json(catalog.ROOT / "schemas/resource.schema.json"), format_checker=jsonschema.FormatChecker())
        rows = catalog.read_jsonl(catalog.DATA / "catalog.jsonl")
        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertEqual(list(validator.iter_errors(row)), [], row["id"])

    def test_committed_generated_views_are_reproducible(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build.build(types.SimpleNamespace(check=True))


class CategoryPageTests(unittest.TestCase):
    def test_paper_column_uses_reviewed_relations_only(self):
        source = paper()
        asset = {"relations": [{"type": "documented_by", "target_id": source["id"]}, {"type": "documented_by", "target_id": source["id"]},
            {"type": "uses", "target_id": "arxiv:2501.00001"}, {"type": "published_by", "target_id": "company:x"}]}
        self.assertEqual(build.paper_cell(asset, {source["id"]: source}), "[2404.07972](https://arxiv.org/abs/2404.07972) (2024)")
        self.assertEqual(build.paper_cell({"relations": [{"type": "introduced_by", "target_id": "arxiv:2501.00001"}]}, {}), "[2501.00001](https://arxiv.org/abs/2501.00001)")
        self.assertEqual(build.paper_cell({"relations": []}, {}), "—")

    def test_license_column_keeps_scopes_and_unknowns(self):
        licenses = {"code": {"declared": "MIT", "url": "https://x.test/LICENSE"}, "data": {"declared": ["cc-by-4.0", "odc-by"], "url": "https://x.test"}, "weights": None, "document": None}
        self.assertEqual(build.license_cell({"licenses": licenses}), "code MIT · data cc-by-4.0/odc-by")
        self.assertEqual(build.license_cell({"licenses": {"code": None, "data": None, "weights": None, "document": None}}), "—")

    def test_environment_family_sections(self):
        family = lambda *envs: build.environment_family({"environments": list(envs)})
        self.assertEqual(family("web"), "web")
        self.assertEqual(family("desktop", "linux", "windows", "macos"), "desktop")
        self.assertEqual(family("android", "ios"), "mobile")
        self.assertEqual(family("desktop", "web"), "cross-platform")
        self.assertEqual(family("cross-platform"), "cross-platform")
        self.assertEqual(family("unspecified"), "unspecified")

    def test_coverage_matrix_marks_gaps(self):
        lines = build.matrix_lines({"benchmark": {"web": 2, "ios": 1}, "company": {"unspecified": 3}})
        self.assertEqual(lines[2], "| [benchmark](benchmarks.md) | 2 | · | · | · | · | · | 1 | · | · | · |")
        self.assertTrue(lines[3].startswith("| [company](companies.md) | · |"))

    def test_kind_specific_columns(self):
        row = {"name": "A|B", "url": "https://example.com/a", "environments": ["web"], "summary": "Short.", "published_at": "2025-01-02",
            "relations": [{"type": "published_by", "target_id": "company:x"}], "licenses": {"code": None, "data": None, "weights": None, "document": None},
            "evidence": [{"method": "editorial_primary_review", "url": "https://example.com/a", "retrieved_at": "2026-10-16T00:00:00Z"}]}
        by_id = {"company:x": {"name": "Example", "url": "https://example.com"}}
        self.assertEqual(build.table_row(row, build.KIND_COLUMNS["product"][0], by_id),
            "| [A\\|B](https://example.com/a) | [Example](https://example.com) | web | Short. | [✓ 2026\u201110\u201116](https://example.com/a) |")
        self.assertEqual(build.table_row(row, build.KIND_COLUMNS["survey"][0], by_id).split(" | ")[0], "| 2025\u201101\u201102")



class ReadmeBlockTests(unittest.TestCase):
    def row(self, rid, name, kind="benchmark", status="curated"):
        return {"id": rid, "name": name, "kind": kind, "review_status": status, "url": "https://example.com/" + name, "environments": ["web"],
            "summary": name + " summary.", "relations": [], "licenses": {"code": None, "data": None, "weights": None, "document": None}}

    def test_highlights_rank_by_distinct_mentioning_resources(self):
        rows = [self.row("github:a/b", "Beta"), self.row("github:a/a", "Alpha"), self.row("github:a/c", "Gamma"), self.row("github:a/d", "Delta", status="metadata_verified")]
        edge = lambda source, target: {"source_id": source, "target_id": target, "target_in_catalog": True}
        edges = [edge("x", "github:a/b"), edge("y", "github:a/b"), edge("x", "github:a/b"), edge("x", "github:a/a"), edge("y", "github:a/c"),
            edge("github:a/c", "github:a/c"), edge("x", "github:a/d"), {"source_id": "z", "target_id": "github:a/c", "target_in_catalog": False}]
        table = [line for line in build.highlights(rows, edges).splitlines() if line.startswith("| [")]
        self.assertEqual([line.split("]")[0][3:] for line in table], ["Beta", "Alpha", "Gamma"])
        self.assertIn("| 2 |", table[0])
        self.assertIn("[all 3 →](docs/benchmarks.md)", build.highlights(rows, edges))
        self.assertEqual(build.highlights(rows, []).strip(), "")

    def test_recently_reviewed_orders_non_paper_approvals(self):
        rows = [self.row("a", "Alpha"), self.row("b", "Beta"), self.row("c", "Gamma", kind="paper"), self.row("d", "Delta", status="metadata_verified"), self.row("e", "Eps")]
        reviewed = {"a": "2026-10-16T01:00:00Z", "b": "2026-10-17T01:00:00Z", "c": "2026-10-18T00:00:00Z", "d": "2026-10-18T00:00:00Z"}
        table = [line for line in build.recently_reviewed(rows, reviewed).splitlines() if line.startswith("| 2026")]
        self.assertEqual([line.split("[")[1].split("]")[0] for line in table], ["Beta", "Alpha"])
        self.assertEqual(build.recently_reviewed(rows, {}), "\n")

    def test_explore_counts_curated_resources(self):
        rows = [self.row("a", "A"), self.row("b", "B"), self.row("c", "C", status="metadata_verified"), self.row("d", "D", kind="paper")]
        table = build.explore(rows, {"bibliographic_records": 1234})
        self.assertIn("[Benchmarks](docs/benchmarks.md) · **2**", table)
        self.assertIn("[Research by topic](docs/topics.md) · **1** reviewed papers", table)
        self.assertIn("[Full bibliography](docs/papers.md) · 1,234 paper and survey records", table)

    def test_shield_escapes_separators(self):
        self.assertEqual(build.shield("evidence through", "2026-10-17", "1d76db"), "https://img.shields.io/badge/evidence%20through-2026--10--17-1d76db")
        self.assertEqual(build.shield("a_b", "1,036", "blue"), "https://img.shields.io/badge/a__b-1%2C036-blue")



class TopicHubTests(unittest.TestCase):
    def row(self, rid, name, kind, topics, published_at=None, status="curated"):
        return {"id": rid, "name": name, "kind": kind, "review_status": status, "url": "https://example.com/" + rid, "environments": ["web"], "topics": topics,
            "summary": name + ".", "published_at": published_at, "relations": [], "licenses": {"code": None, "data": None, "weights": None, "document": None},
            "evidence": [{"method": "editorial_primary_review", "url": "https://example.com/" + rid, "retrieved_at": "2026-10-16T00:00:00Z"}]}

    def test_hubs_list_every_tagged_curated_resource_once_per_topic(self):
        rows = [self.row("arxiv:2401.00001", "Older paper", "paper", ["grounding"], "2024-01-01"),
            self.row("arxiv:2501.00001", "Newer paper", "paper", ["grounding", "safety-security"], "2025-01-01"),
            self.row("github:a/bench", "Bench", "benchmark", ["grounding", "grounding"]),
            self.row("arxiv:2502.00001", "Unreviewed", "paper", ["grounding"], "2025-02-01", status="metadata_verified")]
        files = build.topic_pages(rows)
        self.assertEqual(sorted(files), ["docs/topics.md", "docs/topics/grounding.md", "docs/topics/safety-security.md"])
        hub = files["docs/topics/grounding.md"]
        self.assertLess(hub.index("Newer paper"), hub.index("Older paper"))
        self.assertEqual(hub.count("[Bench]("), 1)
        self.assertNotIn("Unreviewed", hub)
        self.assertIn("[Benchmarks (1)](#benchmarks) · [Papers (2)](#papers)", hub)
        index = files["docs/topics.md"]
        self.assertLess(index.index("[GUI grounding]"), index.index("[Safety & security]"))
        self.assertIn("| [GUI grounding](topics/grounding.md) | 3 | 1 | · | · | · | · | 2 | [Newer paper]", index)

    def test_bibliography_year_index_marks_reviews_and_undated_records(self):
        rows = [self.row("arxiv:2401.00001", "Reviewed", "paper", ["grounding"], "2024-01-01"),
            self.row("arxiv:2402.00001", "Metadata", "paper", [], "2024-02-01", status="metadata_verified"),
            self.row("arxiv:2403.00001", "No date", "paper", [], None, status="metadata_verified")]
        report = {"as_of_utc": "2026-10-16T00:00:00Z", "total_records": 3, "curated_records": 1, "metadata_only_records": 2, "bibliographic_records": 3,
            "arxiv_archive_records": 3, "excluded_records": 0, "discovery_identifiers": 0, "unindexed_candidates": 0, "pending_editorial": [], "sources": [],
            "primary_search": {}, "license_declarations_by_scope": {}, "exclusion_revalidation_pending": 0, "curated_by_kind_and_environment": {}}
        page = build.documents(rows, report)["docs/papers.md"]
        self.assertIn("**Years:** [2024](#2024) (2; 1 ⭐) · [Undated](#undated) (1; 0 ⭐)", page)
        self.assertIn("| 2024-01-01 | [Reviewed](https://example.com/arxiv:2401.00001) | ⭐ reviewed | [grounding](topics/grounding.md) |", page)
        self.assertIn("| — | [No date](https://example.com/arxiv:2403.00001) | metadata |  |", page)
        self.assertNotIn("None", page)

    def test_curated_non_arxiv_paper_stays_in_bibliography(self):
        rows = [self.row("url:0123456789abcdef0123", "Workshop paper", "paper", ["grounding"], None)]
        report = {"as_of_utc": "2026-10-16T00:00:00Z", "total_records": 1, "curated_records": 1, "metadata_only_records": 0, "bibliographic_records": 0,
            "arxiv_archive_records": 0, "excluded_records": 0, "discovery_identifiers": 0, "unindexed_candidates": 0, "pending_editorial": [], "sources": [],
            "primary_search": {}, "license_declarations_by_scope": {}, "exclusion_revalidation_pending": 0, "curated_by_kind_and_environment": {}}
        files = build.documents(rows, report)
        self.assertIn("[Workshop paper](https://example.com/url:0123456789abcdef0123) | ⭐ reviewed", files["docs/papers.md"])
        self.assertIn("Workshop paper", files["docs/topics/grounding.md"])

    def test_bibliography_owns_papers_page(self):
        rows = [self.row("arxiv:2401.00001", "Reviewed paper", "paper", ["grounding"], "2024-01-01")]
        report = {"as_of_utc": "2026-10-16T00:00:00Z", "total_records": 1, "curated_records": 1, "metadata_only_records": 0, "bibliographic_records": 1,
            "arxiv_archive_records": 1, "excluded_records": 0, "discovery_identifiers": 0, "unindexed_candidates": 0, "pending_editorial": [], "sources": [],
            "primary_search": {}, "license_declarations_by_scope": {}, "exclusion_revalidation_pending": 0, "curated_by_kind_and_environment": {}}
        files = build.documents(rows, report)
        self.assertTrue(files["docs/papers.md"].startswith("# Research bibliography"))
        self.assertIn("Reviewed paper", files["docs/topics/grounding.md"])


if __name__ == "__main__":
    unittest.main()
