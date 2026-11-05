#!/usr/bin/env python3
"""Assemble the English survey offline from pinned bibliography and reading ledgers.

This builder never reads the mutable production catalog. It does not fetch sources,
approve records, reproduce papers, or publish the resulting working manuscript.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass, field
import hashlib
import html
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
SURVEY = ROOT / 'research/survey'
PIN = '87166fe8ad9c8e832f7a90ee84b2e93c6e0e40db'
CATALOG_SHA = '7f71a1683ab013e587a20086c3e357956981f517a24ae8bc8e81791108c66e4f'
FROZEN_BIBLIOGRAPHY = SURVEY / 'fixtures/frozen-catalog-bibliography.json'
FROZEN_BIBLIOGRAPHY_SHA = 'c78d5601b8797b7768e968989873fc1aab5a9c4a329b46c3183cbb5a4a874c64'
RECORD_HASH_METHOD = 'sha256-utf8-json-sorted-keys-compact-v1'
TITLE = 'Computer-Use Agents: Methods, Evaluation, Human Agency, and Research Assets'
CANONICAL = 'https://awesomecua.github.io/survey/'
SECTIONS = ('context', 'review-design', 'methods', 'evaluation', 'human-agency', 'assets', 'agenda')
EVIDENCE = ('context', 'methods', 'evaluation', 'root', 'corpus-statistics', 'title-search', 'supplementary-screening', 'extra-references')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

sys.path.insert(0, str(ROOT / 'scripts'))
from export_citations import citation_bibtex, citation_csl, citation_key, tex_escape  # noqa: E402
from publication_metadata import AUTHORS_OMITTED, omit_authors  # noqa: E402


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(name):
    return json.loads((SURVEY / 'evidence' / (name + '.json')).read_text())


def safe_url(url):
    parts = urlsplit(url)
    if parts.scheme not in {'https', 'http'} or not parts.netloc or parts.username or parts.password:
        raise ValueError('Expected a public HTTP(S) source URL: ' + str(url))
    return url


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def record_sha256(record):
    return digest(json_text(record).encode('utf-8'))


def history_catalog():
    """Read an already-local object only. Never fetch, and permit shallow checkouts."""
    try:
        result = subprocess.run(['git', 'show', PIN + ':data/catalog.jsonl'], cwd=ROOT, capture_output=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    if digest(result.stdout) != CATALOG_SHA:
        raise ValueError('Available pinned Git object has the wrong catalog fingerprint')
    return result.stdout


def load_frozen_bibliography(path=None, *, check_history=True):
    """Verify the reviewed subset without requiring the complete historical catalog.

    The file digest is pinned in this script; per-record digests additionally make
    selection and identity changes explicit. A subset cannot independently recreate
    the full catalog hash, so that hash remains its documented source provenance.
    """
    path = Path(path) if path is not None else FROZEN_BIBLIOGRAPHY
    data = path.read_bytes()
    if digest(data) != FROZEN_BIBLIOGRAPHY_SHA:
        raise ValueError('Frozen bibliography fixture fingerprint mismatch')
    fixture = json.loads(data)
    if type(fixture.get('schema_version')) is not int or fixture['schema_version'] != 1:
        raise ValueError('Invalid frozen bibliography schema version')
    if fixture.get('source_commit') != PIN or fixture.get('catalog_sha256') != CATALOG_SHA:
        raise ValueError('Frozen bibliography provenance mismatch')
    if fixture.get('catalog_git_path') != 'data/catalog.jsonl' or fixture.get('record_hash_method') != RECORD_HASH_METHOD:
        raise ValueError('Frozen bibliography hashing/source contract mismatch')
    entries = fixture.get('records')
    if not isinstance(entries, list) or type(fixture.get('record_count')) is not int or fixture['record_count'] != len(entries):
        raise ValueError('Frozen bibliography record-count mismatch')
    records, ids, keys = [], set(), set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get('record'), dict):
            raise ValueError('Malformed frozen bibliography entry')
        record = entry['record']
        if record.get('kind') not in {'paper', 'survey'}:
            raise ValueError('Frozen bibliography must contain only paper/survey records')
        if record_sha256(record) != entry.get('record_sha256'):
            raise ValueError('Frozen bibliography record fingerprint mismatch: ' + str(record.get('id')))
        key = citation_key(record)
        # The canonical exporter validates title, author literals, dates and vN URL.
        citation_csl(record)
        if key != entry.get('citation_key') or key in keys or record['id'] in ids:
            raise ValueError('Duplicate or inconsistent frozen bibliography identity')
        ids.add(record['id'])
        keys.add(key)
        records.append(record)
    history = history_catalog() if check_history else None
    if history is not None:
        archived = {r['id']: r for r in map(json.loads, history.splitlines())}
        for record in records:
            expected = archived.get(record['id'])
            if expected is not None and record.get('authors_omitted') is True:
                # The catalog lists no authors for this record; every other field still matches the pinned object.
                expected = omit_authors(expected)
            if expected != record:
                raise ValueError('Frozen bibliography differs from the available pinned Git object: ' + record['id'])
    return records, {
        'fixture_sha256': digest(data), 'record_count': len(records),
        'record_hash_method': RECORD_HASH_METHOD,
        'history_check': 'matched_available_pinned_git_object' if history is not None else 'not_available_or_disabled; verified_pinned_fixture_used',
        'network_requests': 0,
        'subset_cannot_recompute_full_catalog_sha256': True,
    }


def export_frozen_bibliography(destination):
    """Recreate this reviewed fixture from the exact local Git object for maintenance."""
    data = history_catalog()
    if data is None:
        raise ValueError('Fixture export requires the pinned historical object locally; this command never fetches it')
    keys = set()
    for name in SECTIONS:
        for node in walk(parse((SURVEY / 'sections' / (name + '.html')).read_text())):
            if node.tag == 'cite':
                keys.update(node.attrs['data-keys'].split())
    reviewed = json.loads(FROZEN_BIBLIOGRAPHY.read_bytes())
    omitted = {entry['record']['id'] for entry in reviewed.get('records', []) if entry['record'].get('authors_omitted') is True}
    entries = []
    for record in map(json.loads, data.splitlines()):
        if record['kind'] in {'paper', 'survey'} and citation_key(record) in keys:
            if record['id'] in omitted:
                # Keep the catalog's sorted key order, so authors_omitted follows authors.
                record = dict(sorted(omit_authors(record).items()))
            entries.append({'citation_key': citation_key(record), 'record_sha256': record_sha256(record), 'record': record})
    entries.sort(key=lambda item: item['citation_key'])
    fixture = {'schema_version': 1, 'source_commit': PIN, 'catalog_git_path': 'data/catalog.jsonl', 'catalog_sha256': CATALOG_SHA, 'record_hash_method': RECORD_HASH_METHOD, 'selection': 'Original paper/survey records from the pinned catalog whose stable citation keys occur in this manuscript. Fresh-search citations and extra references are separate inputs.', 'record_count': len(entries), 'records': entries}
    encoded = (json.dumps(fixture, ensure_ascii=False, indent=2) + '\n').encode()
    if digest(encoded) != FROZEN_BIBLIOGRAPHY_SHA:
        raise ValueError('Re-export changes the reviewed fixture; inspect the selection and update its pin only after review')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encoded)
    return fixture


def script_json(value):
    return json_text(value).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)


class Fragment(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs)))

    def handle_endtag(self, tag):
        if len(self.stack) == 1 or self.stack[-1].tag != tag:
            raise ValueError('Unbalanced source HTML at </' + tag + '>')
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def finish(self):
        if len(self.stack) != 1:
            raise ValueError('Unclosed source HTML: ' + self.stack[-1].tag)
        return self.root


def parse(fragment):
    p = Fragment()
    p.feed(fragment)
    return p.finish()


def walk(node):
    if isinstance(node, Node):
        yield node
        for child in node.children:
            yield from walk(child)


def text_content(node):
    if isinstance(node, str):
        return node
    return ''.join(text_content(child) for child in node.children)


def render(node):
    if isinstance(node, str):
        return html.escape(node, quote=False)
    content = ''.join(render(child) for child in node.children)
    if not node.tag:
        return content
    attrs = ''.join(' ' + key + ('' if value is None else '="' + html.escape(str(value), quote=True) + '"') for key, value in node.attrs.items())
    if node.tag in VOID:
        return '<' + node.tag + attrs + '>'
    return '<' + node.tag + attrs + '>' + content + '</' + node.tag + '>'


def public_evidence(value, key=''):
    """Keep claim receipts while excluding copyrighted bodies and private locations."""
    if isinstance(value, dict):
        forbidden = {'citation_abstract', 'abstract', 'full_abstract', 'raw_body', 'fulltext', 'raw_response', 'response', 'cache_file', 'local_body', 'body_path', 'retained_body', 'retained_local_body', 'reused_from', 'receipt_file', 'text_path', 'raw_response_retained_in_cache', 'raw_search_response', 'reading_text_path', 'error_body_path'}
        return {k: public_evidence(v, k) for k, v in value.items() if k not in forbidden}
    if isinstance(value, list):
        return [public_evidence(v, key) for v in value]
    if isinstance(value, str):
        if key == 'skill' and 'paper-writing-review' in value:
            return 'paper-writing-review'
        if value.startswith(('/Users/', '/home/', '.cache/')):
            return 'Retained in private review cache; see source URL and fingerprint.'
    return value


def arxiv_record(row):
    aid = row['id'].split(':', 1)[1]
    match = re.fullmatch(r'https://arxiv\.org/abs/' + re.escape(aid) + r'v([1-9]\d*)', row['versioned_url'])
    if not match:
        raise ValueError('Fresh bibliography has no exact version: ' + aid)
    return {
        'id': row['id'], 'kind': 'paper', 'name': row['title'],
        # An omitted author list stays empty even if the retained search row still names authors.
        'authors': [] if row.get('authors_omitted') is True else row['authors'],
        **({'authors_omitted': True} if row.get('authors_omitted') is True else {}),
        'review_status': 'metadata_verified', 'url': 'https://arxiv.org/abs/' + aid,
        'published_at': row['published'][:10], 'updated_at': row['updated'][:10],
        'identifiers': {'arxiv': aid},
        'details': {'arxiv_snapshot': {'version': int(match.group(1)), 'versioned_url': row['versioned_url'], 'submitted_at': row['published'], 'updated_at': row['updated'], 'abstract_sha256': row['abstract_sha256'], 'abstract_hash_method': 'sha256-utf8-whitespace-collapsed-v1'}}
    }


def extra_citation(extra):
    """Use the canonical formatter for bibliographic records; handle dataset separately."""
    key = extra['key']
    parts = extra.get('date_parts', [extra['year']])
    if extra['type'] == 'dataset':
        item = {'id': extra['canonical_id'], 'citation-key': key, 'type': 'dataset', 'title': extra['title'], 'author': [{'literal': x} for x in extra['authors']], 'issued': {'date-parts': [parts]}, 'URL': extra['url'], 'version': extra['version'], 'custom': {'source_commit': extra['source_commit'], 'catalog_sha256': extra['catalog_sha256'], 'bibliography_authority': extra['metadata_origin']}}
        fields = {'title': '{' + extra['title'] + '}', 'author': ' and '.join('{' + x + '}' for x in extra['authors']), 'year': str(parts[0]), 'url': extra['url'], 'note': 'Versioned catalog snapshot ' + extra['version'] + '; source commit ' + extra['source_commit'] + '.'}
        bib = '@misc{' + key + ',\n' + ',\n'.join('  ' + k + ' = {' + (v if k in {'title', 'author'} else tex_escape(v)) + '}' for k, v in fields.items()) + '\n}\n'
        return item, bib
    record = {'id': extra['canonical_id'], 'kind': 'paper', 'name': extra['title'], 'authors': extra['authors'], 'review_status': 'metadata_verified', 'url': extra['url'], 'published_at': None, 'updated_at': None, 'identifiers': {}, 'details': {}}
    if record['id'].startswith('arxiv:'):
        aid = record['id'].split(':')[1]
        record['identifiers']['arxiv'] = aid
        record['published_at'] = '-'.join([str(parts[0]), f'{parts[1]:02d}', f'{parts[2]:02d}'])
        record['updated_at'] = extra['version_date']
        record['details']['arxiv_snapshot'] = {'version': extra['version'], 'versioned_url': extra['url']}
    else:
        record['identifiers']['doi'] = extra['doi']
        record['details']['publication'] = {'type': 'journal-article', 'title': extra['title'], 'authors': extra['authors'], 'date_parts': parts, 'url': extra['url'], 'doi': extra['doi'], 'venue': extra['venue'], 'volume': extra.get('volume')}
    item = citation_csl(record)
    bib = citation_bibtex(record)
    original_key = item['citation-key']
    item['citation-key'] = key
    bib = bib.replace('{' + original_key + ',', '{' + key + ',', 1)
    item.setdefault('custom', {})['bibliography_authority'] = extra['metadata_origin']
    if extra.get('article_number'):
        item['article-number'] = extra['article_number']
        bib = bib.replace('\n}', ',\n  eid = {' + tex_escape(extra['article_number']) + '}\n}', 1)
    return item, bib


def collect_readings(ledgers):
    records = {}

    def add(key, rid, level, sections, sources, chapter, pages=None):
        row = records.setdefault(key, {'citation_key': key, 'canonical_id': rid, 'readings': []})
        if row['canonical_id'] != rid:
            raise ValueError('Conflicting canonical identity for ' + key)
        row['readings'].append({'chapter': chapter, 'read_level': level, 'sections': sections, 'pdf_pages': pages or [], 'primary_sources': sources})

    context = ledgers['context']
    receipts = {r['receipt_key']: r for r in context['retained_sources']}
    for r in context['records']:
        sources = []
        for receipt_key in r['source_receipt_keys']:
            receipt = receipts.get(receipt_key)
            if receipt and receipt.get('ok') and receipt.get('status') == 200:
                sources.append({'url': safe_url(receipt['url']), 'sha256': receipt['sha256'], 'retrieved_at': receipt.get('retrieved_at'), 'read_sections': receipt.get('read_sections', [])})
        add(r['citation_key'], r['canonical_id'], r['read_status'], r['sections'], sources, 'context')
    for r in ledgers['methods']['sources']:
        add(r['citation_key'], r['resource_id'], 'selected_fulltext_sections_read', r['read_evidence']['sections'], [{'url': safe_url(r['primary_url']), 'sha256': r['body_sha256'], 'retrieved_at': r['retrieved_at'], 'version': r['version_read']}], 'methods', r['read_evidence']['pages'])
    for r in ledgers['evaluation']['records']:
        p = r['primary_source']
        add(r['citation_key'], r['canonical_id'], r['read_status'], r['sections'], [{'url': safe_url(p['url']), 'sha256': p['sha256'], 'retrieved_at': p['retrieved_at'], 'version': r['arxiv_version_read']}], 'evaluation', r.get('pdf_pages_read'))
    extra_keys = {r['canonical_id']: r['key'] for r in ledgers['extra-references']}
    for r in ledgers['root']['records']:
        rid = r['canonical_id']
        key = extra_keys.get(rid) or rid.replace(':', '_').replace('.', '_')
        p = r['primary_receipt']
        add(key, rid, r['read_status'], r['sections'], [{'url': safe_url(p['url']), 'sha256': p['sha256'], 'retrieved_at': p['retrieved_at_utc']}], 'review design, human agency and research assets')
    release = next(r for r in ledgers['extra-references'] if r['key'] == 'awesomecua2026')
    add(release['key'], release['canonical_id'], 'dataset_snapshot_integrity_inspection', ['Frozen catalog records, versioned release artifacts, source-record relationships and descriptive counts'], [{'url': release['url'], 'catalog_sha256': release['catalog_sha256'], 'source_commit': PIN}], 'review design and research assets')
    return records


def verify_read_bibliography(key, item, ledgers):
    """Do not silently swap a ledger's title or ordered authors at assembly."""
    for chapter, collection in [('context', 'records'), ('methods', 'sources'), ('evaluation', 'records')]:
        for source in ledgers[chapter][collection]:
            if source['citation_key'] != key:
                continue
            authors = source.get('ordered_authors', source.get('authors'))
            if source.get('title') != item['title']:
                raise ValueError('Reading/citation title conflict: ' + chapter + '/' + key)
            if (source.get('authors_omitted') is True) != (item.get('custom', {}).get('authors_omitted') is True):
                raise ValueError('Reading/citation author-omission conflict: ' + chapter + '/' + key)
            if authors != [a['literal'] for a in item.get('author', [])]:
                raise ValueError('Reading/citation ordered-author conflict: ' + chapter + '/' + key)


