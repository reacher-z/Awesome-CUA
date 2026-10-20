#!/usr/bin/env python3
"""Bounded, source-traced paper discovery. arXiv remains authoritative for metadata."""
import argparse
import hashlib
import json
import re
import time
import urllib.parse
from catalog import (DATA, canonical, discovery_occurrence, fetch, now, read_json,
                     read_jsonl, retain_discovery_evidence, write_json, write_jsonl)

QUERY_FILE = 'paper-discovery-queries.json'
RUN_FILE = 'paper-discovery-status.json'
POLICY = 'Ranked search windows for candidate discovery, not exhaustive field coverage or editorial approval.'


def query_id(query):
    slug = re.sub('[^a-z0-9]+', '-', query.lower()).strip('-')[:90] or 'query'
    return 'hf-custom-' + slug + '-' + hashlib.sha256(query.encode()).hexdigest()[:10]


def load_queries(custom=None, limit=None):
    if limit is not None and (type(limit) is not int or not 1 <= limit <= 120):
        raise ValueError('limit must be 1..120')
    if custom:
        queries = [{'id': query_id(q), 'query': q, 'area': 'Custom search', 'limit': limit or 80} for q in custom]
    else:
        registry = read_json(DATA / QUERY_FILE, {})
        if registry.get('schema_version') != 1:
            raise ValueError('Missing or unsupported paper-discovery query registry')
        queries = registry.get('queries')
    if not isinstance(queries, list) or not 1 <= len(queries) <= 64:
        raise ValueError('The query registry must contain 1..64 bounded queries')
    ids, texts, result = set(), set(), []
    for item in queries:
        if not isinstance(item, dict):
            raise ValueError('A query definition must be an object')
        sid, query, area = item.get('id'), item.get('query'), item.get('area')
        size = limit if limit is not None else item.get('limit')
        if not isinstance(sid, str) or not re.fullmatch(r'hf-[a-z0-9-]{1,140}', sid):
            raise ValueError('Invalid query identifier')
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 250:
            raise ValueError('Query must contain 1..250 characters')
        if not isinstance(area, str) or not area.strip() or len(area) > 100:
            raise ValueError('Query needs a concise coverage area')
        if type(size) is not int or not 1 <= size <= 120:
            raise ValueError('Every query limit must be 1..120')
        normalized = ' '.join(query.casefold().split())
        if sid in ids or normalized in texts:
            raise ValueError('Duplicate discovery query ID or text')
        ids.add(sid); texts.add(normalized)
        result.append({'id': sid, 'query': query.strip(), 'area': area.strip(), 'limit': size})
    return result


def parse_hits(body, limit):
    payload = json.loads(body)
    if not isinstance(payload, list) or len(payload) > limit:
        raise ValueError('Search response must be an array within the requested limit')
    ids = set()
    for hit in payload:
        if not isinstance(hit, dict):
            raise ValueError('Search hit must be an object')
        paper = hit.get('paper', hit)
        aid = paper.get('id') if isinstance(paper, dict) else None
        if not isinstance(aid, str) or not re.fullmatch(r'\d{4}\.\d{4,5}(?:v[1-9]\d*)?', aid):
            raise ValueError('Search hit has an invalid arXiv identifier')
        ids.add(canonical('https://arxiv.org/abs/' + aid)[0])
    return sorted(ids), len(payload)


def discover(queries, refresh=False):
    started = now()
    rows = {r['id']: r for r in read_jsonl(DATA / 'candidates.jsonl')}
    before = set(rows)
    papers = {r['id'] for r in read_jsonl(DATA / 'papers.jsonl')}
    runs = {r['id']: r for r in read_json(DATA / 'research-discovery.json', [])}
    retain_discovery_evidence(rows.values(), runs)
    results, found = [], set()
    rate_limited = False

    def persist(finished=False):
        successful = [r for r in results if r['state'] == 'success']
        report = {'schema_version': 1, 'started_at': started, 'finished_at': now() if finished else None,
            'provider': 'huggingface_papers_search', 'requested_refresh': refresh,
            'status': ('success' if len(successful) == len(queries) else 'partial') if finished else 'running',
            'configured_query_count': len(queries), 'successful_query_count': len(successful),
            'unique_identifiers': len(found), 'new_candidate_count': len(found - before),
            'without_arxiv_metadata': len(found - papers), 'scope': POLICY, 'queries': results}
        write_jsonl(DATA / 'candidates.jsonl', rows.values())
        write_json(DATA / 'research-discovery.json', sorted(runs.values(), key=lambda r: r['id']))
        write_json(DATA / RUN_FILE, report)
        return report

    # A new run starts with its own receipt, so old successes cannot stand in for it.
    persist()
    for index, spec in enumerate(queries):
        query, sid, size = spec['query'], spec['id'], spec['limit']
        endpoint = 'https://huggingface.co/api/papers/search?' + urllib.parse.urlencode({'q': query, 'limit': size})
        if rate_limited:
            info, body = {'url': endpoint, 'retrieved_at': now(), 'ok': False,
                          'error': 'Deferred after an HTTP 429 from this provider; a later scan can retry.'}, b''
        else:
            info, body = fetch(endpoint, refresh)
        info = {**info, 'url': endpoint}
        run = {**spec, 'provider': 'huggingface_papers_search', 'scope': POLICY,
               'evidence': info, 'identifiers': [], 'returned_count': 0,
               'request_attempted': info.get('request_attempted', not rate_limited),
               'state': 'deferred' if rate_limited or info.get('deferred') else 'failed'}
        if info.get('ok'):
            try:
                identifiers, returned = parse_hits(body, size)
                run.update(identifiers=identifiers, returned_count=returned, state='success')
                run['unique_count'] = len(identifiers)
                run['new_candidate_count'] = len(set(identifiers) - set(rows))
                run['without_arxiv_metadata'] = len(set(identifiers) - papers)
                run['at_result_limit'] = returned == size
                # Only a successfully parsed response replaces this query's current population.
                for row in rows.values():
                    row['discovered_in'] = [o for o in row['discovered_in'] if o['source_id'] != sid]
                for rid in identifiers:
                    row = rows.setdefault(rid, {'id': rid, 'url': 'https://arxiv.org/abs/' + rid.split(':', 1)[1],
                        'provider': 'arxiv', 'first_discovered_at': info['retrieved_at'], 'discovered_in': []})
                    row['discovered_in'].append(discovery_occurrence(sid, info, section=query))
                found.update(identifiers)
            except (ValueError, AttributeError, TypeError) as error:
                run['parse_error'] = str(error)
        if info.get('status') == 429:
            rate_limited = True
        runs[sid] = run; results.append(run)
        persist()
        print(f'{sid}: {run["state"]}; {len(run["identifiers"])} identifiers', flush=True)
        if not rate_limited and index + 1 < len(queries):
            time.sleep(.5)
    report = persist(finished=True)
    print(f'{len(found)} distinct hits; {report["new_candidate_count"]} new candidates; '
          f'{report["without_arxiv_metadata"]} lack arXiv metadata. Candidate discovery does not grant review approval.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', action='append', help='Custom query, repeatable; otherwise run the committed query registry.')
    parser.add_argument('--limit', type=int, help='Override each query window (1..120); registry default is 80.')
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    try:
        queries = load_queries(args.query, args.limit)
    except ValueError as error:
        parser.error(str(error))
    discover(queries, args.refresh)


if __name__ == '__main__':
    main()
