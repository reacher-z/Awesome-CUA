# Maintenance

Ordinary builds are offline and deterministic. Public-source discovery is scheduled three times a day and can also be run manually. No paid API, model inference, login, or private data is required for discovery.

The source workflow runs at **00:17, 08:17 and 16:17 UTC**, evenly spaced eight hours apart. Website publication runs at **01:47, 09:47 and 17:47 UTC**, 90 minutes after each scan slot. This leaves a buffer beyond the scan job's 45-minute timeout for checks and dispatch; it is not an execution dependency, and publication retains its own quality gate. GitHub can delay or drop scheduled jobs under load; [the status page](https://awesomecua.github.io/updates/) records actual completed runs and links to their logs. Because of that, `.github/workflows/freshness.yml` runs `python3 scripts/scan.py --check-freshness` every three hours. The check fails when neither `data/scan-status.json` nor `data/scan-history.jsonl` records a successful or partial scan that finished within `max_scan_age_hours` (10, set in `data/scan-config.json`): eight hours between the scheduled slots plus two hours of slack. A failed check adds a `Stale scan` error annotation and GitHub sends its failure notice, and a separate job then dispatches a recovery scan on `main` instead of waiting for the next slot. The check reads only the committed files and writes nothing. Both workflows can be dispatched manually for recovery. A scan dispatched from any branch other than `main`, or with `dry_run` set, runs every check and uploads its evidence but commits nothing.

```bash
python3 scripts/scan.py
```

One scan attempts to refresh all registered discovery documents and the Hugging Face paper searches, obtains a recent arXiv query result, verifies missing paper identities, rebuilds the catalog, and validates it. New rows remain metadata-only or candidates. Existing-paper changes are proposed for review instead of overwriting retained metadata. Partial source failures are recorded explicitly; a failed build or validation prevents publication. A partial scan still commits its verified data, and each recorded gap, such as an HTTP 429, appears in the job log, the run's step summary and as a warning annotation. After `max_consecutive_partial` partial scans in a row (4, set in `data/scan-config.json`), a separate job fails the run so GitHub sends its failure notification.

The optional [public GitHub candidate metadata scanner](public-candidate-scan.md)
is a separate, bounded pilot path. It records public numeric repository identities
and resumable creation-date search shards in ignored cache, without approving
resources or changing the active catalog. It is not part of the scheduled scan;
integration must first share the scheduler's request and time budgets.

The committed `data/paper-discovery-queries.json` registry defines 32 Hugging Face hybrid searches, each with an 80-result window. The topics include desktop and mobile platforms, professional software, grounding, data, learning, memory, safety, accessibility, and Chinese-language discovery. All three daily scans run the registry. `data/paper-discovery-status.json` records the current pass, each query's receipt, successful/failed/deferred states, unique identifiers, and new candidate contributions. Ranked windows and their overlaps do not establish complete coverage. Per-query new counts depend on query order; the pass total is deduplicated.

Successful query results replace only that query's current candidate occurrences. Failures or malformed responses retain prior occurrences without borrowing an old success for the current scan. A completed query is persisted before the next request. On HTTP 429, remaining queries for that provider are explicitly deferred. arXiv harvest also stops after a 429; a rate-limited recent query defers the same scan's harvest. Unresolved candidates remain queued for later verification.

Sources can declare `parser: huggingface_models` for a public publisher index on the official Hub API. This requires an author and a limit of at most 100 entries. Model IDs are converted into candidate URLs; namespace membership does not establish GUI relevance, release completeness, licensing, or a separate model entity. Invalid response shapes and unexpected publishers fail the source pass without erasing earlier occurrences.

The scheduled arXiv query uses a 14-day first-submission window ending at the current UTC midnight, with a configured limit of 500 results. Its query, time bounds, reported population, pagination receipts, and completeness are recorded in `data/recent-paper-search.json`. It discovers recent submissions; it does not refresh revisions of every historical paper. Targeted maintenance through the other ingestion commands is separate from this coverage claim.

