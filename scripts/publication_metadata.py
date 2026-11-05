"""Publisher bibliography facts and precision-preserving dates, using only stdlib."""
from datetime import date, datetime
import copy
import re
from urllib.parse import urlsplit

PUBLICATION_TYPES = frozenset({'conference-paper', 'journal-article', 'report', 'other'})
DOI_PATTERN = re.compile(r'10\.\d{4,9}/\S+', re.I)
PUBLICATION_TEXT = ('venue', 'publisher', 'series', 'volume', 'issue', 'pages', 'date_basis', 'event_dates', 'identity_basis', 'notes')
PUBLICATION_FIELDS = {'type', 'title', 'authors', 'date_parts', 'url', 'pdf_url', 'evidence_urls', 'doi', *PUBLICATION_TEXT}
# Shown wherever a record with authors_omitted would list names: English and Chinese.
AUTHORS_OMITTED = ('Authors: see the paper', '作者见原文')


def authors_omitted(record):
    """Whether the catalog lists no authors for this record; readers consult its linked source."""
    return isinstance(record, dict) and record.get('authors_omitted') is True


def omit_authors(record):
    """Return a copy of a record that lists no authors, in either its own or its publication's author list."""
    record = copy.deepcopy(record)
    record['authors'] = []
    record['authors_omitted'] = True
    edition = publication(record)
    if edition is not None and 'authors' in edition:
        edition['authors'] = []
    return record


def checked_date_parts(parts):
    """Return only the supplied calendar components; never manufacture month/day."""
    if parts is None:
        return None
    if not isinstance(parts, list) or not 1 <= len(parts) <= 3 or any(type(v) is not int for v in parts):
        raise ValueError('publication date_parts must be null or one to three integer calendar components')
    year = parts[0]
    if not 1 <= year <= 9999:
        raise ValueError('publication year is outside the supported calendar')
    if len(parts) >= 2 and not 1 <= parts[1] <= 12:
        raise ValueError('invalid publication month')
    if len(parts) == 3:
        try:
            date(*parts)
        except ValueError as exc:
            raise ValueError('invalid publication calendar date') from exc
    return list(parts)


def format_date_parts(parts):
    parts = checked_date_parts(parts)
    return '-'.join([f'{parts[0]:04d}', *(f'{part:02d}' for part in parts[1:])]) if parts else ''


def publication(record):
    details = record.get('details') or {}
    if not isinstance(details, dict):
        raise ValueError('details must be an object')
    value = details.get('publication')
    if value is not None and not isinstance(value, dict):
        raise ValueError('publication must be an object')
    return value


def record_date_parts(record):
    """The retained record's date, separate from a linked publication's issue date.

    arXiv identities keep their original submission date. Publisher-only identities
    use their publication's supplied precision. Other resources keep published_at.
    """
    pub = publication(record)
    if pub is not None and not record.get('id', '').startswith('arxiv:'):
        return checked_date_parts(pub.get('date_parts'))
    value = record.get('published_at')
    if not value:
        return None
    parsed = date.fromisoformat(value)
    return [parsed.year, parsed.month, parsed.day]


def record_date_text(record):
    return format_date_parts(record_date_parts(record))


def record_year(record):
    parts = record_date_parts(record)
    return str(parts[0]) if parts else ''


def publication_search_text(record):
    pub = publication(record)
    if not pub:
        return ''
    values = [pub.get(key) for key in ('title', 'doi', 'venue', 'publisher', 'series', 'url', 'pdf_url')]
    if pub.get('doi'):
        values.append('https://doi.org/' + pub['doi'])
    values.extend(pub.get('authors') or [])
    return ' '.join(value for value in values if isinstance(value, str))


def publication_links(record):
    links = copy.deepcopy(record.get('links', []))
    pub = publication(record)
    if pub:
        for relation, key in [('publication', 'url'), ('publication_pdf', 'pdf_url')]:
            if pub.get(key) and not any(item.get('url') == pub[key] for item in links):
                links.append({'rel': relation, 'url': pub[key]})
    return links


def publication_aliases(observations, canonical):
    """Resolve only primary-reviewed publisher/PDF aliases, never fuzzy titles."""
    aliases = {}
    for item in observations:
        pub=item['publication']
        urls=[pub.get(field) for field in ('url','pdf_url')]
        if pub.get('doi'):urls.append('https://doi.org/'+pub['doi'])
        for url in urls:
            parsed = canonical(url or '')
            if not parsed:
                continue
            if parsed[2] == 'github':
                continue  # Repository folding cannot identify an individual paper file.
            alias, owner = parsed[0], item['id']
            if alias.startswith('arxiv:') and alias != owner:
                raise ValueError('Publisher source names an arXiv identity; attach it to ' + alias)
            if alias in aliases and aliases[alias] != owner:
                raise ValueError('Publication URL alias has conflicting owners: ' + alias)
            aliases[alias] = owner
    return aliases


