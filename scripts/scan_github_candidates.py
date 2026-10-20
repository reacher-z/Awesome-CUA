#!/usr/bin/env python3
"""Bounded public GitHub metadata discovery, separate from editorial approval.

The only network operation is an unauthenticated GET to an allowlisted GitHub
API route. The default output is ignored cache; no catalog inputs are modified.
"""
from __future__ import annotations

import argparse
import copy
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import email.utils
import hashlib
import http.client
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from catalog import ROOT, atomic_write, canonical
from repository_identity import repository_aliases
from network_budget import BudgetDeferred, budget_from_environment

TOPICS = frozenset({'computer-use', 'gui-agent', 'gui-agents', 'gui-automation',
                    'desktop-automation', 'browser-agent', 'browser-agents',
                    'browser-automation', 'android-automation'})
DEFAULT_TOPICS = ('computer-use', 'gui-agent', 'browser-automation')
INPUTS = ('catalog.jsonl', 'candidates.jsonl', 'primary-evidence.jsonl',
          'repository-aliases.json', 'candidate-reviews.json')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+\Z', re.ASCII)
SHA = re.compile(r'[0-9a-f]{64}\Z', re.ASCII)
POLICY = ('Public primary metadata observations, not active catalog records or '
          'editorial approval. Counts use numeric repository IDs; query occurrences overlap.')
MAX_BODY = 5_000_000
INTERVAL = 6.5
PAGE_SIZE = 100
SPLIT_THRESHOLD = 900
QUERY_PROGRESS = ('status', 'next_page', 'reported_total', 'total_changed',
                  'incomplete_results_seen', 'seen_repository_ids', 'rejected_rows', 'last_attempt')


def digest(body):
    return hashlib.sha256(body).hexdigest()


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def strict_json(body):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('non-finite JSON number')
    return json.loads(body, object_pairs_hook=pairs, parse_constant=invalid)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be a string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp must have a timezone')
    return result


def public_name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value) or value.endswith('.git'):
        raise ValueError('invalid repository name')
    if value.rsplit('/', 1)[1] in {'.', '..'}:
        raise ValueError('invalid repository name')
    return value


