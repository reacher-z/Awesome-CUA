"""Static, versioned JSON and CSV API under /api/v1/, generated from the same records as the website.

Every file carries `version` (the API format version) and `generated_at` (the newest recorded data time in the
snapshot, so two builds of one source commit write the same bytes). The API indexes the catalog compactly: an
item's Markdown, complete record and citation files live at fixed paths below its `page_url`, and the bulk
downloads hold every record with full evidence, so neither is copied here.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path

from publication_metadata import authors_omitted, publication, record_date_text
from site_data import PAPER_KINDS, eligible, newest_reviewed, utc

API_VERSION = '1.0.0'
API_PATH = '/api/v1/'
CHANGE_WINDOW_DAYS = 30
NOT_CURATED = ('UNREVIEWED: nothing in this file is part of the curated AwesomeCUA catalog. Rows are discovered identifiers '
               'or bibliography records whose relevance has not been reviewed; do not cite them as recommendations or count them as catalog resources.')
LICENSE_NOTE = 'Catalog annotations and these files: MIT. Linked resources, papers, data and weights keep their own terms.'
# Files reached from an item's page_url; listed once per file instead of once per item.
ITEM_LINKS = {'markdown': '{page_url}index.md', 'record': '{page_url}record.json'}
PAPER_LINKS = {**ITEM_LINKS, 'bibtex': '{page_url}citation.bib', 'csl_json': '{page_url}citation.csl.json'}
DEFAULT_QUEUE_REASON = 'discovered identifier; primary evidence and relevance need review'


def _url(site, path):
    return site + path


def _licenses(record):
    """Declared licenses only, by scope (code, data, document, weights); an absent scope means no license is recorded."""
    return {slot: {'declared': value['declared'], 'url': value['url']} for slot, value in record['licenses'].items() if value}


def _common(record, site, resource_path):
    return {'id': record['id'], 'name': record['name'], 'kind': record['kind'], 'url': record['url'], 'page_url': site + resource_path(record)}


def resource_item(record, site, resource_path, reviewed):
    return {**_common(record, site, resource_path), 'summary': record['summary'], 'scope': record['scope'],
            'review_status': record['review_status'], 'environments': record['environments'], 'topics': record['topics'],
            'aliases': record['aliases'], 'licenses': _licenses(record), 'published_at': record['published_at'],
            'reviewed_at': reviewed.get(record['id']), 'last_verified_at': utc(record['last_verified_at']),
            'relations': [{'type': relation['type'], 'target_id': relation['target_id']} for relation in record['relations']]}


def paper_item(record, site, resource_path, reviewed):
    snapshot = record['details'].get('arxiv_snapshot') or {}
    pub = publication(record) or {}
    return {**_common(record, site, resource_path), 'summary': record['summary'], 'scope': record['scope'],
            'review_status': record['review_status'], 'authors': [] if authors_omitted(record) else record['authors'],
            'authors_omitted': authors_omitted(record), 'published': record_date_text(record) or None,
            'arxiv_id': record['identifiers'].get('arxiv'), 'arxiv_version': snapshot.get('version'), 'arxiv_versioned_url': snapshot.get('versioned_url'),
            'venue': pub.get('venue'), 'doi': pub.get('doi'),
            'environments': record['environments'], 'topics': record['topics'], 'licenses': _licenses(record),
            'reviewed_at': reviewed.get(record['id']), 'last_verified_at': utc(record['last_verified_at'])}


def candidate_items(rows, queue, site, resource_path, holds):
    """Unreviewed populations, each row flagged: relevance-pending records first, then unresolved identifiers."""
    items = []
    for record in sorted((r for r in rows if r['review_status'] == 'metadata_verified'), key=lambda r: r['id']):
        hold = holds.get(record['id'])
        items.append({'population': 'relevance_pending_record', 'curated': False, **_common(record, site, resource_path),
                      'review_status': record['review_status'], 'scope': record['scope'], 'published': record_date_text(record) or None,
                      'reason': hold, 'first_discovered_at': None})
    active = {row['id'] for row in rows}
    for row in sorted(queue, key=lambda r: r['id']):
        if row.get('resolution') or row['id'] in active:
            continue  # set aside as a non-resource or an alias, or already listed above as an active record
        items.append({'population': 'candidate_identifier', 'curated': False, 'id': row['id'],
                      'name': row.get('name') or row.get('discovered_title'), 'kind': None, 'url': row['url'],
                      'page_url': None, 'review_status': 'candidate', 'scope': None, 'published': None,
                      'reason': None if row['reason'] == DEFAULT_QUEUE_REASON else row['reason'],
                      'first_discovered_at': utc(row.get('first_discovered_at'))})
    return items


EVENTS = {
    'reviewed': 'Passed AI-assisted editorial review against a primary source and joined (or was re-reviewed in) the curated catalog.',
    'added_to_bibliography': 'Discovered by a scheduled scan; bibliographic metadata verified, relevance not yet reviewed.',
    'excluded': 'Removed from the active catalog after a primary-abstract scope review; `note` gives the recorded reason.',
}


def change_events(rows, reviewed, scan_history, exclusions, snapshot, site, resource_path):
    """Catalog events in the CHANGE_WINDOW_DAYS up to the snapshot: reviews, bibliography additions and scope exclusions."""
    end = dt.datetime.fromisoformat(snapshot.replace('Z', '+00:00'))
    start = utc((end - dt.timedelta(days=CHANGE_WINDOW_DAYS)).isoformat())
    lookup = {row['id']: row for row in rows}
    events = []
    def add(date, event, identity, name, kind, url, note=None):
        record = lookup.get(identity)
        events.append({'date': date, 'event': event, 'id': identity, 'name': name, 'kind': kind,
                       'current_status': record['review_status'] if record else ('excluded' if event == 'excluded' else 'not_active'),
                       'page_url': site + resource_path(record) if record else (site + resource_path({'id': identity}) if event == 'excluded' else None),
                       'url': url, 'note': note})
    for record in newest_reviewed(rows, reviewed):
        if reviewed[record['id']] >= start:
            add(reviewed[record['id']], 'reviewed', record['id'], record['name'], record['kind'], record['url'])
    for scan in scan_history:
        finished = utc(scan.get('finished_at'))
        if not finished or finished < start:
            continue
        for paper in scan.get('new_papers', []):
            add(finished, 'added_to_bibliography', paper['id'], paper['name'], 'paper', paper['url'])
    for decision in exclusions:
        if decision['status'] == 'excluded' and utc(decision['reviewed_at']) >= start:
            add(utc(decision['reviewed_at']), 'excluded', decision['id'], decision['name'], None, decision['url'], decision['reason'])
    events.sort(key=lambda e: (e['date'], e['event'], e['id']), reverse=True)
    return events, start


def category_items(rows, counts, topic_groups, site, kinds, kind_labels, topic_name, topic_path):
    kind_rows = []
    for kind, label in kinds.items():
        kind_rows.append({'id': kind, 'name': label, 'name_zh': kind_labels[kind][1], 'type': 'kind',
                          'curated_count': counts['curated']['by_kind'].get(kind, 0),
                          'active_count': sum(row['kind'] == kind for row in rows),
                          'page_url': f'{site}/categories/{kind}/', 'markdown_url': f'{site}/categories/{kind}/index.md',
                          'api_url': site + API_PATH + ('papers.json' if kind in PAPER_KINDS else 'resources.json')})
    topic_rows = []
    for topic, members in topic_groups.items():
        topic_rows.append({'id': topic, 'name': topic_name(topic), 'name_zh': topic_name(topic, 'zh'), 'type': 'topic',
                           'curated_count': len(members), 'active_count': None,
                           'page_url': site + topic_path(topic), 'markdown_url': site + topic_path(topic) + 'index.md',
                           'api_url': f'{site}/downloads/topics/{topic}/records.jsonl'})
    return kind_rows + topic_rows


def envelope(kind, description, items, *, snapshot, catalog_sha256, site, extra=None):
    return {'version': API_VERSION, 'generated_at': snapshot, 'catalog_sha256': catalog_sha256, 'license': LICENSE_NOTE,
            'documentation': site + '/api/', 'schema': site + API_PATH + 'schema.json#/$defs/' + kind,
            'description': description, **(extra or {}), 'count': len(items), 'items': items}


def dump(document):
    """Compact JSON with one item per line: small enough to fetch whole, and line-diffable between snapshots."""
    head = {key: value for key, value in document.items() if key != 'items'}
    rows = ',\n'.join(json.dumps(item, ensure_ascii=False, separators=(',', ':')) for item in document['items'])
    return json.dumps(head, ensure_ascii=False, separators=(',', ':'))[:-1] + ',"items":[\n' + rows + ('\n' if rows else '') + ']}\n'


CSV_COLUMNS = {
    'resources': ('id', 'name', 'kind', 'url', 'page_url', 'summary', 'scope', 'environments', 'topics', 'licenses', 'published_at', 'reviewed_at', 'last_verified_at'),
    'papers': ('id', 'name', 'kind', 'url', 'page_url', 'summary', 'authors', 'authors_omitted', 'published', 'arxiv_id', 'arxiv_version', 'arxiv_versioned_url', 'venue', 'doi', 'environments', 'topics', 'reviewed_at'),
    'categories': ('type', 'id', 'name', 'name_zh', 'curated_count', 'active_count', 'page_url', 'markdown_url', 'api_url'),
    'candidates': ('population', 'curated', 'id', 'name', 'kind', 'url', 'page_url', 'review_status', 'scope', 'published', 'reason', 'first_discovered_at'),
    'changes': ('date', 'event', 'id', 'name', 'kind', 'current_status', 'page_url', 'url', 'note'),
}


def _cell(value):
    # Whitespace runs collapse to one space: a CSV row stays one line and no line ends in a space.
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, list):
        text = '; '.join(str(item) for item in value)
    elif isinstance(value, dict):
        text = '; '.join(f'{slot}: {item["declared"] if isinstance(item["declared"], str) else ", ".join(item["declared"])}' for slot, item in value.items() if item)
    else:
        text = str(value)
    return ' '.join(text.split())


def csv_text(name, document):
    """One row per item; every row repeats the file's version and snapshot time so a CSV carries both too."""
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(('version', 'generated_at', *CSV_COLUMNS[name]))
    for item in document['items']:
        writer.writerow((document['version'], document['generated_at'], *(_cell(item.get(column)) for column in CSV_COLUMNS[name])))
    return stream.getvalue()


