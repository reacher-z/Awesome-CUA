# Search and AI discovery

The objective is to make accurate public resources discoverable, readable, and citable. Search submission, crawl access, indexing, ranking, and AI citation are separate states. This repository does not claim that a configuration guarantees any of them.

## Implemented discovery surface

- `/catalog/`, `/papers/`, `/categories/<kind>/`, `/guides/`, `/data/`, `/coverage/`, and `/about/` return complete textual HTML without running JavaScript.
- Every resource has a stable `/resources/<id-slug>/` URL and an `index.md` companion. Curated entries are indexable. Metadata-only entries stay accessible with `noindex,follow` until relevance is reviewed.
- Canonical URLs, descriptive titles, visible summaries, ordinary anchor links, breadcrumbs, and JSON-LD describe the content actually shown.
- The catalog download page uses `Dataset`/`DataDownload`; paper entities retain their original authors and dates. Catalog authorship is never substituted for research-paper authorship.
- `sitemap.xml` is a sitemap index of four root-level files: `sitemap-pages.xml`, `sitemap-resources.xml` (reviewed non-paper resources), `sitemap-papers.xml` (reviewed papers and surveys, the research library and the survey) and `sitemap-categories.xml` (catalog, categories, topics and comparisons). Together they list exactly the indexable HTML pages, which `sitemap.txt` repeats one URL per line. Metadata-only, scope-excluded and not-found pages are never listed.
- Each `<lastmod>` is the latest recorded data time behind the page, never the build time: a resource page uses its editorial review time (`reviewed_at` in `data/editorial.json`), its `last_verified_at` and its evidence retrieval times, including those of the records listed under its connected assets. A collection page uses the latest such time among the records it summarizes, the coverage and data-hub pages the catalog snapshot (`as_of_utc`), the updates page the latest scan, and the survey its manuscript date. Pages whose text depends on no recorded data, such as the guides, omit `lastmod`. Two builds of the same commit write the same sitemaps.
- Pages with an English and a Chinese version list both, plus `x-default`, as `xhtml:link` alternates in the sitemap. They are generated from the same language map as the pages' `<link rel="alternate" hreflang>` tags, so the two cannot disagree.
- `robots.txt` allows every crawler. Search engines, AI search indexes, user-triggered assistants and AI-training crawlers (including GPTBot, ClaudeBot, Google-Extended, Applebot-Extended and CCBot) are also named in one explicit allow-all group, because a crawler that matches a named group ignores the `*` group. Both groups carry `Content-Signal: search=yes, ai-input=yes, ai-train=yes`, and the `__usage_ai-training` token states a preference in favour of AI training. `CRAWLERS` in `scripts/discovery_files.py` is the one list; its test checks that every token may fetch every path. Search access and model-training access are different controls; this policy grants both.
- `/feed.xml` (Atom) and `/feed.json` (JSON Feed 1.1) carry the same 100 newest reviewed resources of every kind, newest review first. An entry's publication time is its editorial review time. Metadata-only bibliography records and unreviewed candidates are not announced. Every page links both feeds.
- `llms.txt` and `llms-full.txt` provide optional navigation and machine-readable annotations. They are not mandatory AI-ranking mechanisms.
- Headline counts describe curated records only. `data/index.json` carries a `counts` object with the curated total, papers and surveys, other resources and a per-kind breakdown, and reports metadata-only records, unresolved candidate identifiers and GitHub candidate observations separately. These populations overlap and must not be added together.
- Google’s provided verification file is retained at the site root. Do not delete it during future deployments.

## Reproduce and validate

```bash
python3 scripts/discover_papers.py --query 'GUI grounding benchmark' --limit 30
python3 scripts/catalog.py harvest
# Review selected primary abstracts and update editorial records before promotion.
python3 scripts/catalog.py build
python3 scripts/build_site.py
.venv/bin/python -m unittest discover -s tests -v
node --test tests/web.test.mjs
```

Discovery searches are ranked, bounded windows. Their provenance is saved in `data/research-discovery.json`; their results are not editorial endorsement. Titles returned by discovery services may be outdated, so current arXiv metadata controls the bibliographic title.

## Submit and measure

Google Search Console is the authority for property verification, sitemap processing, URL inspection, and actual indexing. After deploying the tested build, submit `https://awesomecua.com/sitemap.xml` to a property for `awesomecua.com` and inspect the homepage and a representative resource page. The verified `awesomecua.github.io` property now only reports the redirects to the canonical domain. A submission-success message is not an indexing confirmation.

IndexNow is a separate notification channel for participating engines, not a Google submission endpoint:

```bash
python3 scripts/submit_indexnow.py          # dry run; local accepted state defaults to .cache/
# To continue from the public website's accepted state, first update its checkout:
git -C .cache/github-pages-publish pull --ff-only
python3 scripts/submit_indexnow.py --state .cache/github-pages-publish/.indexnow/state.json
# Add --submit only after the exact tested build is live.
```

The script compares page-content hashes with the last accepted state. It submits new or changed indexable pages and previously accepted pages that were removed or changed to `noindex`. Newly discovered metadata-only pages are excluded. An unchanged build sends no network request. IndexNow state is per host: after the configured `site_url` moves, accepted state recorded for an origin listed in `former_site_urls` is set aside and every indexable page is submitted for the new host. Before any submission it verifies the public key file, the exact live search manifest, and agreement between the local sitemap and indexable pages.

The website publication workflow runs this notification only after successful deployment, using the exact source revision that built the site. The website repository keeps `.indexnow/state.json` and the most recent 180 outcomes in `.indexnow/submissions.json`. Only HTTP 200 advances accepted page hashes; failed requests and HTTP 202 leave changes pending for the next publication. Search-notification failure does not undo the already deployed website. Local manual receipts default to `data/search-submissions.json`.

HTTP 200 means submission accepted; 202 means key validation pending. Neither proves indexing. The IndexNow key is intentionally public ownership proof, not a login credential. This automation does not submit URLs to Google or claim AI citation.

Use Search Console to track indexed pages, impressions, clicks, canonical selection, and excluded-page reasons. Track observed AI referral traffic or citations separately. Do not use fabricated testimonials, synthetic backlinks, unsupported rankings, or schema unrelated to visible content. No third-party outreach or paid submission service is part of this implementation.

## Official references

- [Google: AI features and your website](https://developers.google.com/search/docs/appearance/ai-features) — normal search eligibility applies; no special AI text file or schema is required.
- [Google: link best practices](https://developers.google.com/search/docs/crawling-indexing/links-crawlable) — discoverable links use anchors with real destinations.
- [Google: dataset structured data](https://developers.google.com/search/docs/appearance/structured-data/dataset) — names, descriptions, and distribution metadata support dataset discovery.
- [Google: sitemap ping deprecation](https://developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping) — use robots.txt and Search Console, not the retired ping endpoint.
- [OpenAI: crawlers](https://developers.openai.com/api/docs/bots) — OAI-SearchBot handles search; GPTBot is a separate training control.
- [Perplexity: crawlers](https://docs.perplexity.ai/docs/resources/perplexity-crawlers) — PerplexityBot supports search discovery.
- [Anthropic: crawler controls](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler) — search and other crawler roles are separate.
- [IndexNow protocol](https://www.indexnow.org/documentation) — public key proof, URL submissions, and response semantics.

The alternate `sitemap.txt` uses Google’s documented one-URL-per-line format. It is an additional discovery channel and parser-independent diagnostic, not a way to bypass indexing policy. Google live URL-test results and sitemap-processing status are recorded separately.
