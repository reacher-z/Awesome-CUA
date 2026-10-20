from contextlib import closing
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build import write_sqlite
from catalog_citation import catalog_bibtex
from data_hub import build_download_manifest, data_hub_body
from export_citations import build_citation_exports, encode_citations
from export_rag import build_exports, encode_documents


def record(aid, status='curated'):
    url = 'https://arxiv.org/abs/' + aid
    return {
        'id': 'arxiv:' + aid, 'name': 'Interface study — 界面 ' + aid,
        'kind': 'paper', 'url': url, 'aliases': [], 'authors': ['Literal Author'],
        'review_status': status, 'scope': 'core' if status == 'curated' else 'relevance_pending',
        'summary': 'Reviewed interface annotation.' if status == 'curated' else None,
        'published_at': '2026-01-01', 'updated_at': '2026-01-02',
        'identifiers': {'arxiv': aid}, 'environments': ['unspecified'],
        'topics': ['grounding'] if status == 'curated' else [], 'relations': [],
        'links': [{'rel': 'primary', 'url': url}],
        'licenses': dict.fromkeys(('code', 'data', 'weights', 'document')),
        'evidence': [{'url': url, 'sha256': 'a' * 64, 'retrieved_at': '2026-10-17T00:00:00Z',
                      'role': 'primary', 'method': 'arxiv_api', 'supports': ['name']}],
        'last_verified_at': '2026-10-17T00:00:00Z', 'notes': '',
        'details': {'arxiv_snapshot': {
            'version': 2, 'versioned_url': url + 'v2',
            'submitted_at': '2026-01-01T01:00:00Z', 'updated_at': '2026-01-02T01:00:00Z',
            'abstract_sha256': 'b' * 64, 'abstract_hash_method': 'sha256-utf8-whitespace-collapsed-v1',
        }},
    }


def publication(aid):
    url = 'https://example.org/proceedings/' + aid
    return {'type': 'conference-paper', 'title': 'Published interface study ' + aid,
            'authors': ['Edition Author'], 'date_parts': [2026], 'url': url,
            'doi': None, 'venue': 'Interface proceedings', 'evidence_urls': [url]}


