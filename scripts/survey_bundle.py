"""Validate and publish the reviewed survey bundle without rebuilding research or using Git/network."""
from html.parser import HTMLParser
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote, urljoin, urlsplit
from site_config import FORMER_SITES

PAGE = '/survey/'
MANIFEST = 'build-manifest.json'
ROOT_FILES = {'index.html', 'references.bib', 'references.json', 'README.md'}
REQUIRED_FILES = ROOT_FILES | {'evidence/reading-index.json'}
REQUIRED_INPUTS = frozenset(
    {'research/survey/sections/' + name + '.html' for name in
     ('context', 'review-design', 'methods', 'evaluation', 'human-agency', 'assets', 'agenda')}
    | {'research/survey/evidence/' + name + '.json' for name in
       ('context', 'methods', 'evaluation', 'root', 'corpus-statistics', 'title-search',
        'supplementary-screening', 'extra-references')}
    | {'research/survey/scripts/build_article.py', 'research/survey/article.css',
       'research/survey/article.js', 'research/survey/template.html',
       'research/survey/figures/corpus.svg', 'research/survey/fixtures/frozen-catalog-bibliography.json',
       'scripts/export_citations.py', 'scripts/publication_metadata.py'})


def digest(body):
    return hashlib.sha256(body).hexdigest()


def parse_json(body):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate survey JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Non-JSON numeric value in survey bundle: ' + value)
    return json.loads(body, object_pairs_hook=pairs, parse_constant=invalid)


def relative_path(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or str(PurePosixPath(value)) != value
            or any(not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*', part) for part in value.split('/'))):
        raise ValueError('Unsafe survey path: ' + repr(value))
    return value


def checked_path(root, relative):
    """Check every existing component before reading, writing or removing a file."""
    root = Path(root)
    relative_path(relative)
    if root.is_symlink() or root.exists() and not root.is_dir():
        raise ValueError('Unsafe survey root: ' + str(root))
    current = root
    parts = relative.split('/')
    for position, part in enumerate(parts):
        current = current / part
        if current.is_symlink():
            raise ValueError('Survey paths cannot contain symlinks: ' + str(current))
        if current.exists() and (not current.is_dir() if position < len(parts)-1 else not current.is_file()):
            raise ValueError('Unexpected survey path type: ' + str(current))
    if not current.resolve().is_relative_to(root.resolve()):
        raise ValueError('Survey path escapes its root: ' + relative)
    return current


def survey_locations(site_url):
    """The page on the current origin, or on a former origin until the reviewed bundle is rebuilt."""
    # A tuple compares by equality, so a malformed unhashable manifest value still fails as ValueError below.
    return tuple(origin.rstrip('/') + PAGE for origin in (site_url, *FORMER_SITES))


def file_entries(manifest, site_url):
    if (not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int
            or manifest['schema_version'] != 1
            or manifest.get('canonical_location_intended') not in survey_locations(site_url)
            or not re.fullmatch(r'[0-9a-f]{40}', str(manifest.get('source_commit_for_inventory', '')))
            or not re.fullmatch(r'[0-9a-f]{64}', str(manifest.get('catalog_sha256', '')))):
        raise ValueError('Invalid survey manifest identity or version')
    entries = manifest.get('files')
    if not isinstance(entries, list):
        raise ValueError('Survey manifest needs a file list')
    result = {}
    for item in entries:
        if not isinstance(item, dict) or set(item) != {'path', 'bytes', 'sha256'}:
            raise ValueError('Survey file entry needs path, bytes and sha256')
        name = relative_path(item['path'])
        if name not in ROOT_FILES and not re.fullmatch(r'evidence/[A-Za-z0-9_-][A-Za-z0-9_.-]*\.json', name):
            raise ValueError('Unapproved survey bundle file: ' + name)
        if name in result or type(item['bytes']) is not int or item['bytes'] < 0 or not re.fullmatch(r'[0-9a-f]{64}', str(item['sha256'])):
            raise ValueError('Duplicate or invalid survey file entry: ' + name)
        result[name] = item
    if not REQUIRED_FILES <= result.keys():
        raise ValueError('Survey bundle is missing required files')
    return result


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical = []
        self.robots = []
        self.headings = 0
        self.language = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html':
            self.language = attrs.get('lang')
        if tag == 'h1':
            self.headings += 1
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical.append(attrs.get('href'))
        if tag == 'meta' and attrs.get('name') == 'robots':
            self.robots.append(attrs.get('content', ''))
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])


