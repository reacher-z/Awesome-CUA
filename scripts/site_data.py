"""Catalog facts that several website outputs share: review dates, page dates and curated-only counts.

Every value comes from committed data (records, editorial review times, the coverage report), never from the
build clock, so two builds of the same source commit write the same files.
"""
from __future__ import annotations

from collections import Counter
import datetime as dt
import json
from pathlib import Path

from catalog import editorial_identity

PAPER_KINDS = frozenset({'paper', 'survey'})
# Display order shared by counts, feeds and listings.
KIND_ORDER = ('paper', 'survey', 'learning', 'model', 'dataset', 'benchmark', 'agent', 'framework', 'infrastructure', 'tool', 'product', 'company')
COUNT_NOTE = ('Headline counts use curated, source-reviewed records only. Metadata-only bibliography records and discovered '
              'candidates await relevance review and are reported separately; these populations overlap and must not be added together.')


def eligible(record):
    """Curated, in-scope records: the reviewed catalog that pages index and headline counts describe."""
    return record['review_status'] == 'curated' and record['scope'] in {'core', 'adjacent'}


def utc(value):
    """Normalize a recorded ISO-8601 time to `YYYY-MM-DDTHH:MM:SSZ`; a date-only value stays a date."""
    if not isinstance(value, str) or not value:
        return None
    if len(value) == 10:
        return dt.date.fromisoformat(value).isoformat()
    moment = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if moment.tzinfo is None:
        raise ValueError('Recorded time lacks a UTC offset: ' + value)
    return moment.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def review_dates(root):
    """Editorial review time of each approved resource, keyed by catalog ID (the README's recently reviewed list uses the same map).

    A checkout without data/editorial.json (such as a minimal test fixture) has no recorded review times."""
    path = Path(root) / 'data/editorial.json'
    editorial = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    return {(entry.get('id') or editorial_identity(entry)[0]): utc(entry['reviewed_at'])
            for entry in editorial if entry.get('editorial_reviewed') and entry.get('reviewed_at')}


def record_modified(record, reviewed):
    """Latest recorded time behind a record's page: its editorial review, metadata verification or evidence retrieval."""
    times = [utc(record.get('last_verified_at')), reviewed.get(record['id']) if eligible(record) else None]
    times += [utc(item.get('retrieved_at')) for item in record.get('evidence', [])]
    return max((value for value in times if value), default=None)


def latest(records, reviewed):
    """Latest data time across records, or None when no record carries one."""
    return max((value for value in (record_modified(r, reviewed) for r in records) if value), default=None)


def newest_reviewed(rows, reviewed, limit=None):
    """Curated records, most recently reviewed first; ties keep a stable name and ID order."""
    selected = sorted((r for r in rows if eligible(r) and reviewed.get(r['id'])), key=lambda r: (r['name'].casefold(), r['id']))
    selected.sort(key=lambda r: reviewed[r['id']], reverse=True)
    return selected[:limit] if limit else selected


def catalog_counts(rows, coverage, candidate_manifest=None):
    """Curated-only headline counts with the unreviewed populations reported beside them, never added in."""
    curated = [row for row in rows if eligible(row)]
    kinds = Counter(row['kind'] for row in curated)
    papers = sum(kinds[kind] for kind in PAPER_KINDS)
    observations = (candidate_manifest or {}).get('count', {}).get('value')
    return {
        'curated': {'total': len(curated), 'papers_and_surveys': papers, 'other_resources': len(curated) - papers,
                    'by_kind': {kind: kinds[kind] for kind in KIND_ORDER if kinds[kind]}},
        'awaiting_review': {
            'metadata_only_records': sum(row['review_status'] == 'metadata_verified' for row in rows),
            'unresolved_candidate_identifiers': coverage.get('unindexed_candidates', 0),
            'github_candidate_repositories': observations if isinstance(observations, int) else None},
        'active_records': len(rows),
        'snapshot': coverage['as_of_utc'],
        'note': COUNT_NOTE,
    }
