# AwesomeCUA website

The organization homepage is published at **https://awesomecua.com/**. GitHub Pages redirects the former `awesomecua.github.io` address there, keeping the path and query. The GitHub organization entry point is **https://github.com/AwesomeCUA**.

The website combines a static interactive application with complete HTML resource pages and reading guides. Search, filters, pagination, English/Chinese navigation, source evidence, and downloads use the committed catalog. Unknown resource metadata remains unknown. [Search and AI discovery](search-discovery.md) documents canonical pages, sitemap policy, structured data, and submission receipts.

The bilingual [topic directory](https://awesomecua.com/topics/) connects reviewed papers and assets through their existing topic tags. Each topic has static HTML/Markdown, complete-record JSONL and a matching bibliography. The topic manifest retains source and export fingerprints. These are overlapping catalog views, not a new classification inferred from titles or an assertion of dependencies between related-looking resources.

The [paper library](https://awesomecua.com/papers/) and [中文论文库](https://awesomecua.com/zh/papers/) display connected code, data, models, benchmarks and products directly below each paper. Text labels and distinct colors identify the resource types. Links require a reviewed introduction or documentation relationship supported by primary evidence; shared topics and incidental mentions do not qualify. Each row shows up to three resources, with further links available on the paper's detail page. Connected resources do not increase the paper count.

The [English data hub](https://awesomecua.com/data/) and [中文数据中心](https://awesomecua.com/zh/data/) organize downloads into six groups: complete catalog, RAG documents, citations, topics and comparisons, sources and review status, and schemas. The [download manifest](https://awesomecua.com/downloads/manifest.json) records each listed public export's actual count and unit, scope, exact byte size, and SHA-256 fingerprint. Its `catalog_sha256` connects these artifacts to the same source snapshot used by the RAG, citation and topic manifests. Counts across formats, selections and topics overlap; they must not be summed.

The hub is another entry point to the complete catalog available through `git clone https://github.com/reacher-z/Awesome-CUA.git`. Downloaded records retain their review states, evidence and separate license scopes. The manifest describes generated files, not upstream model weights, training samples or paper full text; its format is defined by [download-manifest.schema.json](../schemas/download-manifest.schema.json).

For repeatable ingestion, the hub and bilingual agent guides also link to [versioned data releases](https://github.com/reacher-z/Awesome-CUA/releases). Each complete data bundle keeps the catalog, RAG documents, citations, provenance, schemas and topic subsets together with their manifests. Its release manifest identifies the source commit and file fingerprints. The website serves the current publication; a tagged bundle preserves the chosen snapshot for a retrieval corpus or report.

The [English research survey](https://awesomecua.com/survey/) is a separately authored working manuscript. Its frozen research inventory and source editions do not change with each catalog scan. It is not an additional catalog resource, a peer-reviewed publication, or a claim that the cited experiments were reproduced. Its bibliography and evidence reading register are linked from the article and `llms.txt`.

The production build copies the reviewed static package in `web/survey/`; it never runs the research builder, fetches papers, or requires historical Git objects. Before copying, `scripts/survey_bundle.py` checks `build-manifest.json`, every listed file's byte size and SHA-256, and every `input_sha256` against the current source checkout. A changed research input requires a fresh reviewed package. The package's frozen `catalog_sha256` is not compared with the moving production catalog.

Update the manuscript through its research builder and review the resulting HTML, bibliography and evidence before replacing `web/survey/` with the complete approved package. Keep the package's `index.html` bytes unchanged during site publication: the survey manifest and search manifest must hash the same final HTML. Only listed root files and immediate `evidence/*.json` companions are copied; unlisted files, raw papers and local caches are not published. The package manifest itself is copied separately, without a circular self-hash. The article has one English canonical page at `/survey/`; bibliography and evidence downloads are not separate sitemap pages.

## Build and preview

```bash
python3 scripts/build_site.py
python3 -m http.server 4173 --bind 127.0.0.1 --directory dist/site
```

Open http://127.0.0.1:4173/. Source files are in `web/`; the deployable static bundle is in `dist/site/`. The bundle includes the search index, resource HTML/Markdown, guides, and JSONL/SQLite downloads. Discovery pages are configured for the root of `https://awesomecua.com/`. Canonical, Open Graph, sitemap, feed and download URLs all derive from `SITE` in `scripts/site_config.py`, so an origin change is made there; deploying under a subdirectory would also require updating internal paths.

```bash
node --test tests/web.test.mjs
.venv/bin/python -m unittest discover -s tests -v
```

The `AwesomeCUA/awesomecua.github.io` repository contains the published static snapshot and a scheduled GitHub Pages Actions workflow. It checks out the public `reacher-z/Awesome-CUA` source, validates it, rebuilds, updates the static snapshot, and deploys the artifact. A scheduled check runs at :25 and :55 past every hour UTC. It compares the source `main` revision with the `source_commit` that the live site serves at `/data/build-info.json` and stops when they match, so an unchanged source builds, commits and deploys nothing. Otherwise it publishes that exact source revision; a committed snapshot whose deployment did not reach the live site is deployed again (see [maintenance](maintenance.md) for the CDN and unreadable-site rules). Website-repository pushes and manual dispatches always publish. Scans run every hour; the next check after a scan commit publishes it. The publication workflow independently validates its checked-out source before deployment. The [update status page](https://awesomecua.com/updates/) links to actual scan receipts.

The custom domain `awesomecua.com` and its enforced HTTPS are repository Pages settings, which Actions deployments keep; the build also writes the domain to `CNAME` so the snapshot records it. DNS for the domain is managed in Cloudflare without proxying: apex `A`/`AAAA` records point to GitHub Pages, `www` is a `CNAME` to `awesomecua.github.io`, and a `CAA` record allows Let's Encrypt, which issues the Pages certificate. GitHub Pages redirects `www.awesomecua.com` and `awesomecua.github.io` to `https://awesomecua.com/` with the same path and query.

The `AwesomeCUA/.github` repository contains the organization profile. Its links lead to the public homepage and public website repository.

Successful deployments also run incremental IndexNow notification. The website repository retains the actual response and accepted page hashes in `.indexnow/`; a failed notification preserves the pending changes without rolling back the deployed site. The organization profile uses the website's live count badge so its counts follow future publications.

The initial browser QA covered desktop and a 390-pixel mobile viewport, catalog/category/platform intersections, detail evidence and license separation, empty results, Chinese UI, and absence of horizontal mobile overflow. The automated tests cover filter behavior, Unicode queries, deep-link state, sorting, metadata review boundaries, and safe rendering of untrusted text/URLs.

## Manual publication

Star counts on the site are build-time values. The publication workflow reads them from the GitHub API into `AWESOMECUA_REPO_STARS` for the build; the browser never calls GitHub. The landing pages `/` and `/zh/` carry the counts in their HTML. Every other page reads them from `/data/site-stamp.json`, so a new star does not rewrite thousands of pages on each scan, and without JavaScript or a count each star link keeps its label.

The website repository's `publish.yml` workflow normally publishes the site. Run `scripts/prepare_publication.py` by hand to install a changed publication workflow from `automation/publish.yml`, to refresh the organization profile, or to inspect what a publication would change. The script edits two local checkouts. It never commits, pushes or deploys.

From the repository root, clone both repositories into the default paths under the ignored `.cache/` directory:

```bash
git clone https://github.com/AwesomeCUA/awesomecua.github.io.git .cache/github-pages-publish
git clone https://github.com/AwesomeCUA/.github.git .cache/github-profile
```

Then build the site and prepare the checkouts, in this order. `prepare_publication.py` copies the built `dist/site/` and reads its `data/search-manifest.json`; without that build it stops before changing either checkout:

```bash
python3 scripts/build_site.py
python3 scripts/prepare_publication.py
```

| Flag | Default | Effect |
| --- | --- | --- |
| `--site-dir` | `.cache/github-pages-publish` | Website checkout to update; it must contain `.git` |
| `--profile-dir` | `.cache/github-profile` | Organization profile checkout; it must contain `.git` unless `--skip-profile` is given |
| `--skip-profile` | off | Leaves the profile alone and does not require its checkout. The publication workflow runs `scripts/prepare_publication.py --site-dir "$GITHUB_WORKSPACE" --skip-profile` |
| `--install-workflow` | off | Copies `automation/publish.yml` to `.github/workflows/publish.yml` in the website checkout |

In the website checkout, the script:

- Deletes the generated files (`index.html`, `index.md`, `record.json` and the citation files) of every page that the checkout's previous `data/search-manifest.json` lists and the new build does not, in any section. It stops before deleting anything if such a page resolves outside the checkout or into a dot folder.
- Deletes generated page files under `resources/`, `categories/`, `guides/`, `topics/`, `zh/topics/` and `badges/` whose page is not in the new manifest, record and citation files that the build no longer produces for a kept resource page, and the exports in `downloads/topics/` of topics that no longer exist. For a removed badge gallery, this includes its four featured-resource SVGs; the separately generated `badges/catalog.svg` count badge and unrelated files are preserved.
- Copies `dist/site/` over the checkout, replacing files of the same name.
- Handles `survey/` through its own file-ownership manifest instead of a recursive directory copy. Before any publication deletion or copy, it verifies the incoming survey and current source fingerprints and validates every old/new survey path. Removed companions are deleted even when `/survey/` remains; removing the page deletes its manifest-owned files. Unlisted files are preserved. Symlinks, escaping paths, conflicting unowned files and manual changes to previously published survey files stop preparation for review rather than being overwritten. An orphaned survey directory omitted from the new search manifest is not republished.
- Adds `.pipeline/`, `.cache/`, `__pycache__/` and `.DS_Store` to `.gitignore` when they are missing.
- Copies the resource issue form to `.github/ISSUE_TEMPLATE/resource.yml`, and the resource, scope-decision and publication-observation schemas to `schemas/`.
- Rewrites `README.md` from `data/coverage.json` and `data/catalog.jsonl`.
- Checks every file in the checkout, outside `.git/`, `.pipeline/` and `.cache/`, for [protected names](maintenance.md#protected-names) and stops with only paths and line numbers if one appears, so the publication workflow commits and deploys nothing.

Unless `--skip-profile` is given, it also rewrites `profile/README.md` in the profile checkout and checks it the same way.

Review both checkouts before committing anything:

```bash
git -C .cache/github-pages-publish status
git -C .cache/github-pages-publish diff --stat
git -C .cache/github-profile diff
```

Commit and push from a checkout only during authorized maintenance. A push to the website repository's `main` starts its publication workflow, which checks out this repository's `main`, validates and rebuilds it, and deploys that build. Your local `dist/site/` is never deployed directly. Pushing a change under `.github/workflows/` needs credentials that are allowed to update workflows.