def alias_owner_errors(rows, aliases, canonical):
    errors=[]
    for row in rows:
        url=row.get('url')
        parsed=canonical(url) if isinstance(url,str) else None
        owner=aliases.get(parsed[0]) if parsed else None
        if owner and owner!=row.get('id'):
            errors.append(f"{row.get('id')}: publication URL belongs to canonical resource {owner}")
    return errors


def attach_publications(records, observations, canonical):
    """Merge publisher facts without replacing retained arXiv bibliographic fields.

    An observation targets an existing archived arXiv ID, or seeds a publisher-only
    metadata record. Editorial relevance approval remains a separate operation.
    """
    records = copy.deepcopy(records)
    seen = set()
    doi_owners = {}
    for row in records.values():
        identifiers = row.get('identifiers')
        doi = identifiers.get('doi') if isinstance(identifiers,dict) else None
        if isinstance(doi, str):
            doi_owners[doi.casefold()] = row['id']
    for item in observations:
        if not isinstance(item, dict) or set(item) != {'id', 'publication', 'evidence', 'last_verified_at'}:
            raise ValueError('Publication observation requires id, publication, evidence and last_verified_at only')
        identity, pub = item['id'], item['publication']
        if not isinstance(identity, str) or identity in seen:
            raise ValueError('Duplicate or malformed publication observation ID')
        seen.add(identity)
        if not isinstance(pub, dict):
            raise ValueError('Publication observation needs a publication object')
        if not isinstance(pub.get('url'),str) or not isinstance(pub.get('title'),str) or not pub['title'].strip():
            raise ValueError('Publication observation needs a title and publisher URL')
        if not isinstance(pub.get('authors'),list) or not all(isinstance(name,str) and name.strip() for name in pub['authors']):
            raise ValueError('Publication observation authors must be complete literal strings')
        parts = checked_date_parts(pub.get('date_parts'))
        if not isinstance(item['evidence'], list) or not item['evidence'] or not all(isinstance(ev, dict) for ev in item['evidence']):
            raise ValueError('Publication observation needs primary evidence receipts')
        if not isinstance(item['last_verified_at'], str):
            raise ValueError('Publication observation needs its verification timestamp')
        try:
            if datetime.fromisoformat(item['last_verified_at'].replace('Z','+00:00')).tzinfo is None:
                raise ValueError
        except ValueError as exc:
            raise ValueError('Publication observation verification timestamp needs a timezone') from exc
        doi = pub.get('doi')
        if doi is not None:
            if not isinstance(doi, str) or not DOI_PATTERN.fullmatch(doi):
                raise ValueError('Publication DOI must be a bare DOI identifier')
            previous = doi_owners.get(doi.casefold())
            if previous and previous != identity:
                raise ValueError(f'Publication DOI is already represented by {previous}; do not create {identity}')
            doi_owners[doi.casefold()] = identity
        if identity.startswith('arxiv:'):
            if identity not in records:
                raise ValueError('Publication attachment targets an unretained arXiv identity: ' + identity)
            row = records[identity]
        else:
            parsed = canonical(pub.get('url') or '')
            if not parsed or parsed[0] != identity or not identity.startswith('url:'):
                raise ValueError('Publisher-only ID must match its canonical publisher landing URL')
            if identity in records:
                raise ValueError('Publisher input would replace an existing resource identity: ' + identity)
            row = {
                'id': identity, 'name': pub.get('title'), 'kind': 'paper', 'url': pub.get('url'),
                'aliases': [], 'environments': ['unspecified'], 'topics': [], 'scope': 'relevance_pending',
                'summary': None, 'review_status': 'metadata_verified',
                'published_at': format_date_parts(parts) if parts and len(parts) == 3 else None,
                'updated_at': None, 'authors': copy.deepcopy(pub.get('authors')),
                'identifiers': {'doi': doi} if doi else {},
                'links': [{'rel': 'primary', 'url': pub.get('url')}], 'relations': [],
                'licenses': {scope: None for scope in ('code', 'data', 'weights', 'document')},
                'evidence': [], 'last_verified_at': item['last_verified_at'],
                'notes': 'Bibliographic facts reviewed against retained publication sources; relevance awaits editorial review.',
                'details': {},
            }
            records[identity] = row
        row.setdefault('details', {})['publication'] = copy.deepcopy(pub)
        row['evidence'].extend(copy.deepcopy(ev) for ev in item['evidence'] if ev not in row['evidence'])
        row['links'] = publication_links(row)
        if errors := validate_publication(row):
            raise ValueError(identity + ': ' + '; '.join(errors))
    publication_aliases(observations, canonical)  # Also checks explicit arXiv/PDF alias collisions.
    return records


