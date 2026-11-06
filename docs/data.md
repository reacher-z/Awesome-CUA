# Use the data

Download the catalog, feeds and RAG documents; the data hub also lists sources, review states and schemas.

- [llms.txt](https://awesomecua.com/llms.txt) - Navigation file for language models.
- [llms-full.txt](https://awesomecua.com/llms-full.txt) - Curated annotations in Markdown.
- Data hub - Catalog, RAG documents, citations, topics, comparisons, sources and schemas in six groups.
- [Catalog JSONL](https://awesomecua.com/downloads/catalog.jsonl) - Complete catalog with one resource per line.
- [Download manifest](https://awesomecua.com/downloads/manifest.json) - Export counts, byte sizes and SHA-256 checksums.
- [Atom feed](https://awesomecua.com/feed.xml) - Research updates as an Atom feed.
- [Hugging Face dataset](https://huggingface.co/datasets/AgPerry/awesome-cua) - Parquet and JSONL mirror, one config per record type, refreshed every 2 hours.
- Agent and RAG guide - Guide for agents and RAG systems.

Clone the complete catalog:

```sh
git clone https://github.com/reacher-z/Awesome-CUA.git
```

[Agent instructions](AGENTS.md) · [Retrieval documents](https://awesomecua.com/downloads/rag-documents.jsonl)

Discovery is scheduled every two hours, at **00:07, 02:07, 04:07, 06:07, 08:07, 10:07, 12:07, 14:07, 16:07, 18:07, 20:07 and 22:07 UTC**. [Actual scan results](https://awesomecua.com/updates/) · [Schedule and safeguards](docs/maintenance.md).

[Read the research survey](https://awesomecua.com/survey/) — Methods, evaluation, human agency, and reusable research assets. English working manuscript with a versioned bibliography and reading register.

## Data files and local queries

Browse the interactive website to search and filter all resources, inspect source evidence, switch between English and Chinese, or download the complete catalog. [Website development and publishing](docs/website.md).

The English data hub and [中文数据中心](https://awesomecua.com/zh/data/) organize public downloads into six groups: complete catalog, RAG documents, citations, topics and comparisons, sources and review status, and schemas. Cloning still gives you the complete source catalog; the hub provides exports from its published snapshot.

The download manifest records each listed export's actual count and unit, scope, byte size, and SHA-256 fingerprint. These are different formats and overlapping views of the catalog, so their counts must not be added together. Compare `catalog_sha256` across manifests before combining files from different downloads.

Reviewed research · [Computer-use agent guides](https://awesomecua.com/guides/) · [Static resource directory](https://awesomecua.com/catalog/) · [Search and AI discovery](docs/search-discovery.md)

- [Catalog JSONL](https://github.com/reacher-z/Awesome-CUA/blob/main/data/catalog.jsonl) - One resource per line, with stable IDs, typed fields, provenance, scoped licenses, and review status.
- [Reference graph](https://github.com/reacher-z/Awesome-CUA/blob/main/data/references.jsonl) - Outbound references from primary sources. `mentions` is a separate relation from `trained_on` and `evaluated_on`.
- [Discovery registry](https://github.com/reacher-z/Awesome-CUA/blob/main/data/sources.json) - Source snapshots and where each identifier was found (see also [candidates](data/candidates.jsonl)).
- [Review queue](https://github.com/reacher-z/Awesome-CUA/blob/main/data/review-queue.jsonl) - Unresolved evidence, unindexed discoveries, and proposals requiring editorial work. Discovered links reviewed as non-resources or as other addresses of indexed resources stay listed with a `resolution` and their reason.
- [JSON Schema](https://github.com/reacher-z/Awesome-CUA/blob/main/schemas/resource.schema.json) - Machine-checkable contracts and coverage accounting (see also [coverage JSON](data/coverage.json)).
- [BibTeX](https://awesomecua.com/downloads/citations.bib) - Reviewed-paper citations with recorded authors, dates, and versions. Each resource page also provides its own `record.json` (see also [CSL JSON](https://awesomecua.com/downloads/citations.csl.json)).

```bash
# Python 3.11+. Search and export require only the standard library.
cd Awesome-CUA
python3 scripts/catalog.py search "grounding" --kind model
python3 scripts/catalog.py search --kind dataset --environment android
python3 scripts/catalog.py search --kind product --status curated --json
python3 scripts/catalog.py get arxiv:2404.07972 --related --json
python3 scripts/catalog.py build
# Creates dist/catalog.sqlite and dist/catalog.json, with no network calls.
python3 scripts/export_rag.py --output dist/rag-documents.jsonl
python3 scripts/export_citations.py --format bibtex --output dist/citations.bib
# Add --include-metadata to include every active record, with its review state intact.
```

Use SQLite to join resources, environment/topic facets, and reviewed relations. See [query examples](docs/query-guide.md). `data/catalog.jsonl` is committed; SQLite and JSON array exports are reproducible local build products.
