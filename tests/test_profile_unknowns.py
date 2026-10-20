"""Unrecorded profile values are marked up the same way everywhere, so they never read like recorded data."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from specifications import UNKNOWN, comparison_body, resource_profile_html, shown

ROWS = [json.loads(line) for line in (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]
BARE = re.compile(r"(?<!<span class=\"unknown-value\">)Not recorded")


class ProfileUnknownTests(unittest.TestCase):
    def test_shown_escapes_values_and_marks_missing_ones(self):
        self.assertEqual(shown(["a<b", "c"]), "a&lt;b, c")
        self.assertEqual(shown("interactive"), "interactive")
        for missing in ([], "", "  ", None):
            self.assertEqual(shown(missing), UNKNOWN)
        self.assertEqual(UNKNOWN, '<span class="unknown-value">Not recorded</span>')

    def test_comparison_tables_have_no_unmarked_unknowns(self):
        for kind in ("benchmark", "dataset"):
            body = comparison_body(ROWS, kind, lambda row: "/resources/x/")
            table = body.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
            self.assertGreater(table.count(UNKNOWN), 0, kind)
            self.assertEqual(BARE.findall(table), [], kind)

    def test_resource_profiles_have_no_unmarked_unknowns(self):
        profiled = [row for row in ROWS if row["review_status"] == "curated" and (row["details"].get("benchmark_protocol") or row["details"].get("dataset_profile"))]
        self.assertGreater(len(profiled), 100)
        marked = 0
        for row in profiled:
            html = resource_profile_html(row)
            self.assertEqual(BARE.findall(html), [], row["id"])
            marked += html.count(UNKNOWN)
        self.assertGreater(marked, 0)

    def test_unknown_values_are_styled_apart_from_data(self):
        css = (ROOT / "web/pages.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.unknown-value\{color:var\(--faint\);font-style:italic\}")


if __name__ == "__main__":
    unittest.main()