class Tags(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.tags = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class DataHubTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name)
        for name in ('downloads', 'data', 'schemas'):
            (self.destination / name).mkdir()
        reviewed = record('2601.00001')
        pending = record('2601.00002', 'metadata_verified')
        for row in (reviewed, pending):
            row['details']['publication'] = publication(row['identifiers']['arxiv'])
        dataset = record('2601.00003')
        dataset.update(id='github:example/dataset', name='Dataset — 数据', kind='dataset',
                       url='https://github.com/example/dataset', identifiers={}, authors=[],
                       published_at=None, updated_at=None, details={}, topics=['data-generation'])
        self.rows = [reviewed, pending, dataset]
        self.catalog_bytes = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in self.rows).encode()
        (self.destination / 'downloads/catalog.jsonl').write_bytes(self.catalog_bytes)
        self.write_json('data/records.json', self.rows)
        write_sqlite(self.rows, self.destination / 'downloads/catalog.sqlite')
        build_exports(self.rows, self.destination / 'downloads', self.catalog_bytes)
        build_citation_exports(self.rows, self.destination / 'downloads', self.catalog_bytes)
        (self.destination / 'downloads/awesomecua.bib').write_text(catalog_bibtex('2026-01-01T00:00:00Z'), encoding='utf-8')
        self.write_json('downloads/topics.json', {
            'catalog_sha256': hashlib.sha256(self.catalog_bytes).hexdigest(),
            'topics': [{'id': 'grounding'}, {'id': 'data-generation'}],
        })
        self.write_json('downloads/benchmarks-profiles.json', {'profile_count': 0, 'records': []})
        self.write_json('downloads/datasets-profiles.json', {'profile_count': 1, 'records': [{'id': dataset['id']}]})
        self.write_json('downloads/relationships.json', {'relation_count': 0, 'relations': []})
        self.write_json('downloads/sources.json', [{'id': 'source-a'}, {'id': 'source-b'}])
        self.write_json('downloads/repository-aliases.json', [])
        self.write_json('downloads/exclusions.json', {'decisions': [{'id': 'arxiv:2601.99999', 'status': 'excluded'}]})
        self.write_json('downloads/coverage.json', {'total_records': len(self.rows)})
        archive = [reviewed, pending, record('2601.99999', 'metadata_verified')]
        (self.destination / 'downloads/arxiv-archive.jsonl').write_text(
            ''.join(json.dumps(row) + '\n' for row in archive))
        (self.destination / 'downloads/publications.jsonl').write_text(
            ''.join(json.dumps({'id': row['id'], 'publication': row['details']['publication']}) + '\n'
                    for row in (reviewed, pending)))
        for name in ('resource', 'scope-decision', 'publication-observation', 'download-manifest', 'repository-alias'):
            shutil.copy2(ROOT / 'schemas' / (name + '.schema.json'), self.destination / 'schemas')

    def write_json(self, relative, value):
        (self.destination / relative).write_text(json.dumps(value, ensure_ascii=False) + '\n')

    def manifest(self):
        return build_download_manifest(self.destination, self.rows, self.catalog_bytes)

    def rewrite_export(self, manifest_name, filename, body):
        path = self.destination / 'downloads' / filename
        path.write_bytes(body)
        relative = 'downloads/' + manifest_name
        manifest = json.loads((self.destination / relative).read_text())
        entry = next(item for item in manifest['exports'] if item['file'] == filename)
        entry['sha256'] = hashlib.sha256(body).hexdigest()
        if 'bytes' in entry:
            entry['bytes'] = len(body)
        self.write_json(relative, manifest)

    def test_manifest_uses_actual_bytes_fingerprints_units_and_distinct_scopes(self):
        manifest = self.manifest()
        jsonschema.Draft202012Validator(
            json.loads((ROOT / 'schemas/download-manifest.schema.json').read_text()),
            format_checker=jsonschema.FormatChecker()).validate(manifest)
        artifacts = {item['id']: item for item in manifest['artifacts']}
        self.assertEqual(len(artifacts), len(manifest['artifacts']))
        expected = {
            'catalog-jsonl': (3, 'resources', 'active'), 'catalog-json': (3, 'resources', 'active'),
            'catalog-sqlite': (3, 'resources', 'active'), 'rag-reviewed': (2, 'documents', 'reviewed'),
            'rag-all': (3, 'documents', 'active'), 'citations-bib': (1, 'citations', 'reviewed'),
            'citations-all-bib': (2, 'citations', 'active'),
            'publication-citations-bib': (1, 'citations', 'reviewed-publication'),
            'publications': (2, 'editions', 'recorded-publication'),
            'arxiv-archive': (3, 'papers', 'archive'), 'scope-decisions': (1, 'decisions', 'provenance'),
            'datasets-profiles': (1, 'profiles', 'reviewed'), 'benchmarks-profiles': (0, 'profiles', 'reviewed'),
        }
        for identity, values in expected.items():
            item = artifacts[identity]
            self.assertEqual((item['count']['value'], item['count']['unit'], item['scope']), values, identity)
        for item in artifacts.values():
            body = (self.destination / item['path'].lstrip('/')).read_bytes()
            self.assertEqual(item['bytes'], len(body), item['id'])
            self.assertEqual(item['sha256'], hashlib.sha256(body).hexdigest(), item['id'])
        self.assertGreater(artifacts['catalog-jsonl']['bytes'], len(self.catalog_bytes.decode()))
        self.assertNotIn('/downloads/manifest.json', {item['path'] for item in artifacts.values()})
        self.assertEqual(json.loads((self.destination / 'downloads/manifest.json').read_text()), manifest)

    def test_rejects_catalog_and_export_snapshot_mismatch(self):
        for name in ('rag-manifest.json', 'citations-manifest.json', 'topics.json'):
            with self.subTest(name=name):
                path = self.destination / 'downloads' / name
                original = path.read_bytes()
                value = json.loads(original)
                value['catalog_sha256'] = '0' * 64
                self.write_json('downloads/' + name, value)
                with self.assertRaises(ValueError):
                    self.manifest()
                path.write_bytes(original)
        (self.destination / 'downloads/catalog.jsonl').write_bytes(self.catalog_bytes + b'\n')
        with self.assertRaises(ValueError):
            self.manifest()

    def test_rejects_rag_count_or_fingerprint_mismatch(self):
        path = self.destination / 'downloads/rag-documents.jsonl'
        original = path.read_bytes()
        path.write_bytes(original + b'{}\n')
        with self.assertRaises(ValueError):
            self.manifest()
        path.write_bytes(original.replace(b'Reviewed interface annotation.', b'Changed interface annotation.'))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_rejects_citation_count_size_and_fingerprint_mismatch(self):
        relative = 'downloads/citations-manifest.json'
        original = (self.destination / relative).read_bytes()
        for key in ('records', 'bytes', 'sha256'):
            with self.subTest(key=key):
                manifest = json.loads(original)
                entry = manifest['exports'][0]
                entry[key] = '0' * 64 if key == 'sha256' else entry[key] + 1
                self.write_json(relative, manifest)
                with self.assertRaises(ValueError):
                    self.manifest()
        (self.destination / relative).write_bytes(original)

    def test_rejects_same_count_invalid_rag_json_even_with_matching_receipt(self):
        self.rewrite_export('rag-manifest.json', 'rag-documents.jsonl', b'not-json\nalso-not-json\n')
        with self.assertRaises(ValueError):
            self.manifest()

    def test_rejects_metadata_only_document_in_reviewed_rag_with_matching_count_and_sha(self):
        wrong_rows = [self.rows[1], self.rows[2]]
        self.rewrite_export('rag-manifest.json', 'rag-documents.jsonl', encode_documents(wrong_rows, True))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_rejects_same_count_wrong_citation_identity_with_matching_receipt(self):
        original_manifest = (self.destination / 'downloads/citations-manifest.json').read_bytes()
        for filename, file_format in [('citations.csl.json', 'csl-json'), ('citations.bib', 'bibtex')]:
            with self.subTest(filename=filename):
                path = self.destination / 'downloads' / filename
                original = path.read_bytes()
                try:
                    body = encode_citations([self.rows[1]], file_format, include_metadata=True)
                    self.rewrite_export('citations-manifest.json', filename, body)
                    with self.assertRaises(ValueError):
                        self.manifest()
                finally:
                    path.write_bytes(original)
                    (self.destination / 'downloads/citations-manifest.json').write_bytes(original_manifest)

    def test_rejects_same_count_stale_sqlite_record(self):
        with closing(sqlite3.connect(self.destination / 'downloads/catalog.sqlite')) as database:
            database.execute('UPDATE resources SET record_json=? WHERE id=?',
                             (json.dumps({**self.rows[0], 'name': 'Stale snapshot'}), self.rows[0]['id']))
            database.commit()
        with self.assertRaises(ValueError):
            self.manifest()

    def test_bilingual_body_contains_all_artifacts_and_exact_copy_values(self):
        manifest = self.manifest()
        for language in ('en', 'zh'):
            with self.subTest(language=language):
                markup = data_hub_body(manifest, language=language)
                tags = Tags(markup).tags
                links = {attrs.get('href') for tag, attrs in tags if tag == 'a'}
                values = {attrs['data-copy-value'] for tag, attrs in tags
                          if tag == 'button' and 'data-copy-value' in attrs}
                self.assertIn('/data/' if language == 'zh' else '/zh/data/', links)
                self.assertIn('/downloads/manifest.json', links)
                self.assertIn('/zh/agents/' if language == 'zh' else '/agents/', links)
                self.assertIn('git clone https://github.com/reacher-z/Awesome-CUA.git', values)
                for item in manifest['artifacts']:
                    self.assertIn(item['path'], links)
                    self.assertIn('https://awesomecua.github.io' + item['path'], values)
                    self.assertIn(item['sha256'], values)
                self.assertIn(manifest['catalog_sha256'], values)
                self.assertTrue(any(tag == 'input' and attrs.get('id') == 'data-copy-value'
                                    and 'readonly' in attrs for tag, attrs in tags))

    @unittest.skipUnless(shutil.which('node'), 'Node is required for the clipboard behavior fixture')
    def test_copy_script_success_and_denied_clipboard_fallback(self):
        script = r'''
const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const source = fs.readFileSync(process.argv[1], 'utf8');
async function run(lang, denied, value, followingFailure = false) {
  const status = {textContent: ''};
  const fallback = {hidden: true};
  const field = {value: '', focus() {this.focused = true;}, select() {this.selected = true;}};
  const dismiss = {addEventListener(_, fn) {this.click = fn;}};
  const listeners = {};
  const timers = [];
  const cancelled = [];
  let fail = denied;
  let copied;
  const context = {WeakMap, clearTimeout(id) {cancelled.push(id);}, setTimeout(fn) {timers.push(fn); return timers.length;},
    document: {documentElement: {lang}, querySelector(selector) {
      return {'#data-copy-status': status, '.data-copy-fallback': fallback,
              '#data-copy-value': field, '[data-dismiss-copy]': dismiss}[selector];
    }, addEventListener(type, fn) {listeners[type] = fn;}},
    navigator: {clipboard: {async writeText(value) {if (fail) throw Error('Denied'); copied = value;}}}};
  vm.runInNewContext(source, context);
  const button = {textContent: lang === 'zh-CN' ? '复制链接' : 'Copy URL',
    dataset: {copyValue: value}, focus() {this.focused = true;}};
  const original = button.textContent;
  await listeners.click({target: {closest() {return button;}}});
  if (denied) {
    assert.equal(fallback.hidden, false);
    assert.equal(field.value, button.dataset.copyValue);
    assert.equal(field.focused, true);
    assert.equal(field.selected, true);
    assert.equal(button.textContent, original);
    dismiss.click();
    assert.equal(fallback.hidden, true);
    assert.equal(button.focused, true);
  } else {
    assert.equal(copied, button.dataset.copyValue);
    assert.equal(button.dataset.copyState, 'copied');
    assert.equal(button.textContent, lang === 'zh-CN' ? '已复制' : 'Copied');
    assert.equal(fallback.hidden, true);
    if (followingFailure) {
      fail = true;
      button.dataset.copyValue = 'next:' + value;
      await listeners.click({target: {closest() {return button;}}});
      assert.equal(button.textContent, original);
      assert.equal(button.dataset.copyState, undefined);
      assert.equal(fallback.hidden, false);
      assert.equal(field.value, 'next:' + value);
      assert.equal(field.selected, true);
      assert.equal(cancelled.includes(1), true);
      assert.equal(status.textContent, lang === 'zh-CN' ? '请复制已选中的内容。' : 'Copy the selected value below.');
    } else {
      timers[0]();
      assert.equal(button.textContent, original);
      assert.equal(button.dataset.copyState, undefined);
    }
  }
}
(async () => {
  const values = ['git clone https://github.com/reacher-z/Awesome-CUA.git',
                  'https://example.org/文件?a=1&b=2', '0123456789abcdef'.repeat(4)];
  for (const lang of ['en', 'zh-CN']) for (const value of values) {
    for (const denied of [false, true]) await run(lang, denied, value);
    await run(lang, false, value, true);
  }
})()
  .catch(error => {console.error(error); process.exitCode = 1;});
'''
        result = subprocess.run(['node', '-e', script, str(ROOT / 'web/downloads.js')],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
