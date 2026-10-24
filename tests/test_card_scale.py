import copy
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build
from build_site import compact_scale

ROOT = Path(__file__).resolve().parents[1]
ROWS = {row["id"]: row for row in map(json.loads, (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines())}


def count(value, unit, qualifier="exact", population="release"):
    return {"value": value, "unit": unit, "qualifier": qualifier, "basis": "reported", "population": population, "evidence_url": "https://example.com/readme"}


class CardScaleTests(unittest.TestCase):
    def test_first_count_per_unit_keeps_its_precision_qualifier(self):
        record = {"kind": "benchmark", "details": {"benchmark_protocol": {"counts": [
            count(340, "tasks"), count(300, "tasks", population="subset"), count(15000, "demonstrations", "more-than"),
            count(66, "applications", "approximately"), count(12, "websites", "at-least"), count(1.5, "hours")]}}}
        self.assertEqual(compact_scale(record), {"scale": ["340 tasks", "> 15,000 demonstrations", "≈ 66 applications", "≥ 12 websites", "1.5 hours"]})

    def test_catalog_benchmark_keeps_only_its_first_task_count(self):
        self.assertEqual(compact_scale(ROWS["github:xlang-ai/osworld"]), {"scale": ["369 task definitions"]})

    def test_rows_without_recorded_counts_omit_the_key(self):
        row = copy.deepcopy(ROWS["github:xlang-ai/osworld"])
        row["details"]["benchmark_protocol"]["counts"] = []
        for record in (row, {"kind": "benchmark", "details": {}}, {"kind": "model", "details": {}}, ROWS["arxiv:2404.07972"]):
            self.assertEqual(compact_scale(record), {})

    def test_index_scale_matches_the_category_table_scale(self):
        shown = 0
        for row in ROWS.values():
            scale = compact_scale(row).get("scale", [])
            self.assertTrue(not scale or row["kind"] in ("benchmark", "dataset") and row["review_status"] == "curated", row["id"])
            cell = build.scale_cell(row)
            linked = [] if cell == "—" else [re.sub(r"\\(.)", r"\1", text) for text in re.findall(r"\[((?:\\.|[^\]\\])*)\]\(", cell)]
            self.assertEqual(scale, linked, row["id"])
            shown += bool(scale)
        self.assertGreater(shown, 0)


if __name__ == "__main__":
    unittest.main()
