import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog
import build
import publication_metadata
import specifications

SCHEMA = catalog.read_json(catalog.ROOT / "schemas/resource.schema.json")
FIXTURES = ("github:xlang-ai/osworld", "arxiv:2404.07972", "arxiv:2005.03776", "organization:anthropic")
LICENSE = {"declared": "Apache-2.0", "url": "https://raw.githubusercontent.com/xlang-ai/OSWorld/HEAD/LICENSE", "retrieved_at": "2026-10-16T06:41:57Z", "basis": "repository LICENSE header"}


def records():
    rows = {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl") if r["id"] in FIXTURES}
    return {rid: copy.deepcopy(rows[rid]) for rid in FIXTURES}


def set_path(rid, *path):
    def mutate(rows):
        target = rows[rid]
        for key in path[:-2]:
            target = target[key]
        target[path[-2]] = path[-1](target[path[-2]]) if callable(path[-1]) else path[-1]
    return mutate


def drop(rid, *path):
    def mutate(rows):
        target = rows[rid]
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]
    return mutate


BENCHMARK, PAPER, PUBLISHED, ORGANIZATION = FIXTURES
# Each record passes both validators; each mutation is rejected by the published JSON Schema.
CASES = {
    "http url": set_path(PAPER, "url", "http://arxiv.org/abs/2404.07972"),
    "url with leading space": set_path(PAPER, "url", " https://arxiv.org/abs/2404.07972"),
    "empty links": set_path(PAPER, "links", []),
    "http link": set_path(PAPER, "links", 0, "url", "http://arxiv.org/abs/2404.07972"),
    "link without rel": drop(PAPER, "links", 0, "rel"),
    "link with extra field": set_path(PAPER, "links", 0, "title", "OSWorld"),
    "relation type cites": set_path(BENCHMARK, "relations", 0, "type", "cites"),
    "relation with extra field": set_path(BENCHMARK, "relations", 0, "note", "x"),
    "http relation evidence": set_path(BENCHMARK, "relations", 0, "evidence_url", lambda url: "http://" + url[8:]),
    "duplicate environments": set_path(PAPER, "environments", ["desktop", "desktop"]),
    "duplicate topics": set_path(PAPER, "topics", lambda topics: topics + topics[:1]),
    "duplicate aliases": set_path(PAPER, "aliases", ["OSWorld", "OSWorld"]),
    "unknown top-level field": set_path(PAPER, "extra_field", 1),
    "omitted authors still listed": set_path(PAPER, "authors_omitted", True),
    "authors_omitted false": set_path(PAPER, "authors_omitted", False),
    "id prefix": set_path(ORGANIZATION, "id", "org:anthropic"),
    "id whitespace": set_path(ORGANIZATION, "id", "organization:anthropic labs"),
    "published_at basic format": set_path(PAPER, "published_at", "20240411"),
    "last_verified_at without seconds": set_path(PAPER, "last_verified_at", "2026-10-16T06:41Z"),
    "license without retrieved_at and basis": set_path(PAPER, "licenses", "code", {"declared": "MIT", "url": "https://x.org/L"}),
    "http license url": set_path(PAPER, "licenses", "code", {**LICENSE, "url": "http://x.org/L"}),
    "license with extra field": set_path(PAPER, "licenses", "code", {**LICENSE, "spdx": "Apache-2.0"}),
    "license declared as a number": set_path(PAPER, "licenses", "code", {**LICENSE, "declared": 2}),
    "license retrieved_at without offset": set_path(PAPER, "licenses", "code", {**LICENSE, "retrieved_at": "2026-10-16T06:41:57"}),
    "evidence method": set_path(BENCHMARK, "evidence", 0, "method", "guess"),
    "evidence with extra field": set_path(BENCHMARK, "evidence", 0, "status", 200),
    "upper-case evidence scheme": set_path(BENCHMARK, "evidence", 4, "url", lambda url: "HTTPS" + url[5:]),
    "duplicate evidence supports": set_path(BENCHMARK, "evidence", 0, "supports", lambda supports: supports + supports[:1]),
    "evidence timestamp without time": set_path(BENCHMARK, "evidence", 0, "retrieved_at", "2026-10-16"),
    "benchmark protocol extra field": set_path(BENCHMARK, "details", "benchmark_protocol", "extra", 1),
    "count extra field": set_path(BENCHMARK, "details", "benchmark_protocol", "counts", 0, "extra", 1),
    "snapshot without hash method": drop(PAPER, "details", "arxiv_snapshot", "abstract_hash_method"),
    "snapshot hash method": set_path(PAPER, "details", "arxiv_snapshot", "abstract_hash_method", "sha256-raw-text"),
    "snapshot digest": set_path(PAPER, "details", "arxiv_snapshot", "abstract_sha256", "not-a-digest"),
    "snapshot extra field": set_path(PAPER, "details", "arxiv_snapshot", "extra", 1),
    "publication extra field": set_path(PUBLISHED, "details", "publication", "extra", 1),
    "publication venue type": set_path(PUBLISHED, "details", "publication", "venue", 5),
    "duplicate publication evidence": set_path(PUBLISHED, "details", "publication", "evidence_urls", lambda urls: urls + urls[:1]),
}