def verify_read_edition(key, csl, row):
    version = csl.get('version')
    if not row['canonical_id'].startswith('arxiv:'):
        return
    aid = row['canonical_id'].split(':')[1]
    if not version or csl['URL'] != f'https://arxiv.org/abs/{aid}v{version}':
        raise ValueError('Citation lacks pinned read edition: ' + key)
    for reading in row['readings']:
        for source in reading['primary_sources']:
            url = source['url']
            m = re.search(r'arxiv\.org/(?:abs|html|pdf)/' + re.escape(aid) + r'v(\d+)', url)
            if m and m.group(1) != version:
                raise ValueError('Citation/read version conflict: ' + key)
            if source.get('version') is not None and str(source['version']) != version:
                raise ValueError('Explicit read version conflict: ' + key)


def sanitize_svg(path):
    root = ET.fromstring(path.read_bytes())
    svg_ns = 'http://www.w3.org/2000/svg'
    ET.register_namespace('', svg_ns)
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
    allowed = {'svg', 'g', 'defs', 'style', 'path', 'rect', 'line', 'polyline', 'polygon', 'circle', 'ellipse', 'text', 'tspan', 'title', 'desc', 'clipPath', 'use'}
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.rsplit('}', 1)[-1] == 'metadata':
                parent.remove(child)
    ids = {n.attrib['id']: 'corpus-' + n.attrib['id'] for n in root.iter() if 'id' in n.attrib}
    for node in root.iter():
        tag = node.tag.rsplit('}', 1)[-1]
        if tag not in allowed:
            raise ValueError('Unexpected owned SVG element: ' + tag)
        if tag == 'style' and re.search(r'@import|url\((?!#)', node.text or '', re.I):
            raise ValueError('External SVG style resource')
        for attr, value in list(node.attrib.items()):
            local = attr.rsplit('}', 1)[-1]
            if local.lower().startswith('on'):
                raise ValueError('SVG event handler')
            if local == 'href' and not value.startswith('#'):
                raise ValueError('External SVG reference')
            if local == 'id':
                node.set(attr, ids[value])
            elif local == 'href':
                node.set(attr, '#' + ids[value[1:]])
            else:
                node.set(attr, re.sub(r'url\(#([^)]*)\)', lambda m: 'url(#' + ids[m.group(1)] + ')', value))
    root.set('role', 'img')
    root.set('aria-label', 'Descriptive year and topic distributions of the frozen reviewed-paper inventory.')
    return ET.tostring(root, encoding='unicode')


