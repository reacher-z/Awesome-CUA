import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / 'web'
STYLES = (WEB / 'styles.css').read_text(encoding='utf-8')
PAGES = (WEB / 'pages.css').read_text(encoding='utf-8')
WIDE = '.reading-shell:is(:has(.compare-table),:has(.paper-library),:has(.topic-directory),:has(.data-hub))'


class WideGutterTests(unittest.TestCase):
    def test_wide_pages_use_the_shell_width_at_each_desktop_breakpoint(self):
        shell = re.search(r'(?:^|\})\.shell\{width:([^;}]+)', STYLES).group(1)
        medium = re.search(r'@media\(max-width:1150px\)\{\.shell\{width:([^;}]+)', STYLES).group(1)
        self.assertIn('@media(min-width:761px){' + WIDE + '{width:' + shell + '}}', PAGES)
        self.assertIn('@media(min-width:761px) and (max-width:1150px){' + WIDE + '{width:' + medium + '}}', PAGES)

    def test_override_follows_every_wide_page_width_rule(self):
        override = PAGES.index('@media(min-width:761px){' + WIDE)
        for page in ('compare-table', 'paper-library', 'topic-directory', 'data-hub'):
            for match in re.finditer(r'\.reading-shell:has\(\.' + page + r'\)\{width:min\(', PAGES):
                self.assertLess(match.start(), override, page)


if __name__ == '__main__':
    unittest.main()