def load_bundle(directory, *, source_root, site_url):
    """Read exact output bytes, checking their manifest and the current authored inputs."""
    directory = Path(directory)
    # The source/build directory may itself be real while a parent (web/ or dist/) is a symlink.
    checkout = Path(source_root).absolute()
    if directory.absolute().is_relative_to(checkout):
        relative = directory.absolute().relative_to(checkout).as_posix()
        checked_path(checkout, relative + '/' + MANIFEST)
    manifest_path = checked_path(directory, MANIFEST)
    raw_manifest = manifest_path.read_bytes()
    manifest = parse_json(raw_manifest)
    entries = file_entries(manifest, site_url)
    inputs = manifest.get('input_sha256')
    if not isinstance(inputs, dict) or set(inputs) != REQUIRED_INPUTS:
        raise ValueError('Survey manifest must fingerprint the complete supported source input set')
    for name, expected in inputs.items():
        relative_path(name)
        if not re.fullmatch(r'[0-9a-f]{64}', str(expected)):
            raise ValueError('Invalid survey source input SHA-256: ' + name)
        if digest(checked_path(source_root, name).read_bytes()) != expected:
            raise ValueError('Survey source input changed; rebuild and review the bundle: ' + name)
    payloads = {}
    for name, entry in entries.items():
        body = checked_path(directory, name).read_bytes()
        if len(body) != entry['bytes'] or digest(body) != entry['sha256']:
            raise ValueError('Survey file fingerprint mismatch: ' + name)
        if name.endswith('.json'):
            parse_json(body)
        payloads[name] = body
    metadata = PageMetadata()
    metadata.feed(payloads['index.html'].decode('utf-8'))
    robots = {part.strip().lower() for value in metadata.robots for part in value.split(',')}
    location = manifest['canonical_location_intended']
    if (metadata.canonical != [location] or metadata.headings != 1
            or metadata.language != 'en' or len(metadata.robots) != 1
            or not {'index', 'follow'} <= robots or 'noindex' in robots):
        raise ValueError('Survey HTML needs its canonical URL, English language, one H1 and indexable robots metadata')
    payloads[MANIFEST] = raw_manifest
    origin = urlsplit(location)
    for href in metadata.links:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc:
            if (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc):
                continue
        if not parsed.path:
            continue  # In-page anchor or query; no additional file.
        path = unquote(parsed.path)
        if path.startswith('/') and not path.startswith(PAGE):
            continue  # A link to another site page, checked by the site link tests.
        target = urljoin(PAGE, path)
        if not target.startswith(PAGE):
            raise ValueError('Survey relative link escapes its bundle: ' + href)
        name = target[len(PAGE):] or 'index.html'
        relative_path(name)
        if name not in payloads:
            raise ValueError('Survey link target is absent from its file manifest: ' + href)
    return {'manifest': manifest, 'payloads': payloads,
            'page': {'path': PAGE, 'indexable': True, 'sha256': digest(payloads['index.html'])}}


def copy_bundle(source, destination, *, source_root, site_url):
    """Copy an optional authored bundle into a fresh site staging directory, byte for byte."""
    source = Path(source)
    if not source.exists() and not source.is_symlink():
        return None
    bundle = load_bundle(source, source_root=source_root, site_url=site_url)
    targets = {name: checked_path(destination, name) for name in bundle['payloads']}
    for name, target in targets.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bundle['payloads'][name])
    return bundle['page']


