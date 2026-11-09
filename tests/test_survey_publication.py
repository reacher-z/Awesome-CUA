"""Small failure fixtures for survey publication; real manuscript validation remains separate."""
import contextlib
import copy
import hashlib
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
from search_pages import SITE
from sitemaps import sitemap_urls
from site_config import FORMER_SITES
from survey_bundle import (PAGE, apply_site_shell, MANIFEST, REQUIRED_INPUTS, apply_publication, copy_bundle, digest,
                           load_bundle, publication_plan)
import test_resource_payloads as payloads


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def fixture(root):
    source = root / 'web/survey'
    source.mkdir(parents=True, exist_ok=True)
    # These 23 byte fixtures exercise source completeness, not manuscript correctness.
    for name in REQUIRED_INPUTS:
        authored = root/name
        authored.parent.mkdir(parents=True, exist_ok=True)
        authored.write_text('Authored test input only: '+name+'\n', encoding='utf-8')
    files = {
        'index.html': ('<!doctype html><html lang="en"><head><meta name="robots" content="index,follow">'
                       '<link rel="canonical" href="'+SITE+PAGE+'"><style>h1{}</style></head><body><header class="article-bar"><a href="/">Own bar</a></header><h1>Survey fixture α</h1>  \n'
                       '<a href="references.bib">References</a></body></html>\n\n').encode('utf-8'),
        'references.bib': b'% Test fixture only.\n', 'references.json': b'[]\n',
        'README.md': b'Publication test fixture.\n', 'evidence/reading-index.json': b'{"records": []}\n',
        'evidence/retired.json': b'{"fixture": true}\n'}
    for name, body in files.items():
        target = source/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    manifest = {'schema_version': 1, 'canonical_location_intended': SITE+PAGE,
                'source_commit_for_inventory': 'a'*40, 'catalog_sha256': 'b'*64,
                'input_sha256': {name: digest((root/name).read_bytes()) for name in sorted(REQUIRED_INPUTS)},
                'files': [{'path': name, 'bytes': len(body), 'sha256': digest(body)} for name, body in sorted(files.items())]}
    write_json(source/MANIFEST, manifest)
    return source, manifest


class SurveyBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.manifest = fixture(self.root)
        self.build, self.site = self.root/'build', self.root/'site'
        self.build.mkdir(); self.site.mkdir()

    def copy(self):
        return copy_bundle(self.source, self.build/'survey', source_root=self.root, site_url=SITE)

    def plan(self, pages):
        return publication_plan(self.build, self.site, source_root=self.root, site_url=SITE, pages=pages)

    def contents(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def test_exact_bytes_and_manifest_are_copied_without_cleanup_or_recursive_extras(self):
        (self.source/'unlisted.pdf').write_bytes(b'not part of the approved bundle')
        with mock.patch('subprocess.run', side_effect=AssertionError('No Git process')), \
                mock.patch('socket.create_connection', side_effect=AssertionError('No network')):
            page = self.copy()
        expected = {e['path'] for e in self.manifest['files']} | {MANIFEST}
        copied = self.contents(self.build/'survey')
        self.assertEqual(set(copied), expected)
        for name in expected:
            self.assertEqual(copied[name], (self.source/name).read_bytes())
        self.assertEqual(page, {'path': PAGE, 'indexable': True, 'sha256': digest(copied['index.html'])})
        self.copy()
        self.assertEqual(self.contents(self.build/'survey'), copied)

    def test_source_drift_missing_files_and_bad_fingerprints_fail_before_writes(self):
        authored = self.root/'research/survey/sections/context.html'
        authored.write_text('Changed input\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'source input changed'): self.copy()
        self.assertFalse((self.build/'survey').exists())
        self.source, self.manifest = fixture(self.root)
        (self.source/'references.bib').unlink()
        with self.assertRaises(FileNotFoundError): self.copy()
        self.assertFalse((self.build/'survey').exists())
        self.source, self.manifest = fixture(self.root)
        (self.source/'references.bib').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'fingerprint'): self.copy()
        self.assertFalse((self.build/'survey').exists())

    def test_manifest_paths_versions_sizes_and_duplicates_fail_closed(self):
        cases = []
        for path in ['../outside.txt', '/outside.txt', 'evidence/../../outside.txt', 'evidence/%2e%2e.json',
                     'evidence\\escape.json', 'evidence/.secret.json', 'paper.pdf', MANIFEST]:
            value = copy.deepcopy(self.manifest); value['files'][0]['path'] = path; cases.append(value)
        value = copy.deepcopy(self.manifest); value['schema_version'] = True; cases.append(value)
        value = copy.deepcopy(self.manifest); value['files'][0]['bytes'] = True; cases.append(value)
        value = copy.deepcopy(self.manifest); value['files'].append(value['files'][0]); cases.append(value)
        value = copy.deepcopy(self.manifest); value['input_sha256'] = {'../outside.txt': 'a'*64}; cases.append(value)
        value = copy.deepcopy(self.manifest); value['input_sha256'] = {}; cases.append(value)
        for value in cases:
            with self.subTest(value=value):
                write_json(self.source/MANIFEST, value)
                with self.assertRaises(ValueError): self.copy()
                self.assertFalse((self.build/'survey').exists())

    def test_symlinked_bundle_member_parent_and_source_inputs_are_rejected(self):
        outside = self.root/'outside'; outside.mkdir()
        (outside/'reading-index.json').write_text('{}', encoding='utf-8')
        shutil.rmtree(self.source/'evidence')
        (self.source/'evidence').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'): self.copy()
        self.assertFalse((self.build/'survey').exists())
        (self.source/'evidence').unlink()
        self.source, self.manifest = fixture(self.root)
        authored = self.root/'research/survey/sections/context.html'
        saved = self.root/'authored.html'; authored.rename(saved); authored.symlink_to(saved)
        with self.assertRaisesRegex(ValueError, 'symlink'): self.copy()

    def test_input_manifest_cannot_omit_dependencies_or_add_unsupported_inputs(self):
        self.assertEqual(len(REQUIRED_INPUTS), 23)
        cases = []
        for name in REQUIRED_INPUTS:
            value = copy.deepcopy(self.manifest)
            del value['input_sha256'][name]
            cases.append(value)
        value = copy.deepcopy(self.manifest)
        value['input_sha256'] = {'research/survey/template.html': value['input_sha256']['research/survey/template.html']}
        cases.append(value)
        value = copy.deepcopy(self.manifest)
        value['input_sha256']['research/survey/unsupported.py'] = 'a'*64
        cases.append(value)
        for value in cases:
            with self.subTest(inputs=list(value['input_sha256'])):
                write_json(self.source/MANIFEST, value)
                with self.assertRaisesRegex(ValueError, 'complete supported'): self.copy()
                self.assertFalse((self.build/'survey').exists())

    def test_honestly_rehashed_html_still_needs_canonical_and_robots(self):
        original = (self.source/'index.html').read_bytes()
        for body in [original.replace(b'index,follow', b'noindex,follow'),
                     original.replace((SITE+PAGE).encode(), (SITE+'/wrong/').encode()),
                     original.replace(b'lang="en"', b'lang="zh"')]:
            (self.source/'index.html').write_bytes(body)
            value = copy.deepcopy(self.manifest)
            item = next(x for x in value['files'] if x['path']=='index.html')
            item.update(bytes=len(body), sha256=digest(body));write_json(self.source/MANIFEST, value)
            with self.assertRaisesRegex(ValueError, 'HTML needs'): self.copy()
            self.assertFalse((self.build/'survey').exists())

    def relocate(self, html_location, manifest_location):
        body = (self.source/'index.html').read_bytes().replace((SITE+PAGE).encode(), html_location.encode())
        (self.source/'index.html').write_bytes(body)
        value = copy.deepcopy(self.manifest)
        value['canonical_location_intended'] = manifest_location
        next(x for x in value['files'] if x['path']=='index.html').update(bytes=len(body), sha256=digest(body))
        write_json(self.source/MANIFEST, value)
        return body

    def test_bundle_reviewed_for_a_former_origin_publishes_until_rebuilt_for_the_current_one(self):
        former = FORMER_SITES[0]+PAGE
        body = self.relocate(former, former)
        apply_publication(self.plan([self.copy()]))
        self.assertEqual((self.site/'survey/index.html').read_bytes(), body)
        shutil.rmtree(self.build/'survey')
        self.source, self.manifest = fixture(self.root)
        apply_publication(self.plan([self.copy()]))
        self.assertEqual((self.site/'survey/index.html').read_bytes(), (self.source/'index.html').read_bytes())
        self.assertEqual(json.loads((self.site/'survey'/MANIFEST).read_bytes())['canonical_location_intended'], SITE+PAGE)

    def test_canonical_must_match_its_manifest_and_a_site_origin(self):
        former, foreign = FORMER_SITES[0]+PAGE, 'https://mirror.example'+PAGE
        for html_location, manifest_location, error in [(SITE+PAGE, former, 'HTML needs'), (former, SITE+PAGE, 'HTML needs'),
                                                        (foreign, foreign, 'manifest identity')]:
            with self.subTest(html=html_location, manifest=manifest_location):
                self.source, self.manifest = fixture(self.root)
                self.relocate(html_location, manifest_location)
                with self.assertRaisesRegex(ValueError, error): self.copy()
                self.assertFalse((self.build/'survey').exists())

    def test_symlinked_source_ancestor_is_rejected(self):
        original = self.root/'web'
        original.rename(self.root/'real-web')
        original.symlink_to(self.root/'real-web', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'): self.copy()
        self.assertFalse((self.build/'survey').exists())

    def test_kept_page_drops_retired_companion_but_preserves_unowned_files(self):
        page = self.copy();apply_publication(self.plan([page]))
        note = self.site/'survey/evidence/editor-note.json'
        note.write_text('Unmanaged note\n', encoding='utf-8')
        self.manifest['files'] = [e for e in self.manifest['files'] if e['path']!='evidence/retired.json']
        write_json(self.source/MANIFEST, self.manifest)
        shutil.rmtree(self.build/'survey');page = self.copy()
        (self.build/'survey/unlisted.json').write_text('Do not copy', encoding='utf-8')
        apply_publication(self.plan([page]))
        self.assertFalse((self.site/'survey/evidence/retired.json').exists())
        self.assertFalse((self.site/'survey/unlisted.json').exists())
        self.assertEqual(note.read_text(encoding='utf-8'), 'Unmanaged note\n')

    def test_removed_page_deletes_only_old_manifest_owned_files(self):
        page = self.copy();apply_publication(self.plan([page]))
        note = self.site/'survey/keep.txt';note.write_text('keep', encoding='utf-8')
        # Even an orphaned build bundle must not resurrect a page omitted from the search manifest.
        apply_publication(self.plan([]))
        self.assertEqual(self.contents(self.site/'survey'), {'keep.txt': b'keep'})

    def test_tampered_old_manifest_and_symlink_fail_before_any_owned_deletion(self):
        page = self.copy();apply_publication(self.plan([page]))
        old_path = self.site/'survey'/MANIFEST
        old = json.loads(old_path.read_bytes())
        old['files'].append({'path':'../../outside.txt','bytes':1,'sha256':'a'*64})
        write_json(old_path,old);before = self.contents(self.site)
        with self.assertRaisesRegex(ValueError, 'Unsafe'): self.plan([])
        self.assertEqual(self.contents(self.site), before)
        write_json(old_path,self.manifest)
        original = self.site/'survey/evidence/retired.json'
        original.unlink();original.symlink_to(self.source/'evidence/retired.json')
        with self.assertRaisesRegex(ValueError, 'symlink'): self.plan([])
        self.assertTrue((self.site/'survey/index.html').exists())

    def test_unreviewed_local_edits_or_unowned_collisions_are_not_overwritten(self):
        page = self.copy();apply_publication(self.plan([page]))
        (self.site/'survey/references.bib').write_bytes(b'Local manual edit')
        with self.assertRaisesRegex(ValueError, 'unreviewed local changes'): self.plan([page])
        (self.site/'survey'/MANIFEST).unlink()
        with self.assertRaisesRegex(ValueError, 'unowned'): self.plan([page])
        self.assertEqual((self.site/'survey/references.bib').read_bytes(), b'Local manual edit')

    def test_search_manifest_must_match_the_final_survey_bytes(self):
        page = self.copy();page['sha256']='0'*64
        with self.assertRaisesRegex(ValueError, 'search manifest'): self.plan([page])
        self.assertEqual(self.contents(self.site), {})

    def write_article(self, body):
        (self.source/'index.html').write_bytes(body)
        value = copy.deepcopy(self.manifest)
        next(x for x in value['files'] if x['path']=='index.html').update(bytes=len(body), sha256=digest(body))
        write_json(self.source/MANIFEST, value)

    def shell(self):
        return apply_site_shell(self.build/'survey', head='<link rel="stylesheet" href="/assets/site.css">',
                                top='<header class="site-header">Site</header>', bottom='<footer class="site-footer">Foot</footer>')

    def test_site_shell_wraps_the_reviewed_article_and_keeps_its_fingerprint(self):
        reviewed = (self.source/'index.html').read_bytes()
        self.copy()
        page = self.shell()
        published = (self.build/'survey/index.html').read_bytes()
        self.assertNotIn(b'article-bar', published)
        self.assertLess(published.index(b'/assets/site.css'), published.index(b'<style>'))
        self.assertLess(published.index(b'<header class="site-header">'), published.index(b'<h1>'))
        self.assertLess(published.index(b'</h1>'), published.index(b'<footer class="site-footer">'))
        self.assertEqual(page, {'path': PAGE, 'indexable': True, 'sha256': digest(published)})
        manifest = json.loads((self.build/'survey'/MANIFEST).read_bytes())
        self.assertEqual(manifest['reviewed_index_sha256'], digest(reviewed))
        # The publication plan accepts the shelled page against its rewritten manifest.
        self.assertEqual(self.plan([page])['payloads']['index.html'], published)

    def test_site_shell_needs_the_article_bar_and_changes_nothing_without_it(self):
        self.write_article((self.source/'index.html').read_bytes().replace(b'class="article-bar"', b'class="other"'))
        self.copy()
        before = self.contents(self.build/'survey')
        with self.assertRaisesRegex(ValueError, 'article bar'): self.shell()
        self.assertEqual(self.contents(self.build/'survey'), before)

    def test_linked_optional_companion_cannot_be_removed_only_from_manifest(self):
        path = self.source/'index.html'
        body = path.read_bytes().replace(b'</body>', b'<a href="evidence/retired.json">Evidence</a></body>')
        path.write_bytes(body)
        value = copy.deepcopy(self.manifest)
        item = next(e for e in value['files'] if e['path']=='index.html')
        item.update(bytes=len(body), sha256=digest(body))
        value['files'] = [e for e in value['files'] if e['path']!='evidence/retired.json']
        write_json(self.source/MANIFEST, value)
        with self.assertRaisesRegex(ValueError, 'link target is absent'): self.copy()
        self.assertFalse((self.build/'survey').exists())


class SurveySiteIntegrationTests(unittest.TestCase):
    setUp = payloads.ResourcePayloadTests.setUp
    write_json = payloads.ResourcePayloadTests.write_json
    write_inputs = payloads.ResourcePayloadTests.write_inputs
    build_site = payloads.ResourcePayloadTests.build_site
    publish = payloads.ResourcePayloadTests.publish

    def test_site_manifest_sitemaps_llms_and_publication_preserve_the_same_bundle(self):
        source, _ = fixture(self.root)
        with mock.patch('subprocess.run', side_effect=AssertionError('No Git process')), \
                mock.patch('socket.create_connection', side_effect=AssertionError('No network')):
            self.build_site()
        manifest = json.loads((self.build/'data/search-manifest.json').read_bytes())
        pages = {p['path']:p for p in manifest['pages']}
        published = (self.build/'survey/index.html').read_bytes()
        self.assertEqual(pages[PAGE]['sha256'], hashlib.sha256(published).hexdigest())
        self.assertIn('<h1>Survey fixture α</h1>'.encode('utf-8'), published)
        self.assertIn(b'class="site-footer"', published)
        self.assertEqual(json.loads((self.build/'survey'/MANIFEST).read_bytes())['reviewed_index_sha256'],
                         hashlib.sha256((source/'index.html').read_bytes()).hexdigest())
        self.assertEqual((self.build/'survey/references.bib').read_bytes(), (source/'references.bib').read_bytes())
        self.assertIn(SITE+PAGE,(self.build/'sitemap.txt').read_text(encoding='utf-8').splitlines())
        self.assertIn(SITE+PAGE,sitemap_urls(self.build,SITE))
        for name in ['llms.txt','llms-full.txt']:
            self.assertIn(SITE+PAGE,(self.build/name).read_text(encoding='utf-8'))
        self.assertEqual(len(json.loads((self.build/'data/records.json').read_bytes())),len(self.rows))
        self.publish()
        self.assertEqual((self.site/'survey/index.html').read_bytes(), published)
        self.assertIn(SITE+PAGE,(self.site/'README.md').read_text(encoding='utf-8'))
        shutil.rmtree(source)
        self.build_site();self.publish()
        self.assertFalse((self.site/'survey'/MANIFEST).exists())
        self.assertFalse((self.site/'survey/index.html').exists())
        for path in ['index.html', 'papers/index.html', 'zh/papers/index.html']:
            self.assertNotRegex((self.build/path).read_text(encoding='utf-8'), r'''href\s*=\s*["']/survey/["']''', path)

    def test_invalid_bundle_keeps_prior_build_and_stops_publication_before_other_changes(self):
        source, _ = fixture(self.root);self.build_site();self.publish()
        before = (self.build/'data/search-manifest.json').read_bytes()
        old_site = {p.relative_to(self.site).as_posix():p.read_bytes() for p in self.site.rglob('*') if p.is_file()}
        (self.root/'research/survey/sections/context.html').write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'source input changed'):self.build_site()
        self.assertEqual((self.build/'data/search-manifest.json').read_bytes(),before)
        with self.assertRaisesRegex(ValueError,'source input changed'):self.publish()
        self.assertEqual({p.relative_to(self.site).as_posix():p.read_bytes() for p in self.site.rglob('*') if p.is_file()},old_site)


if __name__ == '__main__':
    unittest.main()
