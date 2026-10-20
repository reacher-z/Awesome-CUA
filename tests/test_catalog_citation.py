import contextlib
import hashlib
import html
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
from catalog_citation import BIBTEX_PATH, catalog_bibtex, cite_section
from citation_file import read_citation_file


class CatalogBibtexTests(unittest.TestCase):
    def test_entry_is_built_from_citation_file_with_the_snapshot_year(self):
        cff = read_citation_file(ROOT / 'CITATION.cff')
        entry = catalog_bibtex('2031-02-03T04:05:06Z')
        fields = dict(re.findall(r'^  (\w+) += \{(.*)\},?$', entry, re.M))
        self.assertTrue(entry.startswith('@misc{awesomecua,\n'))
        self.assertTrue(entry.endswith('\n}\n'))
        self.assertEqual(list(fields), ['title', 'author', 'year', 'url', 'howpublished', 'note'])
        self.assertEqual(fields['title'], cff['title'])
        self.assertEqual(fields['author'], ' and '.join(f"{a['family-names']}, {a['given-names']}" for a in cff['authors']))
        self.assertEqual(fields['year'], '2031')
        self.assertEqual(fields['url'], cff['url'])
        self.assertEqual(fields['howpublished'], '\\url{' + cff['repository-code'] + '}')
        self.assertEqual(fields['note'], 'Versioned data releases: ' + cff['repository-code'] + '/releases')
        self.assertEqual(entry.count('{'), entry.count('}'))

    def test_matches_the_readme_entry_shape(self):
        # The README cite section shows the same entry, so the field order and alignment are fixed.
        self.assertEqual(catalog_bibtex('2026-10-18T08:01:28Z'), '''@misc{awesomecua,
  title        = {Awesome Computer-Use Agents: a source-backed catalog of computer-use, GUI, browser, and mobile agents},
  author       = {Zhang, Yuxuan},
  year         = {2026},
  url          = {https://awesomecua.github.io/},
  howpublished = {\\url{https://github.com/reacher-z/Awesome-CUA}},
  note         = {Versioned data releases: https://github.com/reacher-z/Awesome-CUA/releases}
}
''')

    def test_section_escapes_the_entry_and_localizes_the_prose(self):
        entry = '@misc{x,\n  title = {A <b> & C}\n}\n'
        english = cite_section(entry, 'https://github.com/o/r')
        chinese = cite_section(entry, 'https://github.com/o/r', 'zh')
        self.assertIn('<h2 id="cite-heading">Cite AwesomeCUA</h2>', english)
        self.assertIn('<h2 id="cite-heading">引用 AwesomeCUA</h2>', chinese)
        for section in (english, chinese):
            self.assertIn('{A &lt;b&gt; &amp; C}', section)
            self.assertNotIn('<b>', section)
            self.assertIn(f'href="{BIBTEX_PATH}" download', section)
            self.assertIn('href="https://github.com/o/r/releases"', section)
            self.assertIn('href="https://github.com/o/r/blob/main/CITATION.cff"', section)


class CatalogCitationPagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        with contextlib.redirect_stdout(io.StringIO()):
            cls.dest = build_site(cls.temp.name)
        cls.snapshot = json.loads((ROOT / 'data/coverage.json').read_text(encoding='utf-8'))['as_of_utc']

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_download_serves_the_entry_and_is_listed_in_the_manifest(self):
        body = (self.dest / BIBTEX_PATH.lstrip('/')).read_bytes()
        self.assertEqual(body.decode('utf-8'), catalog_bibtex(self.snapshot))
        manifest = json.loads((self.dest / 'downloads/manifest.json').read_text(encoding='utf-8'))
        item = next(item for item in manifest['artifacts'] if item['path'] == BIBTEX_PATH)
        self.assertEqual((item['id'], item['group'], item['format'], item['media_type']),
                         ('awesomecua-bib', 'citations', 'BibTeX', 'application/x-bibtex'))
        self.assertEqual(item['count'], {'value': 1, 'unit': 'citations'})
        self.assertEqual((item['bytes'], item['sha256']), (len(body), hashlib.sha256(body).hexdigest()))

    def test_data_and_about_pages_show_the_entry(self):
        entry = html.escape(catalog_bibtex(self.snapshot).rstrip())
        for path, heading in (('data', 'Cite AwesomeCUA'), ('zh/data', '引用 AwesomeCUA'), ('about', 'Cite AwesomeCUA')):
            markup = (self.dest / path / 'index.html').read_text(encoding='utf-8')
            self.assertEqual(markup.count('id="cite"'), 1, path)
            self.assertIn(f'<h2 id="cite-heading">{heading}</h2>', markup, path)
            self.assertIn(f'<pre class="command-block"><code>{entry}</code></pre>', markup, path)
            self.assertIn(f'href="{BIBTEX_PATH}" download', markup, path)
        for path in ('data', 'zh/data'):
            self.assertIn('data-artifact-id="awesomecua-bib"', (self.dest / path / 'index.html').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
