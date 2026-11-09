import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import catalog
import discover_papers as discovery


class PaperDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        self.patch=mock.patch.object(discovery,'DATA',self.path);self.patch.start()
        self.sleep=mock.patch.object(discovery.time,'sleep');self.sleep.start()
        self.queries=[{'id':'hf-search-desktop','query':'desktop GUI agent','area':'Desktop','limit':5},
                      {'id':'hf-search-mobile','query':'mobile GUI agent','area':'Mobile','limit':5}]
        self.old={'id':'arxiv:2401.00001','url':'https://arxiv.org/abs/2401.00001','provider':'arxiv',
            'first_discovered_at':'2026-10-01T00:00:00Z','discovered_in':[
                {'source_id':'hf-search-desktop','line':None,'section':'old','snapshot_sha256':'a'*64},
                {'source_id':'official-release','line':10,'section':'paper','snapshot_sha256':'b'*64}]}
        catalog.write_jsonl(self.path/'candidates.jsonl',[self.old])
        catalog.write_jsonl(self.path/'papers.jsonl',[{'id':self.old['id']}])
    def tearDown(self):
        self.sleep.stop();self.patch.stop();self.temp.cleanup()
    def response(self,payload,status=200):
        body=json.dumps(payload).encode()
        info={'url':'https://huggingface.co/api/papers/search','retrieved_at':'2026-10-17T00:00:00Z',
              'ok':status==200,'status':status}
        if status==200:info['sha256']=hashlib.sha256(body).hexdigest()
        else:info['error']=f'HTTP {status}'
        return info,body
    def run_queries(self,responses,queries=None):
        with mock.patch.object(discovery,'fetch',side_effect=responses) as fetch,contextlib.redirect_stdout(io.StringIO()):
            result=discovery.discover(queries or self.queries,True)
        return result,fetch
    def test_known_and_new_hits_deduplicate_versions_without_claiming_review(self):
        result,_=self.run_queries([self.response([{'paper':{'id':'2401.00001v2'}},{'id':'2610.00002'},{'id':'2610.00002v3'}]),
                                   self.response([{'id':'2610.00002'}])])
        rows=catalog.read_jsonl(self.path/'candidates.jsonl')
        self.assertEqual(result['unique_identifiers'],2);self.assertEqual(result['new_candidate_count'],1)
        self.assertEqual(result['without_arxiv_metadata'],1);self.assertEqual(result['status'],'success')
        self.assertEqual(rows[0]['first_discovered_at'],self.old['first_discovered_at'])
        self.assertEqual(len(rows[1]['discovered_in']),2)
        self.assertNotIn('review_status',rows[1]);self.assertNotIn('summary',rows[1])
        self.assertEqual(catalog.read_jsonl(self.path/'papers.jsonl'),[{'id':self.old['id']}])
    def test_true_empty_window_replaces_only_its_current_occurrences(self):
        result,_=self.run_queries([self.response([])],self.queries[:1])
        row=catalog.read_jsonl(self.path/'candidates.jsonl')[0]
        self.assertEqual([o['source_id'] for o in row['discovered_in']],['official-release'])
        self.assertEqual(result['unique_identifiers'],0);self.assertEqual(result['status'],'success')
        self.assertIn('not exhaustive',result['scope'])
    def test_malformed_success_response_never_erases_previous_population(self):
        for payload in [{},[None],[{'id':'2610.00002'},{'id':'2610.00003/extra'}],[{'paper':None}]]:
            with self.subTest(payload=payload):
                result,_=self.run_queries([self.response(payload)],self.queries[:1])
                self.assertEqual(result['status'],'partial')
                self.assertIn('parse_error',result['queries'][0])
                self.assertEqual(catalog.read_jsonl(self.path/'candidates.jsonl'),[self.old])
    def test_rate_limit_defers_remaining_queries_and_preserves_successes(self):
        queries=self.queries+[{'id':'hf-search-other','query':'GUI safety','area':'Safety','limit':5}]
        result,fetch=self.run_queries([self.response([{'id':'2610.00002'}]),self.response({},429)],queries)
        self.assertEqual(fetch.call_count,2)
        self.assertEqual([r['state'] for r in result['queries']],['success','deferred','deferred'])
        self.assertEqual(result['successful_query_count'],1);self.assertEqual(result['configured_query_count'],3)
        self.assertIn('arxiv:2610.00002',{r['id'] for r in catalog.read_jsonl(self.path/'candidates.jsonl')})
        self.assertTrue(result['queries'][1]['request_attempted'])
        self.assertFalse(result['queries'][2]['request_attempted'])
    def test_candidate_receipt_survives_failed_and_malformed_refreshes(self):
        response=self.response([{'id':'2610.00002'}])
        self.run_queries([response],self.queries[:1])
        candidate=next(r for r in catalog.read_jsonl(self.path/'candidates.jsonl') if r['id']=='arxiv:2610.00002')
        occurrence=candidate['discovered_in'][0]
        self.assertEqual(occurrence['evidence']['sha256'],hashlib.sha256(response[1]).hexdigest())
        self.assertEqual(occurrence['evidence']['retrieved_at'],response[0]['retrieved_at'])
        self.assertIn('q=desktop+GUI+agent',occurrence['evidence']['url'])
        for failed in [self.response({},429),self.response({'error':'wrong shape'})]:
            result,_=self.run_queries([failed],self.queries[:1])
            retained=next(r for r in catalog.read_jsonl(self.path/'candidates.jsonl') if r['id']==candidate['id'])
            self.assertEqual(retained,candidate)
            self.assertEqual(result['successful_query_count'],0)
        self.run_queries([response],self.queries[:1])
        fresh=next(r for r in catalog.read_jsonl(self.path/'candidates.jsonl') if r['id']==candidate['id'])
        self.assertEqual(fresh['discovered_in'],[occurrence])
    def test_matching_legacy_receipt_is_retained_before_failed_refresh(self):
        info={'ok':True,'url':'https://huggingface.co/api/papers/search?q=old&limit=5',
              'sha256':'a'*64,'retrieved_at':'2026-10-01T00:00:00Z'}
        catalog.write_json(self.path/'research-discovery.json',[{'id':'hf-search-desktop','state':'success','evidence':info}])
        self.run_queries([self.response({},429)],self.queries[:1])
        retained=catalog.read_jsonl(self.path/'candidates.jsonl')[0]['discovered_in']
        self.assertEqual(retained[0]['evidence'],{k:info[k] for k in ('url','sha256','retrieved_at')})
        self.assertNotIn('evidence',retained[1])  # Never invent the other source's receipt.
    def test_interrupted_later_request_keeps_completed_query_and_nonfinal_status(self):
        with self.assertRaises(RuntimeError):
            self.run_queries([self.response([{'id':'2610.00002'}]),RuntimeError('interruption')])
        status=catalog.read_json(self.path/discovery.RUN_FILE)
        self.assertEqual(status['status'],'running');self.assertIsNone(status['finished_at'])
        self.assertEqual(status['successful_query_count'],1)
        self.assertIn('arxiv:2610.00002',{r['id'] for r in catalog.read_jsonl(self.path/'candidates.jsonl')})
    def test_registry_rejects_duplicate_ids_unbounded_limits_and_empty_text(self):
        for items in [self.queries+[self.queries[0]],[{**self.queries[0],'limit':121}],[{**self.queries[0],'query':' '}]]:
            catalog.write_json(self.path/discovery.QUERY_FILE,{'schema_version':1,'queries':items})
            with self.assertRaises(ValueError):discovery.load_queries()
        catalog.write_json(self.path/discovery.QUERY_FILE,{'schema_version':1,'queries':self.queries})
        self.assertEqual(discovery.load_queries(limit=80)[0]['limit'],80)
        self.assertNotEqual(discovery.query_id('GUI agent'),discovery.query_id('GUI-agent'))
        self.assertNotEqual(discovery.query_id('图形界面'),discovery.query_id('手机操作'))
    def test_harvest_stops_after_first_rate_limit_and_records_remaining_ids(self):
        rows=[{'id':f'arxiv:2610.{i:05d}','provider':'arxiv'} for i in range(120)]
        catalog.write_jsonl(self.path/'candidates.jsonl',rows)
        catalog.write_jsonl(self.path/'papers.jsonl',[])
        with mock.patch.object(catalog,'DATA',self.path),mock.patch.object(catalog,'fetch',return_value=self.response({},429)) as fetch,contextlib.redirect_stdout(io.StringIO()):
            catalog.harvest(types.SimpleNamespace(refresh=False,limit=120))
        self.assertEqual(fetch.call_count,1)
        self.assertEqual(len(catalog.read_jsonl(self.path/'harvest-failures.jsonl')),120)
        self.assertEqual(catalog.read_jsonl(self.path/'papers.jsonl'),[])


