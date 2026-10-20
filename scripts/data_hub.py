"""Bilingual data downloads, with counts and fingerprints from actual artifacts."""
from contextlib import closing
import hashlib
import html
import json
from pathlib import Path
import sqlite3

from agent_pages import CLONE_COMMAND, RELEASES_URL
from export_citations import encode_citations
from export_rag import encode_documents
from repository_identity import attach_repository_aliases
from export_candidates import RECORD_FILE as CANDIDATE_FILE, MANIFEST_FILE as CANDIDATE_MANIFEST, SCHEMAS as CANDIDATE_SCHEMAS, validate_candidate_export


GROUPS = {
    'catalog': ('Complete catalog', '完整目录'),
    'rag': ('Retrieval documents', 'RAG 检索文档'),
    'citations': ('Paper citations', '论文引用'),
    'research': ('Topics and comparisons', '主题与对比'),
    'provenance': ('Sources and review states', '来源与审阅状态'),
    'contracts': ('Data contracts', '数据规范'),
}
UNITS = {
    'resources': ('resources', '条资源'), 'documents': ('documents', '份文档'),
    'citations': ('citations', '条引用'), 'profiles': ('profiles', '份规格'),
    'relations': ('relations', '项关系'), 'topics': ('topics', '个主题'),
    'papers': ('arXiv records', '条 arXiv 记录'), 'decisions': ('decisions', '项决定'),
    'sources': ('discovery documents', '份发现文档'), 'editions': ('publication editions', '份出版记录'),
    'exports': ('export files', '个导出文件'), 'reports': ('report', '份报告'),
    'schemas': ('schema', '份规范'),
    'aliases': ('former repository names', '个仓库旧标识'),
    'repositories': ('repositories', '个仓库'),
}
SCOPE_LABELS = {
    'active': ('All active records', '全部当前记录'),
    'reviewed': ('Reviewed records', '已审阅记录'),
    'reviewed-publication': ('Reviewed publication editions', '已审阅出版版本'),
    'recorded-publication': ('Recorded publication editions', '已记录出版版本'),
    'archive': ('Retained archive', '保留的原始档案'),
    'provenance': ('Provenance and status', '来源与状态'),
    'contract': ('Format contract', '格式规范'),
    'candidate-observations': ('Unreviewed candidates', '待审候选'),
}


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def byte_size(value):
    if value < 1024:
        return str(value) + ' B'
    if value < 1024 * 1024:
        return f'{value / 1024:.1f} KiB'
    return f'{value / (1024 * 1024):.1f} MiB'


def line_count(path, *, prefix=None):
    with Path(path).open(encoding='utf-8') as stream:
        if prefix is None:
            return sum(1 for line in stream if line.strip())
        return sum(1 for line in stream if line.startswith(prefix))


