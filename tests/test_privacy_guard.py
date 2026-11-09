"""Protected personal names never appear in tracked files or a built website.

Only fictional names appear in this file. The guard's real digests come from
names that are never written in the repository.
"""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import catalog  # noqa: E402
import privacy_guard as guard  # noqa: E402
from publication_metadata import authors_omitted  # noqa: E402

SALT = b'test-only salt'
GRAMS = ('ada lovelace', 'lovelace ada', 'adalovelace', 'lovelaceada', 'adalace7', 'ada world', 'qx 7zz')
FICTIONAL = frozenset(hashlib.sha256(SALT + gram.encode()).digest() for gram in GRAMS)
FAMILY = frozenset({hashlib.sha256(SALT + guard.SURNAME_DOMAIN + b'lovelace').digest()})


def found(text):
    return guard.contains_protected(text, FICTIONAL, SALT, FAMILY)


class RepositoryTests(unittest.TestCase):
    def test_tracked_files_and_built_site_name_no_protected_person(self):
        files = guard.default_files()
        self.assertGreater(len(files), 100)
        hits = guard.scan_files(files)
        self.assertEqual(hits, [], 'Protected personal names found (paths and line numbers only); see docs/maintenance.md#protected-names: '
                         + '; '.join(f'{path}: {lines[:10]}' for path, lines in hits))

    def test_only_a_salt_and_digests_are_stored(self):
        self.assertGreaterEqual(len(guard.SALT), 16)
        self.assertGreaterEqual(len(guard.PROTECTED), 8)
        self.assertTrue(guard.SURNAMES)
        self.assertTrue(all(isinstance(digest, bytes) and len(digest) == 32 for digest in guard.PROTECTED | guard.SURNAMES))


