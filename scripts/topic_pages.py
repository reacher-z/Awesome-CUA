"""Dense topic directories and reproducible subsets of reviewed catalog records."""
from specifications import safe_href
from collections import Counter, defaultdict
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlencode

from catalog import TOPICS as VOCABULARY
from export_citations import encode_citations
from paper_library import PAGE_SIZE, PLATFORMS, TOPICS
from publication_metadata import record_date_text


GROUPS = (
    ('papers', ('Papers & surveys', '论文与综述'), {'paper', 'survey'}),
    ('benchmarks', ('Benchmarks', '评测基准'), {'benchmark'}),
    ('datasets', ('Datasets', '数据集'), {'dataset'}),
    ('models', ('Models', '模型'), {'model'}),
    ('systems', ('Engineering & industry', '工程与产业'), {'agent', 'framework', 'infrastructure', 'tool', 'product', 'company'}),
)
KIND_LABELS = {
    'paper': ('Paper', '论文'), 'survey': ('Survey', '综述'), 'benchmark': ('Benchmark', '基准'),
    'dataset': ('Dataset', '数据集'), 'model': ('Model', '模型'), 'agent': ('Agent', '智能体'),
    'framework': ('Framework', '框架'), 'infrastructure': ('Infrastructure', '基础设施'),
    'tool': ('Tool', '工具'), 'product': ('Product', '产品'), 'company': ('Publisher', '发布方'),
}
EXPORT_FILES = ('records.jsonl', 'citations.bib', 'citations.csl.json')


def esc(value):
    return html.escape(str(value), quote=True)


def topic_name(topic, language='en'):
    return TOPICS.get(topic, (topic.replace('-', ' ').capitalize(),) * 2)[language == 'zh']


def topic_definition(topic):
    return VOCABULARY.get(topic, {}).get('definition', '')


def topic_path(topic=None, language='en', number=1):
    if topic is not None and not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', topic):
        raise ValueError('Unsafe topic identifier: ' + str(topic))
    return ('/zh' if language == 'zh' else '') + '/topics/' + (topic + '/' + (f'page/{number}/' if number > 1 else '') if topic else '')


def reviewed_topics(rows):
    grouped = defaultdict(dict)
    for row in rows:
        if row['review_status'] != 'curated' or row['scope'] not in {'core', 'adjacent'}:
            continue
        for topic in row['topics']:
            topic_path(topic)
            grouped[topic][row['id']] = row
    return {topic: sorted(members.values(), key=lambda row: row['id'])
            for topic, members in sorted(grouped.items())}


def topic_counts(rows):
    by_kind = Counter(row['kind'] for row in rows)
    return {'total': len(rows), **{slug: sum(by_kind[kind] for kind in kinds) for slug, _, kinds in GROUPS}}


