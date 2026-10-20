#!/usr/bin/env python3
"""Package a pinned, data-only snapshot from validated public site exports (stdlib only)."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import sys
import tempfile
import zipfile

from data_hub import build_download_manifest, UNITS, SCOPE_LABELS
from build import validate_records, validate_sources, uncurated_linked_papers
from catalog import publication_identity
from publication_metadata import attach_publications, publication_aliases, alias_owner_errors
from scope_review import resolve_exclusions, scope_report
from specifications import profile_export
from export_citations import encode_citations
from topic_pages import reviewed_topics, topic_counts

ROOT = Path(__file__).resolve().parents[1]
ZIP_NAME = 'awesomecua-data.zip'
MANIFEST_NAME = 'release-manifest.json'
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
RELEASE_ASSETS = {'catalog.jsonl', 'coverage.json', 'catalog.json', 'catalog.sqlite', 'topics.json',
                  'benchmarks-profiles.json', 'datasets-profiles.json', ZIP_NAME, MANIFEST_NAME}
RAG_FILES = {'rag-documents.jsonl': False, 'rag-all-records.jsonl': True}
CITATION_FILES = {
    'citations.bib': ('bibtex', False, 'record'),
    'citations.csl.json': ('csl-json', False, 'record'),
    'citations-all.bib': ('bibtex', True, 'record'),
    'citations-all.csl.json': ('csl-json', True, 'record'),
    'publication-citations.bib': ('bibtex', False, 'publication'),
    'publication-citations.csl.json': ('csl-json', False, 'publication'),
}


def digest(body):
    return hashlib.sha256(body).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def public_path(value, *, nested=False):
    """Translate an exact public path to a safe relative ZIP/member path."""
    if not isinstance(value, str) or not value.startswith('/') or value.startswith('//'):
        raise ValueError('Expected one root-relative public export path')
    relative = value[1:]
    parts = relative.split('/')
    if (any(not part or part.startswith('.') or not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*', part) for part in parts)
            or str(PurePosixPath(relative)) != relative):
        raise ValueError('Unsafe export path: ' + value)
    if not nested and (len(parts) != 2 or parts[0] not in {'downloads', 'data', 'schemas'}):
        raise ValueError('Unsupported main artifact path: ' + value)
    if nested and (len(parts) != 4 or parts[:2] != ['downloads', 'topics']):
        raise ValueError('Unsupported topic export path: ' + value)
    return relative


def read_file(root, relative):
    """Reject symlinks in every component, not only at the final filename."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Input root must be a real directory: ' + str(root))
    current = root
    for part in relative.split('/'):
        if not part or part.startswith('.') or part in {'.', '..'}:
            raise ValueError('Unsafe input component: ' + relative)
        current = current / part
        if current.is_symlink():
            raise ValueError('Symlink input is not allowed: ' + relative)
    if not current.resolve().is_relative_to(root.resolve()) or not stat.S_ISREG(current.stat().st_mode):
        raise ValueError('Input must be a regular file within its root: ' + relative)
    return current.read_bytes()


