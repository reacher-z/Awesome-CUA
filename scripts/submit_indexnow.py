#!/usr/bin/env python3
"""Notify IndexNow of published page changes. Dry run unless --submit is supplied."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'https://api.indexnow.org/indexnow'
USER_AGENT = 'AwesomeCUA-indexing/2.0'


def read_json(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def valid_path(path):
    if not isinstance(path, str) or not path.startswith('/') or path.startswith('//'):
        return False
    parsed = urllib.parse.urlsplit(path)
    return not (parsed.netloc or parsed.scheme or parsed.query or parsed.fragment or '\\' in path or any(c.isspace() for c in path))


def fingerprints(manifest, site):
    if manifest.get('site_url', '').rstrip('/') != site:
        raise ValueError('Manifest origin does not match configured site')
    result, seen = {}, set()
    for page in manifest['pages']:
        path = page['path']
        if not valid_path(path) or path in seen or not re.fullmatch(r'[0-9a-f]{64}', page['sha256']):
            raise ValueError('Invalid or duplicate page identity in manifest')
        seen.add(path)
        if page['indexable'] is True:
            result[path] = page['sha256']
    if manifest['indexable_pages'] != len(result):
        raise ValueError('Manifest indexable count is inconsistent')
    return result


def changed_pages(current, previous):
    return {
        'new': sorted(current.keys() - previous.keys()),
        'changed': sorted(path for path in current.keys() & previous.keys() if current[path] != previous[path]),
        'removed': sorted(previous.keys() - current.keys()),
    }


def fetch_public(url):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def submit_changes(*, site_dir, config_path, state_path, receipts_path, submit=False):
    config = read_json(config_path)
    site = config['site_url'].rstrip('/')
    origin = urllib.parse.urlsplit(site)
    if origin.scheme != 'https' or not origin.hostname or origin.path or origin.query or origin.fragment or origin.username:
        raise ValueError('Expected an HTTPS site origin without credentials or a path')
    key = config['indexnow_key']
    if not re.fullmatch(r'[A-Za-z0-9-]{8,128}', key):
        raise ValueError('Invalid IndexNow ownership key format')
    manifest = read_json(site_dir / 'data/search-manifest.json')
    current = fingerprints(manifest, site)
    namespace = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    sitemap = [entry.text for entry in ET.parse(site_dir / 'sitemap.xml').findall('s:url/s:loc', namespace)]
    if len(sitemap) != len(set(sitemap)) or set(sitemap) != {site + path for path in current}:
        raise ValueError('Sitemap and indexable manifest disagree')
    former_sites = config.get('former_site_urls', [])
    if not isinstance(former_sites, list) or not all(isinstance(url, str) for url in former_sites):
        raise ValueError('Former site origins must be a list of URLs')
    previous_state = read_json(state_path, {})
    replaced_site = None
    if previous_state and previous_state.get('schema_version') == 1 and isinstance(previous_state.get('site'), str) \
            and previous_state['site'] != site and previous_state['site'] in {url.rstrip('/') for url in former_sites}:
        # IndexNow state is per host: pages accepted for a former origin were never submitted for this one.
        replaced_site, previous_state = previous_state['site'], {}
    if previous_state and (previous_state.get('schema_version') != 1 or previous_state.get('site') != site):
        raise ValueError('Accepted-state identity does not match this site')
    previous = previous_state.get('accepted_pages', {})
    if any(not valid_path(path) or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest) for path, digest in previous.items()):
        raise ValueError('Invalid accepted-state page identity')
    changes = changed_pages(current, previous)
    paths = sorted(path for group in changes.values() for path in group)
    if len(paths) > 10000:
        raise ValueError('Change set exceeds the IndexNow 10,000-URL request limit')
    urls = [site + path for path in paths]
    counts = {kind: len(group) for kind, group in changes.items()}
    manifest_digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    build_info = read_json(site_dir / 'data/build-info.json', {})
    receipt = {
        'submitted_at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'provider': 'IndexNow', 'endpoint': ENDPOINT, 'site': site,
        'status': 'dry_run', 'url_count': len(urls), 'urls': urls,
        'changes': counts, 'indexable_pages': len(current), 'manifest_sha256': manifest_digest,
        'source_commit': build_info.get('source_commit'), 'publication_run': build_info.get('publication_run'),
        'meaning': 'Planned changes only; no request sent.',
    }
    if replaced_site:
        receipt['replaces_accepted_state_for'] = replaced_site
    if not submit:
        return receipt
    if not urls:
        receipt.update(status='unchanged', meaning='No changed indexable pages; no network submission sent.')
    else:
        phase = 'preflight'
        try:
            if fetch_public(site + '/' + key + '.txt').decode().strip() != key:
                raise ValueError('Public ownership key does not match')
            live = json.loads(fetch_public(site + '/data/search-manifest.json'))
            if live != manifest:
                raise ValueError('Live site does not match the verified build; refusing a stale submission')
            payload = {'host': origin.netloc, 'key': key, 'keyLocation': site + '/' + key + '.txt', 'urlList': urls}
            request = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json; charset=utf-8', 'User-Agent': USER_AGENT}, method='POST')
            phase = 'submission'
            with urllib.request.urlopen(request, timeout=40) as response:
                receipt.update(status=response.status, response=response.read(2000).decode(errors='replace'))
        except urllib.error.HTTPError as error:
            receipt.update(status=error.code if phase == 'submission' else 'not_sent', response=error.read(2000).decode(errors='replace'), failure_phase=phase)
            error.close()
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            receipt.update(status='not_sent' if phase == 'preflight' else 'unconfirmed', response=str(error), failure_phase=phase)
        receipt['meaning'] = {
            200: 'Submission accepted; indexing is not guaranteed.',
            202: 'URLs received; ownership-key validation pending. Accepted state was not advanced.',
        }.get(receipt['status'], 'Submission not confirmed. Accepted state was not advanced; changes remain eligible for a later attempt.')
        if receipt['status'] == 200:
            write_json(state_path, {
                'schema_version': 1, 'site': site, 'accepted_at': receipt['submitted_at'],
                'manifest_sha256': manifest_digest, 'source_commit': receipt['source_commit'],
                'accepted_pages': current,
            })
    receipts = read_json(receipts_path, [])
    receipts.append(receipt)
    write_json(receipts_path, receipts[-180:])
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submit', action='store_true')
    parser.add_argument('--site-dir', type=Path, default=ROOT / 'dist/site')
    parser.add_argument('--config', type=Path, default=ROOT / 'data/site-discovery.json')
    parser.add_argument('--state', type=Path, default=ROOT / '.cache/indexnow-state.json')
    parser.add_argument('--receipts', type=Path, default=ROOT / 'data/search-submissions.json')
    args = parser.parse_args()
    receipt = submit_changes(site_dir=args.site_dir, config_path=args.config, state_path=args.state, receipts_path=args.receipts, submit=args.submit)
    print(f'IndexNow {receipt["status"]}: {receipt["url_count"]} URLs; {receipt["changes"]}. {receipt["meaning"]}')
    if args.submit and receipt['status'] not in {200, 202, 'unchanged'}:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
