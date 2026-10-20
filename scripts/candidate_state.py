#!/usr/bin/env python3
"""Sanitized durable candidate progress and incremental, offline-verified updates.

The authoritative durable snapshot is a bound triplet. Runtime ledgers and new
raw bodies stay in ignored per-run directories. No function makes a request.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile

import export_candidates as export
import scan_github_candidates as scan

PROGRESS_FILE = 'github-candidate-progress.json'
FILES = (*export.FILES, PROGRESS_FILE)
CHECKPOINT_FIELDS = {'schema_version', 'provider', 'observation_snapshot_sha256', 'manifest_sha256', 'state_sha256', 'state'}
FORBIDDEN_STATE_KEYS = {'records', 'description', 'source_description', 'owner', 'email', 'body', 'raw_body',
                        'headers', 'authorization', 'cookies', 'permissions'}


class CandidateStateError(ValueError):
    """A missing, changed or incomplete durable snapshot must not be adopted."""


@dataclass(frozen=True)
class Baseline:
    fingerprints: dict
    state: dict
    manifest: dict
    records: dict
    payloads: dict
    lines: dict


def _reject_private_structure(value):
    if isinstance(value, dict):
        if any(str(key).casefold() in FORBIDDEN_STATE_KEYS for key in value):
            raise CandidateStateError('Checkpoint contains a forbidden metadata field')
        for child in value.values(): _reject_private_structure(child)
    elif isinstance(value, list):
        for child in value: _reject_private_structure(child)


def _meta(state):
    result = {key: copy.deepcopy(value) for key, value in state.items() if key != 'records'}
    _reject_private_structure(result)
    return result


def _runtime_record(row):
    result = {key: copy.deepcopy(row[key]) for key in export.META_FIELDS - {'description', 'topics'}}
    result.update(description=row['source_description'], topics=list(row['github_topics']),
                  first_observed_at=row['first_observed_at'], last_observed_at=row['last_observed_at'],
                  known_names=list(row['known_names']),
                  occurrences=[{key: ev[key] for key in ('query_id', 'receipt_id', 'position')} for ev in row['evidence']])
    return result


def _carry_omissions(row, previous):
    """Automatic discovery cannot silently restore a previously omitted field."""
    if previous.get('omitted_fields'):
        row['source_description'] = None
        unique = {(item['field'], item['reason']): item for item in [*previous['omitted_fields'], *row['omitted_fields']]}
        row['omitted_fields'] = [unique[key] for key in sorted(unique)]
        row['record_sha256'] = export.digest(export.encoded({k: v for k, v in row.items() if k != 'record_sha256'}))
    return row


def _load_payloads(payloads, *, catalog_bytes=None):
    if set(payloads) != set(FILES): raise CandidateStateError('Candidate snapshot requires the complete three-file checkpoint')
    manifest = scan.strict_json(payloads[export.MANIFEST_FILE])
    rows = export.validate_candidate_export(payloads[export.RECORD_FILE], manifest, catalog_bytes=catalog_bytes)
    checkpoint = scan.strict_json(payloads[PROGRESS_FILE])
    if (not isinstance(checkpoint, dict) or set(checkpoint) != CHECKPOINT_FIELDS
            or type(checkpoint['schema_version']) is not int or checkpoint['schema_version'] != 1
            or checkpoint['provider'] != 'github' or not isinstance(checkpoint['state'], dict)):
        raise CandidateStateError('Invalid candidate progress contract')
    _reject_private_structure(checkpoint['state'])
    state_sha = export.digest(export.encoded(checkpoint['state']))
    if (checkpoint['state_sha256'] != state_sha or manifest.get('checkpoint_state_sha256') != state_sha
            or checkpoint['observation_snapshot_sha256'] != export.digest(payloads[export.RECORD_FILE])
            or checkpoint['manifest_sha256'] != export.digest(payloads[export.MANIFEST_FILE])):
        raise CandidateStateError('Candidate checkpoint and public pair fingerprints differ')
    state = copy.deepcopy(checkpoint['state'])
    state['records'] = {r['id']: _runtime_record(r) for r in rows}
    scan.validate_state(state)
    if not export.equal_json(export._summary(state), manifest['scan']):
        raise CandidateStateError('Public scan summary differs from checkpoint progress')
    inputs = [{'id': item['id'], 'files': item['files']} for item in state['inputs']]
    if not export.equal_json(inputs, manifest['input_fingerprints']):
        raise CandidateStateError('Public input fingerprints differ from checkpoint')
    receipts = {r['id']: r for r in state['receipts']}
    for row in rows:
        rebuilt = _carry_omissions(export.public_record(state['records'][row['id']], receipts), row)
        if not export.equal_json(rebuilt, row):
            raise CandidateStateError('Public observation differs from checkpoint receipts: ' + row['id'])
    lines = {}
    for line in payloads[export.RECORD_FILE].splitlines(keepends=True):
        if not line.strip(): raise CandidateStateError('Durable observation JSONL cannot contain blank lines')
        row = scan.strict_json(line)
        if not line.endswith(b'\n'): raise CandidateStateError('Durable JSONL records require a newline')
        lines[row['id']] = line
    return Baseline({key: export.digest(value) for key, value in payloads.items()}, state, manifest,
                    {r['id']: r for r in rows}, copy.deepcopy(payloads), lines)


def load_snapshot(public_dir, *, catalog_bytes=None):
    try:
        payloads = {name: export.file_bytes(export.public_file(public_dir, name)) for name in FILES}
        return _load_payloads(payloads, catalog_bytes=catalog_bytes)
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise CandidateStateError('Candidate snapshot is missing or invalid; explicit offline bootstrap/review is required: ' + str(error)) from error


def prepare_runtime(baseline, runtime_dir):
    """Restore an exact sanitized ledger into a new ignored per-run directory."""
    checked = _load_payloads(baseline.payloads)
    runtime_dir = scan.checked_output(runtime_dir)
    if runtime_dir.exists() and any(runtime_dir.iterdir()):
        raise CandidateStateError('Candidate runtime directory must be fresh and empty')
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / 'raw').mkdir()
    path = runtime_dir / 'candidate-metadata.json'
    scan.atomic_write(path, export.encoded(checked.state, pretty=True))
    return path


def _triplet(state, body, manifest):
    meta = _meta(state)
    state_sha = export.digest(export.encoded(meta))
    manifest = copy.deepcopy(manifest)
    manifest['checkpoint_state_sha256'] = state_sha
    manifest_bytes = export.encoded(manifest, pretty=True)
    checkpoint = {'schema_version': 1, 'provider': 'github',
                  'observation_snapshot_sha256': export.digest(body),
                  'manifest_sha256': export.digest(manifest_bytes),
                  'state_sha256': state_sha, 'state': meta}
    payloads = {export.RECORD_FILE: body, export.MANIFEST_FILE: manifest_bytes,
                PROGRESS_FILE: export.encoded(checkpoint, pretty=True)}
    _load_payloads(payloads)
    return payloads


def _current_hashes(directory):
    hashes = {}
    for name in FILES:
        path = export.public_file(directory, name)
        if path.exists() and not path.is_file(): raise CandidateStateError('Candidate durable target is not a regular file')
        hashes[name] = export.digest(path.read_bytes()) if path.exists() else None
    return hashes


def _write_triplet(directory, payloads, *, expected_prior_hashes):
    """Rollback raised write failures. The workflow's Git commit is the durable boundary."""
    _load_payloads(payloads)
    if set(expected_prior_hashes) != set(FILES) or _current_hashes(directory) != expected_prior_hashes:
        raise CandidateStateError('Candidate durable files changed since this phase started')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {name: export.public_file(directory, name) for name in FILES}
    previous = {name: paths[name].read_bytes() if paths[name].exists() else None for name in FILES}
    with tempfile.TemporaryDirectory(prefix='.candidate-state-', dir=directory.resolve()) as temporary:
        stage = Path(temporary)
        for name in FILES: (stage / name).write_bytes(payloads[name])
        changed = []
        try:
            if _current_hashes(directory) != expected_prior_hashes:
                raise CandidateStateError('Candidate durable files changed before replacement')
            for name in FILES:
                os.replace(stage / name, paths[name]); changed.append(name)
        except BaseException:
            for name in reversed(changed):
                if previous[name] is None: paths[name].unlink(missing_ok=True)
                else:
                    restore = stage / ('restore-' + name)
                    restore.write_bytes(previous[name]); os.replace(restore, paths[name])
            raise
    return {name: export.digest(payloads[name]) for name in FILES}


