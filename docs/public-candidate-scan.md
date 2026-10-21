# Public GitHub candidate metadata scans

This scanner fetches public repository metadata for existing discovery candidates
and precise GUI/browser automation topics. It can run standalone;
`scripts/scan_candidate_stage.py` also provides a bounded scan phase when enabled
in the scan configuration. Python 3.11+ and the standard library are sufficient;
it does not read credentials or require an account.

```sh
# One bounded pilot: at most ten actual, unauthenticated HTTP GETs.
python3 scripts/scan_github_candidates.py \
  --output .cache/github-candidate-scan \
  --max-requests 10 --max-seconds 180 --existing-budget 5 \
  --topic computer-use --topic browser-automation \
  --created-before 2026-10-18

# Resume the same epoch. Omitted topics and dates keep the frozen configuration.
python3 scripts/scan_github_candidates.py \
  --output .cache/github-candidate-scan \
  --max-requests 10 --max-seconds 180 --existing-budget 5
```

The first command's date is an example; choose the intended UTC cutoff when
starting a new epoch. `--created-after` defaults to `2008-01-01`.
`--created-before` defaults to the first run's UTC date and then remains frozen.
Changing the topic set or bounds requires a new output directory. The CLI only
writes beneath this checkout's ignored `.cache/` directory and refuses parent
traversal and symlink paths.

`candidate-metadata.json` is the atomic state and observation ledger. Its schema
is [github-candidate-scan.schema.json](../schemas/github-candidate-scan.schema.json).
It contains input fingerprints, repository records, query shards, request
receipts, run summaries and resume cursors. A repository's official numeric ID
is the counting key. Former public names and repeated query occurrences remain
as provenance, without increasing the unique count. A paper, model, dataset or
separately reviewed monorepo component is not inferred from a repository hit.

Every record has `metadata_status: primary_metadata_observed`,
`review_status: candidate` and `scope: relevance_pending`. It is not an active
catalog record. Descriptions and tags are publisher metadata, not independently
verified capabilities. No license, release availability, paper relation or
editorial approval is inferred. The standalone scanner does not edit `data/`,
rebuild the catalog, publish files, or execute downloaded code. The scheduled
coordinator can adopt a separately validated, sanitized observation snapshot
after the catalog build succeeds.

## Inputs and priorities

Each run records exact SHA-256 fingerprints for `catalog.jsonl`,
`candidates.jsonl`, `primary-evidence.jsonl`, `repository-aliases.json` and
`candidate-reviews.json`, as well as the active and curated counts actually read.
Do not reuse a different checkout's counts or fingerprint when reporting a run.

Existing GitHub candidates without a successful retained primary response are
considered first, ordered by distinct discovery-source count and stable name.
Known repository aliases resolve before requests. `--existing-budget` caps this
phase per invocation; topic shards can use the remaining request budget. Its
cursor persists. An unavailable existing candidate is recorded as an unknown
attempt and the cursor advances, so a permanent 404 cannot block the queue.
There is no automatic repeated probing of that completed seed within an epoch.
If input fingerprints change, a new seed cohort is created, unfinished old seed
cursors are marked `superseded_input`, and previously observed repository data
and search-shard progress remain intact.
Returning to a previously seen input restores that input's own cursor and
supersedes other pending seed cohorts. Its seed count must still match the
retained fingerprint and the current input; a cursor never runs against another
snapshot's candidate list.

Topic choices are constrained by the CLI. Every search uses `is:public
fork:false`, a precise topic, a fixed creation-date interval, `sort=updated` and
`order=asc`. It never performs a broad README search for “computer use.”

## Pagination and limits

A result population over 900 causes the current inclusive creation-date range
to split into two non-overlapping date ranges. Children are persisted immediately
and processed within later budget slots. Metadata already fetched from a parent
remains auditable and deduplicates against its children. A single-day range that
still exceeds the threshold is `blocked_single_day_window`: it needs a reviewed
additional partition strategy, and is not described as covered.

Smaller shards use pages of at most 100 results, never beyond GitHub's ten-page
search window. Each receipt records the API-reported total, returned row count,
`incomplete_results`, exact response SHA-256 and byte count. Changed totals,
duplicate/missing identities, rejected rows, an incomplete result flag and early
empty pages prevent an `observed_pages_exhausted` result. This status means the
observed pages reconcile with the observed total; search ordering and repository
state can change between requests. It is not an immutable snapshot or a claim
of global recall. `finished` describes a run with no pending work, not complete
coverage of GUI automation.

