# Editorial input

`data/editorial.json` is a JSON array with one hand-authored object per reviewed or proposed resource. `python3 scripts/catalog.py verify` fetches primary evidence for each entry, `enrich` extracts declared licenses and references from that evidence, and `build` (`source_records` in `scripts/build.py`) turns each approved entry into a `curated` record in `data/catalog.jsonl`. There is no separate JSON Schema for this file; the [published record](data-dictionary.md) is checked by `validate`.

## Approval

An entry is published as `curated` only when all of the following hold:

- `editorial_reviewed` is `true`
- `data/primary-evidence.jsonl` has a receipt for the entry's ID with `content_matched: true`
- `reviewed_sha256` equals that receipt's `sha256`

Otherwise the entry stays in `data/review-queue.jsonl` and the coverage ledger. If the evidence is unresolved, the reason is "primary evidence unresolved" with the fetch error, followed by the entry's `review_note` when it has one; if the digest differs, it is "current source snapshot needs editorial review"; in all other cases it is the entry's `review_note`. Each pending row in `data/coverage.json` and `data/review-queue.jsonl` also carries its `cause`: `unresolved_evidence`, `unreviewed_snapshot`, `reviewer_hold`, or `scope_revalidation`, and `docs/coverage.md` counts the proposals by cause. An arXiv paper whose entry is pending remains a `metadata_verified` bibliography record.

## Resource ID

The ID is `id` when given, otherwise the first value of `editorial_identity(entry)` in `scripts/catalog.py`. That is `canonical(url)`, except that `paper` and `survey` entries may also use an HTTPS `doi.org` URL: the DOI is case-folded into `https://doi.org/<doi>` and receives a `url:` ID. Other kinds reject bare DOI links, as discovery does. The same ID keys the entry's receipt in `primary-evidence.jsonl`, its row in `enrichment.jsonl`, and the published record, so changing `url` or `id` requires `verify` and another review.

```bash
python3 -c "import sys; sys.path.insert(0,'scripts'); from catalog import editorial_identity; print(editorial_identity({'url': 'https://github.com/xlang-ai/OSWorld/tree/main', 'kind': 'benchmark'})[0])"
# github:xlang-ai/osworld
```

- arXiv abstract, PDF and HTML URLs, versioned URLs, and Hugging Face paper pages become `arxiv:<id>`.
- GitHub repository URLs, including `tree/` and `blob/` links, become `github:<owner>/<repo>` in lowercase.
- Every other URL, including Hugging Face models and datasets, becomes `url:` plus the first 20 hex digits of the SHA-256 of the cleaned URL (HTTPS, lowercase host, no fragment, trailing slash, or `utm_` parameters). Bibliographic records also use `data/publications.jsonl`. `canonical` rejects non-HTTPS URLs, images, badges, social links, and `localhost`, `.local`, loopback and private-network hosts.

An entry for an arXiv paper replaces the bibliographic record from `papers.jsonl`. The published record keeps that record's dates, authors, identifiers, `details.arxiv_snapshot` and `arxiv_api` evidence.

## Fields

In the Required column, `always` means that `build` or `verify` fails without the key. `for approval` means that the entry cannot be published as curated without it: `build` reads the key only for an approved entry, approval depends on it, or `validate` rejects an empty value. Unless a row says otherwise, the consumer is `source_records` in `scripts/build.py`. A relation derived from a shorthand key cites the URL of the primary receipt. `validate` requires every relation target to exist in the catalog.

