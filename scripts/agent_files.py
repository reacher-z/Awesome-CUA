"""Agent-readable Markdown: /llms.txt, /llms-full.txt and Markdown versions of the collection pages.

llms.txt follows https://llmstxt.org/ (H1, blockquote summary, H2 link lists, an `Optional` section last).
Full per-record annotations live beside each page as index.md and are gathered per kind and per research-library
page; llms-full.txt is one compact entry for every curated record, so no single file carries every evidence receipt.
"""
from __future__ import annotations

from publication_metadata import AUTHORS_OMITTED, authors_omitted, record_date_text
from site_data import PAPER_KINDS

# llms-full.txt and the catalog Markdown list non-paper kinds first; papers are the largest group.
FULL_ORDER = ('model', 'dataset', 'benchmark', 'agent', 'framework', 'infrastructure', 'tool', 'product', 'company', 'learning', 'survey', 'paper')
NOTICE = ('Reviews are AI-assisted inspections of primary sources, not reproductions of experiments. Counts are resources, '
          'not independent projects. Code, data, weights and document licenses are recorded separately; unknown values stay unknown.')


def inline(text):
    """One Markdown line: whitespace collapsed, link brackets escaped."""
    return ' '.join(str(text or '').split()).replace('[', r'\[').replace(']', r'\]')


def link(label, url):
    return f'[{inline(label)}]({url})'


def plural(count, one, many=None):
    return f'{count:,} {one if count == 1 else (many or one + "s")}'


def declared_licenses(record):
    parts = []
    for slot, value in record['licenses'].items():
        if value:
            declared = value['declared'] if isinstance(value['declared'], str) else ', '.join(value['declared'])
            parts.append(f'{slot} {declared}')
    return '; '.join(parts)


def compact_entry(record, *, site, page_path, summary, reviewed_at, kind_label):
    """A few lines that identify a curated record and point to its full annotation."""
    lines = ['### ' + inline(record['name']), '', inline(summary), '',
             f'- {site}{page_path} · source: {((record["details"].get("arxiv_snapshot") or {}).get("versioned_url")) or record["url"]}',
             f'- {kind_label} · reviewed {(reviewed_at or "")[:10] or "date not recorded"}'
             + (f' · environments: {", ".join(record["environments"])}' if record['environments'] else '')
             + (f' · topics: {", ".join(record["topics"])}' if record['topics'] else '')]
    if record['kind'] in PAPER_KINDS:
        lines.append('- Published: ' + (record_date_text(record) or 'date not recorded') + ' · '
                     + (AUTHORS_OMITTED[0] if authors_omitted(record) else 'Authors: ' + (inline(', '.join(record['authors'])) or 'not recorded')))
    licenses = declared_licenses(record)
    if licenses:
        lines.append('- Licenses: ' + licenses)
    return '\n'.join(lines)


def kind_markdown(kind, label, records, *, site, snapshot, full_markdown):
    """Markdown version of a category page: every reviewed record of the kind with its full annotation."""
    lines = [f'# Computer-use agent {label.lower()}', '',
             f'> {plural(len(records), "curated record")} of this kind in the AwesomeCUA catalog, each with its complete annotation, primary evidence and license declarations. Snapshot {snapshot}.', '',
             f'HTML page: {site}/categories/{kind}/ · Catalog index: {site}/llms.txt · API: {site}/api/v1/{"papers" if kind in PAPER_KINDS else "resources"}.json', '',
             NOTICE]
    return '\n'.join(lines) + ''.join('\n\n---\n\n' + full_markdown(record, 2).rstrip('\n') for record in records) + '\n'


def paper_hub_markdown(papers, surveys, library, topics, *, site, snapshot):
    """Markdown version of /categories/paper/: a hub into the research-library pages and topics."""
    lines = ['# Computer-use agent research papers', '',
             f'> {plural(papers, "reviewed paper")} and {plural(surveys, "survey")}, listed newest publication first across the research-library pages below. Snapshot {snapshot}.', '',
             f'HTML page: {site}/categories/paper/ · Library: {site}/papers/ · API: {site}/api/v1/papers.json', '', NOTICE, '',
             '## Research library pages', '']
    lines += [f'- {link(f"Page {number}", site + path + "index.md")}: {first} to {last}' for number, path, first, last in library]
    lines += ['', '## Papers by topic', ''] + [f'- {link(f"{name} ({count:,})", site + path + "index.md")}' for name, count, path in topics]
    lines += ['', '## Surveys', '', f'- {link("Surveys", site + "/categories/survey/index.md")}: {plural(surveys, "reviewed survey")}']
    return '\n'.join(lines) + '\n'


def library_markdown(number, pages, records, total, *, site, path_for, full_markdown):
    """Markdown version of one research-library page: the same papers, in the same order, with full annotations."""
    start = (number - 1) * len(records) if number < pages else total - len(records)
    navigation = [link('Previous page', site + path_for(number - 1) + 'index.md')] if number > 1 else []
    navigation += [link('Next page', site + path_for(number + 1) + 'index.md')] if number < pages else []
    lines = [f'# Computer-use research library, page {number} of {pages}', '',
             f'> Reviewed computer-use papers and surveys {start + 1:,} to {start + len(records):,} of {total:,}, newest publication first, with authors, recorded arXiv versions, citation files and primary evidence.', '',
             f'HTML page: {site}{path_for(number)} · ' + ' · '.join(navigation + [link('All pages', site + '/categories/paper/index.md')]), '', NOTICE]
    return '\n'.join(lines) + ''.join('\n\n---\n\n' + full_markdown(record, 2).rstrip('\n') for record in records) + '\n'


