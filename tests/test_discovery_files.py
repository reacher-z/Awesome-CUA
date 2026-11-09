"""robots.txt, the sitemap index, the Atom and JSON feeds and curated-only counts in a real site build."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
import urllib.robotparser
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_site import build_site
from site_fixture import shared_site
from catalog import editorial_identity
from discovery_files import CONTENT_SIGNAL, CRAWLERS, FEED_SIZE, crawler_tokens, robots_txt
from search_pages import SITE, eligible, resource_path
from site_data import catalog_counts, record_modified, utc
from sitemaps import SECTIONS, SITEMAP_NS, XHTML_NS, section_file, sitemap_urls

NS = {'s': SITEMAP_NS, 'x': XHTML_NS, 'a': 'http://www.w3.org/2005/Atom'}
# Crawlers that GOAL A6 requires robots.txt to name explicitly.
REQUIRED = ('GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-User', 'Claude-SearchBot', 'PerplexityBot',
            'Perplexity-User', 'Google-Extended', 'Applebot-Extended', 'CCBot', 'Amazonbot', 'meta-externalagent',
            'DuckAssistBot', 'MistralAI-User', 'bingbot', 'Googlebot')


class HreflangParser(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.alternates = {}
        self.feed(text.split('</head>', 1)[0])
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'link' and a.get('rel') == 'alternate' and 'hreflang' in a:
            self.alternates[a['hreflang']] = a['href']


class RobotsTests(unittest.TestCase):
    def test_every_named_crawler_and_any_other_agent_may_fetch_everything(self):
        text = robots_txt(SITE)
        parser = urllib.robotparser.RobotFileParser(); parser.parse(text.splitlines())
        for agent in [*crawler_tokens(), 'SomeFutureBot', 'Mozilla/5.0']:
            for path in ('/', '/resources/arxiv-2404-07972/', '/api/v1/resources.json', '/llms-full.txt'):
                self.assertTrue(parser.can_fetch(agent, SITE + path), (agent, path))
        self.assertNotRegex(text, r'(?im)^Disallow:')
        self.assertEqual(parser.site_maps(), [SITE + '/sitemap.xml', SITE + '/sitemap.txt'])

    def test_required_crawlers_are_named_with_valid_tokens_in_one_allow_all_group(self):
        named = re.findall(r'(?m)^User-agent: (\S+)$', robots_txt(SITE))
        self.assertEqual(len(named), len(set(name.lower() for name in named)))
        self.assertEqual(set(REQUIRED) - set(named), set())
        for token in named:
            if token != '*':
                self.assertRegex(token, r'^[A-Za-z_-]+$')  # RFC 9309 product-token grammar
        # A blank line ends a group in common parsers, so the named crawlers must not be separated by one.
        block = robots_txt(SITE).split('User-agent: ' + CRAWLERS[0][1][0], 1)[1].split('\n\n', 1)[0]
        self.assertEqual(block.count('User-agent: '), len(crawler_tokens()) - 1)
        self.assertIn('Allow: /', block); self.assertIn('Content-Signal: ' + CONTENT_SIGNAL, block)

    def test_training_preference_token_is_its_own_allow_group(self):
        text = robots_txt(SITE)
        self.assertNotIn('ai-train', text); self.assertNotIn('__usage', text)
        self.assertIn('User-agent: *\nContent-Signal: ' + CONTENT_SIGNAL + '\nAllow: /\n', text)


class BuiltDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); cls.dest = shared_site()
        cls.rows = [json.loads(line) for line in (ROOT / 'data/catalog.jsonl').read_text().splitlines() if line.strip()]
        cls.by_path = {resource_path(row): row for row in cls.rows}
        cls.manifest = json.loads((cls.dest / 'data/search-manifest.json').read_text())
        cls.coverage = json.loads((ROOT / 'data/coverage.json').read_text())
        editorial = json.loads((ROOT / 'data/editorial.json').read_text())
        cls.reviewed = {(e.get('id') or editorial_identity(e)[0]): utc(e['reviewed_at']) for e in editorial if e.get('editorial_reviewed') and e.get('reviewed_at')}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def sitemap_entries(self):
        index = ET.parse(self.dest / 'sitemap.xml').getroot()
        self.assertEqual(index.tag, f'{{{SITEMAP_NS}}}sitemapindex')
        entries = {}
        for item in index.findall('s:sitemap', NS):
            loc = item.find('s:loc', NS).text
            name = loc.removeprefix(SITE + '/')
            self.assertIn(name, [section_file(section) for section in SECTIONS])
            urlset = ET.parse(self.dest / name).getroot()
            urls = urlset.findall('s:url', NS)
            self.assertLessEqual(len(urls), 50_000)
            dates = [url.find('s:lastmod', NS).text for url in urls if url.find('s:lastmod', NS) is not None]
            self.assertEqual(item.find('s:lastmod', NS).text, max(dates), name)
            for url in urls:
                path = url.find('s:loc', NS).text.removeprefix(SITE)
                self.assertNotIn(path, entries)
                lastmod = url.find('s:lastmod', NS)
                entries[path] = {'file': name, 'lastmod': lastmod.text if lastmod is not None else None,
                                 'alternates': {link.get('hreflang'): link.get('href') for link in url.findall('x:link', NS)}}
        return entries

    def test_sitemap_index_splits_pages_by_section_and_lists_only_indexable_pages(self):
        entries = self.sitemap_entries()
        indexable = {page['path'] for page in self.manifest['pages'] if page['indexable']}
        self.assertEqual(set(entries), indexable)
        self.assertEqual({entry['file'] for entry in entries.values()}, {section_file(section) for section in SECTIONS})
        for path, entry in entries.items():
            if path in self.by_path:
                expected = 'papers' if self.by_path[path]['kind'] in {'paper', 'survey'} else 'resources'
                self.assertEqual(entry['file'], section_file(expected), path)
        self.assertEqual(entries['/categories/model/']['file'], section_file('categories'))
        self.assertEqual(entries['/topics/']['file'], section_file('categories'))
        self.assertEqual(entries['/papers/']['file'], section_file('papers'))
        self.assertEqual(entries['/about/']['file'], section_file('pages'))
        self.assertEqual(sorted((self.dest / 'sitemap.txt').read_text().splitlines()), sorted(SITE + path for path in entries))
        self.assertEqual(sorted(sitemap_urls(self.dest, SITE)), sorted(SITE + path for path in entries))

    def test_resource_lastmod_is_the_latest_recorded_time_behind_the_page(self):
        entries = self.sitemap_entries()
        sources = {}
        for row in self.rows:
            for relation in row['relations']:
                sources.setdefault(relation['target_id'], []).append(row)
        def recorded(row):
            times = [row['last_verified_at'], *(e['retrieved_at'] for e in row['evidence'])]
            if eligible(row):
                times.append(self.reviewed[row['id']])
            return max(utc(value) for value in times)
        checked = 0
        for row in self.rows:
            if not eligible(row):
                continue
            expected = max([recorded(row)] + [recorded(source) for source in sources.get(row['id'], [])])
            self.assertEqual(entries[resource_path(row)]['lastmod'], expected, row['id'])
            checked += 1
        self.assertGreater(checked, 1000)

    def test_every_lastmod_is_a_recorded_data_time(self):
        recorded = {utc(row['last_verified_at']) for row in self.rows}
        recorded |= {utc(e['retrieved_at']) for row in self.rows for e in row['evidence']}
        recorded |= set(self.reviewed.values())
        recorded.add(self.coverage['as_of_utc'])
        scan = json.loads((ROOT / 'data/scan-status.json').read_text())
        recorded.add(scan['finished_at'])
        survey = self.dest / 'survey/build-manifest.json'
        if survey.exists():
            recorded.add(json.loads(survey.read_text())['working_manuscript_date'])
        dated = [entry['lastmod'] for entry in self.sitemap_entries().values() if entry['lastmod']]
        self.assertGreater(len(dated), 0.95 * len(self.sitemap_entries()))
        self.assertEqual(sorted(set(dated) - recorded), [])
        for value in dated:
            self.assertRegex(value, r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$')

    def test_sitemap_hreflang_alternates_match_the_pages_and_are_reciprocal(self):
        entries = self.sitemap_entries()
        paired = 0
        for path, entry in entries.items():
            page = HreflangParser((self.dest / path.lstrip('/') / 'index.html').read_text()).alternates
            self.assertEqual(entry['alternates'], page, path)
            if not page:
                continue
            paired += 1
            self.assertIn(SITE + path, page.values(), path)
            self.assertIn('x-default', page)
            for href in page.values():
                other = entries[href.removeprefix(SITE)]
                self.assertEqual(other['alternates'], entry['alternates'], (path, href))
        self.assertGreaterEqual(paired, 200)
        self.assertEqual(entries['/agents/']['alternates']['zh-CN'], SITE + '/zh/agents/')

    def test_feeds_announce_the_newest_reviewed_records_in_both_formats(self):
        atom = ET.parse(self.dest / 'feed.xml').getroot()
        entries = atom.findall('a:entry', NS)
        self.assertEqual(len(entries), FEED_SIZE)
        self.assertGreaterEqual(len(entries), 50)
        published = [entry.find('a:published', NS).text for entry in entries]
        self.assertEqual(published, sorted(published, reverse=True))
        newest = max(self.reviewed[row['id']] for row in self.rows if eligible(row))
        self.assertEqual(published[0], newest)
        self.assertEqual(atom.find('a:link[@rel="self"]', NS).get('href'), SITE + '/feed.xml')
        ids = []
        for entry in entries:
            row = self.by_path[entry.find('a:id', NS).text.removeprefix(SITE)]
            self.assertTrue(eligible(row), row['id'])
            self.assertEqual(entry.find('a:published', NS).text, self.reviewed[row['id']])
            self.assertEqual(entry.find('a:summary', NS).text, ' '.join(row['summary'].split()))
            ids.append(entry.find('a:id', NS).text)
        feed = json.loads((self.dest / 'feed.json').read_text())
        self.assertEqual(feed['version'], 'https://jsonfeed.org/version/1.1')
        self.assertEqual(feed['feed_url'], SITE + '/feed.json')
        self.assertEqual([item['id'] for item in feed['items']], ids)
        for item in feed['items']:
            self.assertEqual(item['_awesomecua']['review_status'], 'curated')
            self.assertTrue(item['url'].startswith(SITE + '/resources/'))
            self.assertRegex(item['date_published'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
        home = (self.dest / 'index.html').read_text()
        for markup in (home, (self.dest / 'about/index.html').read_text()):
            self.assertIn('type="application/atom+xml"', markup); self.assertIn('type="application/feed+json"', markup)

    def test_every_page_head_links_exactly_one_atom_and_one_json_feed(self):
        for page in sorted(self.dest.rglob('index.html')):
            head = page.read_text().split('</head>', 1)[0]
            if 'rel="canonical"' not in head or '/survey/' in page.as_posix():
                continue
            self.assertEqual(head.count('type="application/atom+xml"'), 1, page)
            self.assertEqual(head.count('type="application/feed+json"'), 1, page)
            self.assertNotIn('research updates', head, page)

    def test_index_counts_are_curated_only_and_report_pending_populations_separately(self):
        counts = json.loads((self.dest / 'data/index.json').read_text())['counts']
        curated = [row for row in self.rows if eligible(row)]
        self.assertEqual(counts['curated']['total'], len(curated))
        self.assertEqual(sum(counts['curated']['by_kind'].values()), len(curated))
        self.assertEqual(counts['curated']['papers_and_surveys'] + counts['curated']['other_resources'], len(curated))
        self.assertEqual(counts['awaiting_review']['metadata_only_records'], sum(row['review_status'] == 'metadata_verified' for row in self.rows))
        self.assertEqual(counts['active_records'], len(self.rows))
        self.assertLess(counts['curated']['total'], counts['active_records'])
        self.assertEqual(counts, catalog_counts(self.rows, self.coverage, json.loads((ROOT / 'data/github-candidates-manifest.json').read_text())))

    def test_robots_file_is_the_shared_policy(self):
        self.assertEqual((self.dest / 'robots.txt').read_text(), robots_txt(SITE))


class RecordDateTests(unittest.TestCase):
    def test_record_modified_takes_the_latest_review_verification_or_evidence_time(self):
        row = {'id': 'x', 'review_status': 'curated', 'scope': 'core', 'last_verified_at': '2026-10-01T00:00:00Z',
               'evidence': [{'retrieved_at': '2026-10-03T01:02:03.5+00:00'}]}
        self.assertEqual(record_modified(row, {}), '2026-10-03T01:02:03Z')
        self.assertEqual(record_modified(row, {'x': '2026-10-04T00:00:00Z'}), '2026-10-04T00:00:00Z')
        # A review time applies only while the record is curated.
        self.assertEqual(record_modified({**row, 'review_status': 'metadata_verified'}, {'x': '2026-10-04T00:00:00Z'}), '2026-10-03T01:02:03Z')
        with self.assertRaises(ValueError):
            utc('2026-10-04T00:00:00')


if __name__ == '__main__':
    unittest.main()