def decorate_body(tree, citation_numbers):
    headings, tables = [], []
    used_ids = {n.attrs['id'] for n in walk(tree) if 'id' in n.attrs}
    occurrence = 0
    for node in walk(tree):
        if node.tag in {'h2', 'h3'}:
            if not node.attrs.get('id'):
                stem = re.sub(r'[^a-z0-9]+', '-', text_content(node).lower()).strip('-')
                candidate = stem
                i = 2
                while candidate in used_ids:
                    candidate = stem + '-' + str(i)
                    i += 1
                node.attrs['id'] = candidate
                used_ids.add(candidate)
            headings.append((int(node.tag[1]), node.attrs['id'], ' '.join(text_content(node).split())))
        if node.tag == 'table':
            captions = [n for n in node.children if isinstance(n, Node) and n.tag == 'caption']
            if len(captions) != 1 or not node.attrs.get('id'):
                raise ValueError('Every comparison table needs a stable ID and one caption')
            caption = captions[0]
            raw = re.sub(r'^\s*Table\s+\d+[.:]?\s*', '', text_content(caption), flags=re.I)
            number = len(tables) + 1
            caption.children = [Node('strong', {}, [f'Table {number}. ']), raw]
            tables.append({'id': node.attrs['id'], 'number': number, 'caption': raw})
        if node.tag == 'cite':
            keys = node.attrs.pop('data-keys').split()
            occurrence += 1
            node.attrs['class'] = 'citation-group'
            node.attrs['id'] = 'citation-' + str(occurrence)
            node.children = ['[']
            for i, key in enumerate(keys):
                if i:
                    node.children.append(', ')
                node.children.append(Node('a', {'href': '#ref-' + key, 'aria-label': 'Reference ' + str(citation_numbers[key])}, [str(citation_numbers[key])]))
            node.children.append(']')
    return headings, tables, occurrence