class PublisherIndexTests(unittest.TestCase):
    def source(self):
        return {'id':'publisher','url':'https://huggingface.co/api/models?author=Example&limit=100',
                'homepage':'https://huggingface.co/Example','parser':'huggingface_models'}
    def test_model_ids_are_candidates_without_inferring_relevance(self):
        links=catalog.source_links(self.source(),json.dumps([{'id':'Example/GUI-7B'},{'id':'Example/General-Retriever'}]).encode())
        self.assertEqual([x[2] for x in links],['https://huggingface.co/Example/GUI-7B','https://huggingface.co/Example/General-Retriever'])
        self.assertTrue(all(x[0] is None and 'await review' in x[1] for x in links))
    def test_bad_index_never_clears_a_previous_source_population(self):
        with tempfile.TemporaryDirectory() as directory,mock.patch.object(catalog,'DATA',Path(directory)):
            source=self.source();catalog.write_json(Path(directory)/'sources.json',[source])
            row={'id':'url:retained','url':'https://huggingface.co/Example/Retained','provider':'url','discovered_in':[{'source_id':'publisher','line':None}]}
            catalog.write_jsonl(Path(directory)/'candidates.jsonl',[row])
            info={'ok':True,'sha256':'a'*64,'retrieved_at':'2026-10-17T00:00:00Z'}
            with mock.patch.object(catalog,'fetch',return_value=(info,b'{"error":"unavailable"}')),contextlib.redirect_stdout(io.StringIO()):
                catalog.discover(types.SimpleNamespace(refresh=True))
            self.assertEqual(catalog.read_jsonl(Path(directory)/'candidates.jsonl'),[row])
            self.assertFalse(catalog.read_json(Path(directory)/'discovery-runs.json')[0]['ok'])
    def test_wrong_host_publisher_and_unbounded_response_are_rejected(self):
        for source,body in [({**self.source(),'url':'https://huggingface.co.evil.example/api/models?author=Example&limit=100'},b'[]'),
                            (self.source(),b'[{"id":"Other/Model"}]'),
                            (self.source(),b'[{"id":"Example/Model/extra"}]'),
                            ({**self.source(),'url':'https://huggingface.co/api/models?author=Example&limit=1000'},b'[]')]:
            with self.assertRaises(ValueError):catalog.source_links(source,body)
    def test_source_rate_limit_defers_only_same_host_and_keeps_candidate_receipts(self):
        with tempfile.TemporaryDirectory() as directory,mock.patch.object(catalog,'DATA',Path(directory)):
            path=Path(directory)
            sources=[{'id':'first','url':'https://raw.githubusercontent.com/A/a/HEAD/README.md','homepage':'https://github.com/A/a'},
                     {'id':'second','url':'https://raw.githubusercontent.com/B/b/HEAD/README.md','homepage':'https://github.com/B/b'},
                     self.source()]
            catalog.write_json(path/'sources.json',sources)
            old_info={'ok':True,'url':sources[1]['url'],'sha256':'a'*64,'retrieved_at':'2026-10-01T00:00:00Z'}
            old={'id':'github:old/retained','url':'https://github.com/Old/Retained','provider':'github',
                 'discovered_in':[{'source_id':'second','line':1,'section':'prior release','snapshot_sha256':'a'*64}]}
            catalog.write_jsonl(path/'candidates.jsonl',[old])
            catalog.write_json(path/'discovery-runs.json',[{'id':'second',**old_info},{'id':'removed-source',**old_info}])
            calls=[]
            def fetch(url,refresh):
                calls.append(url)
                if len(calls)==1:
                    return {'url':url,'ok':False,'status':429,'error':'HTTP 429','retrieved_at':'2026-10-17T00:00:00Z'},b''
                body=b'[{"id":"Example/GUI-model"}]'
                return {'url':url,'ok':True,'status':200,'sha256':hashlib.sha256(body).hexdigest(),
                        'retrieved_at':'2026-10-17T00:00:00Z'},body
            with mock.patch.object(catalog,'fetch',side_effect=fetch),contextlib.redirect_stdout(io.StringIO()):
                catalog.discover(types.SimpleNamespace(refresh=True))
            self.assertEqual(calls,[sources[0]['url'],sources[2]['url']])
            runs={r['id']:r for r in catalog.read_json(path/'discovery-runs.json')}
            self.assertNotIn('removed-source',runs)
            self.assertEqual(runs['first']['state'],'deferred')
            self.assertEqual(runs['second']['state'],'deferred');self.assertFalse(runs['second']['request_attempted'])
            self.assertEqual(runs['publisher']['state'],'success')
            candidates={r['id']:r for r in catalog.read_jsonl(path/'candidates.jsonl')}
            retained=candidates[old['id']]['discovered_in'][0]
            self.assertEqual(retained['evidence'],{k:old_info[k] for k in ('url','sha256','retrieved_at')})
            model=next(r for r in candidates.values() if r['url']=='https://huggingface.co/Example/GUI-model')
            self.assertNotIn('review_status',model)
            self.assertEqual(model['discovered_in'][0]['evidence']['sha256'],runs['publisher']['sha256'])


if __name__=='__main__':unittest.main()
