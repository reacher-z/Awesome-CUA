"""Shared transport reservations and hard phase deadlines; no test uses the network."""
import io
import json
from email.message import Message
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import urllib.error
import urllib.request
from urllib.response import addinfourl

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import catalog
import scan
import discover_papers
from network_budget import (RoundBudget, BudgetDeferred, BudgetHandler,
                            ENV_FILE, ENV_ID, ENV_PHASE, budget_from_environment)


class Clock:
    def __init__(self):self.seconds=0.;self.extra_sleep=0.
    def monotonic(self):return self.seconds
    def now(self):return datetime(2026,10,18,tzinfo=timezone.utc)+timedelta(seconds=self.seconds)
    def sleep(self,seconds):self.seconds+=seconds+self.extra_sleep


class FakeHTTP(urllib.request.BaseHandler):
    """Exercise urllib's real opener/redirect machinery through a fake HTTP handler."""
    handler_order=100
    def __init__(self,responses):self.responses=iter(responses);self.requests=[]
    def http_open(self,request):
        self.requests.append(request)
        value=next(self.responses)
        if isinstance(value,Exception):raise value
        code,headers,body=value
        message=Message()
        for name,value in headers.items():message[name]=value
        response=addinfourl(io.BytesIO(body),message,request.full_url,code)
        response.msg='fixture'
        return response


class BudgetCase(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name).resolve();self.clock=Clock()
    def budget(self,**kwargs):
        return RoundBudget.create(self.directory,clock=self.clock.monotonic,sleep=self.clock.sleep,now=self.clock.now,**kwargs)


