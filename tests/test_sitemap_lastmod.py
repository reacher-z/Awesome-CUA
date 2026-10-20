import json
from pathlib import Path
import random
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from catalog import editorial_identity
from search_pages import eligible, resource_lastmod, resource_path, utc_date


def row(rid, **fields):
    base = {"id": rid, "name": rid, "kind": "framework", "url": "https://github.com/example/" + rid.split(":")[-1],
            "review_status": "curated", "scope": "core", "updated_at": None}
    return {**base, **fields}


def review(rid, reviewed_at, **fields):
    return {"id": rid, "editorial_reviewed": True, "reviewed_at": reviewed_at, **fields}


class SitemapLastmodTests(unittest.TestCase):
    def test_review_date_is_normalized_to_utc(self):
        self.assertEqual(utc_date("2026-10-17T23:30:00Z"), "2026-10-17")
        self.assertEqual(utc_date("2026-10-18T01:30:00+08:00"), "2026-10-17")
        self.assertEqual(utc_date("2026-10-16T06:00:00.123456+00:00"), "2026-10-16")

    def test_only_reviewed_pages_get_the_later_of_review_and_source_update(self):
        rows = [row("github:example/a"), row("github:example/b", updated_at="2026-10-17"),
                row("github:example/c", updated_at="2025"), row("github:example/d", review_status="metadata_verified"),
                row("github:example/e", scope="relevance_pending"), row("github:example/f")]
        editorial = [review("github:example/a", "2026-10-16T06:00:00Z"), review("github:example/b", "2026-10-16T06:00:00Z"),
                     review("github:example/c", "2026-10-16T06:00:00Z"), review("github:example/d", "2026-10-16T06:00:00Z"),
                     review("github:example/e", "2026-10-16T06:00:00Z"),
                     {"id": "github:example/f", "editorial_reviewed": False, "reviewed_at": "2026-10-16T06:00:00Z"}]
        dates = resource_lastmod(rows, editorial, "2026-10-18T08:00:00Z")
        self.assertEqual(dates, {resource_path(rows[0]): "2026-10-16", resource_path(rows[1]): "2026-10-17", resource_path(rows[2]): "2026-10-16"})
        # A source tree without editorial decisions has no review dates, so no page gets a lastmod.
        self.assertEqual(resource_lastmod(rows, [], "2026-10-18T08:00:00Z"), {})

    def test_dates_never_pass_the_snapshot(self):
        rows = [row("github:example/a", updated_at="2026-12-01")]
        dates = resource_lastmod(rows, [review("github:example/a", "2026-11-01T00:00:00Z")], "2026-10-18T08:00:00Z")
        self.assertEqual(dates, {resource_path(rows[0]): "2026-10-18"})

    def test_catalog_dates_come_from_editorial_reviews_and_are_deterministic(self):
        rows = [json.loads(line) for line in (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        editorial = json.loads((ROOT / "data/editorial.json").read_text(encoding="utf-8"))
        snapshot = json.loads((ROOT / "data/coverage.json").read_text(encoding="utf-8"))["as_of_utc"]
        dates = resource_lastmod(rows, editorial, snapshot)
        shuffled = list(editorial)
        random.Random(0).shuffle(shuffled)
        self.assertEqual(dates, resource_lastmod(list(reversed(rows)), shuffled, snapshot))
        self.assertEqual(set(dates), {resource_path(r) for r in rows if eligible(r)})
        reviewed = {(e.get("id") or editorial_identity(e)[0]): utc_date(e["reviewed_at"]) for e in editorial if e.get("editorial_reviewed")}
        by_path = {resource_path(r): r for r in rows}
        for path, value in dates.items():
            self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}$", path)
            self.assertLessEqual(value, snapshot[:10], path)
            record = by_path[path]
            # Each value is the record's own review date, a later recorded source version, or the snapshot cap.
            self.assertIn(value, {reviewed.get(record["id"]), record["updated_at"], snapshot[:10]} - {None}, path)
            if record["id"] in reviewed:
                self.assertGreaterEqual(value, min(reviewed[record["id"]], snapshot[:10]), path)


if __name__ == "__main__":
    unittest.main()