def publish_snapshot(staged_public_dir, target_dir, *, expected_prior_hashes, catalog_bytes=None):
    """Validate staged child output, optionally rebind context, then compare-and-swap."""
    staged = load_snapshot(staged_public_dir)
    payloads = copy.deepcopy(staged.payloads)
    if catalog_bytes is not None:
        manifest = copy.deepcopy(staged.manifest)
        manifest['active_catalog_context'] = export.catalog_context(catalog_bytes)
        payloads = _triplet(staged.state, payloads[export.RECORD_FILE], manifest)
        _load_payloads(payloads, catalog_bytes=catalog_bytes)
    hashes = _write_triplet(target_dir, payloads, expected_prior_hashes=expected_prior_hashes)
    return {'staged_files': staged.fingerprints, 'files': hashes,
            'observation_snapshot_sha256': export.digest(payloads[export.RECORD_FILE])}


def _search_cursor(query, prior, receipts, *, reset):
    """Derive this traversal's cursor from ordered receipts, never a claimed jump."""
    page = 1 if prior is None or reset else prior['next_page']
    requestable = prior is None or reset or prior['status'] == 'pending'
    for receipt in receipts:
        if not requestable or receipt['position'] != page:
            raise CandidateStateError('Incremental search receipt skipped or repeated a page')
        parsed = receipt['outcome'] in {'accepted', 'accepted_with_rejections', 'rejected'}
        if parsed and (type(receipt['reported_total']) is not int or type(receipt['returned_count']) is not int):
            raise CandidateStateError('Parsed search receipt lacks its response counts')
        if not parsed:
            # Failed or quarantined requests do not advance and are not retried in this run.
            requestable = False
        elif (receipt['reported_total'] > scan.SPLIT_THRESHOLD or receipt['returned_count'] == 0
              or page * scan.PAGE_SIZE >= receipt['reported_total'] or page >= 10):
            # Split, blocked, exhausted and partial traversals retain the attempted page.
            requestable = False
        else:
            page += 1
    if query['next_page'] != page:
        raise CandidateStateError('Incremental search cursor differs from ordered request receipts')