def verify_fingerprint(body, entry, label, *, require_size=True):
    if not isinstance(entry.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', entry['sha256']):
        raise ValueError('Missing or invalid SHA-256: ' + label)
    if digest(body) != entry['sha256']:
        raise ValueError('SHA-256 mismatch: ' + label)
    if require_size and (type(entry.get('bytes')) is not int or entry['bytes'] != len(body)):
        raise ValueError('Byte-size mismatch: ' + label)


def require_count(value, label):
    if type(value) is not int or value < 0:
        raise ValueError('Count must be a nonnegative integer: ' + label)


def unique_entries(entries, key, label):
    if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
        raise ValueError('Expected entry list: ' + label)
    result = {}
    for item in entries:
        identity = item.get(key)
        if not isinstance(identity, str) or identity in result:
            raise ValueError('Missing or duplicate identity: ' + label)
        result[identity] = item
    return result


def validated_payloads(site, *, repo_root=ROOT):
    """Read bytes once, validate provenance/content in an isolated copy, return the snapshot."""
    raw_manifest = read_file(site, 'downloads/manifest.json')
    manifest = parse_json(raw_manifest)
    if type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1:
        raise ValueError('Unsupported download manifest version')
    entries = unique_entries(manifest['artifacts'], 'path', 'download artifacts')
    if len({item.get('id') for item in entries.values()}) != len(entries):
        raise ValueError('Duplicate download artifact ID')
    payloads = {'downloads/manifest.json': raw_manifest}
    annotations = {}
    for path, entry in entries.items():
        relative = public_path(path)
        count = entry.get('count')
        if not isinstance(count, dict) or set(count) != {'value', 'unit'} or count['unit'] not in UNITS or entry.get('scope') not in SCOPE_LABELS:
            raise ValueError('Invalid count unit or scope: ' + path)
        require_count(count['value'], path)
        if relative in payloads:
            raise ValueError('Download manifest cannot include itself')
        body = read_file(site, relative)
        verify_fingerprint(body, entry, path)
        payloads[relative] = body
        annotations[relative] = {'count': entry['count'], 'scope': entry['scope'], 'artifact_id': entry['id']}
    for required in ['downloads/catalog.jsonl', 'data/records.json', 'downloads/catalog.sqlite',
                     'downloads/rag-manifest.json', 'downloads/citations-manifest.json', 'downloads/topics.json']:
        if required not in payloads:
            raise ValueError('Missing required main artifact: ' + required)
    catalog_bytes = payloads['downloads/catalog.jsonl']
    if digest(catalog_bytes) != manifest['catalog_sha256']:
        raise ValueError('Catalog fingerprint differs from the download manifest')
    rows = [parse_json(line) for line in catalog_bytes.splitlines() if line.strip()]
    rag = parse_json(payloads['downloads/rag-manifest.json'])
    citations = parse_json(payloads['downloads/citations-manifest.json'])
    topics = parse_json(payloads['downloads/topics.json'])
    if any(type(m.get('schema_version')) is not int or m['schema_version'] != 1 for m in (rag, citations, topics)):
        raise ValueError('Unsupported nested manifest version')
    if any(m.get('catalog_sha256') != digest(catalog_bytes) for m in (rag, citations, topics)):
        raise ValueError('Catalog/RAG/citation/topic snapshots differ')
    rag_entries = unique_entries(rag['exports'], 'file', 'RAG exports')
    citation_entries = unique_entries(citations['exports'], 'file', 'citation exports')
    if set(rag_entries) != set(RAG_FILES) or set(citation_entries) != set(CITATION_FILES):
        raise ValueError('Incomplete or unexpected RAG/citation export set')
    for name, metadata in RAG_FILES.items():
        entry = rag_entries[name]
        require_count(entry.get('records'), name)
        if type(entry['includes_metadata_only']) is not bool or entry['includes_metadata_only'] != metadata:
            raise ValueError('Wrong RAG selection: ' + name)
        verify_fingerprint(payloads['downloads/' + name], entry, name, require_size=False)
    for name, (format_, metadata, edition) in CITATION_FILES.items():
        entry = citation_entries[name]
        require_count(entry.get('records'), name)
        if (entry['format'], entry['includes_metadata_only'], entry['edition']) != (format_, metadata, edition) or type(entry['includes_metadata_only']) is not bool:
            raise ValueError('Wrong citation selection: ' + name)
        verify_fingerprint(payloads['downloads/' + name], entry, name)
    grouped = reviewed_topics(rows)
    topic_entries = unique_entries(topics['topics'], 'id', 'topics')
    if set(topic_entries) != set(grouped):
        raise ValueError('Topic inventory differs from reviewed source tags')
    covered = {r['id'] for members in grouped.values() for r in members}
    reviewed = sum(r['review_status'] == 'curated' and r['scope'] in {'core', 'adjacent'} for r in rows)
    for key in ['reviewed_resources', 'resources_with_topics', 'reviewed_resources_without_topics']:
        require_count(topics.get(key), key)
    if (topics['reviewed_resources'], topics['resources_with_topics'], topics['reviewed_resources_without_topics']) != (reviewed, len(covered), reviewed-len(covered)):
        raise ValueError('Topic coverage counts differ from source records')
    for topic, members in grouped.items():
        item = topic_entries[topic]
        for key, value in item['counts'].items():
            require_count(value, topic + ':' + key)
        if item['resource_ids'] != [r['id'] for r in members] or item['counts'] != topic_counts(members):
            raise ValueError('Topic membership/count mismatch: ' + topic)
        expected = {
            'records.jsonl': (''.join(json.dumps(r, ensure_ascii=False, sort_keys=True)+'\n' for r in members).encode(), len(members), 'resources'),
            'citations.bib': (encode_citations(members), sum(r['kind'] in {'paper','survey'} for r in members), 'citations'),
            'citations.csl.json': (encode_citations(members, format='csl-json'), sum(r['kind'] in {'paper','survey'} for r in members), 'citations'),
        }
        exports = unique_entries(item['exports'], 'url', 'topic ' + topic)
        wanted = {'/downloads/topics/' + topic + '/' + name for name in expected}
        if set(exports) != wanted:
            raise ValueError('Missing or unexpected topic export: ' + topic)
        for url, entry in exports.items():
            relative = public_path(url, nested=True)
            body = read_file(site, relative)
            verify_fingerprint(body, entry, url)
            expected_body, count, unit = expected[relative.rsplit('/', 1)[1]]
            if body != expected_body or type(entry['records']) is not int or entry['records'] != count:
                raise ValueError('Topic export content/selection mismatch: ' + url)
            if relative in payloads:
                raise ValueError('Duplicate bundle path: ' + relative)
            payloads[relative] = body
            annotations[relative] = {'count': {'value': count, 'unit': unit}, 'scope': 'reviewed', 'topic': topic}
    validate_provenance(payloads, rows, repo_root)
    # Reuse the strong catalog/SQLite/RAG/citation checks without rewriting the input manifest.
    with tempfile.TemporaryDirectory(prefix='awesomecua-release-validation-') as temporary:
        stage = Path(temporary)
        for name, body in payloads.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        regenerated = build_download_manifest(stage, rows, catalog_bytes)
        if regenerated != manifest:
            raise ValueError('Download manifest differs from recomputed files, counts or policies')
    return payloads, annotations, manifest, rows


def parse_json(body):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON object key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Non-JSON numeric constant: ' + value)
    return json.loads(body, object_pairs_hook=pairs, parse_constant=invalid)


def record_lines(payload, label):
    rows = [parse_json(line) for line in payload.splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError('Expected JSON record objects: ' + label)
    return rows


def same_json(actual, expected, label):
    # JSON encoding distinguishes true from 1, unlike Python's dictionary equality.
    if json_bytes(actual) != json_bytes(expected):
        raise ValueError('Content differs from the source contract: ' + label)


def validate_provenance(payloads, rows, repo_root):
    """Check bundled evidence structures; never claim to re-verify absent network bodies."""
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError('Catalog requires resource objects')
    if errors := validate_records(rows):
        raise ValueError('Catalog contract: ' + '; '.join(errors[:8]))
    by_id = {row['id']: row for row in rows}
    for relative, body in payloads.items():
        if relative.startswith('schemas/'):
            trusted = read_file(repo_root, relative)
            parse_json(body)
            if body != trusted:
                raise ValueError('Schema differs from this trusted source checkout: ' + relative)
    archive = record_lines(payloads['downloads/arxiv-archive.jsonl'], 'arXiv archive')
    if any(not row.get('id', '').startswith('arxiv:') or row.get('review_status') != 'metadata_verified'
           or row.get('kind') != 'paper' or 'publication' in row.get('details', {}) for row in archive):
        raise ValueError('arXiv archive contains a non-archive record')
    normalized = [{**row, 'scope': row.get('scope', 'relevance_pending')} for row in archive]
    if errors := validate_records(normalized):
        raise ValueError('arXiv archive contract: ' + '; '.join(errors[:8]))
    archived = {row['id']: row for row in normalized}
    ledger = parse_json(payloads['downloads/exclusions.json'])
    if not isinstance(ledger, dict) or type(ledger.get('schema_version')) is not int or ledger['schema_version'] != 1:
        raise ValueError('Invalid scope ledger version')
    decisions = ledger['decisions']
    unique_entries(decisions, 'id', 'scope decisions')
    fields = {'id','name','url','decision','basis','reason','reviewed_at','metadata_fingerprint','evidence'}
    if any(set(d) != fields | {'status','status_reason'} or d['status'] not in {'excluded','revalidation_pending'}
           or not isinstance(d['evidence'],dict) or set(d['evidence']) != {'url','sha256','retrieved_at'} for d in decisions):
        raise ValueError('Malformed scope decision contract')
    # A pending decision can depend on an update proposal outside the bundle. Preserve it
    # conservatively; applied exclusions must match the included retained archive exactly.
    pending = {d['id'] for d in decisions if d['status']=='revalidation_pending'}
    resolved = resolve_exclusions({**archived, **by_id}, [{k:d[k] for k in fields} for d in decisions], pending)
    same_json(ledger, scope_report(resolved), 'scope ledger')
    excluded = {d['id'] for d in resolved if d['status']=='excluded'}
    if {rid for rid in by_id if rid.startswith('arxiv:')} != set(archived)-excluded:
        raise ValueError('Active arXiv records differ from archive minus applied exclusions')
    for rid in set(by_id) & set(archived):
        original, active = archived[rid], by_id[rid]
        for field in ['id','name','url','authors','published_at','updated_at','identifiers']:
            same_json(active[field], original[field], 'retained arXiv '+rid+' '+field)
        same_json(active['details'].get('arxiv_snapshot'), original['details'].get('arxiv_snapshot'), 'arXiv snapshot '+rid)
        if any(receipt not in active['evidence'] for receipt in original['evidence']):
            raise ValueError('Original archive receipt missing from active record: '+rid)
    publications = record_lines(payloads['downloads/publications.jsonl'], 'publication observations')
    attached = attach_publications(archived, publications, publication_identity)
    if errors := validate_records(list(attached.values())):
        raise ValueError('Publication observation contract: ' + '; '.join(errors[:8]))
    observed_ids = {item['id'] for item in publications}
    if {rid for rid,row in by_id.items() if row['details'].get('publication')} != observed_ids-excluded:
        raise ValueError('Publication inventory differs from active publication metadata')
    for observation in publications:
        rid = observation['id']
        if rid not in by_id:
            if rid not in excluded:
                raise ValueError('Publication observation lacks a retained owner: '+rid)
            continue
        same_json(by_id[rid]['details']['publication'], observation['publication'], 'publication facts '+rid)
        if any(receipt not in by_id[rid]['evidence'] for receipt in observation['evidence']):
            raise ValueError('Publication evidence missing from active owner: '+rid)
    if errors := alias_owner_errors(rows, publication_aliases(publications, publication_identity), publication_identity):
        raise ValueError('Publication aliases: ' + '; '.join(errors[:8]))
    sources = parse_json(payloads['downloads/sources.json'])
    unique_entries(sources, 'id', 'source registry')
    if errors := validate_sources(sources):
        raise ValueError('Source registry contract: ' + '; '.join(errors[:8]))
    for kind, name in [('benchmark','benchmarks'),('dataset','datasets')]:
        profile = parse_json(payloads['downloads/'+name+'-profiles.json'])
        same_json(profile, profile_export(rows, kind), name+' profiles')
    edges = [{'source_id':r['id'],'source_name':r['name'],'source_kind':r['kind'],**rel}
             for r in rows if r['review_status']=='curated' and r['scope'] in {'core','adjacent'} for rel in r['relations']]
    relationships = parse_json(payloads['downloads/relationships.json'])
    same_json(relationships, {'relation_count':len(edges),
                             'semantics':'Reviewed semantic links only. Documentation does not establish training or evaluation dependency.',
                             'relations':edges}, 'reviewed relationships')
    coverage = parse_json(payloads['downloads/coverage.json'])
    expected = {'as_of_utc':max((e['retrieved_at'] for r in rows for e in r['evidence']),default=''),
        'total_records':len(rows), 'curated_records':sum(r['review_status']=='curated' for r in rows),
        'metadata_only_records':sum(r['review_status']=='metadata_verified' for r in rows),
        'bibliographic_records':sum(r['kind'] in {'paper','survey'} for r in rows),
        'arxiv_active_records':sum(r['kind'] in {'paper','survey'} and r['id'].startswith('arxiv:') for r in rows),
        'non_arxiv_bibliographic_records':sum(r['kind'] in {'paper','survey'} and not r['id'].startswith('arxiv:') for r in rows),
        'publication_metadata_records':sum(bool(r['details'].get('publication')) for r in rows),
        'arxiv_archive_records':len(archive),'excluded_records':len(excluded),'exclusion_revalidation_pending':len(pending),
        'by_kind':dict(sorted(Counter(r['kind'] for r in rows).items())),
        'curated_by_environment':dict(sorted(Counter(e for r in rows if r['review_status']=='curated' for e in r['environments']).items())),
        'curated_by_kind_and_environment':{kind:dict(sorted(Counter(e for r in rows if r['review_status']=='curated' and r['kind']==kind for e in set(r['environments'])).items()))
                                           for kind in sorted({r['kind'] for r in rows if r['review_status']=='curated'})},
        'license_declarations_by_scope':{slot:sum(r['licenses'][slot] is not None for r in rows) for slot in ['code','data','weights','document']},
        'uncurated_linked_papers':uncurated_linked_papers(rows)}
    if not isinstance(coverage,dict):
        raise ValueError('Coverage must be a JSON object')
    for key, value in expected.items():
        same_json(coverage.get(key), value, 'coverage '+key)


def check_destination(destination):
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError('Release output directory cannot be a symlink')
    if destination.exists():
        for file in destination.iterdir():
            if file.name not in RELEASE_ASSETS | {'SHA256SUMS'} or file.is_symlink() or not file.is_file():
                raise ValueError('Unexpected or unsafe release asset: '+file.name)
        pair = [(destination/name).exists() for name in [ZIP_NAME,MANIFEST_NAME]]
        if any(pair) and not all(pair):
            raise ValueError('Previous release has an incomplete ZIP/manifest pair')
        if all(pair):
            old = parse_json((destination/MANIFEST_NAME).read_bytes())
            verify_fingerprint((destination/ZIP_NAME).read_bytes(), old['zip'], 'previous release ZIP')


def publish_pair(stage, destination):
    """Roll back replacements that raise; this does not claim crash-atomic two-file I/O."""
    previous = {name:(destination/name).read_bytes() if (destination/name).exists() else None
                for name in [ZIP_NAME,MANIFEST_NAME]}
    changed = []
    try:
        for name in [ZIP_NAME,MANIFEST_NAME]:
            os.replace(stage/name, destination/name)
            changed.append(name)
    except BaseException:
        for name in reversed(changed):
            if previous[name] is None:
                (destination/name).unlink(missing_ok=True)
            else:
                restore = stage/('restore-'+name)
                restore.write_bytes(previous[name])
                os.replace(restore, destination/name)
        raise


def guidance(source_commit, source_ref):
    return f'''# AwesomeCUA pinned data snapshot

Source commit: {source_commit}
Source ref: {source_ref}

Read `downloads/manifest.json` for each export's scope, count unit and SHA-256.
`downloads/catalog.jsonl` contains every active record; `data/records.json` is the
same data as an array, and `downloads/catalog.sqlite` supports local SQL queries.
`downloads/rag-documents.jsonl` contains reviewed retrieval documents;
`downloads/rag-all-records.jsonl` also preserves metadata-only review states.
Paper citations and publication editions are separate exports in `downloads/`.
`downloads/topics.json` lists full-record and citation subsets under
`downloads/topics/<topic>/`; memberships overlap and their counts must not be added.
Keep stable IDs, review states, evidence, scoped licenses and record fingerprints.
Optional GitHub candidate observations have their own snapshot and input
fingerprints. They remain candidate/relevance_pending, may overlap the active
catalog, and are not included in its normal recommendation or RAG populations.

This ZIP contains data and guidance, not repository scripts. For CLI search or
custom exports, clone the source and select this exact commit:

```sh
git clone https://github.com/reacher-z/Awesome-CUA.git
cd Awesome-CUA
git checkout --detach {source_commit}
```

The source checkout's AGENTS.md explains its commands. To read this bundle directly,
standard Python can iterate JSON objects from `downloads/catalog.jsonl`.
The accompanying `release-manifest.json` records every ZIP member and the ZIP hash;
`SHA256SUMS` covers the downloadable release assets. Ref names label releases;
the recorded source commit and content hashes identify this snapshot.
Linked PDFs, models, training samples and applications are not included. LICENSE
covers original repository code/annotations, not third-party materials.
'''


def package_release(site, destination, *, source_commit, source_ref, repo_root=ROOT):
    if not isinstance(source_commit, str) or not re.fullmatch('[0-9a-f]{40}', source_commit):
        raise ValueError('A full 40-character source Git SHA is required')
    if not isinstance(source_ref, str) or not re.fullmatch(r'refs/(?:heads/[^\s\x00-\x1f\x7f]+|tags/v[^\s\x00-\x1f\x7f]+)', source_ref):
        raise ValueError('Source ref must be a branch preview or a v* tag')
    destination = Path(destination)
    check_destination(destination)
    payloads, annotations, download, rows = validated_payloads(Path(site), repo_root=repo_root)
    source = {'commit': source_commit, 'ref': source_ref,
              'kind': 'tag' if source_ref.startswith('refs/tags/') else 'branch-preview',
              'repository': download['source_repository'], 'catalog_sha256': download['catalog_sha256']}
    payloads['LICENSE'] = read_file(Path(repo_root), 'LICENSE')
    payloads['README.md'] = guidance(source_commit, source_ref).encode()
    payloads['AGENTS.md'] = ('''# Agent instructions for this data bundle

Use the existing exports under downloads/ and data/; this bundle has no scripts/.
Read README.md and downloads/manifest.json before choosing a corpus. Preserve
review_status, source receipts, scoped licenses, aliases and record_sha256.
Use curated records for reviewed recommendations; metadata_verified is bibliography
awaiting relevance review. Topic subsets overlap. Raw arXiv archive records include
scope exclusions and are not the active corpus. Optional GitHub candidate
observations remain candidate/relevance_pending in a separate population with
their own observation fingerprint; do not add their counts to the active catalog.
For source CLI tools, clone and
checkout the exact commit in data/build-info.json; follow that checkout's AGENTS.md.
''').encode()
    payloads['data/build-info.json'] = json_bytes({'artifact_kind': 'offline-data-release', 'source_commit':source_commit,
                                                 'source_ref':source_ref, 'catalog_sha256':download['catalog_sha256']})
    entries = [{'path': name, 'bytes': len(body), 'sha256': digest(body), **annotations.get(name, {})}
               for name, body in sorted(payloads.items())]
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError('Release output directory cannot be a symlink')
    destination.mkdir(parents=True, exist_ok=True)
    for name in (ZIP_NAME, MANIFEST_NAME):
        if (destination / name).is_symlink():
            raise ValueError('Release output cannot replace a symlink: ' + name)
    with tempfile.TemporaryDirectory(prefix='.awesomecua-package-', dir=destination) as temporary:
        stage = Path(temporary)
        archive = stage / ZIP_NAME
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
            for name, body in sorted(payloads.items()):
                info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                zipped.writestr(info, body, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        zip_body = archive.read_bytes()
        release = {'schema_version':1, 'source_commit':source_commit, 'source_ref':source_ref,
                   'source_ref_type':source['kind'], 'source_repository':source['repository'], 'catalog_sha256':download['catalog_sha256'],
                   'count_policy':download['count_policy'],
                   'population_counts':{'active':{'value':len(rows), 'unit':'resources', 'scope':'active'},
                                        'reviewed':{'value':sum(r['review_status']=='curated' for r in rows), 'unit':'resources', 'scope':'reviewed'},
                                        'by_kind':{kind:{'value':count, 'unit':'resources', 'scope':'active'}
                                                   for kind,count in sorted(Counter(r['kind'] for r in rows).items())}},
                   'files':entries, 'zip':{'file':ZIP_NAME, 'bytes':len(zip_body), 'sha256':digest(zip_body), 'members':len(entries),
                                         'compression':'deflate-9', 'entry_timestamp':'1980-01-01T00:00:00'},
                   'validation_boundary':'Checks cover bundled syntax, contracts, identity links and catalog-derived exports/counts. Optional sanitized GitHub candidate observations are a separate, unreviewed population with independent observation/input fingerprints. External raw network bodies and the full scan state are not included or re-fetched; historical receipt claims are preserved, not independently proven by this bundle. The trusted workflow checkout/build establishes source_commit authenticity; a 40-hex string alone does not.',
                   'fingerprint_policy':'File hashes cover exact uncompressed bytes. This external manifest is not inside the ZIP, avoiding a circular ZIP hash.'}
        (stage / MANIFEST_NAME).write_bytes(json_bytes(release))
        publish_pair(stage, destination)
    return release


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT / 'dist/site')
    parser.add_argument('--output', type=Path, default=ROOT / 'release/assets')
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--source-ref', required=True)
    args = parser.parse_args(argv)
    try:
        manifest = package_release(args.site, args.output, source_commit=args.source_commit, source_ref=args.source_ref)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        parser.exit(1, 'Data release package rejected: ' + str(error) + '\n')
    print(json.dumps({'zip':str(args.output / ZIP_NAME), 'manifest':str(args.output / MANIFEST_NAME),
                      'files':len(manifest['files']), 'catalog_sha256':manifest['catalog_sha256']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
