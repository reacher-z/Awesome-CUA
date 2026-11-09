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
from site_config import SITE
from site_shell import HF_DATASET, ic, star_note
from export_candidates import RECORD_FILE as CANDIDATE_FILE, MANIFEST_FILE as CANDIDATE_MANIFEST, SCHEMAS as CANDIDATE_SCHEMAS, validate_candidate_export


GROUPS = {
    'catalog': ('Complete catalog', '完整目录'),
    'rag': ('RAG documents', 'RAG 文档'),
    'citations': ('Citations', '论文引用'),
    'research': ('Topics and comparisons', '主题与对比'),
    'provenance': ('Sources and review status', '来源与审核状态'),
    'contracts': ('File schemas', '文件规范'),
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
    'active': ('All records', '全部记录'),
    'reviewed': ('Reviewed', '已审核'),
    'reviewed-publication': ('Reviewed, published edition', '已审核出版版本'),
    'recorded-publication': ('Published editions', '出版版本'),
    'archive': ('Raw archive', '原始档案'),
    'provenance': ('Background', '来源与状态'),
    'contract': ('Format', '格式规范'),
    'candidate-observations': ('Unreviewed candidates', '待审候选'),
}
GROUP_HINTS = {
    'catalog': ('Every record in one file', '全部记录，一个文件'),
    'rag': ('Text documents for search indexes and agents', '用于检索索引与智能体的文本文档'),
    'citations': ('BibTeX and CSL JSON for reference managers', '用于文献管理工具的 BibTeX 与 CSL JSON'),
    'research': ('Reviewed subsets, profiles and links between records', '已审核的子集、规格与记录间关联'),
    'provenance': ('Where records came from and what review decided', '记录的来源与审核决定'),
    'contracts': ('JSON Schemas for checking the files', '用于校验文件的 JSON Schema'),
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
         ('Every record, reviewed or awaiting review, with its full source history. One JSON object per line.', '全部记录，含已审核与待审核，附完整来源记录。每行一个 JSON 对象。'), 'JSONL', 'application/x-ndjson'),
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
            ('Every record as a document, with its review status for filtering.', '全部记录的文档，附审核状态以便筛选。') if all_records else
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
            ('Every paper and survey in the catalog, with its review status.', '目录中的全部论文与综述，附审核状态。') if all_records else
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
        ('Exact member IDs and JSONL/citation downloads for every reviewed topic.', '每个已审阅主题的精确成员 ID 与 JSONL、引用下载。'),
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
        ('Links between records that a primary source states, such as a paper and its code.', '一手来源明确说明的记录间关联，例如论文与其代码。'),
        'JSON', 'application/json', len(relationships['relations']), 'relations', 'reviewed')

    sources = read_json('/downloads/sources.json')
    scope_decisions = read_json('/downloads/exclusions.json')
    archive_count = line_count(destination / 'downloads/arxiv-archive.jsonl')
    publication_count = line_count(destination / 'downloads/publications.jsonl')
    add('coverage', '/downloads/coverage.json', 'provenance', ('Coverage ledger', '覆盖台账'),
        ('What each source holds, what has been reviewed and what remains.', '每个来源的收录情况、已审核内容与待处理缺口。'), 'JSON', 'application/json', 1, 'reports', 'provenance')
    add('sources', '/downloads/sources.json', 'provenance', ('Where the scans look', '扫描来源登记'),
        ('Community collections and search sources the scans read to find candidates.', '扫描用于发现候选条目的社区合集和检索来源。'), 'JSON', 'application/json', len(sources), 'sources', 'provenance')
    add('scope-decisions', '/downloads/exclusions.json', 'provenance', ('Scope decisions', '范围审阅决定'),
        ('Why records were left out, with the evidence for each decision.', '记录被排除的原因及每项决定的证据。'), 'JSON', 'application/json', len(scope_decisions['decisions']), 'decisions', 'provenance')
    add('arxiv-archive', '/downloads/arxiv-archive.jsonl', 'provenance', ('Raw arXiv harvest', '原始 arXiv 采集档案'),
        ('Every arXiv snapshot the scans kept, including records later excluded.', '扫描保留的全部 arXiv 快照，包括之后被排除的记录。'), 'JSONL', 'application/x-ndjson', archive_count, 'papers', 'archive')
    add('publications', '/downloads/publications.jsonl', 'provenance', ('Published editions of papers', '论文的出版版本'),
        ('Venue, authors and dates for papers with a recorded published version.', '已记录出版版本的论文的会议或期刊、作者与日期。'), 'JSONL', 'application/x-ndjson', publication_count, 'editions', 'recorded-publication')
    repository_declarations = read_json('/downloads/repository-aliases.json')
    if attach_repository_aliases(rows,repository_declarations) != rows:
        raise ValueError('Repository aliases differ from their catalog owners and evidence')
    add('repository-aliases', '/downloads/repository-aliases.json', 'provenance', ('Former repository names', '仓库旧地址映射'),
        ('Earlier GitHub and Hugging Face names of catalog repositories, matched by repository ID.', '目录中仓库在 GitHub 与 Hugging Face 上的旧名称，按仓库 ID 匹配。'),
        'JSON', 'application/json', len(repository_declarations), 'aliases', 'provenance')
    candidate_files = [destination / 'downloads' / name for name in (CANDIDATE_FILE, CANDIDATE_MANIFEST)]
    have_candidates = any(path.exists() or path.is_symlink() for path in candidate_files)
    if have_candidates:
        if any(not path.is_file() or path.is_symlink() for path in candidate_files):
            raise ValueError('Candidate observations require a complete, safe export pair')
        candidate_manifest = read_json('/downloads/' + CANDIDATE_MANIFEST)
        candidate_rows = validate_candidate_export(candidate_files[0].read_bytes(), candidate_manifest, catalog_bytes=catalog_bytes)
        add('github-candidates', '/downloads/' + CANDIDATE_FILE, 'provenance', ('GitHub candidate repositories', 'GitHub 候选仓库'),
            ('Repositories the scans found, from public API metadata, counted by numeric repository ID. Each one awaits review.',
             '扫描发现的仓库，来自公开 API 元数据，按数字仓库 ID 去重。均待审核。'),
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
                'count_policy': 'Each count retains its own unit and scope.',
                'fingerprint_policy': 'SHA-256 and byte size refer to the exact uncompressed file bytes. The manifest does not hash itself.',
                'artifacts': artifacts}
    (destination / 'downloads/manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def data_hub_body(manifest, *, language='en', site_url=SITE, updated=None, preview=None):
    zh = language == 'zh'
    def tr(en, cn): return cn if zh else en
    def esc(value): return html.escape(str(value), quote=True)
    def copy_button(value, label, kind='url'):
        return '<button type="button" class="copy-data" data-copy-value="' + esc(value) + '" aria-label="' + esc(label) + '">' + tr('Copy URL' if kind == 'url' else 'Copy', '复制链接' if kind == 'url' else '复制') + '</button>'
    artifacts = manifest['artifacts']
    by_id = {item['id']: item for item in artifacts}
    total = by_id['catalog-jsonl']['count']['value']
    reviewed = by_id['rag-reviewed']['count']['value']

    def fact(label, value):
        return f'<div><dt>{label}</dt><dd>{value}</dd></div>'

    def choice(tone, title, blurb, action, facts, also):
        return (f'<article class="data-choice {tone}"><h3>{title}</h3><p>{blurb}</p>{action}'
                f'<dl class="data-facts">{"".join(fact(*item) for item in facts)}</dl><p class="data-also">{also}</p></article>')

    def download_choice(tone, identity, title, blurb, also):
        item = by_id[identity]
        facts = [(tr('Format', '格式'), esc(item['format'])), (tr('Records', '条数'), f'{item["count"]["value"]:,}'), (tr('Size', '大小'), byte_size(item['bytes']))]
        if updated:
            facts.append((tr('Updated', '更新'), f'<time datetime="{esc(updated)}">{esc(updated)}</time>'))
        action = f'<a class="btn btn-primary" href="{esc(item["path"])}" download>{ic("download")}{tr("Download", "下载")} {esc(item["format"])}</a>'
        return choice(tone, title, blurb, action, facts, also)

    def also_link(identity, label):
        return f'<a href="{esc(by_id[identity]["path"])}" download>{label}</a>'

    hf_name = HF_DATASET.rsplit('/datasets/', 1)[1]
    choices = ''.join([
        download_choice('r3-f3', 'catalog-jsonl', tr('Full catalog', '完整目录'),
                        tr('Every record with its sources, topics, licenses and review status.', '全部记录，附一手来源、主题、许可与审核状态。'),
                        tr('Also as ', '也提供 ') + also_link('catalog-json', tr('a JSON array', 'JSON 数组')) + tr(' or ', '或 ') + also_link('catalog-sqlite', tr('a SQLite database', 'SQLite 数据库')) + tr('.', '。')),
        download_choice('r3-f4', 'citations-bib', tr('Papers and citations', '论文与引用'),
                        tr('Reviewed papers and surveys, ready for your reference manager.', '已审核的论文与综述，可直接导入文献管理工具。'),
                        tr('Also as ', '也提供 ') + also_link('citations-csl-json', 'CSL JSON') + tr(', or ', '，或') + f'<a href="{"/zh/papers/" if zh else "/papers/"}">{tr("browse the library", "浏览论文库")}</a>' + tr('.', '。')),
        download_choice('r3-f2', 'rag-reviewed', tr('RAG and agents', 'RAG 与智能体'),
                        tr('Reviewed records as text documents, with citations, evidence and licenses.', '已审核记录的文本文档，附引用、证据与许可。'),
                        also_link('rag-all', tr('All records', '全部记录')) + tr(', or the ', '，或') + f'<a href="{"/zh/agents/" if zh else "/agents/"}">{tr("agent and RAG guide", "Agent 与 RAG 指南")}</a>' + tr('.', '。')),
        choice('r3-f1', 'Hugging Face',
               tr('Load the reviewed catalog in one line of Python.', '一行 Python 载入已审核目录。'),
               f'<a class="btn btn-primary" href="{HF_DATASET}">{ic("hf")}{tr("Open on Hugging Face", "在 Hugging Face 打开")}</a>',
               [(tr('Format', '格式'), '<code>datasets</code>'), (tr('Records', '条数'), f'{reviewed:,}'), (tr('Config', '配置'), '<code>resources</code>'), (tr('Updated', '更新'), tr('Every scan', '随扫描'))],
               tr('Other configs include <code>metadata_only</code> and <code>github_candidates</code>.', '其他配置包括 <code>metadata_only</code> 与 <code>github_candidates</code>。')),
    ])

    def key(text):
        return f'<span class="k">{text}</span>'
    comment = lambda text: f'<span class="c"># {text}</span>'
    prompt = '<span class="p"></span>'
    jq_filter = esc("""jq -r 'select(.kind=="benchmark" and .review_status=="curated") | .name'""")
    rag_filter = esc("""jq '{id, text: .text[:120], metadata: (.metadata | keys)}'""")
    snippets = (
        ('curl', 'curl + jq', comment(tr('Names of every reviewed benchmark', '所有已审核评测基准的名称')) +
         f'\n{prompt}curl -s {site_url}/downloads/catalog.jsonl \\\n  | {jq_filter}\n\n' +
         comment(tr('Reviewed papers as BibTeX', '已审核论文的 BibTeX')) + f'\n{prompt}curl -sO {site_url}/downloads/citations.bib\n\n' +
         comment(tr('Query the catalog with SQL', '用 SQL 查询目录')) + f'\n{prompt}curl -sO {site_url}/downloads/catalog.sqlite\n{prompt}' +
         esc('''sqlite3 catalog.sqlite "select name from resources where kind='dataset' limit 5"''')),
        ('python', 'Python', f"""{key("import")} json, urllib.request

url = {key(chr(34) + site_url + '/downloads/catalog.jsonl' + chr(34))}
rows = [json.loads(line) {key("for")} line {key("in")} urllib.request.urlopen(url)]
reviewed = [r {key("for")} r {key("in")} rows {key("if")} r[{key('"review_status"')}] == {key('"curated"')}]
print(len(reviewed), reviewed[0][{key('"name"')}])"""),
        ('hf', 'Hugging Face', f"""{key("from")} datasets {key("import")} load_dataset

ds = load_dataset({key(chr(34) + hf_name + chr(34))}, {key('"resources"')}, split={key('"train"')})
benchmarks = ds.filter({key("lambda")} r: r[{key('"kind"')}] == {key('"benchmark"')})
print(benchmarks[0][{key('"name"')}], benchmarks[0][{key('"url"')}])"""),
        ('rag', 'RAG', comment(tr('One retrieval document: its text and metadata fields', '一份检索文档：文本与元数据字段')) +
         f'\n{prompt}curl -s {site_url}/downloads/rag-documents.jsonl \\\n  | head -n 1 | {rag_filter}'),
    )
    tabs = ''.join(f'<button class="tab" type="button" role="tab" id="dt-{name}" aria-controls="dp-{name}" aria-selected="{"true" if number == 0 else "false"}" tabindex="{0 if number == 0 else -1}">{label}</button>'
                   for number, (name, label, _) in enumerate(snippets))
    panels = ''.join(f'<pre id="dp-{name}" role="tabpanel" aria-labelledby="dt-{name}" tabindex="0"{" hidden" if number else ""}><code>{code}</code></pre>'
                     for number, (name, _, code) in enumerate(snippets))
    record_window = ''
    if preview:
        lines = ',\n'.join(f'  {key(chr(34) + name + chr(34))}: {esc(json.dumps(value, ensure_ascii=False))}' for name, value in preview['record'].items())
        record_window = (f'<div class="window term data-record"><div class="titlebar"><span class="lights" aria-hidden="true"><i></i><i></i><i></i></span><div class="address">{ic("lock")}<output><b>awesomecua.com</b>{esc(preview["path"])}</output></div></div>'
                         f'<pre tabindex="0"><code>{{\n{lines}\n}}</code></pre>'
                         f'<div class="panel-foot"><span>{tr(f"{len(preview["record"])} of {preview["fields"]} fields. ", f"显示 {preview["fields"]} 个字段中的 {len(preview["record"])} 个。")}<a href="{esc(preview["path"])}">{tr("Full record", "完整记录")}</a></span></div></div>')
    agent_links = (f'<a href="{"/zh/agents/" if zh else "/agents/"}">{tr("Agent and RAG guide", "Agent 与 RAG 指南")}</a><a href="/AGENTS.md">AGENTS.md</a><a href="/llms.txt">llms.txt</a>'
                   f'<a href="{"/zh/topics/" if zh else "/topics/"}">{tr("Topic subsets", "专题子集")}</a>')
    command_window = (f'<div class="window term"><div class="titlebar"><span class="lights" aria-hidden="true"><i></i><i></i><i></i></span><div class="address">{ic("lock")}<output><b>awesomecua.com</b>/downloads/</output></div></div>'
                      f'<div class="tabs" role="tablist" aria-label="{tr("Ways to use the data", "使用数据的方式")}">{tabs}</div>{panels}'
                      f'<div class="panel-foot"><span class="data-agent-links">{agent_links}</span><button class="btn btn-ghost js-only" type="button" data-copy-panel>{ic("copy")}{tr("Copy", "复制")}</button></div></div>')

    groups = []
    for group, labels in GROUPS.items():
        files = [entry for entry in artifacts if entry['group'] == group]
        rows = []
        for item in files:
            label = item['title'][language]
            count = item['count']
            rows.append(''.join([
                '<article class="data-file" data-artifact-id="', esc(item['id']), '"><div class="data-file-main"><h3><a href="', item['path'], '" download>', esc(label), '</a></h3><p>',
                esc(item['description'][language]), '</p></div><dl class="data-file-facts"><div><dt class="sr-only">', tr('Format', '格式'), '</dt><dd class="data-format">', esc(item['format']),
                '</dd></div><div><dt class="sr-only">', tr('Review scope', '审核范围'), '</dt><dd class="data-scope">', SCOPE_LABELS[item['scope']][zh], '</dd></div><div><dt class="sr-only">', tr('Count', '数量'),
                '</dt><dd>', f'{count["value"]:,}', ' ', UNITS[count['unit']][zh], '</dd></div><div><dt class="sr-only">', tr('File size', '文件大小'), '</dt><dd>', byte_size(item['bytes']),
                '</dd></div></dl><div class="data-file-actions"><a class="copy-data" href="', item['path'], '" download aria-label="', esc(tr('Download ', '下载') + label + ' · ' + item['format']), '">', tr('Download', '下载'), '</a>',
                copy_button(site_url + item['path'], tr('Copy URL for ', '复制链接：') + label + ' · ' + item['format']),
                '</div><details class="data-sha"><summary>SHA-256</summary><code>', item['sha256'], '</code>', copy_button(item['sha256'], tr('Copy SHA-256 for ', '复制 SHA-256：') + label + ' · ' + item['format'], 'hash'),
                '</details></article>']))
        groups.append(''.join([
            '<details class="data-group" id="downloads-', group, '"><summary><span class="data-group-name">', labels[zh], '</span><span class="data-group-hint">', GROUP_HINTS[group][zh], '</span><span class="data-group-count">',
            str(len(files)), tr(' files' if len(files) != 1 else ' file', ' 个文件'), '</span></summary><div class="data-group-rows">', ''.join(rows), '</div></details>']))

    return ''.join([
        '<div class="data-hub"><header class="wrap data-head"><h1>', tr('Download the data', '下载数据'), '</h1>',
        '<p class="data-intro">', tr('Every record links to its primary source and states its review status. Choose what you need.', '每条记录都链接一手来源并标明审核状态。选择你需要的数据。'), '</p>',
        # Headline: curated resources; the rest of the complete catalog is labelled as awaiting review, never added in.
        '<div class="data-stats"><span><strong>', f'{reviewed:,}', '</strong> ', tr('reviewed records', '条已审核记录'), '</span><span><strong>', f'{total - reviewed:,}', '</strong> ', tr('catalog records awaiting review', '条目录记录待审核'),
        '</span><a href="/downloads/manifest.json">', tr('File list as JSON', '文件清单 JSON'), '</a><a href="', '/data/' if zh else '/zh/data/', '">', 'English' if zh else '中文', '</a></div></header>',
        '<section class="wrap data-choices-wrap" aria-labelledby="data-choose"><h2 class="sr-only" id="data-choose">', tr('Choose a download', '选择下载内容'), '</h2><div class="data-choices">', choices, '</div>', star_note(zh, live=True), '</section>',
        '<section class="r3-term data-try" aria-labelledby="data-try-h"><div class="wrap"><div class="sec-head"><div><h2 id="data-try-h">', tr('What the data looks like', '数据长什么样'), '</h2><p>',
        tr('One real record from the catalog, and the commands to fetch it.', '目录中的一条真实记录，以及获取数据的命令。'), '</p></div></div><div class="data-try-grid">', record_window, command_window, '</div></div></section>',
        '<section class="wrap data-all" aria-labelledby="data-all-h"><div class="sec-head"><div><h2 id="data-all-h">', tr('All files', '全部文件'), '</h2><p>',
        tr(f'{len(artifacts)} files.', f'共 {len(artifacts)} 个文件。'), '</p></div></div>', ''.join(groups), '</section>',
        '<section class="wrap data-notes" aria-label="', tr('Using the data', '使用数据'), '"><div><div class="data-clone-head"><h3>', tr('Clone the repository', '克隆仓库'), '</h3>',
        copy_button(CLONE_COMMAND, tr('Copy the Git clone command', '复制 Git 克隆命令'), 'command'), '</div><code class="data-clone">', CLONE_COMMAND, '</code></div>',
        '<div><h3>', tr('Pin a version', '固定版本'), '</h3><p><a href="', RELEASES_URL, '">', tr('Tagged releases', '版本发布包'), '</a>', tr(' package the catalog, RAG documents, citations and topic subsets with checksums and the source commit. Keep stable IDs, review states and fingerprints with your work.', '将目录、RAG 文档、引用和专题子集打包，并附校验值与源提交。请随工作保留稳定 ID、审核状态和指纹。'), '</p>',
        '<details class="data-sha"><summary>', tr('Source catalog SHA-256', '源目录 SHA-256'), '</summary><code>', manifest['catalog_sha256'], '</code>', copy_button(manifest['catalog_sha256'], tr('Copy source catalog SHA-256', '复制源目录 SHA-256'), 'hash'), '</details></div>',
        '<div><h3>', tr('Licenses', '许可'), '</h3><p>', tr('Downloads hold catalog metadata and original annotations under <a href="/LICENSE">MIT</a>. Papers, datasets and weights stay with their publishers, and each record states its code, data, weights and document licenses.', '下载内容为目录元数据与原创注释，采用 <a href="/LICENSE">MIT</a> 许可。论文、数据集和权重归原发布方所有，每条记录分别标明代码、数据、权重与文档许可。'), '</p>',
        '<p class="data-more"><a href="/about/">', tr('Editorial policy', '收录方法'), '</a><a href="/coverage/">', tr('Coverage ledger', '覆盖台账'), '</a><a href="/compare/benchmarks/">', tr('Compare benchmarks', '对比基准'), '</a><a href="/compare/datasets/">', tr('Compare datasets', '对比数据集'), '</a></p></div></section>',
        '<div id="data-copy-status" role="status" aria-live="polite" class="sr-only"></div><div class="data-copy-fallback" hidden><label for="data-copy-value">', tr('Select and copy this value', '请选择并复制以下内容'),
        '</label><input id="data-copy-value" readonly><button type="button" data-dismiss-copy>', tr('Close', '关闭'), '</button></div></div><script type="module" src="/downloads.js"></script>'])
