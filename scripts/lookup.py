"""Read an exact catalog ID and its reviewed relations without search or network access."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from repository_identity import repository_aliases
from url_identity import url_aliases

DATA = Path(__file__).resolve().parents[1] / 'data'
EXCLUSION_LEDGER_URL = 'https://awesomecua.github.io/downloads/exclusions.json'
EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_EXCLUDED = 3  # argparse reserves 2 for invalid command-line usage.
EXIT_DATA_ERROR = 4
REVIEWED_RELATION_TYPES = frozenset({
    'introduced_by', 'published_by', 'component_of', 'uses', 'evaluates',
    'trained_on', 'variant_of', 'documented_by',
})


def related_resources(resource_id, records):
    """Return directed, source-backed edges; metadata owners and mentions are excluded."""
    result, seen = [], set()
    for owner in records.values():
        if owner.get('review_status') != 'curated':
            continue
        relations = owner.get('relations', [])
        if not isinstance(relations, list) or any(not isinstance(r, dict) for r in relations):
            raise ValueError('Reviewed relations must be a list of objects: ' + owner['id'])
        for relation in relations:
            if relation.get('type') not in REVIEWED_RELATION_TYPES:
                continue
            source_id, target_id = owner['id'], relation.get('target_id')
            if source_id == resource_id:
                direction, other_id = 'outgoing', target_id
            elif target_id == resource_id:
                direction, other_id = 'incoming', source_id
            else:
                continue
            if target_id not in records:
                raise ValueError('A reviewed relation targets an inactive resource: ' + str(target_id))
            evidence_url = relation.get('evidence_url')
            receipts = owner.get('evidence', [])
            if not isinstance(receipts, list) or any(not isinstance(e, dict) for e in receipts):
                raise ValueError('Primary evidence receipts must be a list of objects: ' + source_id)
            evidence = [e for e in receipts
                        if e.get('role') == 'primary' and e.get('url') == evidence_url and 'relations' in e.get('supports', [])]
            if not evidence_url or not evidence:
                raise ValueError('A reviewed relation lacks its retained primary receipt scoped to relations: ' + source_id)
            key = (direction, relation['type'], source_id, target_id, evidence_url)
            if key in seen:
                continue
            seen.add(key)
            result.append({
                'direction': direction, 'type': relation['type'],
                'source_id': source_id, 'target_id': target_id,
                'evidence_url': evidence_url, 'evidence': copy.deepcopy(evidence),
                'resource': copy.deepcopy(records[other_id]),
            })
    return sorted(result, key=lambda r: (
        r['direction'] != 'outgoing', r['type'], r['source_id'], r['target_id'], r['evidence_url']))


def lookup(resource_id, records, decisions=(), *, related=False, aliases=None):
    """Return (JSON-compatible payload, exit code), preserving active records verbatim."""
    by_id = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get('id'), str):
            raise ValueError('Catalog records require a string ID')
        if record['id'] in by_id:
            raise ValueError('Duplicate catalog resource ID: ' + record['id'])
        by_id[record['id']] = record
    if aliases and resource_id in aliases:
        target = aliases[resource_id]
        if resource_id in by_id or target not in by_id or target in aliases:
            raise ValueError('Repository alias must resolve directly to its sole active owner')
        resource_id = target
    matches = [d for d in decisions if d.get('id') == resource_id and d.get('status') == 'excluded']
    if len(matches) > 1:
        raise ValueError('Duplicate applied exclusion for resource ID: ' + resource_id)
    if resource_id in by_id:
        if matches:
            raise ValueError('Resource is both active and scope-excluded: ' + resource_id)
        record = copy.deepcopy(by_id[resource_id])
        if related:
            return {'status': 'active', 'record': record,
                    'related': related_resources(resource_id, by_id)}, EXIT_OK
        return record, EXIT_OK
    if matches:
        decision = matches[0]
        return {'status': 'excluded', 'id': resource_id,
                'reason': decision['reason'], 'ledger_url': EXCLUSION_LEDGER_URL,
                'decision': copy.deepcopy(decision)}, EXIT_EXCLUDED
    return {'status': 'not_found', 'id': resource_id,
            'message': 'No active resource or applied scope exclusion has this exact ID.'}, EXIT_NOT_FOUND


def read_lookup(resource_id, *, related=False, data_dir=None):
    """Read only the active materialization and applied exclusion ledger, never raw archives."""
    directory = Path(data_dir) if data_dir is not None else DATA
    records = [json.loads(line) for line in (directory / 'catalog.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    ledger = json.loads((directory / 'exclusion-status.json').read_text(encoding='utf-8'))
    if not isinstance(ledger, dict) or ledger.get('schema_version') != 1 or not isinstance(ledger.get('decisions'), list):
        raise ValueError('Missing or unsupported applied exclusion ledger')
    if any(not isinstance(d, dict) or not isinstance(d.get('id'), str) for d in ledger['decisions']):
        raise ValueError('Scope decisions require a string ID')
    alias_path = directory / 'repository-aliases.json'
    declarations = json.loads(alias_path.read_text(encoding='utf-8')) if alias_path.exists() else []
    aliases = repository_aliases(declarations, records)
    url_path = directory / 'url-aliases.json'
    url_declarations = json.loads(url_path.read_text(encoding='utf-8')) if url_path.exists() else []
    from catalog import canonical
    active = {row['id'] for row in records}
    for former, target in url_aliases(url_declarations, canonical, records).items():
        if target not in active:
            continue  # An unreviewed candidate never becomes an active lookup.
        if former in aliases and aliases[former] != target:
            raise ValueError('Conflicting former resource ID: ' + former)
        aliases[former] = target
    return lookup(resource_id, records, ledger['decisions'], related=related,
                  aliases=aliases)


def get_resource(args):
    """CLI adapter: successful --json is the original record, unless --related is requested."""
    try:
        payload, code = read_lookup(args.resource_id, related=args.related)
    except (OSError, ValueError, KeyError, TypeError) as error:
        payload = {'status': 'data_error', 'id': args.resource_id, 'message': str(error)}
        code = EXIT_DATA_ERROR
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif code != EXIT_OK:
        # Quote user-provided IDs/messages rather than interpreting terminal control characters.
        print(payload['status'] + ': ' + json.dumps(payload['id'], ensure_ascii=False))
        print(json.dumps(payload.get('reason', payload.get('message')), ensure_ascii=False))
        if payload.get('ledger_url'):
            print('Scope ledger: ' + payload['ledger_url'])
    else:
        record = payload['record'] if args.related else payload
        print(record['id'] + ' | ' + record['name'])
        print('Review: ' + record['review_status'] + ' | Scope: ' + record['scope'])
        print('Primary source: ' + record['url'])
        if record.get('summary'):
            print(record['summary'])
        if args.related:
            print('Reviewed relations: ' + str(len(payload['related'])))
            for edge in payload['related']:
                print(f"{edge['direction']}: {edge['source_id']} --{edge['type']}--> {edge['target_id']}")
                print('Evidence: ' + edge['evidence_url'])
    return code
