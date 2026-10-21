import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import scan
from catalog import write_jsonl


class ScanSafetyTests(unittest.TestCase):
    def row(self,name='Primary title'):
        return {'id':'arxiv:2610.00001','url':'https://arxiv.org/abs/2610.00001','name':name,'authors':['Researcher'],
            'published_at':'2026-10-01','updated_at':'2026-10-02','evidence':[],'review_status':'metadata_verified'}
    def test_new_metadata_does_not_gain_editorial_approval(self):
        records={};proposals={};row=self.row()
        self.assertTrue(scan.consider_paper(row,records,proposals,'2026-10-16T00:00:00Z'))
        self.assertEqual(records[row['id']]['review_status'],'metadata_verified');self.assertEqual(proposals,{})
    def test_changed_existing_metadata_is_queued_without_rewriting_approved_snapshot(self):
        old=self.row();old['review_status']='curated';records={old['id']:copy.deepcopy(old)};proposals={}
        observed=self.row('Updated primary title')
        self.assertFalse(scan.consider_paper(observed,records,proposals,'2026-10-16T00:00:00Z'))
        self.assertEqual(records[old['id']],old)
        self.assertEqual(proposals[old['id']]['review_status'],'metadata_change_pending')
        self.assertEqual(proposals[old['id']]['changes']['name']['observed'],'Updated primary title')
    def test_all_failed_phases_cannot_borrow_old_success_receipts(self):
        phases=[{'name':x,'ok':False} for x in ['discovery','huggingface','recent_arxiv']]
        status,problems=scan.summarize_phases(phases,[{'id':'old','ok':True}],[{'id':'old','evidence':{'ok':True}}],[])
        self.assertEqual(status,'failed');self.assertTrue(problems)
    def test_partial_source_failure_is_reported_separately(self):
        phases=[{'name':'discovery','ok':True},{'name':'validate','ok':True}]
        status,problems=scan.summarize_phases(phases,[{'id':'good','ok':True},{'id':'bad','ok':False}],[],[])
        self.assertEqual(status,'partial');self.assertIn('bad',' '.join(problems))
    def test_validation_failure_prevents_successful_scan_status(self):
        phases=[{'name':'discovery','ok':True},{'name':'validate','ok':False,'error':'invalid record'}]
        status,_=scan.summarize_phases(phases,[{'id':'good','ok':True}],[],[])
        self.assertEqual(status,'failed')
    def test_nullable_error_messages_preserve_failure_classification_and_warnings(self):
        for error in (None,''):
            with self.subTest(error=error):
                phases=[{'name':'discovery','ok':True},
                    {'name':'recent_arxiv','ok':False,'error':error,'warnings':['HTTP 429']},
                    {'name':'build','ok':True},{'name':'validate','ok':True}]
                status,problems=scan.summarize_phases(phases,[{'id':'current','ok':True}],[],[])
                self.assertEqual(status,'partial')
                self.assertIn('recent_arxiv: failed',problems)
                self.assertIn('HTTP 429',problems)
                phases.append({'name':'github_candidates','ok':False,'error':error,
                    'durable_validation':{'ok':False,'error':error}})
                status,problems=scan.summarize_phases(phases,[{'id':'current','ok':True}],[],[])
                self.assertEqual(status,'failed')
                self.assertIn('Candidate snapshot integrity: invalid durable triplet',problems)
    def test_http_success_with_only_parse_failures_is_not_a_usable_scan(self):
        phases=[{'name':'discovery','ok':False},{'name':'huggingface','ok':True},
                {'name':'recent_arxiv','ok':False},{'name':'build','ok':True},{'name':'validate','ok':True}]
        runs=[{'id':'bad-shape','state':'failed','evidence':{'ok':True,'status':200},'parse_error':'not an array'}]
        status,problems=scan.summarize_phases(phases,[],runs,[])
        self.assertEqual(status,'failed');self.assertIn('bad-shape',' '.join(problems))
        runs.append({'id':'empty-valid','state':'success','evidence':{'ok':True,'status':200},'identifiers':[]})
        self.assertEqual(scan.summarize_phases(phases,[],runs,[])[0],'partial')
    def test_arxiv_error_feed_cannot_be_counted_as_successful_empty_search(self):
        body=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#bad_query</id><title>Error</title></entry></feed>'
        info={'ok':True,'url':'https://export.arxiv.org/api/query','retrieved_at':'2026-10-16T00:00:00Z','sha256':'a'*64}
        with tempfile.TemporaryDirectory() as directory,mock.patch.object(scan,'DATA',Path(directory)),mock.patch.object(scan,'fetch',return_value=(info,body)):
            existing=self.row();write_jsonl(Path(directory)/'papers.jsonl',[existing])
            result=scan.recent_papers({'recent_lookback_days':14,'recent_max_results':100})
            self.assertFalse(result['ok'])
            rows=[json.loads(line) for line in (Path(directory)/'papers.jsonl').read_text().splitlines()]
            self.assertEqual(rows,[existing])

    def test_recent_rate_limit_defers_harvest_and_stale_search_receipts_do_not_count(self):
        with tempfile.TemporaryDirectory() as directory,mock.patch.object(scan,'DATA',Path(directory)):
            path=Path(directory)
            scan.write_json(path/'scan-config.json',{'recent_lookback_days':14,'recent_max_results':500,'harvest_limit':500,
                'history_limit':5,'timezone':'UTC','scan_times_local':['08:17','20:17'],'policy':'Fixture'})
            scan.write_json(path/'discovery-runs.json',[{'id':'current','ok':True}])
            scan.write_json(path/'paper-discovery-status.json',{'schema_version':1,'started_at':'2026-10-16T00:00:00Z',
                'finished_at':'2026-10-16T00:01:00Z','configured_query_count':1,
                'queries':[{'id':'old','state':'success','evidence':{'ok':True}}]})
            invoked=[]
            def stage(name,command,timeout=600):
                invoked.append(name)
                return {'name':name,'ok':True,'started_at':'2026-10-17T00:00:00Z'}
            with mock.patch.object(scan,'stage',side_effect=stage),mock.patch.object(scan,'recent_phase',return_value={
                    'name':'recent_arxiv','ok':False,'error':None,'rate_limited':True,'warnings':['HTTP 429']}),mock.patch.dict(scan.os.environ,{'GITHUB_STEP_SUMMARY':''}):
                self.assertEqual(scan.run_scan(),0)
            result=scan.read_json(path/'scan-status.json')
            self.assertNotIn('harvest',invoked)
            self.assertTrue(next(p for p in result['phases'] if p['name']=='harvest')['deferred'])
            self.assertFalse(next(p for p in result['phases'] if p['name']=='huggingface')['ok'])
            self.assertEqual(result['paper_searches']['successful'],0)
            self.assertEqual(result['status'],'partial')
    def test_publisher_hub_rate_limit_defers_paper_search_without_stopping_arxiv(self):
        with tempfile.TemporaryDirectory() as directory,mock.patch.object(scan,'DATA',Path(directory)):
            path=Path(directory)
            scan.write_json(path/'scan-config.json',{'recent_lookback_days':14,'recent_max_results':500,'harvest_limit':500,
                'history_limit':5,'timezone':'UTC','scan_times_local':['08:17','20:17'],'policy':'Fixture'})
            invoked=[]
            def stage(name,command,timeout=600):
                invoked.append(name)
                if name=='discovery':
                    scan.write_json(path/'discovery-runs.json',[{'id':'hub','ok':False,'status':429,
                        'provider_host':'huggingface.co','run_started_at':'2026-10-17T00:00:01Z'}])
                return {'name':name,'ok':True,'started_at':'2026-10-17T00:00:00Z'}
            with mock.patch.object(scan,'stage',side_effect=stage),mock.patch.object(scan,'recent_phase',return_value={
                    'name':'recent_arxiv','ok':True,'complete':True,'warnings':[]}) as recent,mock.patch.dict(scan.os.environ,{'GITHUB_STEP_SUMMARY':''}):
                self.assertEqual(scan.run_scan(),0)
            recent.assert_called_once()
            self.assertEqual(invoked,['discovery','harvest','build','validate'])
            phase=next(p for p in scan.read_json(path/'scan-status.json')['phases'] if p['name']=='huggingface')
            self.assertTrue(phase['deferred']);self.assertFalse(phase['request_attempted'])
    def test_huggingface_query_rate_limit_does_not_stop_arxiv_or_harvest(self):
        with tempfile.TemporaryDirectory() as directory,mock.patch.object(scan,'DATA',Path(directory)):
            path=Path(directory)
            scan.write_json(path/'scan-config.json',{'recent_lookback_days':14,'recent_max_results':500,'harvest_limit':500,
                'history_limit':5,'timezone':'UTC','scan_times_local':['08:17','20:17'],'policy':'Fixture'})
            invoked=[]
            def stage(name,command,timeout=600):
                invoked.append(name)
                if name=='huggingface':
                    scan.write_json(path/'paper-discovery-status.json',{'schema_version':1,
                        'started_at':'2026-10-17T00:00:00Z','finished_at':'2026-10-17T00:00:01Z','configured_query_count':1,
                        'queries':[{'id':'limited','state':'failed','evidence':{'ok':False,'status':429}}]})
                return {'name':name,'ok':True,'started_at':'2026-10-17T00:00:00Z'}
            with mock.patch.object(scan,'stage',side_effect=stage),mock.patch.object(scan,'recent_phase',return_value={
                    'name':'recent_arxiv','ok':True,'complete':True,'warnings':[]}) as recent,mock.patch.dict(scan.os.environ,{'GITHUB_STEP_SUMMARY':''}):
                self.assertEqual(scan.run_scan(),0)
            recent.assert_called_once()
            self.assertEqual(invoked,['discovery','huggingface','harvest','build','validate'])
            self.assertEqual(scan.read_json(path/'scan-status.json')['status'],'partial')


if __name__=='__main__':unittest.main()