def topic_page_count(counts):
    return max(1, -(-sum(counts[slug] for slug, _, _ in GROUPS) // PAGE_SIZE))


def topic_sections(topic, counts, language='en'):
    """Map each resource group to the topic page and anchor where its first entry appears.

    Pages list groups in GROUPS order, so manifest counts alone locate each group without the member rows."""
    links, start = {}, 0
    for slug, _, _ in GROUPS:
        if counts[slug]:
            links[slug] = topic_path(topic, language, start // PAGE_SIZE + 1) + '#' + slug
            start += counts[slug]
    return links


def write_topic_exports(destination, rows, catalog_bytes):
    """Publish full source records, keeping overlapping memberships explicit."""
    destination = Path(destination)
    (destination / 'downloads').mkdir(parents=True, exist_ok=True)
    root = destination / 'downloads/topics'
    if root.is_symlink():
        raise ValueError('Topic export root must not be a symbolic link')
    grouped = reviewed_topics(rows)
    entries = []
    for topic, members in grouped.items():
        folder = root / topic
        if folder.is_symlink():
            raise ValueError('Topic export folders must not be symbolic links')
        folder.mkdir(parents=True, exist_ok=True)
        payloads = [
            ('records.jsonl', ''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in members).encode(), len(members)),
            ('citations.bib', encode_citations(members), sum(row['kind'] in {'paper', 'survey'} for row in members)),
            ('citations.csl.json', encode_citations(members, format='csl-json'), sum(row['kind'] in {'paper', 'survey'} for row in members)),
        ]
        exports = []
        for name, payload, count in payloads:
            (folder / name).write_bytes(payload)
            exports.append({'url': '/downloads/topics/' + topic + '/' + name, 'records': count,
                            'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
        entries.append({'id': topic, 'name': {'en': topic_name(topic), 'zh': topic_name(topic, 'zh')},
                        'counts': topic_counts(members), 'resource_ids': [row['id'] for row in members],
                        'pages': {'en': topic_path(topic), 'zh': topic_path(topic, 'zh')}, 'exports': exports})
    reconcile_topic_exports(destination, grouped)
    reviewed = [row for row in rows if row['review_status'] == 'curated' and row['scope'] in {'core', 'adjacent'}]
    covered = {row['id'] for members in grouped.values() for row in members}
    manifest = {'schema_version': 1, 'catalog_sha256': hashlib.sha256(catalog_bytes).hexdigest(),
                'membership_policy': 'Explicit reviewed topic tags only; curated core/adjacent resources. No title-based inference.',
                'count_policy': 'Resources are not independent projects. Topic memberships overlap; do not sum topic totals.',
                'citation_policy': 'Default retained-source edition; source-specific author/date precision and paper versions are preserved.',
                'reviewed_resources': len(reviewed), 'resources_with_topics': len(covered),
                'reviewed_resources_without_topics': len(reviewed) - len(covered), 'topics': entries}
    (destination / 'downloads/topics.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest, grouped


def reconcile_topic_exports(destination, topic_ids):
    root = Path(destination) / 'downloads/topics'
    if root.is_symlink():
        raise ValueError('Topic export root must not be a symbolic link')
    if root.exists():
        for folder in root.iterdir():
            if folder.name not in topic_ids and folder.is_dir() and not folder.is_symlink():
                for name in EXPORT_FILES:
                    (folder / name).unlink(missing_ok=True)


def topic_index_body(manifest, *, language='en', site_url='https://awesomecua.github.io'):
    zh = language == 'zh'
    def tr(en, cn): return cn if zh else en
    entries = sorted(manifest['topics'], key=lambda item: (-item['counts']['total'], item['id']))
    body = ['<section class="topic-directory"><div class="library-heading"><div><div class="eyebrow">RESEARCH · DATA · TOOLS</div><h1>',
            tr('Explore by topic', '<span class="topic-title-name">Computer-Use</span> <span class="topic-title-name">主题目录</span>'), '</h1></div><a class="library-language" href="',
            topic_path(language='en' if zh else 'zh'), '">', 'English' if zh else '中文', '</a></div>',
            '<p class="topic-intro">', tr('Find the papers, models, datasets, benchmarks, and tools that belong together.', '把同一方向的论文、模型、数据集、评测基准与工具放在一起看。'), '</p>',
            '<div class="topic-overview"><span><strong>', str(len(entries)), '</strong> ', tr('topics', '个主题'), '</span><span><strong>',
            f'{manifest["resources_with_topics"]:,}', '</strong> ', tr('reviewed resources', '条已审阅资源'),
            '</span><a href="/downloads/topics.json">', tr('Topic index · JSON', '主题索引 · JSON'), ' ↓</a></div>',
            '<p class="topic-method">', tr('Topics overlap. Counts describe the reviewed catalog, not the size of the whole field. Blank cells mean no reviewed entries with that tag.',
            '主题可以交叉，数量反映已审阅目录，不代表整个领域的规模。空白表示该标签下尚无已审阅条目。'), '</p><p class="topic-table-help">', tr('Scroll the table horizontally to see every resource type.', '左右滑动表格，查看全部资源类型。'), '</p>',
            '<div class="topic-table-scroll" tabindex="0" role="region" aria-label="', tr('Topic coverage table', '主题覆盖表'), '"><table class="topic-matrix"><thead><tr><th scope="col">', tr('Topic', '主题'), '</th>']
    for slug, labels, _ in GROUPS:
        body += ['<th scope="col" class="topic-col-', slug, '">', labels[zh], '</th>']
    body += ['<th scope="col">', tr('Total', '合计'), '</th></tr></thead><tbody>']
    for entry in entries:
        path = topic_path(entry['id'], language)
        sections = topic_sections(entry['id'], entry['counts'], language)
        body += ['<tr data-topic="', entry['id'], '"><th scope="row"><a href="', path, '">', esc(entry['name'][language]), ' <span aria-hidden="true">↗</span></a></th>']
        for slug, labels, _ in GROUPS:
            count = entry['counts'][slug]
            body += ['<td class="topic-col-', slug, '">']
            if count:
                body += ['<a class="topic-number" href="', sections[slug], '" aria-label="', esc(entry['name'][language] + ' · ' + labels[zh] + ': ' + str(count)), '">', f'{count:,}', '</a>']
            else:
                body += ['<span class="topic-zero" aria-label="', tr('No reviewed entries', '暂无已审阅条目'), '">—</span>']
            body += ['</td>']
        body += ['<td class="topic-total">', f'{entry["counts"]["total"]:,}', '</td></tr>']
    body += ['</tbody></table></div><p class="topic-method">', tr('Use the complete catalog to search metadata-only discoveries or entries without topic tags.', '元数据待审条目及未标注主题的资源仍可在完整目录检索。'),
             ' <a href="/?lang=', language, '#catalog">', tr('Search all resources', '检索全部资源'), ' ↗</a> · <a href="/about/">', tr('Editorial policy', '收录方法'), '</a></p></section>']
    schema = {'@type': 'ItemList', 'name': tr('Computer-use research topics', 'Computer-Use 研究主题'),
              'numberOfItems': len(entries), 'itemListElement': [{'@type': 'ListItem', 'position': i + 1,
              'name': entry['name'][language], 'url': site_url + topic_path(entry['id'], language)} for i, entry in enumerate(entries)]}
    return ''.join(body), schema


def ordered_groups(rows):
    for slug, labels, kinds in GROUPS:
        selected = [row for row in rows if row['kind'] in kinds]
        selected.sort(key=(lambda row: (record_date_text(row), row['id'])) if slug == 'papers'
                      else (lambda row: (row['name'].casefold(), row['id'])), reverse=slug == 'papers')
        if selected:
            yield slug, labels, selected


def topic_body(topic, rows, resource_path, *, language='en', site_url='https://awesomecua.github.io', number=1):
    """Return one topic page's HTML and an ItemList describing exactly its visible resources."""
    zh = language == 'zh'
    def tr(en, cn): return cn if zh else en
    name = topic_name(topic, language)
    counts = topic_counts(rows)
    pages = topic_page_count(counts)
    if not 1 <= number <= pages:
        raise ValueError(f'Topic page {number} is outside 1..{pages}')
    here = topic_path(topic, language, number)
    sections = topic_sections(topic, counts, language)
    start = (number - 1) * PAGE_SIZE
    query = '/?' + esc(urlencode({'topic': topic, 'review': 'curated', 'lang': language})) + '#catalog'
    export = '/downloads/topics/' + topic + '/'
    body = ['<section class="topic-directory topic-detail"><div class="topic-back"><a href="', topic_path(language=language), '">← ',
            tr('All topics', '全部主题'), '</a><a href="', topic_path(topic, 'en' if zh else 'zh', number), '">', 'English' if zh else '中文', '</a></div>',
            '<h1>', esc(name), '</h1><p class="topic-intro">', *(['<span lang="en">', esc(topic_definition(topic)), '</span> '] if topic_definition(topic) else []), tr('Source-reviewed research and assets tagged with ', '已审阅并标注「') + esc(name) + tr('.', '」的研究与资产。'), '</p>',
            '<div class="topic-overview"><span><strong>', f'{counts["total"]:,}', '</strong> ', tr('reviewed resources', '条已审阅资源'), '</span><a href="', query, '">',
            tr('Search this topic', '检索此主题'), ' ↗</a><a href="', export, 'records.jsonl" download>JSONL ↓</a>']
    if counts['papers']:
        body += ['<a href="', export, 'citations.bib" download>BibTeX ↓</a><a href="', export, 'citations.csl.json" download>CSL JSON ↓</a>']
    body += ['</div><nav class="topic-sections" aria-label="', tr('Resource types in this topic', '当前主题的资源类型'), '">']
    for slug, labels, _ in GROUPS:
        if counts[slug]:
            link = sections[slug]
            body += ['<a class="topic-col-', slug, '" href="', link[len(here):] if link.startswith(here + '#') else link, '">', labels[zh], '<strong>', str(counts[slug]), '</strong></a>']
    body += ['</nav><p class="topic-method">', tr('Membership follows reviewed tags; it does not establish a dependency between neighboring records. Dates preserve source precision. Annotations retain their original language.',
             '条目依据已审阅标签归类，同一主题不表示资源之间存在依赖关系。日期保留来源精度，注释保留原语言。'), '</p>']
    visible, offset = [], 0
    for slug, labels, selected in ordered_groups(rows):
        shown = selected[max(0, start - offset):max(0, start + PAGE_SIZE - offset)]
        offset += len(selected)
        if not shown:
            continue
        body += ['<section class="topic-resource-group" aria-labelledby="', slug, '"><div class="paper-year-heading"><h2 id="', slug, '">', labels[zh],
                 '</h2><span>', str(len(selected)), '</span><a href="#content">', tr('Back to top', '回到顶部'), ' ↑</a></div>']
        for row in shown:
            visible.append(row)
            date = record_date_text(row)
            path = resource_path(row)
            primary = row.get('details', {}).get('arxiv_snapshot', {}).get('versioned_url') or row['url']
            body += ['<article class="topic-resource" data-resource-id="', esc(row['id']), '"><div class="topic-resource-meta"><span class="topic-kind topic-col-', slug, '">',
                     KIND_LABELS[row['kind']][zh], '</span>']
            if date:
                body += ['<time datetime="', date, '">', date, '</time>'] if len(date) == 10 else ['<span>', date, '</span>']
            body += ['</div><div class="topic-resource-main"><h3><a href="', path, '">', esc(row['name']), '</a></h3>']
            if row.get('authors'):
                authors = ', '.join(row['authors'][:2])
                if len(row['authors']) > 2:
                    authors += tr(' et al.', ' 等 ' + str(len(row['authors'])) + ' 位作者')
                body += ['<p class="topic-resource-authors">', esc(authors), '</p>']
            body += ['<p>', esc(row.get('summary') or ''), '</p><div class="topic-resource-facets">']
            for platform in row['environments']:
                if platform != 'unspecified':
                    body += ['<span>', esc(PLATFORMS.get(platform, (platform, platform))[zh]), '</span>']
            if row['scope'] == 'adjacent':
                body += ['<span>', tr('Adjacent research', '相关研究'), '</span>']
            body += ['</div></div><div class="topic-resource-links"><a href="', safe_href(primary), '">', tr('Source', '一手来源'), ' ↗</a>']
            if row['kind'] in {'paper', 'survey'}:
                body += ['<a href="', path, 'citation.bib" download>BibTeX ↓</a>']
            body += ['<a href="', path, '">', tr('Details', '详情'), ' →</a></div></article>']
        body += ['</section>']
    if pages > 1:
        body += ['<nav class="pagination library-pager" aria-label="', tr('Topic pages', '主题分页'), '">',
                 '<a href="' + topic_path(topic, language, number - 1) + '" rel="prev">' + tr('← Previous', '← 上一页') + '</a>' if number > 1 else '<span></span>', '<span class="page-numbers">']
        body += ['<a href="' + topic_path(topic, language, n) + '" aria-label="' + tr('Page ', '第 ') + str(n) + tr('', ' 页') + '"' + (' aria-current="page"' if n == number else '') + '>' + str(n) + '</a>' for n in range(1, pages + 1)]
        body += ['</span>', '<a href="' + topic_path(topic, language, number + 1) + '" rel="next">' + tr('Next →', '下一页 →') + '</a>' if number < pages else '<span></span>',
                 '</nav><p class="library-range">', tr(f'Showing {start + 1:,}–{start + len(visible):,} of {offset:,} resources.', f'第 {start + 1:,}–{start + len(visible):,} 条，共 {offset:,} 条资源。'), '</p>']
    body += ['<p class="topic-method">', tr('Get full records and evidence through the ', '通过'), '<a href="/downloads/topics.json">', tr('topic export manifest', '主题导出清单'),
             '</a>', tr('. Source records can be passed to the standard RAG and citation exporters after cloning the catalog.', '获取完整记录和证据。克隆目录后，可将主题记录直接交给标准 RAG 与引用导出工具。'), '</p></section>']
    schema = {'@type': 'ItemList', 'name': name, 'numberOfItems': len(visible),
              'itemListElement': [{'@type': 'ListItem', 'position': start + i + 1, 'name': row['name'], 'url': site_url + resource_path(row)}
                                  for i, row in enumerate(visible)]}
    return ''.join(body), schema


def topic_markdown(topic, rows, resource_path, *, language='en', site_url='https://awesomecua.github.io'):
    lines = ['# ' + topic_name(topic, language), '', *([topic_definition(topic), ''] if topic_definition(topic) else []),
             'Reviewed topic membership; resources can appear in multiple topics. Shared membership is not a dependency claim.', '',
             f'Full source records: {site_url}/downloads/topics/{topic}/records.jsonl', '']
    for _, labels, selected in ordered_groups(rows):
        lines += ['## ' + labels[language == 'zh'], '']
        for row in selected:
            name = row['name'].replace('[', r'\[').replace(']', r'\]').replace('\n', ' ')
            lines += [f"- [{name}]({site_url + resource_path(row)}) — {record_date_text(row) or 'Date not recorded'}",
                      '  ' + (row.get('summary') or '').replace('\n', ' ')]
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'
