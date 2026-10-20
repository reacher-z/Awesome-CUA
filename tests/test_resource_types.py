import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from search_pages import SITE, description, entity_type, page, resource_path, resource_schema, spdx_license


def record(**fields):
    base = {"id": "github:example/agent", "name": "Example agent", "kind": "framework", "url": "https://github.com/example/agent",
            "summary": "An example resource whose summary is long enough to qualify as a dataset description.", "authors": [],
            "published_at": None, "updated_at": None, "topics": [], "relations": [],
            "licenses": {"code": None, "data": None, "weights": None, "document": None}}
    return {**base, **fields}


def declared(value):
    return {"declared": value, "basis": "test", "url": "https://example.com/LICENSE", "retrieved_at": "2026-10-18T00:00:00Z"}


class ResourceTypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(line) for line in (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        cls.lookup = {r["id"]: r for r in cls.rows}

    def test_types_follow_kind_and_host(self):
        self.assertEqual(entity_type(record(kind="paper", url="https://arxiv.org/abs/2404.07972")), "ScholarlyArticle")
        self.assertEqual(entity_type(record(kind="company", url="https://example.com/")), "Organization")
        self.assertEqual(entity_type(record(kind="framework")), "SoftwareSourceCode")
        self.assertEqual(entity_type(record(kind="model")), "SoftwareSourceCode")
        self.assertEqual(entity_type(record(kind="benchmark", url="https://huggingface.co/datasets/example/bench")), "Dataset")
        self.assertEqual(entity_type(record(kind="dataset")), "Dataset")
        self.assertEqual(entity_type(record(kind="model", url="https://huggingface.co/example/model")), "CreativeWork")
        self.assertEqual(entity_type(record(kind="product", url="https://example.com/product")), "CreativeWork")
        self.assertEqual(entity_type(record(kind="product", url="https://github.com/example/product")), "SoftwareSourceCode")
        # Google Dataset Search needs 50+ characters of description; shorter datasets stay generic works, never code.
        self.assertEqual(entity_type(record(kind="dataset", summary="Too short.")), "CreativeWork")
        self.assertEqual(entity_type(record(kind="benchmark", url="https://huggingface.co/datasets/example/bench", summary="Too short.")), "CreativeWork")

    def test_software_names_its_repository_and_organizations_carry_no_creative_work_dates(self):
        schema = resource_schema(record(updated_at="2026-01-01"))
        self.assertEqual(schema["codeRepository"], "https://github.com/example/agent")
        org = resource_schema(record(kind="company", url="https://example.com/", authors=["Someone"], published_at="2025-01-01", updated_at="2025-02-01"))
        self.assertEqual(org["@type"], "Organization")
        for field in ("author", "datePublished", "dateModified", "codeRepository", "license", "citation"):
            self.assertNotIn(field, org)

    def test_license_comes_only_from_the_matching_slot_and_only_when_spdx(self):
        licenses = {"code": declared("Apache-2.0"), "data": declared("cc-by-4.0"), "weights": declared("mit"), "document": declared("CC0-1.0")}
        self.assertEqual(resource_schema(record(licenses=licenses))["license"], "https://spdx.org/licenses/Apache-2.0.html")
        self.assertEqual(resource_schema(record(kind="dataset", licenses=licenses))["license"], "https://spdx.org/licenses/CC-BY-4.0.html")
        self.assertEqual(resource_schema(record(kind="model", url="https://huggingface.co/example/model", licenses=licenses))["license"], "https://spdx.org/licenses/MIT.html")
        for kind, url in (("product", "https://example.com/p"), ("company", "https://example.com/"), ("paper", "https://arxiv.org/abs/2404.07972")):
            self.assertNotIn("license", resource_schema(record(kind=kind, url=url, licenses=licenses)), kind)
        # A code licence never describes data or weights, and absent slots stay absent.
        self.assertNotIn("license", resource_schema(record(kind="dataset", licenses={**licenses, "data": None})))
        self.assertNotIn("license", resource_schema(record(kind="model", url="https://huggingface.co/example/model", licenses={**licenses, "weights": None})))
        for value in ("other", "Apache-2.0 (MAI-UI subdirectory)", "Meta Llama 3 Community License Agreement", "", None, ["MIT"]):
            self.assertIsNone(spdx_license(value), value)
        self.assertEqual(spdx_license("CC0 1.0"), "https://spdx.org/licenses/CC0-1.0.html")
        self.assertEqual(spdx_license("odc-by"), "https://spdx.org/licenses/ODC-By-1.0.html")

    def test_citations_name_reviewed_paper_relations_only(self):
        relations = [{"type": "documented_by", "target_id": "arxiv:2404.07972", "evidence_url": "https://example.com"},
                     {"type": "introduced_by", "target_id": "arxiv:2401.10935", "evidence_url": "https://example.com"},
                     {"type": "introduced_by", "target_id": "github:other/repo", "evidence_url": "https://example.com"},
                     {"type": "uses", "target_id": "arxiv:2307.13854", "evidence_url": "https://example.com"}]
        schema = resource_schema(record(relations=relations), self.lookup)
        self.assertEqual([c["url"] for c in schema["citation"]], ["https://arxiv.org/abs/2401.10935", "https://arxiv.org/abs/2404.07972"])
        self.assertEqual(schema["citation"][1]["name"], self.lookup["arxiv:2404.07972"]["name"])
        self.assertNotIn("citation", resource_schema(record(relations=relations[2:])))
        self.assertNotIn("citation", resource_schema(record(kind="company", url="https://example.com/", relations=relations)))

    def test_every_catalog_record_renders_parseable_typed_json_ld(self):
        allowed = {"ScholarlyArticle", "Dataset", "SoftwareSourceCode", "Organization", "CreativeWork"}
        seen = set()
        for r in self.rows:
            schema = resource_schema(r, self.lookup)
            html = page(r["name"], description(r), resource_path(r), "<h1>x</h1>", schema)
            blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
            self.assertEqual(len(blocks), 1, r["id"])
            entity = next(n for n in json.loads(blocks[0])["@graph"] if n.get("@id") == SITE + resource_path(r) + "#entity")
            self.assertIn(entity["@type"], allowed, r["id"])
            seen.add(entity["@type"])
            if "license" in entity:
                self.assertRegex(entity["license"], r"^https://spdx\.org/licenses/[A-Za-z0-9.\-]+\.html$", r["id"])
            for cited in entity.get("citation", []):
                self.assertRegex(cited["url"], r"^https://arxiv\.org/abs/\d{4}\.\d{4,5}$", r["id"])
            if entity["@type"] == "SoftwareSourceCode":
                self.assertEqual(entity["codeRepository"], r["url"])
            if r["kind"] == "company":
                self.assertEqual(entity["@type"], "Organization")
        self.assertEqual(seen, allowed)


if __name__ == "__main__":
    unittest.main()
