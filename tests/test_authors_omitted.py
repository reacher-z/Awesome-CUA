"""Records whose author list the catalog does not show: validation, pages, exports and the survey."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import catalog  # noqa: E402
from arxiv_metadata import consider_paper  # noqa: E402
import build  # noqa: E402
from build import title_author_collisions, validate_records  # noqa: E402
from export_citations import citation_bibtex, citation_csl  # noqa: E402
from export_rag import documents  # noqa: E402
from paper_library import paper_library  # noqa: E402
from publication_metadata import AUTHORS_OMITTED, authors_omitted, omit_authors  # noqa: E402
from search_pages import resource_body, resource_markdown, resource_path  # noqa: E402
from topic_pages import topic_body  # noqa: E402
from test_resource_payloads import paper  # noqa: E402

NAMES = ('Withheld Fixture Person', 'Another Listed Person')


def omitted_paper(aid='2401.00009'):
    record = paper(aid)
    record.update(authors=list(NAMES), topics=['grounding'], environments=['web'])
    return omit_authors(record)


def schema_errors(row):
    import jsonschema
    contract = catalog.read_json(ROOT / 'schemas/resource.schema.json')
    return [error.message for error in jsonschema.Draft202012Validator(contract, format_checker=jsonschema.FormatChecker()).iter_errors(row)]


class OmittedAuthorValidationTests(unittest.TestCase):
    def test_omission_keeps_every_other_fact_and_empties_both_author_lists(self):
        record = paper('2401.00009')
        record['details']['publication'] = {'type': 'other', 'title': 'Edition', 'authors': list(NAMES),
                                            'date_parts': [2024], 'url': 'https://example.org/edition', 'evidence_urls': ['https://example.org/edition']}
        omitted = omit_authors(record)
        self.assertEqual((omitted['authors'], omitted['authors_omitted'], omitted['details']['publication']['authors']), ([], True, []))
        self.assertEqual(record['authors'], ['王小明', 'A Researcher'])
        self.assertEqual({k: v for k, v in omitted.items() if k not in {'authors', 'authors_omitted', 'details'}},
                         {k: v for k, v in record.items() if k not in {'authors', 'details'}})
        self.assertTrue(authors_omitted(omitted))
        self.assertFalse(authors_omitted(record))

    def test_schema_and_validator_accept_only_true_with_empty_author_lists(self):
        valid = omitted_paper()
        self.assertEqual(schema_errors(valid), [])
        self.assertEqual(validate_records([valid]), [])
        for change in ({'authors': ['Listed Anyway']}, {'authors_omitted': False}, {'authors_omitted': 'yes'}):
            with self.subTest(change=change):
                row = dict(valid, **change)
                self.assertTrue(schema_errors(row))
                self.assertTrue(validate_records([row]))
        edition = copy.deepcopy(valid)
        edition['details']['publication'] = {'type': 'other', 'title': 'Edition', 'authors': ['Listed Anyway'],
                                             'date_parts': [2024], 'url': 'https://example.org/edition', 'evidence_urls': ['https://example.org/edition']}
        self.assertTrue(schema_errors(edition))
        self.assertIn('authors_omitted must be true, with empty record and publication author lists', ' '.join(validate_records([edition])))

    def test_omitted_lists_never_collide_with_unknown_author_lists(self):
        first, second = omitted_paper('2401.00009'), omitted_paper('2401.00010')
        second['name'] = first['name']
        unknown = dict(paper('2401.00011'), name=first['name'], authors=[])
        self.assertEqual([[r['id'] for r in group] for group in title_author_collisions([first, unknown])], [])
        self.assertEqual([sorted(r['id'] for r in group) for group in title_author_collisions([first, second])],
                         [[first['id'], second['id']]])


class OmittedAuthorPipelineTests(unittest.TestCase):
    def test_refreshing_an_omitted_record_proposes_no_author_change(self):
        stored = omitted_paper()
        observed = dict(copy.deepcopy(stored), authors=list(NAMES))
        observed.pop('authors_omitted')
        records, proposals = {stored['id']: stored}, {}
        self.assertFalse(consider_paper(observed, records, proposals, '2026-10-17T00:00:00Z'))
        self.assertEqual(proposals, {})
        renamed = dict(observed, name='A renamed title')
        consider_paper(renamed, records, proposals, '2026-10-17T00:00:00Z')
        self.assertEqual(set(proposals[stored['id']]['changes']), {'name'})
        self.assertNotIn(NAMES[0], json.dumps(proposals))

    def test_build_empties_an_attached_edition_of_an_omitted_record(self):
        archived = omitted_paper()
        observation = {'id': archived['id'], 'last_verified_at': '2026-10-16T01:00:00Z',
                       'evidence': [{'role': 'primary', 'method': 'publisher_metadata', 'supports': ['details.publication'],
                                     'url': 'https://example.org/edition', 'sha256': 'd' * 64, 'retrieved_at': '2026-10-16T01:00:00Z'}],
                       'publication': {'type': 'other', 'title': 'Edition', 'authors': list(NAMES), 'date_parts': [2024],
                                       'url': 'https://example.org/edition', 'evidence_urls': ['https://example.org/edition']}}
        reads = {'papers.jsonl': [archived], 'publications.jsonl': [observation], 'primary-evidence.jsonl': [], 'enrichment.jsonl': [], 'metadata-updates.jsonl': []}
        with mock.patch.object(build, 'read_jsonl', side_effect=lambda path: copy.deepcopy(reads.get(path.name, []))), \
                mock.patch.object(build, 'read_json', side_effect=lambda path, default=None: [] if default is None else default):
            rows, _ = build.source_records()
        row = next(r for r in rows if r['id'] == archived['id'])
        self.assertEqual((row['authors'], row['authors_omitted'], row['details']['publication']['authors']), ([], True, []))
        self.assertEqual(observation['publication']['authors'], list(NAMES))


class OmittedAuthorRenderingTests(unittest.TestCase):
    def setUp(self):
        self.record = omitted_paper()

    def assertNoNames(self, text):
        for name in NAMES:
            self.assertNotIn(name, text)

    def test_resource_page_and_markdown_link_to_the_paper(self):
        body = resource_body(self.record, {self.record['id']: self.record})
        self.assertIn('<h2>Authors</h2><p class="authors-omitted"><a href="https://arxiv.org/abs/2401.00009v2">Authors: see the paper</a></p>', body)
        self.assertIn('citation files omit them', body)
        markdown = resource_markdown(self.record)
        self.assertIn('## Authors\n\n[Authors: see the paper](https://arxiv.org/abs/2401.00009v2)', markdown)
        self.assertNoNames(body + markdown)

    def test_library_and_topic_lists_show_both_languages(self):
        for language, text in (('en', AUTHORS_OMITTED[0]), ('zh', AUTHORS_OMITTED[1])):
            with self.subTest(language=language):
                library, _ = paper_library([self.record], resource_path, language=language)
                topic, _ = topic_body('grounding', [self.record], resource_path, language=language)
                for markup in (library, topic):
                    self.assertIn('<a href="https://arxiv.org/abs/2401.00009v2">' + text + '</a>', markup)
                    self.assertNoNames(markup)

    def test_citations_omit_the_author_field_and_say_where_to_find_it(self):
        item = citation_csl(self.record)
        self.assertNotIn('author', item)
        self.assertTrue(item['custom']['authors_omitted'])
        self.assertIn('Authors: see the paper (https://arxiv.org/abs/2401.00009v2)', item['note'])
        bibtex = citation_bibtex(self.record)
        self.assertNotIn('author =', bibtex)
        self.assertIn('"authors_omitted": true', bibtex)
        self.assertIn('note = {', bibtex)
        self.assertNoNames(json.dumps(item, ensure_ascii=False) + bibtex)

    def test_citations_never_export_names_even_if_an_omitted_record_still_lists_them(self):
        leaky = dict(self.record, authors=list(NAMES))
        leaky['details'] = dict(leaky['details'], publication={'type': 'other', 'title': 'Edition', 'authors': list(NAMES), 'date_parts': [2024],
                                                              'url': 'https://example.org/edition', 'evidence_urls': ['https://example.org/edition']})
        for edition in ('record', 'publication'):
            with self.subTest(edition=edition):
                item, bibtex = citation_csl(leaky, edition), citation_bibtex(leaky, edition)
                self.assertNotIn('author', item)
                self.assertNoNames(json.dumps(item, ensure_ascii=False) + bibtex)

    def test_retrieval_documents_keep_the_flag_and_point_to_the_paper(self):
        document = next(documents([self.record]))
        self.assertIn('Authors: see the paper (https://arxiv.org/abs/2401.00009v2)', document['text'])
        self.assertEqual((document['metadata']['authors'], document['metadata']['authors_omitted']), ([], True))
        self.assertNoNames(json.dumps(document, ensure_ascii=False))
        listed = next(documents([paper('2401.00012')]))
        self.assertNotIn('authors_omitted', listed['metadata'])


SPEC = importlib.util.spec_from_file_location('awesomecua_survey_omission', ROOT / 'research/survey/scripts/build_article.py')
survey = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = survey
SPEC.loader.exec_module(survey)


class SurveyOmittedAuthorTests(unittest.TestCase):
    def test_reference_list_links_to_the_paper_instead_of_names(self):
        item = citation_csl(omitted_paper())
        item['citation-key'] = 'fixture'
        markup = survey.reference_html([item])
        self.assertIn('<p><a href="https://arxiv.org/abs/2401.00009v2">Authors: see the paper</a></p>', markup)
        self.assertNotIn('Complete author list', markup)

    def test_fresh_search_rows_marked_omitted_never_keep_names(self):
        row = {'id': 'arxiv:2401.00009', 'title': 'Fresh row', 'authors': list(NAMES), 'authors_omitted': True,
               'versioned_url': 'https://arxiv.org/abs/2401.00009v1', 'published': '2024-01-01T00:00:00Z',
               'updated': '2024-01-02T00:00:00Z', 'abstract_sha256': 'c' * 64}
        record = survey.arxiv_record(row)
        self.assertEqual((record['authors'], record['authors_omitted']), ([], True))
        self.assertNotIn('author', citation_csl(record))

    def test_reading_ledgers_and_citations_must_agree_on_omission(self):
        item = citation_csl(omitted_paper())
        ledger = {'citation_key': 'fixture', 'title': item['title'], 'authors': [], 'authors_omitted': True}
        ledgers = {'context': {'records': []}, 'methods': {'sources': [ledger]}, 'evaluation': {'records': []}}
        survey.verify_read_bibliography('fixture', item, ledgers)
        listed = dict(ledger)
        listed.pop('authors_omitted')
        with self.assertRaisesRegex(ValueError, 'author-omission conflict'):
            survey.verify_read_bibliography('fixture', item, {**ledgers, 'methods': {'sources': [listed]}})

    def test_history_check_allows_exactly_the_catalog_omission(self):
        records, _ = survey.load_frozen_bibliography(check_history=False)
        original = copy.deepcopy(records[0])
        original['authors'] = list(NAMES)
        fixture = [omit_authors(original), *records[1:]]
        history = '\n'.join(json.dumps(record) for record in [original, *records[1:]]).encode()
        checked = self._check(fixture, history)
        self.assertEqual(checked['history_check'], 'matched_available_pinned_git_object')
        changed = copy.deepcopy(fixture)
        changed[0]['name'] = 'Another title'
        with self.assertRaisesRegex(ValueError, 'differs from the available pinned Git object'):
            self._check(changed, history)

    def _check(self, records, history):
        fixture = json.loads(survey.FROZEN_BIBLIOGRAPHY.read_text())
        fixture['records'] = [{'citation_key': survey.citation_key(r), 'record_sha256': survey.record_sha256(r), 'record': r} for r in records]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.json'
            path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + '\n')
            with mock.patch.object(survey, 'FROZEN_BIBLIOGRAPHY_SHA', survey.digest(path.read_bytes())), \
                    mock.patch.object(survey, 'history_catalog', return_value=history):
                return survey.load_frozen_bibliography(path)[1]


if __name__ == '__main__':
    unittest.main()
