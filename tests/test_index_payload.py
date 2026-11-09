"""The catalog index ships only list fields; each opened record loads its own small payload."""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_site import build_site


class IndexPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.dest = build_site(cls.temp.name)
        cls.index = json.loads((cls.dest / 'data/index.json').read_text())['records']
        cls.client = (ROOT / 'web/app.js').read_text() + (ROOT / 'web/catalog-core.js').read_text()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_index_omits_fields_only_the_detail_dialog_reads(self):
        for row in self.index:
            self.assertFalse({'scope', 'last_verified_at', 'published_at', 'paper_date_precision'} & row.keys(), row['id'])

    def test_every_index_field_is_read_by_the_client(self):
        keys = set().union(*(row.keys() for row in self.index))
        unread = sorted(key for key in keys if not re.search(r'\.' + key + r'\b', self.client))
        self.assertEqual(unread, [])

    def test_opening_a_record_fetches_one_small_payload_with_detail_fields(self):
        for row in self.index:
            path = self.dest / row['page_url'].lstrip('/') / 'record.json'
            # record.json is the complete, per-record lazy payload. Large author
            # lists stay intact here and in the public catalog exports.
            self.assertLess(path.stat().st_size, 32_000, row['id'])
            record = json.loads(path.read_text())
            self.assertEqual(record['id'], row['id'])
            self.assertIn('scope', record)
            self.assertIn('last_verified_at', record)


if __name__ == '__main__':
    unittest.main()
