"""A new UTC frontier stays fresh without erasing unfinished historical coverage."""
import copy
import json
from pathlib import Path
import shutil
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlencode, urlsplit

import test_github_candidate_scan as fixtures
import candidate_state
import export_candidates
from network_budget import RoundBudget

scan=fixtures.scan
repo,page,response=fixtures.repo,fixtures.page,fixtures.response


class FrontierTests(unittest.TestCase):
    setUp=fixtures.ScanTests.setUp
    write_inputs=fixtures.ScanTests.write_inputs

    def execute(self, responses, **options):
        answers=iter(responses)
        def fetch(url,timeout):
            self.calls.append(url)
            return next(answers)
        args={'max_requests':len(responses) or 1,'existing_budget':0,'max_seconds':120,
              'topics':['computer-use'],'strict_replay':True,'advance_epoch':True,
              'fetcher':fetch,'clock':self.timer.clock,'sleep':self.timer.sleep,'now':self.timer.now}
        if not (self.output/'candidate-metadata.json').exists():
            args.update(created_after='2024-01-01',created_before='2026-10-18')
        args.update(options)
        with mock.patch.object(scan,'budget_from_environment',return_value=None), \
             mock.patch('socket.create_connection',side_effect=AssertionError('Network forbidden')):
            return scan.run_scan(self.root,self.output,**args)

    def next_day(self):
        self.timer.sleep(86400)

    def partial_then_frontier(self):
        old,_=self.execute([response(page([repo(1)],incomplete=True))])
        self.next_day()
        new,run=self.execute([response(page([])),response(page([repo(1)],incomplete=True))])
        return old,new,run

    def test_persistent_partial_does_not_block_new_frontier_or_hide_old_gap(self):
        old,new,run=self.partial_then_frontier()
        self.assertEqual(new['epochs'][-1]['reason'],'frontier_continuation')
        self.assertEqual(new['configuration']['created_after'],'2026-10-18')
        self.assertEqual(new['configuration']['created_before'],'2026-10-19')
        self.assertEqual(run['repair_epoch_ids'],[old['current_epoch_id']])
        self.assertEqual(new['receipts'][:len(old['receipts'])],old['receipts'])
        old_query=next(q for q in new['queries'] if q['id']==old['queries'][1]['id'])
        self.assertEqual(old_query['status'],'partial_results')
        self.assertEqual(run['status'],'partial')
        self.assertIn('created:2026-10-18..2026-10-19',parse_qs(urlsplit(self.calls[-2]).query)['q'][0])
        summary=export_candidates._summary(new)
        self.assertIn('partial_results',[q['status'] for q in summary['queries']])
        self.assertFalse(summary['global_completeness_established'])
        epoch_count=len(new['epochs'])
        same_day,_=self.execute([response(page([repo(1)],incomplete=True))])
        self.assertEqual(len(same_day['epochs']),epoch_count)
        self.assertEqual(same_day['runs'][-1]['repair_epoch_ids'],[old['current_epoch_id']])
        scan.validate_state(same_day)

    def test_fresh_and_historical_requests_alternate_within_unchanged_cap(self):
        old,_=self.execute([response(page([repo(i) for i in range(1,101)],201))])
        seeds=[repo(10000+i,'public-owner/seed-'+str(i)) for i in range(1,6)]
        self.write_inputs([{'id':'github:'+r['full_name'],'url':r['html_url'],'provider':'github','discovered_in':[]} for r in seeds])
        self.next_day()
        fresh=lambda i:repo(i,created_at='2026-10-19T00:00:00Z')
        new,run=self.execute([*[response(r) for r in seeds],response(page([fresh(i) for i in range(1001,1101)],201)),
            response(page([repo(i) for i in range(101,201)],201)),
            response(page([fresh(i) for i in range(1101,1201)],201)),response(page([repo(201)],201))],existing_budget=5)
        requests=new['receipts'][len(old['receipts']):]
        self.assertTrue(all(r['query_id'].startswith('existing:') for r in requests[:5]))
        requests=requests[5:]
        old_id=next(q['id'] for q in old['queries'] if q['kind']=='search')
        new_id=new['epochs'][-1]['root_query_ids'][0]
        self.assertEqual([r['query_id'] for r in requests],[new_id,old_id,new_id,old_id])
        self.assertEqual([r['position'] for r in requests],[1,2,2,3])
        self.assertEqual(run['requests_attempted'],9)
        self.assertEqual(run['repair_epoch_ids'],[old['current_epoch_id']])
        self.assertEqual(next(q for q in new['queries'] if q['id']==old_id)['status'],'observed_pages_exhausted')
        # Permission remains justified by the start boundary after that repair finishes.
        scan.validate_state(new)

    def test_blocked_single_day_stays_visible_but_no_longer_blocks_fresh_dates(self):
        item=repo(1,created_at='2026-10-18T00:00:00Z')
        old,_=self.execute([response(page([item],1000))],created_after='2026-10-18')
        self.next_day();new,run=self.execute([response(page([]))])
        self.assertEqual(run['requests_attempted'],1)
        self.assertEqual(run['repair_epoch_ids'],[])
        self.assertEqual(new['epochs'][-1]['reason'],'frontier_continuation')
        self.assertIn('blocked_single_day_window',[q['status'] for q in new['queries']])
        self.assertEqual(new['query_rechecks'],[])

    def test_completed_previous_flow_uses_compatible_daily_transition(self):
        self.execute([response(page([]))]);self.next_day()
        new,run=self.execute([response(page([]))])
        self.assertEqual(new['epochs'][-1]['reason'],'daily_continuation')
        self.assertEqual(run['repair_epoch_ids'],[])
        self.assertEqual(run['status'],'finished')
        scan.validate_state(new)

    def test_shared_topic_roots_have_one_latest_owner_and_one_repair_lane(self):
        old,_=self.execute([response(page([repo(1)],incomplete=True))])
        expanded=scan.expand_topics(old,['computer-use','gui-agent'],at=self.timer.now())
        (self.output/'candidate-metadata.json').write_text(json.dumps(expanded),encoding='utf-8')
        self.next_day();new,run=self.execute([response(page([])),response(page([repo(1)],incomplete=True))],topics=['computer-use','gui-agent'])
        self.assertEqual(run['repair_epoch_ids'],[expanded['current_epoch_id']])
        self.assertNotIn(old['current_epoch_id'],run['repair_epoch_ids'])
        self.assertEqual(len({r['query_id'] for r in new['receipts'][-2:]}),2)
        scan.validate_state(new)

    def test_forged_repair_scope_and_cross_epoch_receipt_are_rejected(self):
        old,new,_=self.partial_then_frontier()
        for scope in [[],[new['current_epoch_id']],[old['current_epoch_id'],new['current_epoch_id']],['epoch:'+'0'*24],[[]]]:
            changed=copy.deepcopy(new);changed['runs'][-1]['repair_epoch_ids']=scope
            with self.subTest(scope=scope),self.assertRaises(ValueError):scan.validate_state(changed)
        changed=copy.deepcopy(new)
        earlier=changed['receipts'][0];earlier['query_id']=changed['epochs'][-1]['root_query_ids'][0]
        # Retarget its numeric row occurrence too, so rejection reaches epoch ownership.
        for row in changed['records'].values():
            for occurrence in row['occurrences']:
                if occurrence['receipt_id']==earlier['id']:occurrence['query_id']=earlier['query_id']
        with self.assertRaisesRegex(ValueError,'another run epoch'):scan.validate_state(changed)

    def test_recheck_owner_run_boundary_and_date_are_bound(self):
        old,new,_=self.partial_then_frontier()
        mutations=[lambda e:e.update(epoch_id=new['current_epoch_id']),
                   lambda e:e.update(run_id=old['runs'][0]['id']),
                   lambda e:e.update(receipt_boundary=0),
                   lambda e:e.update(restarted_at='2026-10-21T00:00:00Z'),
                   lambda e:e.update(restarted_at='2000-01-01T00:00:00Z'),
                   lambda e:e.pop('run_id'),
                   lambda e:e['previous'].update(status='partial_api_window'),
                   lambda e:e['previous'].update(reported_total=999)]
        for mutation in mutations:
            changed=copy.deepcopy(new);mutation(changed['query_rechecks'][-1])
            with self.assertRaises(ValueError):scan.validate_state(changed)

    def test_new_recheck_binding_cannot_be_removed_or_retimed_at_finalization(self):
        initial,_=self.execute([response(page([repo(1)],incomplete=True))])
        catalog=b'{"id":"github:example/active"}\n';ledger=export_candidates.encoded(initial)
        body,manifest=export_candidates.build_candidate_export(ledger,self.output/'raw',catalog)
        pair=self.root/'pair';export_candidates.write_pair(pair,body,manifest)
        bound=self.root/'bound';candidate_state.bootstrap_from_ledger(ledger,self.output/'raw',pair,bound,catalog_bytes=catalog)
        baseline=candidate_state.load_snapshot(bound);before=dict(baseline.payloads)
        self.output=self.root/'fresh-runtime';candidate_state.prepare_runtime(baseline,self.output)
        self.next_day();current,_=self.execute([response(page([])),response(page([repo(1)],incomplete=True))])
        # Matching instants are accepted even when represented with another offset.
        equivalent=copy.deepcopy(current)
        equivalent['query_rechecks'][-1]['restarted_at']='2026-10-18T17:00:00-07:00'
        scan.validate_state(equivalent);candidate_state._history(baseline,equivalent)
        mutations=[('missing_run',lambda e:e.pop('run_id')),
                   ('missing_run_future',lambda e:(e.pop('run_id'),e.update(restarted_at='2026-10-25T00:00:00Z'))),
                   ('backdated',lambda e:e.update(restarted_at='2000-01-01T00:00:00Z')),
                   ('future',lambda e:e.update(restarted_at='2026-10-25T00:00:00Z'))]
        for name,mutation in mutations:
            with self.subTest(case=name):
                changed=copy.deepcopy(current);mutation(changed['query_rechecks'][-1])
                with self.assertRaises(ValueError):scan.validate_state(changed)
                # The adoption boundary must require the binding independently
                # of standalone legacy compatibility, not only when present.
                with self.assertRaises(candidate_state.CandidateStateError):candidate_state._history(baseline,changed)
                (self.output/'candidate-metadata.json').write_bytes(export_candidates.encoded(changed))
                staged=self.root/('invalid-staged-'+name)
                with self.assertRaises(ValueError):candidate_state.finalize_runtime(baseline,self.output,staged,catalog_bytes=catalog)
                self.assertFalse(staged.exists())
        self.assertEqual({n:(bound/n).read_bytes() for n in candidate_state.FILES},before)

    def test_legacy_rechecks_keep_their_bytes_but_need_an_actual_legacy_run(self):
        self.execute([response(page([repo(1)],incomplete=True))])
        self.timer.sleep(10)
        legacy,_=self.execute([response(page([repo(1)],incomplete=True))])
        for run in legacy['runs']:run.pop('repair_epoch_ids')
        event=legacy['query_rechecks'][-1];event.pop('run_id')
        # Old producers recorded the restart just before the run's start.
        event['restarted_at']='2026-10-18T00:00:09+00:00'
        before=export_candidates.encoded(legacy)
        scan.validate_state(legacy)
        self.assertEqual(export_candidates.encoded(legacy),before)
        for time in ['2000-01-01T00:00:00Z','2026-10-25T00:00:00Z']:
            changed=copy.deepcopy(legacy);changed['query_rechecks'][-1]['restarted_at']=time
            with self.assertRaisesRegex(ValueError,'matching legacy run'):scan.validate_state(changed)

    def test_future_frontier_and_observation_clock_forgery_are_rejected(self):
        _,new,_=self.partial_then_frontier()
        # A later introducing-run clock cannot be invented while earlier request
        # receipts still carry their actual observation time.
        changed=copy.deepcopy(new);changed['runs'][-1]['started_at']='2026-10-21T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'precedes its run'):scan.validate_state(changed)
        changed=copy.deepcopy(new);changed['epochs'][-1]['created_at']='2026-10-21T00:00:00Z'
        epoch=changed['epochs'][-1];replacement=scan._epoch(epoch['configuration'],epoch['root_query_ids'],epoch['created_at'],epoch['reason'],epoch['previous_epoch_id'])
        # Epoch IDs exclude timestamp, but its date is independently checked.
        self.assertEqual(replacement['id'],epoch['id'])
        with self.assertRaisesRegex(ValueError,'UTC creation date'):scan.validate_state(changed)
        # Recompute the forged query and epoch identities too; a consistent future
        # shape still cannot outrun the actual introducing run/observation date.
        changed=copy.deepcopy(new);old_epoch=changed['epochs'][-1]
        old_qid=old_epoch['root_query_ids'][0];old_query=next(q for q in changed['queries'] if q['id']==old_qid)
        forged_query=scan.search_query(old_query['topic'],old_query['created_after'],'2026-10-21')
        forged_query.update({k:old_query[k] for k in scan.QUERY_PROGRESS})
        changed['queries'][changed['queries'].index(old_query)]=forged_query
        config={**old_epoch['configuration'],'created_before':'2026-10-21'}
        forged_epoch=scan._epoch(config,[forged_query['id']],'2026-10-21T00:00:00Z',old_epoch['reason'],old_epoch['previous_epoch_id'])
        changed['epochs'][-1]=forged_epoch;changed['configuration']=config;changed['current_epoch_id']=forged_epoch['id']
        changed['runs'][-1]['epoch_id']=forged_epoch['id']
        for receipt in changed['receipts']:
            if receipt['query_id']==old_qid:
                receipt['query_id']=forged_query['id']
                receipt['source_url']='https://api.github.com/search/repositories?'+urlencode({'q':forged_query['query'],'per_page':100,'page':1,'sort':'updated','order':'asc'})
                receipt['request_url_sha256']=scan.digest(receipt['source_url'].encode())
        with self.assertRaisesRegex(ValueError,'exceeds its recorded run date'):scan.validate_state(changed)
        changed=copy.deepcopy(new);changed['runs'][-1].pop('repair_epoch_ids')
        with self.assertRaisesRegex(ValueError,'scoped introducing run'):scan.validate_state(changed)

    def test_shared_zero_get_deferral_and_rate_limit_keep_both_cursors(self):
        old,_=self.execute([response(page([repo(1)],incomplete=True))]);self.next_day()
        budget=RoundBudget.create(self.root/'budgets',max_requests=1,max_seconds=60,clock=self.timer.clock,
            sleep=self.timer.sleep,now=lambda:scan.timestamp(self.timer.now()))
        url='https://api.github.com/repos/public-owner/earlier'
        token=budget.reserve(url);budget.observe_response(url,200,attempt=token)
        deferred,run=self.execute([],shared_budget=budget)
        self.assertEqual(run['requests_attempted'],0);self.assertEqual(deferred['records'],old['records'])
        self.assertEqual(deferred['receipts'],old['receipts'])
        self.assertEqual(sum(q['kind']=='search' and q['status']=='pending' for q in deferred['queries']),2)
        limited,run=self.execute([response({'message':'Rate limit exceeded'},429,{'Retry-After':'60'})],max_requests=5)
        self.assertEqual(run['requests_attempted'],1);self.assertEqual(run['status'],'rate_limited')
        self.assertEqual(limited['records'],old['records'])
        self.assertEqual(sum(q['kind']=='search' and q['status']=='pending' for q in limited['queries']),2)
        scan.validate_state(limited)

    def test_frontier_triplet_continues_from_public_state_without_old_raw(self):
        initial,_=self.execute([response(page([repo(1)],incomplete=True))])
        ledger=export_candidates.encoded(initial);catalog=b'{"id":"github:example/active"}\n'
        body,manifest=export_candidates.build_candidate_export(ledger,self.output/'raw',catalog)
        pair=self.root/'pair';export_candidates.write_pair(pair,body,manifest)
        bound=self.root/'bound';candidate_state.bootstrap_from_ledger(ledger,self.output/'raw',pair,bound,catalog_bytes=catalog)
        baseline=candidate_state.load_snapshot(bound);shutil.rmtree(self.output/'raw')
        self.output=self.root/'fresh-runtime';candidate_state.prepare_runtime(baseline,self.output)
        self.next_day();current,_=self.execute([response(page([])),response(page([repo(1)],incomplete=True))])
        result=candidate_state.finalize_runtime(baseline,self.output,self.root/'staged',catalog_bytes=catalog)
        staged=candidate_state.load_snapshot(self.root/'staged')
        self.assertEqual(result['verification']['successful_receipts_replayed'],2)
        self.assertFalse(result['verification']['historical_raw_replayed'])
        self.assertEqual(staged.state['receipts'][:len(baseline.state['receipts'])],baseline.state['receipts'])
        self.assertEqual(staged.manifest['scan']['epochs'][-1]['reason'],'frontier_continuation')
        self.assertIn('partial_results',[q['status'] for q in staged.manifest['scan']['queries']])
        import jsonschema
        root=Path(__file__).resolve().parents[1]
        for name,payload in [('github-candidate-progress.schema.json',json.loads(staged.payloads[candidate_state.PROGRESS_FILE])),
                             ('github-candidate-observation-manifest.schema.json',staged.manifest)]:
            jsonschema.Draft202012Validator(json.loads((root/'schemas'/name).read_bytes())).validate(payload)


if __name__=='__main__':unittest.main()