ENDPOINTS = (
    ('resources', 'Curated resources other than papers: models, datasets, benchmarks, agents, frameworks, infrastructure, tools, products, publishers and learning resources.'),
    ('papers', 'Curated research papers and surveys, with authors, recorded publication dates, arXiv versions and citation files.'),
    ('categories', 'Resource kinds and research topics with curated counts and links to their pages, Markdown and data.'),
    ('changes', f'Catalog events in the {CHANGE_WINDOW_DAYS} days before the snapshot: editorial reviews, new bibliography records and scope exclusions.'),
    ('candidates', 'UNREVIEWED rows, clearly flagged: bibliography records awaiting relevance review and discovered identifiers awaiting any review. Not part of the curated catalog.'),
)


def _schema(site, snapshot):
    text, nullable = {'type': 'string'}, {'type': ['string', 'null']}
    when = {'type': 'string', 'pattern': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'}
    when_or_null = {'anyOf': [when, {'type': 'null'}]}
    # Editorial reviews retain their recorded precision; observation times stay timestamp-only.
    review_date = {'anyOf': [when, {'type': 'string', 'pattern': r'^\d{4}-\d{2}-\d{2}$'}]}
    review_or_null = {'anyOf': [review_date, {'type': 'null'}]}
    strings = {'type': 'array', 'items': text}
    link = {'type': 'string', 'pattern': '^https://'}
    link_or_null = {'anyOf': [link, {'type': 'null'}]}
    def item(properties, required=None):
        return {'type': 'object', 'properties': properties, 'required': sorted(required or properties), 'additionalProperties': False}
    identity = {'id': text, 'name': text, 'kind': text, 'url': link, 'page_url': link}
    defs = {
        'license': item({'declared': {'anyOf': [text, strings]}, 'url': link}),
        'licenses': {'type': 'object', 'properties': {slot: {'$ref': '#/$defs/license'} for slot in ('code', 'data', 'document', 'weights')}, 'additionalProperties': False},
        'resource': item({**identity, 'summary': text, 'scope': {'enum': ['core', 'adjacent']}, 'review_status': {'const': 'curated'},
                          'environments': strings, 'topics': strings, 'aliases': {'type': 'array'}, 'licenses': {'$ref': '#/$defs/licenses'},
                          'published_at': nullable, 'reviewed_at': review_or_null, 'last_verified_at': when,
                          'relations': {'type': 'array', 'items': item({'type': text, 'target_id': text})}}),
        'paper': item({**identity, 'kind': {'enum': ['paper', 'survey']}, 'summary': text, 'scope': {'enum': ['core', 'adjacent']},
                       'review_status': {'const': 'curated'}, 'authors': strings, 'authors_omitted': {'type': 'boolean'}, 'published': nullable,
                       'arxiv_id': nullable, 'arxiv_version': {'type': ['integer', 'null']}, 'arxiv_versioned_url': nullable, 'venue': nullable,
                       'doi': nullable, 'environments': strings, 'topics': strings, 'licenses': {'$ref': '#/$defs/licenses'},
                       'reviewed_at': review_or_null, 'last_verified_at': when}),
        'category': item({'id': text, 'name': text, 'name_zh': text, 'type': {'enum': ['kind', 'topic']}, 'curated_count': {'type': 'integer', 'minimum': 0},
                          'active_count': {'type': ['integer', 'null']}, 'page_url': link, 'markdown_url': link, 'api_url': link}),
        'candidate': item({'population': {'enum': ['relevance_pending_record', 'candidate_identifier']}, 'curated': {'const': False},
                           'id': text, 'name': nullable, 'kind': nullable, 'url': link, 'page_url': link_or_null,
                           'review_status': {'enum': ['metadata_verified', 'candidate']}, 'scope': nullable,
                           'published': nullable, 'reason': nullable, 'first_discovered_at': when_or_null}),
        'change': item({'date': review_date, 'event': {'enum': sorted(EVENTS)}, 'id': text, 'name': text,
                        'kind': nullable, 'current_status': text, 'page_url': link_or_null, 'url': link, 'note': nullable}),
        'envelope': {'type': 'object', 'required': ['version', 'generated_at', 'catalog_sha256', 'license', 'documentation', 'schema', 'description', 'count', 'items'],
                     'properties': {'version': {'const': API_VERSION}, 'generated_at': when, 'catalog_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                                    'count': {'type': 'integer', 'minimum': 0}, 'items': {'type': 'array'}}},
        'endpoint': item({'name': text, 'description': text, 'json': link, 'csv': link, 'count': {'type': 'integer'},
                          'json_bytes': {'type': 'integer'}, 'json_sha256': text, 'csv_bytes': {'type': 'integer'}, 'csv_sha256': text}),
        'index': {'type': 'object', 'required': ['version', 'generated_at', 'catalog_sha256', 'documentation', 'schema', 'counts', 'endpoints'],
                  'properties': {'version': {'const': API_VERSION}, 'generated_at': when, 'endpoints': {'type': 'array', 'items': {'$ref': '#/$defs/endpoint'}}}},
    }
    for name, member in (('resources', 'resource'), ('papers', 'paper'), ('categories', 'category'), ('candidates', 'candidate'), ('changes', 'change')):
        defs[name] = {'allOf': [{'$ref': '#/$defs/envelope'}, {'properties': {'items': {'type': 'array', 'items': {'$ref': '#/$defs/' + member}}}}]}
    defs['candidates']['allOf'].append({'required': ['notice'], 'properties': {'notice': {'const': NOT_CURATED}, 'review_status': {'const': 'unreviewed'}}})
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': site + API_PATH + 'schema.json',
            'title': 'AwesomeCUA static API v1', 'version': API_VERSION, 'generated_at': snapshot,
            'description': ('JSON Schema for every file under /api/v1/. Validate a file against $defs/<name>, for example $defs/resources for resources.json. '
                            'generated_at is the newest recorded data time in the snapshot (UTC), not the wall-clock build time.'),
            '$defs': defs, 'anyOf': [{'$ref': '#/$defs/' + name} for name in ('resources', 'papers', 'categories', 'candidates', 'changes', 'index')]}


def snapshot_time(rows, coverage, review_times, exclusions, scan_history):
    """The newest recorded data time in a source snapshot: the API's `generated_at` and the end of its change window."""
    times = [coverage['as_of_utc'], *review_times.values(), *(utc(row['last_verified_at']) for row in rows)]
    times += [utc(item['retrieved_at']) for row in rows for item in row['evidence']]
    times += [utc(decision['reviewed_at']) for decision in exclusions] + [utc(scan.get('finished_at')) for scan in scan_history]
    return max(value for value in times if value)


def write_api(destination, *, rows, coverage, root, site, resource_path, review_times, counts, catalog_sha256, kinds, kind_labels, topic_groups, topic_name, topic_path):
    """Write every /api/v1/ file and return the endpoint list that the documentation page describes."""
    target = Path(destination) / API_PATH.strip('/')
    target.mkdir(parents=True, exist_ok=True)
    holds = {item['id']: item['reason'] for item in coverage.get('pending_editorial', []) if item.get('cause') == 'reviewer_hold' and item.get('reason')}
    queue_path = Path(root) / 'data/review-queue.jsonl'
    queue = [json.loads(line) for line in queue_path.read_text(encoding='utf-8').splitlines() if line.strip()] if queue_path.exists() else []
    history_path = Path(root) / 'data/scan-history.jsonl'
    history = [json.loads(line) for line in history_path.read_text(encoding='utf-8').splitlines() if line.strip()] if history_path.exists() else []
    exclusions = json.loads((Path(root) / 'data/exclusion-status.json').read_text(encoding='utf-8'))['decisions']
    snapshot = snapshot_time(rows, coverage, review_times, exclusions, history)
    curated = sorted((row for row in rows if eligible(row)), key=lambda row: row['id'])
    events, start = change_events(rows, review_times, history, exclusions, snapshot, site, resource_path)
    common = {'snapshot': snapshot, 'catalog_sha256': catalog_sha256, 'site': site}
    descriptions = dict(ENDPOINTS)
    documents = {
        'resources': envelope('resources', descriptions['resources'], [resource_item(r, site, resource_path, review_times) for r in curated if r['kind'] not in PAPER_KINDS], **common, extra={'links': ITEM_LINKS}),
        'papers': envelope('papers', descriptions['papers'], [paper_item(r, site, resource_path, review_times) for r in curated if r['kind'] in PAPER_KINDS], **common, extra={'links': PAPER_LINKS}),
        'categories': envelope('categories', descriptions['categories'], category_items(rows, counts, topic_groups, site, kinds, kind_labels, topic_name, topic_path), **common, extra={'counts': counts}),
        'changes': envelope('changes', descriptions['changes'], events, **common, extra={'window': {'start': start, 'end': snapshot, 'days': CHANGE_WINDOW_DAYS}, 'events': EVENTS}),
        'candidates': envelope('candidates', descriptions['candidates'], candidate_items(rows, queue, site, resource_path, holds), **common,
                               extra={'notice': NOT_CURATED, 'review_status': 'unreviewed', 'links': ITEM_LINKS,
                                      'populations': {'relevance_pending_record': 'In the catalog with verified bibliographic metadata; relevance not reviewed. `reason` is a recorded reviewer hold, if any. Pages are noindex.',
                                                      'candidate_identifier': 'Discovered identifier, not yet a catalog record; `reason` is recorded only when it differs from the default (primary evidence and relevance need review).'},
                                      'github_candidate_observations': {'url': site + '/downloads/github-candidates.jsonl', 'manifest': site + '/downloads/github-candidates-manifest.json',
                                                                        'repositories': counts['awaiting_review']['github_candidate_repositories'],
                                                                        'note': 'Public GitHub metadata observations, all unreviewed; published separately and not copied here.'}}),
    }
    endpoints = []
    for name, description in ENDPOINTS:
        body = dump(documents[name])
        table = csv_text(name, documents[name])
        (target / (name + '.json')).write_text(body, encoding='utf-8')
        (target / (name + '.csv')).write_text(table, encoding='utf-8')
        endpoints.append({'name': name, 'description': description, 'json': site + API_PATH + name + '.json', 'csv': site + API_PATH + name + '.csv',
                          'count': documents[name]['count'], 'json_bytes': len(body.encode()), 'json_sha256': hashlib.sha256(body.encode()).hexdigest(),
                          'csv_bytes': len(table.encode()), 'csv_sha256': hashlib.sha256(table.encode()).hexdigest()})
    schema = _schema(site, snapshot)
    (target / 'schema.json').write_text(json.dumps(schema, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    index = {'version': API_VERSION, 'generated_at': snapshot, 'catalog_sha256': catalog_sha256, 'license': LICENSE_NOTE,
             'documentation': site + '/api/', 'schema': site + API_PATH + 'schema.json', 'counts': counts, 'endpoints': endpoints,
             'bulk_downloads': {'catalog_jsonl': site + '/downloads/catalog.jsonl', 'catalog_sqlite': site + '/downloads/catalog.sqlite',
                                'download_manifest': site + '/downloads/manifest.json'}}
    (target / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return index


def _size(value):
    return f'{value / 1024:,.0f} KiB' if value < 1024 * 1024 else f'{value / (1024 * 1024):.1f} MiB'


API_TITLE = 'AwesomeCUA static data API'
API_SUMMARY = ('Versioned JSON and CSV files for agents and scripts: curated resources and papers, categories, recent changes and '
               'clearly flagged unreviewed candidates, regenerated with every catalog snapshot. No key or account is needed.')
FIELD_NOTES = (
    ('Identity', 'Each item keeps the catalog `id`, which never changes when a resource is renamed. `url` is the original source and `page_url` the catalog page. The page\'s Markdown version, complete record and (for papers) citation files sit at fixed paths below `page_url`, given once per file in `links`, such as `{page_url}record.json`.'),
    ('Versions', '`version` is the API format version: a new major version means a breaking field change, minor versions add fields. `generated_at` is the newest recorded data time in the snapshot (UTC), so every file built from one source commit carries the same value. `catalog_sha256` fingerprints the source catalog.'),
    ('Review states', '`resources.json`, `papers.json` and the counts in `categories.json` contain curated records only: an AI-assisted editorial review checked each against a primary source. `candidates.json` is unreviewed and every row says so.'),
    ('Dates', '`reviewed_at` and change-event `date` retain the recorded precision: YYYY-MM-DD or a UTC timestamp. Observation timestamps and `generated_at` use YYYY-MM-DDTHH:MM:SSZ.'),
    ('Licenses', 'Code, data, weights and document licenses are separate declarations; `null` means no license is recorded. Catalog annotations and these files are MIT licensed; linked resources keep their own terms.'),
    ('Caching and CORS', 'The files are static and served by GitHub Pages with `Access-Control-Allow-Origin: *`, an `ETag` and `Last-Modified`, so browsers can fetch them across origins and clients can send conditional requests. Compare `generated_at` or `catalog_sha256` before re-ingesting.'),
    ('CSV', 'Each CSV has one row per JSON item and repeats `version` and `generated_at` in every row. Lists are joined with `; `, and whitespace inside a value collapses to single spaces.'),
)


def api_docs_body(index, *, site, esc):
    """HTML body of /api/ (rendered inside the site's shared page template)."""
    rows = ''.join(f'<tr><td><a href="{esc(item["json"])}">{esc(item["name"])}.json</a></td><td><a href="{esc(item["csv"])}">{esc(item["name"])}.csv</a></td>'
                   f'<td>{item["count"]:,}</td><td>{esc(_size(item["json_bytes"]))}</td><td>{esc(item["description"])}</td></tr>' for item in index['endpoints'])
    body = (f'<div class="eyebrow">STATIC API</div><h1>{esc(API_TITLE)}</h1><p class="answer-lead">{esc(API_SUMMARY)}</p>'
            f'<p>Base URL: <code>{esc(site + API_PATH)}</code> · Version {esc(index["version"])} · Snapshot {esc(index["generated_at"])} · '
            f'<a href="{esc(site + API_PATH + "index.json")}">API index</a> · <a href="{esc(site + API_PATH + "schema.json")}">JSON Schema</a> · <a href="/api/index.md">Markdown version</a></p>'
            '<h2>Endpoints</h2><div class="table-scroll"><table class="coverage-table"><thead><tr><th>JSON</th><th>CSV</th><th>Items</th><th>Size</th><th>Contents</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')
    for heading, text in FIELD_NOTES:
        body += f'<h2>{esc(heading)}</h2><p>{_code(esc(text))}</p>'
    body += ('<h2>Examples</h2><pre class="command-block"><code>'
             + esc(f"curl -s {site}{API_PATH}resources.json | jq -r '.items[] | select(.kind == \"benchmark\") | .name'")
             + '</code></pre><pre class="command-block"><code>'
             + esc(f"python3 -c \"import json, urllib.request; d = json.load(urllib.request.urlopen('{site}{API_PATH}papers.json')); print(d['generated_at'], d['count'])\"")
             + '</code></pre>'
             '<h2>Bulk data</h2><p>The API indexes the catalog; it does not copy it. For every record with full evidence use the '
             '<a href="/downloads/catalog.jsonl">catalog JSONL</a>, the <a href="/downloads/catalog.sqlite">SQLite database</a> or the <a href="/data/">data hub</a>, '
             'and for unreviewed GitHub repositories the <a href="/downloads/github-candidates.jsonl">candidate observations</a>.</p>')
    return body


def _code(text):
    # Backticks in the shared notes mark code; HTML gets <code>, Markdown keeps the backticks.
    parts = text.split('`')
    return ''.join(f'<code>{part}</code>' if i % 2 else part for i, part in enumerate(parts))


def api_docs_markdown(index, *, site):
    lines = [f'# {API_TITLE}', '', f'> {API_SUMMARY}', '',
             f'Base URL: {site}{API_PATH} · Version {index["version"]} · Snapshot {index["generated_at"]} · HTML page: {site}/api/', '',
             f'- [API index]({site}{API_PATH}index.json): endpoints with counts, byte sizes and SHA-256',
             f'- [JSON Schema]({site}{API_PATH}schema.json): validate a file against `$defs/<name>`', '', '## Endpoints', '']
    lines += [f'- [{item["name"]}.json]({item["json"]}) ([CSV]({item["csv"]})), {item["count"]:,} items: {item["description"]}' for item in index['endpoints']]
    for heading, text in FIELD_NOTES:
        lines += ['', f'## {heading}', '', text]
    lines += ['', '## Bulk data', '', f'- [Catalog JSONL]({site}/downloads/catalog.jsonl): every active record with full evidence',
              f'- [SQLite database]({site}/downloads/catalog.sqlite)', f'- [Download manifest]({site}/downloads/manifest.json)']
    return '\n'.join(lines) + '\n'
