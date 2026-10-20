"""Shared request accounting, replay quarantine and explicit epoch continuation."""
import copy
import json
from pathlib import Path
import unittest
from unittest import mock

import test_github_candidate_scan as fixtures
from network_budget import RoundBudget

scan = fixtures.scan
repo, page, response = fixtures.repo, fixtures.page, fixtures.response


class ScheduledScannerTests(unittest.TestCase):
    setUp = fixtures.ScanTests.setUp
    write_inputs = fixtures.ScanTests.write_inputs
    execute = fixtures.ScanTests.execute
    ledger_bytes = fixtures.ScanTests.ledger_bytes

    def budget(self, **kwargs):
        return RoundBudget.create(self.root / '.cache' / 'budgets', clock=self.timer.clock,
                                  sleep=self.timer.sleep, now=lambda: scan.timestamp(self.timer.now()), **kwargs)

    def test_shared_preflight_deferral_is_not_a_get_or_receipt(self):
        budget = self.budget(max_requests=1, max_seconds=60)
        token = budget.reserve('https://api.github.com/repos/public-owner/earlier')
        budget.observe_response('https://api.github.com/repos/public-owner/earlier', 200, {}, attempt=token)
        state, run = self.execute([], max_requests=2, shared_budget=budget, strict_replay=True)
        self.assertEqual(self.calls, [])
        self.assertEqual(run['requests_attempted'], 0)
        self.assertEqual(run['unknown_requests'], 0)
        self.assertEqual(state['receipts'], [])
        self.assertEqual(run['status'], 'request_budget')
        self.assertEqual(run['shared_budget']['reservations_charged'], 0)
        self.assertEqual(run['shared_budget']['deferred_reason'], 'request_budget')
        self.assertEqual(run['deferred_queries'], 1)

    def test_reservation_before_local_deadline_deferral_remains_distinct(self):
        budget = self.budget(max_requests=2, max_seconds=60)
        original = budget.reserve
        def reserve_then_delay(*args, **kwargs):
            number = original(*args, **kwargs); self.timer.sleep(2); return number
        with mock.patch.object(budget, 'reserve', side_effect=reserve_then_delay):
            state, run = self.execute([], max_seconds=1, shared_budget=budget)
        self.assertEqual(self.calls, [])
        self.assertEqual(run['requests_attempted'], 0)
        self.assertEqual(run['shared_budget']['reservations_charged'], 1)
        self.assertEqual(budget.summary()['unknown_attempts'], 1)
        self.assertEqual(state['receipts'], [])
        self.assertEqual(run['status'], 'wall_budget')

    def test_shared_attempts_and_body_rate_limit_stop_same_provider(self):
        budget = self.budget(max_requests=4, max_seconds=60)
        state, run = self.execute([response(page([repo()])),
                                  response({'message': 'You have exceeded a secondary rate limit.'}, 403)],
                                 max_requests=3, topics=['browser-automation', 'computer-use', 'gui-agent'],
                                 shared_budget=budget, strict_replay=True)
        self.assertEqual(run['requests_attempted'], 2)
        self.assertEqual(run['shared_budget']['reservations_charged'], 2)
        self.assertEqual(budget.summary()['responses_received'], 2)
        self.assertIn('api.github.com', budget.summary()['blocked_providers'])
        self.assertEqual(run['shared_budget']['deferred_reason'], 'provider_cooldown')
        self.assertEqual(run['status'], 'rate_limited')
        before_calls = len(self.calls)
        self.timer.sleep(61)
        state, run = self.execute([], max_requests=3, topics=['browser-automation', 'computer-use', 'gui-agent'],
                                 shared_budget=budget, strict_replay=True)
        self.assertEqual(len(self.calls), before_calls)
        self.assertEqual(run['requests_attempted'], 0)
        self.assertEqual(len(state['records']), 1)

    def test_default_context_is_loaded_and_shared_timeout_is_used(self):
        budget = self.budget(max_requests=2, max_seconds=3)
        with mock.patch.object(scan, 'budget_from_environment', return_value=budget):
            _, run = self.execute([response(page([repo()]))], max_seconds=30)
        self.assertEqual(run['requests_attempted'], 1)
        self.assertLessEqual(self.calls[0][1], 3)
        self.assertEqual(run['shared_budget']['round_id'], budget.run_id)

    def test_retry_after_http_date_matches_shared_and_survives_standalone_resume(self):
        budget = self.budget(max_requests=2, max_seconds=60)
        state, _ = self.execute([response({'message':'Rate limited.'}, 429,
                                         {'Retry-After':'Sun, 18 Oct 2026 02:00:00 GMT'})],
                                shared_budget=budget, strict_replay=True)
        self.assertEqual(state['deferred_until'], '2026-10-18T02:00:00+00:00')
        self.assertEqual(state['deferred_until'], budget.summary()['provider_cooldowns']['api.github.com'])
        self.timer.sleep(61)
        state, run = self.execute([], strict_replay=True)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(run['requests_attempted'], 0)
        self.assertEqual(run['status'], 'rate_limited')
        self.assertEqual(state['deferred_until'], '2026-10-18T02:00:00+00:00')

    def test_retry_after_dates_use_same_fallback_and_cap_as_shared_budget(self):
        headers_list = [
            {'Retry-After':'Wed, 21 Oct 2026 02:00:00 GMT'},
            {'Retry-After':'Sun, 18 Oct 2026 02:00:00'},
            {'Retry-After':'Sat, 17 Oct 2026 23:00:00 GMT'},
            {'Retry-After':'malformed'},
            {'Retry-After':'120'},
            {'Retry-After':'60', 'X-RateLimit-Reset':str(int(scan.timestamp('2026-10-18T03:00:00Z').timestamp()))},
        ]
        for headers in headers_list:
            with self.subTest(headers=headers):
                budget = self.budget(max_requests=1, max_seconds=60)
                url = 'https://api.github.com/repos/public-owner/fixture'
                token = budget.reserve(url)
                budget.observe_response(url,429,headers,attempt=token)
                self.assertEqual(scan.delay_until(headers,scan.timestamp(self.timer.now())),
                                 budget.summary()['provider_cooldowns']['api.github.com'])

    def test_strict_mixed_page_keeps_cursor_and_all_siblings_for_retry(self):
        state, _ = self.execute([response(page([repo(i) for i in range(1, 101)], 101))],
                                strict_replay=True, advance_epoch=True)
        before = copy.deepcopy(state)
        state, run = self.execute([response(page([repo(101), repo(102, 'SECRET/private', private=True)], 102))],
                                  strict_replay=True, advance_epoch=True)
        self.assertEqual(state['records'], before['records'])
        self.assertEqual(state['receipts'][:-1], before['receipts'])
        receipt = state['receipts'][-1]
        self.assertEqual(receipt['outcome'], 'quarantined')
        self.assertEqual(receipt['accepted_repository_ids'], [])
        self.assertFalse(receipt['raw_body_retained'])
        self.assertIsNone(receipt['source_url'])
        self.assertNotIn(b'SECRET', self.ledger_bytes())
        query = next(q for q in state['queries'] if q['kind'] == 'search')
        old_query = next(q for q in before['queries'] if q['kind'] == 'search')
        self.assertEqual({k:v for k,v in query.items() if k != 'last_attempt'},
                         {k:v for k,v in old_query.items() if k != 'last_attempt'})
        self.assertEqual(run['accepted_metadata_rows'], 0)
        self.assertEqual(run['requests_attempted'], 1)
        state, run = self.execute([response(page([repo(101)], 101))], strict_replay=True, advance_epoch=True)
        self.assertEqual(len(state['records']), 101)
        self.assertEqual(run['new_unique_repositories'], 1)
        self.assertIn('page=2', self.calls[-1][0])
        self.assertEqual(next(q for q in state['queries'] if q['kind'] == 'search')['status'], 'observed_pages_exhausted')

    def test_strict_direct_rejection_does_not_skip_seed(self):
        self.write_inputs([{'id':'github:public-owner/wanted', 'url':'https://github.com/public-owner/wanted',
                            'provider':'github', 'discovered_in':[]}])
        state, _ = self.execute([response(repo(1, 'different/unrequested'))], existing_budget=1, strict_replay=True)
        query = next(q for q in state['queries'] if q['kind'] == 'existing')
        self.assertEqual((query['next_index'], query['status']), (0, 'pending'))
        state, run = self.execute([response(repo(1, 'public-owner/wanted'))], existing_budget=1, strict_replay=True)
        self.assertEqual(run['new_unique_repositories'], 1)
        self.assertTrue(self.calls[-1][0].endswith('/repos/public-owner/wanted'))

    def test_split_children_use_remaining_request_budget_in_same_invocation(self):
        for advance_epoch in (False, True):
            with self.subTest(advance_epoch=advance_epoch):
                self.output = self.root / '.cache' / f'split-{advance_epoch}'
                start = len(self.calls)
                state, run = self.execute([response(page([repo()], 1000)),
                                           response(page([])), response(page([]))],
                                          max_requests=3, strict_replay=True,
                                          advance_epoch=advance_epoch)
                self.assertEqual(len(self.calls) - start, 3)
                self.assertEqual(run['requests_attempted'], 3)
                children = [q for q in state['queries'] if q.get('parent_id')]
                self.assertEqual(len(children), 2)
                self.assertTrue(all(q['status'] == 'observed_pages_exhausted' for q in children))
                self.assertEqual(run['deferred_queries'], 0)
                scan.validate_state(state)

    def test_strict_duplicate_identity_page_is_quarantined_before_any_mutation(self):
        for conflicting in (False, True):
            with self.subTest(conflicting=conflicting):
                self.output = self.root / '.cache' / f'duplicate-{conflicting}'
                before, _ = self.execute([response(page([repo(i) for i in range(1, 101)], 101))],
                                         strict_replay=True, advance_epoch=True)
                raw_before = {p.name for p in (self.output / 'raw').iterdir()}
                duplicate = repo(101, description='Conflicting metadata.' if conflicting else repo(101)['description'])
                state, run = self.execute([response(page([repo(101), duplicate], 101))],
                                         strict_replay=True, advance_epoch=True)
                receipt = state['receipts'][-1]
                self.assertEqual(state['records'], before['records'])
                self.assertEqual(state['receipts'][:-1], before['receipts'])
                self.assertEqual((receipt['outcome'], receipt['accepted_repository_ids']), ('quarantined', []))
                self.assertEqual(receipt['rejected_rows'], {'malformed': 1})
                self.assertFalse(receipt['raw_body_retained'])
                self.assertIsNone(receipt['source_url'])
                self.assertEqual({p.name for p in (self.output / 'raw').iterdir()}, raw_before)
                self.assertEqual(run['accepted_metadata_rows'], 0)
                query = next(q for q in state['queries'] if q['kind'] == 'search')
                old_query = next(q for q in before['queries'] if q['kind'] == 'search')
                self.assertEqual({k:v for k,v in query.items() if k != 'last_attempt'},
                                 {k:v for k,v in old_query.items() if k != 'last_attempt'})
                state, _ = self.execute([response(page([repo(101)], 101))],
                                       strict_replay=True, advance_epoch=True)
                self.assertIn('page=2', self.calls[-1][0])
                self.assertEqual(len(state['records']), 101)
                self.assertEqual(len(state['records']['github-repository:101']['occurrences']), 1)
                scan.validate_state(state)

    def test_strict_replay_receipt_cannot_claim_unretained_accepted_rows(self):
        state, _ = self.execute([response(page([repo()]))], strict_replay=True)
        state['receipts'][0].update(source_url=None, raw_body_retained=False, outcome='accepted_with_rejections')
        with self.assertRaisesRegex(ValueError, 'strict replay receipt'): scan.validate_state(state)

    def test_v1_migration_is_explicit_pure_and_idempotent(self):
        state, _ = self.execute([response(page([repo()]))])
        original = copy.deepcopy(state)
        migrated = scan.migrate_state(state, at=self.timer.now())
        self.assertEqual(state, original)
        self.assertEqual(migrated['schema_version'], 2)
        for field in ('records', 'queries', 'receipts', 'runs', 'inputs', 'configuration'):
            self.assertEqual(migrated[field], original[field])
        epoch = migrated['epochs'][0]
        self.assertEqual(epoch['reason'], 'v1_migration')
        self.assertEqual(epoch['source_state_sha256'], scan._state_digest(original))
        self.assertEqual(scan.migrate_state(migrated, at='2026-10-19T00:00:00Z'), migrated)

    def test_additive_nine_topic_expansion_preserves_pending_historical_roots(self):
        state, _ = self.execute([response(page([repo(i) for i in range(1, 101)], 101))],
                                topics=['browser-automation', 'computer-use'])
        original = copy.deepcopy(state)
        expanded = scan.expand_topics(state, sorted(scan.TOPICS), at=self.timer.now())
        self.assertEqual(state, original)
        by_id = {q['id']:q for q in expanded['queries']}
        self.assertTrue(all(by_id[q['id']] == q for q in original['queries']))
        self.assertEqual(expanded['epochs'][-1]['reason'], 'topic_expansion')
        for q in expanded['queries']:
            if q['id'] not in {old['id'] for old in original['queries']}:
                self.assertEqual((q['created_after'], q['created_before']), ('2024-01-01', '2024-01-04'))
        self.assertEqual(expanded['records'], original['records'])
        self.assertEqual(expanded['receipts'], original['receipts'])
        for bad in [['computer-use'], ['browser-automation', 'computer-use', 'generic-ai']]:
            with self.assertRaises(ValueError): scan.expand_topics(expanded, bad)

    def test_later_topic_addition_still_starts_at_original_history_floor(self):
        state, _ = self.execute([response(page([]))])
        state = scan.migrate_state(state, at='2024-01-04T12:00:00Z')
        scan._advance_epoch(state, '2024-01-05T12:00:00Z')
        existing = copy.deepcopy(state['queries'])
        expanded = scan.expand_topics(state, ['browser-automation', 'gui-agent'], at='2024-01-05T13:00:00Z')
        new = next(q for q in expanded['queries'] if q.get('topic') == 'gui-agent')
        self.assertEqual(new['created_after'], '2024-01-01')
        self.assertEqual(new['created_before'], '2024-01-05')
        self.assertEqual(expanded['queries'][:len(existing)], existing)

    def test_partial_recheck_uses_only_new_traversal_before_daily_overlap(self):
        state, _ = self.execute([response(page([repo(1)], incomplete=True))], advance_epoch=True, strict_replay=True)
        old_receipts = copy.deepcopy(state['receipts']); old_runs = copy.deepcopy(state['runs'])
        state, _ = self.execute([response(page([repo(2)]))], advance_epoch=True, strict_replay=True)
        self.assertEqual(state['receipts'][:1], old_receipts)
        self.assertEqual(state['runs'][:1], old_runs)
        self.assertEqual(len(state['epochs']), 1)
        self.assertEqual(len(state['query_rechecks']), 1)
        event = state['query_rechecks'][0]
        self.assertEqual(event['receipt_boundary'], 1)
        self.assertEqual(event['previous']['seen_repository_ids'], [1])
        self.assertEqual(event['previous']['status'], 'partial_results')
        query = next(q for q in state['queries'] if q['kind'] == 'search')
        self.assertEqual(query['seen_repository_ids'], [2])
        self.assertEqual(query['status'], 'observed_pages_exhausted')
        self.assertEqual(len(state['records']), 2)
        state, _ = self.execute([response(page([]))], advance_epoch=True, strict_replay=True,
                                created_after=None, created_before=None)
        self.assertEqual(len(state['epochs']), 2)
        self.assertEqual(state['epochs'][-1]['reason'], 'daily_continuation')
        self.assertEqual(state['configuration']['created_after'], '2024-01-04')
        self.assertEqual(state['configuration']['created_before'], '2026-10-18')

    def test_partial_restart_budget_is_two_and_does_not_fake_completion(self):
        topics = ['browser-automation', 'computer-use', 'gui-agent']
        self.execute([response(page([], incomplete=True)) for _ in topics], max_requests=3, topics=topics,
                     advance_epoch=True, strict_replay=True)
        state, _ = self.execute([response(page([])), response(page([]))], max_requests=2, topics=topics,
                                advance_epoch=True, strict_replay=True)
        self.assertEqual(len(state['query_rechecks']), 2)
        self.assertEqual(sum(q['status'] == 'partial_results' for q in state['queries']), 1)
        self.assertEqual(len(state['epochs']), 1)

    def test_single_day_overflow_is_not_automatically_restarted_or_advanced(self):
        self.execute([response(page([repo()], 1000))], created_before='2024-01-01', advance_epoch=True)
        state, run = self.execute([], created_before='2024-01-01', advance_epoch=True)
        self.assertEqual(run['requests_attempted'], 0)
        self.assertEqual(state['query_rechecks'], [])
        self.assertEqual(len(state['epochs']), 1)
        self.assertEqual(next(q for q in state['queries'] if q['kind']=='search')['status'], 'blocked_single_day_window')

    def test_epoch_history_and_receipt_progress_cannot_be_rewritten(self):
        state, _ = self.execute([response(page([repo()]))], advance_epoch=True)
        mutations = [lambda s:s['queries'][1].update(reported_total=0),
                     lambda s:s.update(current_epoch_id='epoch:'+'0'*24),
                     lambda s:s['epochs'][0].update(root_query_ids=[])]
        for mutation in mutations:
            changed=copy.deepcopy(state);mutation(changed)
            with self.assertRaises(ValueError):scan.validate_state(changed)

    def test_public_epoch_projection_reuses_exact_epoch_validator(self):
        state, _ = self.execute([response(page([]))], advance_epoch=True)
        keys = ('id','kind','topic','created_after','created_before','parent_id','status')
        projected = [{k:q[k] for k in keys if k in q} for q in state['queries']]
        scan.validate_public_epochs(state['configuration'],state['epochs'],state['current_epoch_id'],projected)
        broken=copy.deepcopy(projected)
        next(q for q in broken if q['kind']=='search')['created_after']='2023-01-01'
        with self.assertRaises(ValueError):scan.validate_public_epochs(state['configuration'],state['epochs'],state['current_epoch_id'],broken)

    def test_v2_and_scheduled_fields_conform_to_schema(self):
        try: import jsonschema
        except ImportError: self.skipTest('repository validation dependency unavailable under -S')
        budget=self.budget(max_requests=3,max_seconds=60)
        state,_=self.execute([response(page([repo()]))],advance_epoch=True,strict_replay=True,shared_budget=budget)
        schema=json.loads((Path(__file__).resolve().parents[1]/'schemas/github-candidate-scan.schema.json').read_text(encoding='utf-8'))
        self.assertFalse(list(jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).iter_errors(state)))
        copy_state=copy.deepcopy(state);copy_state['schema_version']=1
        self.assertTrue(list(jsonschema.Draft202012Validator(schema).iter_errors(copy_state)))


if __name__=='__main__':unittest.main()
