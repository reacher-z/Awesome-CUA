#!/usr/bin/env python3
"""Stage one bounded candidate-observation continuation; never write data/ here."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import time

from network_budget import budget_from_environment

ROOT = Path(__file__).resolve().parents[1]
PHASE = 'github_candidates'
FINALIZE_SECONDS = 10
TERMINAL = {'finished', 'request_budget', 'wall_budget', 'partial', 'rate_limited'}
SUMMARY_COUNTS = ('requests_attempted', 'new_unique_repositories',
                  'total_unique_repositories', 'pending_queries', 'unknown_requests')


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def runtime_path(budget):
    return budget.path.with_name(budget.run_id + '-github-candidates')


def result_path(budget):
    return budget.path.with_name(budget.run_id + '-github-candidates-result.json')


def settings(config):
    from scan_github_candidates import TOPICS
    enabled = config.get('github_candidates_enabled', False)
    requests = config.get('github_candidate_max_requests', 30)
    seconds = config.get('github_candidate_max_seconds', 220)
    existing = config.get('github_candidate_existing_budget', 5)
    topics = config.get('github_candidate_topics', sorted(TOPICS))
    if (type(enabled) is not bool or type(requests) is not int or not 1 <= requests <= 30
            or type(seconds) is not int or not 20 <= seconds <= 220
            or type(existing) is not int or not 0 <= existing <= min(5, requests)
            or not isinstance(topics, list) or not topics or any(not isinstance(t, str) or t not in TOPICS for t in topics)
            or len(topics) != len(set(topics))):
        raise ValueError('Unbounded GitHub candidate phase configuration')
    return {'enabled': enabled, 'max_requests': requests, 'max_seconds': seconds,
            'existing_budget': existing, 'topics': list(topics)}


def checked_summary(summary):
    if not isinstance(summary, dict) or summary.get('status') not in TERMINAL:
        raise ValueError('Candidate stage has no complete terminal scan receipt')
    if not isinstance(summary.get('run_id'), str) or not summary['run_id'].startswith('run:'):
        raise ValueError('Candidate stage has no current scan run ID')
    for key in SUMMARY_COUNTS:
        if type(summary.get(key)) is not int or summary[key] < 0:
            raise ValueError('Invalid candidate stage count: ' + key)
    rejected = summary.get('rejected_rows')
    if (not isinstance(rejected, dict)
            or any(not isinstance(k, str) or type(v) is not int or v < 0 for k, v in rejected.items())):
        raise ValueError('Invalid candidate rejection counts')
    statuses = summary.get('query_status_counts', {})
    if (not isinstance(statuses, dict)
            or any(not isinstance(k, str) or type(v) is not int or v < 0 for k, v in statuses.items())):
        raise ValueError('Invalid candidate query status counts')
    return summary


def phase_summary(summary, started):
    summary = checked_summary(summary)
    warnings = []
    if summary['status'] == 'rate_limited':
        warnings.append('GitHub candidate observations paused for provider rate limiting; verified progress and cursor are retained.')
    if summary['unknown_requests']:
        warnings.append(f"{summary['unknown_requests']} GitHub candidate requests have no accepted metadata response.")
    if sum(summary['rejected_rows'].values()):
        warnings.append(f"{sum(summary['rejected_rows'].values())} GitHub metadata rows were rejected; rejection reasons remain in the candidate scan receipt.")
    statuses = summary.get('query_status_counts', {})
    blocked = statuses.get('blocked_single_day_window', 0)
    partial = statuses.get('partial_results', 0) + statuses.get('partial_api_window', 0)
    if blocked:
        warnings.append(f'{blocked} GitHub search windows remain blocked at one day and require an explicit operator decision.')
    if partial:
        warnings.append(f'{partial} GitHub search windows retain incomplete-response or pagination gaps; completion is not claimed.')
    complete = (summary['status'] == 'finished' and not summary['pending_queries']
                and not summary['unknown_requests'] and not summary['rejected_rows'] and not blocked and not partial)
    successful = summary.get('verification', {}).get('successful_receipts_replayed', 0)
    if type(successful) is not int or not 0 <= successful <= summary['requests_attempted']:
        raise ValueError('Invalid newly verified candidate response count')
    return {'name': PHASE, 'started_at': started, 'finished_at': now(), 'ok': True,
            'state': 'complete' if complete else 'rate_limited' if summary['status'] == 'rate_limited'
                     else 'blocked' if blocked else 'bounded_progress' if summary['pending_queries'] else 'partial',
            'complete': complete, 'scan_status': summary['status'],
            'run_id': summary['run_id'], 'request_attempted': summary['requests_attempted'] > 0,
            'successful_responses': successful,
            **{key: summary[key] for key in SUMMARY_COUNTS},
            'epoch_id': summary.get('epoch_id'), 'query_status_counts': statuses,
            'rejected_rows': summary['rejected_rows'], 'warnings': warnings,
            'files': summary['files'], 'published': False}


def write_result(baseline, budget, phase):
    from catalog import write_json
    receipt = {'schema_version': 1, 'round_id': budget.run_id,
               'baseline_files': baseline.fingerprints, 'phase': phase}
    write_json(result_path(budget), receipt)
    return receipt


def run_stage(root, budget, *, config=None, clock=time.monotonic):
    """Restore checked-in state, scan into private cache, replay new bodies, stage output."""
    import candidate_state
    import scan_github_candidates

    root = Path(root)
    if budget is None:
        raise ValueError('Candidate stage requires the existing network-round context')
    config = config if config is not None else json.loads((root / 'data/scan-config.json').read_text(encoding='utf-8'))
    limits = settings(config)
    if not limits['enabled']:
        raise ValueError('Candidate stage is disabled')
    start_clock = clock(); started = now()
    runtime = runtime_path(budget)
    if runtime.exists():
        raise ValueError('Candidate stage runtime already exists for this network round')
    baseline = candidate_state.load_snapshot(root / 'data')
    runtime.mkdir(parents=True)
    candidate_state.prepare_runtime(baseline, runtime)
    remaining = min(limits['max_seconds'] - (clock() - start_clock), budget.remaining_seconds()) - FINALIZE_SECONDS
    request_count = min(limits['max_requests'], budget.summary()['max_requests'] - budget.summary()['requests_reserved'])
    if remaining < 1 or request_count < 1:
        return write_result(baseline, budget, {
            'name': PHASE, 'started_at': started, 'finished_at': now(), 'ok': True,
            'state': 'deferred_budget', 'deferred': True, 'request_attempted': False,
            'requests_attempted': 0, 'new_unique_repositories': 0,
            'total_unique_repositories': len(baseline.records),
            'warnings': [], 'files': baseline.fingerprints, 'published': False,
            'reason': 'The remaining network/time allowance cannot start another bounded request; checkpoint unchanged.'})
    _, run = scan_github_candidates.run_scan(root, runtime, max_requests=request_count,
        max_seconds=remaining, existing_budget=min(limits['existing_budget'], request_count),
        topics=limits['topics'], strict_replay=True, advance_epoch=True, shared_budget=budget)
    summary = candidate_state.finalize_runtime(baseline, runtime, runtime / 'public',
        catalog_bytes=(root / 'data/catalog.jsonl').read_bytes())
    checked_summary(summary)
    if summary['run_id'] != run['id'] or summary['status'] != run['status']:
        raise ValueError('Candidate finalization returned a different scan round')
    phase = phase_summary(summary, started)
    # The result is written last. The parent rejects an interrupted child with no receipt.
    return write_result(baseline, budget, phase)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        receipt = run_stage(ROOT, budget_from_environment())
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, 'Candidate phase rejected: ' + str(error) + '\n')
    phase = receipt['phase']
    print(json.dumps({'phase': PHASE, 'run_id': phase.get('run_id'),
                      'requests_attempted': phase['requests_attempted'],
                      'new_unique_repositories': phase['new_unique_repositories'],
                      'total_unique_repositories': phase['total_unique_repositories'],
                      'state': phase['state'], 'published': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