| Field | Required | Type | Default | Read by | Effect on the published record |
| --- | --- | --- | --- | --- | --- |
| `name` | always | string | — | `source_records`, `verify_editorial` | `name`; default verification term |
| `kind` | for approval | one of the `kind` values in the [schema](../schemas/resource.schema.json) | — | `source_records`, `enrich` | `kind`; selects the license slot for a Hub card: `data` for a `dataset` or any card in a Hub dataset repository, `weights` for a `model` |
| `url` | always | HTTPS URL accepted by `canonical` | — | `canonical`, `verify_editorial`, `source_records` | `url` and the `primary` link; default ID and default evidence URLs |
| `environments` | for approval | non-empty array of schema environments | — | `source_records` | `environments`; `validate` rejects an empty array |
| `topics` | for approval | array of keys from the [topic vocabulary](data-dictionary.md#topic-vocabulary) in `data/topics.json` | — | `source_records` | `topics` and topic-hub placement |
| `summary` | for approval | string; original and concise: at most 220 characters, ending with a period, without superlatives | — | `source_records` | `summary`; `validate` rejects an empty one. `catalog.py lint` reports a curated summary over 220 characters, under 60 characters for a kind other than `paper` or `survey`, without a terminal period, or with "state-of-the-art", "best" or "revolutionary"; the report is advisory and never fails |
| `editorial_reviewed` | for approval | boolean | `false` | `source_records` | `false` keeps a proposal in the review queue |
| `reviewed_sha256` | for approval | 64 hex digits | — | `source_records` | Must equal the current primary receipt's `sha256` |
| `reviewed_at` | no | ISO 8601 UTC time of the review | — | `build` (README) | Informational. It does not gate approval and is not compared with the receipt. It orders the README's Recently reviewed table, which omits papers, surveys, and entries without it |
| `review_note` | no | string | `"editorial review pending"` | `source_records` | Review-queue reason for an unapproved entry whose evidence matches; appended to the fetch error when the evidence is unresolved |
| `verify_terms` | no | array of strings | `[name]` | `verify_editorial` | A source matches when at least one term occurs, ignoring case and whitespace runs. Bot-challenge pages never match |
| `evidence_urls` | no | array of HTTPS URLs | GitHub: raw `README.md`, `README.MD`, `readme.md` at `HEAD`, then the repository page. Hugging Face dataset: `/api/datasets/<id>`. Other Hugging Face page except a collection: `/api/models/<id>`. Otherwise `url` | `verify_editorial` | Tried in order. The first matching response becomes the primary receipt, and its retrieval time becomes `last_verified_at` |
| `id` | no | `arxiv:`, `github:`, `url:`, `component:` or `organization:` ID | `editorial_identity(entry)[0]` | `verify_editorial`, `enrich`, `source_records` | Record `id`. Use `component:<owner>/<path>` for one asset inside a monorepo and `organization:<slug>` for a publisher |
| `aliases` | no | array of strings | `[]` | `source_records` | `aliases`; searched by the CLI and SQLite. `validate` rejects a URL alias that is itself an active record or that another record already claims. A renamed GitHub repository's former name resolves to this record only through `data/repository-aliases.json` |
| `scope` | no | `core` or `adjacent` | `"core"` | `source_records` | `scope` |
| `notes` | no | string | `""` | `source_records` | `notes` |
| `details` | no | object | `{}` | `source_records`, `validate_profiles` | Merged over bibliographic details. Details extracted by `enrich` from the same receipt override it. The build adds no null or empty placeholders for unset keys. `dataset_profile` and `benchmark_protocol` must cite retained receipts. Record an inspected Git commit as `repository_revision` and pin receipts by that commit, such as `raw.githubusercontent.com/<owner>/<repo>/<commit>/README.md`; the [data dictionary](data-dictionary.md#kind-specific-details) defines every key. When present without `primary_supports`, `details` is added to the primary receipt's supports |
| `primary_supports` | no | array of field paths | `name`, `kind`, `summary`, `environments`, `topics`, `scope`, `relations` | `source_records` | `supports` of the primary `editorial_primary_review` receipt |
| `additional_evidence` | no | array of receipts with `role: "primary"`, `method`, `supports`, `url`, `sha256`, `retrieved_at` | `[]` | `source_records`, `verify_editorial`, `apply_license_reviews` | Appended to `evidence` after the primary receipt; can back relations, licenses, and profiles. `verify` refetches each one, and a changed digest or failed fetch revokes the content match |
| `reviewed_relations` | no | array of `{type, target_id, evidence_url}` | `[]` | `source_records` | Copied into `relations` before derived relations. `validate` requires `evidence_url` to be one of the record's receipts |
| `paper_ids` | no | array of bare arXiv IDs | `[]` | `source_records` | One `introduced_by` relation to `arxiv:<id>` per ID |
| `documented_by` | no | array of bare arXiv IDs | `[]` | `source_records` | One `documented_by` relation to `arxiv:<id>` per ID |
| `publisher_id` | no | resource ID, usually `organization:<slug>` | — | `source_records` | `published_by` relation to that ID |
| `component_of` | no | URL of the containing resource | — | `source_records` | `component_of` relation to `canonical(component_of)[0]` |
| `family_url` | no | URL of the model family | — | `source_records` | `variant_of` relation to `canonical(family_url)[0]` |
| `reviewed_licenses` | no | object keyed by `code`, `data`, `weights`, or `document`; each `{value, reason, evidence_urls}` | `{}` | `apply_license_reviews` | Replaces that license slot with `value`, either `null` or a license object whose `url` is in `evidence_urls`, and publishes the reason and sources in `details.license_review`. Each evidence URL must be a receipt whose `supports` include `licenses` or `licenses.<slot>` |
| `read_basis` | no | string | — | none | Informational audit note on what the reviewer read; not published |

`build` sets the remaining record fields: `review_status: "curated"`, the `primary` link, `licenses` from `enrich` plus `reviewed_licenses`, and the evidence list (bibliographic receipts, then the primary receipt, `additional_evidence`, and `enrich` receipts).

## Examples

A GitHub repository. Its primary receipt is the raw README, and its ID is `github:xlang-ai/osworld`:

```json
{
  "name": "OSWorld",
  "kind": "benchmark",
  "url": "https://github.com/xlang-ai/OSWorld",
  "environments": ["desktop", "linux", "windows", "macos"],
  "topics": ["evaluation", "cross-app"],
  "summary": "Execution-based evaluation of agents performing tasks in real desktop environments.",
  "verify_terms": ["OSWorld"],
  "documented_by": ["2404.07972"],
  "editorial_reviewed": true,
  "reviewed_sha256": "<sha256 of the github:xlang-ai/osworld receipt in data/primary-evidence.jsonl>",
  "reviewed_at": "2026-10-16T11:51:16Z"
}
```

A Hugging Face dataset. The default Hub API receipt establishes identity and the declared data license. The inspected dataset card supports the profile through `additional_evidence`:

```json
{
  "name": "AgentNet",
  "kind": "dataset",
  "url": "https://huggingface.co/datasets/xlangai/AgentNet",
  "environments": ["desktop"],
  "topics": ["data-generation"],
  "summary": "Computer-use demonstrations released with OpenCUA.",
  "verify_terms": ["AgentNet"],
  "documented_by": ["2508.09123"],
  "details": {"dataset_profile": {"supervision": ["computer-use trajectories", "synthesized reasoning"],
    "modalities": ["screenshots", "instructions", "actions", "generated reasoning"], "formats": ["JSONL", "image archives"], "splits": [],
    "counts": [{"value": 22600, "unit": "tasks", "qualifier": "approximately", "population": "AgentNet collection", "basis": "reported",
      "evidence_url": "https://huggingface.co/datasets/xlangai/AgentNet/raw/main/README.md"}],
    "notes": "Generated labels are not independent human quality acceptance records.",
    "evidence_urls": ["https://huggingface.co/datasets/xlangai/AgentNet/raw/main/README.md"]}},
  "primary_supports": ["name", "kind", "summary", "environments", "topics", "scope", "relations"],
  "additional_evidence": [{"role": "primary", "method": "editorial_primary_review", "supports": ["details.dataset_profile"],
    "url": "https://huggingface.co/datasets/xlangai/AgentNet/raw/main/README.md", "sha256": "<sha256 of the reviewed card>", "retrieved_at": "2026-10-16T11:40:46Z"}],
  "editorial_reviewed": true,
  "reviewed_sha256": "<sha256 of the API receipt in data/primary-evidence.jsonl>",
  "reviewed_at": "2026-10-16T11:51:16Z"
}
```

A dataset inside a monorepo, shown as an unapproved proposal. Without the `id` override, it would collapse into `github:google-research/google-research`. `evidence_urls` points at the component's own README rather than the monorepo's:

```json
{
  "id": "component:google-research/android_control",
  "name": "AndroidControl",
  "kind": "dataset",
  "url": "https://github.com/google-research/google-research/tree/master/android_control",
  "evidence_urls": ["https://raw.githubusercontent.com/google-research/google-research/master/android_control/README.md"],
  "environments": ["android"],
  "topics": ["data-generation", "mobile-navigation"],
  "summary": "Android demonstrations with high-level goals, step instructions, screenshots, and accessibility trees.",
  "verify_terms": ["AndroidControl"],
  "paper_ids": ["2406.03679"],
  "editorial_reviewed": false,
  "review_note": "Awaiting a check of the published split files."
}
```