Requests are sequential, at least 6.5 seconds apart, including immediate resume
against the same ledger. The budget counts HTTP attempts, not successful pages;
there are no automatic redirects or retries. The wall-clock budget prevents new
requests and limits each request timeout to the remaining budget (at most 20
seconds). On 429 or a rate-limit 403, the provider stops and a derived cooldown
is retained; unrequested shards remain pending. Other HTTP errors are explicit
unknown attempts. A failed search page keeps its cursor for a later invocation
and cannot masquerade as a prior success.
Standard GitHub rate-limit messages in a 403 JSON body also stop the provider
when rate-limit headers are absent. The body is not retained. The deadline is
checked again after spacing waits, before counting or starting another request.

The scanner is single-writer: do not run two processes against the same output
directory. Atomic state replacement prevents partially written JSON. A request
completed just before an interrupted state write may be fetched again on resume;
numeric-ID deduplication prevents double-counting it.

## Public-data boundary and reporting

The scanner does not read a GitHub token, send authorization/cookies, use
environment proxy credentials, or follow redirects. Each returned row must also
have literal `private=false`, `visibility=public` and `fork=false`, regardless of
the search qualifiers. Missing or contradictory flags reject the row. Canonical
repository URLs and timestamps must be valid; search results must belong to the
requested topic and creation-date range.
A direct repository response must match the requested `owner/name`, ignoring
case, because redirects are not followed. A mismatched 200 response is rejected
and neither its metadata nor raw body is retained.

Only necessary public repository fields are retained in records. Owner/contact
objects, permissions, request headers and credentials are not copied into the
ledger. Unavailable or rejected responses do not expose their unverified request
URL or response body there; receipts retain a request-URL fingerprint, response
fingerprint and reason counts. Exact response bodies are cached by SHA-256 only
when the response parses without any rejected rows. A mixed/private/unknown
response has a receipt but no retained raw body. All raw bodies remain under the
ignored output cache; do not commit them or publish them as downloads.
Resume validation checks both directions of the evidence link: each occurrence
must match its receipt's query, position and accepted repository ID, and every
accepted ID must have a record with a matching occurrence. Existing-candidate
receipts must belong to the same input snapshot as their run. Retained source
URLs must also match their request-URL fingerprints.

Report `after_unique_repositories`, `new_unique_repositories`, input fingerprint,
actual request count, unknown attempts, rejected-row reasons and deferred shards.
Query occurrences and accepted rows can overlap. Neither their sum nor
`reported_total` is the number of independently scanned resources. A large
metadata-observed candidate population still needs relevance and source review;
the scan target does not imply that all candidates belong in the curated catalog.

```sh
PYTHONPATH=tests python3 -S -B -m unittest test_github_candidate_scan -v
# With the repository validation dependency installed, also checks JSON Schema.
PYTHONPATH=tests .venv/bin/python -B -m unittest test_github_candidate_scan -v
```

## Export a frozen observation snapshot

The offline exporter requires an explicitly selected ledger and its retained
primary-response cache. It makes no network requests and does not read the
resumable scan state implicitly:

```sh
python3 -S scripts/export_candidates.py \
  --input .cache/candidate-scan/frozen-round.json \
  --raw-dir .cache/candidate-scan/raw \
  --catalog data/catalog.jsonl \
  --output-dir dist/candidate-observations
```

It replays every accepted occurrence from the actual SHA-named API bytes,
checks the query, numeric repository identity, public/non-fork flags, metadata,
recorded names and observation times, then writes only:

- `github-candidates.jsonl`: one sanitized observation per numeric GitHub
  repository ID, always `candidate` and `relevance_pending`.
- `github-candidates-manifest.json`: the exact observation-file fingerprint,
  source-ledger fingerprint, original input-file fingerprints, observed time
  window, bounded query/round summary, counts and explicit privacy omissions.

The two contracts are
[`github-candidate-observation.schema.json`](../schemas/github-candidate-observation.schema.json)
and
[`github-candidate-observation-manifest.schema.json`](../schemas/github-candidate-observation-manifest.schema.json).
`source_description` and `github_topics` are publisher-supplied text and tags,
not catalog annotations or a relevance classification. Treat them as untrusted
data rather than instructions. `known_names` records observed spellings under
the same numeric ID; it does not replace reviewed catalog alias decisions.

