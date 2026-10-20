import re
import unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / 'web' / 'pages.css').read_text(encoding='utf-8')


class DataHubLayoutTests(unittest.TestCase):
    def setUp(self):
        match = re.search(r'@media\(min-width:761px\)\{\.download-row\{.*?\}\}', CSS)
        self.assertIsNotNone(match, 'wide-screen data hub rule is missing')
        self.wide = match.group(0)

    def test_count_size_and_actions_share_one_line_on_wide_screens(self):
        self.assertIn('.download-facts{flex-direction:row', self.wide)
        self.assertIn('.download-facts dd span{display:inline', self.wide)
        self.assertIn('.download-actions{flex-direction:row', self.wide)

    def test_scope_sits_beside_the_name_and_rows_stay_compact(self):
        self.assertIn('.download-scope{grid-column:2;grid-row:1}', self.wide)
        self.assertRegex(self.wide, r'\.download-row\{[^}]*padding:10px 0')

    def test_phone_layout_is_left_to_the_existing_rule(self):
        # The phone rule follows the wide-screen rule, so it is not overridden below 761 px.
        self.assertLess(CSS.index(self.wide), CSS.index('@media(max-width:760px){.reading-shell:has(.data-hub)'))


if __name__ == '__main__':
    unittest.main()
