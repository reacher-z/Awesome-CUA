"""Offline integrity and boundary checks for the complete data-release bundle."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build as builder
from build import write_sqlite
from catalog_citation import catalog_bibtex
from data_hub import build_download_manifest
from export_citations import build_citation_exports
from export_rag import build_exports, encode_documents
from package_data_release import package_release, public_path, ZIP_NAME, MANIFEST_NAME, FIXED_TIME
from topic_pages import write_topic_exports
from specifications import profile_export
from scope_review import metadata_fingerprint, resolve_exclusions, scope_report

COMMIT = 'a' * 40
REF = 'refs/tags/v2026.10.18'


def make_release_fixture(root, *, with_scripts=False):
    """Small actual catalog/SQLite/RAG/citation/topic exports, not mocked hashes."""
    root = Path(root)
    site = root / 'dist/site'
    for directory in ['downloads', 'data', 'schemas']:
        (site / directory).mkdir(parents=True, exist_ok=True)
    def record(aid, status):
        url = 'https://arxiv.org/abs/' + aid
        return {'id':'arxiv:'+aid, 'name':'GUI study 界面 '+aid, 'kind':'paper', 'url':url,
                'aliases':[], 'authors':['Literal Author'], 'review_status':status,
                'scope':'core' if status=='curated' else 'relevance_pending',
                'summary':'A reviewed GUI annotation.' if status=='curated' else None,
                'published_at':'2026-01-01', 'updated_at':'2026-01-02', 'identifiers':{'arxiv':aid},
                'environments':['web'], 'topics':['grounding'] if status=='curated' else [],
                'relations':[], 'links':[{'rel':'primary','url':url}],
                'licenses':dict.fromkeys(['code','data','weights','document']),
                'evidence':[{'url':url,'retrieved_at':'2026-10-17T00:00:00Z','sha256':'b'*64,
                             'role':'primary','method':'arxiv_api','supports':['name','details.arxiv_snapshot']}],
                'last_verified_at':'2026-10-17T00:00:00Z','notes':'',
                'details':{'arxiv_snapshot':{'version':2,'versioned_url':url+'v2',
                    'submitted_at':'2026-01-01T00:00:00Z','updated_at':'2026-01-02T00:00:00Z',
                    'abstract_sha256':'c'*64,'abstract_hash_method':'sha256-utf8-whitespace-collapsed-v1'}}}
    archive = [record('2601.00001','metadata_verified'), record('2601.00002','metadata_verified'), record('2601.99999','metadata_verified')]
    for row in archive:
        row.pop('scope')
    rows = copy.deepcopy(archive[:2])
    rows[0].update(review_status='curated',scope='core',summary='A reviewed GUI annotation.',topics=['grounding'])
    rows[1]['scope']='relevance_pending'
    observations=[]
    for row in rows:
        pub={'type':'conference-paper','title':'Publication '+row['name'],
             'authors':['Edition Author'],'date_parts':[2026],'url':'https://example.org/'+row['identifiers']['arxiv'],
             'doi':None,'venue':'GUI Proceedings','evidence_urls':['https://example.org/'+row['identifiers']['arxiv']]}
        receipt={'url':pub['url'],'retrieved_at':'2026-10-17T00:00:00Z','sha256':'d'*64,
                 'role':'primary','method':'editorial_primary_review','supports':['details.publication']}
        row['details']['publication']=pub
        row['evidence'].append(receipt)
        row['links'].append({'rel':'publication','url':pub['url']})
        observations.append({'id':row['id'],'publication':pub,'evidence':[receipt],'last_verified_at':receipt['retrieved_at']})
    dataset = copy.deepcopy(rows[0])
    dataset.update(id='github:example/data',kind='dataset',name='GUI data',url='https://github.com/example/data',
                   authors=[],identifiers={},published_at=None,updated_at=None,details={},topics=['grounding','data-generation'])
    source='https://raw.githubusercontent.com/example/data/main/README.md'
    dataset['links']=[{'rel':'primary','url':dataset['url']}]
    dataset['evidence']=[{'url':source,'retrieved_at':'2026-10-17T00:00:00Z','sha256':'e'*64,
                         'role':'primary','method':'editorial_primary_review','supports':['name','details.dataset_profile','relations']}]
    dataset['details']['dataset_profile']={'supervision':['GUI grounding'],'modalities':['screenshot'],
        'formats':['JSON'],'splits':['train'],'counts':[],'notes':'Fixture profile with unknown example count.', 'evidence_urls':[source]}
    dataset['relations']=[{'type':'introduced_by','target_id':rows[0]['id'],'evidence_url':source}]
    rows.append(dataset)
    raw = ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True)+'\n' for row in rows).encode()
    def write_json(name, value):
        target = site / name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    (site/'downloads/catalog.jsonl').write_bytes(raw)
    write_json('data/records.json',rows)
    write_sqlite(rows,site/'downloads/catalog.sqlite')
    build_exports(rows,site/'downloads',raw)
    build_citation_exports(rows,site/'downloads',raw)
    (site/'downloads/awesomecua.bib').write_text(catalog_bibtex('2026-10-17T00:00:00Z'),encoding='utf-8')
    write_topic_exports(site,rows,raw)
    write_json('downloads/benchmarks-profiles.json',profile_export(rows,'benchmark'))
    write_json('downloads/datasets-profiles.json',profile_export(rows,'dataset'))
    edges=[{'source_id':r['id'],'source_name':r['name'],'source_kind':r['kind'],**relation} for r in rows for relation in r['relations']]
    write_json('downloads/relationships.json',{'relation_count':len(edges),'semantics':'Reviewed semantic links only. Documentation does not establish training or evaluation dependency.','relations':edges})
    sources=[{'id':'source-a','name':'Fixture source','homepage':'https://example.org/catalog'}]
    write_json('downloads/sources.json',sources)
    write_json('downloads/repository-aliases.json',[])
    excluded=archive[-1]
    decision={'id':excluded['id'],'name':excluded['name'],'url':excluded['url'],'decision':'out_of_scope',
              'basis':'primary_abstract_review','reason':'Fixture paper studies a different domain.',
              'reviewed_at':'2026-10-17T01:00:00Z','metadata_fingerprint':metadata_fingerprint(excluded),
              'evidence':{k:excluded['evidence'][0][k] for k in ['url','sha256','retrieved_at']}}
    resolved=resolve_exclusions({r['id']:r for r in archive+rows},[decision])
    write_json('downloads/exclusions.json',scope_report(resolved))
    def rj(path,*args,**kwargs):
        return {'sources.json':sources,'discovery-runs.json':[],'repository-aliases.json':[]}.get(Path(path).name,args[0] if args else {})
    def rjl(path,*args,**kwargs):
        return {'papers.jsonl':archive,'publications.jsonl':observations}.get(Path(path).name,[])
    with mock.patch.object(builder,'read_json',rj),mock.patch.object(builder,'read_jsonl',rjl):
        coverage=builder.coverage(rows,[],resolved)
    write_json('downloads/coverage.json',coverage)
    (site/'downloads/arxiv-archive.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in archive))
    (site/'downloads/publications.jsonl').write_text(''.join(json.dumps(item)+'\n' for item in observations))
    (root/'schemas').mkdir(exist_ok=True)
    for name in ['resource','scope-decision','publication-observation','download-manifest','repository-alias']:
        shutil.copy2(ROOT/'schemas'/(name+'.schema.json'),site/'schemas')
        shutil.copy2(ROOT/'schemas'/(name+'.schema.json'),root/'schemas')
    build_download_manifest(site,rows,raw)
    (root/'data').mkdir(exist_ok=True)
    (root/'data/catalog.jsonl').write_bytes(raw)
    (root/'data/coverage.json').write_text(json.dumps(coverage)+'\n')
    shutil.copy2(site/'data/records.json',root/'dist/catalog.json')
    shutil.copy2(site/'downloads/catalog.sqlite',root/'dist/catalog.sqlite')
    shutil.copy2(ROOT/'LICENSE',root/'LICENSE')
    if with_scripts:
        shutil.copytree(ROOT/'scripts',root/'scripts',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (root/'schemas').mkdir(exist_ok=True)
        for schema in (ROOT/'schemas').glob('*.json'):
            shutil.copy2(schema,root/'schemas')
        shutil.copy2(ROOT/'data/topics.json',root/'data/topics.json')
    return site,rows


class DataReleasePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.site,self.rows=make_release_fixture(self.root)
        self.out=self.root/'release/assets'
    def package(self, **kwargs):
        return package_release(self.site,self.out,source_commit=kwargs.pop('source_commit',COMMIT),
                               source_ref=kwargs.pop('source_ref',REF),repo_root=self.root,**kwargs)
    def write_json(self, relative, value):
        (self.site/relative).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    def refresh_main_hashes(self):
        manifest=json.loads((self.site/'downloads/manifest.json').read_text())
        for entry in manifest['artifacts']:
            path=self.site/entry['path'].lstrip('/')
            body=path.read_bytes();entry.update(bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
        self.write_json('downloads/manifest.json',manifest)
    def test_complete_bundle_preserves_public_paths_and_every_member_fingerprint(self):
        original=(self.site/'downloads/manifest.json').read_bytes()
        result=self.package()
        self.assertEqual((self.site/'downloads/manifest.json').read_bytes(),original)
        manifest=json.loads(original)
        expected={e['path'].lstrip('/') for e in manifest['artifacts']}
        topics=json.loads((self.site/'downloads/topics.json').read_text())
        expected|={e['url'].lstrip('/') for topic in topics['topics'] for e in topic['exports']}
        expected|={'downloads/manifest.json','LICENSE','README.md','AGENTS.md','data/build-info.json'}
        with zipfile.ZipFile(self.out/ZIP_NAME) as archive:
            self.assertEqual(archive.namelist(),sorted(expected))
            for item in result['files']:
                body=archive.read(item['path'])
                self.assertEqual(item['bytes'],len(body))
                self.assertEqual(item['sha256'],hashlib.sha256(body).hexdigest())
            for item in archive.infolist():
                self.assertEqual(item.date_time,FIXED_TIME)
                self.assertTrue(stat.S_ISREG(item.external_attr>>16))
                self.assertFalse(item.filename.endswith(('.html','.pdf','.pt','.safetensors')))
            self.assertIn('downloads/catalog.jsonl',archive.read('README.md').decode())
            self.assertIn('no scripts/',archive.read('AGENTS.md').decode())
            self.assertEqual(json.loads(archive.read('data/build-info.json'))['source_commit'],COMMIT)
        self.assertEqual(result['source_commit'],COMMIT)
        self.assertEqual(result['population_counts']['active'],{'value':3,'unit':'resources','scope':'active'})
        self.assertEqual(result['source_ref'],REF)
        self.assertEqual(result['source_ref_type'],'tag')
        self.assertEqual(result['zip']['sha256'],hashlib.sha256((self.out/ZIP_NAME).read_bytes()).hexdigest())
        self.assertEqual(json.loads((self.out/MANIFEST_NAME).read_text()),result)
        self.assertEqual(next(e for e in result['files'] if e['path']=='downloads/rag-all-records.jsonl')['count'],{'value':3,'unit':'documents'})
        self.assertEqual(next(e for e in result['files'] if e['path']=='downloads/topics/grounding/records.jsonl')['count'],{'value':2,'unit':'resources'})
    def test_rebuild_is_byte_deterministic_despite_input_mtimes(self):
        first=self.package();zip_bytes=(self.out/ZIP_NAME).read_bytes();manifest_bytes=(self.out/MANIFEST_NAME).read_bytes()
        for file in self.site.rglob('*'):
            if file.is_file():os.utime(file,(1_800_000_000,1_800_000_000))
        self.assertEqual(self.package(),first)
        self.assertEqual((self.out/ZIP_NAME).read_bytes(),zip_bytes)
        self.assertEqual((self.out/MANIFEST_NAME).read_bytes(),manifest_bytes)
        changed=self.package(source_ref='refs/heads/release-preview')
        self.assertEqual(changed['source_ref_type'],'branch-preview')
        self.assertNotEqual(changed['zip']['sha256'],first['zip']['sha256'])
    def test_requires_full_source_commit_and_explicit_ref(self):
        for commit in ['', 'abc123', 'z'*40]:
            with self.subTest(commit=commit), self.assertRaises(ValueError):self.package(source_commit=commit)
        for ref in ['', 'v2026', 'refs/tags/not-version', 'refs/heads/main\nextra']:
            with self.subTest(ref=ref), self.assertRaises(ValueError):self.package(source_ref=ref)
        self.assertFalse(self.out.exists())
    def test_tampering_rejected_without_replacing_previous_release(self):
        self.package();before={n:(self.out/n).read_bytes() for n in [ZIP_NAME,MANIFEST_NAME]}
        with (self.site/'downloads/rag-documents.jsonl').open('ab') as stream:stream.write(b'{}\n')
        with self.assertRaisesRegex(ValueError,'SHA-256'):self.package()
        self.assertEqual({n:(self.out/n).read_bytes() for n in before},before)
    def test_forged_consistent_hashes_do_not_hide_wrong_rag_selection(self):
        body=encode_documents([self.rows[1],self.rows[2]],include_metadata=True)
        (self.site/'downloads/rag-documents.jsonl').write_bytes(body)
        rag=json.loads((self.site/'downloads/rag-manifest.json').read_text());rag['exports'][0]['sha256']=hashlib.sha256(body).hexdigest()
        self.write_json('downloads/rag-manifest.json',rag);self.refresh_main_hashes()
        with self.assertRaisesRegex(ValueError,'RAG content'):self.package()
        self.assertFalse(self.out.exists())
    def test_topic_contents_are_checked_against_records_even_with_matching_hashes(self):
        topics=json.loads((self.site/'downloads/topics.json').read_text())
        entry=next(t for t in topics['topics'] if t['id']=='grounding')['exports'][0]
        body=(json.dumps(self.rows[1])+'\n'+json.dumps(self.rows[2])+'\n').encode()
        (self.site/entry['url'].lstrip('/')).write_bytes(body);entry.update(bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
        self.write_json('downloads/topics.json',topics);self.refresh_main_hashes()
        with self.assertRaisesRegex(ValueError,'Topic export content'):self.package()
    def test_snapshot_mismatch_and_missing_exports_fail_closed(self):
        path=self.site/'downloads/citations-manifest.json';original=path.read_bytes();value=json.loads(original)
        value['catalog_sha256']='0'*64;self.write_json('downloads/citations-manifest.json',value);self.refresh_main_hashes()
        with self.assertRaisesRegex(ValueError,'snapshots differ'):self.package()
        path.write_bytes(original);self.refresh_main_hashes()
        value=json.loads((self.site/'downloads/rag-manifest.json').read_text());value['exports'].pop();self.write_json('downloads/rag-manifest.json',value);self.refresh_main_hashes()
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.package()
    def test_paths_reject_traversal_absolute_urls_hidden_and_encoded_components(self):
        for path in ['/../secret','//downloads/catalog.jsonl','https://example.org/a','/downloads/.private.json',
                     '/downloads/../secret','/downloads/%2e%2e/a','/downloads/a\\b.json','/downloads/a.json?x=1']:
            with self.subTest(path=path),self.assertRaises(ValueError):public_path(path)
        manifest=json.loads((self.site/'downloads/manifest.json').read_text());manifest['artifacts'][0]['path']='/downloads/../secret'
        self.write_json('downloads/manifest.json',manifest)
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.package()
        self.assertFalse(self.out.exists())
    def test_topic_export_path_cannot_escape_or_add_hidden_files(self):
        topics=json.loads((self.site/'downloads/topics.json').read_text());topics['topics'][0]['exports'][0]['url']='/downloads/topics/a/../../secret'
        self.write_json('downloads/topics.json',topics);self.refresh_main_hashes()
        with self.assertRaisesRegex(ValueError,'unexpected topic export'):self.package()
    def test_symlinked_parent_and_license_are_rejected(self):
        downloads=self.site/'downloads';downloads.rename(self.site/'real-downloads');downloads.symlink_to('real-downloads',target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'Symlink'):self.package()
        downloads.unlink();(self.site/'real-downloads').rename(downloads)
        (self.root/'LICENSE').unlink();(self.root/'LICENSE').symlink_to(ROOT/'LICENSE')
        with self.assertRaisesRegex(ValueError,'Symlink'):self.package()
    def test_duplicate_manifest_entry_is_rejected(self):
        manifest=json.loads((self.site/'downloads/manifest.json').read_text());manifest['artifacts'].append(manifest['artifacts'][0])
        self.write_json('downloads/manifest.json',manifest)
        with self.assertRaisesRegex(ValueError,'duplicate'):self.package()
    def test_boolean_count_is_not_accepted_as_an_integer(self):
        manifest=json.loads((self.site/'downloads/manifest.json').read_text())
        manifest['artifacts'][0]['count']['value']=True
        self.write_json('downloads/manifest.json',manifest)
        with self.assertRaisesRegex(ValueError,'nonnegative integer'):self.package()

    def test_pair_publication_failure_rolls_back_both_initial_and_existing_outputs(self):
        real_replace=os.replace
        for previous in [False,True]:
            with self.subTest(previous=previous):
                if self.out.exists():shutil.rmtree(self.out)
                before={}
                if previous:
                    self.package()
                    before={name:(self.out/name).read_bytes() for name in [ZIP_NAME,MANIFEST_NAME]}
                calls=0
                def fail_manifest(source,target):
                    nonlocal calls
                    calls+=1
                    if calls==2:raise OSError('injected second publication rename failure')
                    return real_replace(source,target)
                with mock.patch('package_data_release.os.replace',side_effect=fail_manifest):
                    with self.assertRaisesRegex(OSError,'injected second'):
                        self.package(source_ref='refs/heads/new-preview')
                for name in [ZIP_NAME,MANIFEST_NAME]:
                    if previous:self.assertEqual((self.out/name).read_bytes(),before[name])
                    else:self.assertFalse((self.out/name).exists())
                self.assertEqual(sorted(p.name for p in self.out.iterdir()),sorted(before))

    def test_honest_hashes_do_not_authorize_invalid_provenance_or_contracts(self):
        cases={
            'downloads/coverage.json':json.dumps({**json.loads((self.site/'downloads/coverage.json').read_text()),'total_records':999}).encode(),
            'downloads/arxiv-archive.jsonl':b'not-json\n',
            'downloads/publications.jsonl':b'not-json\n',
            'schemas/resource.schema.json':b'not-json\n',
            'downloads/relationships.json':json.dumps({'relation_count':1,'semantics':'Reviewed semantic links only. Documentation does not establish training or evaluation dependency.','relations':[{'source_id':'github:fake/owner','target_id':self.rows[0]['id'],'type':'introduced_by','evidence_url':'https://example.org/none'}]}).encode(),
        }
        originals={name:(self.site/name).read_bytes() for name in cases}
        for name,payload in cases.items():
            with self.subTest(name=name):
                (self.site/name).write_bytes(payload);self.refresh_main_hashes()
                with self.assertRaises(ValueError):self.package()
                (self.site/name).write_bytes(originals[name]);self.refresh_main_hashes()
        self.assertFalse(self.out.exists())

    def test_valid_json_still_requires_archive_publication_and_trusted_schema_contracts(self):
        paths=['downloads/arxiv-archive.jsonl','downloads/publications.jsonl','schemas/resource.schema.json']
        for name in paths:
            with self.subTest(name=name):
                path=self.site/name;original=path.read_bytes()
                if name.endswith('arxiv-archive.jsonl'):
                    rows=[json.loads(line) for line in original.splitlines()];rows[0].pop('authors')
                    payload=''.join(json.dumps(row)+'\n' for row in rows).encode()
                elif name.endswith('publications.jsonl'):
                    rows=[json.loads(line) for line in original.splitlines()];rows[0].pop('evidence')
                    payload=''.join(json.dumps(row)+'\n' for row in rows).encode()
                else:payload=b'{"type":"object"}\n'
                path.write_bytes(payload);self.refresh_main_hashes()
                with self.assertRaises(ValueError):self.package()
                path.write_bytes(original);self.refresh_main_hashes()

    def test_wrong_profile_owner_or_boolean_version_is_rejected(self):
        path=self.site/'downloads/datasets-profiles.json';original=path.read_bytes();profile=json.loads(original)
        profile['records'][0]['id']='github:fake/owner'
        self.write_json('downloads/datasets-profiles.json',profile);self.refresh_main_hashes()
        with self.assertRaisesRegex(ValueError,'profiles'):self.package()
        path.write_bytes(original);self.refresh_main_hashes()
        manifest=json.loads((self.site/'downloads/manifest.json').read_text());manifest['schema_version']=True
        self.write_json('downloads/manifest.json',manifest)
        with self.assertRaisesRegex(ValueError,'version'):self.package()

    def test_residual_output_files_cannot_silently_join_release(self):
        self.out.mkdir(parents=True);(self.out/'unreviewed.bin').write_bytes(b'unexpected')
        with self.assertRaisesRegex(ValueError,'Unexpected'):self.package()
        self.assertFalse((self.out/ZIP_NAME).exists())

    def test_cli_uses_standard_library_with_site_packages_disabled(self):
        env={k:v for k,v in os.environ.items() if k not in {'PYTHONPATH','PYTHONHOME'}}
        env['PYTHONDONTWRITEBYTECODE']='1'
        result=subprocess.run([sys.executable,'-S',str(ROOT/'scripts/package_data_release.py'),'--site',str(self.site),
                               '--output',str(self.out),'--source-commit',COMMIT,'--source-ref','refs/heads/main'],
                              env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue((self.out/ZIP_NAME).exists())


if __name__ == '__main__':
    unittest.main()
