"""Public-only, bounded candidate harvesting; fixtures never approve resources."""
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import scan_github_candidates as scan


def repo(number=1, name=None, **overrides):
    name = name or f'public-owner/repo-{number}'
    return {'id': number, 'full_name': name, 'html_url': 'https://github.com/' + name,
            'private': False, 'visibility': 'public', 'fork': False, 'archived': False,
            'description': 'A public GUI observation and control tool.',
            'topics': ['browser-automation', 'computer-use', 'gui-agent'],
            'created_at': '2024-01-01T00:00:00Z', 'updated_at': '2026-10-18T00:00:00Z',
            'pushed_at': None, **overrides}


def page(items, total=None, incomplete=False):
    return {'total_count': len(items) if total is None else total,
            'incomplete_results': incomplete, 'items': items}


def response(value, status=200, headers=None):
    return status, (value if isinstance(value, bytes) else json.dumps(value).encode()), headers or {}


class Timer:
    def __init__(self): self.seconds = 0
    def clock(self): return self.seconds
    def sleep(self, seconds): self.seconds += seconds
    def now(self): return (datetime(2026, 10, 18, tzinfo=timezone.utc) + timedelta(seconds=self.seconds)).isoformat()


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'data').mkdir()
        self.output = self.root / '.cache' / 'pilot'
        self.timer = Timer()
        self.calls = []
        self.write_inputs()

    def write_inputs(self, candidates=(), primary=(), catalog=()):
        for name, rows in [('catalog.jsonl', catalog), ('candidates.jsonl', candidates), ('primary-evidence.jsonl', primary)]:
            (self.root / 'data' / name).write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
        for name in ['repository-aliases.json', 'candidate-reviews.json']:
            (self.root / 'data' / name).write_text('[]\n', encoding='utf-8')

    def execute(self, responses, **kwargs):
        responses = iter(responses)
        def fetch(url, timeout):
            self.calls.append((url, timeout))
            return next(responses)
        options = {'max_requests': 1, 'existing_budget': 0, 'topics': ['browser-automation'],
                   'created_after': '2024-01-01', 'created_before': '2024-01-04',
                   'fetcher': fetch, 'clock': self.timer.clock, 'sleep': self.timer.sleep, 'now': self.timer.now}
        options.update(kwargs)
        return scan.run_scan(self.root, self.output, **options)

    def ledger_bytes(self): return (self.output / 'candidate-metadata.json').read_bytes()

    def test_numeric_identity_deduplicates_query_occurrences_and_names(self):
        state, run = self.execute([response(page([repo(7, 'old-owner/gui')])), response(page([repo(7, 'new-owner/gui')]))],
                                  max_requests=2, topics=['browser-automation', 'computer-use'])
        self.assertEqual(len(state['records']), 1)
        row = state['records']['github-repository:7']
        self.assertEqual(row['full_name'], 'new-owner/gui')
        self.assertEqual(row['known_names'], ['new-owner/gui', 'old-owner/gui'])
        self.assertEqual(len(row['occurrences']), 2)
        self.assertEqual(run['new_unique_repositories'], 1)
        self.assertEqual(run['accepted_metadata_rows'], 2)
        self.assertEqual(row['review_status'], 'candidate')
        self.assertEqual(row['scope'], 'relevance_pending')
        for url, _ in self.calls:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['q'][0]
            self.assertIn('is:public fork:false', query)

    def test_private_unknown_and_fork_rows_do_not_leak_into_ledger_or_raw_cache(self):
        unsafe = [repo(2, 'SECRET/private', private=True), repo(3, 'SECRET/unknown', visibility=None),
                  repo(4, 'SECRET/missing', private=None), repo(5, 'SECRET/fork', fork=True)]
        state, run = self.execute([response(page([repo(), *unsafe]))])
        self.assertEqual(len(state['records']), 1)
        self.assertEqual(sum(run['rejected_rows'].values()), 4)
        self.assertNotIn(b'SECRET', self.ledger_bytes())
        self.assertFalse((self.output / 'raw').exists())
        receipt = state['receipts'][0]
        self.assertIsNone(receipt['source_url'])
        self.assertFalse(receipt['raw_body_retained'])
        self.assertEqual(receipt['response_sha256'], hashlib.sha256(response(page([repo(), *unsafe]))[1]).hexdigest())

    def test_metadata_types_and_canonical_urls_are_strict(self):
        changes = [{'id': True}, {'private': 0}, {'fork': 0}, {'archived': 0}, {'full_name': '../private'},
                   {'html_url': 'http://localhost/private'}, {'html_url': 'https://user:secret@github.com/public-owner/repo-1'},
                   {'created_at': '2024-01-01'}, {'topics': ['bad topic']}, {'description': {'token': 'secret'}}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(scan.Rejected): scan.repository_metadata(repo(**change))

    def test_ledger_allowlist_omits_contact_permissions_and_response_headers(self):
        item = repo(owner={'email': 'not-needed@example.org'}, permissions={'admin': True}, clone_url='unused')
        state, _ = self.execute([response(page([item]), headers={'Authorization': 'SECRET', 'Cookie': 'SECRET'})])
        text = self.ledger_bytes().decode()
        for forbidden in ['not-needed@example.org', 'permissions', 'clone_url', 'Authorization', 'Cookie', 'SECRET']:
            self.assertNotIn(forbidden, text)
        receipt = state['receipts'][0]
        self.assertEqual((self.output / 'raw' / (receipt['response_sha256'] + '.body')).read_bytes(), response(page([item]))[1])

    def test_malformed_search_response_cannot_create_resources_or_advance_page(self):
        invalid = [b'{', b'{"total_count":0,"total_count":1,"incomplete_results":false,"items":[]}',
                   page([], total=True), page([], incomplete=0), [], {'total_count': 1, 'incomplete_results': False, 'items': {}},
                   page([repo()], total=0)]
        for index, payload in enumerate(invalid):
            with self.subTest(index=index):
                self.output = self.root / '.cache' / f'invalid-{index}'
                state, run = self.execute([response(payload)])
                self.assertFalse(state['records'])
                self.assertEqual(state['receipts'][0]['outcome'], 'malformed_response')
                self.assertEqual(next(q for q in state['queries'] if q['kind'] == 'search')['next_page'], 1)
                self.assertEqual(run['unknown_requests'], 1)

    def test_request_budget_and_resume_retain_first_page(self):
        first = [repo(i) for i in range(1, 101)]
        state, run = self.execute([response(page(first, 101))])
        self.assertEqual(run['status'], 'request_budget')
        self.assertEqual(run['requests_attempted'], 1)
        self.assertEqual(len(state['records']), 100)
        old_receipt = copy.deepcopy(state['receipts'][0])
        state, run = self.execute([response(page([repo(101)], 101))])
        self.assertIn('page=2', self.calls[-1][0])
        self.assertEqual(len(state['records']), 101)
        self.assertEqual(run['new_unique_repositories'], 1)
        self.assertEqual(state['receipts'][0], old_receipt)
        query = next(q for q in state['queries'] if q['kind'] == 'search')
        self.assertEqual(query['status'], 'observed_pages_exhausted')

    def test_wall_budget_defers_without_an_extra_request(self):
        state, run = self.execute([response(page([repo()]))], max_requests=2,
                                  topics=['browser-automation', 'computer-use'], max_seconds=6)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(run['status'], 'wall_budget')
        self.assertEqual(run['deferred_queries'], 1)
        self.assertEqual(len(run['deferred_query_ids']), 1)

    def test_rate_limit_preserves_success_and_defers_provider_on_resume(self):
        state, run = self.execute([response(page([repo()])), response({'message': 'SECRET'}, 429, {'Retry-After': '120'})],
                                  max_requests=3, topics=['browser-automation', 'computer-use', 'gui-agent'])
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(run['status'], 'rate_limited')
        self.assertEqual(len(state['records']), 1)
        self.assertNotIn(b'SECRET', self.ledger_bytes())
        self.assertIsNone(state['receipts'][-1]['source_url'])
        state, run = self.execute([], max_requests=3, topics=['browser-automation', 'computer-use', 'gui-agent'])
        self.assertEqual(run['requests_attempted'], 0)
        self.timer.sleep(121)
        state, run = self.execute([response(page([repo(2)])), response(page([repo(3)]))], max_requests=2,
                                  topics=['browser-automation', 'computer-use', 'gui-agent'])
        self.assertEqual(len(state['records']), 3)

    def test_rate_limit_403_stops_but_plain_unavailable_403_does_not(self):
        state, run = self.execute([response({}, 403, {'X-RateLimit-Remaining': '0'})], max_requests=3,
                                  topics=['browser-automation', 'computer-use'])
        self.assertEqual(run['status'], 'rate_limited'); self.assertEqual(len(self.calls), 1)
        self.output = self.root / '.cache' / 'plain-403'
        state, run = self.execute([response({}, 403), response(page([repo()]))], max_requests=2,
                                  topics=['browser-automation', 'computer-use'])
        self.assertEqual(run['requests_attempted'], 2)
        self.assertEqual(len(state['records']), 1)

    def test_large_query_splits_fixed_created_date_bounds_and_resumes(self):
        state, run = self.execute([response(page([repo()], 5236))])
        query = next(q for q in state['queries'] if q['kind'] == 'search' and q['parent_id'] is None)
        self.assertEqual(query['status'], 'split')
        children = [q for q in state['queries'] if q.get('parent_id') == query['id']]
        self.assertEqual([(q['created_after'], q['created_before']) for q in children], [('2024-01-01', '2024-01-02'), ('2024-01-03', '2024-01-04')])
        self.assertEqual(run['deferred_queries'], 2)
        state, run = self.execute([response(page([repo()])), response(page([repo(2, created_at='2024-01-03T00:00:00Z')]))], max_requests=2)
        self.assertEqual(len(state['records']), 2)
        self.assertEqual(run['new_unique_repositories'], 1)
        self.assertTrue(all('sort=updated' in url and 'sort=created' not in url for url, _ in self.calls))

    def test_single_day_above_window_remains_blocked_not_complete(self):
        state, run = self.execute([response(page([repo()], 1100))], created_before='2024-01-01')
        query = next(q for q in state['queries'] if q['kind'] == 'search')
        self.assertEqual(query['status'], 'blocked_single_day_window')
        self.assertEqual(run['status'], 'partial')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(state['receipts'][0]['reported_total'], 1100)

    def test_incomplete_results_or_duplicate_pages_never_claim_completion(self):
        state, run = self.execute([response(page([repo()], incomplete=True))])
        self.assertEqual(next(q for q in state['queries'] if q['kind'] == 'search')['status'], 'partial_results')
        self.output = self.root / '.cache' / 'duplicates'
        state, run = self.execute([response(page([repo()] * 100, 101)), response(page([repo()], 101))], max_requests=2)
        self.assertEqual(len(state['records']), 1)
        self.assertEqual(next(q for q in state['queries'] if q['kind'] == 'search')['status'], 'partial_results')

    def test_changing_total_is_visible_even_when_final_count_matches(self):
        state, run = self.execute([response(page([repo(i) for i in range(1, 101)], 101)),
                                  response(page([repo(101), repo(102)], 102))], max_requests=2)
        query = next(q for q in state['queries'] if q['kind'] == 'search')
        self.assertTrue(query['total_changed']); self.assertEqual(query['status'], 'partial_results')
        self.assertEqual([r['reported_total'] for r in state['receipts']], [101, 102])

    def test_existing_seed_priority_skips_successful_primary(self):
        def candidate(name, refs): return {'id': 'github:' + name, 'provider': 'github', 'url': 'https://github.com/' + name, 'discovered_in': [{'source_id': str(i)} for i in range(refs)]}
        self.write_inputs([candidate('public-owner/already', 9), candidate('public-owner/high', 5), candidate('public-owner/low', 1)],
                          primary=[{'id': 'github:public-owner/already', 'ok': True, 'status': 200}])
        state, run = self.execute([response(repo(1, 'public-owner/high')), response(page([repo(2)]))], max_requests=2, existing_budget=1)
        self.assertTrue(self.calls[0][0].endswith('/repos/public-owner/high'))
        self.assertIn('/search/repositories?', self.calls[1][0])
        self.assertEqual(state['inputs'][0]['active_records'], 0)
        self.assertEqual(state['inputs'][0]['existing_seed_count'], 2)

    def test_failed_response_never_overwrites_previous_metadata_or_body(self):
        state, _ = self.execute([response(page([repo(i) for i in range(1, 101)], 101))])
        old = copy.deepcopy(state['records'])
        raw = {p.name: p.read_bytes() for p in (self.output / 'raw').glob('*')}
        state, run = self.execute([response(b'{"message":"SECRET private repo"}', 404)])
        self.assertEqual(state['records'], old)
        self.assertEqual({p.name: p.read_bytes() for p in (self.output / 'raw').glob('*')}, raw)
        self.assertNotIn(b'SECRET', self.ledger_bytes())
        self.assertEqual(run['new_unique_repositories'], 0)

    def test_redirect_is_not_followed_or_stored_as_an_unverified_url(self):
        state, run = self.execute([response({'url': 'http://localhost/SECRET'}, 301, {'Location': 'http://localhost/SECRET'})])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(state['receipts'][0]['outcome'], 'redirect_not_followed')
        self.assertNotIn(b'localhost', self.ledger_bytes()); self.assertNotIn(b'SECRET', self.ledger_bytes())

    def test_settled_existing_answers_neither_stall_the_lane_nor_repeat_in_later_cohorts(self):
        def candidate(name, refs): return {'id': 'github:' + name, 'provider': 'github', 'url': 'https://github.com/' + name,
                                           'discovered_in': [{'source_id': str(i)} for i in range(refs)]}
        seeds = [candidate('public-owner/moved', 4), candidate('public-owner/gone', 3), candidate('public-owner/live', 2)]
        options = {'max_requests': 3, 'existing_budget': 3, 'strict_replay': True}
        names = lambda: [url.rsplit('/', 1)[-1] for url, _ in self.calls]
        self.write_inputs(seeds)
        # A rename and a deletion each answer for one name; the lane continues past them in the same run.
        state, run = self.execute([response({'message': 'Moved Permanently'}, 301), response({'message': 'Not Found'}, 404),
                                   response(repo(3, 'public-owner/live'))], **options)
        self.assertEqual(names(), ['moved', 'gone', 'live'])
        self.assertEqual([r['outcome'] for r in state['receipts']], ['redirect_not_followed', 'unavailable', 'accepted'])
        self.assertEqual(run['unknown_requests'], 2)
        self.assertEqual(scan.settled_unknown_requests(state['receipts'], run['id']), 2)
        # Every scan changes the catalog, so a new cohort restarts at index 0: it asks none of the settled names again.
        self.write_inputs(seeds, catalog=[{'id': 'github:public-owner/other', 'review_status': 'curated'}])
        self.calls.clear()
        state, run = self.execute([response(page([]))], **options)
        self.assertEqual(len(self.calls), 1)
        self.assertIn('/search/repositories?', self.calls[0][0])
        self.assertEqual(run['unknown_requests'], 0)
        cohort = next(q for q in state['queries'] if q['id'] == 'existing:' + run['input_id'])
        self.assertEqual((cohort['next_index'], cohort['status']), (3, 'exhausted'))
        # After the recheck window the names are asked again; a transient failure never settles a name.
        self.timer.seconds += 31 * 86400
        self.write_inputs(seeds, catalog=[{'id': 'github:public-owner/other-2', 'review_status': 'curated'}])
        self.calls.clear()
        state, run = self.execute([response({'message': 'Server Error'}, 502)], **options)
        self.assertEqual((names(), run['unknown_requests'], scan.settled_unknown_requests(state['receipts'], run['id'])), (['moved'], 1, 0))
        self.write_inputs(seeds, catalog=[{'id': 'github:public-owner/other-3', 'review_status': 'curated'}])
        self.calls.clear()
        state, run = self.execute([response(repo(1, 'public-owner/moved')), response({'message': 'Not Found'}, 404)], **options)
        self.assertEqual(names(), ['moved', 'gone'])
        self.assertIn('github-repository:1', state['records'])

    def test_a_quarantined_direct_answer_is_retried_rather_than_settled(self):
        self.write_inputs([{'id': 'github:public-owner/forked', 'url': 'https://github.com/public-owner/forked', 'provider': 'github',
                            'discovered_in': [{'source_id': 'a'}]},
                           {'id': 'github:public-owner/next', 'url': 'https://github.com/public-owner/next', 'provider': 'github',
                            'discovered_in': []}])
        state, run = self.execute([response(repo(5, 'public-owner/forked', fork=True))], max_requests=1, existing_budget=1, strict_replay=True)
        self.assertEqual(([r['outcome'] for r in state['receipts']], len(self.calls)), (['quarantined'], 1))
        self.assertEqual(scan.settled_seed_requests(state, self.timer.now()), set())
        self.write_inputs([{'id': 'github:public-owner/forked', 'url': 'https://github.com/public-owner/forked', 'provider': 'github',
                            'discovered_in': [{'source_id': 'a'}]}], catalog=[{'id': 'github:public-owner/other', 'review_status': 'curated'}])
        self.execute([response(repo(5, 'public-owner/forked'))], max_requests=1, existing_budget=1, strict_replay=True)
        self.assertTrue(self.calls[-1][0].endswith('/repos/public-owner/forked'))

    def test_input_changes_create_new_seed_fingerprint_without_losing_records(self):
        state, _ = self.execute([response(page([repo()]))])
        old_input = state['inputs'][0]['id']
        self.write_inputs(catalog=[{'id': 'github:public-owner/repo-1', 'review_status': 'curated'}])
        state, run = self.execute([])
        self.assertEqual(len(state['inputs']), 2)
        self.assertNotEqual(old_input, run['input_id'])
        self.assertEqual(state['inputs'][-1]['active_records'], 1)
        self.assertEqual(len(state['records']), 1)

    def test_snapshot_a_b_a_restores_current_cursor_and_receipt_context(self):
        def candidates(prefix):
            return [{'id': f'github:public-owner/{prefix}{i}', 'url': f'https://github.com/public-owner/{prefix}{i}',
                     'provider': 'github', 'discovered_in': []} for i in (1, 2)]
        self.write_inputs(candidates('a'))
        state, run = self.execute([response({}, 404)], existing_budget=1)
        a_input = run['input_id']
        self.write_inputs(candidates('b'))
        state, run = self.execute([response({}, 404)], existing_budget=1)
        b_input = run['input_id']
        self.write_inputs(candidates('a'))
        state, run = self.execute([response(repo(2, 'public-owner/a2'))], existing_budget=1)
        self.assertTrue(self.calls[-1][0].endswith('/repos/public-owner/a2'))
        self.assertEqual(run['input_id'], a_input)
        self.assertEqual(state['receipts'][-1]['query_id'], 'existing:' + a_input)
        self.assertEqual(state['receipts'][-1]['position'], 1)
        a_query = next(q for q in state['queries'] if q['id'] == 'existing:' + a_input)
        b_query = next(q for q in state['queries'] if q['id'] == 'existing:' + b_input)
        self.assertEqual((a_query['next_index'], a_query['status']), (2, 'exhausted'))
        self.assertEqual((b_query['next_index'], b_query['status']), (1, 'superseded_input'))
        # A finished cursor must not reset when that input is revisited again.
        self.execute([response(page([]))], existing_budget=1)
        self.assertIn('/search/repositories?', self.calls[-1][0])

    def test_seed_count_must_match_retained_and_current_input(self):
        candidate = {'id': 'github:public-owner/a', 'url': 'https://github.com/public-owner/a',
                     'provider': 'github', 'discovered_in': []}
        self.write_inputs([candidate])
        state, _ = self.execute([response({}, 404)], existing_budget=1)
        count = len(self.calls)
        for change_input_too in (False, True):
            with self.subTest(change_input_too=change_input_too):
                altered = copy.deepcopy(state)
                next(q for q in altered['queries'] if q['kind'] == 'existing')['seed_count'] += 1
                if change_input_too:
                    altered['inputs'][0]['existing_seed_count'] += 1
                (self.output / 'candidate-metadata.json').write_text(json.dumps(altered), encoding='utf-8')
                with self.assertRaises(ValueError): self.execute([], existing_budget=1)
                self.assertEqual(len(self.calls), count)

    def test_direct_endpoint_requires_requested_identity_but_allows_case(self):
        candidate = {'id': 'github:public-owner/requested', 'url': 'https://github.com/public-owner/requested',
                     'provider': 'github', 'discovered_in': []}
        self.write_inputs([candidate])
        state, run = self.execute([response(repo(3, 'SECRET/unrequested'))], existing_budget=1)
        self.assertFalse(state['records'])
        self.assertEqual(run['rejected_rows'], {'requested_repository_mismatch': 1})
        self.assertEqual(state['receipts'][-1]['outcome'], 'rejected')
        self.assertIsNone(state['receipts'][-1]['source_url'])
        self.assertNotIn(b'SECRET', self.ledger_bytes())
        self.assertFalse((self.output / 'raw').exists())
        self.output = self.root / '.cache' / 'case-only'
        state, run = self.execute([response(repo(3, 'Public-Owner/Requested'))], existing_budget=1)
        self.assertEqual(run['new_unique_repositories'], 1)
        self.assertEqual(state['records']['github-repository:3']['full_name'], 'Public-Owner/Requested')

    def test_standard_403_message_stops_provider_without_rate_limit_headers(self):
        messages = ['API rate limit exceeded for SECRET.',
                    'You have exceeded a secondary rate limit. SECRET',
                    'You have triggered an abuse detection mechanism. SECRET']
        for index, message in enumerate(messages):
            with self.subTest(message=message):
                self.output = self.root / '.cache' / f'body-limit-{index}'
                before_calls = len(self.calls)
                state, run = self.execute([response({'message': message}, 403, {'X-RateLimit-Remaining': '12'})],
                                          max_requests=2, topics=['browser-automation', 'computer-use'])
                self.assertEqual(len(self.calls) - before_calls, 1)
                self.assertEqual(run['status'], 'rate_limited')
                self.assertGreater(scan.timestamp(state['deferred_until']), scan.timestamp(self.timer.now()))
                self.assertEqual(run['deferred_queries'], 2)
                self.assertNotIn(b'SECRET', self.ledger_bytes())
                self.assertFalse((self.output / 'raw').exists())
        for body in (b'{', b'{"message":["API rate limit exceeded"]}', b'{"message":"Resource not accessible by integration"}'):
            self.assertFalse(scan.rate_limited(403, {}, body))

    def test_occurrences_and_accepted_ids_are_bidirectionally_bound(self):
        state, _ = self.execute([response(page([repo(7)])), response(page([repo(8)]))],
                                max_requests=2, topics=['browser-automation', 'computer-use'])
        mutations = [
            lambda s: s['receipts'][0].update(accepted_repository_ids=[999]),
            lambda s: s['receipts'][0].update(accepted_repository_ids=[7, 8]),
            lambda s: s['records']['github-repository:7']['occurrences'][0].update(query_id=s['receipts'][1]['query_id']),
            lambda s: s['records']['github-repository:7']['occurrences'][0].update(position=2),
            lambda s: s['receipts'][0].update(request_url_sha256='0' * 64),
            lambda s: s['records']['github-repository:7'].update(occurrences=[]),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                altered = copy.deepcopy(state); mutation(altered)
                with self.assertRaises(ValueError): scan.validate_state(altered)

    def test_existing_receipt_cannot_belong_to_a_different_run_input(self):
        def candidate(name): return {'id': 'github:' + name, 'url': 'https://github.com/' + name,
                                     'provider': 'github', 'discovered_in': []}
        self.write_inputs([candidate('public-owner/a')])
        self.execute([response(repo(1, 'public-owner/a'))], existing_budget=1)
        self.write_inputs([candidate('public-owner/b')])
        state, _ = self.execute([response(repo(2, 'public-owner/b'))], existing_budget=1)
        state['runs'][0]['input_id'] = state['runs'][1]['input_id']
        with self.assertRaisesRegex(ValueError, 'different input snapshot'): scan.validate_state(state)

    def test_scheduler_oversleep_cannot_start_request_after_deadline(self):
        def oversleep(seconds): self.timer.sleep(seconds + 10)
        state, run = self.execute([response(page([])), response(page([]))], max_requests=2,
                                  max_seconds=8, topics=['browser-automation', 'computer-use'], sleep=oversleep)
        self.assertEqual(self.timer.seconds, 16.5)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(run['requests_attempted'], 1)
        self.assertEqual(run['status'], 'wall_budget')
        self.assertEqual(run['deferred_queries'], 1)

    def test_unsafe_url_and_output_paths_fail_before_transport(self):
        urls = ['https://user:password@api.github.com/repos/o/r', 'https://api.github.com/repos/o/r?token=SECRET',
                'http://api.github.com/repos/o/r', 'https://api.github.com/user/repos', 'https://localhost/repos/o/r']
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError): scan.safe_api_url(url)
        with self.assertRaises(ValueError): scan.checked_output(self.root / '.cache' / '..' / 'data')
        (self.root / 'link').symlink_to(self.root / 'data', target_is_directory=True)
        with self.assertRaises(ValueError): scan.checked_output(self.root / 'link' / 'ledger')

    def test_corrupted_resume_state_is_rejected_before_any_request(self):
        state, _ = self.execute([response(page([repo()]))])
        mutations = [lambda s: s.update(schema_version=True),
                     lambda s: s['records']['github-repository:1'].update(private=True),
                     lambda s: s['receipts'][0].update(Authorization='SECRET'),
                     lambda s: s['records']['github-repository:1'].update(review_status='curated')]
        before_calls = len(self.calls)
        for mutation in mutations:
            changed = copy.deepcopy(state); mutation(changed)
            (self.output / 'candidate-metadata.json').write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaises(ValueError): self.execute([])
        self.assertEqual(len(self.calls), before_calls)

    def test_query_bound_change_requires_explicit_new_epoch(self):
        self.execute([response(page([repo()]))])
        with self.assertRaises(ValueError): self.execute([], created_before='2024-01-05')

    def test_out_of_partition_and_wrong_topic_rows_are_not_counted(self):
        state, run = self.execute([response(page([repo(1, created_at='2025-01-01T00:00:00Z'), repo(2, topics=['unrelated'])]))])
        self.assertFalse(state['records'])
        self.assertEqual(run['rejected_rows'], {'outside_created_bounds': 1, 'query_topic_mismatch': 1})

    def test_real_transport_builds_no_auth_cookie_or_redirect_request(self):
        response_obj = mock.MagicMock()
        response_obj.__enter__.return_value = response_obj
        response_obj.status = 200; response_obj.read.return_value = b'{}'; response_obj.headers = {}
        opener = mock.Mock(); opener.open.return_value = response_obj
        with mock.patch.object(scan.urllib.request, 'build_opener', return_value=opener) as build:
            scan.public_get('https://api.github.com/repos/public-owner/tool', 10)
        request = opener.open.call_args.args[0]
        self.assertEqual(set(k.lower() for k, _ in request.header_items()), {'user-agent', 'accept'})
        self.assertTrue(any(isinstance(h, scan.NoRedirect) for h in build.call_args.args))
        self.assertIsNone(scan.NoRedirect().redirect_request(request, None, 301, '', {}, 'https://api.github.com/repos/elsewhere/private'))

    def test_schema_accepts_real_ledger_and_rejects_approval_and_private(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('JSON Schema check uses the repository validation dependency; scanner itself is stdlib-only')
        state, _ = self.execute([response(page([repo()]))])
        schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas/github-candidate-scan.schema.json').read_text(encoding='utf-8'))
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        self.assertFalse(list(validator.iter_errors(state)))
        for field, value in [('private', True), ('visibility', 'private'), ('review_status', 'curated')]:
            changed = copy.deepcopy(state); changed['records']['github-repository:1'][field] = value
            self.assertTrue(list(validator.iter_errors(changed)))


if __name__ == '__main__':
    unittest.main()