def _history(baseline, state):
    old = baseline.state
    if (len(state['runs']) != len(old['runs']) + 1 or not export.equal_json(state['runs'][:-1], old['runs'])
            or not state['runs'][-1]['finished_at'] or state['runs'][-1]['status'] == 'running'):
        raise CandidateStateError('Incremental update requires one appended, completed round')
    for key in ('receipts', 'inputs'):
        if not export.equal_json(state[key][:len(old[key])], old[key]):
            raise CandidateStateError('Incremental update changed retained ' + key)
    if not set(old['records']) <= set(state['records']): raise CandidateStateError('Incremental update removed a retained observation')
    queries = {q['id']: q for q in state['queries']}
    new_receipts = state['receipts'][len(old['receipts']):]
    old_rechecks = old.get('query_rechecks', [])
    if not export.equal_json(state.get('query_rechecks', [])[:len(old_rechecks)], old_rechecks):
        raise CandidateStateError('Incremental update changed historical query rechecks')
    rechecks = state.get('query_rechecks', [])[len(old_rechecks):]
    if len(rechecks) > 2 or len({r['query_id'] for r in rechecks}) != len(rechecks):
        raise CandidateStateError('Too many or duplicate per-round query rechecks')
    resets = {r['query_id']: r for r in rechecks}
    progress_keys = {'status', 'next_page', 'reported_total', 'total_changed', 'incomplete_results_seen',
                     'seen_repository_ids', 'rejected_rows', 'last_attempt'}
    old_queries = {q['id']: q for q in old['queries']}
    for reset in resets.values():
        prior = old_queries.get(reset['query_id'])
        if (prior is None or prior['kind'] != 'search' or prior['status'] not in {'partial_results', 'partial_api_window'}
                or reset['receipt_boundary'] != len(old['receipts'])
                or not export.equal_json(reset['previous'], {k: prior[k] for k in progress_keys})):
            raise CandidateStateError('Query recheck is not bound to the prior cursor and receipt boundary')
    for query in old['queries']:
        new = queries.get(query['id'])
        if new is None: raise CandidateStateError('Incremental update removed a query cursor')
        immutable = {'id', 'kind', 'input_id', 'seed_count', 'topic', 'created_after', 'created_before', 'query', 'parent_id'} & set(query)
        if any(not export.equal_json(query[key], new.get(key)) for key in immutable):
            raise CandidateStateError('Incremental update changed query identity or bounds')
        if query['kind'] == 'search':
            related = [r for r in new_receipts if r['query_id'] == query['id']]
            reset = query['id'] in resets
            untouched = copy.deepcopy(query)
            if reset:
                untouched.update(status='pending', next_page=1, reported_total=None, total_changed=False,
                                 incomplete_results_seen=False, seen_repository_ids=[], rejected_rows=0, last_attempt=0)
            if not related and not export.equal_json(untouched, new):
                raise CandidateStateError('A query without a new request changed progress')
    for query in queries.values():
        if query['kind'] != 'search': continue
        prior = old_queries.get(query['id'])
        reset = query['id'] in resets
        related = [r for r in new_receipts if r['query_id'] == query['id']]
        expected = (set() if prior is None or reset else set(prior['seen_repository_ids']))
        expected |= {rid for r in related for rid in r['accepted_repository_ids']}
        if set(query['seen_repository_ids']) != expected:
            raise CandidateStateError('Incremental query progress differs from accepted receipts')
        _search_cursor(query, prior, related, reset=reset)
    if 'epochs' in old and not export.equal_json(state.get('epochs', [])[:len(old['epochs'])], old['epochs']):
        raise CandidateStateError('Incremental update changed a historical query epoch')
    return new_receipts


