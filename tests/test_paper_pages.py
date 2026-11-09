"""One paginated, canonical list of reviewed papers; the paper category is a hub into it."""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import paper_library
from build_site import build_site
from paper_library import library_pages, library_path, library_years
from search_pages import SITE, resource_path
from sitemaps import sitemap_urls
from test_paper_library import LibraryParser, record

BUDGET = 150_000


def entries(markup):
    # A listed entry is an <article> whose first resource link names the record it shows.
    return {m[1] for m in (re.search(r'href="(/resources/[^"]+)"', block) for block in re.findall(r'<article\b.*?</article>', markup, re.S)) if m}


class PaginationTests(unittest.TestCase):
    # Two per page: 2026 spans pages 1-2 and 2025 spans pages 2-3.
    rows = [record(f'p{i}', date) for i, date in enumerate(['2026-03-01', '2026-02-01', '2026-01-01', '2025-02-01', '2025-01-01'])]

    def render(self, number, language='en'):
        markup, schema = paper_library.paper_library(self.rows, resource_path, language=language, number=number)
        return LibraryParser(markup), markup, schema

    def test_pages_partition_the_library_in_date_order_with_page_scoped_item_lists(self):
        with mock.patch.object(paper_library, 'PAGE_SIZE', 2):
            self.assertEqual(library_pages(self.rows), 3)
            seen = []
            for number in (1, 2, 3):
                parsed, _, schema = self.render(number)
                self.assertEqual(schema['numberOfItems'], len(parsed.records))
                self.assertEqual([item['position'] for item in schema['itemListElement']],
                                 list(range(len(seen) + 1, len(seen) + len(parsed.records) + 1)))
                seen += parsed.records
            self.assertEqual(seen, ['p0', 'p1', 'p2', 'p3', 'p4'])
            with self.assertRaises(ValueError):
                self.render(4)

    def test_pager_years_and_language_switch_resolve_to_real_pages(self):
        with mock.patch.object(paper_library, 'PAGE_SIZE', 2):
            ids = {library_path(n, language): self.render(n, language)[0].ids for n in (1, 2, 3) for language in ('en', 'zh')}
            for language in ('en', 'zh'):
                for number in (1, 2, 3):
                    path = library_path(number, language)
                    parsed, markup, _ = self.render(number, language)
                    self.assertEqual(re.findall(r'<a href="([^"]+)"[^>]*aria-current="page"', markup), [path])
                    self.assertEqual('rel="prev"' in markup, number > 1)
                    self.assertEqual('rel="next"' in markup, number < 3)
                    self.assertIn(library_path(number, 'zh' if language == 'en' else 'en'), parsed.links)
                    for link in parsed.links:
                        target, _, anchor = link.partition('#')
                        if anchor and target in ('', *ids):
                            self.assertIn(anchor, ids[target or path], (path, link))
            self.assertEqual(library_years(self.rows), {'2026': '/papers/#papers-2026', '2025': '/papers/page/2/#papers-2025'})
            self.assertEqual(library_years(self.rows, 'zh')['2025'], '/zh/papers/page/2/#papers-2025')
            self.assertIn('href="/papers/page/2/#papers-2025"', self.render(3)[1])

    def test_a_single_page_library_has_no_pager(self):
        _, markup, schema = self.render(1)
        self.assertNotIn('library-pager', markup)
        self.assertEqual(schema['numberOfItems'], 5)


class PaperPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.dest = build_site(cls.temp.name)
        cls.pages = {item['path']: item for item in json.loads((cls.dest / 'data/search-manifest.json').read_text())['pages']}
        cls.markup = {path: (cls.dest / path.lstrip('/') / 'index.html').read_text() for path in cls.pages
                      if re.match(r'/(zh/)?papers/|/categories/', path)}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_listing_pages_stay_within_the_byte_budget(self):
        self.assertIn('/papers/page/2/', self.markup)
        for path, markup in self.markup.items():
            self.assertLessEqual(len(markup.encode()), BUDGET, path)

    def test_paginated_category_lists_every_reviewed_record_once(self):
        paths = [path for path in self.markup if path == '/categories/framework/' or path.startswith('/categories/framework/page/')]
        self.assertGreater(len(paths), 1)
        listed = [url for path in paths for block in re.findall(r'<article\b.*?</article>', self.markup[path], re.S)
                  if (match := re.search(r'href="(/resources/[^"]+)"', block)) for url in [match[1]]]
        rows = [json.loads(line) for line in (Path(__file__).resolve().parents[1] / 'data/catalog.jsonl').read_text(encoding='utf-8').splitlines()]
        expected = {resource_path(row) for row in rows if row['kind'] == 'framework' and row['review_status'] == 'curated' and row['scope'] in {'core', 'adjacent'}}
        self.assertEqual(len(listed), len(set(listed)))
        self.assertEqual(set(listed), expected)
        for path in paths:
            pager = re.search(r'<nav class="pager"[^>]*>(.*?)</nav>', self.markup[path], re.S)
            self.assertIsNotNone(pager)
            self.assertEqual(set(re.findall(r'href="([^"]+)"', pager[1])), set(paths))
            self.assertTrue((self.dest / path.lstrip('/') / 'index.md').is_file())

    def test_no_two_indexable_listings_share_more_than_half_their_entries(self):
        # Chinese library pages are hreflang translations of the English pages, not competing duplicates.
        listed = {path: entries(markup) for path, markup in self.markup.items() if self.pages[path]['indexable'] and not path.startswith('/zh/')}
        for first, a in listed.items():
            for second, b in listed.items():
                if first < second and a and b:
                    self.assertLessEqual(len(a & b), min(len(a), len(b)) / 2, (first, second))

    def test_paper_category_is_a_hub_into_the_canonical_library(self):
        markup = self.markup['/categories/paper/']
        self.assertTrue(self.pages['/categories/paper/']['indexable'])
        self.assertEqual(entries(markup), set())
        self.assertNotIn('"ItemList"', markup)
        self.assertIn('href="/papers/"', markup)
        years = re.findall(r'href="(/papers/(?:page/\d+/)?)#(papers-[^"]+)"', markup)
        self.assertTrue(years)
        for path, anchor in years:
            self.assertIn(f'id="{anchor}"', self.markup[path])

    def test_library_pages_are_indexable_canonical_language_pairs_in_the_sitemap(self):
        sitemap = set(sitemap_urls(self.dest, SITE))
        numbers = [int(m[1] or 1) for path in self.markup if (m := re.fullmatch(r'/papers/(?:page/(\d+)/)?', path))]
        self.assertEqual(sorted(numbers), list(range(1, max(numbers) + 1)))
        for number in numbers:
            for language in ('en', 'zh'):
                path = library_path(number, language)
                self.assertTrue(self.pages[path]['indexable'], path)
                self.assertIn(SITE + path, sitemap)
                markup = self.markup[path]
                self.assertIn(f'<link rel="canonical" href="{SITE}{path}">', markup)
                self.assertIn(f'hreflang="{"en" if language == "zh" else "zh-CN"}" href="{SITE}{library_path(number, "zh" if language == "en" else "en")}"', markup)


if __name__ == '__main__':
    unittest.main()
