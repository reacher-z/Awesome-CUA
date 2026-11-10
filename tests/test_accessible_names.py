"""An aria-label must contain the element's visible text (WCAG 2.5.3 Label in Name, axe label-content-name-mismatch)."""
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import home_page  # noqa: E402
import site_shell  # noqa: E402

WIDGET_TAGS = {'a', 'button', 'summary', 'label'}
WIDGET_ROLES = {'button', 'link', 'tab', 'menuitem', 'option', 'checkbox', 'radio', 'switch'}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


class LabelInName(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.failures = [], []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        attrs = dict(attrs)
        hidden = attrs.get('aria-hidden') == 'true' or any(frame['hidden'] for frame in self.stack)
        widget = tag in WIDGET_TAGS or attrs.get('role') in WIDGET_ROLES
        self.stack.append({'tag': tag, 'label': attrs.get('aria-label') if widget else None, 'text': [], 'hidden': hidden})

    def handle_data(self, data):
        for frame in self.stack:
            if not self.stack[-1]['hidden']:
                frame['text'].append(data)

    def handle_endtag(self, tag):
        if tag in VOID or not self.stack:
            return
        frame = self.stack.pop()
        text = ' '.join(''.join(frame['text']).split())
        if frame['label'] is not None and re.search(r'\w{2,}', text):
            if text.casefold() not in ' '.join(frame['label'].split()).casefold():
                self.failures.append(f'<{frame["tag"]} aria-label="{frame["label"]}"> shows "{text}"')


def failures(markup):
    parser = LabelInName()
    parser.feed(markup)
    return parser.failures


class AccessibleNameTests(unittest.TestCase):
    def test_header_controls_name_their_visible_text(self):
        for lang in ('en', 'zh-CN'):
            for live in (False, True):
                with self.subTest(lang=lang, live=live):
                    self.assertEqual(failures(site_shell.top(lang=lang, live=live)), [])

    def test_year_bars_name_their_visible_count_and_year(self):
        view = {'years': {2019: 39, 2022: 16, 2025: 514, 2026: 879},
                'year_links': {language: {str(year): f'/papers/#papers-{year}' for year in (2022, 2025, 2026)} for language in ('en', 'zh')}}
        for zh in (False, True):
            with self.subTest(zh=zh):
                markup = home_page.year_chart(view, zh=zh)
                self.assertIn('879', markup)
                self.assertEqual(failures(markup), [])


if __name__ == '__main__':
    unittest.main()