def finalize_runtime(baseline, runtime_dir, staged_public_dir, *, catalog_bytes):
    """Verify only newly accepted raw bodies; leave historical bytes trusted and explicit."""
    baseline = _load_payloads(baseline.payloads)
    runtime_dir = scan.checked_output(runtime_dir)
    ledger_bytes = export.file_bytes(runtime_dir / 'candidate-metadata.json')
    state = scan.validate_state(scan.strict_json(ledger_bytes))
    new_receipts = _history(baseline, state)
    ids = {r['id'] for r in new_receipts}
    receipts, replayed, body_count = export.replay_receipts(state, runtime_dir / 'raw', receipt_ids=ids)
    output = []
    for rid, row in sorted(state['records'].items(), key=lambda item: item[1]['repository_id']):
        previous = baseline.state['records'].get(rid)
        if previous is not None and export.equal_json(row, previous):
            output.append(baseline.lines[rid]); continue
        old_occurrences = previous['occurrences'] if previous else []
        if not export.equal_json(row['occurrences'][:len(old_occurrences)], old_occurrences):
            raise CandidateStateError('An observation changed historical receipt occurrences')
        delta = row['occurrences'][len(old_occurrences):]
        if not delta or any(o['receipt_id'] not in ids for o in delta):
            raise CandidateStateError('Changed observation lacks a new primary receipt')
        history = [replayed[o['receipt_id']][row['repository_id']] for o in delta]
        if not export.equal_json({k: row[k] for k in export.META_FIELDS}, history[-1]):
            raise CandidateStateError('Incremental metadata differs from its newly retained response')
        first = previous['first_observed_at'] if previous else receipts[delta[0]['receipt_id']]['requested_at']
        names = set(previous['known_names'] if previous else []) | {r['full_name'] for r in history}
        times = [receipts[o['receipt_id']]['requested_at'] for o in row['occurrences']]
        if (row['first_observed_at'] != first or row['last_observed_at'] != times[-1]
                or row['known_names'] != sorted(names)
                or any(scan.timestamp(a) > scan.timestamp(b) for a, b in zip(times, times[1:]))):
            raise CandidateStateError('Incremental observation history does not match primary evidence')
        public = export.public_record(row, receipts)
        if rid in baseline.records: public = _carry_omissions(public, baseline.records[rid])
        output.append(export.encoded(public))
    body = b''.join(output)
    verification = {'mode': 'incremental_retained_replay', 'historical_raw_replayed': False,
                    'baseline_observation_sha256': baseline.fingerprints[export.RECORD_FILE],
                    'baseline_checkpoint_sha256': baseline.fingerprints[PROGRESS_FILE],
                    'successful_receipts_replayed': len(replayed), 'primary_bodies_replayed': body_count}
    manifest = export.manifest_for_records(state, body, catalog_bytes,
        source_ledger_sha256=export.digest(ledger_bytes), verification=verification)
    payloads = _triplet(state, body, manifest)
    expected = _current_hashes(staged_public_dir)
    if any(expected.values()) and expected != baseline.fingerprints:
        raise CandidateStateError('Staged public files changed from the validated baseline')
    files = _write_triplet(staged_public_dir, payloads, expected_prior_hashes=expected)
    run = state['runs'][-1]
    return {'run_id': run['id'], 'status': run['status'], 'requests_attempted': run['requests_attempted'],
            'new_unique_repositories': run['new_unique_repositories'], 'total_unique_repositories': len(state['records']),
            'pending_queries': sum(q['status'] == 'pending' for q in state['queries']),
            'query_status_counts': dict(sorted(Counter(q['status'] for q in state['queries']).items())),
            'epoch_id': state.get('current_epoch_id'),
            'unknown_requests': run['unknown_requests'], 'rejected_rows': copy.deepcopy(run['rejected_rows']),
            'files': files, 'verification': verification}