A complete successful recent query can be reused by later scans in the same UTC day. Reuse requires the same query and bounds, matching unique and reported counts, no warnings, and successful page receipts with valid hashes and retrieval times in that UTC day. A genuine zero-result Atom feed is eligible. Failed requests, malformed feeds, changing pagination totals, partial results, and capped incomplete searches are not eligible and can be retried on a later scan. The scan phase reports `cache_used` and the original `source_retrieved_at` when reused.

UTC-day reuse is the repository's cache policy, following the API's recommendation to cache identical queries within a daily publication cycle. The official date-query syntax uses GMT. [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html) All three scheduled workflow runs continue, and discovery documents and Hugging Face searches still refresh on each run even when the recent arXiv query is reused.

The discovery registry includes first-party release pages as well as research collections. Refreshing a release page can discover newly linked code, data, or checkpoints, but does not approve those assets or rewrite their reviewed specifications. Announced releases such as CarryOn and GraceBench remain in the editorial queue until the recorded release gap is resolved and reviewed.

```bash
# Re-fetch the declared discovery documents and update provenance.
python3 scripts/catalog.py discover --refresh

# Fetch missing arXiv identities. Requests are batched and spaced.
python3 scripts/catalog.py harvest

# Run the recorded title query; inspect its manifest for pagination completeness.
python3 scripts/catalog.py search-arxiv

# Refresh first-party evidence for editorial proposals.
python3 scripts/catalog.py verify --refresh
python3 scripts/catalog.py enrich

# Refresh and enrich only the named entries; repeat --id for several.
python3 scripts/catalog.py verify --refresh --id github:xlang-ai/osworld
python3 scripts/catalog.py enrich --id github:xlang-ai/osworld

# Review changed snapshots before updating editorial approval digests.
python3 scripts/catalog.py build

# Advisory: list curated summaries over 220 characters, without a terminal period, or with superlatives. Never fails.
python3 scripts/catalog.py lint

# Run the same checks as CI, in order; see "Maintain and verify" in the README.
.venv/bin/python scripts/catalog.py validate
.venv/bin/python scripts/catalog.py build --check
.venv/bin/python -m unittest discover -s tests -v
node --test tests/web.test.mjs
.venv/bin/python scripts/build_site.py
```

`--limit` bounds a harvest or search; it does not select editorial entries. Search manifests explicitly report incomplete pagination. Successful responses are cached; failed requests are recorded separately and never overwrite the last successful response. A failed refresh remains a failure in the latest run manifest. Re-running without `--refresh` can reuse an older successful cache response, retaining its original retrieval timestamp.

