# Search and AI discovery

The objective is to make accurate public resources discoverable, readable, and citable. Search submission, crawl access, indexing, ranking, and AI citation are separate states. This repository does not claim that a configuration guarantees any of them.

## Implemented discovery surface

- `/catalog/`, `/papers/`, `/categories/<kind>/`, `/guides/`, `/data/`, `/coverage/`, and `/about/` return complete textual HTML without running JavaScript.
- Every resource has a stable `/resources/<id-slug>/` URL and an `index.md` companion. Curated entries are indexable. Metadata-only entries stay accessible with `noindex,follow` until relevance is reviewed.
- Canonical URLs, descriptive titles, visible summaries, ordinary anchor links, breadcrumbs, and JSON-LD describe the content actually shown.
- The catalog download page uses `Dataset`/`DataDownload`; paper entities retain their original authors and dates. Catalog authorship is never substituted for research-paper authorship.
- The XML and plain-text sitemaps contain the same indexable HTML pages. It omits artificial build-time `lastmod` values; a source retrieval date is not a page-modification date.
- `robots.txt` allows Googlebot, bingbot, OAI-SearchBot, PerplexityBot, and Claude-SearchBot. The existing general access policy is retained. Search access and model-training access are different controls.
- `llms.txt`, `llms-full.txt`, and an Atom feed provide optional navigation and machine-readable annotations. They are not mandatory AI-ranking mechanisms.
- The homepage `WebSite` node names the site's alternate names (`Awesome-CUA`, `Awesome Computer-Use Agents`) and declares a `SearchAction` for `/?q=<terms>`, the query the catalog app reads. Every page links `/opensearch.xml`, which gives browsers the same search URL. Google no longer shows a sitelinks search box, so neither is a ranking signal.
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

Google Search Console is the authority for property verification, sitemap processing, URL inspection, and actual indexing. After deploying the tested build, submit `https://awesomecua.github.io/sitemap.xml` and inspect the homepage and a representative resource page. A submission-success message is not an indexing confirmation.

IndexNow is a separate notification channel for participating engines, not a Google submission endpoint:

```bash
python3 scripts/submit_indexnow.py          # dry run; local accepted state defaults to .cache/
# To continue from the public website's accepted state, first update its checkout:
git -C .cache/github-pages-publish pull --ff-only
python3 scripts/submit_indexnow.py --state .cache/github-pages-publish/.indexnow/state.json
# Add --submit only after the exact tested build is live.
```

The script compares page-content hashes with the last accepted state. It submits new or changed indexable pages and previously accepted pages that were removed or changed to `noindex`. Newly discovered metadata-only pages are excluded. An unchanged build sends no network request. Before any submission it verifies the public key file, the exact live search manifest, and agreement between the local sitemap and indexable pages.

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