def catalog_markdown(kinds, topics, *, site, counts):
    curated = counts['curated']
    lines = ['# AwesomeCUA resource directory', '',
             f'> {curated["total"]:,} curated computer-use agent resources: {curated["papers_and_surveys"]:,} papers and surveys and {curated["other_resources"]:,} other resources. '
             f'{counts["awaiting_review"]["metadata_only_records"]:,} metadata-only bibliography records await relevance review and are not counted.', '',
             f'HTML page: {site}/catalog/ · Catalog index: {site}/llms.txt', '', '## Resource kinds', '']
    lines += [f'- {link(label, site + md_path)}: {plural(count, "curated record")}' for label, count, md_path in kinds]
    lines += ['', '## Topics', ''] + [f'- {link(name, site + path + "index.md")}: {plural(count, "reviewed resource")}' for name, count, path in topics]
    return '\n'.join(lines) + '\n'


def home_markdown(newest, kinds, *, site, counts, snapshot):
    curated, waiting = counts['curated'], counts['awaiting_review']
    lines = ['# AwesomeCUA', '',
             f'> A source-backed catalog of computer-use, GUI, browser and mobile agent research and resources: {curated["total"]:,} curated records '
             f'({curated["papers_and_surveys"]:,} papers and surveys, {curated["other_resources"]:,} models, datasets, benchmarks, agents, frameworks, tools and products), each reviewed against a primary source.', '',
             f'Snapshot {snapshot}. Awaiting review and not counted above: {waiting["metadata_only_records"]:,} metadata-only bibliography records and {waiting["unresolved_candidate_identifiers"]:,} discovered identifiers. {counts["note"]}', '',
             f'HTML page: {site}/ · 中文: {site}/zh/ · Agent index: {site}/llms.txt', '', '## Newest reviewed resources', '']
    lines += [f'- {link(name, url)} — {kind} · reviewed {reviewed[:10]}: {inline(summary)}' for name, url, kind, reviewed, summary in newest]
    lines += ['', '## Browse by kind', ''] + [f'- {link(label, site + md_path)}: {plural(count, "curated record")}' for label, count, md_path in kinds]
    lines += ['', '## Machine-readable access', '',
              f'- {link("Static API", site + "/api/")}: versioned JSON and CSV',
              f'- {link("Complete curated catalog in one file", site + "/llms-full.txt")}',
              f'- {link("Atom feed", site + "/feed.xml")} and {link("JSON Feed", site + "/feed.json")} of newly reviewed resources',
              f'- {link("Data downloads", site + "/data/")}: JSONL, SQLite, RAG documents and citations']
    return '\n'.join(lines) + '\n'


def llms_full(groups, *, site, snapshot, counts, survey_line, kind_files):
    """Every curated record once, compactly, grouped by kind; full annotations stay in the per-kind files."""
    curated = counts['curated']
    lines = ['# AwesomeCUA curated catalog', '',
             f'> All {curated["total"]:,} curated, source-reviewed records of the AwesomeCUA computer-use agent catalog, one compact entry each, grouped by kind. '
             f'Snapshot {snapshot}. Metadata-only bibliography records and unreviewed candidates are excluded.', '',
             'Each entry links its catalog page. Append `index.md` to that URL for the full annotation with evidence fingerprints, or `record.json` for the complete record. '
             'Full annotations by kind: ' + ', '.join(link(label, site + path) for label, path in kind_files) + '.', '', NOTICE]
    if survey_line:
        lines += ['', survey_line]
    for label, entries in groups:
        lines += ['', f'## {label} ({len(entries):,})', ''] + ['\n\n'.join(entries)]
    return '\n'.join(lines) + '\n'


