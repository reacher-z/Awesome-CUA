"""Markdown twins for hand-written pages: the page's <main> content converted to Markdown."""
from __future__ import annotations

from html.parser import HTMLParser
import re

SKIP = {'script', 'style', 'svg', 'button', 'nav', 'form', 'noscript', 'template'}
BLOCK = {'p', 'div', 'section', 'article', 'ul', 'ol', 'li', 'table', 'details', 'summary', 'dl', 'dt', 'dd', 'pre', 'blockquote', 'figure', 'header', 'footer', 'aside'}


class Converter(HTMLParser):
    def __init__(self, site):
        super().__init__(convert_charrefs=True)
        self.site, self.out, self.skip, self.links, self.pre, self.main, self.lists = site, [], 0, [], False, 0, []
        self.cells, self.head = 0, False

    def text(self, value):
        self.out.append(value)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'main':
            self.main += 1
        if not self.main or self.skip:
            self.skip += tag in SKIP and self.main > 0
            return
        if tag in SKIP or 'vh' in (attrs.get('class') or '').split() and tag == 'nav':
            self.skip += 1
        elif re.fullmatch(r'h[1-6]', tag):
            self.text('\n\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'li':
            self.text('\n' + '  ' * max(len(self.lists) - 1, 0) + ('1. ' if self.lists and self.lists[-1] == 'ol' else '- '))
        elif tag in ('ul', 'ol'):
            self.lists.append(tag)
            self.text('\n')
        elif tag == 'a' and attrs.get('href'):
            href = attrs['href']
            self.links.append(self.site + href if href.startswith('/') else href)
            self.text('[')
        elif tag == 'code' and not self.pre:
            self.text('`')
        elif tag == 'pre':
            self.pre = True
            self.text('\n\n```\n')
        elif tag == 'tr':
            self.cells, self.head = 0, False
            self.text('\n| ')
        elif tag in ('td', 'th'):
            self.head = self.head or tag == 'th'
        elif tag == 'br':
            self.text('\n')
        elif tag in BLOCK:
            self.text('\n\n')

    def handle_endtag(self, tag):
        if tag == 'main':
            self.main -= 1
            return
        if not self.main:
            return
        if self.skip:
            self.skip -= tag in SKIP or tag == 'nav'
            return
        if tag == 'a' and self.links:
            self.text(f']({self.links.pop()})')
        elif tag == 'code' and not self.pre:
            self.text('`')
        elif tag == 'pre':
            self.pre = False
            self.text('\n```\n\n')
        elif tag in ('td', 'th'):
            self.cells += 1
            self.text(' | ')
        elif tag == 'tr':
            self.text('\n|' + ' --- |' * self.cells if self.head else '')
        elif tag in ('ul', 'ol') and self.lists:
            self.lists.pop()
            self.text('\n')
        elif re.fullmatch(r'h[1-6]', tag) or tag in BLOCK:
            self.text('\n')

    def handle_data(self, data):
        if self.main and not self.skip:
            self.text(data if self.pre else re.sub(r'\s+', ' ', data))


def page_markdown(markup, site):
    """Markdown for the <main> element of a built page: headings, paragraphs, lists, links and code."""
    parser = Converter(site)
    parser.feed(markup)
    text = ''.join(parser.out)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return re.sub(r'(?m)^ (?=\S)', '', text) + '\n'
