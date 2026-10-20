"""Topic hubs are split into crawlable, canonical pages that each stay within the HTML byte budget."""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import topic_pages
from build_site import build_site
from search_pages import SITE, resource_path
from topic_pages import topic_counts, topic_index_body, topic_page_count, topic_path, topic_sections
from test_paper_library import LibraryParser, record
from test_paper_pages import BUDGET


class TopicPaginationTests(unittest.TestCase):
    # Two per page: assets come first (benchmark and dataset on page 1, tool and the first paper on page 2), then the remaining papers on page 3.
    rows = [record('p0', '2026-03-01'), record('p1', '2026-02-01'), record('p2', '2026-01-01'),
            record('b0', None, kind='benchmark'), record('d0', None, kind='dataset'), record('t0', None, kind='tool')]

    def render(self, number, language='en'):
        markup, schema = topic_pages.topic_body('grounding', self.rows, resource_path, language=language, number=number)
        return LibraryParser(markup), markup, schema

    def test_pages_partition_the_topic_in_group_order_with_page_scoped_item_lists(self):
        with mock.patch.object(topic_pages, 'PAGE_SIZE', 2):
            self.assertEqual(topic_page_count(topic_counts(self.rows)), 3)
            seen = []
            for number in (1, 2, 3):
                parsed, _, schema = self.render(number)
                self.assertEqual(schema['numberOfItems'], len(parsed.records))
                self.assertEqual([item['position'] for item in schema['itemListElement']],
                                 list(range(len(seen) + 1, len(seen) + len(parsed.records) + 1)))
                seen += parsed.records
            self.assertEqual(seen, ['b0', 'd0', 't0', 'p0', 'p1', 'p2'])
            for number in (0, 4):
                with self.assertRaises(ValueError):
                    self.render(number)

    def test_pager_sections_and_language_switch_resolve_to_real_pages(self):
        with mock.patch.object(topic_pages, 'PAGE_SIZE', 2):
            ids = {topic_path('grounding', language, n): self.render(n, language)[0].ids for n in (1, 2, 3) for language in ('en', 'zh')}
            for language in ('en', 'zh'):
                for number in (1, 2, 3):
                    path = topic_path('grounding', language, number)
                    parsed, markup, _ = self.render(number, language)
                    self.assertEqual(re.findall(r'<a href="([^"]+)"[^>]*aria-current="page"', markup), [path])
                    self.assertEqual('rel="prev"' in markup, number > 1)
                    self.assertEqual('rel="next"' in markup, number < 3)
                    self.assertIn(topic_path('grounding', 'zh' if language == 'en' else 'en', number), parsed.links)
                    for link in parsed.links:
                        target, _, anchor = link.partition('#')
                        if anchor and anchor != 'content' and target in ('', *ids):
                            self.assertIn(anchor, ids[target or path], (path, link))
            self.assertEqual(topic_sections('grounding', topic_counts(self.rows)),
                             {'benchmarks': '/topics/grounding/#benchmarks', 'datasets': '/topics/grounding/#datasets',
                              'systems': '/topics/grounding/page/2/#systems', 'papers': '/topics/grounding/page/2/#papers'})
            manifest = {'resources_with_topics': 6, 'topics': [{'id': 'grounding', 'name': {'en': 'Grounding', 'zh': '定位'}, 'counts': topic_counts(self.rows)}]}
            for language in ('en', 'zh'):
                links = LibraryParser(topic_index_body(manifest, language=language)[0]).links
                for link in topic_sections('grounding', topic_counts(self.rows), language).values():
                    self.assertIn(link, links)
                    target, _, anchor = link.partition('#')
                    self.assertIn(anchor, ids[target], link)

    def test_a_single_page_topic_has_no_pager(self):
        _, markup, schema = self.render(1)
        self.assertNotIn('library-pager', markup)
        self.assertEqual(schema['numberOfItems'], 6)
        self.assertEqual(topic_path('grounding', 'zh', 1), '/zh/topics/grounding/')


class TopicPageBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.dest = build_site(cls.temp.name)
        cls.pages = {item['path']: item for item in json.loads((cls.dest / 'data/search-manifest.json').read_text())['pages']}
        cls.markup = {path: (cls.dest / path.lstrip('/') / 'index.html').read_text() for path in cls.pages if re.match(r'/(zh/)?topics/', path)}
        cls.topics = json.loads((cls.dest / 'downloads/topics.json').read_text())['topics']

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_topic_pages_stay_within_the_byte_budget(self):
        self.assertTrue(any('/page/' in path for path in self.markup))
        for path, markup in self.markup.items():
            self.assertLessEqual(len(markup.encode()), BUDGET, path)
            self.assertLessEqual(len(LibraryParser(markup).records), topic_pages.PAGE_SIZE, path)

    def test_every_topic_resource_is_reachable_from_the_topic_directory_through_links(self):
        for language in ('en', 'zh'):
            start = topic_path(language=language)
            seen, queue = {start}, [start]
            while queue:
                for link in LibraryParser(self.markup[queue.pop()]).links:
                    target = link.partition('#')[0]
                    if target in self.markup and target not in seen:
                        seen.add(target)
                        queue.append(target)
            self.assertEqual({path for path in seen if path.startswith(start)}, {path for path in self.markup if path.startswith(start)})
            for entry in self.topics:
                first = entry['pages'][language]
                listed = [rid for path in self.markup if path.startswith(first) for rid in LibraryParser(self.markup[path]).records]
                self.assertEqual(sorted(listed), sorted(entry['resource_ids']), first)

    def test_topic_pages_are_indexable_canonical_language_pairs_in_the_sitemap(self):
        sitemap = {x.text for x in ET.parse(self.dest / 'sitemap.xml').getroot().iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')}
        for path, markup in self.markup.items():
            match = re.fullmatch(r'(/zh)?/topics/(?:([a-z0-9-]+)/(?:page/(\d+)/)?)?', path)
            self.assertTrue(match, path)
            self.assertTrue(self.pages[path]['indexable'], path)
            self.assertIn(SITE + path, sitemap)
            self.assertIn(f'<link rel="canonical" href="{SITE}{path}">', markup)
            if match[2]:
                language, number = 'zh' if match[1] else 'en', int(match[3] or 1)
                other = topic_path(match[2], 'en' if language == 'zh' else 'zh', number)
                self.assertIn(other, self.markup)
                self.assertIn(f'hreflang="{"en" if language == "zh" else "zh-CN"}" href="{SITE}{other}"', markup)


if __name__ == '__main__':
    unittest.main()