def llms_txt(*, site, counts, kinds, library, topics, api_endpoints, guides, survey_links, releases_url):
    """The /llms.txt index: what the site is and where each Markdown and data entry point lives."""
    curated, waiting = counts['curated'], counts['awaiting_review']
    lines = ['# AwesomeCUA', '',
             f'> Source-backed catalog of computer-use, GUI, browser and mobile agents: {curated["total"]:,} curated resources ({curated["papers_and_surveys"]:,} papers and surveys, '
             f'{curated["other_resources"]:,} models, datasets, benchmarks, agents, frameworks, tools and products), each reviewed against a primary source with evidence, '
             f'review dates and separate license declarations. {waiting["metadata_only_records"]:,} metadata-only bibliography records await relevance review and are labeled separately.', '',
             'Counts are resources, not independent projects. Source review does not reproduce experiments. Code, data, weights and document licenses are separate. '
             'Every resource, category, topic and research-library page has a Markdown version at `index.md` beside it, and every resource page its complete record at `record.json`. '
             'This file is an optional navigation aid, not an indexing requirement or a request to rank this site.', '',
             '## Catalog by kind', '']
    lines += [f'- {link(label, site + md_path)}: {plural(count, "curated record")}' + (f'; {note}' if note else '') for label, count, md_path, note in kinds]
    lines += ['', '## Research library', '',
              'Reviewed papers and surveys, newest publication first, 60 per page with full annotations. The same pages in Chinese: ' + site + '/zh/papers/', '']
    lines += [f'- {link(f"Page {number}", site + path + "index.md")}: published {first} to {last}' for number, path, first, last in library]
    lines += ['', '## Topics', '', 'Reviewed topic membership; resources can belong to several topics, so counts overlap. Chinese topic pages: ' + site + '/zh/topics/', '']
    lines += [f'- {link(name, site + path + "index.md")}: {plural(count, "reviewed resource")}' for name, count, path in topics]
    lines += ['', '## Static API', '', f'Versioned JSON and CSV under {site}/api/v1/; every file carries `version` and `generated_at`.', '',
              f'- {link("API documentation", site + "/api/index.md")}: endpoints, fields, review states and versioning',
              f'- {link("API index", site + "/api/v1/index.json")}: endpoint list with counts, byte sizes and SHA-256',
              f'- {link("JSON Schema", site + "/api/v1/schema.json")}']
    lines += [f'- {link(name + ".json", url_json)} ({link("CSV", url_csv)}): {inline(description)}' for name, url_json, url_csv, description in api_endpoints]
    lines += ['', '## Agent and RAG access', '', '```sh', 'git clone https://github.com/reacher-z/Awesome-CUA.git', '```', '',
              f'- {link("Agent instructions", site + "/AGENTS.md")}', f'- {link("Human and agent guide", site + "/agents/")}', f'- {link("中文指南", site + "/zh/agents/")}',
              f'- {link("Reviewed retrieval documents", site + "/downloads/rag-documents.jsonl")}', f'- {link("All retrieval documents", site + "/downloads/rag-all-records.jsonl")}',
              f'- {link("Export manifest", site + "/downloads/rag-manifest.json")}', f'- {link("Full catalog JSONL", site + "/downloads/catalog.jsonl")}: every active record, including metadata-only ones']
    lines += ['', '## Guides and policies', ''] + [f'- {link(title, site + path)}: {inline(description)}' for title, path, description in guides]
    lines += ['', '## Optional', '',
              f'- {link("Complete curated catalog in one file", site + "/llms-full.txt")}: every curated record once, compactly; full annotations are in the per-kind files above',
              f'- {link("Atom feed", site + "/feed.xml")} and {link("JSON Feed", site + "/feed.json")}: the 100 newest reviewed resources',
              f'- {link("Benchmark protocols", site + "/compare/benchmarks/")} and {link("dataset profiles", site + "/compare/datasets/")}: source-reviewed specifications ({link("benchmarks JSON", site + "/downloads/benchmarks-profiles.json")}, {link("datasets JSON", site + "/downloads/datasets-profiles.json")})',
              f'- {link("Reviewed paper BibTeX", site + "/downloads/citations.bib")}, {link("CSL JSON", site + "/downloads/citations.csl.json")} and {link("citation manifest", site + "/downloads/citations-manifest.json")}',
              f'- {link("Reviewed publication BibTeX", site + "/downloads/publication-citations.bib")}, {link("CSL JSON", site + "/downloads/publication-citations.csl.json")}, {link("publication observations", site + "/downloads/publications.jsonl")} and {link("their schema", site + "/schemas/publication-observation.schema.json")}: default arXiv citations keep the recorded preprint; publication editions use their own title, authors and date',
              f'- {link("Topic manifest", site + "/downloads/topics.json")}: exact reviewed resource IDs, counts, subset URLs and SHA-256 fingerprints; each /downloads/topics/<topic>/ directory serves records.jsonl, citations.bib and citations.csl.json',
              f'- {link("Verified former repository names", site + "/downloads/repository-aliases.json")} and {link("their schema", site + "/schemas/repository-alias.schema.json")}: use the canonical returned ID for retrieval upserts; aliases add no resources',
              f'- {link("Bilingual data hub", site + "/data/")}, {link("中文数据中心", site + "/zh/data/")} and {link("download manifest", site + "/downloads/manifest.json")} ({link("schema", site + "/schemas/download-manifest.schema.json")}): file paths, byte sizes, SHA-256 fingerprints, counts and units; compare catalog_sha256 across manifests before combining artifacts',
              f'- {link("Tagged data releases", releases_url)}: complete data bundles; verify SHA256SUMS and retain release-manifest.json, source_commit and catalog_sha256',
              f'- {link("Hugging Face dataset mirror", "https://huggingface.co/datasets/AgPerry/awesome-cua")}: read-only Parquet and JSONL mirror of these downloads, one config per record type, refreshed every 2 hours. metadata_only and github_candidates are not curated.']
    lines += [f'- {link(label, url)}' + (f': {note}' if note else '') for label, url, note in survey_links]
    return '\n'.join(lines) + '\n'
