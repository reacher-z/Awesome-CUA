"""Scheduled candidates resume from public state without historical raw cache or network."""
import copy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import candidate_state
import catalog
import build as builder
import export_candidates
from export_rag import encode_documents
import network_budget
from network_budget import RoundBudget
import scan
import scan_candidate_stage as stage
import scan_github_candidates as scanner
from test_data_release_package import make_release_fixture
from test_github_candidate_scan import Timer, page, repo, response


CONFIG = {'github_candidates_enabled': True, 'github_candidate_max_requests': 1,
          'github_candidate_max_seconds': 30, 'github_candidate_existing_budget': 1,
          'github_candidate_topics': ['computer-use']}


class CandidateStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.root = self.directory / 'initial'; self.root.mkdir()
        _, self.active_rows = make_release_fixture(self.root)
        for name in scanner.INPUTS:
            path = self.root / 'data' / name
            if not path.exists(): path.write_text('' if name.endswith('.jsonl') else '[]\n', encoding='utf-8')
        self.timer = Timer()
        self.enterContext(mock.patch('socket.create_connection', side_effect=AssertionError('Network forbidden')))
        values = [repo(i) for i in range(1, 100)] + [repo(100, 'example/data')]
        old, _ = scanner.run_scan(self.root, self.root / '.cache/bootstrap-ledger',
            max_requests=1, max_seconds=30, existing_budget=0, topics=['computer-use'],
            created_after='2024-01-01', created_before='2026-10-18',
            fetcher=lambda url, timeout: response(page(values, total=101)),
            clock=self.timer.clock, sleep=self.timer.sleep, now=self.timer.now)
        raw = self.root / '.cache/bootstrap-ledger/raw'
        ledger = export_candidates.encoded(old)
        catalog = (self.root / 'data/catalog.jsonl').read_bytes()
        body, manifest = export_candidates.build_candidate_export(ledger, raw, catalog)
        export_candidates.write_pair(self.root / 'data', body, manifest)
        bootstrap = self.root / '.cache/bootstrap-output'
        candidate_state.bootstrap_from_ledger(ledger, raw, self.root / 'data', bootstrap, catalog_bytes=catalog)
        prior = {name: hashlib.sha256((self.root/'data'/name).read_bytes()).hexdigest()
                 if (self.root/'data'/name).exists() else None for name in candidate_state.FILES}
        candidate_state.publish_snapshot(bootstrap, self.root / 'data', expected_prior_hashes=prior)
        self.timer.seconds += 20
        self.fresh_checkout('fresh')

    def fresh_checkout(self, name):
        fresh = self.directory / name; fresh.mkdir()
        shutil.copytree(self.root / 'data', fresh / 'data')
        self.root = fresh
        self.assertFalse((fresh / '.cache').exists())

    def budget(self, **kwargs):
        return RoundBudget.create(self.root / '.cache/rounds', max_requests=kwargs.pop('max_requests', 8),
            max_seconds=kwargs.pop('max_seconds', 90), clock=self.timer.clock, sleep=self.timer.sleep,
            now=lambda: datetime.fromisoformat(self.timer.now()), **kwargs)

    def hashes(self):
        return {name: hashlib.sha256((self.root/'data'/name).read_bytes()).hexdigest() for name in candidate_state.FILES}

    def child(self, budget, responses, *, config=None):
        outcomes = iter(responses); calls = []
        original = scanner.run_scan
        def open_url(request, timeout):
            calls.append(request.full_url)
            value = next(outcomes)
            if isinstance(value, BaseException): raise value
            status, body, headers = value
            result = mock.MagicMock(status=status, headers=headers)
            result.__enter__.return_value = result
            result.read.return_value = body
            return result
        def run(*args, **kwargs):
            return original(*args, **kwargs, clock=self.timer.clock, sleep=self.timer.sleep, now=self.timer.now)
        with mock.patch.object(scanner, 'run_scan', side_effect=run), \
                mock.patch.object(scanner.urllib.request, 'build_opener', return_value=mock.Mock(open=open_url)), \
                mock.patch.object(network_budget, 'budget_from_environment', return_value=budget), \
                mock.patch.object(scanner, 'budget_from_environment', return_value=budget, create=True):
            result = stage.run_stage(self.root, budget, config=config or CONFIG, clock=self.timer.clock)
        return result, calls

    def phase(self, budget, responses, *, config=None, receipt_mutation=None):
        calls = []
        def child(name, command, timeout=None):
            self.assertEqual(name, stage.PHASE)
            receipt, requested = self.child(budget, responses, config=config)
            if receipt_mutation is not None:
                receipt_mutation(receipt)
                stage.result_path(budget).write_text(json.dumps(receipt),encoding='utf-8')
            calls.extend(requested)
            return {'name': name, 'ok': True, 'started_at': receipt['phase']['started_at'], 'exit_code': 0}
        with mock.patch.object(scan, 'DATA', self.root / 'data'), \
                mock.patch.object(scan, 'budget_from_environment', return_value=budget), \
                mock.patch.object(scan, 'stage', side_effect=child):
            phase = scan.candidate_phase(config or CONFIG)
        return phase, calls

    def publish(self, phase, budget):
        with mock.patch.object(scan, 'DATA', self.root / 'data'):
            scan.publish_candidate_phase(phase, budget)

    def test_fresh_checkout_resumes_next_page_and_preserves_active_catalog_and_rag(self):
        before = self.hashes(); active = (self.root/'data/catalog.jsonl').read_bytes()
        rag = encode_documents(self.active_rows, include_metadata=True)
        budget = self.budget()
        phase, calls = self.phase(budget, [response(page([repo(101)], total=101))])
        self.assertTrue(phase['ok']); self.assertTrue(phase['ready_to_publish'])
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(calls[0]).query)['page'], ['2'])
        self.assertEqual(len(calls), 1); self.assertEqual(phase['requests_attempted'], 1)
        self.assertEqual(self.hashes(), before, 'A successful child must still leave data untouched')
        runtime = stage.runtime_path(budget)
        self.assertEqual(len(list((runtime/'raw').glob('*.body'))), 1, 'Only the new page body is needed')
        self.publish(phase, budget)
        new = candidate_state.load_snapshot(self.root/'data')
        self.assertEqual(len(new.records), 101); self.assertTrue(phase['published'])
        self.assertEqual((self.root/'data/catalog.jsonl').read_bytes(), active)
        self.assertEqual(encode_documents(self.active_rows, include_metadata=True), rag)
        self.assertTrue(all(r['review_status']=='candidate' and r['scope']=='relevance_pending' for r in new.records.values()))
        self.fresh_checkout('fresh-again')
        next_budget = self.budget()
        phase, calls = self.phase(next_budget, [])
        self.assertEqual(calls, []); self.assertEqual(phase['requests_attempted'], 0)
        self.assertTrue(phase['complete']); self.assertEqual(phase['warnings'], [])
        self.publish(phase, next_budget)
        self.assertEqual(len(candidate_state.load_snapshot(self.root/'data').records), 101)

    def test_post_build_comparison_context_is_rebound_without_changing_child_observations(self):
        budget = self.budget()
        phase, _ = self.phase(budget, [response(page([repo(101)], total=101))])
        staged = candidate_state.load_snapshot(stage.runtime_path(budget)/'public')
        extra = copy.deepcopy(self.active_rows[1]); extra['id']='arxiv:2601.00003'
        final_catalog = (self.root/'data/catalog.jsonl').read_bytes() + (json.dumps(extra)+'\n').encode()
        (self.root/'data/catalog.jsonl').write_bytes(final_catalog)
        self.publish(phase, budget)
        published = candidate_state.load_snapshot(self.root/'data', catalog_bytes=final_catalog)
        self.assertEqual(published.payloads[export_candidates.RECORD_FILE], staged.payloads[export_candidates.RECORD_FILE])
        self.assertEqual(published.manifest['input_fingerprints'], staged.manifest['input_fingerprints'])
        self.assertEqual(phase['staged_files'], staged.fingerprints)
        self.assertEqual(phase['files'], published.fingerprints)
        self.assertNotEqual(phase['files'][export_candidates.MANIFEST_FILE], phase['staged_files'][export_candidates.MANIFEST_FILE])

    def test_shared_budget_exhaustion_starts_no_child_and_is_not_a_source_alarm(self):
        before=self.hashes(); budget=self.budget(max_requests=1)
        number=budget.reserve('https://earlier.example/fixture'); budget.observe_response('https://earlier.example/fixture',200,attempt=number)
        with mock.patch.object(scan,'DATA',self.root/'data'), mock.patch.object(scan,'budget_from_environment',return_value=budget), \
                mock.patch.object(scan,'stage') as child:
            phase=scan.candidate_phase(CONFIG)
        child.assert_not_called();self.assertTrue(phase['ok']);self.assertEqual(phase['state'],'deferred_budget')
        self.assertFalse(phase['request_attempted']);self.assertEqual(phase['warnings'],[])
        self.assertEqual(self.hashes(),before)

    def test_rate_limit_keeps_previous_rows_and_explicit_current_round_gap(self):
        body=(self.root/'data'/export_candidates.RECORD_FILE).read_bytes(); budget=self.budget()
        phase,calls=self.phase(budget,[response(b'{"message":"API rate limit exceeded"}',429,{'Retry-After':'60'})],
            receipt_mutation=lambda receipt:receipt['phase'].update(warnings=[],complete=True,state='complete'))
        self.assertEqual(len(calls),1);self.assertEqual(phase['scan_status'],'rate_limited')
        self.assertTrue(phase['warnings']);self.assertFalse(phase['complete'])
        self.publish(phase,budget)
        self.assertEqual((self.root/'data'/export_candidates.RECORD_FILE).read_bytes(),body)
        current=candidate_state.load_snapshot(self.root/'data')
        self.assertEqual(current.state['receipts'][-1]['status'],429)
        self.assertEqual(current.state['runs'][-1]['requests_attempted'],1)

    def test_killed_child_and_missing_current_receipt_preserve_all_durable_files(self):
        before=self.hashes();budget=self.budget()
        with self.assertRaises(KeyboardInterrupt):self.child(budget,[KeyboardInterrupt()])
        self.assertEqual(self.hashes(),before);self.assertFalse(stage.result_path(budget).exists())
        other=self.budget()
        stage.result_path(other).write_text(json.dumps({'round_id':other.run_id,'phase':{'ok':True}}),encoding='utf-8')
        with mock.patch.object(scan,'DATA',self.root/'data'), mock.patch.object(scan,'budget_from_environment',return_value=other), \
                mock.patch.object(scan,'stage',return_value={'name':stage.PHASE,'ok':True}):
            phase=scan.candidate_phase(CONFIG)
        self.assertFalse(phase['ok']);self.assertFalse(stage.result_path(other).exists())
        self.assertEqual(self.hashes(),before)

    def test_missing_checkpoint_never_fetches_or_implicitly_bootstraps(self):
        (self.root/'data'/candidate_state.PROGRESS_FILE).unlink();budget=self.budget()
        with mock.patch.object(scanner,'run_scan') as fetch, self.assertRaises(candidate_state.CandidateStateError):
            stage.run_stage(self.root,budget,config=CONFIG)
        fetch.assert_not_called();self.assertFalse(stage.result_path(budget).exists())

    def test_changed_staged_output_is_rejected_before_installation(self):
        before=self.hashes();budget=self.budget()
        phase,_=self.phase(budget,[response(page([repo(101)],total=101))])
        record=stage.runtime_path(budget)/'public'/export_candidates.RECORD_FILE
        record.write_bytes(record.read_bytes()+b'{}\n')
        with self.assertRaises(ValueError):self.publish(phase,budget)
        self.assertEqual(self.hashes(),before)

    def test_valid_staged_output_cannot_borrow_another_rounds_result_receipt(self):
        before=self.hashes();budget=self.budget()
        phase,_=self.phase(budget,[response(page([repo(101)],total=101))],
            receipt_mutation=lambda receipt:receipt.update(round_id='0'*32))
        self.assertFalse(phase['ok']);self.assertFalse(phase['published'])
        self.assertEqual(self.hashes(),before)

    def test_current_receipt_cannot_inflate_new_repository_count(self):
        before=self.hashes();budget=self.budget()
        phase,_=self.phase(budget,[response(page([repo(101)],total=101))],
            receipt_mutation=lambda receipt:receipt['phase'].update(new_unique_repositories=999))
        self.assertFalse(phase['ok']);self.assertFalse(phase['published'])
        self.assertEqual(self.hashes(),before)

    def test_durable_snapshot_change_between_child_and_publication_is_not_overwritten(self):
        budget=self.budget();phase,_=self.phase(budget,[response(page([repo(101)],total=101))])
        path=self.root/'data'/candidate_state.PROGRESS_FILE
        path.write_bytes(path.read_bytes()+b' ')
        changed=self.hashes()
        with self.assertRaises(ValueError):self.publish(phase,budget)
        self.assertEqual(self.hashes(),changed)

    def run_coordinator(self, phase, budget, *, enabled=True):
        config={**CONFIG,'github_candidates_enabled':enabled,'recent_lookback_days':14,
                'recent_max_results':20,'harvest_limit':20,'history_limit':5,
                'timezone':'UTC','scan_times_local':['00:17','08:17','16:17'],'policy':'Fixture'}
        # The final gate must be independent even of a successful legacy validate receipt.
        def child(name, command, timeout=None):
            return {'name':name,'ok':True,'started_at':self.timer.now(),'exit_code':0}
        with mock.patch.object(scan,'DATA',self.root/'data'),mock.patch.object(scan,'stage',side_effect=child), \
                mock.patch.object(scan,'candidate_phase',return_value=phase), \
                mock.patch.object(scan,'recent_phase',return_value={'name':'recent_arxiv','ok':True,'complete':True}), \
                mock.patch.dict(scan.os.environ,{'GITHUB_STEP_SUMMARY':'','GITHUB_OUTPUT':''}), \
                mock.patch('sys.stdout',new_callable=io.StringIO):
            code=scan.run_round(config,budget)
        return code,json.loads((self.root/'data/scan-status.json').read_bytes())

    def test_failed_triplet_write_and_failed_rollback_are_fatal_despite_legacy_success(self):
        prior=self.hashes();budget=self.budget()
        phase,_=self.phase(budget,[response(page([repo(101)],total=101))])
        replace=candidate_state.os.replace
        def fail_write_and_rollback(source,target):
            if (Path(target).name==candidate_state.PROGRESS_FILE
                    or Path(source).name=='restore-'+export_candidates.MANIFEST_FILE):
                raise OSError('Injected candidate write and rollback failure')
            return replace(source,target)
        with mock.patch.object(candidate_state.os,'replace',side_effect=fail_write_and_rollback):
            code,report=self.run_coordinator(phase,budget)
        self.assertEqual((code,report['status']),(1,'failed'))
        self.assertFalse(report['candidate_observations']['durable_validation']['ok'])
        self.assertTrue(any('Candidate snapshot integrity:' in w for w in report['warnings']))
        self.assertEqual(self.hashes()[candidate_state.PROGRESS_FILE],prior[candidate_state.PROGRESS_FILE])
        self.assertNotEqual(self.hashes()[export_candidates.MANIFEST_FILE],prior[export_candidates.MANIFEST_FILE])
        with self.assertRaises(ValueError):candidate_state.load_snapshot(self.root/'data')
        with mock.patch.object(builder,'DATA',self.root/'data'),self.assertRaisesRegex(ValueError,'Candidate snapshot integrity'):
            catalog.main(['validate'])

    def test_successful_rollback_keeps_verified_legacy_progress_partial(self):
        prior=self.hashes();budget=self.budget()
        phase,_=self.phase(budget,[response(page([repo(101)],total=101))])
        replace=candidate_state.os.replace
        def fail_progress_once(source,target):
            if Path(source).name==candidate_state.PROGRESS_FILE:
                raise OSError('Injected candidate progress replacement failure')
            return replace(source,target)
        with mock.patch.object(candidate_state.os,'replace',side_effect=fail_progress_once):
            code,report=self.run_coordinator(phase,budget)
        self.assertEqual((code,report['status']),(0,'partial'))
        self.assertTrue(report['candidate_observations']['durable_validation']['ok'])
        self.assertEqual(self.hashes(),prior)

    def test_final_gate_also_rejects_torn_state_after_deferred_failed_or_disabled_phase(self):
        path=self.root/'data'/candidate_state.PROGRESS_FILE
        checkpoint=json.loads(path.read_bytes());checkpoint['manifest_sha256']='0'*64
        path.write_text(json.dumps(checkpoint),encoding='utf-8')
        for state,enabled,ok in [('deferred_budget',True,True),('child_failed',True,False),
                                 ('rate_limited',True,True),('disabled',False,True)]:
            with self.subTest(state=state):
                phase={'name':stage.PHASE,'ok':ok,'state':state,'published':False,
                       'request_attempted':False,'requests_attempted':0,'warnings':[]}
                code,report=self.run_coordinator(phase,self.budget(),enabled=enabled)
                self.assertEqual((code,report['status']),(1,'failed'))
                self.assertFalse(report['candidate_observations']['durable_validation']['ok'])

    def test_catalog_validation_accepts_disabled_optional_pair_but_requires_enabled_checkpoint(self):
        (self.root/'data'/candidate_state.PROGRESS_FILE).unlink()
        config=self.root/'data/scan-config.json'
        config.write_text(json.dumps({'github_candidates_enabled':False}),encoding='utf-8')
        # Retained comparison context can legitimately differ from current catalog bytes.
        path=self.root/'data/catalog.jsonl';path.write_bytes(path.read_bytes()+b'\n')
        self.assertEqual(catalog.validate_candidate_snapshot(self.root/'data')['mode'],'optional_pair')
        with mock.patch.object(builder,'DATA',self.root/'data'),mock.patch('sys.stdout',new_callable=io.StringIO):
            self.assertEqual(catalog.main(['validate']),0)
        config.write_text(json.dumps({'github_candidates_enabled':True}),encoding='utf-8')
        with mock.patch.object(builder,'DATA',self.root/'data'),self.assertRaisesRegex(ValueError,'Candidate snapshot integrity'):
            catalog.main(['validate'])
        phase={'name':stage.PHASE,'ok':True,'state':'deferred_budget','published':False,'warnings':[]}
        code,report=self.run_coordinator(phase,self.budget())
        self.assertEqual((code,report['status']),(1,'failed'))

    def test_catalog_validation_checks_present_checkpoint_even_with_automation_disabled(self):
        (self.root/'data/scan-config.json').write_text(json.dumps({'github_candidates_enabled':False}),encoding='utf-8')
        self.assertEqual(catalog.validate_candidate_snapshot(self.root/'data')['mode'],'resumable_triplet')
        path=self.root/'data'/candidate_state.PROGRESS_FILE;path.write_bytes(b'{')
        with mock.patch.object(builder,'DATA',self.root/'data'),self.assertRaisesRegex(ValueError,'Candidate snapshot integrity'):
            builder.validate(type('Args',(),{})())


