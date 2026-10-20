"""Fresh-checkout candidate continuation without historical raw bodies."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import candidate_state as state
import export_candidates as export
import scan_github_candidates as scan
from test_candidate_exports import fixture
from test_github_candidate_scan import repo, page, response, Timer


class DurableCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.ledger, self.raw = fixture(self.root)
        self.ledger_bytes = export.encoded(self.ledger)
        self.catalog = b'{"id":"github:example/active"}\n'
        self.public = self.root / 'public'
        body, manifest = export.build_candidate_export(self.ledger_bytes, self.raw, self.catalog)
        export.write_pair(self.public, body, manifest)
        self.bound = self.root / 'bound'
        state.bootstrap_from_ledger(self.ledger_bytes, self.raw, self.public, self.bound, catalog_bytes=self.catalog)

    def files(self, directory):
        return {name: (directory / name).read_bytes() for name in state.FILES}

    def next_round(self, baseline, runtime, *, item=None, raw_response=None):
        state.prepare_runtime(baseline, runtime)
        item = item or repo(99, 'new-owner/gui')
        # A changed seed input is expected and retains prior query/history state.
        seed = {'id': 'github:' + item['full_name'].casefold(), 'url': item['html_url'],
                'provider': 'github', 'discovered_in': [{'source_id': 'fixture'}]}
        (self.root / 'data/candidates.jsonl').write_bytes(export.encoded(seed))
        timer = Timer(); timer.seconds = 100
        options = dict(max_requests=1, existing_budget=1, fetcher=lambda url, timeout: raw_response or response(item),
                       clock=timer.clock, sleep=timer.sleep, now=timer.now)
        import inspect
        if 'strict_replay' in inspect.signature(scan.run_scan).parameters: options['strict_replay'] = True
        return scan.run_scan(self.root, runtime, **options)

    def test_bootstrap_binds_pair_without_descriptions_or_records_in_checkpoint(self):
        baseline = state.load_snapshot(self.bound, catalog_bytes=self.catalog)
        self.assertEqual(baseline.payloads[export.RECORD_FILE], (self.public / export.RECORD_FILE).read_bytes())
        checkpoint = json.loads(baseline.payloads[state.PROGRESS_FILE])
        self.assertNotIn('records', checkpoint['state'])
        state._reject_private_structure(checkpoint['state'])
        self.assertEqual(checkpoint['manifest_sha256'], baseline.fingerprints[export.MANIFEST_FILE])
        self.assertEqual(checkpoint['state_sha256'], baseline.manifest['checkpoint_state_sha256'])
        self.assertEqual(baseline.manifest['verification']['mode'], 'full_retained_replay')

    def test_checkpoint_and_public_manifest_json_schemas(self):
        try: import jsonschema
        except ImportError: self.skipTest('jsonschema is the optional catalog validation dependency')
        baseline = state.load_snapshot(self.bound)
        for filename, payload in [('github-candidate-progress.schema.json', baseline.payloads[state.PROGRESS_FILE]),
                                  ('github-candidate-observation-manifest.schema.json', baseline.payloads[export.MANIFEST_FILE])]:
            schema = json.loads((ROOT / 'schemas' / filename).read_bytes())
            jsonschema.Draft202012Validator.check_schema(schema)
            jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(json.loads(payload))

    def test_checkpoint_contract_tracks_only_scanner_metadata(self):
        scanner = json.loads((ROOT / 'schemas/github-candidate-scan.schema.json').read_bytes())
        checkpoint = json.loads((ROOT / 'schemas/github-candidate-progress.schema.json').read_bytes())
        expected = {key: copy.deepcopy(scanner[key]) for key in ['type', 'required', 'properties', 'additionalProperties', 'allOf']}
        expected['required'].remove('records'); del expected['properties']['records']
        definitions = copy.deepcopy(scanner['$defs']); definitions.pop('record')
        self.assertEqual(checkpoint['properties']['state'], expected)
        self.assertEqual(checkpoint['$defs'], definitions)

    def test_missing_checkpoint_never_bootstraps_or_fetches_implicitly(self):
        with mock.patch.object(scan, 'public_get', side_effect=AssertionError('No network')):
            with self.assertRaisesRegex(state.CandidateStateError, 'bootstrap'):
                state.load_snapshot(self.public)
        self.assertFalse((self.public / state.PROGRESS_FILE).exists())

    def test_fresh_checkout_resume_uses_only_new_body_and_preserves_old_lines(self):
        clone = self.root / 'fresh-checkout'
        clone.mkdir()
        for name in state.FILES: shutil.copy2(self.bound / name, clone / name)
        baseline = state.load_snapshot(clone)
        shutil.rmtree(self.raw)
        runtime = self.root / 'runtime'
        current, run = self.next_round(baseline, runtime)
        self.assertEqual(len(list((runtime / 'raw').glob('*.body'))), 1)
        staged = self.root / 'staged'
        result = state.finalize_runtime(baseline, runtime, staged, catalog_bytes=self.catalog)
        updated = state.load_snapshot(staged)
        self.assertEqual(result['total_unique_repositories'], 3)
        self.assertEqual(result['requests_attempted'], 1)
        self.assertEqual(result['verification']['primary_bodies_replayed'], 1)
        self.assertIs(result['verification']['historical_raw_replayed'], False)
        self.assertEqual(updated.state['receipts'][:-1], baseline.state['receipts'])
        self.assertEqual(updated.state['runs'][:-1], baseline.state['runs'])
        for rid, line in baseline.lines.items(): self.assertEqual(updated.lines[rid], line)
        self.assertEqual(self.files(clone), baseline.payloads)

    def test_missing_new_raw_or_changed_old_history_preserves_staged_baseline(self):
        baseline = state.load_snapshot(self.bound); runtime = self.root / 'runtime'
        current, _ = self.next_round(baseline, runtime)
        staged = self.root / 'staged'; shutil.copytree(self.bound, staged); before = self.files(staged)
        raw = next((runtime / 'raw').glob('*.body')); raw.unlink()
        with self.assertRaises(ValueError): state.finalize_runtime(baseline, runtime, staged, catalog_bytes=self.catalog)
        self.assertEqual(self.files(staged), before)
        current['runs'][0]['finished_at'] = '2026-10-18T00:00:01Z'
        (runtime / 'candidate-metadata.json').write_bytes(export.encoded(current))
        with self.assertRaises(ValueError): state.finalize_runtime(baseline, runtime, staged, catalog_bytes=self.catalog)
        self.assertEqual(self.files(staged), before)

    def test_cursor_changes_cannot_be_hidden_by_rehashing_only_checkpoint(self):
        path = self.bound / state.PROGRESS_FILE; value = json.loads(path.read_bytes())
        query = next(q for q in value['state']['queries'] if q['kind'] == 'search')
        query['next_page'] = 7
        value['state_sha256'] = export.digest(export.encoded(value['state']))
        path.write_bytes(export.encoded(value, pretty=True))
        with self.assertRaisesRegex(state.CandidateStateError, 'fingerprints differ'): state.load_snapshot(self.bound)

    def test_binding_rejects_resealed_private_checkpoint_fields(self):
        before = self.files(self.bound); checkpoint = json.loads(before[state.PROGRESS_FILE])
        checkpoint['state']['headers'] = {'Authorization': 'synthetic-private-fixture'}
        checkpoint['state_sha256'] = export.digest(export.encoded(checkpoint['state']))
        manifest = json.loads(before[export.MANIFEST_FILE]); manifest['checkpoint_state_sha256'] = checkpoint['state_sha256']
        manifest_bytes = export.encoded(manifest, pretty=True); checkpoint['manifest_sha256'] = export.digest(manifest_bytes)
        (self.bound / export.MANIFEST_FILE).write_bytes(manifest_bytes)
        (self.bound / state.PROGRESS_FILE).write_bytes(export.encoded(checkpoint, pretty=True))
        with self.assertRaisesRegex(state.CandidateStateError, 'forbidden'): state.load_snapshot(self.bound)

    def test_interrupted_runtime_never_replaces_public_triplet(self):
        baseline = state.load_snapshot(self.bound); runtime = self.root / 'runtime'
        current, _ = self.next_round(baseline, runtime)
        current['runs'][-1].update(status='running', finished_at=None)
        (runtime / 'candidate-metadata.json').write_bytes(export.encoded(current))
        before = self.files(self.bound)
        with self.assertRaises(ValueError): state.finalize_runtime(baseline, runtime, self.bound, catalog_bytes=self.catalog)
        self.assertEqual(self.files(self.bound), before)

    def test_publish_compare_and_swap_and_three_file_failure_rollback(self):
        baseline = state.load_snapshot(self.bound); runtime = self.root / 'runtime'
        self.next_round(baseline, runtime); staged = self.root / 'staged'
        state.finalize_runtime(baseline, runtime, staged, catalog_bytes=self.catalog)
        before = self.files(self.bound)
        for failure in (1, 2, 3):
            calls = 0; replace = state.os.replace
            def interrupted(source, target):
                nonlocal calls
                calls += 1
                if calls == failure: raise OSError('injected replacement failure')
                return replace(source, target)
            with mock.patch.object(state.os, 'replace', side_effect=interrupted), self.assertRaises(OSError):
                state.publish_snapshot(staged, self.bound, expected_prior_hashes=baseline.fingerprints)
            self.assertEqual(self.files(self.bound), before)
        wrong = dict(baseline.fingerprints); wrong[state.PROGRESS_FILE] = '0' * 64
        with self.assertRaises(state.CandidateStateError): state.publish_snapshot(staged, self.bound, expected_prior_hashes=wrong)
        self.assertEqual(self.files(self.bound), before)
        newer_catalog = b'{"id":"github:example/new-active"}\n'
        published = state.publish_snapshot(staged, self.bound, expected_prior_hashes=baseline.fingerprints, catalog_bytes=newer_catalog)
        updated = state.load_snapshot(self.bound, catalog_bytes=newer_catalog)
        self.assertEqual(published['files'], updated.fingerprints)
        self.assertNotEqual(published['staged_files'][export.MANIFEST_FILE], published['files'][export.MANIFEST_FILE])
        self.assertEqual(published['staged_files'][export.RECORD_FILE], published['files'][export.RECORD_FILE])

    def test_omitted_descriptions_stay_omitted_after_new_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); ledger, raw = fixture(root, description='file:///Users/private-fixture/notes.txt')
            ledger_bytes = export.encoded(ledger); body, manifest = export.build_candidate_export(ledger_bytes, raw, self.catalog)
            public = root / 'public'; export.write_pair(public, body, manifest)
            bound = root / 'bound'; state.bootstrap_from_ledger(ledger_bytes, raw, public, bound, catalog_bytes=self.catalog)
            baseline = state.load_snapshot(bound)
            old = baseline.records['github-repository:8']; self.assertIsNone(old['source_description'])
            runtime = root / 'runtime'; state.prepare_runtime(baseline, runtime)
            # A new public spelling makes this observed numeric ID a valid unobserved seed.
            item = repo(8, 'new-owner/renamed-eight', description='Now a harmless public description.')
            seed = {'id': 'github:new-owner/renamed-eight', 'url': item['html_url'], 'provider': 'github', 'discovered_in': []}
            (root / 'data/candidates.jsonl').write_bytes(export.encoded(seed)); timer = Timer(); timer.seconds = 100
            scan.run_scan(root, runtime, max_requests=1, existing_budget=1, fetcher=lambda u,t: response(item), clock=timer.clock, sleep=timer.sleep, now=timer.now)
            staged = root / 'staged'; state.finalize_runtime(baseline, runtime, staged, catalog_bytes=self.catalog)
            new = state.load_snapshot(staged).records['github-repository:8']
            self.assertIsNone(new['source_description']); self.assertEqual(new['omitted_fields'], old['omitted_fields'])
            self.assertNotIn(b'private-fixture/notes', b''.join(self.files(staged).values()))

    def initial_search_snapshot(self, root, *, incomplete=False, topics=None, items=None, total=None):
        (root / 'data').mkdir()
        for name in scan.INPUTS: (root / 'data' / name).write_text('' if name.endswith('.jsonl') else '[]\n')
        timer = Timer()
        ledger, _ = scan.run_scan(root, root / '.cache/initial', max_requests=1, existing_budget=0,
            topics=topics or ['browser-automation'], created_after='2024-01-01', created_before='2026-10-18',
            fetcher=lambda u,t: response(page([repo(1)] if items is None else items, total, incomplete=incomplete)),
            clock=timer.clock, sleep=timer.sleep, now=timer.now)
        raw = root / '.cache/initial/raw'; ledger_bytes = export.encoded(ledger)
        body, manifest = export.build_candidate_export(ledger_bytes, raw, self.catalog)
        export.write_pair(root / 'public', body, manifest)
        state.bootstrap_from_ledger(ledger_bytes, raw, root / 'public', root / 'bound', catalog_bytes=self.catalog)
        shutil.rmtree(raw)
        return state.load_snapshot(root / 'bound')

    def test_search_cursors_follow_exact_pages_for_resumed_reset_and_new_queries(self):
        for case in ('resumed', 'recheck', 'backfill', 'split', 'daily_epoch'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                options = {'incomplete': True} if case == 'recheck' else {}
                if case in {'resumed', 'split'}:
                    options.update(items=[repo(i) for i in range(1, 101)], total=301)
                baseline = self.initial_search_snapshot(root, **options)
                runtime = root / 'runtime'; state.prepare_runtime(baseline, runtime)
                timer = Timer(); timer.seconds = 86400 if case == 'daily_epoch' else 100
                row_options = {'created_at': '2026-10-18T00:00:00Z'} if case == 'daily_epoch' else {}
                replies = [response(page([repo(i, **row_options) for i in range(101, 201)], 301))]
                if case == 'split':
                    replies.insert(0, response(page([repo(i) for i in range(1, 101)], 1001)))
                responses = iter(replies)
                current, _ = scan.run_scan(root, runtime, max_requests=len(replies), existing_budget=0,
                    strict_replay=True, advance_epoch=True,
                    topics=['browser-automation', 'computer-use'] if case == 'backfill' else None,
                    fetcher=lambda u,t: next(responses), clock=timer.clock, sleep=timer.sleep, now=timer.now)
                last = current['receipts'][-1]
                query = next(q for q in current['queries'] if q['id'] == last['query_id'])
                self.assertEqual(query['next_page'], 3 if case == 'resumed' else 2)
                old_ids = {q['id'] for q in baseline.state['queries']}
                if case in {'backfill', 'split', 'daily_epoch'}: self.assertNotIn(query['id'], old_ids)
                if case == 'recheck': self.assertEqual(len(current['query_rechecks']), 1)
                valid = root / 'valid'
                state.finalize_runtime(baseline, runtime, valid, catalog_bytes=self.catalog)
                self.assertEqual(state.load_snapshot(valid).state['queries'], current['queries'])
                before = self.files(root / 'bound')
                query['next_page'] = 10
                (runtime / 'candidate-metadata.json').write_bytes(export.encoded(current))
                with self.assertRaisesRegex(state.CandidateStateError, 'cursor differs'):
                    state.finalize_runtime(baseline, runtime, root / 'bound', catalog_bytes=self.catalog)
                self.assertEqual(self.files(root / 'bound'), before)

    def test_new_unrequested_query_cannot_claim_a_later_page(self):
        baseline = state.load_snapshot(self.bound); runtime = self.root / 'runtime'
        state.prepare_runtime(baseline, runtime); timer = Timer(); timer.seconds = 100
        current, _ = scan.run_scan(self.root, runtime, max_requests=1, existing_budget=0, strict_replay=True,
            advance_epoch=True, topics=sorted(scan.TOPICS), fetcher=lambda u,t: response(page([])),
            clock=timer.clock, sleep=timer.sleep, now=timer.now)
        old_ids = {q['id'] for q in baseline.state['queries']}
        queried = {r['query_id'] for r in current['receipts']}
        untouched = next(q for q in current['queries'] if q['id'] not in old_ids | queried and q['kind'] == 'search')
        untouched['next_page'] = 2
        (runtime / 'candidate-metadata.json').write_bytes(export.encoded(current))
        with self.assertRaisesRegex(state.CandidateStateError, 'cursor differs'):
            state.finalize_runtime(baseline, runtime, self.root / 'staged', catalog_bytes=self.catalog)
        self.assertFalse((self.root / 'staged').exists())

    def test_failed_search_requests_do_not_advance_cursor(self):
        replies = [('quarantine', response(page([repo(2, private=True)]))),
                   ('malformed', response(b'{')), ('rate_limit', response({}, 429))]
        for case, reply in replies:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                baseline = self.initial_search_snapshot(root, items=[repo(i) for i in range(1, 101)], total=301)
                runtime = root / 'runtime'; state.prepare_runtime(baseline, runtime)
                timer = Timer(); timer.seconds = 100
                current, _ = scan.run_scan(root, runtime, max_requests=1, existing_budget=0, strict_replay=True,
                    fetcher=lambda u,t: reply, clock=timer.clock, sleep=timer.sleep, now=timer.now)
                query = next(q for q in current['queries'] if q['kind'] == 'search')
                self.assertEqual(query['next_page'], 2)
                state.finalize_runtime(baseline, runtime, root / 'valid', catalog_bytes=self.catalog)
                query['next_page'] = 3
                (runtime / 'candidate-metadata.json').write_bytes(export.encoded(current))
                with self.assertRaisesRegex(state.CandidateStateError, 'cursor differs'):
                    state.finalize_runtime(baseline, runtime, root / 'staged', catalog_bytes=self.catalog)
                self.assertFalse((root / 'staged').exists())

    def test_resealed_receipt_position_cannot_skip_a_page(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            baseline = self.initial_search_snapshot(root, items=[repo(i) for i in range(1, 101)], total=301)
            runtime = root / 'runtime'; state.prepare_runtime(baseline, runtime)
            timer = Timer(); timer.seconds = 100
            current, _ = scan.run_scan(root, runtime, max_requests=1, existing_budget=0, strict_replay=True,
                fetcher=lambda u,t: response(page([repo(i) for i in range(101, 201)], 301)),
                clock=timer.clock, sleep=timer.sleep, now=timer.now)
            receipt = current['receipts'][-1]
            receipt['position'] = 9
            receipt['source_url'] = receipt['source_url'].replace('page=2&', 'page=9&')
            receipt['request_url_sha256'] = export.digest(receipt['source_url'].encode())
            for row in current['records'].values():
                for occurrence in row['occurrences']:
                    if occurrence['receipt_id'] == receipt['id']: occurrence['position'] = 9
            query = next(q for q in current['queries'] if q['kind'] == 'search'); query['next_page'] = 10
            (runtime / 'candidate-metadata.json').write_bytes(export.encoded(current))
            with self.assertRaisesRegex(state.CandidateStateError, 'skipped or repeated'):
                state.finalize_runtime(baseline, runtime, root / 'staged', catalog_bytes=self.catalog)
            self.assertFalse((root / 'staged').exists())

    def test_mixed_response_is_quarantined_without_poisoning_public_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            baseline = self.initial_search_snapshot(root, topics=['browser-automation', 'computer-use'])
            runtime = root / 'runtime'; state.prepare_runtime(baseline, runtime); timer = Timer(); timer.seconds = 100
            mixed = page([repo(9), repo(10, private=True, description='private-fixture-never-export')])
            current, run = scan.run_scan(root, runtime, max_requests=1, existing_budget=0, strict_replay=True,
                fetcher=lambda u,t: response(mixed), clock=timer.clock, sleep=timer.sleep, now=timer.now)
            self.assertEqual(current['receipts'][-1]['outcome'], 'quarantined')
            self.assertEqual(current['receipts'][-1]['accepted_repository_ids'], [])
            result = state.finalize_runtime(baseline, runtime, root / 'staged', catalog_bytes=self.catalog)
            updated = state.load_snapshot(root / 'staged')
            self.assertEqual(updated.payloads[export.RECORD_FILE], baseline.payloads[export.RECORD_FILE])
            self.assertEqual(result['verification']['primary_bodies_replayed'], 0)
            self.assertEqual(result['rejected_rows'], {'private_or_unknown': 1})
            self.assertNotIn(b'private-fixture-never-export', b''.join(updated.payloads.values()))
            self.assertEqual(list((runtime / 'raw').iterdir()), [])

    def test_partial_recheck_is_bound_to_prior_cursor_and_keeps_old_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); baseline = self.initial_search_snapshot(root, incomplete=True)
            runtime = root / 'runtime'; state.prepare_runtime(baseline, runtime); timer = Timer(); timer.seconds = 100
            current, _ = scan.run_scan(root, runtime, max_requests=1, existing_budget=0, strict_replay=True, advance_epoch=True,
                fetcher=lambda u,t: response(page([repo(1), repo(2)])), clock=timer.clock, sleep=timer.sleep, now=timer.now)
            self.assertEqual(len(current['query_rechecks']), 1)
            result = state.finalize_runtime(baseline, runtime, root / 'staged', catalog_bytes=self.catalog)
            updated = state.load_snapshot(root / 'staged')
            self.assertEqual(result['total_unique_repositories'], 2)
            self.assertEqual(updated.state['receipts'][:-1], baseline.state['receipts'])
            self.assertEqual(updated.manifest['scan']['query_rechecks_count'], 1)
            self.assertEqual(result['query_status_counts'].get('observed_pages_exhausted'), 1)
            current['query_rechecks'][-1]['previous']['next_page'] = 7
            (runtime / 'candidate-metadata.json').write_bytes(export.encoded(current))
            before = self.files(root / 'bound')
            with self.assertRaises(ValueError): state.finalize_runtime(baseline, runtime, root / 'bound', catalog_bytes=self.catalog)
            self.assertEqual(self.files(root / 'bound'), before)

    def test_additive_topics_keep_bootstrap_epoch_and_observation_bytes(self):
        baseline = state.load_snapshot(self.bound); runtime = self.root / 'runtime'; state.prepare_runtime(baseline, runtime)
        timer = Timer(); timer.seconds = 100
        current, _ = scan.run_scan(self.root, runtime, max_requests=1, existing_budget=0, strict_replay=True,
            advance_epoch=True, topics=sorted(scan.TOPICS), fetcher=lambda u,t: response(page([])),
            clock=timer.clock, sleep=timer.sleep, now=timer.now)
        result = state.finalize_runtime(baseline, runtime, self.root / 'staged', catalog_bytes=self.catalog)
        updated = state.load_snapshot(self.root / 'staged')
        self.assertEqual(updated.state['epochs'][:len(baseline.state['epochs'])], baseline.state['epochs'])
        self.assertEqual(set(updated.manifest['scan']['configuration']['topics']), set(scan.TOPICS))
        self.assertEqual(updated.payloads[export.RECORD_FILE], baseline.payloads[export.RECORD_FILE])
        self.assertEqual(result['epoch_id'], current['current_epoch_id'])

    def test_first_triplet_interruption_leaves_no_half_snapshot(self):
        baseline = state.load_snapshot(self.bound); output = self.root / 'empty-target'
        replace = state.os.replace; calls = 0
        def interrupt_third(source, target):
            nonlocal calls
            calls += 1
            if calls == 3: raise KeyboardInterrupt('synthetic interrupted adoption')
            return replace(source, target)
        with mock.patch.object(state.os, 'replace', side_effect=interrupt_third), self.assertRaises(KeyboardInterrupt):
            state._write_triplet(output, baseline.payloads, expected_prior_hashes={name: None for name in state.FILES})
        self.assertEqual(list(output.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
