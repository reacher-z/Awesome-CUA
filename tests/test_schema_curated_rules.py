import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog
import build

PAPER, BENCHMARK, DATASET, PUBLISHED, SURVEY = (
    "arxiv:2404.07972", "github:xlang-ai/osworld", "github:alibabaresearch/rots", "url:347925d0f440d6396080", "arxiv:2411.02006")
# Any metadata-only arXiv paper will do. A fixed one would break as soon as it is curated or excluded.
BIBLIOGRAPHY = next(r["id"] for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl")
                    if r["review_status"] == "metadata_verified" and r["kind"] == "paper" and r["id"].startswith("arxiv:"))


def records():
    return {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl") if r["id"] in {PAPER, BENCHMARK, DATASET, BIBLIOGRAPHY, PUBLISHED, SURVEY}}


def snapshot_support(row):
    receipt = next(e for e in row["evidence"] if e["method"] == "arxiv_api")
    receipt["supports"] = [field for field in receipt["supports"] if field != "details.arxiv_snapshot"]


def moved(source, key):
    def mutate(rows, target):
        target["details"][key] = copy.deepcopy(rows[source]["details"][key])
    return mutate


# (record, mutation): each breaks one rule that validate_records enforces and the schema now states.
REJECTED = {
    "curated null summary": (PAPER, lambda rows, row: row.update(summary=None)),
    "curated empty summary": (PAPER, lambda rows, row: row.update(summary="")),
    "curated relevance_pending": (PAPER, lambda rows, row: row.update(scope="relevance_pending")),
    "benchmark protocol on a dataset": (DATASET, moved(BENCHMARK, "benchmark_protocol")),
    "benchmark protocol on a metadata-only record": (BENCHMARK, lambda rows, row: row.update(review_status="metadata_verified", summary=None, scope="relevance_pending", topics=[])),
    "dataset profile on a benchmark": (BENCHMARK, moved(DATASET, "dataset_profile")),
    "dataset profile on a metadata-only record": (DATASET, lambda rows, row: row.update(review_status="metadata_verified", summary=None, scope="relevance_pending", topics=[])),
    "arXiv snapshot on a repository": (BENCHMARK, moved(PAPER, "arxiv_snapshot")),
    "arXiv snapshot on a non-paper arXiv record": (PAPER, lambda rows, row: row.update(kind="benchmark")),
    "arXiv snapshot without its API receipt": (PAPER, lambda rows, row: snapshot_support(row)),
    "publication on a benchmark": (BENCHMARK, moved(PUBLISHED, "publication")),
}


class SchemaCuratedRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import jsonschema
        cls.validator = jsonschema.Draft202012Validator(catalog.read_json(catalog.ROOT / "schemas/resource.schema.json"), format_checker=jsonschema.FormatChecker())
        cls.rows = records()

    def test_schema_accepts_records_the_validator_accepts(self):
        # Metadata-only, adjacent, survey and publisher-only records sit just outside each conditional.
        adjacent = {**copy.deepcopy(self.rows[PAPER]), "scope": "adjacent"}
        for row in [*self.rows.values(), adjacent]:
            with self.subTest(row["id"]):
                self.assertEqual(list(self.validator.iter_errors(row)), [])
        self.assertEqual(self.rows[BIBLIOGRAPHY]["review_status"], "metadata_verified")
        self.assertIsNone(self.rows[BIBLIOGRAPHY]["summary"])
        self.assertEqual(self.rows[SURVEY]["kind"], "survey")
        self.assertIn("publication", self.rows[PUBLISHED]["details"])

    def test_schema_rejects_what_validate_records_rejects(self):
        for name, (rid, mutate) in REJECTED.items():
            with self.subTest(name):
                rows = copy.deepcopy(self.rows)
                before = set(build.validate_records(list(rows.values())))
                mutate(rows, rows[rid])
                self.assertTrue(set(build.validate_records(list(rows.values()))) - before)
                self.assertTrue(list(self.validator.iter_errors(rows[rid])))

    def test_conditions_do_not_apply_to_malformed_details(self):
        # A non-object details value is reported once, as a type error, not as a missing kind.
        row = {**copy.deepcopy(self.rows[DATASET]), "details": None}
        self.assertEqual([error.validator for error in self.validator.iter_errors(row)], ["type"])


if __name__ == "__main__":
    unittest.main()