The exporter checks the selected public text fields for credential-shaped
strings, local home paths and URLs containing user information. A suspect
description is replaced with null and its record ID, field and reason are
reported explicitly; the suspect value is never copied into the report.
Sensitive-shaped identity fields block export. These bounded checks do not
claim to detect every possible secret format. Raw owner/contact objects,
permissions, headers, API bodies and local cache paths are never exported.

The observation population has its own `observation_snapshot_sha256`.
`input_fingerprints` describe the files used when scanning; they may predate the
active catalog. `active_catalog_context` separately identifies the catalog
provided for comparison and confers no approval. Counts use **numeric repository
identities**, not independent projects. Candidates can overlap each other’s
queries and the active catalog, and no query total establishes a global CUA count.

After reviewing the sanitized output, maintainers can retain those **two files
only** as `data/github-candidates.jsonl` and
`data/github-candidates-manifest.json`. Do not copy the scan directory or raw
API cache into `data/`. This is an optional durable observation input: a website
build validates both files, preserves the observation bytes and input hashes,
and updates only the manifest’s active-catalog comparison context for that build.
Absent inputs remove the owned optional downloads on the next publication.

When present, the JSONL and manifest appear in the data hub’s **Sources and review
states** group; their schemas appear in **Data contracts**. They are not added to
the active catalog, resource pages, search recommendations, citations, or default
RAG exports. A consumer can ingest them into a separate candidate collection
keyed by `github-repository:<numeric ID>`, preserving review state and evidence.
The catalog CLI and normal RAG exporter continue to consume the active resource
schema, not this separate observation schema.

Public-file validation checks the sanitized contract and fingerprints. It does
not claim to recreate or independently verify historical network responses that
are absent from the downloaded bundle. Re-running the producer requires the
operator’s retained ledger and raw cache.

```sh
.venv/bin/python -B -m unittest discover -s tests -p 'test_candidate_exports.py' -v
```

## Durable progress across fresh checkouts

Scheduled continuation uses a bound three-file snapshot:

- `data/github-candidates.jsonl` contains sanitized public observations.
- `data/github-candidates-manifest.json` describes that observation population,
  its input fingerprints and the current catalog comparison context.
- `data/github-candidate-progress.json` contains only operational configuration,
  input/query/epoch cursors, run summaries and request receipts. It has no
  repository records or descriptions, owner/contact objects, headers, or raw
  API bodies. Its contract is
  [`github-candidate-progress.schema.json`](../schemas/github-candidate-progress.schema.json).

The checkpoint hashes the exact observation and manifest bytes. The manifest
also binds the checkpoint's state digest, without creating a circular file hash.
`state_sha256` hashes UTF-8 JSON with sorted keys, compact comma/colon separators,
unescaped Unicode and one trailing newline. This differs from an epoch migration's
`source_state_sha256`, which uses the scanner's canonical JSON without a trailing
newline, and from `source_ledger_sha256`, which hashes the exact ledger file bytes.
A missing checkpoint, changed binding, invalid cursor/history, or incomplete
triplet stops continuation before a request. A fresh checkout must not silently
re-bootstrap from an old mutable URL or assume that an ignored raw cache exists.

The coordinator copies the three validated files into an ignored per-run staging
area. `candidate_state.prepare_runtime` reconstructs the scanner's runtime ledger
there from public observations and the sanitized checkpoint. Previously omitted
source descriptions remain null, with their public omission annotations retained.
Only newly successful response bodies need to be retained for this invocation.
`finalize_runtime` verifies those bytes and their exact accepted metadata, preserves
all old receipt/run history, and keeps unchanged observation lines byte-for-byte.
It rejects an update that removes old observations or changes their historical
provenance. Strict scheduled scanning quarantines a mixed or rejected response
without adding even its otherwise-public rows to the durable population.

The public manifest states the verification mode explicitly:

- `full_retained_replay` means the producer re-read all retained successful primary
  response bodies for the selected frozen ledger.
- `incremental_retained_replay` means the producer trusted a fingerprint-bound,
  validated prior public triplet and replayed only this invocation's new successful
  responses. It records the baseline observation/checkpoint hashes and replay
  counts, and sets `historical_raw_replayed` to false. Its `source_ledger_sha256`
  identifies the reconstructed runtime ledger, not a claim to have re-read all
  historical network bodies.

