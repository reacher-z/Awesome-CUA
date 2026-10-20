import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'web' / 'styles.css').read_text(encoding='utf-8')
HTML = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')


class HomePhoneIntroTests(unittest.TestCase):
    def setUp(self):
        match = re.search(r'@media\(max-width:760px\)\{\.hero\{padding-block:20px 16px\}.*?\}\}', CSS)
        self.assertIsNotNone(match, 'compact phone introduction rule is missing')
        self.phone = match.group(0)

    def test_phone_intro_hides_only_repeated_or_decorative_text(self):
        for hidden in ('.hero-caption{display:none}', '.agent-entry-copy{display:none}', '.agent-entry-links a>span{display:none}'):
            self.assertIn(hidden, self.phone)
        # Hidden text stays in the page for other widths and for the Chinese interface.
        for key in ('heroCaption', 'agentCopy', 'agentGuideCopy'):
            self.assertIn(f'data-i18n="{key}"', HTML)

    def test_links_and_buttons_keep_their_tap_targets(self):
        self.assertIn('.agent-entry-links a{display:flex;min-height:36px', self.phone)
        self.assertIn('.hero .button{min-height:44px', self.phone)
        self.assertIn('.agent-search summary{min-height:36px', self.phone)

    def test_rule_follows_the_existing_phone_rules(self):
        last_phone_rule = CSS.index('@media(max-width:760px){.hero{padding-block:29px 25px;display:block}')
        self.assertGreater(CSS.index(self.phone), last_phone_rule)


if __name__ == '__main__':
    unittest.main()
