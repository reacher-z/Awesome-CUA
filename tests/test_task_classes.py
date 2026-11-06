import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build import validate_records  # noqa: E402

CLASSES = json.loads((ROOT / "data/task-classes.json").read_text(encoding="utf-8"))
ROWS = [json.loads(line) for line in (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]
PAPER = next(r for r in ROWS if r["review_status"] == "curated" and r["kind"] == "paper")
MODEL = next(r for r in ROWS if r["review_status"] == "curated" and r["kind"] == "model")


def errors(row):
    return [e for e in validate_records([row]) if "task_classes" in e]


class TaskClassTests(unittest.TestCase):
    def test_taxonomy_file_has_fifteen_realms_and_their_classes(self):
        self.assertEqual([r["id"] for r in CLASSES["realms"]], [f"R{n:02d}" for n in range(1, 16)])
        self.assertEqual(len(CLASSES["classes"]), 430)
        for c in CLASSES["classes"]:
            self.assertTrue(c["id"].startswith(c["realm"] + "."))
            self.assertTrue(c["name"] and c["zh"])

    def test_accepts_known_sorted_ids_on_a_curated_paper(self):
        row = copy.deepcopy(PAPER)
        row["task_classes"] = sorted([CLASSES["classes"][0]["id"], CLASSES["classes"][5]["id"]])
        self.assertEqual(errors(row), [])

    def test_rejects_unknown_unsorted_empty_and_wrong_kind(self):
        a, b = CLASSES["classes"][5]["id"], CLASSES["classes"][0]["id"]
        for value in (["R99.01.01.01"], [a, b], [], [a, a]):
            row = copy.deepcopy(PAPER)
            row["task_classes"] = value
            self.assertTrue(errors(row), value)
        row = copy.deepcopy(MODEL)
        row["task_classes"] = [b]
        self.assertTrue(errors(row))


if __name__ == "__main__":
    unittest.main()