A completed partial or rate-limited round may retain verified progress with its
explicit gaps and cooldown. A crash, missing terminal result, invalid new evidence,
or unfinished round cannot replace the durable snapshot. The child writes only
its staging area; the parent verifies its round-bound receipt and triplet, waits
for the catalog build to succeed, and uses `publish_snapshot` with the original
three file hashes as a compare-and-swap precondition. Only the manifest's catalog
comparison context is rebound to the final catalog bytes; observation bytes and
historical input fingerprints remain separate. Raised replacement failures roll
back the three prior files. This is not a claim that three filesystem renames are
one crash-atomic operation: workflow validation and the final Git commit remain
the durable publication boundary, and an incomplete local triplet fails closed.

Scanner v2 records explicit query epochs. Approved topic additions keep old roots
and cursors and backfill new topics from the original historical lower bound.
The production configuration names seventeen allowlisted topics. The original
nine remain: `android-automation`, `browser-agent`, `browser-agents`,
`browser-automation`, `computer-use`, `desktop-automation`, `gui-agent`,
`gui-agents`, and `gui-automation`. Eight additional exact spellings are supported
by retained publisher topic observations: `computer-use-agent`,
`computer-use-agents`, `gui-grounding`, `browser-use`, `web-agent`, `web-agents`,
`desktop-agent`, and `mobile-agent`. See the
[topic decision and evidence](reviews/2026-10-20-candidate-topic-expansion.md).
These are discovery queries, separate from reviewed catalog topic assignments.

Each addition starts at the first epoch's historical lower bound and ends at the
frontier's recorded upper date. Existing roots, cursors and receipts are retained,
including unfinished work from earlier epochs. For example, adding a topic after
a frontier has advanced to `2026-10-18..2026-10-20` still backfills that topic from
`2008-01-01`, when that was the original lower bound. Expansion is explicit and
additive; repeated invocations with the same topic set do not reset the backfill.

On a new UTC date, continuation records a new creation-date frontier even when
older topic trees still contain gaps. Its inclusive lower bound is the preceding
frontier's upper date, giving a recorded one-day overlap. The transition is
`daily_continuation` when that preceding tree is complete, or explicitly
`frontier_continuation` otherwise; it never marks old gaps complete. The new upper
date must match epoch creation and cannot exceed its associated run or request
observation date. Same-day runs resume the existing frontier.

New runs retain the current `epoch_id` and a `repair_epoch_ids` list. Permission
to repair an older epoch is derived from actual query ownership and progress at
the run's starting receipt boundary, not accepted merely because an ID is listed.
Shared roots introduced by topic additions have one latest owner. Legacy runs
without this field keep their original epoch rules. Every newly appended recheck
in a scoped run must name that `run_id` and the exact run-start instant; removing
the binding cannot downgrade it to a legacy event during incremental adoption.
Legacy events retain their bytes and must match an actual legacy run boundary,
epoch and time interval. Prior events and receipt prefixes remain unchanged.

After the existing-candidate sub-budget, search attempts alternate between the
current frontier and eligible historical repair work when both have pending
pages. When one lane has no pending page, the other can use the remaining budget.
This allocation never extends the 30-GET/220-second candidate limits or the shared
round allowance. Each scheduled invocation may reopen at most two traversals in
`partial_results` or `partial_api_window` from page one, retaining the prior cursor
and receipt boundary instead of deleting observations or counting old IDs toward
the new traversal. A `blocked_single_day_window` is not reopened automatically: it
requires a separately reviewed partition strategy. Public
manifests expose all historical query gaps, epoch history and the recheck count;
unresolved statuses remain visible even when the newest frontier is complete or
the ordinary pending counter is zero. None of these
states establishes global completeness or CUA relevance.

### One-time offline bootstrap

An operator who has the original frozen ledger and successful raw cache can
prepare the initial checkpoint explicitly. This operation first replays the raw
evidence and requires the result to match the already reviewed public observation
bytes exactly. It writes a reviewable proposal to the specified output directory:

```sh
python3 -S scripts/candidate_state.py \
  --ledger .cache/candidate-scan/frozen-round.json \
  --raw-dir .cache/candidate-scan/raw \
  --public-dir data \
  --catalog data/catalog.jsonl \
  --output-dir .cache/candidate-bootstrap/public
```

Review and adopt only that sanitized triplet. Keep the frozen original ledger,
raw responses and earlier export artifacts unchanged in ignored local storage.
Scheduled jobs never perform this bootstrap automatically. The checkpoint is
operational source state, not an additional resource, a normal RAG corpus, or
an SEO resource page.

```sh
.venv/bin/python -B -m unittest discover -s tests -p 'test_candidate_state.py' -v
```