def validate_publication(record):
    errors = []
    try:
        pub = publication(record)
    except ValueError as exc:
        return [str(exc)]
    if pub is None:
        return errors
    if record.get('kind') not in {'paper', 'survey'}:
        errors.append('publication metadata is only supported for papers and surveys')
    if unknown := set(pub) - PUBLICATION_FIELDS:
        errors.append('publication has unknown fields ' + ', '.join(sorted(unknown)))
    if wrong := [key for key in PUBLICATION_TEXT if not isinstance(pub.get(key), (str, type(None)))]:
        errors.append('publication ' + ', '.join(wrong) + ' must be text or null')
    if not isinstance(pub.get('type'),str) or pub['type'] not in PUBLICATION_TYPES:
        errors.append('invalid publication type')
    for key in ('title', 'url'):
        if not isinstance(pub.get(key), str) or not pub[key].strip():
            errors.append('publication lacks ' + key)
    for key in ('url','pdf_url'):
        value=pub.get(key)
        if value is None and key=='pdf_url':continue
        try:
            parsed=urlsplit(value) if isinstance(value,str) else None
            if not parsed or parsed.scheme!='https' or not parsed.hostname or parsed.username is not None or parsed.password is not None:
                raise ValueError
        except ValueError:
            errors.append('publication '+key+' must be a public HTTPS URL')
    if not isinstance(pub.get('authors'), list) or not all(isinstance(v, str) and v.strip() for v in pub.get('authors', [])):
        errors.append('publication authors must be complete literal strings')
    try:
        if 'date_parts' not in pub:
            raise ValueError('publication requires date_parts, including null for unknown dates')
        parts = checked_date_parts(pub.get('date_parts'))
    except ValueError as exc:
        errors.append(str(exc))
        parts = None
    receipts = {}
    for item in record.get('evidence', []):
        if isinstance(item,dict) and isinstance(item.get('url'),str):receipts.setdefault(item['url'],[]).append(item)
    sources = pub.get('evidence_urls')
    if not isinstance(sources, list) or not sources or not all(isinstance(v, str) for v in sources):
        errors.append('publication lacks source evidence URLs')
    else:
        if len(set(sources)) != len(sources):
            errors.append('publication has duplicate source evidence URLs')
        for url in sources:
            candidates = receipts.get(url)
            if not candidates:
                errors.append('publication source lacks a retained receipt: ' + url)
            elif not any(scope == 'details.publication' or scope.startswith('details.publication.')
                         for receipt in candidates for scope in (receipt.get('supports') if isinstance(receipt.get('supports'),list) else []) if isinstance(scope, str)):
                errors.append('publication source does not support publication facts: ' + url)
    doi = pub.get('doi')
    if doi is not None and (not isinstance(doi, str) or not DOI_PATTERN.fullmatch(doi)):
        errors.append('publication DOI must be a bare DOI identifier')
    publication_checks = [receipt.get('retrieved_at') for url in sources if isinstance(url,str)
                          for receipt in receipts.get(url,[])] if isinstance(sources,list) else []
    publication_checks = [value for value in publication_checks if isinstance(value,str)]
    verified_at = max(publication_checks,default=record.get('last_verified_at') or '')
    if parts and verified_at:
        try:
            verified = date.fromisoformat(verified_at[:10])
            if tuple(parts) > (verified.year, verified.month, verified.day)[:len(parts)]:
                errors.append('publication date is after its verification date')
        except ValueError:
            pass  # The general resource validator reports an invalid receipt date.
    if not record.get('id', '').startswith('arxiv:'):
        if pub.get('title') != record.get('name'):
            errors.append('publisher-only record title differs from its publication title')
        if pub.get('authors') != record.get('authors'):
            errors.append('publisher-only record authors differ from its publication authors')
        expected_day = format_date_parts(parts) if parts and len(parts) == 3 else None
        if record.get('published_at') != expected_day:
            errors.append('published_at must match the known full publication date or remain null for partial dates')
        if record.get('identifiers', {}).get('doi') != doi:
            errors.append('publisher-only record DOI differs from its publication DOI')
    return errors


def duplicate_publication_errors(rows):
    """Prevent double-counting known DOI identities among reviewed papers.

    Discovery can retain unreviewed identities. Titles alone never merge records;
    a DOI collision needs an explicit identity review before a second approval.
    """
    seen, errors = {}, []
    for record in rows:
        if not isinstance(record.get('kind'),str) or record['kind'] not in {'paper', 'survey'} or record.get('review_status') != 'curated':
            continue
        try:
            pub = publication(record) or {}
        except ValueError:
            continue
        identifiers = record.get('identifiers')
        candidates = [pub.get('doi'), identifiers.get('doi') if isinstance(identifiers, dict) else None]
        for value in {v.casefold() for v in candidates if isinstance(v, str) and v}:
            previous = seen.get(value)
            if previous and previous != record.get('id'):
                errors.append(f"{record.get('id')}: reviewed DOI {value} is already represented by {previous}")
            seen[value] = record.get('id')
    return errors
