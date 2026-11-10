"""Every record URL belongs to one record unless the pair is declared in data/shared-urls.json."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build import shared_url_errors, shared_url_key  # noqa: E402


def row(rid, url):
    return {'id': rid, 'url': url}


class SharedUrlTests(unittest.TestCase):
    def test_spelling_variants_are_the_same_url(self):
        self.assertEqual(shared_url_key('https://www.Example.com/a/'), shared_url_key('http://example.com/a#top'))
        self.assertNotEqual(shared_url_key('https://example.com/a'), shared_url_key('https://example.com/b'))

    def test_undeclared_duplicates_fail_and_declared_pairs_pass(self):
        rows = [row('organization:x', 'https://x.dev/'), row('url:1', 'https://www.x.dev'), row('url:2', 'https://y.dev/')]
        self.assertEqual(len(shared_url_errors(rows, [])), 1)
        self.assertEqual(shared_url_errors(rows, [{'url': 'https://x.dev/', 'ids': ['url:1', 'organization:x'], 'reason': 'r'}]), [])

    def test_a_stale_or_widened_declaration_fails(self):
        rows = [row('organization:x', 'https://x.dev/'), row('url:1', 'https://x.dev/product')]
        self.assertIn('no longer shares', shared_url_errors(rows, [{'url': 'https://x.dev/', 'ids': ['organization:x', 'url:1'], 'reason': 'r'}])[0])
        third = rows[:1] + [row('url:1', 'https://x.dev/'), row('url:2', 'https://x.dev')]
        self.assertTrue(shared_url_errors(third, [{'url': 'https://x.dev/', 'ids': ['organization:x', 'url:1'], 'reason': 'r'}]))

    def test_missing_urls_are_left_to_the_record_checks(self):
        rows = [row('url:1', None), row('url:2', ''), row('url:3', 'https://x.dev/')]
        self.assertEqual(shared_url_errors(rows, []), [])

    def test_committed_catalog_has_only_declared_shared_urls(self):
        rows = [json.loads(line) for line in (ROOT / 'data/catalog.jsonl').read_text(encoding='utf-8').splitlines()]
        declared = json.loads((ROOT / 'data/shared-urls.json').read_text(encoding='utf-8'))
        self.assertEqual(shared_url_errors(rows, declared), [])


if __name__ == '__main__':
    unittest.main()
