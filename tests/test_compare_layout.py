import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from search_pages import resource_path  # noqa: E402
from specifications import comparison_body, selected_profiles  # noqa: E402

ROWS = [json.loads(line) for line in (ROOT / 'data/catalog.jsonl').read_text(encoding='utf-8').splitlines()]


class CompareLayoutTests(unittest.TestCase):
    def test_every_cell_names_its_column_for_the_stacked_phone_layout(self):
        for kind in ('benchmark', 'dataset'):
            html = comparison_body(ROWS, kind, resource_path)
            columns = re.findall(r'<th scope="col">([^<]+)</th>', html)
            self.assertEqual(len(columns), 4)
            rows = re.findall(r'<tr data-profile-row.*?</tr>', html, re.S)
            self.assertEqual(len(rows), len(selected_profiles(ROWS, kind)))
            for row in rows:
                self.assertEqual(re.findall(r'<td data-label="([^"]+)">', row), columns)

    def test_platforms_use_display_labels_and_filters_keep_slug_values(self):
        html = comparison_body(ROWS, 'benchmark', resource_path)
        self.assertIn('<option value="web">Web</option>', html)
        self.assertIn('<option value="cross-platform">Cross-platform</option>', html)
        self.assertNotRegex(html, r'<option value="[^"]+">[a-z][a-z-]*</option>')
        self.assertRegex(html, r'data-environments="web"')
        self.assertNotIn('<div>web</div>', html)
        self.assertIn('Setting: interactive', html)

    def test_phone_stylesheet_stacks_the_table_and_hides_the_scroll_hint(self):
        css = (ROOT / 'web/pages.css').read_text(encoding='utf-8')
        phone = re.search(r'@media\(max-width:760px\)\{\.reading-shell \.compare-help\{display:none\}.*?\}\}', css)
        self.assertIsNotNone(phone)
        self.assertIn('.compare-table,.compare-table tbody,.compare-table tr,.compare-table td{display:block', phone.group(0))
        self.assertIn('content:attr(data-label)', phone.group(0))


if __name__ == '__main__':
    unittest.main()
