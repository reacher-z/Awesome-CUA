"""Read and write the XML sitemaps (standard library only: the IndexNow job runs without dependencies)."""
from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

SITEMAP_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
XHTML_NS = 'http://www.w3.org/1999/xhtml'
# sitemap.xml is an index of these root-level files; a sitemap may list only URLs at or below its own location.
SECTIONS = ('pages', 'resources', 'papers', 'categories')
URL_LIMIT = 50_000


def section_file(section):
    return f'sitemap-{section}.xml'


def _xml(element):
    # Namespaces are written as literal attributes and prefixes, without ElementTree's global prefix registry.
    ET.indent(element, space='  ')
    return ET.tostring(element, encoding='utf-8', xml_declaration=True).decode() + '\n'


def write_sitemaps(destination, site, entries):
    """Write sitemap.xml (an index), one urlset per section and the plain-text sitemap.txt.

    `entries` are the indexable pages: {'path', 'section', 'lastmod' (or None), 'alternates' ({hreflang: path})}.
    Alternates may name only pages that are themselves listed, so every URL in the files is a canonical page.
    """
    destination = Path(destination)
    entries = sorted(entries, key=lambda entry: entry['path'])
    listed = {entry['path'] for entry in entries}
    if len(listed) != len(entries):
        raise ValueError('A page is listed twice in the sitemap entries')
    index = ET.Element('sitemapindex', xmlns=SITEMAP_NS)
    for section in SECTIONS:
        members = [entry for entry in entries if entry['section'] == section]
        if len(members) > URL_LIMIT:
            raise ValueError(f'Sitemap section {section} exceeds {URL_LIMIT:,} URLs')
        target = destination / section_file(section)
        if not members:
            target.unlink(missing_ok=True)
            continue
        urlset = ET.Element('urlset', {'xmlns': SITEMAP_NS, 'xmlns:xhtml': XHTML_NS})
        for entry in members:
            node = ET.SubElement(urlset, 'url')
            ET.SubElement(node, 'loc').text = site + entry['path']
            if entry.get('lastmod'):
                ET.SubElement(node, 'lastmod').text = entry['lastmod']
            for language, path in (entry.get('alternates') or {}).items():
                if path not in listed:
                    raise ValueError(f'{entry["path"]} names an alternate outside the sitemap: {path}')
                ET.SubElement(node, 'xhtml:link', rel='alternate', hreflang=language, href=site + path)
        target.write_text(_xml(urlset), encoding='utf-8')
        item = ET.SubElement(index, 'sitemap')
        ET.SubElement(item, 'loc').text = f'{site}/{section_file(section)}'
        dates = [entry['lastmod'] for entry in members if entry.get('lastmod')]
        if dates:
            ET.SubElement(item, 'lastmod').text = max(dates)
    (destination / 'sitemap.xml').write_text(_xml(index), encoding='utf-8')
    (destination / 'sitemap.txt').write_text(''.join(site + entry['path'] + '\n' for entry in entries), encoding='utf-8')


def sitemap_urls(site_dir, site):
    """Every page URL in a built site's sitemap.xml, following a sitemap index to its local child files."""
    site_dir = Path(site_dir)
    namespace = {'s': SITEMAP_NS}
    root = ET.parse(site_dir / 'sitemap.xml').getroot()
    if root.tag == f'{{{SITEMAP_NS}}}urlset':
        return [loc.text for loc in root.findall('s:url/s:loc', namespace)]
    if root.tag != f'{{{SITEMAP_NS}}}sitemapindex':
        raise ValueError('sitemap.xml is neither a urlset nor a sitemap index')
    urls = []
    for loc in root.findall('s:sitemap/s:loc', namespace):
        name = loc.text.removeprefix(site + '/')
        if name == loc.text or '/' in name or not name.endswith('.xml'):
            raise ValueError('Sitemap index names a file outside the site root: ' + loc.text)
        child = ET.parse(site_dir / name).getroot()
        if child.tag != f'{{{SITEMAP_NS}}}urlset':
            raise ValueError('Sitemap index child is not a urlset: ' + name)
        urls += [item.text for item in child.findall('s:url/s:loc', namespace)]
    return urls