`--id <catalog id>` restricts `verify` and `enrich` to the editorial entries with that ID, which is the entry's `id` when given, otherwise its URL's identity ([Editorial input](editorial-input.md#resource-id)). It can be repeated. Every other receipt in `primary-evidence.jsonl` and row in `enrichment.jsonl` is written back unchanged, so adding or correcting one resource neither refetches the whole editorial list nor restamps every retrieval time. An ID that no editorial entry has stops the command before any request or write.

`enrich` reads each primary-evidence body from the local `.cache/http/` and uses it only when its SHA-256 equals the recorded receipt. A missing or different body (a fresh clone, another machine, or receipts pulled from CI) leaves that record's previous enrichment untouched and is reported as `STALE`; run `verify` on the same machine first. A LICENSE request that fails with anything other than 404 keeps the previously recorded code license.

`harvest`, `search-arxiv`, and the scheduled recent search all use the same revision-proposal path for known IDs, including manual `--refresh` calls. Comparisons cover title, authors, publication/update dates, Atom version, exact submission/update timestamps, and the normalized abstract digest. A changed date-only field is not required: a new version or abstract can be detected within the same day. The retained archive row and its original receipt stay in place until a source-backed decision reconciles the proposal.

Inspect `data/metadata-updates.jsonl` before accepting new metadata. `metadata_change_pending` identifies a confirmed field difference; `metadata_revalidation_pending` identifies an observation whose missing, incomplete, or unsupported baseline prevents a confident comparison. A proposal may also carry an uncertainty reason alongside confirmed differences. Review its `changes`, `observed_snapshot`, source evidence, and first/last observation times. A proposal clears itself when a later complete observation matches the retained record again, for example after a transient incomplete Atom entry or a reverted upstream change; a remaining proposal therefore reflects the latest observation. Accepting revised bibliographic facts does not itself approve an old editorial summary for the new paper version. Reconcile editorial and scope decisions against the evidence actually reviewed.

The snapshot schema and field meanings are documented in [methodology](methodology.md#paper-versions-and-revision-proposals). For older rows, recover a baseline from the original response cache with the offline backfill tool:

```bash
# Validate the complete archive and report a plan without changing files.
python3 scripts/backfill_arxiv_snapshots.py

# Apply only after the original-receipt validation succeeds.
python3 scripts/backfill_arxiv_snapshots.py --write
```

The completed migration recovered snapshots for 1,764 retained records. The tool makes no network requests. It checks every original `arxiv_api` receipt's SHA-256, requires one matching entry per paper, checks retained title/authors/dates, and requires multiple receipts to agree. Missing or conflicting evidence blocks the whole write. Existing snapshots must match the original evidence; they are never replaced with a new baseline. A write adds the snapshot and its evidence-support label, preserves record order and existing facts, and atomically replaces the file only if the input has not changed during validation. Repeating the tool on an already completed archive is a no-op.

Every editorial entry binds to a `reviewed_sha256`. If an upstream page changes, rerun the editorial review, fix names/taxonomy/notes as needed, and copy the new digest and record the review time in `reviewed_at` only after inspection. [Editorial input](editorial-input.md) documents every key of an editorial entry. A changed or unresolved entry remains in the review queue until this is done. HTTP success and keyword matching do not grant editorial approval.

`.github/workflows/scan.yml` performs discovery and commits validated metadata using its own repository-scoped `GITHUB_TOKEN`. Before committing, it runs the same validation, tests and website build as Catalog quality and refuses to commit if any tracked or untracked change falls outside the committed paths. A push made with `GITHUB_TOKEN` starts no `push` workflow, so a separate `dispatch_quality` job then dispatches Catalog quality on the new `main` commit. Only that job, which checks out nothing, has `actions: write`; the scan job has only `contents: write`. No checkout saves credentials (`persist-credentials: false`), so the dependency install, the scan, its tests and the site build never see a push-capable token: only the commit steps receive `github.token`, and they pass it to `git push` and `git pull` alone as a per-command HTTP header. The publication workflow's commit steps do the same. If `main` moves during a scan, the commit step rebases onto it, rebuilds and validates the generated files from the combined inputs, and retries the push up to three times; a conflicting change stops the run with an error annotation and pushes nothing. The public site's `publish.yml` independently checks out this public source, validates and builds it, updates the website snapshot, and deploys through the GitHub Pages Actions API. Its snapshot and search-receipt commits are likewise rebased onto the latest website `main` before a rejected push is retried. No cross-repository personal access token is required. The publication workflow source is maintained in `automation/publish.yml`; install workflow changes explicitly with `prepare_publication.py --install-workflow` during authorized maintenance. [Manual publication](website.md#manual-publication) lists the checkouts it needs, its flags, and what it deletes or rewrites.

`data/scan-status.json` records the latest completed attempt; `data/scan-history.jsonl` retains the most recent 180 receipts. One scheduled scan shares **180 network-attempt reservations and 600 seconds** across discovery documents, Hugging Face searches, recent arXiv search, metadata harvest, and GitHub candidate observations. `network_max_requests` and `network_max_seconds` in `data/scan-config.json` set these round limits. Retries and followed redirects each consume a reservation; an intact successful cache hit consumes none. Budget deferral never becomes a successful empty response and preserves the last verified response and records.

`scripts/network_budget.py` stores the round ledger under ignored `.cache/scan-rounds/` and passes its path and round ID to sequential child processes. Each reservation is atomically saved before I/O. If a process is interrupted between reservation and response, that attempt stays conservatively charged and is reported as unknown; the ledger does not prove that the server received it. The ledger stores provider names, phases and URL hashes, not credentials, request URLs, headers or bodies. A completed scan exposes the budget totals, provider cooldowns and ledger fingerprint in its status/history. The raw local budget ledger is not a new catalog source or a durable candidate cursor.

Every network phase has an outer subprocess timeout capped by the same remaining round deadline, including the recent arXiv search. This bounds a stalled transfer as well as new request starts; a socket timeout alone is not a total-transfer deadline. Spacing and retry waits recheck the deadline before another attempt. HTTP 429 and header-signaled rate-limit 403 stop requests to that provider for the rest of the round. A new round reads UTC cooldowns from the completed scan status available in its checkout. If a fatal error, failed quality gate or failed push prevents that status from being committed, the new cooldown may survive only in the run's evidence artifact; a fresh Actions checkout does not automatically restore it. Other providers may continue within the shared limits. The recent search still reuses only complete same-UTC-day snapshots.

Offline build and validation retain separate 180-second phase limits; the network budget does not consume their time allocation. The three-daily workflow schedule and 45-minute job timeout are unchanged, leaving time for the remaining quality checks and commit. A scan writes a `running` receipt when it starts and replaces it when it finishes; a receipt still marked `running`, for example in a cancelled run's evidence artifact, belongs to a run that ended before writing its result. Workflow failures before a valid receipt are visible in GitHub Actions and its uploaded evidence artifact. Review the run timestamps, not just the presence of a status file.

The shared budget is optional for standalone catalog commands. The scheduled GitHub candidate phase runs after the four existing network phases and before offline catalog build/validation. Its local limits are **30 GETs, 220 seconds and at most five existing-candidate requests**; all requests also consume the same round allowance. Ten seconds of the phase allowance are reserved for validating and staging the result. Exhausting the earlier phases' allowance defers candidates without starting another request budget. The configured nine precise interface/automation topics are an allowlist, not an assertion that every returned repository belongs in the catalog. Existing query cursors and epochs remain auditable; new topic coverage is added with historical backfill rather than resetting old cursors.

`scripts/scan_candidate_stage.py` restores `data/github-candidates.jsonl`, `data/github-candidates-manifest.json` and their bound `data/github-candidate-progress.json` cursor checkpoint into a new ignored runtime directory. It replays newly fetched SHA-bound bodies before staging a new public snapshot, while preserving already validated historical observations without requiring their old raw API cache. It never writes `data/`. The parent requires a complete result for the current network round, checks the staged hashes and request accounting, then installs the three validated files only after a successful catalog build. Installation checks the previous file hashes and updates the manifest/checkpoint comparison context to the final catalog bytes; historical observation and input fingerprints remain unchanged. A killed child, missing or invalid receipt, or failed build leaves the durable candidate files unchanged. Bootstrap is an explicit offline maintenance step; missing state is not reconstructed by fetching old responses.

Pending query pages at a local or shared limit are normal bounded progress, not a failed-source alarm. The scan report records candidate observations separately, including requests, unique numeric repository IDs, pending queries, unknown responses and rejection reasons. Actual provider errors and rate limits remain explicit warnings. Candidate counts are not added to active resource, recommendation, citation or RAG counts, and HTTP success grants no editorial approval. See [public candidate scans](public-candidate-scan.md) for the public observation and checkpoint contracts.

After a successful website deployment, the publication workflow notifies IndexNow of changed pages and preserves accepted fingerprints and submission receipts in the website repository's `.indexnow/` directory. Unchanged pages are not resubmitted. HTTP 202 and failures do not advance fingerprints, so a later publication retries the pending changes. See [search discovery](search-discovery.md) for manual use and the distinction between submission and indexing.

Python dependencies are locked with hashes. `requirements-dev.in` lists the direct requirements, and `requirements-dev.txt`, generated from it by pip-tools, pins every transitive dependency to an exact version with its SHA-256 hashes. Every workflow, including the scan and publication jobs that hold a write token, installs it with `pip install --require-hashes`, so a new or replaced upstream release changes nothing until a commit changes the lock file. Dependabot's weekly pip update recompiles the lock. After editing `requirements-dev.in`, regenerate the lock with Python 3.12, the CI version, and commit both files:

```bash
python3.12 -m venv .venv/pip-tools && .venv/pip-tools/bin/python -m pip install pip-tools
.venv/pip-tools/bin/pip-compile --generate-hashes --strip-extras requirements-dev.in
```

For each expansion, prioritize sources or resource kinds with known gaps rather than a raw-count target. Track primary metadata coverage separately from editorial review, protocol completeness, license completeness, and executable reproduction. Keep removed/renamed resources explainable; do not silently substitute a different project with the same name.

Review scope exclusions in `data/exclusion-status.json`. An upstream-change proposal prevents an old exclusion from continuing silently; reconcile the metadata proposal and renew or remove the scope decision after source review. `arxiv_archive_records` counts retained arXiv ingestion records, while `bibliographic_records` counts all active papers and surveys, including publisher-only identities. `arxiv_active_records` is the active arXiv subset. The exclusion ledger and archive are published separately from the active catalog.

Reviewed license decisions can override machine extraction through `reviewed_licenses` on an editorial input. Each scope retains a value (including null for an unresolved conflict), a reason, and evidence URLs bound to retained receipts that explicitly support that license scope. The public record keeps the reason and sources in `details.license_review`. A model-hosting namespace does not imply that an environment archive contains model weights.

Discovery occurrences preserve `receipt_id` and the source URL, SHA-256 and retrieval time in `evidence`; a later failed source run cannot erase that provenance or masquerade as a successful refresh. Backfilling older occurrences requires a matching retained successful receipt. HTTP 429 deferral is scoped to the provider host; unrelated sources can continue. A successful response that yields fewer than half of a source's retained candidates, including an empty body, is recorded as a failed `suspicious shrink` run and keeps the earlier occurrences. After confirming the upstream change, apply it with `python3 scripts/catalog.py discover --refresh --accept-shrink <source-id>`.

## Versioned data releases

The website's downloads always show the latest snapshot, and the `cua-catalog` artifact of a Catalog quality run expires after 90 days. A pinned, citable version is a GitHub release made by `.github/workflows/release.yml`. Releases are cut by hand, and no workflow creates or moves a tag. Tag a `main` commit whose Catalog quality run passed, using the snapshot date as the version, and push the tag:

```bash
git fetch origin
git tag -a v2026.10.17 -m 'Catalog snapshot 2026-10-17' origin/main
git push origin v2026.10.17
```

Push the tag with git, not through the GitHub release form: the form publishes its own release, and the workflow then fails at the publish step. The tag push starts the workflow. Its build job checks out the tag without saved credentials, runs `catalog.py validate` and `build --check`, rebuilds the exports with `catalog.py build` and `build_site.py`, packages the complete data snapshot, and writes asset checksums to `SHA256SUMS`. The release job, the only one with `contents: write`, checks out nothing and runs no repository code. It publishes those files as the release of the existing tag with `gh release create --verify-tag`, which fails rather than create a missing tag. The release notes give the source commit, the coverage time, and the record counts by review state and kind, with the profile and topic counts.

| Asset | Contents |
| --- | --- |
| `awesomecua-data.zip` | All main public data exports and complete topic subsets, including reviewed/all RAG documents, citations, provenance, schemas and manifests, with their relative paths preserved |
| `release-manifest.json` | The source commit, version reference, catalog fingerprint, file inventory and ZIP checksum |
| `catalog.jsonl`, `catalog.json`, `catalog.sqlite` | The active catalog as JSONL, a JSON array, and the SQLite database in the [query guide](query-guide.md) |
| `coverage.json` | The coverage ledger |
| `topics.json` | Reviewed topic memberships with exact resource IDs |
| `benchmarks-profiles.json`, `datasets-profiles.json` | Source-reviewed benchmark and dataset profiles |
| `SHA256SUMS` | SHA-256 of every other asset; check them with `sha256sum -c SHA256SUMS` |

Asset names are the same in every release, so a pinned download is `https://github.com/reacher-z/Awesome-CUA/releases/download/<tag>/awesomecua-data.zip`. The bundle is data-only: its own instructions describe the included paths; repository CLI commands require a source clone at the recorded commit. The site downloads continue to follow newer publications, so compare catalog fingerprints before mixing them with a release.

If a run failed before creating a release, re-run it, or dispatch the workflow on the tag with `gh workflow run release.yml --ref <tag>`; a tag pushed with another workflow's `GITHUB_TOKEN` starts no run and needs this dispatch. Once a release has been published, preserve its tag and assets for existing citations. Use a new version for changed data. Dispatched on a branch, the workflow builds the same files into a `release-assets` artifact without publishing, which previews a release.
