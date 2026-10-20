import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from search_pages import listing, listing_facts  # noqa: E402

ROWS = {row['id']: row for row in map(json.loads, (ROOT / 'data/catalog.jsonl').read_text(encoding='utf-8').splitlines())}


class CategoryListingTests(unittest.TestCase):
    def test_entries_drop_the_repeated_overline_and_unrecorded_placeholders(self):
        benchmarks = [row for row in ROWS.values() if row['kind'] == 'benchmark' and row['review_status'] == 'curated']
        html = listing(benchmarks)
        self.assertNotIn('list-overline', html)
        self.assertNotIn('not recorded', html.lower())
        self.assertEqual(html.count('<article>'), len(benchmarks))

    def test_facts_use_platform_labels_paper_and_scoped_licenses(self):
        row = ROWS['github:thudm/agentbench']
        self.assertEqual(listing_facts(row)[0], 'Cross-platform, Web')
        self.assertIn('arXiv 2308.03688', listing_facts(row))
        self.assertIn('Code Apache-2.0', listing_facts(row))
        self.assertNotIn('cross-platform', listing([row]))

    def test_unspecified_platform_and_missing_facts_leave_no_empty_meta(self):
        row = {**ROWS['github:thudm/agentbench'], 'environments': ['unspecified'], 'relations': [], 'identifiers': {},
               'licenses': {slot: None for slot in ('code', 'data', 'weights', 'document')}, 'published_at': None}
        self.assertEqual(listing_facts(row), [])
        self.assertNotIn('<small>', listing([row]))

    def test_entry_text_is_escaped(self):
        row = {**ROWS['github:thudm/agentbench'], 'name': '<img src=x onerror=alert(1)>', 'summary': 'a <b> & c'}
        html = listing([row])
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)
        self.assertIn('a &lt;b&gt; &amp; c', html)


if __name__ == '__main__':
    unittest.main()