class SchemaParityTests(unittest.TestCase):
    def schema_errors(self, row):
        import jsonschema
        return [error.message for error in jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker()).iter_errors(row)]

    def test_fixtures_pass_both_validators(self):
        rows = records()
        self.assertEqual(build.validate_records(list(rows.values())), [])
        for row in rows.values():
            self.assertEqual(self.schema_errors(row), [], row["id"])

    def test_build_gate_rejects_what_the_schema_rejects(self):
        original = records()
        for name, mutate in CASES.items():
            with self.subTest(name):
                rows = copy.deepcopy(original)
                mutate(rows)
                changed = next(row for rid, row in rows.items() if row != original[rid])
                self.assertTrue(self.schema_errors(changed))
                self.assertTrue(build.validate_records(list(rows.values())))

    def test_mirrored_vocabularies_match_the_schema(self):
        properties, definitions = SCHEMA["properties"], SCHEMA["$defs"]
        evidence = properties["evidence"]["items"]["properties"]
        self.assertEqual(set(build.FIELD_TYPES), set(SCHEMA["required"]))
        self.assertEqual(set(build.FIELD_TYPES) | set(build.OPTIONAL_FIELD_TYPES), set(properties))
        self.assertEqual(catalog.KINDS, set(properties["kind"]["enum"]))
        self.assertEqual(catalog.ENVIRONMENTS, set(properties["environments"]["items"]["enum"]))
        self.assertEqual(catalog.STATUSES, set(properties["review_status"]["enum"]))
        self.assertEqual(build.REVIEWED_RELATION_TYPES, set(properties["relations"]["items"]["properties"]["type"]["enum"]))
        self.assertEqual(build.EVIDENCE_FIELDS, set(evidence))
        for scope in ("code", "data", "weights", "document"):
            self.assertEqual(build.LICENSE_FIELDS, set(properties["licenses"]["properties"][scope]["properties"]))
        self.assertEqual(specifications.COUNT_FIELDS, set(definitions["countObservation"]["properties"]))
        self.assertEqual(publication_metadata.PUBLICATION_FIELDS, set(definitions["publication"]["properties"]))

    def test_timestamps_follow_the_schema_date_time_format(self):
        import jsonschema
        checker = jsonschema.FormatChecker()
        for value in ["2026-10-16T06:41:57Z", "2026-10-16t06:41:57.5z", "2026-10-16T06:41:57+05:30", "2026-10-16", "2026-10-16T06:41Z",
                      "2026-10-16 06:41:57Z", "2026-10-16T06:41:57", "2026-02-30T00:00:00Z", "2026-10-16T24:00:00Z", "2026-10-16T23:59:60Z", "20261016T064157Z"]:
            with self.subTest(value):
                self.assertEqual(build.timestamp(value), checker.conforms(value, "date-time"))


if __name__ == "__main__":
    unittest.main()
