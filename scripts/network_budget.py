"""One persisted network budget for sequential processes in a single scan round.

The ledger is private cache, contains no request URLs or credentials, and is
reserved atomically before I/O. Monotonic deadlines are valid only on the same
host/boot; a new Actions invocation creates a new round, carrying UTC cooldowns.
"""
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import email.utils
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.parse
import urllib.request
import uuid

ENV_FILE = 'CUA_SCAN_BUDGET_FILE'
ENV_ID = 'CUA_SCAN_BUDGET_ID'
ENV_PHASE = 'CUA_SCAN_PHASE'
DEFAULT_REQUESTS = 180
DEFAULT_SECONDS = 600
MIN_INTERVALS = {'export.arxiv.org': 3.1, 'api.github.com': 6.5}


class BudgetDeferred(Exception):
    def __init__(self, reason, provider=None):
        self.reason, self.provider = reason, provider
        super().__init__('Network request deferred: ' + reason + (': ' + provider if provider else ''))


def utcnow():
    return datetime.now(timezone.utc)


def provider_for(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        raise ValueError('Network budget requires an HTTP(S) provider')
    return parsed.hostname.lower()


def checked_path(path):
    path = Path(path).absolute()
    if '..' in path.parts or any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Unsafe network-budget path')
    return path


def atomic_json(path, value):
    path = checked_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _number(value):
    return type(value) in {int, float} and math.isfinite(value)


def _timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Network-budget timestamp lacks timezone')
    return result.astimezone(timezone.utc)


class RoundBudget:
    """Single-writer ledger shared by sequential parent/child processes."""
    def __init__(self, path, run_id, *, clock=None, sleep=None, now=None):
        self.path, self.run_id = checked_path(path), run_id
        self.clock, self.sleep, self.now = clock or time.monotonic, sleep or time.sleep, now or utcnow
        self.read()

    @classmethod
    def create(cls, directory, *, max_requests=DEFAULT_REQUESTS, max_seconds=DEFAULT_SECONDS,
               cooldowns=None, clock=None, sleep=None, now=None):
        if type(max_requests) is not int or not 1 <= max_requests <= 1000:
            raise ValueError('Network request limit must be 1..1000')
        if not _number(max_seconds) or not 0 < max_seconds <= 1200:
            raise ValueError('Network time limit must be >0 and <=1200 seconds')
        clock, now = clock or time.monotonic, now or utcnow
        started, current, run_id = clock(), now(), uuid.uuid4().hex
        retained = {}
        for host, until in (cooldowns or {}).items():
            if not re.fullmatch(r'[a-z0-9.-]+', host):
                raise ValueError('Invalid cooldown provider')
            if _timestamp(until) > current:
                retained[host] = _timestamp(until).isoformat()
        state = {'schema_version': 1, 'round_id': run_id, 'started_at': current.isoformat(),
                 'started_monotonic': started, 'deadline_monotonic': started + max_seconds,
                 'max_requests': max_requests, 'max_seconds': max_seconds,
                 'attempts': [], 'last_request_monotonic': {}, 'provider_cooldowns': retained,
                 'blocked_providers': []}
        path = checked_path(Path(directory) / (run_id + '.json'))
        atomic_json(path, state)
        return cls(path, run_id, clock=clock, sleep=sleep, now=now)

    def read(self):
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result: raise ValueError('Duplicate network-budget key')
                result[key] = value
            return result
        state = json.loads(checked_path(self.path).read_bytes(), object_pairs_hook=pairs)
        fields = {'schema_version','round_id','started_at','started_monotonic','deadline_monotonic',
                  'max_requests','max_seconds','attempts','last_request_monotonic','provider_cooldowns','blocked_providers'}
        if (not isinstance(state, dict) or set(state) != fields or type(state['schema_version']) is not int
                or state['schema_version'] != 1 or state['round_id'] != self.run_id
                or not re.fullmatch('[0-9a-f]{32}', str(self.run_id))):
            raise ValueError('Invalid or different network budget round')
        if (type(state['max_requests']) is not int or not 1 <= state['max_requests'] <= 1000
                or not all(_number(state[k]) for k in ('started_monotonic','deadline_monotonic','max_seconds'))
                or not 0 < state['max_seconds'] <= 1200
                or abs(state['deadline_monotonic'] - state['started_monotonic'] - state['max_seconds']) > .001
                or not isinstance(state['attempts'], list) or len(state['attempts']) > state['max_requests']):
            raise ValueError('Invalid network budget limits or count')
        if self.clock() < state['started_monotonic']:
            raise ValueError('Network budget cannot resume on a different monotonic clock')
        _timestamp(state['started_at'])
        for index, attempt in enumerate(state['attempts'], 1):
            if (set(attempt) != {'number','phase','provider','url_sha256','started_at','finished_at','status','outcome'}
                    or type(attempt['number']) is not int or attempt['number'] != index
                    or not re.fullmatch('[a-z0-9_.-]{1,60}', attempt['phase'])
                    or not re.fullmatch('[a-z0-9.-]+', attempt['provider'])
                    or not re.fullmatch('[0-9a-f]{64}', attempt['url_sha256'])
                    or attempt['outcome'] not in {'reserved','response','transport_error'}
                    or attempt['status'] is not None and (type(attempt['status']) is not int or not 100 <= attempt['status'] <= 599)):
                raise ValueError('Invalid network attempt receipt')
            _timestamp(attempt['started_at'])
            if attempt['finished_at'] is not None: _timestamp(attempt['finished_at'])
        for host, value in state['last_request_monotonic'].items():
            if not re.fullmatch('[a-z0-9.-]+', host) or not _number(value):
                raise ValueError('Invalid provider spacing')
        for host, value in state['provider_cooldowns'].items():
            if not re.fullmatch('[a-z0-9.-]+', host): raise ValueError('Invalid cooldown provider')
            _timestamp(value)
        blocked=state['blocked_providers']
        if not isinstance(blocked,list) or len(blocked)!=len(set(blocked)) or any(host not in state['provider_cooldowns'] for host in blocked):
            raise ValueError('Invalid blocked providers')
        return state

    def remaining_seconds(self):
        return max(0, self.read()['deadline_monotonic'] - self.clock())

    def provider_deferred(self, url):
        state,host=self.read(),provider_for(url)
        until = state['provider_cooldowns'].get(host)
        return host in state['blocked_providers'] or bool(until and _timestamp(until) > self.now())

    def wait(self, seconds):
        """A retry/spacing wait cannot create a new attempt after the deadline."""
        if not _number(seconds) or seconds < 0: raise ValueError('Invalid network delay')
        if seconds >= self.remaining_seconds(): raise BudgetDeferred('wall_budget')
        if seconds: self.sleep(seconds)
        if self.remaining_seconds() <= 0: raise BudgetDeferred('wall_budget')

    def reserve(self, url, *, phase=None, min_interval=0):
        host = provider_for(url)
        phase = phase or os.getenv(ENV_PHASE, 'standalone')
        if not re.fullmatch('[a-z0-9_.-]{1,60}', phase): raise ValueError('Invalid network phase')
        if not _number(min_interval) or min_interval < 0: raise ValueError('Invalid network spacing')
        state = self.read()
        if self.provider_deferred(url): raise BudgetDeferred('provider_cooldown', host)
        if len(state['attempts']) >= state['max_requests']: raise BudgetDeferred('request_budget', host)
        if self.remaining_seconds() <= 0: raise BudgetDeferred('wall_budget', host)
        last = state['last_request_monotonic'].get(host)
        interval = max(min_interval, MIN_INTERVALS.get(host, 0))
        if last is not None:
            self.wait(max(0, interval - (self.clock() - last)))
        # Sleep may overshoot; load and check again before committing the reservation.
        state = self.read()
        if self.remaining_seconds() <= 0: raise BudgetDeferred('wall_budget', host)
        if len(state['attempts']) >= state['max_requests']: raise BudgetDeferred('request_budget', host)
        number = len(state['attempts']) + 1
        state['attempts'].append({'number':number,'phase':phase,'provider':host,
            'url_sha256':hashlib.sha256(url.encode('utf-8')).hexdigest(),'started_at':self.now().isoformat(),
            'finished_at':None,'status':None,'outcome':'reserved'})
        state['last_request_monotonic'][host] = self.clock()
        atomic_json(self.path, state)
        return number

    def timeout(self, maximum=30):
        remaining = self.remaining_seconds()
        if remaining <= 0: raise BudgetDeferred('wall_budget')
        return min(maximum, remaining)

    def observe_response(self, url, status, headers=None, *, attempt=None, rate_limited=False):
        state, host = self.read(), provider_for(url)
        values = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
        limited = rate_limited or status == 429 or status == 403 and (
            values.get('x-ratelimit-remaining') == '0' or 'retry-after' in values)
        if limited:
            current = self.now(); until = current + timedelta(seconds=60)
            retry = values.get('retry-after', '')
            try:
                until = max(until, current + timedelta(seconds=min(86400, max(0, int(retry)))))
            except ValueError:
                try:
                    parsed = email.utils.parsedate_to_datetime(retry)
                    if parsed.tzinfo is not None: until = max(until, parsed)
                except (ValueError, TypeError, OverflowError): pass
            try:
                until = max(until, datetime.fromtimestamp(int(values.get('x-ratelimit-reset', '0')), timezone.utc))
            except (ValueError, OverflowError, OSError): pass
            until = min(until, current + timedelta(days=1))
            previous = state['provider_cooldowns'].get(host)
            if previous: until = max(until, _timestamp(previous))
            state['provider_cooldowns'][host] = until.isoformat()
            state['blocked_providers'] = sorted(set(state['blocked_providers']) | {host})
        if attempt is not None:
            if type(attempt) is not int or not 1 <= attempt <= len(state['attempts']):
                raise ValueError('Unknown network attempt')
            receipt = state['attempts'][attempt-1]
            if receipt['url_sha256'] != hashlib.sha256(url.encode('utf-8')).hexdigest():
                raise ValueError('Network response belongs to another request')
            receipt.update(finished_at=self.now().isoformat(), status=status,
                           outcome='response' if status is not None else 'transport_error')
        atomic_json(self.path, state)

    def summary(self):
        state = self.read()
        return {'round_id': self.run_id, 'max_requests': state['max_requests'], 'max_seconds': state['max_seconds'],
                'requests_reserved': len(state['attempts']),
                'responses_received': sum(x['outcome']=='response' for x in state['attempts']),
                'unknown_attempts': sum(x['outcome']!='response' for x in state['attempts']),
                'by_phase': dict(Counter(x['phase'] for x in state['attempts'])),
                'by_provider': dict(Counter(x['provider'] for x in state['attempts'])),
                'provider_cooldowns': state['provider_cooldowns'],
                'blocked_providers': state['blocked_providers'],
                'ledger_sha256': hashlib.sha256(self.path.read_bytes()).hexdigest(),
                'count_boundary': 'Reservations are persisted before I/O; interrupted attempts remain conservatively charged. HTTP status observation does not establish complete or validated content.'}

    @contextmanager
    def activate(self):
        old = {k:os.environ.get(k) for k in (ENV_FILE, ENV_ID, ENV_PHASE)}
        os.environ[ENV_FILE], os.environ[ENV_ID] = str(self.path), self.run_id
        os.environ.pop(ENV_PHASE, None)
        try: yield self
        finally:
            for key, value in old.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value


def budget_from_environment():
    path, run_id = os.getenv(ENV_FILE), os.getenv(ENV_ID)
    if not path and not run_id: return None
    if not path or not run_id: raise ValueError('Incomplete network-budget context')
    return RoundBudget(path, run_id)


class BudgetHandler(urllib.request.BaseHandler):
    """Charge every HTTP(S) request, including redirects within an opener."""
    handler_order = 400  # Before HTTPErrorProcessor redirects or raises an HTTP error.
    def __init__(self, budget):
        self.budget, self.pending = budget, []

    def http_request(self, request):
        url = request.full_url
        attempt = self.budget.reserve(url)
        self.pending.append((url, attempt))
        request._cua_budget_attempt = attempt
        request.timeout = self.budget.timeout(getattr(request, 'timeout', 30))
        return request

    https_request = http_request

    def http_response(self, request, response):
        attempt = getattr(request, '_cua_budget_attempt', None)
        self.budget.observe_response(request.full_url, response.code, response.headers, attempt=attempt)
        if (request.full_url, attempt) in self.pending:
            self.pending.remove((request.full_url, attempt))
        return response

    https_response = http_response

    def failed(self):
        for url, attempt in self.pending:
            self.budget.observe_response(url, None, attempt=attempt)
        self.pending.clear()


class HTTPOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        # urllib also supports FTP redirects, which have no HTTP request hook.
        provider_for(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def budgeted_urlopen(request, budget, *, timeout=30):
    handler = BudgetHandler(budget)
    opener = urllib.request.build_opener(handler, HTTPOnlyRedirect())
    open_url = opener.open  # Binary HTTP transport, not a text-file open.
    try:
        return open_url(request, timeout=budget.timeout(timeout))
    except BaseException:
        handler.failed()
        raise
