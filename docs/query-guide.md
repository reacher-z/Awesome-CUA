# Search and SQL

Run commands from the repository root. Search is literal, case-insensitive, AND across words. It covers names, original summaries, aliases, authors, curated topics, record ids such as `arxiv:2404.07972` or `github:xlang-ai/osworld`, URLs, arXiv numbers, and recorded publication titles, authors, venues and DOIs. A pasted arXiv, GitHub, or web URL also finds its record after version and path folding; reviewed publisher/PDF/DOI aliases resolve to their canonical paper identity. Text output prints each record's id. Default output is limited to 20 matches; use `--limit 0` for all matches.

```bash
python3 scripts/catalog.py search "GUI grounding" --limit 10
python3 scripts/catalog.py search 2404.07972
python3 scripts/catalog.py search https://github.com/xlang-ai/OSWorld/tree/main
python3 scripts/catalog.py search --kind dataset --environment android
python3 scripts/catalog.py search --kind benchmark --topic safety-security
python3 scripts/catalog.py search --kind product --status curated --json
python3 scripts/catalog.py search "reinforcement" --kind paper --json
```

Environment and topic filters refer to reviewed facets. Bibliography entries with unreviewed taxonomy use `unspecified` and will not appear in an Android filter merely because the title mentions Android. Search the title when investigating those entries.

