"""Export contracts for date precision and a complete compact catalog."""
import copy
import json
from pathlib import Path
import re
import sys
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from agent_files import FULL_ORDER, compact_entry, llms_full
from search_pages import KINDS, SITE, description, resource_path
from site_data import catalog_counts, eligible, review_dates
from static_api import _schema, change_events, paper_item, resource_item


class ReviewPrecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(line) for line in (ROOT / 'data/catalog.jsonl').read_text().splitlines() if line]
        cls.defs = _schema(SITE, '2026-11-07T00:00:00Z')['$defs']

    def validator(self, name):
        return Draft202012Validator({'$defs': self.defs, '$ref': '#/$defs/' + name})

    def test_date_only_reviews_retain_precision_in_items_and_events(self):
        for kind, make_item in [('resource', resource_item), ('paper', paper_item)]:
            record = next(r for r in self.rows if eligible(r) and (r['kind'] == 'paper' if kind == 'paper' else r['kind'] == 'tool'))
            reviewed = {record['id']: '2026-11-04'}
            item = make_item(record, SITE, resource_path, reviewed)
            with self.subTest(kind=kind):
                self.assertEqual(item['reviewed_at'], '2026-11-04')
                self.assertEqual(list(self.validator(kind).iter_errors(item)), [])
            events, _ = change_events([record], reviewed, [], [], '2026-11-07T00:00:00Z', SITE, resource_path)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]['date'], '2026-11-04')
            self.assertEqual(list(self.validator('change').iter_errors(events[0])), [])

    def test_review_schema_rejects_partial_or_unzoned_times_and_keeps_observation_times_strict(self):
        record = next(r for r in self.rows if eligible(r) and r['kind'] == 'tool')
        item = resource_item(record, SITE, resource_path, {record['id']: '2026-11-04T12:34:56Z'})
        self.assertEqual(list(self.validator('resource').iter_errors(item)), [])
        for invalid in ['2026', '2026-11', '2026-11-04T12:34:56', '2026-11-04junk', '']:
            with self.subTest(invalid=invalid):
                self.assertTrue(list(self.validator('resource').iter_errors({**item, 'reviewed_at': invalid})))
        self.assertTrue(list(self.validator('resource').iter_errors({**item, 'last_verified_at': '2026-11-04'})))
        self.assertEqual(list(self.validator('resource').iter_errors({**item, 'reviewed_at': None})), [])


class CompactCatalogTests(unittest.TestCase):
    def test_current_catalog_fits_without_dropping_curated_records_or_primary_links(self):
        rows = [json.loads(line) for line in (ROOT / 'data/catalog.jsonl').read_text().splitlines() if line]
        curated = [r for r in rows if eligible(r)]
        counts = catalog_counts(rows, json.loads((ROOT / 'data/coverage.json').read_text()))
        dates = review_dates(ROOT)
        groups = []
        for kind in FULL_ORDER:
            members = [r for r in curated if r['kind'] == kind]
            groups.append((KINDS[kind], [compact_entry(r, site=SITE, page_path=resource_path(r), summary=description(r),
                reviewed_at=dates.get(r['id']), kind_label=KINDS[kind]) for r in members]))
        text = llms_full(groups, site=SITE, snapshot=counts['snapshot'], counts=counts, survey_line='', kind_files=[])
        self.assertLess(len(text.encode()), 1_600_000)
        listed = re.findall(r'^- (https://awesomecua\.com/resources/[^ ]+/) · source:', text, re.M)
        self.assertEqual(len(listed), len(curated))
        self.assertEqual(set(listed), {SITE + resource_path(r) for r in curated})
        for row in curated:
            source = (row['details'].get('arxiv_snapshot') or {}).get('versioned_url') or row['url']
            self.assertIn(' · source: ' + source + '\n', text)

    def test_compact_record_keeps_summary_and_date_with_full_annotation_link(self):
        row = next(json.loads(line) for line in (ROOT / 'data/catalog.jsonl').read_text().splitlines()
                   if json.loads(line)['kind'] == 'tool' and json.loads(line)['review_status'] == 'curated')
        before = copy.deepcopy(row)
        text = compact_entry(row, site=SITE, page_path=resource_path(row), summary='A source-backed tool summary.',
                             reviewed_at='2026-11-04', kind_label='Tool')
        self.assertIn('A source-backed tool summary.', text)
        self.assertIn('reviewed 2026-11-04', text)
        self.assertIn(SITE + resource_path(row), text)
        self.assertEqual(row, before)


if __name__ == '__main__':
    unittest.main()
