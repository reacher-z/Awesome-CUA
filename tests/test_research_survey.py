"""Offline survey assembly and pinned-bibliography integrity checks."""
from contextlib import redirect_stdout
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('awesomecua_survey_builder', ROOT / 'research/survey/scripts/build_article.py')
survey = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = survey
SPEC.loader.exec_module(survey)


class SurveyFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(survey.FROZEN_BIBLIOGRAPHY.read_text())

    def write_fixture(self, folder, value):
        path = Path(folder) / 'fixture.json'
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        return path

    def load_mutation(self, value):
        """Allow a test-only outer hash to reach an inner contract check."""
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_fixture(folder, value)
            with mock.patch.object(survey, 'FROZEN_BIBLIOGRAPHY_SHA', survey.digest(path.read_bytes())):
                return survey.load_frozen_bibliography(path, check_history=False)

    def test_real_fixture_preserves_seventy_original_bibliographies(self):
        rows, verification = survey.load_frozen_bibliography(check_history=False)
        self.assertEqual(len(rows), 70)
        self.assertEqual(verification['fixture_sha256'], survey.FROZEN_BIBLIOGRAPHY_SHA)
        self.assertEqual({r['kind'] for r in rows}, {'paper', 'survey'})
        self.assertEqual(len({r['id'] for r in rows}), 70)
        for entry, row in zip(self.fixture['records'], rows):
            self.assertEqual(entry['record'], row)
            self.assertEqual(entry['record_sha256'], survey.record_sha256(row))
            self.assertEqual(entry['citation_key'], survey.citation_key(row))

    def test_tampering_rejected_even_when_record_hash_is_recomputed(self):
        changed = copy.deepcopy(self.fixture)
        entry = changed['records'][0]
        entry['record']['name'] = 'An unreviewed replacement title'
        entry['record_sha256'] = survey.record_sha256(entry['record'])
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_fixture(folder, changed)
            with self.assertRaisesRegex(ValueError, 'fixture fingerprint'):
                survey.load_frozen_bibliography(path, check_history=False)

    def test_inner_record_hash_is_checked(self):
        changed = copy.deepcopy(self.fixture)
        changed['records'][0]['record']['authors'].reverse()
        with self.assertRaisesRegex(ValueError, 'record fingerprint'):
            self.load_mutation(changed)

    def test_duplicate_canonical_identity_is_rejected(self):
        changed = copy.deepcopy(self.fixture)
        changed['records'].append(copy.deepcopy(changed['records'][0]))
        changed['record_count'] += 1
        with self.assertRaisesRegex(ValueError, 'Duplicate or inconsistent'):
            self.load_mutation(changed)

    def test_boolean_schema_and_wrong_provenance_are_rejected(self):
        for field, replacement in [('schema_version', True), ('source_commit', '0' * 40), ('catalog_sha256', '0' * 64), ('record_count', True)]:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.fixture)
                changed[field] = replacement
                with self.assertRaises(ValueError):
                    self.load_mutation(changed)

    def test_snapshot_version_url_must_match(self):
        changed = copy.deepcopy(self.fixture)
        entry = next(x for x in changed['records'] if x['record']['id'].startswith('arxiv:'))
        entry['record']['details']['arxiv_snapshot']['version'] = 999
        entry['record_sha256'] = survey.record_sha256(entry['record'])
        with self.assertRaisesRegex(ValueError, 'version URL'):
            self.load_mutation(changed)

    def test_missing_git_or_pinned_object_uses_verified_fixture_without_fetch(self):
        unavailable = subprocess.CompletedProcess(['git'], 128, b'', b'object unavailable')
        for outcome in [unavailable, FileNotFoundError('git unavailable')]:
            with self.subTest(outcome=type(outcome).__name__):
                kwargs = {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome}
                with mock.patch.object(survey.subprocess, 'run', **kwargs) as run:
                    rows, verification = survey.load_frozen_bibliography()
                self.assertEqual(len(rows), 70)
                self.assertIn('not_available', verification['history_check'])
                self.assertEqual(run.call_args.args[0], ['git', 'show', survey.PIN + ':data/catalog.jsonl'])
                self.assertEqual(run.call_count, 1)

    def test_available_history_is_checked_instead_of_ignored(self):
        result = subprocess.CompletedProcess(['git'], 0, b'wrong historical object', b'')
        with mock.patch.object(survey.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'wrong catalog fingerprint'):
                survey.load_frozen_bibliography()


class SurveyAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledgers = {name: survey.load(name) for name in survey.EVIDENCE}

    def test_committed_site_bundle_exactly_matches_offline_rebuild(self):
        committed = ROOT / 'web/survey'
        with tempfile.TemporaryDirectory() as folder, redirect_stdout(io.StringIO()):
            destination = Path(folder)
            manifest = survey.build(destination, check_history=False)
            checked_in = json.loads((committed / 'build-manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest, checked_in)
            for item in manifest['files']:
                self.assertEqual((destination / item['path']).read_bytes(),
                                 (committed / item['path']).read_bytes(), item['path'])

    def test_title_author_and_edition_disagreement_rejects(self):
        records, _ = survey.load_frozen_bibliography(check_history=False)
        record = next(r for r in records if r['id'] == 'arxiv:2501.12326')
        item = survey.citation_csl(record)
        key = item['citation-key']
        for field, replacement in [('title', 'Another work'), ('author', [{'literal': 'Unrecorded Author'}])]:
            changed = dict(item, **{field: replacement})
            with self.subTest(field=field), self.assertRaises(ValueError):
                survey.verify_read_bibliography(key, changed, self.ledgers)
        changed = dict(item, version='999', URL='https://arxiv.org/abs/2501.12326v999')
        reading = survey.collect_readings(self.ledgers)[key]
        with self.assertRaisesRegex(ValueError, 'version conflict'):
            survey.verify_read_edition(key, changed, reading)

    def test_all_committed_evidence_is_public_and_sanitization_idempotent(self):
        forbidden = {'citation_abstract', 'abstract', 'full_abstract', 'fulltext', 'raw_body'}

        def inspect(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden & set(value))
                for child in value.values():
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)
            elif isinstance(value, str):
                self.assertFalse(value.startswith(('/Users/', '/home/', '.cache/')))

        for name, ledger in self.ledgers.items():
            with self.subTest(ledger=name):
                inspect(ledger)
                self.assertEqual(survey.public_evidence(ledger), ledger)
        self.assertEqual(self.ledgers['context']['writing_review']['skill'], 'paper-writing-review')

    def test_complete_offline_build_is_deterministic_and_does_not_update_sources(self):
        source_paths = [survey.SURVEY / name for name in ['index.html', 'references.bib', 'references.json', 'evidence/reading-index.json']]
        before = {p: p.read_bytes() if p.exists() else None for p in source_paths}
        unavailable = subprocess.CompletedProcess(['git'], 128, b'', b'object not in shallow checkout')
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'artifact'
            with mock.patch.object(survey.subprocess, 'run', return_value=unavailable), mock.patch('socket.create_connection', side_effect=AssertionError('No network is permitted')), redirect_stdout(io.StringIO()):
                manifest = survey.build(destination)
                first = {f['path']: (destination / f['path']).read_bytes() for f in manifest['files']}
                survey.build(destination)
                second = {p: (destination / p).read_bytes() for p in first}
            self.assertEqual(first, second)
            self.assertEqual(manifest['counts']['unique_cited_works'], 89)
            self.assertEqual(manifest['counts']['fulltext_section_read_works'], 87)
            refs = json.loads((destination / 'references.json').read_text())
            readings = json.loads((destination / 'evidence/reading-index.json').read_text())['records']
            self.assertEqual({r['citation-key'] for r in refs}, {r['citation_key'] for r in readings})
            for citation in refs:
                reading = next(r for r in readings if r['citation_key'] == citation['citation-key'])
                self.assertEqual(citation['title'], reading['title'])
                self.assertEqual([a['literal'] for a in citation.get('author', [])], reading['ordered_authors'])
                self.assertEqual(citation['URL'], reading['citation_url'])
            for artifact in manifest['files']:
                data = (destination / artifact['path']).read_bytes()
                self.assertEqual(len(data), artifact['bytes'])
                self.assertEqual(survey.digest(data), artifact['sha256'])
            html_text = (destination / 'index.html').read_text()
            self.assertIn('<details class="contents" id="article-contents">', html_text)
            self.assertNotIn('data-keys=', html_text)
            self.assertTrue(manifest['checks']['all_internal_anchors_resolve'])
            self.assertTrue(manifest['checks']['all_relative_downloads_exist'])
        self.assertEqual(before, {p: p.read_bytes() if p.exists() else None for p in source_paths})


if __name__ == '__main__':
    unittest.main()
