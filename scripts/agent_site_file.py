"""The site's agent file, served as /AGENTS.md, /agents.md and /agents.txt: facts and copy-paste commands for coding agents.

The repository's own AGENTS.md (contributor and maintainer instructions) stays in the repository.
"""
from __future__ import annotations

EXAMPLE_ID = 'arxiv-2404-07972'
EXAMPLE_ARXIV = '2404.07972'
ENDPOINTS = ('resources', 'papers', 'categories', 'changes')
FILES = ('AGENTS.md', 'agents.md', 'agents.txt')


def site_agents_md(*, site, counts, snapshot, repo='https://github.com/reacher-z/Awesome-CUA'):
    curated, waiting = counts['curated'], counts['awaiting_review']
    year = snapshot[:4]
    return f'''# Awesome CUA for agents

Awesome CUA (Awesome Computer-Use Agents, {site}/) is a source-backed catalog of computer-use, GUI, browser and mobile agents: {curated["total"]:,} curated resources ({curated["papers_and_surveys"]:,} papers and surveys, {curated["other_resources"]:,} models, datasets, benchmarks, agents, frameworks, tools and products), each reviewed against a primary source. {waiting["metadata_only_records"]:,} metadata-only bibliography records are labeled separately. Snapshot {snapshot}.

## Read one item

Every page has a Markdown twin at `index.md` and every resource its complete record at `record.json`. The resource id is the last path segment of its catalog URL.

```sh
curl -sL {site}/resources/<id>/index.md
curl -sL {site}/resources/<id>/record.json
curl -sL {site}/resources/{EXAMPLE_ID}/index.md
```

Papers carry their arXiv id, so the same item reads through Hugging Face:

```sh
hf papers read {EXAMPLE_ARXIV}
```

Other kinds follow the same pattern: `{site}/categories/<kind>/index.md` where kind is one of model, dataset, benchmark, agent, framework, infrastructure, tool, product, company, learning, survey, paper; `{site}/topics/<topic>/index.md`; `{site}/papers/index.md` (research library, 60 per page).

## Search

```sh
{site}/explore/?q=<query>              # interactive search over every record
curl -sL {site}/api/v1/resources.json  # filter locally, for example with jq
git clone {repo}.git && python3 scripts/catalog.py search "grounding" --kind model --status curated --json
```

## JSON API

```sh
curl -sL {site}/api/v1/index.json       # endpoint list with counts, bytes and SHA-256
curl -sL {site}/api/v1/resources.json   # curated non-paper resources
curl -sL {site}/api/v1/papers.json      # curated papers and surveys
curl -sL {site}/api/v1/categories.json
curl -sL {site}/api/v1/changes.json     # recent changes
curl -sL {site}/feed.json               # 100 newest reviewed resources (Atom: {site}/feed.xml)
```

## Whole-site files

```sh
curl -sL {site}/llms.txt                # index of Markdown pages, llmstxt.org format
curl -sL {site}/llms-full.txt           # every curated record once, compactly
curl -sL {site}/sitemap.xml
curl -sL {site}/downloads/catalog.jsonl # complete catalog, one JSON object per line
curl -sL {site}/downloads/manifest.json # every download with bytes, SHA-256, counts
curl -sL {site}/downloads/rag-documents.jsonl
curl -sL {site}/downloads/citations.bib
git clone {repo}.git
```

Hugging Face mirror: `load_dataset("TIGER-Lab/AwesomeCUA", "resources")`.

## Cite

```bibtex
@misc{{awesomecua{year},
  title        = {{Awesome Computer-Use Agents: a source-backed catalog of computer-use, GUI, browser, and mobile agents}},
  author       = {{{{Awesome CUA}}}},
  year         = {{{year}}},
  howpublished = {{\\url{{{site}/}}}},
  note         = {{Snapshot {snapshot}; code at {repo}}}
}}
```

## Updates

Discovery scans run every 8 hours. Release tags attach versioned data bundles with SHA-256 checksums: {repo}/releases

## Contact

Suggest a resource or report a correction: {repo}/issues/new/choose
'''
