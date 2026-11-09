"""Crawler and subscriber entry points: robots.txt and the Atom and JSON feeds of newly reviewed resources."""
from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET

ATOM_NS = 'http://www.w3.org/2005/Atom'
FEED_SIZE = 100
FEED_TITLE = 'AwesomeCUA: newly reviewed resources'
FEED_DESCRIPTION = ('Computer-use agent papers, models, datasets, benchmarks and tools as they pass source review, '
                    'newest review first. Metadata-only bibliography records and unreviewed candidates are not included.')

# One list drives robots.txt and its test. A crawler that matches a named group ignores the * group
# (RFC 9309 2.2.1), so every named group repeats the same allow-all policy. Tokens use only letters, '-' and '_'.
CRAWLERS = (
    ('Search engines', ('Googlebot', 'bingbot', 'Applebot', 'DuckDuckBot', 'YandexBot', 'Baiduspider', 'Bytespider',
                        'PetalBot', 'Yeti', 'SeznamBot', 'YouBot')),
    ('AI search and answer indexes', ('OAI-SearchBot', 'Claude-SearchBot', 'PerplexityBot', 'Amzn-SearchBot', 'meta-webindexer',
                                      'DuckAssistBot', 'MistralAI-Index', 'Kimi-SearchBot', 'ExaSearchBot', 'YandexAdditional',
                                      'YandexAdditionalBot')),
    ("Assistants and agents fetching on a user's request", ('ChatGPT-User', 'Claude-User', 'Claude-Agent', 'Perplexity-User',
                                                            'Google-Agent', 'Amzn-User', 'meta-externalfetcher', 'MistralAI-User',
                                                            'Kimi-User', 'ExaUser')),
    ('Model training, research and grounding (Google-Extended and Applebot-Extended are control tokens)',
     ('GPTBot', 'ClaudeBot', 'Google-Extended', 'GoogleOther', 'Google-CloudVertexBot', 'Applebot-Extended', 'CCBot',
      'meta-externalagent', 'Amazonbot', 'MistralAI-Training', 'KimiBot')),
)
# Cloudflare Content Signals Policy (https://contentsignals.org/). The catalog's own annotations are MIT licensed.
CONTENT_SIGNAL = 'search=yes, ai-input=yes'


def crawler_tokens():
    return [token for _, tokens in CRAWLERS for token in tokens]


def robots_txt(site):
    lines = [f'# Crawl policy for {site}/', '# Search engines, AI search, AI assistants and AI crawlers are all welcome.',
             '# Content Signals Policy: https://contentsignals.org/', f'# Agent-readable index: {site}/llms.txt', '',
             'User-agent: *', f'Content-Signal: {CONTENT_SIGNAL}', 'Allow: /', '',
             '# A crawler that matches a named group ignores the * group (RFC 9309 2.2.1),',
             '# so every named crawler below shares one group with the same allow-all policy.',
             '# Also covered by *: 360Spider, Sogou spider, YisouSpider (outside the RFC 9309 token grammar or undocumented).', '']
    # Comment lines may separate the User-agent lines of one group; a blank line would end it.
    for label, tokens in CRAWLERS:
        lines += ['# ' + label] + [f'User-agent: {token}' for token in tokens]
    lines += [f'Content-Signal: {CONTENT_SIGNAL}', 'Allow: /', '',
              f'Sitemap: {site}/sitemap.xml', f'Sitemap: {site}/sitemap.txt']
    return '\n'.join(lines) + '\n'


def feed_entry(record, *, site, page_path, reviewed_at, modified, summary, kind_label):
    """One feed item, shared by the Atom and JSON Feed writers so both describe the same entries.

    Titles and summaries collapse to single-spaced text: no feed line may end in whitespace (publication runs git diff --check)."""
    return {'id': site + page_path, 'url': site + page_path, 'title': ' '.join(record['name'].split()), 'summary': ' '.join(summary.split()),
            'published': reviewed_at, 'updated': modified or reviewed_at, 'kind': record['kind'], 'kind_label': kind_label,
            'source_url': record['url'], 'topics': list(record['topics']), 'environments': list(record['environments']),
            'record_url': site + page_path + 'record.json', 'markdown_url': site + page_path + 'index.md'}


def atom_feed(entries, *, site, updated):
    def node(parent, tag, text=None, **attributes):
        element = ET.SubElement(parent, tag, attributes)
        if text is not None:
            element.text = text
        return element
    # The namespace is a literal attribute, as in the sitemaps, so no global ElementTree prefix is registered.
    feed = ET.Element('feed', {'xmlns': ATOM_NS, 'xml:lang': 'en'})
    node(feed, 'title', FEED_TITLE)
    node(feed, 'subtitle', FEED_DESCRIPTION)
    node(feed, 'id', site + '/feed.xml')
    node(feed, 'updated', updated)
    node(feed, 'link', href=site + '/feed.xml', rel='self', type='application/atom+xml')
    node(feed, 'link', href=site + '/', rel='alternate', type='text/html')
    node(feed, 'link', href=site + '/feed.json', rel='alternate', type='application/feed+json')
    author = node(feed, 'author')
    node(author, 'name', 'AwesomeCUA')
    node(author, 'uri', site + '/')
    node(feed, 'rights', 'Catalog annotations: MIT. Linked resources keep their own terms.')
    for entry in entries:
        item = node(feed, 'entry')
        node(item, 'title', entry['title'])
        node(item, 'id', entry['id'])
        node(item, 'link', href=entry['url'], rel='alternate', type='text/html')
        node(item, 'link', href=entry['source_url'], rel='related')
        node(item, 'link', href=entry['markdown_url'], rel='alternate', type='text/markdown')
        node(item, 'published', entry['published'])
        node(item, 'updated', entry['updated'])
        node(item, 'category', term=entry['kind'], label=entry['kind_label'])
        node(item, 'summary', entry['summary'])
    ET.indent(feed, space='  ')
    return ET.tostring(feed, encoding='utf-8', xml_declaration=True).decode() + '\n'


def json_feed(entries, *, site):
    """JSON Feed 1.1 (https://www.jsonfeed.org/version/1.1/) with the same items as the Atom feed."""
    return {
        'version': 'https://jsonfeed.org/version/1.1', 'title': FEED_TITLE, 'description': FEED_DESCRIPTION,
        'home_page_url': site + '/', 'feed_url': site + '/feed.json', 'language': 'en',
        'favicon': site + '/favicon.svg', 'authors': [{'name': 'AwesomeCUA', 'url': site + '/'}],
        'items': [{'id': entry['id'], 'url': entry['url'], 'external_url': entry['source_url'], 'title': entry['title'],
                   'content_text': entry['summary'], 'summary': entry['summary'], 'date_published': entry['published'],
                   'date_modified': entry['updated'], 'tags': [entry['kind'], *entry['topics']],
                   '_awesomecua': {'kind': entry['kind'], 'review_status': 'curated', 'environments': entry['environments'],
                                   'record_json': entry['record_url'], 'markdown': entry['markdown_url']}}
                  for entry in entries],
    }


def write_feeds(destination, entries, *, site, updated):
    destination = Path(destination)
    (destination / 'feed.xml').write_text(atom_feed(entries, site=site, updated=updated), encoding='utf-8')
    (destination / 'feed.json').write_text(json.dumps(json_feed(entries, site=site), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