def make_toc(headings):
    out, opened = ['<ol>'], False
    for level, target, text in headings:
        if level == 2:
            if opened:
                out.append('</ol></li>')
            out.append('<li><a href="#' + html.escape(target) + '">' + html.escape(text) + '</a><ol>')
            opened = True
        elif opened:
            out.append('<li><a href="#' + html.escape(target) + '">' + html.escape(text) + '</a></li>')
    if opened:
        out.append('</ol></li>')
    out.append('</ol>')
    return ''.join(out)


def date_string(item):
    parts = item.get('issued', {}).get('date-parts', [[]])[0]
    return '-'.join(str(x) if i == 0 else f'{x:02d}' for i, x in enumerate(parts)) if parts else 'Date not recorded'


def reference_html(items):
    out = ['<ol>']
    for number, item in enumerate(items, 1):
        key = item['citation-key']
        authors = [a.get('literal', '') for a in item.get('author', [])]
        out.append(f'<li id="ref-{html.escape(key)}" value="{number}"><a class="reference-title" href="{html.escape(safe_url(item["URL"]), quote=True)}">{html.escape(item["title"])}</a>')
        if item.get('custom', {}).get('authors_omitted') is True:
            out.append(f'<p><a href="{html.escape(safe_url(item["URL"]), quote=True)}">{html.escape(AUTHORS_OMITTED[0])}</a></p>')
        elif len(authors) > 8:
            out.append('<p>' + html.escape(', '.join(authors[:3])) + ', and colleagues.</p><details><summary>Complete author list (' + str(len(authors)) + ')</summary><p>' + html.escape('; '.join(authors)) + '</p></details>')
        elif authors:
            out.append('<p>' + html.escape('; '.join(authors)) + '.</p>')
        info = [date_string(item)]
        if item.get('archive') == 'arXiv':
            info.append('arXiv:' + item['archive_location'] + 'v' + item['version'])
            update = item.get('custom', {}).get('arxiv_snapshot', {}).get('updated_at') or item.get('custom', {}).get('record_updated_at')
            if update:
                info.append('version updated ' + update[:10])
        elif item.get('container-title'):
            info.append(item['container-title'])
        elif item.get('version'):
            info.append('version ' + item['version'])
        if item.get('DOI'):
            info.append('DOI ' + item['DOI'])
        out.append('<p class="reference-meta">' + html.escape(' · '.join(info)) + ' · <a href="#reading-' + html.escape(key) + '">Read basis</a></p></li>')
    out.append('</ol>')
    return ''.join(out)


