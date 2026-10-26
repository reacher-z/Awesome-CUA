import contextlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_site import build_site
from citation_file import read_citation_file
from search_pages import SITE


def graph(markup):
    return [node for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', markup, re.S)
            for node in json.loads(block).get('@graph', [])]


class CatalogDatasetTests(unittest.TestCase):
    # Google Dataset Search reads the data hub's Dataset node; both translations must describe one dataset.
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        with contextlib.redirect_stdout(io.StringIO()):
            cls.dest = build_site(cls.temp.name)
        cls.rows = [json.loads(line) for line in (ROOT / 'data/catalog.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        cls.coverage = json.loads((ROOT / 'data/coverage.json').read_text(encoding='utf-8'))
        cls.manifest = json.loads((cls.dest / 'downloads/manifest.json').read_text(encoding='utf-8'))
        cls.pages = {path: graph((cls.dest / path / 'index.html').read_text(encoding='utf-8')) for path in ('data', 'zh/data')}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def dataset(self, path='data'):
        found = [node for node in self.pages[path] if node.get('@type') == 'Dataset']
        self.assertEqual(len(found), 1, path)
        return found[0]

    def test_both_languages_share_one_dataset_identity(self):
        english, chinese = self.dataset('data'), self.dataset('zh/data')
        self.assertEqual(english, chinese)
        self.assertEqual((english['@id'], english['url']), (SITE + '/data/#dataset', SITE + '/data/'))
        for path in self.pages:
            page = next(node for node in self.pages[path] if node.get('@type') == 'WebPage')
            self.assertEqual(page['mainEntity'], {'@id': SITE + '/data/#dataset'}, path)

    def test_creator_license_and_source_follow_citation_file(self):
        cff = read_citation_file(ROOT / 'CITATION.cff')
        dataset = self.dataset()
        self.assertEqual([person['name'] for person in dataset['creator']],
                         [a['given-names'] + ' ' + a['family-names'] for a in cff['authors']])
        for person in dataset['creator']:
            self.assertEqual(person['@type'], 'Person')
            self.assertTrue(person['url'].startswith('https://github.com/'))
            self.assertTrue(cff['repository-code'].lower().startswith(person['url'].lower() + '/'))
        self.assertEqual(dataset['license'], 'https://spdx.org/licenses/MIT.html')
        self.assertEqual(cff['license'], 'MIT')
        self.assertEqual(dataset['sameAs'], [cff['repository-code']])
        self.assertEqual(dataset['publisher']['name'], 'AwesomeCUA')
        self.assertEqual(dataset['publisher']['url'], SITE + '/')
        self.assertIn('Awesome Computer-Use Agents', dataset['alternateName'])
        self.assertIs(dataset['isAccessibleForFree'], True)

    def test_description_version_and_coverage_come_from_the_snapshot(self):
        dataset = self.dataset()
        self.assertGreaterEqual(len(dataset['description']), 50)
        self.assertLessEqual(len(dataset['description']), 5000)
        self.assertEqual(dataset['dateModified'], self.coverage['as_of_utc'])
        self.assertEqual(dataset['version'], self.coverage['as_of_utc'][:10])
        dates = sorted(r['published_at'] for r in self.rows
                       if r['kind'] in {'paper', 'survey'} and r['review_status'] == 'curated' and r['published_at'])
        self.assertEqual(dataset['temporalCoverage'], f'{dates[0]}/{dates[-1]}')
        self.assertRegex(dataset['temporalCoverage'], r'^\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}$')

    def test_every_distribution_is_a_listed_download_with_its_exact_size(self):
        listed = {SITE + item['path']: item for item in self.manifest['artifacts']}
        distribution = self.dataset()['distribution']
        urls = [item['contentUrl'] for item in distribution]
        self.assertEqual(len(urls), len(set(urls)))
        for expected in ('/downloads/catalog.jsonl', '/data/records.json', '/downloads/catalog.sqlite',
                         '/downloads/rag-documents.jsonl', '/downloads/citations.bib'):
            self.assertIn(SITE + expected, urls)
        for item in distribution:
            self.assertEqual(item['@type'], 'DataDownload')
            artifact = listed[item['contentUrl']]
            target = self.dest / item['contentUrl'][len(SITE) + 1:]
            self.assertTrue(target.is_file(), item['contentUrl'])
            self.assertEqual(item['contentSize'], f'{target.stat().st_size} bytes')
            self.assertEqual(target.stat().st_size, artifact['bytes'])
            self.assertEqual(item['encodingFormat'], artifact['media_type'])
            self.assertIn(artifact['format'], item['name'])
            self.assertNotIn('manifest', item['contentUrl'])


class CitationFileReaderTests(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'CITATION.cff'
            path.write_text(text, encoding='utf-8')
            return read_citation_file(path)

    def test_reads_top_level_scalars_and_every_author(self):
        facts = self.read('cff-version: 1.2.0\ntitle: "A: catalog"\nauthors:\n  - given-names: Ada\n    family-names: Lovelace\n'
                          '  - given-names: Alan\n    family-names: Turing\n    alias: aturing\nlicense: MIT\n'
                          'repository-code: "https://github.com/aturing/x"\nurl: "https://example.org/"\nkeywords:\n  - agents\n')
        self.assertEqual(facts['title'], 'A: catalog')
        self.assertEqual(facts['repository-code'], 'https://github.com/aturing/x')
        self.assertEqual(facts['authors'], [{'given-names': 'Ada', 'family-names': 'Lovelace'},
                                            {'given-names': 'Alan', 'family-names': 'Turing', 'alias': 'aturing'}])
        self.assertNotIn('keywords', facts)

    def test_rejects_missing_authors_or_required_fields(self):
        with self.assertRaisesRegex(ValueError, 'authors'):
            self.read('title: x\nlicense: MIT\nrepository-code: r\nurl: u\n')
        with self.assertRaisesRegex(ValueError, 'license'):
            self.read('title: x\nauthors:\n  - given-names: A\n    family-names: B\nrepository-code: r\nurl: u\n')


if __name__ == '__main__':
    unittest.main()
