#!/usr/bin/env python3
"""Offline, public-only GitHub candidate observations; never catalog approvals.

The producer replays the explicitly supplied frozen scan ledger against retained
raw bytes. Public consumers can check the sanitized contract and fingerprints;
they cannot re-prove historical upstream bytes that are not distributed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.parse

import scan_github_candidates as scan

ROOT = Path(__file__).resolve().parents[1]
RECORD_FILE = 'github-candidates.jsonl'
MANIFEST_FILE = 'github-candidates-manifest.json'
SCHEMAS = ('github-candidate-observation.schema.json', 'github-candidate-observation-manifest.schema.json')
FILES = (RECORD_FILE, MANIFEST_FILE)
PUBLIC_PATHS = tuple('downloads/' + name for name in FILES) + tuple('schemas/' + name for name in SCHEMAS)
POLICY = ('Public GitHub metadata observations only. Every row remains candidate/relevance_pending; '
          'HTTP success, a topic tag, or a repository name does not establish CUA relevance, '
          'release completeness, licensing, or editorial approval.')
COUNT_POLICY = ('Unique positive numeric GitHub repository IDs within this observation snapshot. '
                'Query occurrences overlap. Candidates may overlap active catalog resources; '
                'these populations must not be added or treated as independent projects.')
CONTEXT_POLICY = 'Comparison context only; not the observation source, selection, or approval.'
PRIVACY_POLICY = ('Only allowlisted public repository fields and accepted primary receipts. '
                  'Suspect descriptions are explicitly omitted; owner/contact objects, headers, '
                  'raw bodies and local paths are not exported.')
META_FIELDS = {'id', 'repository_id', 'canonical_id', 'full_name', 'url', 'description', 'topics',
               'private', 'visibility', 'fork', 'archived', 'created_at', 'updated_at', 'pushed_at',
               'metadata_status', 'review_status', 'scope'}
EVIDENCE_FIELDS = {'receipt_id', 'run_id', 'query_id', 'position', 'url', 'request_url_sha256',
                   'observed_at', 'retrieved_at', 'sha256', 'bytes'}
PUBLIC_FIELDS = (META_FIELDS - {'description', 'topics'}) | {'source_description', 'github_topics',
                 'first_observed_at', 'last_observed_at', 'known_names', 'evidence',
                 'metadata_receipt_id', 'omitted_fields', 'record_sha256'}
OMISSION_REASONS = {'credential_shaped_string', 'private_home_path', 'url_userinfo'}


def digest(body):
    return hashlib.sha256(body).hexdigest()


def encoded(value, *, pretty=False):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       indent=2 if pretty else None, separators=None if pretty else (',', ':')) + '\n').encode()


def equal_json(left, right):
    return encoded(left) == encoded(right)


def checked_count(value):
    if type(value) is not int or value < 0:
        raise ValueError('Expected a nonnegative integer count')
    return value


def checked_sha(value):
    if not isinstance(value, str) or not scan.SHA.fullmatch(value):
        raise ValueError('Invalid observation fingerprint')
    return value


def file_bytes(path):
    path = scan.checked_output(path)
    if not path.is_file():
        raise ValueError('Missing regular observation input')
    return path.read_bytes()


def public_file(root, relative):
    """Guard paths below a trusted build root, allowing OS aliases above it."""
    root = Path(root)
    if root.is_symlink(): raise ValueError('Public candidate root cannot be a symlink')
    current = root
    for part in relative.split('/'):
        if not part or part.startswith('.') or '\\' in part:
            raise ValueError('Unsafe public candidate path')
        current = current / part
        if current.is_symlink(): raise ValueError('Public candidate paths cannot contain symlinks')
    resolved = current.resolve()
    if not resolved.is_relative_to(root.resolve()): raise ValueError('Public candidate path escaped its root')
    return resolved


def privacy_findings(value):
    """Bounded public-field inspection; never return or log the suspect value."""
    if not isinstance(value, str):
        return []
    findings = []
    tokens = r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{35,}|(?:AKIA|ASIA)[A-Z0-9]{16})\b'
    if re.search(tokens, value) or re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', value):
        findings.append('credential_shaped_string')
    if re.search(r'(?<![A-Za-z0-9:/])/(?:Users|home)/[^/\s]+(?:/|$)|[A-Za-z]:\\Users\\[^\\\s]+\\', value):
        findings.append('private_home_path')
    for url in re.findall(r'\b[A-Za-z][A-Za-z0-9+.-]*://[^\s<>"\']+', value):
        try:
            parts = urllib.parse.urlsplit(url)
            if parts.username is not None or parts.password is not None:
                findings.append('url_userinfo')
            if parts.scheme.casefold() == 'file':
                path = urllib.parse.unquote(parts.path).replace('\\', '/')
                if re.match(r'^/(?:Users|home)/[^/]+(?:/|$)|^/[A-Za-z]:/Users/[^/]+(?:/|$)', path, re.I):
                    findings.append('private_home_path')
        except ValueError:
            findings.append('url_userinfo')
    return sorted(set(findings))


def catalog_context(catalog_bytes):
    rows = [scan.strict_json(line) for line in catalog_bytes.splitlines() if line.strip()]
    if any(not isinstance(r, dict) or not isinstance(r.get('id'), str) for r in rows) or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Invalid active catalog comparison context')
    return {'sha256': digest(catalog_bytes), 'records': len(rows), 'role': CONTEXT_POLICY}


def replay_receipts(state, raw_dir, *, receipt_ids=None):
    """Replay an explicit receipt selection; an empty set never reads old raw bodies."""
    raw_dir = scan.checked_output(raw_dir)
    if not raw_dir.is_dir(): raise ValueError('Retained primary bodies require a real directory')
    queries = {q['id']: q for q in state['queries']}
    receipts = {r['id']: r for r in state['receipts']}
    observed = {}
    bodies = {}
    for receipt in state['receipts']:
        if receipt_ids is not None and receipt['id'] not in receipt_ids:
            continue
        if not receipt['raw_body_retained']:
            if receipt['accepted_repository_ids']:
                raise ValueError('Accepted metadata has no replayable primary body')
            continue
        if receipt['outcome'] != 'accepted' or receipt['status'] != 200 or not receipt['source_url']:
            raise ValueError('Retained body is not an accepted public response')
        sha = checked_sha(receipt['response_sha256'])
        if sha not in bodies:
            bodies[sha] = file_bytes(Path(raw_dir) / (sha + '.body'))
        body = bodies[sha]
        if digest(body) != sha or len(body) != receipt['response_bytes']:
            raise ValueError('Retained primary body fingerprint mismatch')
        value = scan.strict_json(body)
        query = queries[receipt['query_id']]
        parts = urllib.parse.urlsplit(scan.safe_api_url(receipt['source_url']))
        if query['kind'] == 'search':
            params = urllib.parse.parse_qs(parts.query)
            if (parts.path != '/search/repositories' or params['q'] != [query['query']]
                    or params['page'] != [str(receipt['position'])]):
                raise ValueError('Search receipt differs from its query and page')
            if (not isinstance(value, dict) or not isinstance(value.get('items'), list)
                    or type(value.get('total_count')) is not int or value['total_count'] < 0
                    or type(value.get('incomplete_results')) is not bool):
                raise ValueError('Invalid retained search response')
            if (receipt['reported_total'] != value['total_count']
                    or receipt['incomplete_results'] is not value['incomplete_results']):
                raise ValueError('Search receipt differs from the primary response')
            items = value['items']
        else:
            if not parts.path.startswith('/repos/'):
                raise ValueError('Existing-candidate receipt is not a repository endpoint')
            items = [value]
        if len(items) != receipt['returned_count']:
            raise ValueError('Returned count differs from the primary response')
        accepted = {}
        for item in items:
            try:
                row = scan.repository_metadata(item)
            except scan.Rejected:
                raise ValueError('Retained response contains non-public or rejected metadata') from None
            if query['kind'] == 'existing':
                if row['full_name'].casefold() != parts.path.removeprefix('/repos/').casefold():
                    raise ValueError('Direct response identifies a different repository')
            elif (query['topic'] not in row['topics'] or not query['created_after'] <= row['created_at'][:10] <= query['created_before']):
                raise ValueError('Primary metadata lies outside its query cohort')
            if row['repository_id'] in accepted:
                raise ValueError('Duplicate numeric repository ID in one response')
            accepted[row['repository_id']] = row
        if set(accepted) != set(receipt['accepted_repository_ids']):
            raise ValueError('Accepted numeric identities differ from the primary response')
        observed[receipt['id']] = accepted
    return receipts, observed, len(bodies)


def _replay(state, raw_dir):
    """Recompute every retained metadata observation for an offline full replay."""
    receipts, observed, body_count = replay_receipts(state, raw_dir)
    for row in state['records'].values():
        occurrences = row['occurrences']
        histories = [observed[o['receipt_id']][row['repository_id']] for o in occurrences]
        last = histories[-1]
        if not equal_json({key: row[key] for key in META_FIELDS}, last):
            raise ValueError('Current candidate metadata differs from its last retained observation: ' + row['id'])
        times = [receipts[o['receipt_id']]['requested_at'] for o in occurrences]
        if (row['first_observed_at'] != times[0] or row['last_observed_at'] != times[-1]
                or any(scan.timestamp(a) > scan.timestamp(b) for a, b in zip(times, times[1:]))
                or row['known_names'] != sorted({r['full_name'] for r in histories})):
            raise ValueError('Candidate observation history differs from its receipts: ' + row['id'])
    return receipts, body_count


def public_record(row, receipts):
    result = {key: copy.deepcopy(row[key]) for key in META_FIELDS - {'description', 'topics'}}
    result.update(source_description=row['description'], github_topics=list(row['topics']),
                  first_observed_at=row['first_observed_at'], last_observed_at=row['last_observed_at'],
                  known_names=list(row['known_names']), omitted_fields=[])
    for reason in privacy_findings(result['source_description']):
        result['omitted_fields'].append({'field': 'source_description', 'reason': reason})
    if result['omitted_fields']:
        result['source_description'] = None
    for field in ('full_name', 'url', 'canonical_id', 'known_names', 'github_topics'):
        values = result[field] if isinstance(result[field], list) else [result[field]]
        if any(privacy_findings(value) for value in values):
            raise ValueError('Sensitive-shaped identity field: ' + row['id'] + ' / ' + field)
    evidence = []
    for occurrence in row['occurrences']:
        r = receipts[occurrence['receipt_id']]
        evidence.append({'receipt_id': r['id'], 'run_id': r['run_id'], 'query_id': r['query_id'], 'position': r['position'],
                         'url': r['source_url'], 'request_url_sha256': r['request_url_sha256'],
                         'observed_at': r['requested_at'], 'retrieved_at': r['finished_at'],
                         'sha256': r['response_sha256'], 'bytes': r['response_bytes']})
    result['evidence'] = evidence
    result['metadata_receipt_id'] = evidence[-1]['receipt_id']
    result['record_sha256'] = digest(encoded(result))
    return result


def _summary(state):
    runs = []
    seen = set()
    for run in state['runs']:
        if run['finished_at'] is None:
            raise ValueError('Export requires a frozen, finished scan round')
        receipts = [r for r in state['receipts'] if r['run_id'] == run['id']]
        accepted = set().union(*(set(r['accepted_repository_ids']) for r in receipts)) if receipts else set()
        counts = {'requests_attempted': len(receipts), 'before_unique_repositories': len(seen),
                  'new_unique_repositories': len(accepted - seen),
                  'accepted_metadata_rows': sum(len(r['accepted_repository_ids']) for r in receipts)}
        seen |= accepted
        counts['after_unique_repositories'] = len(seen)
        if any(type(run[k]) is not int or run[k] != v for k, v in counts.items()):
            raise ValueError('Run counts differ from retained accepted observations')
        runs.append({key: run[key] for key in ('id', 'input_id', 'started_at', 'finished_at', 'status')} | counts)
    if seen != {row['repository_id'] for row in state['records'].values()}:
        raise ValueError('Run population differs from candidate observations')
    queries = []
    for q in state['queries']:
        keys = ('id', 'kind', 'status', 'topic', 'created_after', 'created_before', 'reported_total') if q['kind'] == 'search' else ('id', 'kind', 'status', 'input_id')
        queries.append({key: q[key] for key in keys})
        if 'epochs' in state and q['kind'] == 'search': queries[-1]['parent_id'] = q['parent_id']
    result = {'configuration': copy.deepcopy(state['configuration']), 'runs': runs, 'queries': queries,
            'request_outcomes': dict(sorted(Counter(r['outcome'] for r in state['receipts']).items())),
            'global_completeness_established': False,
            'limit': 'Bounded observed requests, not an exhaustive GitHub/CUA census. Per-query totals and overlapping shards are not a global union.'}
    if 'epochs' in state:
        result.update(epochs=copy.deepcopy(state['epochs']), current_epoch_id=state['current_epoch_id'],
                      query_rechecks_count=len(state.get('query_rechecks', [])))
    return result


def build_candidate_export(ledger_bytes, raw_dir, catalog_bytes):
    state = scan.validate_state(scan.strict_json(ledger_bytes))
    receipts, body_count = _replay(state, raw_dir)
    rows = [public_record(row, receipts) for row in sorted(state['records'].values(), key=lambda r: r['repository_id'])]
    body = b''.join(encoded(row) for row in rows)
    verification = {'mode': 'full_retained_replay', 'historical_raw_replayed': True,
                    'baseline_observation_sha256': None, 'baseline_checkpoint_sha256': None,
                    'successful_receipts_replayed': sum(r['raw_body_retained'] for r in state['receipts']),
                    'primary_bodies_replayed': body_count}
    return body, manifest_for_records(state, body, catalog_bytes,
        source_ledger_sha256=digest(ledger_bytes), verification=verification)


def manifest_for_records(state, body, catalog_bytes, *, source_ledger_sha256, verification,
                         checkpoint_state_sha256=None):
    """Describe already verified public rows; incremental callers declare their boundary."""
    rows = [scan.strict_json(line) for line in body.splitlines() if line.strip()]
    omissions = [{'id': r['id'], **o} for r in rows for o in r['omitted_fields']]
    manifest = {'schema_version': 1, 'provider': 'github', 'scope': 'candidate-observations',
                'observation_snapshot_sha256': digest(body), 'source_ledger_sha256': source_ledger_sha256,
                'verification': verification, 'checkpoint_state_sha256': checkpoint_state_sha256,
                'input_fingerprints': [{'id': i['id'], 'files': copy.deepcopy(i['files'])} for i in state['inputs']], 'scan': _summary(state),
                'active_catalog_context': catalog_context(catalog_bytes),
                'count': {'value': len(rows), 'unit': 'repositories'},
                'supporting_primary_bodies': len({e['sha256'] for r in rows for e in r['evidence']}),
                'observed_from': min((r['first_observed_at'] for r in rows), key=scan.timestamp, default=None),
                'observed_through': max((r['last_observed_at'] for r in rows), key=scan.timestamp, default=None),
                'review_policy': POLICY, 'count_policy': COUNT_POLICY,
                'privacy': {'checked_records': len(rows), 'omitted_fields': omissions, 'policy': PRIVACY_POLICY},
                'export': {'file': RECORD_FILE, 'format': 'JSONL', 'bytes': len(body), 'sha256': digest(body)},
                'schema': '/schemas/' + SCHEMAS[0], 'manifest_schema': '/schemas/' + SCHEMAS[1]}
    validate_candidate_export(body, manifest, catalog_bytes=catalog_bytes)
    return manifest


def validate_candidate_export(body, manifest, *, catalog_bytes=None):
    """Validate public files without claiming access to undistributed raw bodies."""
    if not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1:
        raise ValueError('Unsupported candidate export manifest')
    required = {'schema_version', 'provider', 'scope', 'observation_snapshot_sha256', 'source_ledger_sha256',
                'input_fingerprints', 'scan', 'active_catalog_context', 'count', 'supporting_primary_bodies',
                'observed_from', 'observed_through', 'review_policy', 'count_policy', 'privacy', 'export', 'schema', 'manifest_schema'}
    optional = {'verification', 'checkpoint_state_sha256'}
    if set(manifest) - optional != required or manifest['provider'] != 'github' or manifest['scope'] != 'candidate-observations':
        raise ValueError('Unexpected candidate manifest fields or scope')
    if manifest['review_policy'] != POLICY or manifest['count_policy'] != COUNT_POLICY:
        raise ValueError('Candidate review/count boundaries differ')
    checked_sha(manifest['source_ledger_sha256'])
    if 'verification' in manifest or 'checkpoint_state_sha256' in manifest:
        if not optional <= set(manifest): raise ValueError('Incomplete candidate verification boundary')
        if manifest['checkpoint_state_sha256'] is not None: checked_sha(manifest['checkpoint_state_sha256'])
        verification = manifest['verification']
        keys = {'mode', 'historical_raw_replayed', 'baseline_observation_sha256', 'baseline_checkpoint_sha256',
                'successful_receipts_replayed', 'primary_bodies_replayed'}
        if not isinstance(verification, dict) or set(verification) != keys or verification['mode'] not in {'full_retained_replay', 'incremental_retained_replay'}:
            raise ValueError('Invalid candidate verification boundary')
        checked_count(verification['successful_receipts_replayed']); checked_count(verification['primary_bodies_replayed'])
        if verification['mode'] == 'full_retained_replay':
            if verification['historical_raw_replayed'] is not True or any(verification[k] is not None for k in ('baseline_observation_sha256', 'baseline_checkpoint_sha256')):
                raise ValueError('Invalid full-history verification claim')
        else:
            if verification['historical_raw_replayed'] is not False: raise ValueError('Incremental validation must not claim historical raw replay')
            for key in ('baseline_observation_sha256', 'baseline_checkpoint_sha256'): checked_sha(verification[key])
    if manifest['observation_snapshot_sha256'] != digest(body):
        raise ValueError('Candidate observation snapshot fingerprint mismatch')
    if (not equal_json(manifest['export'], {'file': RECORD_FILE, 'format': 'JSONL', 'bytes': len(body), 'sha256': digest(body)})
            or manifest['schema'] != '/schemas/' + SCHEMAS[0] or manifest['manifest_schema'] != '/schemas/' + SCHEMAS[1]):
        raise ValueError('Candidate artifact differs from its manifest')
    rows = [scan.strict_json(line) for line in body.splitlines() if line.strip()]
    receipts = {}
    omissions = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != PUBLIC_FIELDS:
            raise ValueError('Unexpected public candidate fields')
        source = {key: row[key] for key in META_FIELDS - {'description', 'topics'}}
        source.update(id=row['repository_id'], html_url=row['url'], description=row['source_description'], topics=row['github_topics'])
        try:
            normalized = scan.repository_metadata(source)
        except scan.Rejected:
            raise ValueError('Invalid public candidate metadata') from None
        expected = {key: row[key] for key in META_FIELDS - {'description', 'topics'}} | {'description': row['source_description'], 'topics': row['github_topics']}
        if not equal_json(normalized, expected):
            raise ValueError('Public candidate identity/state mismatch')
        if digest(encoded({k: v for k, v in row.items() if k != 'record_sha256'})) != row['record_sha256']:
            raise ValueError('Candidate record fingerprint mismatch')
        if not isinstance(row['known_names'], list) or row['known_names'] != sorted(set(row['known_names'])) or row['full_name'] not in row['known_names']:
            raise ValueError('Invalid observed repository names')
        for name in row['known_names']: scan.public_name(name)
        if not isinstance(row['omitted_fields'], list) or len({encoded(v) for v in row['omitted_fields']}) != len(row['omitted_fields']):
            raise ValueError('Invalid privacy omission list')
        for item in row['omitted_fields']:
            if not isinstance(item, dict) or set(item) != {'field', 'reason'} or item['field'] != 'source_description' or item['reason'] not in OMISSION_REASONS or row['source_description'] is not None:
                raise ValueError('Invalid explicit privacy omission')
            omissions.append({'id': row['id'], **item})
        for value in [row['source_description'], row['full_name'], row['url'], *row['known_names'], *row['github_topics']]:
            if privacy_findings(value):
                raise ValueError('Unsafe public candidate field: ' + row['id'])
        if not isinstance(row['evidence'], list) or not row['evidence']:
            raise ValueError('Candidate lacks primary observation receipts')
        for ev in row['evidence']:
            if not isinstance(ev, dict) or set(ev) != EVIDENCE_FIELDS:
                raise ValueError('Invalid candidate evidence fields')
            if (not re.fullmatch(r'receipt:[0-9a-f]{64}', str(ev['receipt_id']))
                    or not re.fullmatch(r'run:[0-9a-f]{24}', str(ev['run_id']))
                    or not re.fullmatch(r'(?:search:[0-9a-f]{24}|existing:[0-9a-f]{64})', str(ev['query_id']))):
                raise ValueError('Invalid candidate receipt identity')
            scan.safe_api_url(ev['url']); checked_sha(ev['sha256']); checked_count(ev['bytes']); checked_count(ev['position'])
            if digest(ev['url'].encode()) != ev['request_url_sha256'] or scan.timestamp(ev['retrieved_at']) < scan.timestamp(ev['observed_at']):
                raise ValueError('Invalid candidate source receipt binding')
            if ev['receipt_id'] in receipts and not equal_json(receipts[ev['receipt_id']], ev):
                raise ValueError('Conflicting repeated primary receipt')
            receipts[ev['receipt_id']] = ev
        if (row['metadata_receipt_id'] != row['evidence'][-1]['receipt_id']
                or row['first_observed_at'] != row['evidence'][0]['observed_at']
                or row['last_observed_at'] != row['evidence'][-1]['observed_at']
                or len({ev['receipt_id'] for ev in row['evidence']}) != len(row['evidence'])
                or any(scan.timestamp(a['observed_at']) > scan.timestamp(b['observed_at']) for a, b in zip(row['evidence'], row['evidence'][1:]))):
            raise ValueError('Candidate observation dates differ from its evidence')
    ids = [row['repository_id'] for row in rows]
    if ids != sorted(set(ids)) or not equal_json(manifest['count'], {'value': len(rows), 'unit': 'repositories'}):
        raise ValueError('Candidate count/order differs from unique numeric repositories')
    if type(manifest['supporting_primary_bodies']) is not int or manifest['supporting_primary_bodies'] != len({ev['sha256'] for ev in receipts.values()}):
        raise ValueError('Invalid supporting primary-body count')
    if (manifest['observed_from'] != min((r['first_observed_at'] for r in rows), key=scan.timestamp, default=None)
            or manifest['observed_through'] != max((r['last_observed_at'] for r in rows), key=scan.timestamp, default=None)):
        raise ValueError('Candidate observation window differs from its records')
    privacy = manifest['privacy']
    if (not isinstance(privacy, dict) or set(privacy) != {'checked_records', 'omitted_fields', 'policy'}
            or type(privacy['checked_records']) is not int or privacy['checked_records'] != len(rows)
            or privacy['omitted_fields'] != omissions or privacy['policy'] != PRIVACY_POLICY):
        raise ValueError('Privacy audit does not match exported records')
    context = manifest['active_catalog_context']
    if not isinstance(context, dict) or set(context) != {'sha256', 'records', 'role'} or context['role'] != CONTEXT_POLICY:
        raise ValueError('Invalid active catalog comparison context')
    checked_sha(context['sha256']); checked_count(context['records'])
    if catalog_bytes is not None and not equal_json(context, catalog_context(catalog_bytes)):
        raise ValueError('Candidate publication context differs from active catalog bytes')
    _validate_public_provenance(manifest, rows, receipts)
    return rows


def _validate_public_provenance(manifest, rows, receipts):
    inputs = {}
    if not isinstance(manifest['input_fingerprints'], list) or not manifest['input_fingerprints']: raise ValueError('Invalid scan input fingerprints')
    for item in manifest['input_fingerprints']:
        if not isinstance(item, dict) or set(item) != {'id', 'files'} or not isinstance(item['files'], dict) or set(item['files']) != set(scan.INPUTS):
            raise ValueError('Unexpected public input fingerprint fields')
        for value in item['files'].values():
            if not isinstance(value, dict) or set(value) != {'bytes', 'sha256'}: raise ValueError('Invalid input file fingerprint')
            checked_count(value['bytes']); checked_sha(value['sha256'])
        if item['id'] != digest(json.dumps(item['files'], sort_keys=True).encode()) or item['id'] in inputs:
            raise ValueError('Invalid or duplicate scan input fingerprint')
        inputs[item['id']] = item
    report = manifest['scan']
    epoch_fields = {'epochs', 'current_epoch_id', 'query_rechecks_count'}
    if not isinstance(report, dict) or set(report) - epoch_fields != {'configuration', 'runs', 'queries', 'request_outcomes', 'global_completeness_established', 'limit'}:
        raise ValueError('Unexpected scan summary fields')
    has_epochs = bool(set(report) & epoch_fields)
    if has_epochs and not epoch_fields <= set(report): raise ValueError('Incomplete public query epoch metadata')
    if report['global_completeness_established'] is not False or report['limit'] != 'Bounded observed requests, not an exhaustive GitHub/CUA census. Per-query totals and overlapping shards are not a global union.':
        raise ValueError('Candidate observations cannot establish global completeness')
    config = report['configuration']
    if (not isinstance(config, dict) or set(config) != {'topics', 'created_after', 'created_before'}
            or not isinstance(config['topics'], list) or not config['topics']
            or len(config['topics']) != len(set(config['topics'])) or any(t not in scan.TOPICS for t in config['topics'])
            or scan.date.fromisoformat(config['created_after']) > scan.date.fromisoformat(config['created_before'])):
        raise ValueError('Invalid public scan configuration')
    queries = {}
    if not isinstance(report['queries'], list) or not isinstance(report['runs'], list): raise ValueError('Invalid scan summary lists')
    for query in report['queries']:
        if not isinstance(query, dict) or query.get('id') in queries: raise ValueError('Duplicate public query')
        if query.get('kind') == 'search':
            expected_fields = {'id', 'kind', 'status', 'topic', 'created_after', 'created_before', 'reported_total'}
            if has_epochs: expected_fields.add('parent_id')
            if set(query) != expected_fields:
                raise ValueError('Unexpected public search fields')
            expected = scan.search_query(query['topic'], query['created_after'], query['created_before'])
            if (query['id'] != expected['id'] or (not has_epochs and query['topic'] not in config['topics'])
                    or query['status'] not in {'pending', 'split', 'blocked_single_day_window', 'observed_pages_exhausted', 'partial_results', 'partial_api_window'}
                    or (not has_epochs and not config['created_after'] <= query['created_after'] <= query['created_before'] <= config['created_before'])):
                raise ValueError('Invalid public query cohort')
            scan.date.fromisoformat(query['created_after']); scan.date.fromisoformat(query['created_before'])
            if query['reported_total'] is not None: checked_count(query['reported_total'])
        elif query.get('kind') == 'existing':
            if (set(query) != {'id', 'kind', 'status', 'input_id'} or query['input_id'] not in inputs
                    or query['id'] != 'existing:' + query['input_id'] or query['status'] not in {'pending', 'exhausted', 'superseded_input'}):
                raise ValueError('Invalid public existing-candidate cohort')
        else: raise ValueError('Unknown public query kind')
        queries[query['id']] = query
    if has_epochs:
        checked_count(report['query_rechecks_count'])
        scan.validate_public_epochs(config, report['epochs'], report['current_epoch_id'], report['queries'])
    run_fields = {'id', 'input_id', 'started_at', 'finished_at', 'status', 'requests_attempted',
                  'before_unique_repositories', 'new_unique_repositories', 'accepted_metadata_rows', 'after_unique_repositories'}
    runs = {}; seen = set()
    for run in report['runs']:
        if (not isinstance(run, dict) or set(run) != run_fields or not re.fullmatch(r'run:[0-9a-f]{24}', str(run['id']))
                or run['id'] in runs or run['input_id'] not in inputs
                or run['status'] not in {'rate_limited', 'wall_budget', 'request_budget', 'partial', 'finished'}
                or scan.timestamp(run['started_at']) > scan.timestamp(run['finished_at'])):
            raise ValueError('Invalid public scan round')
        run_receipts = {key for key, value in receipts.items() if value['run_id'] == run['id']}
        accepted = {row['repository_id'] for row in rows if any(e['receipt_id'] in run_receipts for e in row['evidence'])}
        hits = sum(1 for row in rows for ev in row['evidence'] if ev['receipt_id'] in run_receipts)
        expected = {'before_unique_repositories': len(seen), 'new_unique_repositories': len(accepted-seen),
                    'accepted_metadata_rows': hits, 'after_unique_repositories': len(seen | accepted)}
        if any(type(run[key]) is not int or run[key] != count for key, count in expected.items()) or checked_count(run['requests_attempted']) < len(run_receipts):
            raise ValueError('Public scan counts differ from candidate evidence')
        seen |= accepted; runs[run['id']] = run
    if seen != {row['repository_id'] for row in rows}: raise ValueError('Public round population differs from candidate records')
    for ev in receipts.values():
        if ev['query_id'] not in queries or ev['run_id'] not in runs: raise ValueError('Primary receipt lacks public cohort/round')
        query, run = queries[ev['query_id']], runs[ev['run_id']]
        parts = urllib.parse.urlsplit(ev['url'])
        if not scan.timestamp(run['started_at']) <= scan.timestamp(ev['observed_at']) <= scan.timestamp(ev['retrieved_at']) <= scan.timestamp(run['finished_at']):
            raise ValueError('Primary receipt lies outside its scan round')
        if query['kind'] == 'existing':
            if query['input_id'] != run['input_id'] or not parts.path.startswith('/repos/'):
                raise ValueError('Existing receipt has a different input context')
        else:
            params = urllib.parse.parse_qs(parts.query)
            if (parts.path != '/search/repositories' or params.get('page') != [str(ev['position'])]
                    or params.get('q') != [scan.search_query(query['topic'], query['created_after'], query['created_before'])['query']]):
                raise ValueError('Public primary receipt differs from its query')
    outcomes = report['request_outcomes']
    allowed = {'accepted', 'accepted_with_rejections', 'rejected', 'quarantined', 'rate_limited', 'unavailable', 'redirect_not_followed', 'fetch_failed', 'response_too_large', 'malformed_response'}
    if not isinstance(outcomes, dict) or set(outcomes) - allowed:
        raise ValueError('Invalid public request outcomes')
    if sum(checked_count(n) for n in outcomes.values()) != sum(r['requests_attempted'] for r in runs.values()) or outcomes.get('accepted', 0) < len(receipts):
        raise ValueError('Public request outcome count differs from recorded rounds')


def write_pair(destination, body, manifest):
    """Publish the two files together, restoring the prior pair after a failure."""
    destination = scan.checked_output(destination)
    destination.mkdir(parents=True, exist_ok=True)
    payloads = {RECORD_FILE: body, MANIFEST_FILE: manifest if isinstance(manifest, bytes) else encoded(manifest, pretty=True)}
    old = {}
    for name in FILES:
        path = scan.checked_output(destination / name)
        if path.exists() and not path.is_file(): raise ValueError('Output is not a regular file')
        old[name] = path.read_bytes() if path.exists() else None
    with tempfile.TemporaryDirectory(prefix='candidate-export-', dir=destination) as temporary:
        stage = Path(temporary)
        for name, payload in payloads.items(): (stage / name).write_bytes(payload)
        replaced = []
        try:
            for name in FILES:
                os.replace(stage / name, destination / name); replaced.append(name)
        except OSError:
            for name in reversed(replaced):
                if old[name] is None: (destination / name).unlink()
                else: (destination / name).write_bytes(old[name])
            raise


def copy_public_candidates(source, destination, catalog_bytes):
    """Optional durable inputs; no raw cache dependency during a website build."""
    source, destination = Path(source), Path(destination)
    if any((source / name).is_symlink() for name in FILES):
        raise ValueError('Durable candidate inputs cannot be symlinks')
    present = [(source / name).exists() for name in FILES]
    if not any(present):
        for name in FILES: public_file(destination, name).unlink(missing_ok=True)
        return None
    if not all(present): raise ValueError('Candidate observations require both durable input files')
    body = file_bytes(public_file(source, RECORD_FILE))
    manifest = scan.strict_json(file_bytes(public_file(source, MANIFEST_FILE)))
    validate_candidate_export(body, manifest)
    manifest['active_catalog_context'] = catalog_context(catalog_bytes)
    validate_candidate_export(body, manifest, catalog_bytes=catalog_bytes)
    for name in FILES: public_file(destination, name)
    write_pair(destination.resolve(), body, manifest)
    return manifest


def candidate_publication_plan(build, destination):
    """Use the download manifest as authority, never stray build-directory files."""
    build, destination = Path(build), Path(destination)
    main = scan.strict_json(file_bytes(public_file(build, 'downloads/manifest.json')))
    if not isinstance(main, dict) or type(main.get('schema_version')) is not int or main['schema_version'] != 1 or not isinstance(main.get('artifacts'), list):
        raise ValueError('Candidate publication requires a download manifest')
    owned = {('/' + name) for name in PUBLIC_PATHS}
    entries = [entry for entry in main['artifacts'] if isinstance(entry, dict) and entry.get('path') in owned]
    if entries and (len(entries) != len(owned) or {e['path'] for e in entries} != owned):
        raise ValueError('Download manifest has an incomplete candidate observation bundle')
    targets = {name: public_file(destination, name) for name in PUBLIC_PATHS}
    payloads = {}
    for entry in entries:
        relative = entry['path'][1:]
        body = file_bytes(public_file(build, relative))
        if digest(body) != entry.get('sha256') or type(entry.get('bytes')) is not int or len(body) != entry['bytes']:
            raise ValueError('Candidate publication artifact fingerprint mismatch')
        payloads[relative] = body
    if entries:
        catalog_bytes = file_bytes(public_file(build, 'downloads/catalog.jsonl'))
        if main.get('catalog_sha256') != digest(catalog_bytes):
            raise ValueError('Candidate publication has a mismatched catalog comparison context')
        manifest = scan.strict_json(payloads['downloads/' + MANIFEST_FILE])
        rows = validate_candidate_export(payloads['downloads/' + RECORD_FILE], manifest, catalog_bytes=catalog_bytes)
        expected = {
            '/downloads/' + RECORD_FILE: ('github-candidates', 'provenance', 'candidate-observations', len(rows), 'repositories'),
            '/downloads/' + MANIFEST_FILE: ('github-candidates-manifest', 'provenance', 'candidate-observations', 1, 'reports'),
            **{'/schemas/' + name: (name.replace('.', '-'), 'contracts', 'contract', 1, 'schemas') for name in SCHEMAS},
        }
        for entry in entries:
            identity, group, scope, count, unit = expected[entry['path']]
            if (entry.get('id'), entry.get('group'), entry.get('scope')) != (identity, group, scope) or not equal_json(entry.get('count'), {'value': count, 'unit': unit}):
                raise ValueError('Candidate publication count or scope mismatch')
        for name in SCHEMAS:
            if payloads['schemas/' + name] != file_bytes(ROOT / 'schemas' / name):
                raise ValueError('Candidate publication schema differs from this source checkout')
    return {'targets': targets, 'payloads': payloads}


def candidate_copy_ignores(build, folder, names):
    relative = Path(folder).relative_to(Path(build))
    return [name for name in names if (relative / name).as_posix() in PUBLIC_PATHS]


def apply_candidate_publication(plan):
    """Apply previously validated bytes; orphans are excluded from generic copying."""
    if not plan['payloads']:
        for target in plan['targets'].values(): target.unlink(missing_ok=True)
        return
    for name in SCHEMAS:
        target = plan['targets']['schemas/' + name]
        target.parent.mkdir(parents=True, exist_ok=True)
        scan.atomic_write(target, plan['payloads']['schemas/' + name])
    body = plan['payloads']['downloads/' + RECORD_FILE]
    write_pair(plan['targets']['downloads/' + RECORD_FILE].parent, body, plan['payloads']['downloads/' + MANIFEST_FILE])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Explicit frozen scan ledger; never a mutable cursor by default.')
    parser.add_argument('--raw-dir', type=Path, required=True, help='Ignored SHA-named primary API response bodies.')
    parser.add_argument('--catalog', type=Path, default=ROOT / 'data/catalog.jsonl', help='Active catalog bytes for comparison context only.')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist/candidate-observations')
    args = parser.parse_args(argv)
    try:
        body, manifest = build_candidate_export(file_bytes(args.input), args.raw_dir, file_bytes(args.catalog))
        write_pair(args.output_dir, body, manifest)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('Candidate export rejected: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps({'records': manifest['count']['value'], 'unit': 'repositories',
                      'observation_snapshot_sha256': manifest['observation_snapshot_sha256'],
                      'source_ledger_sha256': manifest['source_ledger_sha256'],
                      'privacy_omissions': manifest['privacy']['omitted_fields']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
