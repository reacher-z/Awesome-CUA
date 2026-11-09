"""llms.txt, llms-full.txt, the collection-page Markdown and the static /api/v1/ files in a real site build."""
import csv
import hashlib
import html
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_site import build_site
from paper_library import library_pages, library_path, reviewed_papers
from search_pages import KINDS, SITE, eligible, resource_path
from site_data import utc
from static_api import API_VERSION, CHANGE_WINDOW_DAYS, ENDPOINTS, NOT_CURATED

API = ['resources', 'papers', 'categories', 'changes', 'candidates']


class AgentFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); cls.dest = build_site(cls.temp.name)
        cls.rows = [json.loads(line) for line in (ROOT / 'data/catalog.jsonl').read_text().splitlines() if line.strip()]
        cls.curated = [row for row in cls.rows if eligible(row)]
        cls.coverage = json.loads((ROOT / 'data/coverage.json').read_text())
        cls.manifest = json.loads((cls.dest / 'data/search-manifest.json').read_text())
        # generated_at is the newest recorded data time in the source snapshot, never the build clock.
        editorial = json.loads((ROOT / 'data/editorial.json').read_text())
        times = [cls.coverage['as_of_utc']] + [e['reviewed_at'] for e in editorial if e.get('editorial_reviewed') and e.get('reviewed_at')]
        times += [row['last_verified_at'] for row in cls.rows] + [e['retrieved_at'] for row in cls.rows for e in row['evidence']]
        times += [d['reviewed_at'] for d in json.loads((ROOT / 'data/exclusion-status.json').read_text())['decisions']]
        times += [json.loads(line)['finished_at'] for line in (ROOT / 'data/scan-history.jsonl').read_text().splitlines() if line.strip()]
        cls.snapshot = max(utc(value) for value in times if value)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def local(self, url):
        self.assertTrue(url.startswith(SITE + '/'), url)
        path = url[len(SITE):].split('#')[0]
        target = self.dest / path.lstrip('/')
        return target / 'index.html' if path.endswith('/') else target

    def test_llms_txt_follows_the_llmstxt_format_and_every_link_resolves(self):
        text = (self.dest / 'llms.txt').read_text()
        lines = text.splitlines()
        self.assertEqual(lines[0], '# AwesomeCUA')
        self.assertTrue(lines[2].startswith('> '))
        headings = [line for line in lines if line.startswith('#')]
        self.assertEqual([h for h in headings if h.startswith('# ')], ['# AwesomeCUA'])
        self.assertEqual(headings[-1], '## Optional')
        self.assertLessEqual(len(text.encode()), 50_000)
        links = re.findall(r'\]\((https://awesomecua\.com/[^)]*)\)', text)
        self.assertGreater(len(links), 80)
        for url in links:
            self.assertTrue(self.local(url).is_file(), url)
        curated = len(self.curated)
        self.assertIn(f'{curated:,} curated resources', lines[2])
        for kind in KINDS:
            if kind != 'paper':
                self.assertIn(f'{SITE}/categories/{kind}/index.md', text)
        for number in range(1, library_pages(self.rows) + 1):
            self.assertIn(SITE + library_path(number) + 'index.md', text)
        for topic in json.loads((self.dest / 'downloads/topics.json').read_text())['topics']:
            self.assertIn(f'{SITE}/topics/{topic["id"]}/index.md', text)
        for name in API:
            self.assertIn(f'{SITE}/api/v1/{name}.json', text)

    def test_llms_full_lists_every_curated_record_once_and_nothing_unreviewed(self):
        text = (self.dest / 'llms-full.txt').read_text()
        self.assertLess(len(text.encode()), 1_600_000)
        listed = re.findall(r'^- (https://awesomecua\.com/resources/[^ ]+/) · source:', text, re.M)
        self.assertEqual(len(listed), len(set(listed)))
        self.assertEqual(set(listed), {SITE + resource_path(row) for row in self.curated})
        self.assertNotIn('Recorded arXiv snapshot', text)  # full annotations live in the per-kind files

    def test_kind_and_library_markdown_carry_every_full_annotation_exactly_where_the_html_lists_it(self):
        def headings(path):
            return re.findall(r'^## (.+)$', path.read_text(), re.M)
        for kind in KINDS:
            target = self.dest / f'categories/{kind}/index.md'
            self.assertTrue(target.is_file(), kind)
            if kind == 'paper':
                continue
            expected = [SITE + resource_path(row) for row in self.curated if row['kind'] == kind]
            listed = re.findall(r'^- Catalog URL: (\S+)$', target.read_text(), re.M)
            self.assertCountEqual(listed, expected, kind)
            # The twin follows the category pages in order; a Featured group above the list repeats records.
            rows, number = [], 1
            while (page := self.dest / (f'categories/{kind}/' if number == 1 else f'categories/{kind}/page/{number}/') / 'index.html').is_file():
                section = page.read_text().split('data-list-rows>', 1)[1].split('</ul>', 1)[0]
                rows += re.findall(r'<h3 class="row-name"><a href="([^"]+)"', section)
                number += 1
            self.assertEqual(listed, [SITE + href for href in rows], kind)
        papers = reviewed_papers(self.rows)
        seen = []
        for number in range(1, library_pages(self.rows) + 1):
            path = library_path(number)
            markup = (self.dest / path.lstrip('/') / 'index.html').read_text()
            on_page = [html.unescape(value) for value in re.findall(r'data-resource-id="([^"]+)"', markup)]
            text = (self.dest / path.lstrip('/') / 'index.md').read_text()
            listed = re.findall(r'^- ID: (\S+)$', text, re.M)
            self.assertEqual(listed, on_page, path)
            seen += listed
        self.assertEqual(seen, [row['id'] for row in papers])
        with_snapshot = sum(bool(row['details'].get('arxiv_snapshot')) for row in papers)
        library_snapshots = sum((self.dest / library_path(n).lstrip('/') / 'index.md').read_text().count('### Recorded arXiv snapshot') for n in range(1, library_pages(self.rows) + 1))
        self.assertEqual(library_snapshots, with_snapshot)
        for path in ('index.md', 'catalog/index.md', 'categories/paper/index.md', 'api/index.md'):
            text = (self.dest / path).read_text()
            for url in re.findall(r'\]\((https://awesomecua\.com/[^)]*)\)', text):
                self.assertTrue(self.local(url).is_file(), (path, url))

    def test_api_files_validate_against_the_published_schema(self):
        schema = json.loads((self.dest / 'api/v1/schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        self.assertEqual(schema['version'], API_VERSION)
        for name in API + ['index']:
            document = json.loads((self.dest / f'api/v1/{name}.json').read_text())
            self.assertEqual(document['version'], API_VERSION, name)
            self.assertEqual(document['generated_at'], self.snapshot, name)
            validator = Draft202012Validator({'$schema': schema['$schema'], '$defs': schema['$defs'], '$ref': f'#/$defs/{name}'})
            errors = [f'{list(e.absolute_path)}: {e.message}' for e in validator.iter_errors(document)][:5]
            self.assertEqual(errors, [], name)

    def test_api_populations_are_exact_and_unreviewed_rows_are_flagged(self):
        load = lambda name: json.loads((self.dest / f'api/v1/{name}.json').read_text())
        resources, papers, candidates = load('resources'), load('papers'), load('candidates')
        self.assertEqual({item['id'] for item in resources['items']}, {row['id'] for row in self.curated if row['kind'] not in {'paper', 'survey'}})
        self.assertEqual({item['id'] for item in papers['items']}, {row['id'] for row in self.curated if row['kind'] in {'paper', 'survey'}})
        curated_ids = {row['id'] for row in self.curated}
        self.assertEqual(candidates['notice'], NOT_CURATED)
        self.assertEqual(candidates['review_status'], 'unreviewed')
        self.assertFalse(curated_ids & {item['id'] for item in candidates['items']})
        ids = [item['id'] for item in candidates['items']]
        self.assertEqual(len(ids), len(set(ids)))  # IDs are stable upsert keys, so each appears once
        self.assertTrue(all(item['curated'] is False for item in candidates['items']))
        pending = {row['id'] for row in self.rows if row['review_status'] == 'metadata_verified'}
        self.assertEqual({item['id'] for item in candidates['items'] if item['population'] == 'relevance_pending_record'}, pending)
        for paper in papers['items']:
            if paper['authors_omitted']:
                self.assertEqual(paper['authors'], [])
        categories = load('categories')
        kinds = {item['id']: item for item in categories['items'] if item['type'] == 'kind'}
        self.assertEqual(sum(item['curated_count'] for item in kinds.values()), len(self.curated))
        self.assertEqual(categories['counts']['curated']['total'], len(self.curated))

    def test_changes_cover_the_thirty_days_before_the_snapshot(self):
        changes = json.loads((self.dest / 'api/v1/changes.json').read_text())
        self.assertEqual(changes['window']['days'], CHANGE_WINDOW_DAYS)
        self.assertEqual(changes['window']['end'], self.snapshot)
        dates = [item['date'] for item in changes['items']]
        self.assertEqual(dates, sorted(dates, reverse=True))
        self.assertTrue(all(changes['window']['start'] <= date <= changes['window']['end'] for date in dates))
        self.assertIn('reviewed', {item['event'] for item in changes['items']})

    def test_csv_files_mirror_the_json_items_and_carry_version_and_snapshot(self):
        index = json.loads((self.dest / 'api/v1/index.json').read_text())
        self.assertEqual([item['name'] for item in index['endpoints']], [name for name, _ in ENDPOINTS])
        for item in index['endpoints']:
            body = (self.dest / f'api/v1/{item["name"]}.json').read_bytes()
            table = (self.dest / f'api/v1/{item["name"]}.csv').read_bytes()
            self.assertEqual((item['json_bytes'], item['json_sha256']), (len(body), hashlib.sha256(body).hexdigest()))
            self.assertEqual((item['csv_bytes'], item['csv_sha256']), (len(table), hashlib.sha256(table).hexdigest()))
            rows = list(csv.DictReader(io.StringIO(table.decode())))
            document = json.loads(body)
            self.assertEqual(len(rows), document['count'], item['name'])
            self.assertEqual([row['id'] for row in rows], [entry['id'] for entry in document['items']], item['name'])
            self.assertTrue(all(row['version'] == API_VERSION and row['generated_at'] == self.snapshot for row in rows))
            self.assertNotRegex(table.decode(), r'[ \t]\r?\n')

    def test_api_documentation_page_lists_every_endpoint(self):
        markup = (self.dest / 'api/index.html').read_text()
        pages = {item['path']: item for item in self.manifest['pages']}
        self.assertTrue(pages['/api/']['indexable'])
        for name in API:
            self.assertIn(f'{SITE}/api/v1/{name}.json', markup)
            self.assertIn(f'{SITE}/api/v1/{name}.csv', markup)
        self.assertIn('Access-Control-Allow-Origin', markup)


if __name__ == '__main__':
    unittest.main()