def safe_api_url(url):
    """No arbitrary hosts, credentials, query keys, userinfo or redirect targets."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != 'https' or parts.netloc != 'api.github.com' or parts.fragment:
        raise ValueError('not an allowed public API URL')
    if parts.path.startswith('/repos/'):
        public_name(parts.path.removeprefix('/repos/'))
        if parts.query:
            raise ValueError('repository endpoint has a query')
    elif parts.path == '/search/repositories':
        params = urllib.parse.parse_qs(parts.query, strict_parsing=True)
        if set(params) != {'q', 'per_page', 'page', 'sort', 'order'} or any(len(v) != 1 for v in params.values()):
            raise ValueError('unsupported search parameters')
        match = re.fullmatch(r'topic:([a-z-]+) is:public fork:false created:(\d{4}-\d\d-\d\d)\.\.(\d{4}-\d\d-\d\d)', params['q'][0])
        if not match or match[1] not in TOPICS or date.fromisoformat(match[2]) > date.fromisoformat(match[3]):
            raise ValueError('unsupported query cohort')
        if params['per_page'] != [str(PAGE_SIZE)] or params['sort'] != ['updated'] or params['order'] != ['asc']:
            raise ValueError('unsupported search ordering or page size')
        if not re.fullmatch(r'[1-9]|10', params['page'][0]):
            raise ValueError('search page outside the API window')
    else:
        raise ValueError('unsupported API route')
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http_get(url, timeout):
    """No auth, cookies, environment proxies, retries or automatic redirects."""
    safe_api_url(url)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Awesome-CUA/public-candidate-scan (+https://github.com/reacher-z/Awesome-CUA)',
        'Accept': 'application/vnd.github+json',
    })
    open_url = opener.open  # Binary HTTP transport, not a text-file open.
    try:
        with open_url(request, timeout=timeout) as response:
            return response.status, response.read(MAX_BODY + 1), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(MAX_BODY + 1), dict(error.headers)
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError):
        # Exception text can contain an unverified request URL: never persist it.
        return None, b'', {}


def _transport_get(url, timeout, *, transport, budget=None, on_attempt=None, remaining_seconds=None):
    """Charge the shared round without treating preflight deferral as HTTP I/O."""
    safe_api_url(url)
    attempt = budget.reserve(url, min_interval=INTERVAL) if budget else None
    try:
        if budget:
            timeout = min(timeout, budget.timeout(timeout))
        if remaining_seconds is not None:
            timeout = min(timeout, remaining_seconds())
        if timeout <= 0:
            raise BudgetDeferred('wall_budget', 'api.github.com')
        if on_attempt is not None:
            on_attempt()
        try:
            status, body, headers = transport(url, timeout)
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError):
            status, body, headers = None, b'', {}
        if not isinstance(body, bytes) or not isinstance(headers, dict):
            raise ValueError('transport returned invalid types')
        if budget:
            budget.observe_response(url, status, headers, attempt=attempt,
                                    rate_limited=rate_limited(status, headers, body))
        return status, body, headers
    except BaseException:
        if budget and attempt is not None:
            budget.observe_response(url, None, attempt=attempt)
        raise


def public_get(url, timeout):
    return _transport_get(url, timeout, transport=_http_get, budget=budget_from_environment())


class Rejected(ValueError):
    pass


def repository_metadata(item):
    """Allowlist public fields only; ignore owner/contact/permissions/HTML URLs."""
    if not isinstance(item, dict):
        raise Rejected('malformed')
    if item.get('private') is not False:
        raise Rejected('private_or_unknown')
    if item.get('visibility') != 'public':
        raise Rejected('visibility_not_public_or_unknown')
    if item.get('fork') is not False:
        raise Rejected('fork_or_unknown')
    rid = item.get('id')
    if type(rid) is not int or rid <= 0:
        raise Rejected('malformed')
    try:
        name = public_name(item.get('full_name'))
        expected = 'https://github.com/' + name
        if item.get('html_url') != expected:
            raise ValueError('canonical URL differs')
        description = item.get('description')
        if description is not None and (not isinstance(description, str) or len(description) > 2000 or any(ord(c) < 32 for c in description)):
            raise ValueError('invalid public description')
        topics = item.get('topics', [])
        if not isinstance(topics, list) or len(topics) > 100 or any(not isinstance(t, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,49}', t) for t in topics):
            raise ValueError('invalid topics')
        if type(item.get('archived')) is not bool:
            raise ValueError('invalid archived flag')
        dates = {}
        for key in ('created_at', 'updated_at', 'pushed_at'):
            value = item.get(key)
            if value is not None:
                timestamp(value)
            elif key != 'pushed_at':
                raise ValueError('missing repository timestamp')
            dates[key] = value
    except (ValueError, TypeError):
        raise Rejected('malformed') from None
    return {'id': 'github-repository:' + str(rid), 'repository_id': rid,
            'canonical_id': 'github:' + name.casefold(), 'full_name': name,
            'url': expected, 'description': description, 'topics': sorted(set(topics)),
            'private': False, 'visibility': 'public', 'fork': False,
            'archived': item['archived'], **dates,
            'metadata_status': 'primary_metadata_observed',
            'review_status': 'candidate', 'scope': 'relevance_pending'}


def input_snapshot(root):
    raw = {name: (root / 'data' / name).read_bytes() for name in INPUTS}
    data = {name: ([strict_json(line) for line in body.splitlines() if line.strip()]
                  if name.endswith('.jsonl') else strict_json(body)) for name, body in raw.items()}
    catalog = data['catalog.jsonl']
    aliases = repository_aliases(data['repository-aliases.json'], catalog)
    observed = {r['id'] for r in data['primary-evidence.jsonl'] if r.get('ok') is True and r.get('status') == 200}
    set_aside = {r.get('id') for r in data['candidate-reviews.json'] if r.get('decision') == 'not_a_resource'}
    names = {}
    for row in data['candidates.jsonl']:
        parsed = canonical(row.get('url'))
        if not parsed or parsed[2] != 'github' or row.get('id') in set_aside:
            continue
        rid = aliases.get(parsed[0], parsed[0])
        if rid in observed:
            continue
        name = rid.removeprefix('github:')
        public_name(name)
        names[name] = max(names.get(name, 0), len({o['source_id'] for o in row.get('discovered_in', [])}))
    seeds = sorted(names, key=lambda n: (-names[n], n))
    files = {name: {'sha256': digest(body), 'bytes': len(body)} for name, body in raw.items()}
    sid = digest(json.dumps(files, sort_keys=True).encode())
    return {'id': sid, 'files': files, 'active_records': len(catalog),
            'curated_records': sum(r['review_status'] == 'curated' for r in catalog),
            'existing_seed_count': len(seeds)}, seeds


def search_query(topic, after, before, parent=None):
    query = f'topic:{topic} is:public fork:false created:{after}..{before}'
    return {'id': 'search:' + digest(query.encode())[:24], 'kind': 'search',
            'topic': topic, 'created_after': after, 'created_before': before,
            'query': query, 'parent_id': parent, 'next_page': 1,
            'status': 'pending', 'last_attempt': 0, 'reported_total': None,
            'total_changed': False, 'incomplete_results_seen': False,
            'seen_repository_ids': [], 'rejected_rows': 0}


def checked_output(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('output paths cannot traverse parents')
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError('output paths cannot be symlinks')
    return path


def _state_digest(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def _epoch(configuration, roots, at, reason, previous=None, source_sha=None):
    identity = [configuration, roots, reason, previous]
    return {'id': 'epoch:' + _state_digest(identity)[:24],
            'configuration': copy.deepcopy(configuration), 'root_query_ids': list(roots),
            'created_at': at, 'reason': reason, 'previous_epoch_id': previous,
            'source_state_sha256': source_sha}


def _epoch_nodes(state, epoch_id=None):
    epoch = next(e for e in state['epochs'] if e['id'] == (epoch_id or state['current_epoch_id']))
    pending = list(epoch['root_query_ids']); seen = set()
    while pending:
        qid = pending.pop()
        if qid in seen:
            continue
        seen.add(qid)
        pending.extend(q['id'] for q in state['queries'] if q.get('parent_id') == qid)
    return seen


def _epoch_complete(state, epoch_id=None):
    queries = {q['id']: q for q in state['queries']}
    nodes = _epoch_nodes(state, epoch_id)
    for qid in nodes:
        query = queries[qid]
        if query['status'] == 'observed_pages_exhausted':
            continue
        if query['status'] != 'split':
            return False
        children = sorted((q for q in state['queries'] if q.get('parent_id') == qid), key=lambda q: q['created_after'])
        if (len(children) != 2 or children[0]['created_after'] != query['created_after']
                or children[1]['created_before'] != query['created_before']
                or date.fromisoformat(children[1]['created_after']) - date.fromisoformat(children[0]['created_before']) != timedelta(days=1)):
            return False
    return True


def migrate_state(state, *, at=None):
    """Explicit, pure v1 migration; original records and receipt/run prefixes survive."""
    validate_state(state)
    result = copy.deepcopy(state)
    if result['schema_version'] == 2:
        return result
    at = at or utcnow(); timestamp(at)
    roots = [search_query(topic, result['configuration']['created_after'], result['configuration']['created_before'])['id']
             for topic in result['configuration']['topics']]
    if any(not any(q['id'] == qid for q in result['queries']) for qid in roots):
        raise ValueError('v1 migration requires every frozen topic root')
    epoch = _epoch(result['configuration'], roots, at, 'v1_migration', source_sha=_state_digest(state))
    result.update(schema_version=2, epochs=[epoch], current_epoch_id=epoch['id'], query_rechecks=[])
    return validate_state(result)


def expand_topics(state, topics, *, at=None):
    """Add explicit topic backfills from the original historical floor, never reset old roots."""
    result = migrate_state(state, at=at)
    topics = list(dict.fromkeys(topics))
    old = result['configuration']
    if not topics or any(topic not in TOPICS for topic in topics) or not set(old['topics']) <= set(topics):
        raise ValueError('topic expansion only permits supported additions')
    added = [topic for topic in topics if topic not in old['topics']]
    if not added:
        return result
    at = at or utcnow(); timestamp(at)
    current = next(e for e in result['epochs'] if e['id'] == result['current_epoch_id'])
    queries = {q['id']: q for q in result['queries']}
    roots = {queries[qid]['topic']: qid for qid in current['root_query_ids']}
    floor = result['epochs'][0]['configuration']['created_after']
    for topic in added:
        query = search_query(topic, floor, old['created_before'])
        result['queries'].append(query); roots[topic] = query['id']
    config = {'topics': topics, 'created_after': floor, 'created_before': old['created_before']}
    epoch = _epoch(config, [roots[t] for t in topics], at, 'topic_expansion', current['id'])
    result['epochs'].append(epoch); result['current_epoch_id'] = epoch['id']; result['configuration'] = config
    return validate_state(result)


def _retry_partial_queries(state, at, limit=2):
    """A retry starts a fresh traversal; old evidence and its progress remain auditable."""
    active = _epoch_nodes(state)
    queries = sorted((q for q in state['queries'] if q['id'] in active and q['status'] in {'partial_results', 'partial_api_window'}),
                     key=lambda q: (q['last_attempt'], q['id']))[:limit]
    for query in queries:
        boundary = len(state['receipts'])
        event = {'id': 'recheck:' + _state_digest([query['id'], len(state['query_rechecks']), boundary])[:24],
                 'query_id': query['id'], 'epoch_id': state['current_epoch_id'],
                 'restarted_at': at, 'receipt_boundary': boundary,
                 'previous': {key: copy.deepcopy(query[key]) for key in QUERY_PROGRESS}}
        state['query_rechecks'].append(event)
        query.update(status='pending', next_page=1, reported_total=None, total_changed=False,
                     incomplete_results_seen=False, seen_repository_ids=[], rejected_rows=0, last_attempt=0)


def _advance_epoch(state, at):
    current = next(e for e in state['epochs'] if e['id'] == state['current_epoch_id'])
    previous = current['configuration']; today = str(timestamp(at).astimezone(timezone.utc).date())
    if today <= previous['created_before'] or not _epoch_complete(state):
        return
    # Inclusive lower bound repeats the final day of the preceding epoch.
    config = {'topics': list(previous['topics']), 'created_after': previous['created_before'], 'created_before': today}
    queries = [search_query(t, config['created_after'], config['created_before']) for t in config['topics']]
    state['queries'].extend(queries)
    epoch = _epoch(config, [q['id'] for q in queries], at, 'daily_continuation', current['id'])
    state['epochs'].append(epoch); state['current_epoch_id'] = epoch['id']; state['configuration'] = config


def validate_state(state):
    if not isinstance(state, dict) or type(state.get('schema_version')) is not int or state['schema_version'] not in {1, 2}:
        raise ValueError('unsupported scan ledger version')
    fields = {'schema_version', 'provider', 'policy', 'configuration', 'inputs', 'records', 'queries', 'receipts', 'runs', 'deferred_until'}
    if state['schema_version'] == 2:
        fields |= {'epochs', 'current_epoch_id', 'query_rechecks'}
    if set(state) != fields:
        raise ValueError('unsupported scan ledger fields')
    if state['provider'] != 'github' or state['policy'] != POLICY:
        raise ValueError('unsupported ledger provider or policy')
    if not isinstance(state['records'], dict) or not isinstance(state['queries'], list) or not isinstance(state['receipts'], list) or not isinstance(state['runs'], list) or not isinstance(state['inputs'], list):
        raise ValueError('invalid scan ledger containers')
    config = state['configuration']
    if not isinstance(config, dict) or set(config) != {'topics', 'created_after', 'created_before'} or not isinstance(config['topics'], list) or not config['topics'] or any(t not in TOPICS for t in config['topics']):
        raise ValueError('invalid frozen query configuration')
    if date.fromisoformat(config['created_after']) > date.fromisoformat(config['created_before']):
        raise ValueError('invalid frozen date bounds')
    for key, row in state['records'].items():
        parsed = repository_metadata({**row, 'id': row.get('repository_id'), 'html_url': row.get('url')})
        if key != parsed['id'] or any(row.get(field) != value for field, value in parsed.items()):
            raise ValueError('invalid candidate identity or state')
        allowed = set(parsed) | {'first_observed_at', 'last_observed_at', 'known_names', 'occurrences'}
        if set(row) != allowed or not isinstance(row['known_names'], list) or not isinstance(row['occurrences'], list):
            raise ValueError('unsupported candidate fields')
        for name in row['known_names']:
            public_name(name)
        if row['full_name'] not in row['known_names'] or len(set(row['known_names'])) != len(row['known_names']):
            raise ValueError('invalid recorded public names')
        timestamp(row['first_observed_at']); timestamp(row['last_observed_at'])
    if state['deferred_until'] is not None:
        timestamp(state['deferred_until'])
    query_ids = set()
    for query in state['queries']:
        if not isinstance(query, dict) or query.get('id') in query_ids:
            raise ValueError('invalid or duplicate query')
        query_ids.add(query['id'])
        if query.get('kind') == 'search':
            expected = search_query(query['topic'], query['created_after'], query['created_before'], query['parent_id'])
            if set(query) != set(expected) or query['id'] != expected['id'] or query['query'] != expected['query']:
                raise ValueError('invalid search shard')
            if type(query['next_page']) is not int or not 1 <= query['next_page'] <= 11:
                raise ValueError('invalid search page')
            if query['topic'] not in config['topics'] or date.fromisoformat(query['created_after']) > date.fromisoformat(query['created_before']):
                raise ValueError('invalid search cohort')
            if query['status'] not in {'pending', 'split', 'blocked_single_day_window', 'observed_pages_exhausted', 'partial_results', 'partial_api_window'}:
                raise ValueError('invalid shard status')
            if any(type(query[k]) is not bool for k in ('total_changed', 'incomplete_results_seen')) or any(type(query[k]) is not int or query[k] < 0 for k in ('last_attempt', 'rejected_rows')):
                raise ValueError('invalid shard observations')
            if query['reported_total'] is not None and (type(query['reported_total']) is not int or query['reported_total'] < 0):
                raise ValueError('invalid reported total')
            if not isinstance(query['seen_repository_ids'], list) or any(type(i) is not int or i <= 0 for i in query['seen_repository_ids']):
                raise ValueError('invalid shard identities')
        elif query.get('kind') == 'existing':
            if set(query) != {'id', 'kind', 'input_id', 'seed_count', 'next_index', 'status', 'last_attempt'} or any(type(query[k]) is not int or query[k] < 0 for k in ('seed_count', 'next_index', 'last_attempt')):
                raise ValueError('invalid existing-candidate cursor')
            if query['status'] not in {'pending', 'exhausted', 'superseded_input'} or query['next_index'] > query['seed_count']:
                raise ValueError('invalid existing-candidate progress')
        else:
            raise ValueError('unknown query kind')
    input_ids = set()
    for item in state['inputs']:
        if not isinstance(item, dict) or set(item) != {'id', 'files', 'active_records', 'curated_records', 'existing_seed_count'} or not SHA.fullmatch(str(item['id'])) or set(item['files']) != set(INPUTS):
            raise ValueError('invalid input fingerprint')
        if item['id'] in input_ids or any(type(item[k]) is not int or item[k] < 0 for k in ('active_records', 'curated_records', 'existing_seed_count')):
            raise ValueError('invalid input counts')
        input_ids.add(item['id'])
        for info in item['files'].values():
            if not isinstance(info, dict) or set(info) != {'sha256', 'bytes'} or not SHA.fullmatch(str(info['sha256'])) or type(info['bytes']) is not int or info['bytes'] < 0:
                raise ValueError('invalid input file receipt')
        if item['id'] != digest(json.dumps(item['files'], sort_keys=True).encode()):
            raise ValueError('input fingerprint differs from file receipts')
    inputs_by_id = {item['id']: item for item in state['inputs']}
    queries_by_id = {query['id']: query for query in state['queries']}
    for query in state['queries']:
        if query['kind'] == 'existing':
            source = inputs_by_id.get(query['input_id'])
            if source is None or query['id'] != 'existing:' + query['input_id'] or query['seed_count'] != source['existing_seed_count']:
                raise ValueError('existing cohort differs from its input snapshot')
    run_ids = set()
    run_fields = {'id', 'input_id', 'started_at', 'finished_at', 'status', 'request_budget', 'wall_seconds_budget', 'requests_attempted', 'new_unique_repositories', 'accepted_metadata_rows', 'rejected_rows', 'unknown_requests', 'deferred_queries', 'deferred_query_ids', 'before_unique_repositories', 'after_unique_repositories'}
    optional_run_fields = {'shared_budget', 'strict_replay', 'epoch_id'}
    for run in state['runs']:
        if not isinstance(run, dict) or not run_fields <= set(run) or set(run) - run_fields - optional_run_fields or not re.fullmatch(r'run:[0-9a-f]{24}', str(run['id'])) or run['id'] in run_ids or run['input_id'] not in input_ids:
            raise ValueError('invalid run receipt')
        run_ids.add(run['id']); timestamp(run['started_at'])
        if run['finished_at'] is not None: timestamp(run['finished_at'])
        if run['status'] not in {'running', 'rate_limited', 'wall_budget', 'request_budget', 'partial', 'finished'}:
            raise ValueError('invalid run status')
        for key in ('request_budget', 'requests_attempted', 'new_unique_repositories', 'accepted_metadata_rows', 'unknown_requests', 'deferred_queries', 'before_unique_repositories', 'after_unique_repositories'):
            if type(run[key]) is not int or run[key] < 0: raise ValueError('invalid run counts')
        if not 1 <= run['request_budget'] <= 200 or run['requests_attempted'] > run['request_budget'] or type(run['wall_seconds_budget']) not in {int, float} or not 1 <= run['wall_seconds_budget'] <= 900:
            raise ValueError('invalid recorded budget')
        if not isinstance(run['deferred_query_ids'], list) or any(q not in query_ids for q in run['deferred_query_ids']):
            raise ValueError('invalid deferred queries')
        if 'strict_replay' in run and type(run['strict_replay']) is not bool:
            raise ValueError('invalid strict replay flag')
        if 'shared_budget' in run:
            shared = run['shared_budget']
            if (not isinstance(shared, dict) or set(shared) != {'round_id', 'reservations_before', 'reservations_after', 'reservations_charged', 'deferred_reason', 'deferred_provider'}
                    or not re.fullmatch('[0-9a-f]{32}', str(shared['round_id']))
                    or any(type(shared[k]) is not int or shared[k] < 0 for k in ('reservations_before', 'reservations_after', 'reservations_charged'))
                    or shared['reservations_after'] - shared['reservations_before'] != shared['reservations_charged']
                    or shared['reservations_charged'] < run['requests_attempted']
                    or shared['deferred_reason'] not in {None, 'request_budget', 'wall_budget', 'provider_cooldown'}
                    or shared['deferred_provider'] is not None and not re.fullmatch('[a-z0-9.-]+', shared['deferred_provider'])):
                raise ValueError('invalid shared-budget observation')
    runs_by_id = {run['id']: run for run in state['runs']}
    receipt_ids = set()
    receipt_fields = {'id', 'run_id', 'query_id', 'position', 'requested_at', 'finished_at', 'status', 'request_url_sha256', 'response_sha256', 'response_bytes', 'outcome', 'source_url', 'accepted_repository_ids', 'rejected_rows', 'raw_body_retained', 'reported_total', 'incomplete_results', 'returned_count'}
    rejection_names = {'private_or_unknown', 'visibility_not_public_or_unknown', 'fork_or_unknown', 'malformed', 'outside_created_bounds', 'query_topic_mismatch', 'requested_repository_mismatch'}
    for receipt in state['receipts']:
        if not isinstance(receipt, dict) or set(receipt) != receipt_fields or not re.fullmatch(r'receipt:[0-9a-f]{64}', str(receipt['id'])) or receipt['id'] in receipt_ids or receipt['run_id'] not in run_ids or receipt['query_id'] not in query_ids:
            raise ValueError('invalid request receipt')
        receipt_ids.add(receipt['id']); timestamp(receipt['requested_at']); timestamp(receipt['finished_at'])
        for key in ('request_url_sha256', 'response_sha256'):
            if not SHA.fullmatch(str(receipt[key])): raise ValueError('invalid response fingerprint')
        if receipt['status'] is not None and (type(receipt['status']) is not int or not 100 <= receipt['status'] <= 599):
            raise ValueError('invalid HTTP status')
        for key in ('position', 'response_bytes', 'reported_total', 'returned_count'):
            if receipt[key] is not None and (type(receipt[key]) is not int or receipt[key] < 0): raise ValueError('invalid request counts')
        if type(receipt['raw_body_retained']) is not bool or receipt['incomplete_results'] is not None and type(receipt['incomplete_results']) is not bool:
            raise ValueError('invalid request flags')
        if receipt['outcome'] not in {'accepted', 'accepted_with_rejections', 'rejected', 'quarantined', 'rate_limited', 'unavailable', 'redirect_not_followed', 'fetch_failed', 'response_too_large', 'malformed_response'}:
            raise ValueError('invalid request outcome')
        if not isinstance(receipt['accepted_repository_ids'], list) or any(type(i) is not int or i <= 0 for i in receipt['accepted_repository_ids']):
            raise ValueError('invalid accepted repository IDs')
        if len(set(receipt['accepted_repository_ids'])) != len(receipt['accepted_repository_ids']) or any('github-repository:' + str(i) not in state['records'] for i in receipt['accepted_repository_ids']):
            raise ValueError('accepted repository IDs lack unique actual records')
        query = queries_by_id[receipt['query_id']]
        if query['kind'] == 'existing' and runs_by_id[receipt['run_id']]['input_id'] != query['input_id']:
            raise ValueError('existing receipt belongs to a different input snapshot')
        if (type(receipt['position']) is not int or
                not (0 <= receipt['position'] < query['seed_count'] if query['kind'] == 'existing' else 1 <= receipt['position'] <= 10)):
            raise ValueError('request position is outside its cohort')
        if receipt['source_url'] is not None:
            safe_api_url(receipt['source_url'])
            if digest(receipt['source_url'].encode()) != receipt['request_url_sha256']:
                raise ValueError('source URL differs from its request fingerprint')
            if receipt['outcome'] != 'accepted' or not receipt['raw_body_retained']:
                raise ValueError('unverified source URL in ledger')
        if runs_by_id[receipt['run_id']].get('strict_replay') and receipt['accepted_repository_ids']:
            if receipt['outcome'] != 'accepted' or not receipt['source_url'] or not receipt['raw_body_retained']:
                raise ValueError('strict replay receipt lacks its complete public body')
        if receipt['outcome'] == 'quarantined' and (receipt['accepted_repository_ids'] or receipt['source_url'] is not None or receipt['raw_body_retained']):
            raise ValueError('quarantined page retained metadata or body')
    for item in [*state['runs'], *state['receipts']]:
        rejections = item['rejected_rows']
        if not isinstance(rejections, dict) or set(rejections) - rejection_names or any(type(v) is not int or v < 0 for v in rejections.values()):
            raise ValueError('invalid rejection counts')
    receipts_by_id = {receipt['id']: receipt for receipt in state['receipts']}
    provenance_owners = {rid: set() for rid in receipt_ids}
    for row in state['records'].values():
        if not row['occurrences']:
            raise ValueError('candidate metadata lacks an observation')
        for occurrence in row['occurrences']:
            if not isinstance(occurrence, dict) or set(occurrence) != {'query_id', 'receipt_id', 'position'} or occurrence['query_id'] not in query_ids or occurrence['receipt_id'] not in receipt_ids or type(occurrence['position']) is not int or occurrence['position'] < 0:
                raise ValueError('invalid metadata provenance')
            receipt = receipts_by_id[occurrence['receipt_id']]
            if (occurrence['query_id'] != receipt['query_id'] or occurrence['position'] != receipt['position']
                    or row['repository_id'] not in receipt['accepted_repository_ids']):
                raise ValueError('metadata occurrence does not match its accepted request receipt')
            provenance_owners[receipt['id']].add(row['repository_id'])
    for receipt in state['receipts']:
        if provenance_owners[receipt['id']] != set(receipt['accepted_repository_ids']):
            raise ValueError('accepted repository lacks a matching metadata occurrence')
    if state['schema_version'] == 2:
        _validate_epochs(state, queries_by_id)
    elif any('epoch_id' in run for run in state['runs']):
        raise ValueError('v1 run cannot claim an unrecorded epoch')
    return state


def _validate_epoch_structure(state, queries):
    epochs = state['epochs']
    if not isinstance(epochs, list) or not epochs:
        raise ValueError('v2 state requires explicit epoch history')
    ids = set(); covered = set()
    for index, epoch in enumerate(epochs):
        if not isinstance(epoch, dict) or set(epoch) != {'id', 'configuration', 'root_query_ids', 'created_at', 'reason', 'previous_epoch_id', 'source_state_sha256'}:
            raise ValueError('invalid epoch fields')
        cfg = epoch['configuration']; timestamp(epoch['created_at'])
        if (not isinstance(cfg, dict) or set(cfg) != {'topics', 'created_after', 'created_before'} or not isinstance(cfg['topics'], list)
                or not cfg['topics'] or any(t not in TOPICS for t in cfg['topics']) or len(set(cfg['topics'])) != len(cfg['topics'])
                or date.fromisoformat(cfg['created_after']) > date.fromisoformat(cfg['created_before'])):
            raise ValueError('invalid epoch configuration')
        previous = epochs[index-1] if index else None
        if epoch['previous_epoch_id'] != (previous['id'] if previous else None):
            raise ValueError('epoch history is not an append-only chain')
        expected = _epoch(cfg, epoch['root_query_ids'], epoch['created_at'], epoch['reason'], epoch['previous_epoch_id'], epoch['source_state_sha256'])
        if epoch['id'] != expected['id'] or epoch['id'] in ids:
            raise ValueError('invalid or duplicate epoch identity')
        ids.add(epoch['id'])
        roots = epoch['root_query_ids']
        if (not isinstance(roots, list) or len(roots) != len(cfg['topics']) or len(set(roots)) != len(roots)
                or any(qid not in queries or queries[qid]['kind'] != 'search' or queries[qid]['parent_id'] is not None for qid in roots)
                or [queries[qid]['topic'] for qid in roots] != cfg['topics']
                or any(not cfg['created_after'] <= queries[qid]['created_after'] <= queries[qid]['created_before'] == cfg['created_before'] for qid in roots)):
            raise ValueError('epoch roots do not describe their exact topic bounds')
        if not previous:
            if epoch['reason'] not in {'initial', 'v1_migration'}:
                raise ValueError('first epoch lacks an initialization or migration reason')
            if epoch['reason'] == 'v1_migration' and not SHA.fullmatch(str(epoch['source_state_sha256'])):
                raise ValueError('migration lacks its canonical prior-state fingerprint')
        elif epoch['reason'] == 'topic_expansion':
            old_cfg = previous['configuration']
            if not set(old_cfg['topics']) < set(cfg['topics']) or cfg['created_before'] != old_cfg['created_before'] or cfg['created_after'] != epochs[0]['configuration']['created_after']:
                raise ValueError('invalid topic expansion')
            old_roots = {queries[qid]['topic']: qid for qid in previous['root_query_ids']}
            for qid in roots:
                topic = queries[qid]['topic']
                if (topic in old_roots and old_roots[topic] != qid or
                        topic not in old_roots and queries[qid]['created_after'] != epochs[0]['configuration']['created_after']):
                    raise ValueError('topic expansion reset an old cursor or omitted historical backfill')
        elif epoch['reason'] == 'daily_continuation':
            old_cfg = previous['configuration']
            if (cfg['topics'] != old_cfg['topics'] or cfg['created_after'] != old_cfg['created_before']
                    or cfg['created_before'] <= old_cfg['created_before'] or not _epoch_complete(state, previous['id'])
                    or any(queries[qid]['created_after'] != cfg['created_after'] for qid in roots)):
                raise ValueError('daily continuation lacks complete preceding traversal or one-day overlap')
        else:
            raise ValueError('unsupported epoch transition')
        if epoch['reason'] != 'v1_migration' and epoch['source_state_sha256'] is not None:
            raise ValueError('nonmigration epoch cannot claim a migration fingerprint')
        covered |= _epoch_nodes(state, epoch['id'])
    if state['current_epoch_id'] != epochs[-1]['id'] or state['configuration'] != epochs[-1]['configuration']:
        raise ValueError('current epoch and configuration disagree')
    if covered != {q['id'] for q in state['queries'] if q['kind'] == 'search'}:
        raise ValueError('unowned search shard in epoch history')
    for qid in covered:
        parent = queries[qid]['parent_id']
        if parent is not None and (parent not in queries or queries[parent]['kind'] != 'search' or queries[parent]['topic'] != queries[qid]['topic']
                                   or not queries[parent]['created_after'] <= queries[qid]['created_after'] <= queries[qid]['created_before'] <= queries[parent]['created_before']):
            raise ValueError('invalid shard ancestry')
    return ids, covered


def _validate_epochs(state, queries):
    ids, covered = _validate_epoch_structure(state, queries)
    history = state['query_rechecks']
    if not isinstance(history, list):
        raise ValueError('v2 state requires traversal history')
    for run in state['runs']:
        if 'epoch_id' in run and run['epoch_id'] not in ids:
            raise ValueError('run references an unknown epoch')
    runs = {run['id']: run for run in state['runs']}
    for receipt in state['receipts']:
        epoch_id = runs[receipt['run_id']].get('epoch_id')
        if epoch_id and queries[receipt['query_id']]['kind'] == 'search' and receipt['query_id'] not in _epoch_nodes(state, epoch_id):
            raise ValueError('search receipt belongs to another run epoch')
    boundaries = {}; event_ids = set()
    for index, event in enumerate(history):
        if not isinstance(event, dict) or set(event) != {'id', 'query_id', 'epoch_id', 'restarted_at', 'receipt_boundary', 'previous'}:
            raise ValueError('invalid traversal restart record')
        qid = event['query_id']; boundary = event['receipt_boundary']; prior = event['previous']
        if (qid not in covered or event['epoch_id'] not in ids or qid not in _epoch_nodes(state, event['epoch_id'])
                or type(boundary) is not int or not boundaries.get(qid, 0) <= boundary <= len(state['receipts'])
                or not isinstance(prior, dict) or set(prior) != set(QUERY_PROGRESS) or prior['status'] not in {'partial_results', 'partial_api_window'}):
            raise ValueError('invalid traversal restart boundary')
        timestamp(event['restarted_at'])
        expected_id = 'recheck:' + _state_digest([qid, index, boundary])[:24]
        if event['id'] != expected_id or event['id'] in event_ids:
            raise ValueError('invalid traversal restart identity')
        event_ids.add(event['id'])
        prior_seen = {rid for r in state['receipts'][boundaries.get(qid, 0):boundary] if r['query_id'] == qid for rid in r['accepted_repository_ids']}
        if prior_seen != set(prior['seen_repository_ids']):
            raise ValueError('restart discarded unaccounted observations')
        boundaries[qid] = boundary
    for qid in covered:
        query = queries[qid]
        traversal = [r for r in state['receipts'][boundaries.get(qid, 0):] if r['query_id'] == qid]
        observed = {rid for r in traversal for rid in r['accepted_repository_ids']}
        if observed != set(query['seen_repository_ids']):
            raise ValueError('traversal reuses observations from another attempt')
        progress = [r for r in traversal if r['outcome'] in {'accepted', 'accepted_with_rejections', 'rejected'}]
        totals = [r['reported_total'] for r in progress]
        if (query['reported_total'] != (totals[-1] if totals else None)
                or query['total_changed'] != any(a != b for a, b in zip(totals, totals[1:]))
                or query['incomplete_results_seen'] != any(r['incomplete_results'] for r in progress)
                or query['rejected_rows'] != sum(sum(r['rejected_rows'].values()) for r in progress)):
            raise ValueError('traversal progress differs from its source receipts')
        if query['status'] == 'observed_pages_exhausted' and (query['reported_total'] != len(observed) or query['total_changed'] or query['incomplete_results_seen'] or query['rejected_rows']):
            raise ValueError('query completion is not supported by a reconciled traversal')


def validate_epoch_metadata(metadata):
    """Check epoch semantics on structurally validated metadata, without resource rows."""
    if metadata.get('schema_version') == 2:
        queries = {q['id']: q for q in metadata['queries']}
        if len(queries) != len(metadata['queries']):
            raise ValueError('duplicate query in epoch metadata')
        _validate_epochs(metadata, queries)
    elif metadata.get('schema_version') != 1 or any(k in metadata for k in ('epochs', 'current_epoch_id', 'query_rechecks')):
        raise ValueError('unsupported epoch metadata version')
    return metadata


def validate_public_epochs(configuration, epochs, current_epoch_id, queries):
    """Validate the shared epoch algorithm on public query projections, without cursors or receipts."""
    by_id = {q['id']: q for q in queries}
    if len(by_id) != len(queries):
        raise ValueError('duplicate public query identity')
    for query in queries:
        if query['kind'] == 'search':
            expected = search_query(query['topic'], query['created_after'], query['created_before'], query['parent_id'])
            if query['id'] != expected['id']:
                raise ValueError('public query identity differs from its declared bounds')
    metadata = {'configuration': configuration, 'epochs': epochs, 'current_epoch_id': current_epoch_id, 'queries': queries}
    _validate_epoch_structure(metadata, by_id)
    return metadata


def save(path, state):
    validate_state(state)
    atomic_write(path, (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def delay_until(headers, now):
    headers = {str(k).casefold(): str(v) for k, v in headers.items()}
    until = now + timedelta(seconds=60)
    retry = headers.get('retry-after', '')
    try:
        until = max(until, now + timedelta(seconds=min(86400, max(0, int(retry)))))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(retry)
            if parsed.tzinfo is not None:
                until = max(until, parsed)
        except (ValueError, TypeError, OverflowError):
            pass
    try:
        until = max(until, datetime.fromtimestamp(int(headers.get('x-ratelimit-reset', '0')), timezone.utc))
    except (ValueError, OverflowError, OSError):
        pass
    return min(until, now + timedelta(days=1)).isoformat()


def rate_limited(status, headers, body):
    if status == 429:
        return True
    if status != 403:
        return False
    headers = {str(key).casefold(): value for key, value in headers.items()}
    if headers.get('x-ratelimit-remaining') == '0' or 'retry-after' in headers:
        return True
    if len(body) > MAX_BODY:
        return False
    try:
        payload = strict_json(body)
    except (ValueError, UnicodeError):
        return False
    message = payload.get('message') if isinstance(payload, dict) else None
    if not isinstance(message, str):
        return False
    message = ' '.join(message.casefold().split())
    return message.startswith(('api rate limit exceeded', 'rate limit exceeded',
                               'you have exceeded a secondary rate limit',
                               'you have triggered an abuse detection mechanism'))


def run_scan(root, output, *, max_requests=10, max_seconds=180, existing_budget=5,
             topics=None, created_after=None, created_before=None,
             strict_replay=False, advance_epoch=False, shared_budget=None,
             fetcher=None, clock=time.monotonic, sleep=time.sleep, now=utcnow):
    if type(max_requests) is not int or not 1 <= max_requests <= 200 or type(existing_budget) is not int or not 0 <= existing_budget <= max_requests:
        raise ValueError('invalid request budgets')
    if type(max_seconds) not in {int, float} or not 1 <= max_seconds <= 900:
        raise ValueError('invalid wall-clock budget')
    if type(strict_replay) is not bool or type(advance_epoch) is not bool:
        raise ValueError('scheduled-mode flags must be boolean')
    shared_budget = shared_budget or budget_from_environment()
    output = checked_output(output)
    path = checked_output(output / 'candidate-metadata.json')
    snapshot, seeds = input_snapshot(Path(root))
    state = validate_state(strict_json(path.read_bytes())) if path.exists() else None
    config = state['configuration'] if state else {
        'topics': list(dict.fromkeys(topics or DEFAULT_TOPICS)),
        'created_after': created_after or '2008-01-01',
        'created_before': created_before or timestamp(now()).date().isoformat()}
    if state and ((not advance_epoch and topics is not None and list(dict.fromkeys(topics)) != config['topics']) or (created_after is not None and created_after != config['created_after']) or (created_before is not None and created_before != config['created_before'])):
        raise ValueError('resume requires the frozen cohort bounds; use a new output directory for a new epoch')
    new_state = state is None
    if not state:
        state = {'schema_version': 1, 'provider': 'github', 'policy': POLICY,
                 'configuration': config, 'inputs': [], 'records': {},
                 'queries': [search_query(t, config['created_after'], config['created_before']) for t in config['topics']],
                 'receipts': [], 'runs': [], 'deferred_until': None}
    if advance_epoch:
        at = now()
        state = migrate_state(state, at=at)
        if new_state:
            epoch = _epoch(state['configuration'], state['epochs'][0]['root_query_ids'], at, 'initial')
            state['epochs'] = [epoch]; state['current_epoch_id'] = epoch['id']
        if topics is not None:
            state = expand_topics(state, topics, at=at)
        _retry_partial_queries(state, at)
        _advance_epoch(state, at)
        config = state['configuration']
    retained_input = next((item for item in state['inputs'] if item['id'] == snapshot['id']), None)
    if retained_input is None:
        state['inputs'].append(snapshot)
    elif retained_input != snapshot:
        raise ValueError('current input facts differ from their retained snapshot')
    current_cohort = None
    for query in state['queries']:
        if query['kind'] != 'existing':
            continue
        if query['input_id'] == snapshot['id']:
            current_cohort = query
            if query['seed_count'] != len(seeds):
                raise ValueError('current existing cohort seed count differs')
            query['status'] = 'pending' if query['next_index'] < len(seeds) else 'exhausted'
        elif query['status'] == 'pending':
            query['status'] = 'superseded_input'
    if current_cohort is None:
        state['queries'].insert(0, {'id': 'existing:' + snapshot['id'], 'kind': 'existing',
            'input_id': snapshot['id'], 'seed_count': len(seeds), 'next_index': 0,
            'status': 'pending' if seeds else 'exhausted', 'last_attempt': 0})
    started = now(); start_clock = clock(); previous_request = None
    if state['receipts']:
        age = max(0, (timestamp(started) - timestamp(state['receipts'][-1]['requested_at'])).total_seconds())
        previous_request = start_clock - age
    run = {'id': 'run:' + digest((started + str(len(state['runs']))).encode())[:24],
           'input_id': snapshot['id'], 'started_at': started, 'finished_at': None,
           'status': 'running', 'request_budget': max_requests, 'wall_seconds_budget': max_seconds,
           'requests_attempted': 0, 'new_unique_repositories': 0, 'accepted_metadata_rows': 0,
           'rejected_rows': {}, 'unknown_requests': 0, 'deferred_queries': 0,
           'deferred_query_ids': [],
           'before_unique_repositories': len(state['records']), 'after_unique_repositories': len(state['records'])}
    run['strict_replay'] = strict_replay
    if state['schema_version'] == 2:
        run['epoch_id'] = state['current_epoch_id']
    if shared_budget:
        shared = shared_budget.summary()
        run['shared_budget'] = {'round_id': shared['round_id'], 'reservations_before': shared['requests_reserved'],
                                'reservations_after': shared['requests_reserved'], 'reservations_charged': 0,
                                'deferred_reason': None, 'deferred_provider': None}
    state['runs'].append(run)

    def persist():
        if shared_budget:
            shared = run['shared_budget']; shared['reservations_after'] = shared_budget.summary()['requests_reserved']
            shared['reservations_charged'] = shared['reservations_after'] - shared['reservations_before']
        save(path, state)

    persist()
    attempted_failed = set(); existing_attempts = 0; stopped = None
    while run['requests_attempted'] < max_requests:
        if state['deferred_until'] and timestamp(state['deferred_until']) > timestamp(now()):
            stopped = 'rate_limited'; break
        if clock() - start_clock >= max_seconds:
            stopped = 'wall_budget'; break
        # Splitting a parent adds eligible children during this invocation.
        active_search = _epoch_nodes(state) if state['schema_version'] == 2 else {q['id'] for q in state['queries'] if q['kind'] == 'search'}
        pending = [q for q in state['queries'] if q['status'] == 'pending' and q['id'] not in attempted_failed
                   and (q['id'] in active_search if q['kind'] == 'search' else q['input_id'] == snapshot['id'] and existing_attempts < existing_budget)]
        if not pending:
            break
        query = min(pending, key=lambda q: (q['kind'] != 'existing', q['last_attempt']))
        if query['kind'] == 'existing':
            known = {name.casefold() for r in state['records'].values() for name in r['known_names']}
            while query['next_index'] < len(seeds) and seeds[query['next_index']] in known:
                query['next_index'] += 1
            if query['next_index'] >= len(seeds):
                query['status'] = 'exhausted'; persist(); continue
            position = query['next_index']
            url = 'https://api.github.com/repos/' + seeds[position]
        else:
            position = query['next_page']
            url = 'https://api.github.com/search/repositories?' + urllib.parse.urlencode({
                'q': query['query'], 'per_page': PAGE_SIZE, 'page': position, 'sort': 'updated', 'order': 'asc'})
        safe_api_url(url)
        wait = max(0, INTERVAL - (clock() - previous_request)) if previous_request is not None else 0
        if clock() - start_clock + wait >= max_seconds:
            stopped = 'wall_budget'; break
        if wait:
            sleep(wait)
        remaining = max_seconds - (clock() - start_clock)
        if remaining <= 0:
            stopped = 'wall_budget'; break
        requested = None

        def attempted():
            nonlocal requested, previous_request, existing_attempts
            requested = now(); previous_request = clock()
            run['requests_attempted'] += 1
            if query['kind'] == 'existing': existing_attempts += 1

        try:
            status, body, headers = _transport_get(url, min(20, remaining), transport=fetcher or _http_get,
                budget=shared_budget, on_attempt=attempted, remaining_seconds=lambda: max_seconds - (clock() - start_clock))
        except BudgetDeferred as error:
            stopped = {'request_budget': 'request_budget', 'wall_budget': 'wall_budget', 'provider_cooldown': 'rate_limited'}[error.reason]
            if shared_budget:
                run['shared_budget'].update(deferred_reason=error.reason, deferred_provider=error.provider)
                until = shared_budget.summary()['provider_cooldowns'].get('api.github.com')
                if until and (not state['deferred_until'] or timestamp(until) > timestamp(state['deferred_until'])):
                    state['deferred_until'] = until
            break
        if not isinstance(body, bytes) or not isinstance(headers, dict):
            raise ValueError('transport returned invalid types')
        sha = digest(body)
        receipt = {'id': 'receipt:' + digest((run['id'] + str(run['requests_attempted']) + sha).encode()),
                   'run_id': run['id'], 'query_id': query['id'], 'position': position,
                   'requested_at': requested, 'finished_at': now(), 'status': status,
                   'request_url_sha256': digest(url.encode()), 'response_sha256': sha,
                   'response_bytes': len(body), 'outcome': 'unknown', 'source_url': None,
                   'accepted_repository_ids': [], 'rejected_rows': {}, 'raw_body_retained': False,
                   'reported_total': None, 'incomplete_results': None, 'returned_count': None}
        query['last_attempt'] = len(state['receipts']) + 1
        limited = rate_limited(status, headers, body)
        parsed = False
        quarantined = False
        if limited:
            receipt['outcome'] = 'rate_limited'; state['deferred_until'] = delay_until(headers, timestamp(now()))
            if shared_budget:
                run['shared_budget'].update(deferred_reason='provider_cooldown', deferred_provider='api.github.com')
        elif status != 200:
            receipt['outcome'] = 'unavailable' if status in {403, 404} else 'redirect_not_followed' if status in {301, 302, 303, 307, 308} else 'fetch_failed'
        elif len(body) > MAX_BODY:
            receipt['outcome'] = 'response_too_large'
        else:
            try:
                value = strict_json(body)
                if query['kind'] == 'search':
                    if not isinstance(value, dict) or type(value.get('total_count')) is not int or value['total_count'] < 0 or type(value.get('incomplete_results')) is not bool or not isinstance(value.get('items'), list) or len(value['items']) > PAGE_SIZE:
                        raise ValueError('malformed search response')
                    items = value['items']
                    if len(items) > value['total_count']:
                        raise ValueError('search rows exceed the reported population')
                    receipt.update(reported_total=value['total_count'], incomplete_results=value['incomplete_results'])
                else:
                    items = [value]
                receipt['returned_count'] = len(items)
                rejected = Counter(); accepted = []; response_ids = set()
                for item in items:
                    try:
                        metadata = repository_metadata(item)
                        if query['kind'] == 'existing' and metadata['full_name'].casefold() != seeds[position].casefold():
                            raise Rejected('requested_repository_mismatch')
                        if query['kind'] == 'search' and not date.fromisoformat(query['created_after']) <= timestamp(metadata['created_at']).date() <= date.fromisoformat(query['created_before']):
                            raise Rejected('outside_created_bounds')
                        if query['kind'] == 'search' and query['topic'] not in metadata['topics']:
                            raise Rejected('query_topic_mismatch')
                        if strict_replay and metadata['repository_id'] in response_ids:
                            # Duplicate or conflicting identities cannot be replayed as one page.
                            raise Rejected('malformed')
                        response_ids.add(metadata['repository_id'])
                        accepted.append(metadata)
                    except Rejected as error:
                        rejected[str(error)] += 1
                receipt['rejected_rows'] = dict(rejected)
                if strict_replay and rejected:
                    accepted = []; quarantined = True
                for metadata in accepted:
                    rid = metadata['id']; old = state['records'].get(rid)
                    occurrence = {'query_id': query['id'], 'receipt_id': receipt['id'], 'position': position}
                    state['records'][rid] = {**metadata,
                        'first_observed_at': old['first_observed_at'] if old else requested,
                        'last_observed_at': requested,
                        'known_names': sorted(set((old['known_names'] if old else []) + [metadata['full_name']])),
                        'occurrences': (old['occurrences'] if old else []) + [occurrence]}
                    receipt['accepted_repository_ids'].append(metadata['repository_id'])
                receipt['accepted_repository_ids'] = sorted(set(receipt['accepted_repository_ids']))
                receipt['outcome'] = 'quarantined' if quarantined else 'accepted_with_rejections' if rejected and accepted else 'rejected' if rejected else 'accepted'
                # A mixed/unknown/private response has a digest but no raw body or request URL in the public ledger.
                if not rejected:
                    receipt['source_url'] = url
                    raw = checked_output(output / 'raw' / (sha + '.body'))
                    atomic_write(raw, body); receipt['raw_body_retained'] = True
                parsed = True
                if query['kind'] == 'search' and not quarantined:
                    total = value['total_count']
                    query['total_changed'] |= query['reported_total'] is not None and query['reported_total'] != total
                    query['reported_total'] = total
                    query['incomplete_results_seen'] |= value['incomplete_results']
                    query['seen_repository_ids'] = sorted(set(query['seen_repository_ids']) | set(receipt['accepted_repository_ids']))
                    query['rejected_rows'] += sum(rejected.values())
                    if total > SPLIT_THRESHOLD:
                        left, right = date.fromisoformat(query['created_after']), date.fromisoformat(query['created_before'])
                        if left == right:
                            query['status'] = 'blocked_single_day_window'
                        else:
                            middle = left + (right - left) // 2
                            children = [search_query(query['topic'], str(left), str(middle), query['id']),
                                        search_query(query['topic'], str(middle + timedelta(days=1)), str(right), query['id'])]
                            state['queries'].extend(child for child in children if not any(q['id'] == child['id'] for q in state['queries']))
                            query['status'] = 'split'
                    elif not items or position * PAGE_SIZE >= total:
                        complete = (not query['incomplete_results_seen'] and not query['total_changed']
                                    and query['rejected_rows'] == 0 and len(query['seen_repository_ids']) == total)
                        query['status'] = 'observed_pages_exhausted' if complete else 'partial_results'
                    elif position >= 10:
                        query['status'] = 'partial_api_window'
                    else:
                        query['next_page'] += 1
            except (ValueError, TypeError, KeyError, UnicodeError):
                receipt['outcome'] = 'malformed_response'
        if query['kind'] == 'existing' and not limited and not quarantined:
            query['next_index'] += 1
            if query['next_index'] >= query['seed_count']: query['status'] = 'exhausted'
        if not parsed:
            run['unknown_requests'] += 1; attempted_failed.add(query['id'])
        if quarantined:
            attempted_failed.add(query['id'])
        state['receipts'].append(receipt)
        run['accepted_metadata_rows'] += len(receipt['accepted_repository_ids'])
        run['rejected_rows'] = dict(Counter(run['rejected_rows']) + Counter(receipt['rejected_rows']))
        run['after_unique_repositories'] = len(state['records'])
        run['new_unique_repositories'] = len(state['records']) - run['before_unique_repositories']
        persist()
        if limited: stopped = 'rate_limited'; break
    pending_count = sum(q['status'] == 'pending' for q in state['queries'])
    run['finished_at'] = now(); run['deferred_queries'] = pending_count
    run['deferred_query_ids'] = [q['id'] for q in state['queries'] if q['status'] == 'pending']
    run['status'] = stopped or ('request_budget' if pending_count and run['requests_attempted'] >= max_requests else 'partial' if pending_count or run['unknown_requests'] or run['rejected_rows'] or any(q['status'] in {'partial_results', 'blocked_single_day_window', 'partial_api_window'} for q in state['queries']) else 'finished')
    persist()
    return state, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.cache' / 'github-candidate-scan')
    parser.add_argument('--max-requests', type=int, default=10)
    parser.add_argument('--max-seconds', type=float, default=180)
    parser.add_argument('--existing-budget', type=int, default=5, help='Maximum existing-candidate requests per run; topic shards receive the remaining budget.')
    parser.add_argument('--topic', action='append', choices=sorted(TOPICS), help='Repeatable; resume uses the original topics if omitted.')
    parser.add_argument('--created-after')
    parser.add_argument('--created-before', help='Fixed inclusive creation-date upper bound; defaults to the first run UTC day and stays frozen on resume.')
    parser.add_argument('--strict-replay', action='store_true', help='Quarantine a whole mixed/rejected page without advancing its cursor or retaining accepted siblings.')
    parser.add_argument('--advance-epoch', action='store_true', help='Explicitly migrate v1, allow additive historical topic backfills, retry up to two partial traversals, and continue completed epochs with a one-day overlap.')
    args = parser.parse_args(argv)
    try:
        output = checked_output(args.output)
        output.relative_to((ROOT / '.cache').absolute())
        state, run = run_scan(ROOT, output, max_requests=args.max_requests, max_seconds=args.max_seconds,
            existing_budget=args.existing_budget, topics=args.topic,
            created_after=args.created_after, created_before=args.created_before,
            strict_replay=args.strict_replay, advance_epoch=args.advance_epoch)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('Scan failed: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps({'run': run, 'unique_repository_metadata': len(state['records']),
                      'ledger': str(output / 'candidate-metadata.json'), 'policy': POLICY}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