class MatchingTests(unittest.TestCase):
    def test_finds_orders_joins_encodings_and_structured_fields(self):
        cases = [
            'Ada Lovelace', 'ADA LOVELACE', 'Lovelace Ada', 'Lovelace, Ada', 'AdaLovelace', 'lovelaceada',
            'A-da Lovelace', 'Lovelace, A da', 'Ádá Lövelace', 'Ada&nbsp;Lovelace', 'Ada&#160;Lovelace',
            'Ada%20Lovelace', 'Ada+Lovelace', 'ada_lovelace@example.org', 'ada.lovelace', '"Ada\\u0020Lovelace"',
            'Ada Lovelace', 'Ada​Lovelace', 'Ａｄａ　Ｌｏｖｅｌａｃｅ', '~Ada_Lovelace2', 'adalovelace2026',
            'by Ada\nLovelace and others', '<span>Ada Lovelace</span>', '(Lovelace, Ada, 1843)',
            'author = {Smith, Kim and Lovelace, Ada}', '[{"family": "Lovelace", "given": "Ada"}]',
            'authors:\n  - given-names: Ada\n    family-names: Lovelace\n', '{"givenName":"Ada","familyName":"Lovelace"}',
            'https://github.com/AdaLace7/tool', 'https://ada.world/papers/', 'https://example.org/citations?user=QX_7zz&hl=en',
            'Ada\u2013Lovelace', 'Ada\u2014Lovelace', 'Ada\u2019Lovelace', 'Lovelace\u2013Ada', 'Lovelace\u00b7Ada',
            'Ada\u3001Lovelace', 'Ada\u2026Lovelace', '<b>Ada</b>\u2009<b>Lovelace</b>'.replace('</b>\u2009<b>', '\u2009'),
            '<span>Ada</span><span>Lovelace</span>', '<td>Lovelace</td>\n<td>Ada</td>', '<p>Ada <em class="x">Lovelace</em></p>',
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertTrue(found(text))

    def test_neighbouring_list_entries_match_as_a_plain_text_search_would(self):
        cases = [
            '["Kim Ada", "Lovelace Smith"]', '["Kim Lovelace", "Ada Smith"]', 'Kim Lovelace, Ada Smith', 'Kim Lovelace; Ada Smith',
            '- Kim Lovelace\n- Ada Smith', 'Kim Lovelace\n\nAda Smith', 'Kim Lovelace · Ada Smith', 'Kim Lovelace – Ada Smith',
            'Kim Lovelace | Ada Smith', 'Lovelace, Ada Smith', '<li>Kim Lovelace</li>\n<li>Ada Smith</li>', '{"authors": ["Kim Lovelace"]}\n{"authors": ["Ada Smith"]}'.replace('"]}\n{"authors": ["', '", "'),
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertTrue(found(text))

    def test_neighbouring_names_initials_and_other_people_do_not_match(self):
        cases = [
            'Kim Lovelace and Ada Smith', '1. Kim Lovelace\n2. Ada Smith',
            '[{"family": "Lovelace", "given": "Kim"}, {"family": "Smith", "given": "Ada"}]', 'Lovelace, Kim and Smith, Ada',
            'A. Lovelace', 'A. B. Lovelace', 'Ada Smith', 'Adalovelacey', 'Ada Lovelaces', 'Kim Lovelace 李 Ada Smith',
            'Kim Lovelace et al. Ada Smith', 'Lovelacexada',
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertFalse(found(text))

    def test_reports_paths_and_lines_only_with_or_without_workers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'site' / 'deep').mkdir(parents=True)
            (root / 'clean.md').write_text('Kim Lovelace and Ada Smith\n')
            (root / 'listed.json').write_text('{\n  "authors": [\n    "Ada Lovelace"\n  ]\n}\n')
            (root / 'site' / 'deep' / 'copy.json').write_bytes((root / 'listed.json').read_bytes())
            (root / 'CITATION.cff').write_text('authors:\n  - given-names: Ada\n    family-names: Lovelace\n')
            (root / 'binary.sqlite').write_bytes(b'SQLite format 3\x00' + b'\x00\x01' * 50 + b'{"authors":["Ada Lovelace"]}')
            files = [root / 'clean.md', root / 'listed.json', root / 'CITATION.cff', root / 'binary.sqlite', *guard.tree_files(root / 'site')]
            expected = [(root / 'listed.json', [3]), (root / 'CITATION.cff', [0]), (root / 'binary.sqlite', [1]),
                        (root / 'site' / 'deep' / 'copy.json', [3])]
            self.assertEqual(guard.scan_files(files, FICTIONAL, SALT, workers=1, surnames=FAMILY), expected)
            self.assertEqual(guard.scan_files(files, FICTIONAL, SALT, workers=3, surnames=FAMILY), expected)
            with mock.patch.object(guard, 'PROTECTED', FICTIONAL), mock.patch.object(guard, 'SALT', SALT), \
                    mock.patch.object(guard, 'SURNAMES', FAMILY):
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    self.assertEqual(guard.main([str(root)]), 1)
                self.assertIn('listed.json: protected personal name on line 3', stderr.getvalue())
                self.assertNotIn('Lovelace', stderr.getvalue())
                with self.assertRaises(SystemExit) as raised:
                    guard.require_clean(files, 'test')
                self.assertNotIn('Lovelace', str(raised.exception))
                (root / 'listed.json').write_text('{"authors": [], "authors_omitted": true}\n')
                self.assertEqual(guard.require_clean([root / 'listed.json', root / 'clean.md'], 'test'), 2)


class BuildBoundaryTests(unittest.TestCase):
    def test_a_rejected_site_build_keeps_the_previous_build(self):
        import build_site

        def write(text):
            def writer(staging):
                (staging / 'data').mkdir()
                (staging / 'data/search-manifest.json').write_text('{}')
                (staging / 'index.html').write_text(text)
                return [], 0
            return writer

        def check(staging):
            guard.require_clean(guard.tree_files(staging), 'website')
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(guard, 'PROTECTED', FICTIONAL), \
                mock.patch.object(guard, 'SALT', SALT), mock.patch.object(guard, 'SURNAMES', FAMILY), redirect_stderr(io.StringIO()):
            output = Path(folder) / 'site'
            with mock.patch.object(build_site, 'write_site', write('<p>Kim Smith</p>')), redirect_stdout(io.StringIO()):
                build_site.build_site(output, check=check)
            with mock.patch.object(build_site, 'write_site', write('<p>Ada Lovelace</p>')), self.assertRaises(SystemExit):
                build_site.build_site(output, check=check)
            self.assertEqual((output / 'index.html').read_text(), '<p>Kim Smith</p>')
            self.assertEqual([path.name for path in Path(folder).iterdir()], ['site'])


class AuthorOmissionTests(unittest.TestCase):
    def setUp(self):
        patches = [mock.patch.object(guard, 'PROTECTED', FICTIONAL), mock.patch.object(guard, 'SALT', SALT),
                   mock.patch.object(guard, 'SURNAMES', FAMILY)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_omits_whole_author_lists_only_when_one_names_a_protected_person(self):
        listed = {'id': 'arxiv:2401.00001', 'authors': ['Ada Smith', 'Kim Lovelace'], 'details': {}}
        self.assertIs(guard.omit_protected_authors(listed), listed)
        neighbours = {'id': 'arxiv:2401.00006', 'authors': ['Kim Lovelace', 'Ada Smith'], 'details': {}}
        self.assertTrue(authors_omitted(guard.omit_protected_authors(neighbours)))
        named = {'id': 'arxiv:2401.00002', 'authors': ['Kim Smith', 'Ada Lovelace'], 'details': {
            'publication': {'title': 'Edition', 'authors': ['Kim Smith']}}}
        omitted = guard.omit_protected_authors(named)
        self.assertEqual((omitted['authors'], omitted['details']['publication']['authors']), ([], []))
        self.assertTrue(authors_omitted(omitted))
        self.assertEqual(named['authors'], ['Kim Smith', 'Ada Lovelace'])
        edition_only = {'id': 'url:example', 'authors': ['Kim Smith'], 'details': {'publication': {'authors': ['Lovelace, Ada']}}}
        self.assertTrue(authors_omitted(guard.omit_protected_authors(edition_only)))
        # An omitted record stays omitted, even when an edition attached later lists other people.
        later = {**omitted, 'details': {'publication': {'title': 'Edition', 'authors': ['Kim Smith']}}}
        self.assertEqual(guard.omit_protected_authors(later)['details']['publication']['authors'], [])

    def test_arxiv_ingest_never_retains_a_protected_author_list(self):
        atom = 'http://www.w3.org/2005/Atom'
        entry = ET.fromstring(f'''<entry xmlns="{atom}"><id>http://arxiv.org/abs/2401.00003v1</id>
            <title>A fixture paper</title><published>2024-01-01T00:00:00Z</published><updated>2024-01-02T00:00:00Z</updated>
            <summary>Fixture.</summary><author><name>Kim Smith</name></author><author><name>Ada Lovelace</name></author></entry>''')
        row = catalog.arxiv_entry(entry, {'url': 'https://export.arxiv.org/api/query?id_list=2401.00003', 'retrieved_at': '2024-01-03T00:00:00Z', 'sha256': 'a' * 64})
        self.assertEqual((row['authors'], row['authors_omitted']), ([], True))
        self.assertNotIn('Lovelace', json.dumps(row))

    def test_archive_rewrite_changes_only_named_records(self):
        rows = [{'id': 'arxiv:2401.00004', 'authors': ['Ada Lovelace'], 'details': {}},
                {'id': 'arxiv:2401.00005', 'authors': ['Ada Smith', 'Kim Lovelace'], 'details': {}}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'papers.jsonl'
            catalog.write_jsonl(path, rows)
            self.assertEqual(guard.omit_archive_authors(path), ['arxiv:2401.00004'])
            self.assertEqual(guard.omit_archive_authors(path), [])
            stored = catalog.read_jsonl(path)
        self.assertEqual(stored[0], {'id': 'arxiv:2401.00004', 'authors': [], 'authors_omitted': True, 'details': {}})
        self.assertEqual(stored[1], rows[1])


if __name__ == '__main__':
    unittest.main()