class BudgetTests(BudgetCase):
    def test_reservation_is_durable_before_transport_and_contains_no_credentials(self):
        budget=self.budget(max_requests=2,max_seconds=30)
        url='https://example.org/path?token=do-not-store'
        number=budget.reserve(url,phase='discovery')
        # A new process/object observes an unfinished reservation; no refund after interruption.
        resumed=RoundBudget(budget.path,budget.run_id,clock=self.clock.monotonic,now=self.clock.now)
        self.assertEqual(resumed.summary()['requests_reserved'],1)
        self.assertEqual(resumed.summary()['unknown_attempts'],1)
        resumed.observe_response(url,200,{'Authorization':'SECRET','Set-Cookie':'SECRET'},attempt=number)
        self.assertNotIn('SECRET',budget.path.read_text(encoding='utf-8'))
        self.assertNotIn('do-not-store',budget.path.read_text(encoding='utf-8'))
        self.assertNotIn('https://',budget.path.read_text(encoding='utf-8'))
        self.assertEqual(resumed.summary()['responses_received'],1)

    def test_sequential_real_child_processes_share_one_cap(self):
        budget=RoundBudget.create(self.directory,max_requests=2,max_seconds=30)
        code="from network_budget import budget_from_environment; b=budget_from_environment(); b.reserve('https://example.org/fixture'); print(b.summary()['requests_reserved'])"
        with budget.activate():
            env={**__import__('os').environ,'PYTHONPATH':str(ROOT/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'}
            for expected in ('1','2'):
                result=subprocess.run([sys.executable,'-S','-c',code],env=env,capture_output=True,text=True,check=True)
                self.assertEqual(result.stdout.strip(),expected)
            result=subprocess.run([sys.executable,'-S','-c',code],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('request_budget',result.stderr)
        self.assertEqual(budget.summary()['requests_reserved'],2)

    def test_deadline_is_rechecked_after_spacing_sleep(self):
        budget=self.budget(max_requests=2,max_seconds=8)
        budget.reserve('https://api.github.com/repos/public/one')
        self.clock.extra_sleep=10
        with self.assertRaisesRegex(BudgetDeferred,'wall_budget'):
            budget.reserve('https://api.github.com/repos/public/two')
        self.assertEqual(self.clock.seconds,16.5)
        self.assertEqual(budget.summary()['requests_reserved'],1)

    def test_cooldown_is_shared_and_other_provider_can_continue(self):
        budget=self.budget(max_requests=4,max_seconds=600)
        number=budget.reserve('https://example.org/a')
        budget.observe_response('https://example.org/a',429,{'Retry-After':'120','Set-Cookie':'SECRET'},attempt=number)
        other=RoundBudget(budget.path,budget.run_id,clock=self.clock.monotonic,sleep=self.clock.sleep,now=self.clock.now)
        with self.assertRaisesRegex(BudgetDeferred,'provider_cooldown'):other.reserve('https://example.org/b')
        other.reserve('https://another.example/a')
        self.assertEqual(other.summary()['requests_reserved'],2)
        self.assertNotIn('SECRET',budget.path.read_text(encoding='utf-8'))
        future=self.budget(max_requests=2,max_seconds=30,cooldowns=other.summary()['provider_cooldowns'])
        with self.assertRaisesRegex(BudgetDeferred,'provider_cooldown'):future.reserve('https://example.org/c')
        self.clock.seconds=121
        with self.assertRaisesRegex(BudgetDeferred,'provider_cooldown'):other.reserve('https://example.org/d')
        next_round=self.budget(max_requests=2,max_seconds=30,cooldowns=other.summary()['provider_cooldowns'])
        next_round.reserve('https://example.org/e')
        self.assertEqual(next_round.summary()['requests_reserved'],1)

    def test_round_mismatch_and_invalid_counts_fail_closed(self):
        budget=self.budget(max_requests=1,max_seconds=10)
        with self.assertRaises(ValueError):RoundBudget(budget.path,'0'*32)
        value=json.loads(budget.path.read_bytes());value['max_requests']=True
        budget.path.write_text(json.dumps(value),encoding='utf-8')
        with self.assertRaises(ValueError):budget.summary()

    def test_a_round_cannot_be_reused_with_a_reset_monotonic_clock(self):
        self.clock.seconds=10
        budget=self.budget(max_requests=1,max_seconds=30)
        self.clock.seconds=0
        with self.assertRaisesRegex(ValueError,'different monotonic clock'):
            budget.remaining_seconds()

    def test_outer_recent_subprocess_uses_remaining_round_time(self):
        budget=self.budget(max_requests=2,max_seconds=60)
        self.clock.seconds=53
        with mock.patch.object(scan,'budget_from_environment',return_value=budget), \
                mock.patch.object(scan.subprocess,'run',side_effect=subprocess.TimeoutExpired(['fixture'],7)) as run:
            result=scan.recent_phase()
        self.assertFalse(result['ok']);self.assertEqual(run.call_args.kwargs['timeout'],7)
        self.assertIn('--recent-only',run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs['env'][ENV_PHASE],'recent_arxiv')

    def test_recent_phase_requires_a_new_receipt_from_the_current_round(self):
        budget=self.budget(max_requests=2,max_seconds=60)
        output=scan.recent_result_path(budget)
        output.write_text(json.dumps({'round_id':budget.run_id,'phase':{'name':'recent_arxiv','ok':True}}),encoding='utf-8')
        with mock.patch.object(scan,'budget_from_environment',return_value=budget), \
                mock.patch.object(scan,'stage',return_value={'name':'recent_arxiv','ok':True}):
            self.assertFalse(scan.recent_phase()['ok'])
        self.assertFalse(output.exists())
        def child(name,command):
            output.write_text(json.dumps({'round_id':budget.run_id,'phase':{'name':name,'ok':False,'rate_limited':True}}),encoding='utf-8')
            return {'name':name,'ok':True}
        with mock.patch.object(scan,'budget_from_environment',return_value=budget),mock.patch.object(scan,'stage',side_effect=child):
            result=scan.recent_phase()
        self.assertFalse(result['ok']);self.assertTrue(result['rate_limited'])

    def test_outer_deadline_really_terminates_a_blocked_local_child(self):
        budget=RoundBudget.create(self.directory,max_requests=2,max_seconds=.2)
        started=time.monotonic()
        with budget.activate():
            result=scan.stage('recent_arxiv',['-c','import time; time.sleep(3)'])
        self.assertFalse(result['ok'])
        self.assertIn('Stage exceeded',result['error'])
        self.assertLess(time.monotonic()-started,2)

    def test_expired_round_defers_network_but_runs_offline_validation(self):
        budget=self.budget(max_requests=2,max_seconds=1);self.clock.seconds=2
        with mock.patch.object(scan,'budget_from_environment',return_value=budget), \
                mock.patch.object(scan.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'')) as run:
            self.assertTrue(scan.stage('harvest',['scripts/catalog.py','harvest'])['deferred'])
            self.assertFalse(run.called)
            self.assertTrue(scan.stage('validate',['scripts/catalog.py','validate'])['ok'])
        self.assertEqual(run.call_args.kwargs['timeout'],180)

    def test_discovery_reports_do_not_claim_a_deferred_transport_was_sent(self):
        data=self.directory/'data';data.mkdir()
        (data/'sources.json').write_text(json.dumps([{'id':'fixture','url':'https://example.org/list'}]),encoding='utf-8')
        info={'url':'https://example.org/list','retrieved_at':'2026-10-18T00:00:00Z','ok':False,
              'deferred':True,'deferred_reason':'request_budget','request_attempted':False,'error':'Budget deferred'}
        with mock.patch.object(catalog,'DATA',data),mock.patch.object(catalog,'fetch',return_value=(info,b'')),redirect_stdout(io.StringIO()):
            catalog.discover(type('Args',(),{'refresh':True})())
        result=json.loads((data/'discovery-runs.json').read_bytes())[0]
        self.assertEqual(result['state'],'deferred');self.assertFalse(result['request_attempted']);self.assertFalse(result['ok'])
        with mock.patch.object(discover_papers,'DATA',data),mock.patch.object(discover_papers,'fetch',return_value=(info,b'')),redirect_stdout(io.StringIO()):
            report=discover_papers.discover([{'id':'hf-fixture','query':'gui','area':'Fixture','limit':1}],refresh=True)
        self.assertEqual(report['queries'][0]['state'],'deferred')
        self.assertFalse(report['queries'][0]['request_attempted']);self.assertEqual(report['successful_query_count'],0)


class BudgetFetchTests(BudgetCase):
    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch.object(catalog,'CACHE',self.directory/'http'))
        self.enterContext(mock.patch('socket.create_connection',side_effect=AssertionError('No network permitted')))

    def fetch(self,budget,responses,url='http://example.org/start',**kwargs):
        transport=FakeHTTP(responses)
        real_build=urllib.request.build_opener
        with mock.patch.object(catalog,'budget_from_environment',return_value=budget), \
                mock.patch('urllib.request.build_opener',side_effect=lambda *handlers:real_build(urllib.request.ProxyHandler({}),transport,*handlers)), \
                mock.patch.object(catalog.time,'sleep',side_effect=self.clock.sleep):
            result=catalog.fetch(url,**kwargs)
        return result,transport

    def test_followed_redirects_are_separate_actual_attempts(self):
        budget=self.budget(max_requests=2,max_seconds=30)
        (info,body),transport=self.fetch(budget,[(302,{'Location':'http://other.example/final'},b''),(200,{},b'payload')])
        self.assertTrue(info['ok']);self.assertEqual(body,b'payload');self.assertEqual(len(transport.requests),2)
        self.assertEqual(info['request_attempts'],2)
        self.assertEqual(budget.summary()['requests_reserved'],2)
        self.assertEqual(budget.summary()['by_provider'],{'example.org':1,'other.example':1})
        self.assertEqual([x['status'] for x in budget.read()['attempts']],[302,200])

    def test_redirect_cannot_escape_request_cap_or_replace_good_cache(self):
        url='http://example.org/start'
        self.fetch(self.budget(max_requests=2,max_seconds=30),[(200,{},b'old good')],url=url)
        budget=self.budget(max_requests=1,max_seconds=30)
        (info,body),transport=self.fetch(budget,[(302,{'Location':'http://other.example/final'},b'')],refresh=True)
        self.assertFalse(info['ok']);self.assertEqual(body,b'');self.assertEqual(info['deferred_reason'],'request_budget')
        self.assertEqual(len(transport.requests),1)
        with mock.patch.object(catalog,'budget_from_environment',side_effect=AssertionError('Cache hit must not need budget')):
            self.assertEqual(catalog.fetch(url)[1],b'old good')

    def test_non_http_redirect_cannot_bypass_the_counted_transport(self):
        budget=self.budget(max_requests=2,max_seconds=30)
        (info,_),transport=self.fetch(budget,[(302,{'Location':'ftp://example.org/file'},b'')])
        self.assertFalse(info['ok']);self.assertEqual(len(transport.requests),1)
        self.assertEqual(budget.summary()['requests_reserved'],1)

    def test_retry_attempts_use_shared_counter_and_cache_hits_cost_zero(self):
        budget=self.budget(max_requests=2,max_seconds=30)
        (info,body),transport=self.fetch(budget,[(503,{'Retry-After':'1'},b''),(200,{},b'ok')],refresh=True)
        self.assertTrue(info['ok']);self.assertEqual(body,b'ok');self.assertEqual(len(transport.requests),2)
        self.assertEqual(budget.summary()['requests_reserved'],2)
        (info,body),transport=self.fetch(budget,[])
        self.assertTrue(info['ok']);self.assertEqual(body,b'ok');self.assertEqual(len(transport.requests),0)
        self.assertFalse(info['request_attempted']);self.assertEqual(info['request_attempts'],0)
        self.assertTrue(info['cache_used'])

    def test_cache_hit_reports_current_zero_transport_without_rewriting_primary_receipt(self):
        url='http://example.org/start'
        (first,_),_=self.fetch(self.budget(max_requests=2,max_seconds=30),
            [(200,{},b'https://github.com/public/gui\n')],url=url)
        saved={p.name:p.read_bytes() for p in catalog.CACHE.iterdir()}
        current=self.budget(max_requests=1,max_seconds=30)
        data=self.directory/'data';data.mkdir()
        (data/'sources.json').write_text(json.dumps([{'id':'fixture','url':url,'homepage':'https://example.org/'}]),encoding='utf-8')
        with mock.patch.object(catalog,'budget_from_environment',side_effect=AssertionError('Cache must not load a budget')), \
                mock.patch.object(catalog,'DATA',data),redirect_stdout(io.StringIO()):
            cached,body=catalog.fetch(url)
            catalog.discover(type('Args',(),{'refresh':False,'accept_shrink':[]})())
        self.assertEqual(body,b'https://github.com/public/gui\n')
        receipt=json.loads((data/'discovery-runs.json').read_bytes())[0]
        for info in (cached,receipt):
            self.assertTrue(info['ok']);self.assertTrue(info['cache_used'])
            self.assertFalse(info['request_attempted']);self.assertEqual(info['request_attempts'],0)
            for field in ('url','final_url','retrieved_at','sha256','bytes','status'):
                self.assertEqual(info[field],first[field])
        self.assertEqual(current.summary()['requests_reserved'],0)
        self.assertEqual({p.name:p.read_bytes() for p in catalog.CACHE.iterdir()},saved)

    def test_redirected_rate_limit_preserves_target_receipt_without_retrying_origin(self):
        url='http://example.org/start';target='http://limited.example/final'
        self.fetch(self.budget(max_requests=1,max_seconds=30),[(200,{},b'old verified body')],url=url)
        saved={p.name:p.read_bytes() for p in catalog.CACHE.iterdir()}
        budget=self.budget(max_requests=5,max_seconds=300)
        (info,body),transport=self.fetch(budget,[(302,{'Location':target},b''),
            (429,{'Retry-After':'1'},b'')],url=url,refresh=True)
        self.assertFalse(info['ok']);self.assertEqual(body,b'')
        self.assertEqual(info['status'],429);self.assertEqual(info['final_url'],target)
        self.assertEqual(info['deferred_reason'],'provider_cooldown')
        self.assertEqual(info['deferred_provider'],'limited.example')
        self.assertEqual(info['request_attempts'],2);self.assertTrue(info['request_attempted'])
        self.assertEqual([r.full_url for r in transport.requests],[url,target])
        self.assertEqual([a['status'] for a in budget.read()['attempts']],[302,429])
        self.assertEqual(budget.summary()['blocked_providers'],['limited.example'])
        self.assertTrue(all((catalog.CACHE/name).read_bytes()==body for name,body in saved.items()))

    def test_rate_limit_does_not_retry_and_does_not_become_a_success(self):
        budget=self.budget(max_requests=5,max_seconds=300)
        (info,body),transport=self.fetch(budget,[(429,{'Retry-After':'120'},b'')],refresh=True)
        self.assertFalse(info['ok']);self.assertEqual(info['status'],429);self.assertEqual(body,b'')
        self.assertEqual(len(transport.requests),1)
        (info,body),transport=self.fetch(budget,[],refresh=True)
        self.assertFalse(info['ok']);self.assertTrue(info['deferred']);self.assertFalse(info['request_attempted'])
        self.assertEqual(len(transport.requests),0)

    def test_retry_wait_cannot_exceed_the_round_deadline(self):
        budget=self.budget(max_requests=3,max_seconds=2)
        (info,_),transport=self.fetch(budget,[(503,{},b'')],refresh=True)
        self.assertFalse(info['ok']);self.assertEqual(info['deferred_reason'],'wall_budget')
        self.assertEqual(len(transport.requests),1);self.assertEqual(self.clock.seconds,0)


if __name__=='__main__':unittest.main()