The [topic directory](https://awesomecua.github.io/topics/) groups reviewed papers, benchmarks, datasets, models, and engineering assets. Its [JSON manifest](https://awesomecua.github.io/downloads/topics.json) records exact member IDs, source snapshot SHA-256 and per-file fingerprints. Use a topic page's JSONL download as `--input` to the RAG or citation exporter for a focused corpus. Topic counts overlap and do not represent independent projects or the total size of a research field.

```bash
python3 scripts/catalog.py build
sqlite3 dist/catalog.sqlite
```

```sql
-- Curated Android datasets.
SELECT r.name, r.url
FROM resources r
JOIN facets f ON f.resource_id = r.id
WHERE r.kind = 'dataset' AND r.review_status = 'curated'
  AND f.facet = 'environments' AND f.value = 'android'
ORDER BY r.name;

-- FTS5 title/description/author search.
SELECT r.name, r.kind, r.review_status, r.url
FROM resource_search s JOIN resources r ON r.id = s.id
WHERE resource_search MATCH 'grounding'
LIMIT 20;

-- Dataset licenses explicitly declared in publisher metadata.
SELECT name, json_extract(record_json, '$.licenses.data.declared') AS declaration
FROM resources
WHERE kind = 'dataset'
  AND json_type(record_json, '$.licenses.data') = 'object';

-- Offerings linked to selected publishers/brands.
SELECT publisher.name AS publisher, offering.name AS offering, offering.kind
FROM relations rel
JOIN resources offering ON offering.id = rel.source_id
JOIN resources publisher ON publisher.id = rel.target_id
WHERE rel.relation = 'published_by'
ORDER BY publisher.name, offering.name;
```

SQLite uses `resources`, `facets`, `relations`, and `resource_search`. The full record is retained in `resources.record_json`. FTS5 syntax differs from the CLI's literal search. Model variant and publisher counts must not be described as counts of independent projects.

## Agent and RAG access

Clone the complete source catalog with `git clone https://github.com/reacher-z/Awesome-CUA.git`. [AGENTS.md](../AGENTS.md) contains executable local-search examples and a citation-preserving retrieval workflow.

Known former GitHub IDs resolve through reviewed [repository identity observations](https://awesomecua.github.io/downloads/repository-aliases.json). For example, `python3 scripts/catalog.py get github:mnotgod96/appagent --json` returns the canonical AppAgent record; pasting the former repository URL into `search` finds the same owner. Use the returned canonical ID for joins and retrieval-store updates. These are dated identity observations, not additional resource records or new content approvals.

For ready-made exports, use the [English data hub](https://awesomecua.github.io/data/) or [中文数据中心](https://awesomecua.github.io/zh/data/). The six groups cover the complete catalog, RAG, citations, topics and comparisons, sources and review status, and schemas. These downloads and the clone are entry points to the same catalog; use the published snapshot's [download manifest](https://awesomecua.github.io/downloads/manifest.json) to select a file by `path`, format, and `scope`.

Check each selected file's actual `count.value`, `count.unit`, `bytes`, and `sha256`, and require matching `catalog_sha256` values across the download, RAG, citation and topic manifests. Counts for resources, retrieval documents, citations and archive records can overlap and must not be added together. A successful file check does not turn metadata-only records into reviewed resources. See the [data dictionary](data-dictionary.md) for the manifest fields and populations.

Use a [tagged release](https://github.com/reacher-z/Awesome-CUA/releases) when a retrieval corpus must remain tied to one version. `awesomecua-data.zip` includes the full catalog, reviewed and complete RAG exports, citations, provenance, schemas and complete topic subsets, with their original relative paths. Check `SHA256SUMS`, then retain `release-manifest.json` and the source commit. Read `downloads/catalog.jsonl` or `downloads/rag-documents.jsonl` within the extracted bundle; clone the source at the recorded commit to use the repository's CLI tools.

```sh
python3 scripts/export_rag.py --output dist/rag-documents.jsonl
python3 scripts/export_rag.py --include-metadata --output dist/rag-all-records.jsonl
```

The default includes reviewed resources; `--include-metadata` includes every active record with its review state intact. Each row contains `id`, `text`, and `metadata`. Keep citation URLs, evidence, dates, recorded arXiv versions, licenses, and `record_sha256` alongside embeddings. Use IDs for upserts and reconcile removed IDs against the full snapshot and scope ledger. The public [RAG manifest](https://awesomecua.github.io/downloads/rag-manifest.json) gives file counts and SHA-256 fingerprints. Embeddings and upstream paper full text are not part of the export.

`metadata_verified` also covers entries held after source reading; it does not imply that every such paper is unread. Recorded holds appear in `pending_editorial` in the [coverage ledger](https://awesomecua.github.io/downloads/coverage.json). They remain outside the default reviewed export until an editorial decision approves them.

### Catalog and RAG field mapping

The complete catalog and RAG exports use different JSON shapes. For an exact source record from `catalog.py get --json` or a resource's `record.json`, use the catalog column below.

| Meaning | Catalog record | RAG document |
| --- | --- | --- |
| Stable resource ID | `id` | `id`, also `metadata.resource_id` |
| Primary citation URL | `details.arxiv_snapshot.versioned_url` when recorded, otherwise `url` | `metadata.source_url` |
| Canonical landing URL | `url` | `metadata.canonical_source_url` |
| Catalog page URL | Added by the exporter | `metadata.citation_url` |
| Recorded arXiv version | `details.arxiv_snapshot` | `metadata.arxiv_snapshot` |
| Review status and provenance | `review_status`, `last_verified_at`, `evidence` | The same keys under `metadata` |
| Source-record fingerprint | Computed by the exporter | `metadata.record_sha256` |

`record_sha256` hashes the source object encoded as UTF-8 JSON with sorted keys, unescaped Unicode, compact `,` / `:` separators and no trailing newline. It does not hash the original JSONL line or the upstream paper. Use `scripts/export_rag.py` to obtain the fingerprint with the matching record. Preserve the primary source URL when citing findings; the catalog page supplies the annotation and review context.

Track export-manifest fingerprints as well: a generator or text-policy change can update retrieval text while its source-record fingerprint remains unchanged.

## Exact identity and reviewed connections

```sh
python3 scripts/catalog.py get arxiv:2404.07972 --json
python3 scripts/catalog.py get arxiv:2404.07972 --related --json
```

Plain lookup returns the full active record. Related lookup wraps it with reviewed incoming and outgoing relationships and the original evidence URL for each assertion. Mere mentions are excluded. Unknown identifiers and scope-excluded identifiers have distinct nonzero exit codes; exclusions return a reason and ledger reference instead of an active record.

## Bibliography exports

```sh
python3 scripts/export_citations.py --format bibtex --output dist/citations.bib
python3 scripts/export_citations.py --format csl-json --output dist/citations.csl.json
```

Reviewed papers and surveys are exported by default; `--include-metadata` explicitly includes unreviewed bibliography entries. Individual paper records also provide `citation.bib` and `citation.csl.json`. Original authors and paper-version URLs are retained. Missing venue or DOI metadata is not inferred from an arXiv ID.

Select a recorded publication edition explicitly when you need its formal venue, authors, and date:

```sh
python3 scripts/export_citations.py --edition publication --format csl-json --output dist/publication-citations.csl.json
python3 scripts/catalog.py search "10.1145/3126594.3126651" --json
```

The default citation for an arXiv identity retains its preprint edition. The publication edition can have a different title, author list, or date. Publisher-only records use their publication in either mode. Year-only and month-only dates remain partial; `published_at` can be null even when `details.publication.date_parts` records a known year. Publication exports include only records with this source-backed edition.