def apply_site_shell(directory, *, head, top, bottom, retitle=None):
    """Publish a copied article inside the current site header and footer; the manifest keeps the reviewed fingerprint."""
    index, manifest_path = checked_path(directory, 'index.html'), checked_path(directory, MANIFEST)
    reviewed = index.read_bytes()
    manifest = parse_json(manifest_path.read_bytes())
    document = reviewed.decode('utf-8')
    document, bars = re.subn(r'<header class="article-bar">.*?</header>', lambda _: top, document, count=1, flags=re.S)
    if not bars or document.count('</body>') != 1 or '<style>' not in document:
        raise ValueError('Survey HTML needs one article bar, one closing body tag and an embedded stylesheet')
    # The site stylesheet comes first, so the article's reading styles decide its own column.
    document = document.replace('<style>', head + '<style>', 1).replace('</body>', bottom + '</body>')
    if retitle:
        # The site's title length limit applies to the article's <title> too; the reviewed body is unchanged.
        document = re.sub(r'<title>(.*?)</title>', lambda m: '<title>' + html.escape(retitle(html.unescape(m[1])), quote=False) + '</title>', document, count=1, flags=re.S)
    body = document.encode('utf-8')
    manifest['reviewed_index_sha256'] = digest(reviewed)
    manifest['files'] = [dict(item, bytes=len(body), sha256=digest(body)) if item['path'] == 'index.html' else item
                         for item in manifest['files']]
    index.write_bytes(body)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return {'path': PAGE, 'indexable': True, 'sha256': digest(body)}


def publication_plan(build, site, *, source_root, site_url, pages):
    """Validate the incoming bundle and all owned deletion paths before publication changes anything."""
    build, site = Path(build), Path(site)
    page_entries = [item for item in pages if item['path'] == PAGE]
    if len(page_entries) > 1:
        raise ValueError('Duplicate survey page in search manifest')
    payloads = {}
    if page_entries:
        incoming = load_bundle(build / 'survey', source_root=source_root, site_url=site_url)
        if page_entries[0] != incoming['page']:
            raise ValueError('Survey page differs from final search manifest')
        payloads = incoming['payloads']
    old_manifest = checked_path(site, 'survey/' + MANIFEST)
    owned = {}
    if old_manifest.exists():
        old_bytes = old_manifest.read_bytes()
        old = parse_json(old_bytes)
        owned = file_entries(old, site_url)
        owned[MANIFEST] = {'bytes': len(old_bytes), 'sha256': digest(old_bytes)}
    targets = {name: checked_path(site, 'survey/' + name) for name in set(owned) | set(payloads)}
    for name, target in targets.items():
        if not target.exists():
            continue
        body = target.read_bytes()
        if name in owned:
            if len(body) != owned[name]['bytes'] or digest(body) != owned[name]['sha256']:
                raise ValueError('Previously published survey file has unreviewed local changes: ' + name)
        elif body != payloads[name]:
            raise ValueError('Refusing to replace an unowned survey file: ' + name)
    return {'payloads': payloads, 'targets': targets, 'stale': sorted(set(owned)-set(payloads))}


def apply_publication(plan):
    """Apply a prevalidated plan; unrelated files are never removed or recursively copied."""
    for name, body in plan['payloads'].items():
        if name == MANIFEST:
            continue
        target = plan['targets'][name]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    for name in plan['stale']:
        if name != MANIFEST:
            plan['targets'][name].unlink(missing_ok=True)
    # Publish/remove the ownership manifest last.
    if MANIFEST in plan['payloads']:
        plan['targets'][MANIFEST].write_bytes(plan['payloads'][MANIFEST])
    elif MANIFEST in plan['stale']:
        plan['targets'][MANIFEST].unlink(missing_ok=True)
