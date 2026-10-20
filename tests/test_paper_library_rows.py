import re
import unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / 'web' / 'pages.css').read_text(encoding='utf-8')
SCROLLER = '.paper-library :is(.paper-years,.library-topics){flex-wrap:nowrap;overflow-x:auto'


class PaperLibraryRowTests(unittest.TestCase):
    def test_phone_year_and_topic_shortcuts_scroll_in_one_row(self):
        phone = re.search(r'@media\(max-width:760px\)\{\.paper-library :is\(\.paper-years,\.library-topics\)\{.*?\}\}', CSS)
        self.assertIsNotNone(phone)
        self.assertIn(SCROLLER, phone.group(0))
        # Topic links keep a tap target of at least 24 px once they sit in one row.
        self.assertRegex(phone.group(0), r'\.library-topics a\{[^}]*min-height:(2[4-9]|[3-9]\d)px')

    def test_scroller_follows_the_existing_phone_rules_and_spares_other_pages(self):
        self.assertGreater(CSS.index(SCROLLER), CSS.index('@media(max-width:760px){.reading-shell:has(.paper-library)'))
        # The paper category hub lists every topic, so its rows keep wrapping.
        self.assertNotRegex(CSS, r'(?:^|[}\s])\.library-topics\{[^}]*flex-wrap:nowrap')


if __name__ == '__main__':
    unittest.main()