def bootstrap_from_ledger(ledger_bytes, raw_dir, public_dir, output_dir, *, catalog_bytes):
    """Explicit offline migration; it never adopts files into data/ implicitly."""
    prior_files = _current_hashes(public_dir)
    existing = {name: export.file_bytes(export.public_file(public_dir, name)) for name in export.FILES}
    old_manifest = scan.strict_json(existing[export.MANIFEST_FILE])
    export.validate_candidate_export(existing[export.RECORD_FILE], old_manifest)
    body, manifest = export.build_candidate_export(ledger_bytes, raw_dir, catalog_bytes)
    if body != existing[export.RECORD_FILE] or old_manifest['source_ledger_sha256'] != export.digest(ledger_bytes):
        raise CandidateStateError('Bootstrap ledger does not exactly reproduce the approved public observations')
    state = scan.validate_state(scan.strict_json(ledger_bytes))
    if hasattr(scan, 'migrate_state'): state = scan.migrate_state(copy.deepcopy(state))
    manifest = export.manifest_for_records(state, body, catalog_bytes,
        source_ledger_sha256=export.digest(ledger_bytes), verification=manifest['verification'])
    payloads = _triplet(state, body, manifest)
    expected = prior_files if Path(output_dir).resolve() == Path(public_dir).resolve() else _current_hashes(output_dir)
    files = _write_triplet(output_dir, payloads, expected_prior_hashes=expected)
    return {'records': len(state['records']), 'files': files, 'prior_files': prior_files,
            'verification': manifest['verification']}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Explicit offline bootstrap of candidate progress; no network requests.')
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--raw-dir', type=Path, required=True)
    parser.add_argument('--public-dir', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = bootstrap_from_ledger(export.file_bytes(args.ledger), args.raw_dir, args.public_dir, args.output_dir,
                                       catalog_bytes=export.file_bytes(args.catalog))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, 'Candidate bootstrap rejected: ' + str(error) + '\n')
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
