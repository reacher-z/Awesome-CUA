"""Version and abstract fingerprints from an individual, retained Atom entry."""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import urllib.parse
import xml.etree.ElementTree as ET

ATOM = '{http://www.w3.org/2005/Atom}'
ABSTRACT_HASH_METHOD = 'sha256-utf8-whitespace-collapsed-v1'
SNAPSHOT_FIELDS = ('version', 'submitted_at', 'updated_at', 'abstract_sha256')


def parse_search_feed(body, expected_total=None, max_entries=None):
    """A successful HTTP response alone does not prove a complete arXiv search."""
    root = ET.fromstring(body)
    if root.tag != ATOM + 'feed':
        raise ValueError('arXiv response is not an Atom feed')
    entries = root.findall(ATOM + 'entry')
    if any('/api/errors' in entry.findtext(ATOM + 'id', '') for entry in entries):
        raise ValueError('arXiv returned an API error entry instead of search results')
    text = root.findtext('{http://a9.com/-/spec/opensearch/1.1/}totalResults')
    if text is None:
        raise ValueError('arXiv feed is missing totalResults')
    total = int(text)
    if total < 0:
        raise ValueError('arXiv totalResults must be nonnegative')
    if expected_total is not None and total != expected_total:
        raise ValueError('arXiv result population changed during pagination')
    if len(entries) > total or (max_entries is not None and len(entries) > max_entries):
        raise ValueError('arXiv returned more entries than its request or result count')
    return entries, total


def timestamp(value):
    if not value:
        return None
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('arXiv entry timestamp requires a timezone')
    return parsed.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def entry_snapshot(entry, arxiv_id):
    text = lambda name: ' '.join(entry.findtext(ATOM + name, '').split())
    path = urllib.parse.urlsplit(text('id')).path.rstrip('/')
    version = re.fullmatch(r'/abs/' + re.escape(arxiv_id) + r'v([1-9][0-9]*)', path)
    abstract = text('summary')
    number = int(version[1]) if version else None
    return {
        'version': number,
        'versioned_url': f'https://arxiv.org/abs/{arxiv_id}v{number}' if number else None,
        'submitted_at': timestamp(text('published')),
        'updated_at': timestamp(text('updated')),
        'abstract_sha256': hashlib.sha256(abstract.encode('utf-8')).hexdigest() if abstract else None,
        'abstract_hash_method': ABSTRACT_HASH_METHOD,
    }


def snapshot_differences(current, observed):
    """Return changed facts and uncertainty, without adopting an observed baseline."""
    if not observed:
        return {}, 'observed_snapshot_missing'
    current = current or {}
    def comparable(field, value):
        return timestamp(value) if field in {'submitted_at','updated_at'} else value
    changes = {
        'details.arxiv_snapshot.' + field: {'current': current.get(field), 'observed': observed.get(field)}
        for field in SNAPSHOT_FIELDS if comparable(field,current.get(field)) != comparable(field,observed.get(field))
    }
    if current.get('abstract_hash_method') != ABSTRACT_HASH_METHOD or observed.get('abstract_hash_method') != ABSTRACT_HASH_METHOD:
        if current.get('abstract_hash_method') != observed.get('abstract_hash_method'):
            changes['details.arxiv_snapshot.abstract_hash_method'] = {
                'current': current.get('abstract_hash_method'), 'observed': observed.get('abstract_hash_method')}
        return changes, 'snapshot_baseline_requires_review'
    if any(current.get(field) is None for field in SNAPSHOT_FIELDS):
        return changes, 'snapshot_baseline_requires_review'
    if any(observed.get(field) is None for field in SNAPSHOT_FIELDS):
        return changes, 'observed_snapshot_incomplete'
    return changes, None


def consider_paper(row, records, proposals, observed_at):
    """Retain existing snapshots and propose source changes or missing-baseline review."""
    rid = row['id']
    if rid not in records:
        records[rid] = row
        return True
    old = records[rid]
    # An omitted author list is never compared with, or proposed from, the names a source returns.
    fields = ('name', 'published_at', 'updated_at') if old.get('authors_omitted') is True else ('name', 'authors', 'published_at', 'updated_at')
    changes = {field: {'current': old.get(field), 'observed': row.get(field)}
               for field in fields if old.get(field) != row.get(field)}
    known_change = bool(changes)
    current = old.get('details', {}).get('arxiv_snapshot')
    observed = row.get('details', {}).get('arxiv_snapshot')
    snapshot_changes, uncertainty = snapshot_differences(current, observed)
    same_hash_method = bool(current and observed and current.get('abstract_hash_method') == observed.get('abstract_hash_method') == ABSTRACT_HASH_METHOD)
    known_change |= any(value['current'] is not None and value['observed'] is not None
                        and (not field.endswith('abstract_sha256') or same_hash_method)
                        and not field.endswith('abstract_hash_method')
                        for field, value in snapshot_changes.items())
    changes.update(snapshot_changes)
    if changes or uncertainty:
        previous = proposals.get(rid, {})
        proposals[rid] = {
            'id': rid, 'url': row['url'],
            'review_status': 'metadata_change_pending' if known_change else 'metadata_revalidation_pending',
            'first_observed_at': previous.get('first_observed_at', observed_at),
            'last_observed_at': observed_at, 'changes': changes,
            'evidence': row['evidence'], 'observed_snapshot': observed,
        }
        if uncertainty:
            proposals[rid]['reason'] = uncertainty
    elif observed_at >= proposals.get(rid, {}).get('last_observed_at', ''):
        # A complete observation that matches the retained record again withdraws a pending proposal,
        # unless it predates that proposal, as a cached page replayed without --refresh can.
        proposals.pop(rid, None)
    return False


def validate_snapshot(record):
    snapshot = record.get('details', {}).get('arxiv_snapshot')
    if snapshot is None:
        return []
    if not isinstance(snapshot, dict):
        return ['arXiv snapshot must be an object']
    errors = []
    rid = record.get('id', '')
    if not rid.startswith('arxiv:') or record.get('kind') not in {'paper', 'survey'}:
        errors.append('arXiv snapshot requires an arXiv paper or survey')
    if set(snapshot) != (keys := {*SNAPSHOT_FIELDS, 'versioned_url', 'abstract_hash_method'}):
        errors.append('arXiv snapshot needs exactly ' + ', '.join(sorted(keys)))
    digest = snapshot.get('abstract_sha256')
    if snapshot.get('abstract_hash_method') != ABSTRACT_HASH_METHOD or digest is not None and not (isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest)):
        errors.append('arXiv snapshot abstract fingerprint is not a ' + ABSTRACT_HASH_METHOD + ' SHA-256 digest')
    version = snapshot.get('version')
    expected = f'https://arxiv.org/abs/{rid.split(":",1)[-1]}v{version}' if type(version) is int and version > 0 else None
    if snapshot.get('versioned_url') != expected:
        errors.append('arXiv version link does not match the record identity and version')
    try:
        submitted = timestamp(snapshot.get('submitted_at'))
        updated = timestamp(snapshot.get('updated_at'))
        if submitted and updated and dt.datetime.fromisoformat(updated.replace('Z','+00:00')) < dt.datetime.fromisoformat(submitted.replace('Z','+00:00')):
            errors.append('arXiv version update precedes its first submission')
    except (ValueError, TypeError, AttributeError):
        errors.append('arXiv snapshot has an invalid timestamp')
    if not any(source.get('method') == 'arxiv_api' and 'details.arxiv_snapshot' in source.get('supports', [])
               for source in record.get('evidence', [])):
        errors.append('arXiv snapshot lacks a supporting Atom-entry receipt')
    return errors
