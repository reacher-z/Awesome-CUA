# Scope review and retained bibliography

The active catalog focuses on computer-use agents and directly relevant foundations. Broad discovery queries can also retrieve work in unrelated areas such as physical quantum computing or reservoir hardware. Bibliographic verification alone does not establish CUA relevance.

## Explicit decisions

`data/exclusions.json` is an authored list of primary-abstract scope reviews. Each entry records the paper identity, original title and URL, reason, review time, metadata fingerprint, and primary response receipt. No keyword rule automatically excludes a paper. A GitHub, Hugging Face or website candidate outside the scope is recorded in `data/candidate-reviews.json` with `decision: out_of_scope` instead; see [methodology](methodology.md#explicit-scope-review).

`data/exclusion-status.json` is generated during the offline build. A decision applies only while its metadata fingerprint and retained evidence match and no upstream metadata change is queued. Otherwise the record remains visible as metadata-only and the decision is queued for revalidation. A curated inclusion or a dependency from a retained relationship must be reconciled before an exclusion can take effect.

## Authoring a decision

Exclude a paper only after reading its abstract at `https://arxiv.org/abs/<id>`. The paper must already have a record in `data/papers.jsonl`, and it must not have an approved editorial entry.

Run this snippet from the repository root, with the arXiv ID as its argument, to print a draft entry. It reads the retained record, computes its fingerprint with `scope_review.metadata_fingerprint`, and copies `url`, `sha256` and `retrieved_at` from the record's `arxiv_api` receipt:

```bash
python3 - 2501.02813 <<'PY'
import json, sys
sys.path.insert(0, 'scripts')
from scope_review import metadata_fingerprint
rid = 'arxiv:' + sys.argv[1]
record = next(row for row in map(json.loads, open('data/papers.jsonl', encoding='utf-8')) if row['id'] == rid)
receipt = next(source for source in record['evidence'] if source['method'] == 'arxiv_api')
print(json.dumps({'id': rid, 'name': record['name'], 'url': 'https://arxiv.org/abs/' + sys.argv[1],
    'decision': 'out_of_scope', 'basis': 'primary_abstract_review', 'reason': '', 'reviewed_at': '',
    'metadata_fingerprint': metadata_fingerprint(record),
    'evidence': {key: receipt[key] for key in ('url', 'sha256', 'retrieved_at')}}, ensure_ascii=False, indent=2))
PY
```

The fingerprint is the SHA-256 of the UTF-8 encoding of `json.dumps({id, name, authors, published_at, updated_at}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))`, taken from the retained record. Then complete the draft:

1. Write `reason`: what the abstract studies and why that falls outside the catalog's scope. An empty `reason` fails validation.
2. Set `reviewed_at` to the UTC time you read the abstract, for example from `date -u +%Y-%m-%dT%H:%M:%SZ`. It must not be earlier than `evidence.retrieved_at`, and an empty value fails validation.
3. Append the entry to the array in `data/exclusions.json`.
4. Run the [checks](#checks). Then confirm that `data/exclusion-status.json` lists the decision with `"status": "excluded"`.

The committed decision for arXiv 2501.02813 is a complete example:

```json
{
  "id": "arxiv:2501.02813",
  "name": "Multi-time scale and high performance in-material reservoir computing using graphene-based ion-gating reservoir",
  "url": "https://arxiv.org/abs/2501.02813",
  "decision": "out_of_scope",
  "basis": "primary_abstract_review",
  "reason": "The abstract develops a graphene ion-gating reservoir and evaluates physical recurrent computation on chaotic time-series prediction. This neuromorphic device research is outside the GUI/computer-use agent scope.",
  "reviewed_at": "2026-10-17T05:27:45Z",
  "metadata_fingerprint": "8c2d9877f64e4bf3e134ffc51b4016ac99d021b2373c630f8b5c0aacab116f23",
  "evidence": {
    "url": "https://export.arxiv.org/api/query?search_query=%28ti%3A%22computer+use%22+OR+ti%3A%22computer-use%22+OR+ti%3A%22GUI+agent%22+OR+ti%3A%22GUI+agents%22+OR+ti%3A%22GUI+grounding%22+OR+ti%3A%22web+agents%22+OR+ti%3A%22browser+agent%22%29+AND+submittedDate%3A%5B200001010000+TO+202610160636%5D&start=800&max_results=100&sortBy=submittedDate&sortOrder=descending",
    "sha256": "c87e97eb397da04806d53145cf9c13be739fc657bb54dca9318c8c4ed2a36249",
    "retrieved_at": "2026-10-16T06:36:58Z"
  }
}
```

`catalog.py build` stops, and `catalog.py validate` reports an error, when an entry breaks any of these rules:

- `id` is `arxiv:` followed by a new-style identifier with no version suffix, such as `arxiv:2501.02813`, and occurs only once in the file.
- The ID has a retained record in `data/papers.jsonl`.
- `decision` is `out_of_scope` and `basis` is `primary_abstract_review`.
- `name` is not empty and `reason` is not blank.
- `url` is exactly `https://arxiv.org/abs/<id>`.
- `metadata_fingerprint` is 64 lowercase hexadecimal characters.
- `evidence.url` is an `https` URL and `evidence.sha256` is 64 lowercase hexadecimal characters.
- `reviewed_at` and `evidence.retrieved_at` are timestamps with a time zone, and `reviewed_at` is not earlier than `evidence.retrieved_at`.
- The record is not curated. Reconcile its editorial entry before excluding it.
- No retained record has a relation, or an `identifiers.preferred_arxiv`, that points at the excluded paper.

`catalog.py validate` also checks the file against [scope-decision.schema.json](../schemas/scope-decision.schema.json), which requires every key in the example and allows no others.

The following conditions do not fail the build. Instead the decision resolves to `revalidation_pending`: the record stays in the catalog as metadata-only, and the decision is added to `data/review-queue.jsonl` for another review.

- `evidence.url` and `evidence.sha256` match no receipt in the record's `evidence`.
- `metadata_fingerprint` differs from the fingerprint of the current retained record.
- `data/metadata-updates.jsonl` holds an upstream change proposal for the ID.

## Preserving provenance

- `data/papers.jsonl` retains ingested arXiv metadata, including excluded records. It is an archive of input snapshots, not the current editorial catalog.
- `data/catalog.jsonl`, SQLite search, and the interactive catalog omit applied exclusions.
- Previous resource URLs remain available as scope explanations with `noindex,follow`; their Markdown companions are updated too.
- The website exposes the scope ledger and raw metadata archive as separate downloads. Active-catalog counts, archive counts, exclusions, and unresolved candidates have different meanings.

A decision concerns the catalog's scope, not the quality of the underlying research. It can be corrected by updating or removing the authored decision in a source-backed commit; Git history retains the previous decision. If an upstream metadata proposal triggered revalidation, reconcile that proposal before renewing the decision.

## Checks

`schemas/scope-decision.schema.json` defines the authored input. `scripts/scope_review.py` resolves decisions and guards against source drift, silent removal of curated entries, and broken retained relationships. Tests cover preservation of the archive, revalidation, explicit-only decisions, coverage counts, and non-indexed explanation pages.

```bash
python3 scripts/catalog.py build
python3 scripts/catalog.py validate
python3 -m unittest discover -s tests -p 'test_scope_review.py' -v
```
