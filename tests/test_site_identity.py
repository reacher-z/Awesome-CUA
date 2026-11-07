"""The visible catalog definition and its metadata agree without a production build."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from agent_files import home_markdown, llms_txt
import home_page
from search_pages import homepage_document, SITE, SOURCE_REPO
from site_identity import ALTERNATE_NAMES, DEFINITION, FULL_NAME, HOME_TITLE, NAME
import site_shell


class IdentityParser(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.title = ''
        self.lead = ''
        self.meta = {}
        self.canonical = []
        self.alternates = {}
        self.links = []
        self.h1_count = 0
        self.capture = None
        self.language = None
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html':
            self.language = attrs.get('lang')
        if tag == 'title':
            self.capture = 'title'
        if tag == 'p' and attrs.get('class') == 'hero-lede':
            self.capture = 'lead'
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'meta':
            self.meta[attrs.get('name') or attrs.get('property')] = attrs.get('content')
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical.append(attrs['href'])
        if tag == 'link' and attrs.get('rel') == 'alternate' and 'hreflang' in attrs:
            self.alternates[attrs['hreflang']] = attrs['href']
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])

    def handle_endtag(self, tag):
        if (tag, self.capture) in (('title', 'title'), ('p', 'lead')):
            self.capture = None

    def handle_data(self, data):
        if self.capture:
            setattr(self, self.capture, getattr(self, self.capture) + data)


class SiteIdentityTests(unittest.TestCase):
    def setUp(self):
        site_shell.configure()
        self.addCleanup(site_shell.configure)
        self.view = {'reviewed': [], 'papers': 0, 'candidates': 0}

    def document(self, zh=False):
        # The finder has its own tests; render the real hero, head and shared shell.
        with mock.patch.object(home_page, 'finder', return_value=''):
            return homepage_document(home_page.hero(self.view, None, zh=zh), zh=zh)

    def test_bilingual_homepages_expose_the_same_definition_as_their_metadata(self):
        for language, path, lang in (('en', '/', 'en'), ('zh', '/zh/', 'zh-CN')):
            with self.subTest(language=language):
                parsed = IdentityParser(self.document(zh=language == 'zh'))
                self.assertEqual(parsed.lead, DEFINITION[language])
                self.assertIn('Awesome CUA', parsed.lead)
                self.assertIn('Awesome Computer-Use Agents', parsed.lead)
                self.assertEqual(parsed.title, HOME_TITLE[language])
                self.assertEqual(parsed.title.count('Awesome CUA'), 1)
                self.assertNotIn(' | AwesomeCUA', parsed.title)
                self.assertEqual(parsed.meta['og:title'], parsed.title)
                self.assertEqual(parsed.meta['description'], parsed.lead)
                self.assertEqual(parsed.meta['og:description'], parsed.lead)
                self.assertEqual(parsed.language, lang)
                self.assertEqual(parsed.h1_count, 1)
                self.assertEqual(parsed.canonical, [SITE + path])
                self.assertEqual(parsed.meta['og:url'], SITE + path)
                self.assertEqual(parsed.meta['robots'], 'index,follow,max-image-preview:large')
                self.assertEqual(parsed.alternates, {'en': SITE + '/', 'zh-CN': SITE + '/zh/', 'x-default': SITE + '/'})
                self.assertIn(SOURCE_REPO, parsed.links)
                for link in ('/catalog/', '/papers/', '/data/') if language == 'en' else ('/catalog/', '/zh/papers/', '/zh/data/'):
                    self.assertIn(link, parsed.links)

    def test_website_aliases_are_supported_names_not_other_projects_or_domains(self):
        self.assertEqual(NAME, 'Awesome CUA')
        self.assertEqual(ALTERNATE_NAMES, ('AwesomeCUA', 'Awesome Computer-Use Agents'))
        self.assertIn(FULL_NAME, (ROOT / 'CITATION.cff').read_text(encoding='utf-8'))
        for zh in (False, True):
            markup = self.document(zh)
            graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', markup, re.S)[1])['@graph']
            website = next(item for item in graph if item['@type'] == 'WebSite')
            webpage = next(item for item in graph if item['@type'] == 'WebPage')
            organization = next(item for item in graph if item['@type'] == 'Organization')
            self.assertEqual(website['name'], NAME)
            self.assertEqual(website['alternateName'], list(ALTERNATE_NAMES))
            self.assertEqual(website['description'], DEFINITION['en'])
            self.assertEqual(website['@id'], SITE + '/#website')
            self.assertEqual(website['url'], SITE + '/')
            self.assertEqual(webpage['isPartOf'], {'@id': website['@id']})
            self.assertEqual(webpage['description'], DEFINITION['zh' if zh else 'en'])
            self.assertEqual(website['publisher'], {'@id': organization['@id']})
            self.assertIn(SOURCE_REPO, organization['sameAs'])
            self.assertNotIn('alternateName', organization)  # A catalog title is not an organization alias.

    def test_authored_readme_openings_match_the_visible_homepage_definitions(self):
        for filename, language in (('README.md', 'en'), ('README.zh-CN.md', 'zh')):
            with self.subTest(filename=filename):
                text = (ROOT / filename).read_text(encoding='utf-8')
                opening = text.split('<!-- BADGES:START -->', 1)[0]
                self.assertEqual(opening.split('\n\n', 2)[1], DEFINITION[language])
                self.assertIn('<h1 align="center">', opening)
                self.assertRegex(opening, r'alt="Awesome CUA[^"\n]+"')

    def test_markdown_entry_points_share_the_visible_definition_and_review_counts(self):
        counts = {'curated': {'total': 3, 'papers_and_surveys': 2, 'other_resources': 1},
                  'awaiting_review': {'metadata_only_records': 5, 'unresolved_candidate_identifiers': 7},
                  'note': 'Resource groups overlap.'}
        home = home_markdown([], [], site=SITE, counts=counts, snapshot='2026-11-07')
        index = llms_txt(site=SITE, counts=counts, kinds=[], library=[], topics=[], api_endpoints=[],
                         guides=[], survey_links=[], releases_url=SOURCE_REPO + '/releases')
        for text in (home, index):
            self.assertEqual(text.splitlines()[0], '# AwesomeCUA')
            self.assertTrue(text.splitlines()[2].startswith('> ' + DEFINITION['en']))
            self.assertIn('2 papers and surveys', text)
            self.assertIn('5 metadata-only bibliography records', text)
        self.assertIn('3 curated records', home)
        self.assertIn('3 curated resources', index)
        self.assertIn('7 discovered identifiers', home)
        self.assertIn('## Optional', index)
        self.assertIn(SOURCE_REPO + '.git', index)


if __name__ == '__main__':
    unittest.main()
