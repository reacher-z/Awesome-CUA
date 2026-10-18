import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build
import catalog


class CanonicalJsonlTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.data = Path(directory.name)

    def test_written_inputs_are_canonical(self):
        catalog.write_jsonl(self.data / "primary-evidence.jsonl", [{"id": "github:b/b", "sha256": "2"}, {"id": "github:a/a", "sha256": "1"}])
        self.assertEqual(build.noncanonical_jsonl_errors(self.data), [])

    def test_hand_appended_receipt_is_reported(self):
        catalog.write_jsonl(self.data / "primary-evidence.jsonl", [{"id": "github:b/b", "sha256": "2"}])
        with (self.data / "primary-evidence.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"id": "github:a/a", "sha256": "1"}) + "\n")
        errors = build.noncanonical_jsonl_errors(self.data)
        self.assertEqual(len(errors), 1)
        self.assertIn("data/primary-evidence.jsonl is not in canonical order", errors[0])
        self.assertIn("verify --id", errors[0])

    def test_unsorted_keys_are_reported(self):
        (self.data / "enrichment.jsonl").write_text('{"sha256": "1", "id": "github:a/a"}\n', encoding="utf-8")
        self.assertIn("data/enrichment.jsonl", build.noncanonical_jsonl_errors(self.data)[0])

    def test_missing_files_are_skipped(self):
        self.assertEqual(build.noncanonical_jsonl_errors(self.data), [])

    def test_repository_inputs_are_canonical(self):
        self.assertEqual(build.noncanonical_jsonl_errors(), [])


if __name__ == "__main__":
    unittest.main()
