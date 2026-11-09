"""End-to-end fixtures for per-resource exports and incremental publication."""
import collections
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_site
import prepare_publication
from search_pages import resource_path


MANAGED = ('index.html', 'index.md', 'record.json', 'citation.bib', 'citation.csl.json',
           'publication-citation.bib','publication-citation.csl.json')


def paper(aid, status='curated', kind='paper'):
    url = 'https://arxiv.org/abs/' + aid
    return {
        'id': 'arxiv:' + aid, 'name': 'Payload fixture ' + aid, 'kind': kind,
        'url': url, 'aliases': [], 'environments': ['unspecified'], 'topics': [],
        'scope': 'core' if status == 'curated' else 'relevance_pending',
        'summary': 'A fixture annotation for GUI research.' if status == 'curated' else None,
        'review_status': status, 'published_at': '2024-01-02', 'updated_at': '2025-03-04',
        'authors': ['王小明', 'A Researcher'], 'identifiers': {'arxiv': aid},
        'links': [{'rel': 'paper', 'url': url}], 'relations': [],
        'licenses': dict.fromkeys(('code', 'data', 'weights', 'document')),
        'evidence': [{'role': 'primary', 'method': 'arxiv_api',
                      'supports': ['name', 'authors', 'details.arxiv_snapshot'],
                      'url': 'https://example.org/fixture.atom', 'sha256': 'a' * 64,
                      'retrieved_at': '2026-10-16T01:00:00Z'}],
        'last_verified_at': '2026-10-16T01:00:00Z', 'notes': 'Fixture only.',
        'details': {'arxiv_snapshot': {
            'version': 2, 'versioned_url': url + 'v2',
            'submitted_at': '2024-01-02T03:04:05Z', 'updated_at': '2025-03-04T05:06:07Z',
            'abstract_sha256': 'b' * 64,
            'abstract_hash_method': 'sha256-utf8-whitespace-collapsed-v1',
        }},
    }


class ResourcePayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        self.build = self.root / 'dist/site'
        self.site = Path(self.temp.name) / 'published'
        (self.site / '.git').mkdir(parents=True)
        # These catalog fixtures have no research source inputs. Survey publication has its own fixtures.
        shutil.copytree(ROOT / 'web', self.root / 'web', ignore=shutil.ignore_patterns('survey'))
        shutil.copytree(ROOT / 'schemas', self.root / 'schemas')
        for name in ('AGENTS.md', 'LICENSE'):
            shutil.copy2(ROOT / name, self.root / name)
        for name in ('schemas/resource.schema.json', 'schemas/scope-decision.schema.json',
                     '.github/ISSUE_TEMPLATE/resource.yml'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        self.reviewed = paper('2401.00001')
        self.metadata = paper('2401.00002', 'metadata_verified')
        self.metadata.update(authors=[], published_at=None, updated_at=None, details={})
        self.survey = paper('2401.00003', kind='survey')
        self.tool = copy.deepcopy(self.reviewed)
        self.tool.update(id='github:example/tool', name='Fixture tool', kind='tool',
                         url='https://github.com/example/tool', authors=[], identifiers={},
                         published_at=None, updated_at=None, details={},
                         links=[{'rel': 'primary', 'url': 'https://github.com/example/tool'}])
        self.tool['evidence'][0].update(method='editorial_primary_review', supports=['relations'])
        self.tool['relations'] = [{'type': 'documented_by', 'target_id': self.reviewed['id'],
                                  'evidence_url': self.tool['evidence'][0]['url']}]
        self.rows = [self.reviewed, self.metadata, self.survey, self.tool]
        self.excluded = paper('2401.00004', 'metadata_verified')
        self.removed = paper('2401.00005', 'metadata_verified')
        self.decision = {
            'id': self.excluded['id'], 'name': self.excluded['name'], 'url': self.excluded['url'],
            'decision': 'out_of_scope', 'basis': 'primary_abstract_review',
            'reason': 'Fixture source is outside the GUI-agent scope.',
            'reviewed_at': '2026-10-16T02:00:00Z', 'metadata_fingerprint': 'c' * 64,
            'evidence': {k: self.excluded['evidence'][0][k] for k in ('url', 'sha256', 'retrieved_at')},
            'status': 'excluded', 'status_reason': 'Fixture snapshot unchanged.',
        }
        self.write_inputs(self.rows)

    def write_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) + '\n')

    def write_inputs(self, rows, decisions=()):
        data = self.root / 'data'
        data.mkdir(exist_ok=True)
        (data / 'catalog.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
        archive = copy.deepcopy([self.reviewed, self.metadata, self.survey, self.excluded, self.removed])
        for record in archive:
            record['details'].pop('publication',None)
        (data / 'papers.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in archive))
        coverage = {
            'as_of_utc': '2026-10-16T02:00:00Z', 'total_records': len(rows),
            'curated_records': sum(r['review_status'] == 'curated' for r in rows),
            'metadata_only_records': sum(r['review_status'] == 'metadata_verified' for r in rows),
            'bibliographic_records': sum(r['id'].startswith('arxiv:') for r in rows),
            'by_kind': dict(collections.Counter(r['kind'] for r in rows)),
            'unindexed_candidates': 0, 'sources': [], 'excluded_records': len(decisions),
            'arxiv_archive_records': len(archive),
        }
        self.write_json(data / 'coverage.json', coverage)
        self.write_json(data / 'sources.json', [])
        self.write_json(data / 'site-guides.json', [])
        self.write_json(data / 'exclusion-status.json', {
            'excluded_records': len(decisions), 'revalidation_pending': 0, 'decisions': list(decisions)})
        for name in ('scan-config.json', 'site-discovery.json'):
            shutil.copy2(ROOT / 'data' / name, data / name)

    def build_site(self):
        with mock.patch.object(build_site, 'ROOT', self.root), contextlib.redirect_stdout(io.StringIO()):
            build_site.build_site(self.build)

    def publish(self):
        with mock.patch.object(prepare_publication, 'ROOT', self.root), \
                mock.patch.object(sys, 'argv', ['prepare_publication.py', '--site-dir', str(self.site), '--skip-profile']), \
                contextlib.redirect_stdout(io.StringIO()):
            prepare_publication.main()

    def folder(self, output, row):
        return output / resource_path(row).lstrip('/')

    def seed_managed(self, output, row):
        folder = self.folder(output, row)
        folder.mkdir(parents=True, exist_ok=True)
        for name in MANAGED:
            (folder / name).write_text('STALE RESOURCE CONTENT\n')

    def test_active_payloads_preserve_full_records_and_review_states(self):
        self.build_site()
        for row in self.rows:
            folder = self.folder(self.build, row)
            self.assertEqual(json.loads((folder / 'record.json').read_text()), row)
            self.assertIn('record.json', (folder / 'index.html').read_text())
            if row['kind'] in ('paper', 'survey'):
                item = json.loads((folder / 'citation.csl.json').read_text())
                self.assertEqual(item['id'], row['id'])
                self.assertEqual(item['custom']['catalog_review_status'], row['review_status'])
                self.assertTrue((folder / 'citation.bib').read_text().strip())
                if row is self.metadata:
                    for unknown in ('issued', 'author', 'version', 'DOI', 'container-title'):
                        self.assertNotIn(unknown, item)
                    self.assertEqual(item['URL'], row['url'])
                else:
                    self.assertEqual(item['issued'], {'date-parts': [[2024, 1, 2]]})
                    self.assertEqual(item['URL'], row['url'] + 'v2')
                    self.assertEqual(item['author'], [{'literal': name} for name in row['authors']])
            else:
                self.assertFalse((folder / 'citation.bib').exists())
                self.assertFalse((folder / 'citation.csl.json').exists())
        index = json.loads((self.build / 'data/index.json').read_text())
        compact = {r['id']: r for r in index['records']}
        self.assertEqual(compact[self.reviewed['id']]['incoming_relations'], [{
            'source_id': self.tool['id'], 'type': 'documented_by',
            'evidence_url': self.tool['evidence'][0]['url']}])
        self.assertEqual(compact[self.reviewed['id']]['related_count'], 1)
        self.assertEqual(compact[self.tool['id']]['incoming_relations'], [])

    def test_incremental_exclusion_and_removal_survive_publication_copy(self):
        self.write_inputs([*self.rows, self.excluded, self.removed])
        self.build_site()
        self.publish()
        self.assertTrue((self.folder(self.site, self.excluded) / 'citation.bib').exists())
        self.assertTrue((self.folder(self.site, self.removed) / 'record.json').exists())
        # Old auxiliary machine files can also predate a kind correction.
        for output in (self.build, self.site):
            for name in ('citation.bib', 'citation.csl.json'):
                (self.folder(output, self.tool) / name).write_text('STALE CITATION\n')
        self.write_inputs(self.rows, [self.decision])
        self.build_site()
        self.publish()
        for output in (self.build, self.site):
            excluded = self.folder(output, self.excluded)
            payload = json.loads((excluded / 'record.json').read_text())
            self.assertEqual(payload['status'], 'excluded')
            self.assertEqual(payload['id'], self.excluded['id'])
            self.assertEqual(payload['decision'], self.decision)
            self.assertNotIn('review_status', payload)
            for name in ('citation.bib', 'citation.csl.json'):
                self.assertFalse((excluded / name).exists())
                self.assertFalse((self.folder(output, self.tool) / name).exists())
            for name in MANAGED:
                self.assertFalse((self.folder(output, self.removed) / name).exists(), (output, name))
        archive = (self.site / 'downloads/arxiv-archive.jsonl').read_text()
        self.assertIn(self.excluded['id'], archive)
        self.assertEqual(json.loads((self.folder(self.site, self.metadata) / 'record.json').read_text()), self.metadata)

    def test_publication_removes_machine_files_absent_from_current_resource_build(self):
        self.write_inputs(self.rows, [self.decision])
        self.build_site()
        self.seed_managed(self.site, self.excluded)
        self.seed_managed(self.site, self.tool)
        # Simulate a current producer without the new record export, while the
        # publication checkout still contains a previous active payload.
        (self.folder(self.build, self.tool) / 'record.json').unlink()
        self.publish()
        for row in (self.excluded, self.tool):
            for name in ('citation.bib', 'citation.csl.json'):
                self.assertFalse((self.folder(self.site, row) / name).exists())
        self.assertFalse((self.folder(self.site, self.tool) / 'record.json').exists())
        self.assertEqual(json.loads((self.folder(self.site, self.excluded) / 'record.json').read_text())['status'], 'excluded')

    def test_build_cleans_orphan_managed_files_missing_from_previous_manifest(self):
        self.build_site()
        # An older/interrupted build may have written its new manifest before
        # deleting the old payloads. A subsequent build must reconcile them.
        self.seed_managed(self.build, self.removed)
        self.seed_managed(self.site, self.removed)
        unmanaged = self.folder(self.site, self.removed) / 'publisher-note.txt'
        unmanaged.write_text('Preserve unmanaged material.\n')
        self.build_site()
        # The build output is replaced whole; the publication checkout keeps material it did not generate.
        self.assertFalse(self.folder(self.build, self.removed).exists())
        self.publish()
        for name in MANAGED:
            self.assertFalse((self.folder(self.site, self.removed) / name).exists(), name)
        self.assertTrue(unmanaged.exists())

    def test_publication_does_not_restore_removed_files_from_orphaned_build_output(self):
        self.build_site()
        self.seed_managed(self.build, self.removed)
        self.seed_managed(self.site, self.removed)
        old = json.loads((self.build / 'data/search-manifest.json').read_text())
        old['pages'].append({'path': resource_path(self.removed), 'indexable': False, 'sha256': 'd' * 64})
        self.write_json(self.site / 'data/search-manifest.json', old)
        self.publish()
        for name in MANAGED:
            self.assertFalse((self.folder(self.site, self.removed) / name).exists(), name)

    def test_publication_citations_keep_their_edition_and_are_removed_with_metadata(self):
        source='https://publisher.example/paper'
        self.reviewed['details']['publication']={'type':'conference-paper','title':'Published edition title',
            'authors':['Publication Author'],'date_parts':[2025,7],'venue':'Example Conference',
            'url':source,'evidence_urls':[source]}
        self.reviewed['evidence'].append({'role':'primary','method':'editorial_primary_review',
            'supports':['details.publication'],'url':source,'sha256':'e'*64,'retrieved_at':'2026-10-16T01:00:00Z'})
        self.write_inputs(self.rows)
        self.build_site();self.publish()
        folder=self.folder(self.site,self.reviewed)
        retained=json.loads((folder/'citation.csl.json').read_text())
        published=json.loads((folder/'publication-citation.csl.json').read_text())
        self.assertEqual(retained['issued']['date-parts'],[[2024,1,2]])
        self.assertEqual(published['issued']['date-parts'],[[2025,7]])
        self.assertEqual(published['author'],[{'literal':'Publication Author'}])
        self.assertEqual(published['URL'],source)
        self.assertTrue((folder/'publication-citation.bib').exists())
        self.reviewed['details'].pop('publication')
        self.write_inputs(self.rows);self.build_site();self.publish()
        for output in (self.build,self.site):
            for filename in ('publication-citation.bib','publication-citation.csl.json'):
                self.assertFalse((self.folder(output,self.reviewed)/filename).exists())

    def test_topic_subsets_and_bilingual_pages_remove_stale_members_after_review_changes(self):
        self.reviewed['topics']=['grounding']
        self.metadata['topics']=['grounding','video']
        self.write_inputs(self.rows)
        self.build_site();self.publish()
        self.assertTrue((self.site/'topics/grounding/index.html').exists())
        self.assertTrue((self.site/'zh/topics/grounding/index.md').exists())
        self.assertFalse((self.site/'topics/video/index.html').exists())
        exported=[json.loads(line) for line in (self.site/'downloads/topics/grounding/records.jsonl').read_text().splitlines()]
        self.assertEqual(exported,[self.reviewed])
        self.reviewed['topics']=[]
        self.write_inputs(self.rows)
        self.build_site();self.publish()
        for output in (self.build,self.site):
            for prefix in ('topics/','zh/topics/'):
                self.assertFalse((output/prefix/'grounding/index.html').exists())
                self.assertFalse((output/prefix/'grounding/index.md').exists())
            for name in ('records.jsonl','citations.bib','citations.csl.json'):
                self.assertFalse((output/'downloads/topics/grounding'/name).exists())


if __name__ == '__main__':
    unittest.main()