class CandidateCoordinatorTests(unittest.TestCase):
    def test_candidate_child_timeout_uses_the_shared_remaining_deadline(self):
        budget=mock.Mock();budget.remaining_seconds.return_value=7
        with mock.patch.object(scan,'budget_from_environment',return_value=budget), \
                mock.patch.object(scan.subprocess,'run',side_effect=subprocess.TimeoutExpired(['fixture'],7)) as run:
            result=scan.stage(stage.PHASE,['scripts/scan_candidate_stage.py'],timeout=30)
        self.assertFalse(result['ok']);self.assertEqual(run.call_args.kwargs['timeout'],7)
        self.assertEqual(run.call_args.kwargs['env'][network_budget.ENV_PHASE],stage.PHASE)

    def test_production_configuration_has_exact_precise_topics_and_bounded_caps(self):
        config=json.loads((ROOT/'data/scan-config.json').read_text(encoding='utf-8'))
        limits=stage.settings(config)
        self.assertTrue(limits['enabled']);self.assertEqual(set(limits['topics']),scanner.TOPICS)
        self.assertEqual((limits['max_requests'],limits['max_seconds'],limits['existing_budget']),(30,220,5))
        for change in ({'github_candidate_max_requests':31},{'github_candidate_max_seconds':221},
                       {'github_candidate_existing_budget':6},{'github_candidate_topics':['ai-agent']},
                       {'github_candidates_enabled':1}):
            with self.subTest(change=change),self.assertRaises(ValueError):stage.settings({**config,**change})

    def test_bounded_pending_progress_does_not_create_repeated_failure_warnings(self):
        summary={'run_id':'run:fixture','status':'request_budget','requests_attempted':30,
                 'new_unique_repositories':5,'total_unique_repositories':105,'pending_queries':20,
                 'unknown_requests':0,'rejected_rows':{},'files':{}}
        phase=stage.phase_summary(summary,'2026-10-18T00:00:00Z')
        self.assertTrue(phase['ok']);self.assertFalse(phase['complete']);self.assertEqual(phase['warnings'],[])
        status,warnings=scan.summarize_phases([{'name':'recent_arxiv','ok':True},phase],[],[],[])
        self.assertEqual((status,warnings),('success',[]))

    def test_zero_pending_does_not_hide_blocked_or_partial_search_windows(self):
        summary={'run_id':'run:fixture','status':'partial','requests_attempted':0,
                 'new_unique_repositories':0,'total_unique_repositories':100,'pending_queries':0,
                 'unknown_requests':0,'rejected_rows':{},'files':{},
                 'query_status_counts':{'blocked_single_day_window':1,'partial_results':1}}
        phase=stage.phase_summary(summary,'2026-10-18T00:00:00Z')
        self.assertFalse(phase['complete']);self.assertEqual(phase['state'],'blocked')
        self.assertEqual(len(phase['warnings']),2)

    def test_only_new_verified_candidate_responses_can_make_an_otherwise_failed_round_partial(self):
        legacy=[{'name':'discovery','ok':False},{'name':'huggingface','ok':False},
                {'name':'recent_arxiv','ok':False},{'name':'build','ok':True},{'name':'validate','ok':True}]
        for successes,published,expected in [(0,True,'failed'),(1,False,'failed'),(1,True,'partial')]:
            phase={'name':stage.PHASE,'ok':True,'published':published,'successful_responses':successes}
            with self.subTest(successes=successes,published=published):
                self.assertEqual(scan.summarize_phases([*legacy,phase],[],[],[])[0],expected)

    def test_candidate_publication_follows_successful_build_only(self):
        for build_ok in (True,False):
            with self.subTest(build_ok=build_ok),tempfile.TemporaryDirectory() as directory:
                root=Path(directory).resolve();events=[]
                config={'recent_lookback_days':14,'recent_max_results':20,'harvest_limit':20,'history_limit':5,
                        'timezone':'UTC','scan_times_local':['00:17','08:17','16:17'],'policy':'Fixture'}
                budget=RoundBudget.create(root/'rounds',max_requests=10,max_seconds=60)
                phase={'name':stage.PHASE,'ok':True,'ready_to_publish':True,'published':False,'warnings':[]}
                def child(name,command):
                    events.append(name)
                    return {'name':name,'ok':build_ok if name=='build' else True,'started_at':'2026-10-18T00:00:00Z'}
                def candidate(config):events.append(stage.PHASE);return phase
                def publish(p,b):events.append('publish_candidates');p['published']=True
                with mock.patch.object(scan,'DATA',root),mock.patch.object(scan,'stage',side_effect=child), \
                        mock.patch.object(scan,'recent_phase',return_value={'name':'recent_arxiv','ok':True}), \
                        mock.patch.object(scan,'candidate_phase',side_effect=candidate), \
                        mock.patch.object(scan,'publish_candidate_phase',side_effect=publish) as install, \
                        mock.patch.dict(scan.os.environ,{'GITHUB_STEP_SUMMARY':'','GITHUB_OUTPUT':''}), \
                        mock.patch('sys.stdout',new_callable=io.StringIO):
                    scan.run_round(config,budget)
                self.assertEqual(events[:4],['discovery','huggingface','harvest',stage.PHASE])
                if build_ok:
                    self.assertLess(events.index('build'),events.index('publish_candidates'))
                    self.assertLess(events.index('publish_candidates'),events.index('validate'))
                    install.assert_called_once()
                else:install.assert_not_called();self.assertFalse(phase['published'])


if __name__=='__main__':unittest.main()