def build_download_manifest(destination, rows, catalog_bytes):
    destination = Path(destination)
    source_sha = hashlib.sha256(catalog_bytes).hexdigest()
    expected_records = {row['id']: row for row in rows}
    source_records = [json.loads(line) for line in catalog_bytes.splitlines() if line.strip()]
    if len(expected_records) != len(rows) or len(source_records) != len(rows) or {row['id']: row for row in source_records} != expected_records:
        raise ValueError('Source catalog bytes differ from the supplied records')
    artifacts = []
    def read_json(path): return json.loads((destination / path.lstrip('/')).read_text(encoding='utf-8'))
    def add(identity, path, group, title, description, file_format, media_type, count, unit, scope):
        target = destination / path.lstrip('/')
        if not target.is_file() or target.is_symlink():
            raise ValueError('Missing or unsafe download artifact: ' + path)
        artifacts.append({'id': identity, 'path': path, 'group': group,
                          'title': dict(zip(('en', 'zh'), title)), 'description': dict(zip(('en', 'zh'), description)),
                          'format': file_format, 'media_type': media_type, 'count': {'value': count, 'unit': unit},
                          'scope': scope, 'bytes': target.stat().st_size, 'sha256': fingerprint(target)})
    if fingerprint(destination / 'downloads/catalog.jsonl') != source_sha:
        raise ValueError('Download catalog differs from the source snapshot')
    array = read_json('/data/records.json')
    if len(array) != len(rows) or {r['id']: r for r in array} != expected_records:
        raise ValueError('JSON array differs from the source records')
    with closing(sqlite3.connect((destination / 'downloads/catalog.sqlite').resolve().as_uri() + '?mode=ro', uri=True)) as database:
        sql_rows = database.execute('SELECT id, name, kind, url, review_status, scope, published_at, summary, record_json FROM resources').fetchall()
    if len(sql_rows) != len(rows) or {row[0]: json.loads(row[-1]) for row in sql_rows} != expected_records:
        raise ValueError('SQLite records differ from the source catalog')
    for sql_row in sql_rows:
        if sql_row[:-1] != tuple(expected_records[sql_row[0]][key] for key in ('id', 'name', 'kind', 'url', 'review_status', 'scope', 'published_at', 'summary')):
            raise ValueError('SQLite searchable fields differ from the source catalog')
    for identity, path, title, description, file_format, media in [
        ('catalog-jsonl', '/downloads/catalog.jsonl', ('Full catalog', '完整目录'),
         ('Every active source record, including metadata-only discoveries. One JSON object per line.', '全部当前资源及完整来源记录，包含仅核实书目的发现项。每行一个 JSON 对象。'), 'JSONL', 'application/x-ndjson'),
        ('catalog-json', '/data/records.json', ('Full catalog as a JSON array', '完整目录 JSON 数组'),
         ('The same complete records in one JSON array for clients that expect a single JSON document.', '同一份完整记录，以单个 JSON 数组提供，适合直接读取 JSON 的客户端。'), 'JSON', 'application/json'),
        ('catalog-sqlite', '/downloads/catalog.sqlite', ('Queryable database', '可查询数据库'),
         ('Resource rows, full-text search, topic/platform facets and reviewed relationships.', '资源记录、全文搜索、主题与平台分面，以及已审阅的关联关系。'), 'SQLite', 'application/vnd.sqlite3'),
    ]:
        add(identity, path, 'catalog', title, description, file_format, media, len(rows), 'resources', 'active')

    rag = read_json('/downloads/rag-manifest.json')
    citations = read_json('/downloads/citations-manifest.json')
    topics = read_json('/downloads/topics.json')
    if any(manifest['catalog_sha256'] != source_sha for manifest in (rag, citations, topics)):
        raise ValueError('Download manifests refer to different catalog snapshots')
    for export in rag['exports']:
        all_records = export['includes_metadata_only']
        expected = len(rows) if all_records else sum(row['review_status'] == 'curated' for row in rows)
        if export['records'] != expected or line_count(destination / 'downloads' / export['file']) != expected:
            raise ValueError('RAG count differs from its source selection')
        add('rag-all' if all_records else 'rag-reviewed', '/downloads/' + export['file'], 'rag',
            ('All retrieval documents', '全部检索文档') if all_records else ('Reviewed retrieval documents', '已审阅检索文档'),
            ('Complete active corpus; preserve the metadata-only review states when retrieving.', '完整当前语料；检索时保留其中仅核实书目的待审状态。') if all_records else
            ('Reviewed core and adjacent resources, with text, citations, evidence and license metadata.', '已审阅的核心与相关资源，保留文本、引用、证据和许可元数据。'),
            'JSONL', 'application/x-ndjson', export['records'], 'documents', 'active' if all_records else 'reviewed')
        if artifacts[-1]['sha256'] != export['sha256']:
            raise ValueError('RAG export fingerprint mismatch: ' + export['file'])
        expected_sha = hashlib.sha256(encode_documents(rows, include_metadata=all_records)).hexdigest()
        if artifacts[-1]['sha256'] != expected_sha:
            raise ValueError('RAG content differs from the source selection: ' + export['file'])
    add('rag-manifest', '/downloads/rag-manifest.json', 'rag', ('RAG export manifest', 'RAG 导出清单'),
        ('Document counts, review policy and file fingerprints.', '文档数量、审阅规则和文件指纹。'), 'JSON', 'application/json', len(rag['exports']), 'exports', 'provenance')

    for export in citations['exports']:
        is_publication = export['edition'] == 'publication'
        all_records = export['includes_metadata_only']
        title = ('Publication citations', '正式出版版引用') if is_publication else (
            ('All bibliography citations', '全部书目引用') if all_records else ('Reviewed paper citations', '已审阅论文引用'))
        description = ('The recorded publication edition uses its own authors, title, venue and date precision.', '使用所记录出版版的作者、题名、会议／期刊及日期精度。') if is_publication else (
            ('Includes metadata-only papers and surveys with their review state retained.', '包含仅核实书目的论文与综述，并保留审阅状态。') if all_records else
            ('Reviewed papers and surveys. Retained arXiv versions and partial dates remain explicit.', '已审阅论文与综述，保留记录的 arXiv 版本与部分日期。'))
        is_bibtex = export['format'] == 'bibtex'
        expected = sum(row['kind'] in {'paper','survey'} and (all_records or row['review_status'] == 'curated')
                       and (not is_publication or bool(row['details'].get('publication'))) for row in rows)
        actual = line_count(destination / 'downloads' / export['file'], prefix='@') if is_bibtex else len(read_json('/downloads/' + export['file']))
        if export['records'] != expected or actual != expected:
            raise ValueError('Citation count differs from its source selection')
        add(export['file'].replace('.', '-'), '/downloads/' + export['file'], 'citations', title, description,
            'BibTeX' if is_bibtex else 'CSL JSON', 'application/x-bibtex' if is_bibtex else 'application/vnd.citationstyles.csl+json',
            export['records'], 'citations', 'reviewed-publication' if is_publication else ('active' if all_records else 'reviewed'))
        if artifacts[-1]['sha256'] != export['sha256'] or artifacts[-1]['bytes'] != export['bytes']:
            raise ValueError('Citation export fingerprint mismatch: ' + export['file'])
        expected_sha = hashlib.sha256(encode_citations(rows, format=export['format'], include_metadata=all_records, edition=export['edition'])).hexdigest()
        if artifacts[-1]['sha256'] != expected_sha:
            raise ValueError('Citation content differs from the source edition and selection: ' + export['file'])
    add('citations-manifest', '/downloads/citations-manifest.json', 'citations', ('Citation export manifest', '引用导出清单'),
        ('Edition, date and identity policies with exact counts and fingerprints.', '引用版次、日期和身份规则，以及精确数量与指纹。'), 'JSON', 'application/json', len(citations['exports']), 'exports', 'provenance')

    add('topics', '/downloads/topics.json', 'research', ('Topic subsets', '主题子集'),
        ('Exact member IDs and JSONL/citation downloads for every reviewed topic. Memberships overlap.', '每个已审阅主题的精确成员 ID 与 JSONL、引用下载。主题成员可以交叉。'),
        'JSON', 'application/json', len(topics['topics']), 'topics', 'reviewed')
    for slug, labels in [('benchmarks', ('Benchmark protocols', '基准协议')), ('datasets', ('Dataset profiles', '数据集规格'))]:
        profile = read_json('/downloads/' + slug + '-profiles.json')
        if profile['profile_count'] != len(profile['records']):
            raise ValueError('Profile count does not match its records')
        add(slug + '-profiles', '/downloads/' + slug + '-profiles.json', 'research', labels,
            ('Source-reviewed interfaces, formats, counting units and scope. Missing fields remain unknown.', '已核读来源的接口、格式、计数单位和范围；未记录字段保持未知。'),
            'JSON', 'application/json', len(profile['records']), 'profiles', 'reviewed')
    relationships = read_json('/downloads/relationships.json')
    if relationships['relation_count'] != len(relationships['relations']):
        raise ValueError('Relationship count does not match its edges')
    add('relationships', '/downloads/relationships.json', 'research', ('Reviewed relationships', '已审阅关系'),
        ('Explicit source-backed relationships; incidental mentions and shared topics are separate.', '有明确来源的关联关系；偶然提及和相同主题分别处理。'),
        'JSON', 'application/json', len(relationships['relations']), 'relations', 'reviewed')

    sources = read_json('/downloads/sources.json')
    scope_decisions = read_json('/downloads/exclusions.json')
    archive_count = line_count(destination / 'downloads/arxiv-archive.jsonl')
    publication_count = line_count(destination / 'downloads/publications.jsonl')
    add('coverage', '/downloads/coverage.json', 'provenance', ('Coverage ledger', '覆盖台账'),
        ('Observed source populations, review states and unresolved gaps.', '已观察到的来源范围、审阅状态和待解决缺口。'), 'JSON', 'application/json', 1, 'reports', 'provenance')
    add('sources', '/downloads/sources.json', 'provenance', ('Discovery-source registry', '发现来源登记'),
        ('Community collections and search sources used to discover candidates.', '用于发现候选条目的社区合集和来源文档。'), 'JSON', 'application/json', len(sources), 'sources', 'provenance')
    add('scope-decisions', '/downloads/exclusions.json', 'provenance', ('Scope decisions', '范围审阅决定'),
        ('Exclusion reasons, original evidence and any decisions awaiting revalidation.', '排除理由、原始证据，以及需要重新验证的决定。'), 'JSON', 'application/json', len(scope_decisions['decisions']), 'decisions', 'provenance')
    add('arxiv-archive', '/downloads/arxiv-archive.jsonl', 'provenance', ('Raw arXiv metadata archive', '原始 arXiv 元数据档案'),
        ('Retained ingestion snapshots, including excluded records. This is not the active catalog.', '保留的采集快照，包含已排除记录；其范围不同于当前有效目录。'), 'JSONL', 'application/x-ndjson', archive_count, 'papers', 'archive')
    add('publications', '/downloads/publications.jsonl', 'provenance', ('Publication observations', '出版来源记录'),
        ('Publication facts attached to canonical paper identities; not a second paper count.', '附加到规范论文身份的出版事实，不作为另一篇论文重复计数。'), 'JSONL', 'application/x-ndjson', publication_count, 'editions', 'recorded-publication')
    repository_declarations = read_json('/downloads/repository-aliases.json')
    if attach_repository_aliases(rows,repository_declarations) != rows:
        raise ValueError('Repository aliases differ from their catalog owners and evidence')
    add('repository-aliases', '/downloads/repository-aliases.json', 'provenance', ('Former repository names', '仓库旧地址映射'),
        ('Former and canonical GitHub or Hugging Face names verified against the same repository ID. They do not add resources.', '通过相同的 GitHub 或 Hugging Face 仓库 ID 核实旧名与规范名称。它们不增加资源记录。'),
        'JSON', 'application/json', len(repository_declarations), 'aliases', 'provenance')
    candidate_files = [destination / 'downloads' / name for name in (CANDIDATE_FILE, CANDIDATE_MANIFEST)]
    have_candidates = any(path.exists() or path.is_symlink() for path in candidate_files)
    if have_candidates:
        if any(not path.is_file() or path.is_symlink() for path in candidate_files):
            raise ValueError('Candidate observations require a complete, safe export pair')
        candidate_manifest = read_json('/downloads/' + CANDIDATE_MANIFEST)
        candidate_rows = validate_candidate_export(candidate_files[0].read_bytes(), candidate_manifest, catalog_bytes=catalog_bytes)
        add('github-candidates', '/downloads/' + CANDIDATE_FILE, 'provenance', ('GitHub candidate repositories', 'GitHub 候选仓库'),
            ('Public API metadata, counted by numeric repository ID. CUA relevance, availability and licenses await review; these observations are separate from and may overlap the active catalog.',
             '公开 API 元数据，按数字仓库 ID 去重。CUA 相关性、可用性和许可仍待审阅；这些观察记录独立于当前目录且可能与其重叠。'),
            'JSONL', 'application/x-ndjson', len(candidate_rows), 'repositories', 'candidate-observations')
        add('github-candidates-manifest', '/downloads/' + CANDIDATE_MANIFEST, 'provenance', ('Candidate observation manifest', '候选观察清单'),
            ('Independent observation and input fingerprints, query limits, primary receipts, and a separate active-catalog comparison context.',
             '独立的观察与输入指纹、查询边界、一手收据，以及单独标明的当前目录对照信息。'),
            'JSON', 'application/json', 1, 'reports', 'candidate-observations')
    for name, title in [
        ('resource.schema.json', ('Resource schema', '资源记录规范')),
        ('scope-decision.schema.json', ('Scope-decision schema', '范围决定规范')),
        ('publication-observation.schema.json', ('Publication-observation schema', '出版来源规范')),
        ('download-manifest.schema.json', ('Download-manifest schema', '下载清单规范')),
        ('repository-alias.schema.json', ('Repository-alias schema', '仓库地址映射规范')),
    ]:
        add(name.replace('.', '-'), '/schemas/' + name, 'contracts', title,
            ('Machine-readable field and format contract.', '可供程序读取的字段与格式约束。'), 'JSON Schema', 'application/schema+json', 1, 'schemas', 'contract')
    if have_candidates:
        for name, title in zip(CANDIDATE_SCHEMAS, [('Candidate observation schema', '候选观察记录规范'), ('Candidate manifest schema', '候选清单规范')]):
            add(name.replace('.', '-'), '/schemas/' + name, 'contracts', title,
                ('Candidate status, public field allowlist and independent observation provenance.', '候选状态、公开字段白名单与独立观察溯源。'),
                'JSON Schema', 'application/schema+json', 1, 'schemas', 'contract')
    if len({item['id'] for item in artifacts}) != len(artifacts):
        raise ValueError('Download artifact identifiers must be unique')
    manifest = {'schema_version': 1, 'catalog_sha256': source_sha,
                'source_repository': 'https://github.com/reacher-z/Awesome-CUA', 'source_catalog': '/downloads/catalog.jsonl',
                'publication_build_info': '/data/build-info.json',
                'count_policy': 'Each count retains its own unit and scope. Artifact populations overlap and must not be added together.',
                'fingerprint_policy': 'SHA-256 and byte size refer to the exact uncompressed file bytes. The manifest does not hash itself.',
                'artifacts': artifacts}
    (destination / 'downloads/manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def data_hub_body(manifest, *, language='en', site_url='https://awesomecua.github.io'):
    zh = language == 'zh'
    def tr(en, cn): return cn if zh else en
    def esc(value): return html.escape(str(value), quote=True)
    def copy_button(value, label, kind='url'):
        return '<button type="button" class="copy-data" data-copy-value="' + esc(value) + '" aria-label="' + esc(label) + '">' + tr('Copy URL' if kind == 'url' else 'Copy', '复制链接' if kind == 'url' else '复制') + '</button>'
    def size(value): return byte_size(value)
    artifacts = manifest['artifacts']
    by_id = {item['id']: item for item in artifacts}
    total = by_id['catalog-jsonl']['count']['value']
    reviewed = by_id['rag-reviewed']['count']['value']
    title = tr('Download the complete data', '数据中心')
    body = ['<section class="data-hub"><div class="library-heading"><div><div class="eyebrow">PEOPLE · RAG · AGENTS</div><h1>', title,
            '</h1></div><a class="library-language" href="', '/data/' if zh else '/zh/data/', '">', 'English' if zh else '中文', '</a></div>',
            '<p class="data-intro">', tr('Choose the complete catalog, retrieval documents, citations, or a focused research subset. Counts and fingerprints come from the published files.',
             '选择完整目录、检索文档、论文引用或专题子集。条数、文件大小和指纹均来自实际导出文件。'), '</p>',
            '<div class="data-stats"><span><strong>', f'{total:,}', '</strong> ', tr('active resources', '条当前资源'), '</span><span><strong>', f'{reviewed:,}',
            '</strong> ', tr('reviewed resources', '条已审阅资源'), '</span><a href="/downloads/manifest.json">', tr('Complete download manifest', '完整下载清单'), ' ↗</a></div>',
            '<div class="data-clone"><div class="clone-command"><code>', CLONE_COMMAND, '</code>',
            copy_button(CLONE_COMMAND, tr('Copy the Git clone command', '复制 Git 克隆命令'), 'command'), '</div><p><a href="', '/zh/agents/' if zh else '/agents/', '">',
            tr('Agent & RAG guide', 'Agent 与 RAG 指南'), '</a> · <a href="/AGENTS.md">AGENTS.md</a> · <a href="', '/zh/topics/' if zh else '/topics/', '">', tr('Browse topic subsets', '浏览主题子集'), '</a> · <a href="', RELEASES_URL, '">', tr('Versioned snapshots', '版本快照'), '</a></p></div>',
            '<nav class="data-group-nav" aria-label="', tr('Download groups', '下载分组'), '">']
    for group, labels in GROUPS.items():
        body += ['<a href="#downloads-', group, '">', labels[zh], '</a>']
    body += ['</nav><p class="data-boundary">', tr('All-active exports include metadata-only discoveries. Reviewed means source-based catalog curation, not independent experimental reproduction. Counts overlap; do not add them together.',
              '全部当前记录包含仅核实书目的发现项。“已审阅”指目录来源审阅，实验未独立复现。各导出范围交叉，数量不可相加。'), '</p>']
    for group, labels in GROUPS.items():
        body += ['<section class="download-group" aria-labelledby="downloads-', group, '"><h2 id="downloads-', group, '">', labels[zh], '</h2>']
        for item in [entry for entry in artifacts if entry['group'] == group]:
            label = item['title'][language]
            count = item['count']
            body += ['<article class="download-row" data-artifact-id="', esc(item['id']), '"><div class="download-description"><div class="download-name"><h3><a href="', item['path'], '" download>',
                     esc(label), '</a></h3><span class="download-format">', esc(item['format']), '</span></div><p>', esc(item['description'][language]), '</p><span class="download-scope">',
                     SCOPE_LABELS[item['scope']][zh], '</span></div><dl class="download-facts"><div><dt class="sr-only">', tr('Count', '数量'), '</dt><dd>', f'{count["value"]:,}',
                     '<span>', UNITS[count['unit']][zh], '</span></dd></div><div><dt class="sr-only">', tr('File size', '文件大小'), '</dt><dd class="download-size">', size(item['bytes']),
                     '</dd></div></dl><div class="download-actions"><a class="button secondary" href="', item['path'], '" download aria-label="', esc(tr('Download ', '下载') + label + ' · ' + item['format']), '">',
                     tr('Download', '下载'), ' ↓</a>', copy_button(site_url + item['path'], tr('Copy URL for ', '复制链接：') + label + ' · ' + item['format']),
                     '</div><details class="download-fingerprint"><summary>SHA-256</summary><code>', item['sha256'], '</code>', copy_button(item['sha256'], tr('Copy SHA-256 for ', '复制 SHA-256：') + label + ' · ' + item['format'], 'hash'),
                     '</details></article>']
        body += ['</section>']
    body += ['<section class="data-use-notes"><h2>', tr('Keep the source snapshot with your work', '保存所使用的数据快照'), '</h2><p>',
             tr('Keep stable IDs, review states, primary sources, license scopes and record fingerprints when building retrieval systems. Reconcile deletions against the complete snapshot and scope ledger.',
                '构建检索系统时保留稳定 ID、审阅状态、一手来源、许可范围和记录指纹。对照完整快照与范围台账处理被移除的记录。'), '</p><details><summary>', tr('Source catalog SHA-256', '源目录 SHA-256'),
             '</summary><code>', manifest['catalog_sha256'], '</code>', copy_button(manifest['catalog_sha256'], tr('Copy source catalog SHA-256', '复制源目录 SHA-256'), 'hash'), '</details>',
             '<p><a href="', RELEASES_URL, '">', tr('Download a versioned data bundle', '下载指定版本的数据包'), '</a>', tr(' to keep catalog, RAG documents, citations and topic subsets on one recorded snapshot. Releases include file checksums and the source commit.', '，将目录、RAG 文档、引用和专题子集固定在同一份已记录快照上。发布包附带文件校验值和源提交。'), '</p>',
             '<p>', tr('Downloads contain catalog metadata and original annotations. Linked papers, training datasets and weights remain with their publishers. Code, data, weights and document licenses stay separate.',
             '下载包含目录元数据与原创注释。所链接的论文、训练数据和权重由原发布方提供；代码、数据、权重与文档许可分别记录。'), ' <a href="/LICENSE">MIT</a> · <a href="/about/">', tr('Editorial policy', '收录方法'),
             '</a> · <a href="/coverage/">', tr('Coverage ledger', '覆盖台账'), '</a> · <a href="/compare/benchmarks/">', tr('Compare benchmarks', '对比基准'), '</a> · <a href="/compare/datasets/">', tr('Compare datasets', '对比数据集'),
             '</a></p></section><div id="data-copy-status" role="status" aria-live="polite" class="sr-only"></div><div class="data-copy-fallback" hidden><label for="data-copy-value">',
             tr('Select and copy this value', '请选择并复制以下内容'), '</label><input id="data-copy-value" readonly><button type="button" data-dismiss-copy>', tr('Close', '关闭'), '</button></div></section><script type="module" src="/downloads.js"></script>']
    return ''.join(body)