def evidence_html(reading_index, search, screening):
    counts = reading_index['counts']
    out = [f'<p>The cited set contains <strong>{counts["fulltext_section_read_works"]} works read in selected full-text sections</strong>, one source used at abstract/project-page level, and one versioned catalog dataset. These counts deduplicate works across chapters. They do not mean that every page or reported experiment was audited.</p>',
           '<p>Bibliographic baseline: <a href="https://github.com/reacher-z/Awesome-CUA/tree/' + PIN + '"><code>' + PIN + '</code></a>. The frozen catalog SHA-256 is <code>' + CATALOG_SHA + '</code>. Later production-catalog changes are outside this manuscript snapshot.</p>',
           '<p>Download the <a href="evidence/reading-index.json">compact reading index</a>, <a href="evidence/title-search.json">complete title-search ledger</a>, <a href="evidence/supplementary-screening.json">supplementary screening decisions</a>, and <a href="evidence/corpus-statistics.json">inventory analysis</a>. Chapter ledgers: <a href="evidence/context.json">context</a>, <a href="evidence/methods.json">methods</a>, <a href="evidence/evaluation.json">evaluation</a>, and <a href="evidence/root.json">review design and human agency</a>.</p>',
           '<details><summary>Exact supplementary query and screening boundary</summary><p>Platform: ' + html.escape(search['platform']) + '. Started ' + html.escape(search['started_at_utc']) + '; completed ' + html.escape(search['completed_at_utc']) + '. Cutoff: ' + html.escape(search['cutoff_utc']) + '.</p><pre><code>' + html.escape(search['query']) + '</code></pre>',
           f'<p>{len(search["pages"])} pages returned {search["unique_returned"]:,} unique identifiers, matching the service-reported query total of {search["reported_total"]:,}. The {screening["titles_inspected"]} absent-inventory titles received title screening; {screening["complete_abstracts_read"]} received complete abstract screening and {screening["advanced"]} advanced for further reading. Those populations overlap and do not measure recall for the whole field. Targeted searches are recorded in the individual chapter ledgers.</p></details>',
           '<h3 id="reading-register">Source-by-source reading register</h3><p>Open a source to inspect the actual sections and response fingerprints. The edition column identifies the citation used here; primary-source links retain the reading authority. Raw source documents are not redistributed in this artifact.</p><div class="table-scroll"><table id="reading-register-table"><caption>Reading level and inspected sections for every cited source. Repeated readings of one work are grouped in one row.</caption><thead><tr><th scope="col">Source</th><th scope="col">Edition and read level</th><th scope="col">Sections and evidence</th></tr></thead><tbody>']
    labels = {'selected_fulltext_sections_read': 'Selected full-text sections', 'abstract_and_author_project_only': 'Abstract and author project only', 'dataset_snapshot_integrity_inspection': 'Dataset snapshot inspection'}
    for r in reading_index['records']:
        key = r['citation_key']
        out.append('<tr id="reading-' + html.escape(key) + '"><th scope="row"><a href="#ref-' + html.escape(key) + '">[' + str(r['reference_number']) + '] ' + html.escape(r['title']) + '</a></th><td>' + html.escape(r['edition_label']) + '<br>' + labels[r['read_level']] + '</td><td><details><summary>Sections and source receipts</summary>')
        for reading in r['readings']:
            out.append('<p><strong>' + html.escape(reading['chapter']) + ':</strong> ' + html.escape('; '.join(reading['sections'])) + '</p>')
            if reading['pdf_pages']:
                out.append('<p>PDF pages: ' + html.escape(', '.join(map(str, reading['pdf_pages']))) + '.</p>')
            for source in reading['primary_sources']:
                out.append('<p><a href="' + html.escape(safe_url(source['url']), quote=True) + '">Primary source</a>')
                if source.get('retrieved_at'):
                    out.append(' · retrieved ' + html.escape(source['retrieved_at']))
                fingerprint = source.get('sha256') or source.get('catalog_sha256')
                if fingerprint:
                    out.append('<br>SHA-256: <code>' + fingerprint + '</code>')
                out.append('</p>')
        out.append('</details></td></tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)


class DocumentAudit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.tags = [], [], []
        self.errors = []
        self.in_script = False
        self.details = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in VOID:
            self.tags.append(tag)
        if 'id' in a:
            self.ids.append(a['id'])
        if 'href' in a:
            self.links.append(a['href'])
        if tag == 'script' and 'src' in a:
            self.errors.append('External script')
        if tag == 'details':
            self.details.append(a)

    def handle_startendtag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if 'href' in a:
            self.links.append(a['href'])

    def handle_endtag(self, tag):
        if not self.tags or self.tags[-1] != tag:
            self.errors.append('Unbalanced ' + tag)
        else:
            self.tags.pop()


def build(output, *, check_history=True, write_source_outputs=False):
    frozen, frozen_verification = load_frozen_bibliography(check_history=check_history)
    by_key = {citation_key(r): r for r in frozen if r['kind'] in {'paper', 'survey'}}
    ledgers = {name: load(name) for name in EVIDENCE}
    if ledgers['corpus-statistics']['catalog_sha256'] != CATALOG_SHA:
        raise ValueError('Figure statistics use another catalog')
    for row in ledgers['title-search']['records']:
        key = row['id'].replace(':', '_').replace('.', '_')
        if key not in by_key:
            by_key[key] = arxiv_record(row)
    extras = {r['key']: r for r in ledgers['extra-references']}
    raw_body = '\n\n'.join((SURVEY / 'sections' / (name + '.html')).read_text() for name in SECTIONS)
    tree = parse(raw_body)
    keys = []
    for n in walk(tree):
        if n.tag == 'cite':
            for key in n.attrs['data-keys'].split():
                if key not in keys:
                    keys.append(key)
    numbers = {key: i + 1 for i, key in enumerate(keys)}
    readings = collect_readings(ledgers)
    citations, bibs, register, fresh_count = [], [], [], 0
    for key in keys:
        if key not in readings:
            raise ValueError('Cited source has no reading record: ' + key)
        if key in extras:
            item, bib = extra_citation(extras[key])
        elif key in by_key:
            record = by_key[key]
            item, bib = citation_csl(record), citation_bibtex(record)
            if record['id'] not in {r['id'] for r in frozen}:
                fresh_count += 1
                item['custom']['manuscript_bibliography_basis'] = 'Fresh official arXiv title-search metadata; no production catalog approval implied.'
        else:
            raise ValueError('No bibliographic authority for ' + key)
        if item['citation-key'] != key:
            raise ValueError('Citation key changed: ' + key)
        verify_read_bibliography(key, item, ledgers)
        reading = copy.deepcopy(readings[key])
        verify_read_edition(key, item, reading)
        levels = {r['read_level'] for r in reading['readings']}
        level = 'selected_fulltext_sections_read' if 'selected_fulltext_sections_read' in levels else reading['readings'][0]['read_level']
        if level not in {'selected_fulltext_sections_read', 'abstract_and_author_project_only', 'dataset_snapshot_integrity_inspection'}:
            raise ValueError('Unsupported reading level for cited source: ' + key)
        if item.get('custom', {}).get('authors_omitted') is True:
            reading['authors_omitted'] = True
        reading.update(reference_number=numbers[key], title=item['title'], ordered_authors=[a['literal'] for a in item.get('author', [])], citation_url=item['URL'], read_level=level, edition_label=('arXiv v' + str(item['version']) + '; first submitted ' + date_string(item)) if item.get('archive') == 'arXiv' else (item.get('version') or date_string(item)))
        item.setdefault('custom', {})['manuscript_read_level'] = level
        citations.append(item)
        bibs.append(bib)
        register.append(reading)
    fulltext = sum(r['read_level'] == 'selected_fulltext_sections_read' for r in register)
    counts = {'unique_cited_works': len(keys), 'fulltext_section_read_works': fulltext, 'abstract_and_project_only_works': sum(r['read_level'] == 'abstract_and_author_project_only' for r in register), 'dataset_snapshots': sum(r['read_level'] == 'dataset_snapshot_integrity_inspection' for r in register), 'fresh_arxiv_bibliography_additions': fresh_count}
    if counts != {'unique_cited_works': 89, 'fulltext_section_read_works': 87, 'abstract_and_project_only_works': 1, 'dataset_snapshots': 1, 'fresh_arxiv_bibliography_additions': 14}:
        raise ValueError('Reading population changed; inspect before release: ' + str(counts))
    index = {'schema_version': 1, 'article_title': TITLE, 'working_manuscript_date': '2026-10-18', 'source_commit': PIN, 'catalog_sha256': CATALOG_SHA, 'counts': counts, 'read_boundary': 'Selected sections, not entire-document audits or independently reproduced experiments. Works are deduplicated by retained canonical identity.', 'records': register}
    headings, tables, occurrences = decorate_body(tree, numbers)
    body = render(tree)
    svg = sanitize_svg(SURVEY / 'figures/corpus.svg')
    marker = '<div data-figure="corpus"></div>'
    if body.count(marker) != 1:
        raise ValueError('Expected one corpus figure slot')
    body = body.replace(marker, '<div data-figure="corpus">' + svg + '</div><p class="figure-scroll-hint">Scroll horizontally to view both panels.</p>')
    body_word_count = len(re.findall(r"\b[\w’'-]+\b", text_content(tree)))
    abstract = ('Computer-use agents translate human goals into actions across browsers, desktop applications, and mobile interfaces. '
                'Their progress is difficult to compare because systems differ in what they observe, how they act, what experience they learn from, and how completion is judged. '
                'This survey organizes the field around four questions: how interface choices constrain agent design; what demonstrations, synthetic trajectories, and reinforcement learning teach; which capabilities evaluation protocols establish; and how research assets can remain reusable by people and software agents. '
                'We connect historical interface automation with visual grounding, modular and native policies, memory, verification, recovery, and runtime systems. '
                'Comparisons retain the distinction between local action prediction, interactive task completion, safety, and acceptable assistance to a person. '
                f'The evidence base combines selected full-text sections from {fulltext} unique works with a pinned inventory of 1,123 editorially reviewed papers and surveys, supplemented by a reproducible title search and bounded abstract screening. '
                'Inventory review is not full-paper review, and no cited experiment is independently reproduced here. '
                'We provide an inspectable reading register and versioned bibliography, and identify opportunities for clearer generalization tests, evaluator validation, human control, and maintenance of connected research artifacts.')
    appendix = evidence_html(index, ledgers['title-search'], ledgers['supplementary-screening'])
    # The appendix table follows the body tables and shares global numbering.
    appendix_tree = parse(appendix)
    for n in walk(appendix_tree):
        if n.tag == 'caption':
            n.children.insert(0, Node('strong', {}, [f'Table {len(tables) + 1}. ']))
    appendix = render(appendix_tree)
    tables.append({'id': 'reading-register-table', 'number': len(tables) + 1, 'caption': 'Reading level and inspected sections for every cited source.'})
    structured = {'@context': 'https://schema.org', '@type': 'ScholarlyArticle', 'headline': TITLE, 'description': abstract, 'inLanguage': 'en', 'dateCreated': '2026-10-18', 'creativeWorkStatus': 'Working manuscript; not peer reviewed', 'publisher': {'@type': 'Organization', 'name': 'AwesomeCUA', 'url': 'https://awesomecua.github.io/'}, 'url': CANONICAL, 'isAccessibleForFree': True, 'citation': [{'@type': 'CreativeWork', 'name': item['title'], 'url': item['URL']} for item in citations]}
    structured.pop('@context')
    structured = {'@context': 'https://schema.org', '@graph': [structured, {
        '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'AwesomeCUA', 'item': 'https://awesomecua.github.io/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Research survey', 'item': CANONICAL},
        ]
    }]}
    values = {'TITLE': html.escape(TITLE), 'ABSTRACT': '<p>' + html.escape(abstract) + '</p>', 'BODY': body, 'TOC': make_toc(headings), 'REFERENCE_COUNT': str(len(keys)), 'FULLTEXT_COUNT': str(fulltext), 'READING_MINUTES': str(math.ceil((body_word_count + len(abstract.split())) / 220)), 'REFERENCES': reference_html(citations), 'EVIDENCE_SUMMARY': appendix, 'STRUCTURED_DATA': script_json(structured), 'BIB_DATA': script_json(citations), 'CSS': (SURVEY / 'article.css').read_text(), 'JS': (SURVEY / 'article.js').read_text()}
    template = (SURVEY / 'template.html').read_text()
    placeholders = set(re.findall(r'\{\{([A-Z_]+)\}\}', template))
    if placeholders != set(values):
        raise ValueError('Template placeholder contract changed')
    article = re.sub(r'\{\{([A-Z_]+)\}\}', lambda m: values[m.group(1)], template)
    article = article.replace('<meta name="color-scheme" content="light">', '<meta name="color-scheme" content="light">\n  <link rel="canonical" href="' + CANONICAL + '">')
    if 'data-keys=' in article or '.cache/' in article or '/Users/' in article or '{{' in article:
        raise ValueError('Unresolved citation, template, or private path in final HTML')
    audit = DocumentAudit()
    audit.feed(article)
    if audit.errors or audit.tags or len(audit.ids) != len(set(audit.ids)):
        raise ValueError('HTML document validation failed: ' + str(audit.errors or audit.tags or 'duplicate IDs'))
    missing = sorted({unquote(url[1:]) for url in audit.links if url.startswith('#')} - set(audit.ids))
    if missing:
        raise ValueError('Broken internal anchors: ' + str(missing))
    toc = next(x for x in audit.details if x.get('id') == 'article-contents')
    if 'open' in toc:
        raise ValueError('Mobile contents must be closed in static markup')
    csl_bytes = (json.dumps(citations, ensure_ascii=False, indent=2) + '\n').encode()
    bib_bytes = ('% AwesomeCUA survey bibliography. Working manuscript dated 2026-10-18.\n% Edition-specific citations; bibliographic exports do not imply independent reproduction.\n\n' + '\n'.join(bibs)).encode()
    if len(re.findall(r'^@\w+\{', bib_bytes.decode(), re.M)) != len(keys):
        raise ValueError('BibTeX entry count mismatch')
    if len({item['id'] for item in citations}) != len(keys):
        raise ValueError('Duplicate citation identity')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'evidence').mkdir(exist_ok=True)
    for name, data in [('index.html', article.encode()), ('references.bib', bib_bytes), ('references.json', csl_bytes)]:
        if write_source_outputs:
            (SURVEY / name).write_bytes(data)
        (output / name).write_bytes(data)
    index_bytes = (json_text(index) + '\n').encode()
    if write_source_outputs:
        (SURVEY / 'evidence/reading-index.json').write_bytes(index_bytes)
    (output / 'evidence/reading-index.json').write_bytes(index_bytes)
    for name, ledger in ledgers.items():
        clean = public_evidence(ledger)
        encoded = (json_text(clean) + '\n').encode()
        if b'/Users/' in encoded or b'.cache/' in encoded:
            raise ValueError('Private source path escaped sanitization: ' + name)
        (output / 'evidence' / (name + '.json')).write_bytes(encoded)
    readme = ('# AwesomeCUA research survey\n\nOpen `index.html` in a browser. It is a complete English working manuscript with embedded CSS, JavaScript, and the original inventory figure. No external runtime dependency is required.\n\n`references.bib` and `references.json` preserve the source editions used. `evidence/reading-index.json` lists every cited source and actual read level. The other JSON ledgers document the search, bounded screening, original claim notes, and inventory analysis. Raw papers, full abstracts, model weights, and training data are not included.\n\nThe research inventory is pinned to source commit ' + PIN + ' and catalog SHA-256 ' + CATALOG_SHA + '. The generated survey is a working manuscript, not a claim of independent experiment reproduction or peer-reviewed publication. Its intended public location is ' + CANONICAL + '; this build does not publish it.\n')
    (output / 'README.md').write_text(readme)
    expected_files = {'index.html', 'references.bib', 'references.json', 'README.md', 'evidence/reading-index.json'} | {'evidence/' + name + '.json' for name in EVIDENCE}
    for url in audit.links:
        if not url or url in {'/', '/survey/'} or url.startswith(('#', 'https://', 'http://', 'mailto:')):
            continue
        path = unquote(url.split('#', 1)[0])
        if path not in expected_files or not (output / path).is_file():
            raise ValueError('Broken artifact-relative link: ' + url)
    manifest = {'schema_version': 1, 'artifact': 'English working-manuscript survey', 'working_manuscript_date': '2026-10-18', 'source_commit_for_inventory': PIN, 'catalog_sha256': CATALOG_SHA, 'canonical_location_intended': CANONICAL, 'publication_performed': False, 'counts': counts, 'body_word_count': body_word_count, 'estimated_reading_minutes': int(values['READING_MINUTES']), 'citation_occurrences': occurrences, 'tables': tables, 'toc_headings': len(headings), 'checks': {'all_citation_keys_resolved': True, 'all_citations_have_read_basis': True, 'all_read_versions_match_citations': True, 'all_read_titles_and_ordered_authors_match_citations': True, 'all_internal_anchors_resolve': True, 'all_relative_downloads_exist': True, 'mobile_contents_default_collapsed': True, 'external_runtime_dependencies': 0, 'raw_source_documents_redistributed': False}, 'input_sha256': {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in [SURVEY / 'sections' / (name + '.html') for name in SECTIONS] + [SURVEY / 'evidence' / (name + '.json') for name in EVIDENCE] + [Path(__file__).resolve(), SURVEY / 'article.css', SURVEY / 'article.js', SURVEY / 'template.html', SURVEY / 'figures/corpus.svg', ROOT / 'scripts/export_citations.py', ROOT / 'scripts/publication_metadata.py']}, 'files': [{'path': name, 'bytes': (output / name).stat().st_size, 'sha256': digest((output / name).read_bytes())} for name in sorted(expected_files)]}
    manifest['frozen_bibliography_verification'] = frozen_verification
    manifest['input_sha256'][str(FROZEN_BIBLIOGRAPHY.relative_to(ROOT))] = FROZEN_BIBLIOGRAPHY_SHA
    (output / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: manifest[k] for k in ['counts', 'body_word_count', 'estimated_reading_minutes', 'citation_occurrences', 'toc_headings', 'checks']}, indent=2))
    print('Article: ' + str(output / 'index.html'))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'output/survey')
    parser.add_argument('--no-history-check', action='store_true', help='Use only the fingerprint-verified committed fixture; do not inspect Git history')
    source_mode = parser.add_mutually_exclusive_group()
    source_mode.add_argument('--update-source', action='store_true', help='Also update generated research/survey index, references and reading index; omitted by default')
    source_mode.add_argument('--output-only', action='store_true', help='Explicitly select the default: write only the destination artifact')
    parser.add_argument('--export-frozen-bibliography', type=Path, metavar='PATH', help='Re-export the pinned fixture from an already-local historical Git object, then exit')
    args = parser.parse_args()
    if args.export_frozen_bibliography:
        fixture = export_frozen_bibliography(args.export_frozen_bibliography)
        print(json.dumps({'record_count': fixture['record_count'], 'fixture_sha256': FROZEN_BIBLIOGRAPHY_SHA, 'source_commit': PIN}, indent=2))
        return
    build(args.output.resolve(), check_history=not args.no_history_check, write_source_outputs=args.update_source)


if __name__ == '__main__':
    main()
