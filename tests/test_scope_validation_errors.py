import copy
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog
import build
import scope_review


def osworld():
    row = next(r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl") if r["id"] == "arxiv:2404.07972")
    return {**copy.deepcopy(row), "relations": []}


def decision(rid="arxiv:2401.00001", **changes):
    return {"id": rid, "name": "A reviewed out-of-scope title", "url": "https://arxiv.org/abs/" + rid.split(":", 1)[1], "decision": "out_of_scope",
        "basis": "primary_abstract_review", "reason": "Reviewed abstract describes unrelated work.", "reviewed_at": "2026-10-16T01:00:00Z",
        "metadata_fingerprint": "b" * 64, "evidence": {"url": "https://export.arxiv.org/api/query?id_list=2401.00001", "sha256": "c" * 64, "retrieved_at": "2026-10-16T00:00:00Z"}, **changes}


def validate_errors(rows, decisions):
    with tempfile.TemporaryDirectory() as directory:
        catalog.write_jsonl(Path(directory) / "catalog.jsonl", rows)
        catalog.write_json(Path(directory) / "exclusions.json", decisions)
        catalog.write_json(Path(directory) / "task-classes.json", catalog.read_json(catalog.DATA / "task-classes.json"))
        with mock.patch.object(build, "DATA", Path(directory)), unittest.TestCase().assertRaises(ValueError) as raised:
            build.validate(types.SimpleNamespace())
    return str(raised.exception).splitlines()


class ScopeValidationErrorTests(unittest.TestCase):
    def test_resolver_failure_is_reported_with_record_and_schema_errors(self):
        insecure, unscoped = osworld(), osworld()
        insecure["url"] = "http://arxiv.org/abs/2404.07972"
        unscoped.update(id="arxiv:2404.00001", url="https://arxiv.org/abs/2404.00001", scope="unknown")
        errors = validate_errors([insecure, unscoped], [decision()])
        self.assertIn("arxiv:2404.00001: invalid scope", errors)
        self.assertIn("arxiv:2404.07972: 'http://arxiv.org/abs/2404.07972' does not match '^https://'", errors)
        self.assertIn("Scope decisions: arxiv:2401.00001: scope decision has no retained bibliographic record", errors)

    def test_whitespace_only_reason_fails_the_schema_before_the_resolver(self):
        errors = validate_errors([osworld()], [decision(reason="   ")])
        self.assertEqual(errors, ["Scope decisions: '   ' does not match '\\\\S'"])

    def test_schema_matches_the_resolver_on_reason_and_url(self):
        validator = jsonschema.Draft202012Validator(catalog.read_json(catalog.ROOT / "schemas/scope-decision.schema.json"))
        self.assertEqual(list(validator.iter_errors([decision()])), [])
        for bad in [decision(reason=" \t\n"), decision(url="https://arxivXorg/abs/2401.00001")]:
            with self.subTest(bad=bad):
                self.assertTrue(list(validator.iter_errors([bad])))
                with self.assertRaises(ValueError):
                    scope_review.resolve_exclusions({bad["id"]: {"id": bad["id"]}}, [bad])


if __name__ == "__main__":
    unittest.main()
