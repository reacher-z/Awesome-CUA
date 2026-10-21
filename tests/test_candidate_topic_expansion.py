"""Exact query vocabulary additions retain historical coverage and bounded continuation."""
import copy
import json
from pathlib import Path
import shutil
import unittest
from unittest import mock
from urllib.parse import urlencode

import test_github_candidate_scan as fixtures
import candidate_state
import export_candidates
from network_budget import RoundBudget

scan = fixtures.scan
repo, page, response = fixtures.repo, fixtures.page, fixtures.response
ROOT = Path(__file__).resolve().parents[1]
OLD_TOPICS = [
    'computer-use', 'gui-agent', 'gui-agents', 'gui-automation',
    'desktop-automation', 'browser-agent', 'browser-agents',
    'browser-automation', 'android-automation',
]
ADDED_TOPICS = [
    'computer-use-agent', 'computer-use-agents', 'gui-grounding',
    'browser-use', 'web-agent', 'web-agents', 'desktop-agent', 'mobile-agent',
]
EXPANDED_TOPICS = OLD_TOPICS + ADDED_TOPICS


class CandidateTopicExpansionTests(unittest.TestCase):
    setUp = fixtures.ScanTests.setUp
    write_inputs = fixtures.ScanTests.write_inputs

    def execute(self, responses, **options):
        answers = iter(responses)

        def fetch(url, timeout):
            self.calls.append((url, timeout))
            return next(answers)

        args = {
            'max_requests': len(responses) or 1, 'max_seconds': 220,
            'existing_budget': 0, 'topics': OLD_TOPICS,
            'strict_replay': True, 'advance_epoch': True,
            'fetcher': fetch, 'clock': self.timer.clock,
            'sleep': self.timer.sleep, 'now': self.timer.now,
        }
        if not (self.output / 'candidate-metadata.json').exists():
            args.update(created_after='2008-01-01', created_before='2026-10-18')
        args.update(options)
        with mock.patch.object(scan, 'budget_from_environment', return_value=None), \
                mock.patch('socket.create_connection', side_effect=AssertionError('Network forbidden')):
            return scan.run_scan(self.root, self.output, **args)

    def historical_gaps_and_frontier(self):
        # Retain both a partial traversal and a split tree with unvisited children.
        self.execute([
            response(page([repo(1)], incomplete=True)),
            response(page([repo(2)], 1000)),
        ])
        self.timer.sleep(86400)
        current, _ = self.execute([response(page([]))])
        self.assertEqual(current['configuration']['created_after'], '2026-10-18')
        self.assertEqual(current['configuration']['created_before'], '2026-10-19')
        self.assertTrue(any(q.get('parent_id') for q in current['queries']))
        return current

    def budget(self, requests):
        return RoundBudget.create(
            self.root / '.cache/budgets', max_requests=requests, max_seconds=220,
            clock=self.timer.clock, sleep=self.timer.sleep,
            now=lambda: scan.timestamp(self.timer.now()),
        )

    def test_exact_added_topics_are_public_queries_not_generic_searches(self):
        config = json.loads((ROOT / 'data/scan-config.json').read_text(encoding='utf-8'))
        self.assertEqual(config['github_candidate_topics'], EXPANDED_TOPICS)
        self.assertEqual(
            tuple(config[key] for key in (
                'github_candidate_max_requests', 'github_candidate_max_seconds',
                'github_candidate_existing_budget', 'network_max_requests', 'network_max_seconds',
            )),
            (30, 220, 5, 180, 600),
        )
        for topic in ADDED_TOPICS:
            query = scan.search_query(topic, '2008-01-01', '2026-10-20')['query']
            url = 'https://api.github.com/search/repositories?' + urlencode({
                'q': query, 'per_page': 100, 'page': 1, 'sort': 'updated', 'order': 'asc',
            })
            self.assertEqual(scan.safe_api_url(url), url)
        for query in (
            'topic:ai-agent is:public fork:false created:2008-01-01..2026-10-20',
            'topic:automation is:public fork:false created:2008-01-01..2026-10-20',
            'computer-use-agent in:readme is:public fork:false',
        ):
            with self.subTest(query=query), self.assertRaises(ValueError):
                scan.safe_api_url('https://api.github.com/search/repositories?' + urlencode({
                    'q': query, 'per_page': 100, 'page': 1, 'sort': 'updated', 'order': 'asc',
                }))

    def test_additions_after_frontier_backfill_original_dates_without_resetting_history(self):
        current = self.historical_gaps_and_frontier()
        original = copy.deepcopy(current)
        expanded = scan.expand_topics(current, EXPANDED_TOPICS, at=self.timer.now())
        self.assertEqual(current, original)
        for key in ('records', 'receipts', 'runs', 'inputs', 'query_rechecks'):
            self.assertEqual(expanded[key], original[key])
        self.assertEqual(expanded['epochs'][:-1], original['epochs'])
        self.assertEqual(expanded['queries'][:len(original['queries'])], original['queries'])
        added = expanded['queries'][len(original['queries']):]
        self.assertEqual([q['topic'] for q in added], ADDED_TOPICS)
        self.assertTrue(all(q['created_after'] == '2008-01-01'
                            and q['created_before'] == '2026-10-19'
                            and q['next_page'] == 1 and q['status'] == 'pending'
                            for q in added))
        self.assertEqual(expanded['epochs'][-1]['reason'], 'topic_expansion')
        self.assertEqual(expanded['epochs'][-1]['root_query_ids'][:len(OLD_TOPICS)],
                         original['epochs'][-1]['root_query_ids'])
        self.assertEqual(
            scan.expand_topics(expanded, EXPANDED_TOPICS, at='2026-10-20T00:00:00Z'),
            expanded,
        )
        scan.validate_state(expanded)

    def test_fresh_checkout_can_stage_expansion_without_old_raw_or_new_gets(self):
        current = self.historical_gaps_and_frontier()
        ledger = export_candidates.encoded(current)
        catalog = b'{"id":"github:example/active"}\n'
        body, manifest = export_candidates.build_candidate_export(
            ledger, self.output / 'raw', catalog,
        )
        pair = self.root / 'pair'
        export_candidates.write_pair(pair, body, manifest)
        bound = self.root / 'bound'
        candidate_state.bootstrap_from_ledger(
            ledger, self.output / 'raw', pair, bound, catalog_bytes=catalog,
        )
        baseline = candidate_state.load_snapshot(bound)
        shutil.rmtree(self.output / 'raw')
        self.output = self.root / '.cache/fresh-runtime'
        candidate_state.prepare_runtime(baseline, self.output)
        self.assertEqual(list((self.output / 'raw').glob('*.body')), [])
        budget = self.budget(1)
        url = 'https://api.github.com/repos/public-owner/prior-attempt'
        reservation = budget.reserve(url)
        budget.observe_response(url, 200, attempt=reservation)
        before_calls = len(self.calls)
        expanded, run = self.execute(
            [], topics=EXPANDED_TOPICS, max_requests=30, shared_budget=budget,
        )
        self.assertEqual(len(self.calls), before_calls)
        self.assertEqual(run['requests_attempted'], 0)
        self.assertEqual(run['status'], 'request_budget')
        self.assertEqual(expanded['records'], baseline.state['records'])
        self.assertEqual(expanded['receipts'], baseline.state['receipts'])
        staged_dir = self.root / 'staged'
        result = candidate_state.finalize_runtime(
            baseline, self.output, staged_dir, catalog_bytes=catalog,
        )
        staged = candidate_state.load_snapshot(staged_dir, catalog_bytes=catalog)
        self.assertEqual(staged.payloads[export_candidates.RECORD_FILE],
                         baseline.payloads[export_candidates.RECORD_FILE])
        self.assertEqual(result['verification']['primary_bodies_replayed'], 0)
        self.assertFalse(result['verification']['historical_raw_replayed'])
        new_queries = [q for q in staged.state['queries'] if q.get('topic') in ADDED_TOPICS]
        self.assertEqual(len(new_queries), len(ADDED_TOPICS))
        self.assertTrue(all(q['created_after'] == '2008-01-01'
                            and q['created_before'] == '2026-10-19'
                            for q in new_queries))
        try:
            import jsonschema
        except ImportError:
            self.skipTest('repository validation dependency unavailable')
        payloads = [
            ('github-candidate-scan.schema.json', expanded),
            ('github-candidate-progress.schema.json',
             json.loads(staged.payloads[candidate_state.PROGRESS_FILE])),
            ('github-candidate-observation-manifest.schema.json', staged.manifest),
        ]
        for name, payload in payloads:
            schema = json.loads((ROOT / 'schemas' / name).read_text(encoding='utf-8'))
            jsonschema.Draft202012Validator(
                schema, format_checker=jsonschema.FormatChecker(),
            ).validate(payload)

    def test_new_topic_overlap_counts_once_and_cannot_exceed_shared_allowance(self):
        # Finish the old roots so the next same-day invocation reaches new backfills.
        prior, _ = self.execute([response(page([])) for _ in OLD_TOPICS])
        budget = self.budget(2)
        item = repo(70001, topics=ADDED_TOPICS)
        catalog_before = (self.root / 'data/catalog.jsonl').read_bytes()
        state, run = self.execute(
            [response(page([item])), response(page([item]))],
            topics=EXPANDED_TOPICS, max_requests=30, existing_budget=5,
            shared_budget=budget,
        )
        new_receipts = state['receipts'][len(prior['receipts']):]
        self.assertEqual(len(new_receipts), 2)
        self.assertEqual(run['requests_attempted'], 2)
        self.assertEqual(run['accepted_metadata_rows'], 2)
        self.assertEqual(run['new_unique_repositories'], 1)
        self.assertEqual(run['status'], 'request_budget')
        self.assertEqual(budget.summary()['requests_reserved'], 2)
        self.assertEqual(len(state['records']), 1)
        record = next(iter(state['records'].values()))
        self.assertEqual(record['review_status'], 'candidate')
        self.assertEqual(record['scope'], 'relevance_pending')
        self.assertEqual(len(record['occurrences']), 2)
        self.assertEqual((self.root / 'data/catalog.jsonl').read_bytes(), catalog_before)
        query_topics = {q['id']: q.get('topic') for q in state['queries']}
        self.assertEqual([query_topics[r['query_id']] for r in new_receipts], ADDED_TOPICS[:2])
        scan.validate_state(state)


if __name__ == '__main__':
    unittest.main()
