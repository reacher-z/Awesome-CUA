import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from search_pages import incoming_relations, resource_body, utc_time  # noqa: E402

ROWS = [json.loads(line) for line in (ROOT / 'data/catalog.jsonl').read_text(encoding='utf-8').splitlines()]
LOOKUP = {row['id']: row for row in ROWS}
INCOMING = incoming_relations(ROWS)


class ResourceFactsTests(unittest.TestCase):
    def setUp(self):
        self.html = resource_body(LOOKUP['arxiv:2404.07972'], LOOKUP, INCOMING)
        self.facts = re.search(r'<dl class="page-facts">(.*?)</dl>', self.html).group(1)

    def test_facts_use_labels_links_and_readable_times(self):
        self.assertIn('<dt>Category</dt><dd><a href="/categories/paper/">Research papers</a></dd>', self.facts)
        self.assertIn('<dt>Platforms</dt><dd>Desktop, Linux, Windows, macOS</dd>', self.facts)
        self.assertIn('<a href="/topics/evaluation/">Evaluation</a>', self.facts)
        self.assertRegex(self.facts, r'<time datetime="2026-[^"]+">2026-\d\d-\d\d \d\d:\d\d UTC</time>')
        self.assertNotIn('Explore related topics', self.html)

    def test_connected_assets_follow_the_facts(self):
        self.assertIn('id="connected-assets"', self.html)
        self.assertLess(self.html.index('id="connected-assets"'), self.html.index('<h2>Recorded paper version</h2>'))
        self.assertLess(self.html.index('</dl>'), self.html.index('id="connected-assets"'))

    def test_times_convert_offsets_to_utc_and_keep_the_recorded_value(self):
        self.assertEqual(utc_time('2026-10-18T13:06:20.028238+00:00'), '<time datetime="2026-10-18T13:06:20.028238+00:00">2026-10-18 13:06 UTC</time>')
        self.assertEqual(utc_time('2026-10-18T15:06:20+02:00'), '<time datetime="2026-10-18T15:06:20+02:00">2026-10-18 13:06 UTC</time>')
        self.assertEqual(utc_time('not a time <b>'), 'not a time &lt;b&gt;')

    def test_unspecified_platform_reads_as_not_specified(self):
        row = {**LOOKUP['arxiv:2404.07972'], 'environments': ['unspecified']}
        self.assertIn('<dt>Platforms</dt><dd>Not specified</dd>', resource_body(row, LOOKUP, INCOMING))


if __name__ == '__main__':
    unittest.main()
