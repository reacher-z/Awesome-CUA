# Scope and methodology

The unit of the catalog is a **resource**. A research paper, dataset release, model checkpoint, repository, product, and publisher entity have distinct identities even when they belong to the same project. Totals must always be accompanied by kind and review-state breakdowns.

## Inclusion boundary

Core resources concern agents that observe and interact with graphical interfaces, web pages, desktop applications, or mobile devices. Hybrid GUI/code/API interaction is included when computer interaction is material to the work. GUI grounding, screen understanding, training data, evaluation, execution environments, and safety research are in scope.

Supporting automation libraries and workflow recording tools may be marked `adjacent`. Generic coding assistants, LLM frameworks, RPA vendors, and crawlers are not automatically core CUA resources. Discovery can contain such items; discovery is not inclusion.

## Discovery and authority

1. Community collections and survey repositories supply candidate identifiers. They are credited, but do not establish the correctness of a resource's claims.
2. A separate, timestamped arXiv title query supplies primary-source candidates. Its exact expression, cutoff, pagination, and reported population are saved.
3. arXiv's API supplies bibliographic facts. Full abstracts and papers are not copied into the catalog.
4. Editorial resources use official repositories, publisher documentation, and model/dataset cards. A reachable page or name match alone is insufficient for curation.
5. Editorial decisions are AI-assisted, not an assertion of independent human peer review. The reviewed content digest is recorded. A changed snapshot cannot inherit approval merely because its URL still works.

## Identity and deduplication

- arXiv PDF, abstract, HTML, versioned URLs, and Hugging Face paper mirrors map to one version-independent arXiv ID.
- GitHub repository spelling/case, `.git`, and repository-file links fold to a repository ID for discovery.
- Explicit `component:` IDs distinguish reviewed assets inside a monorepo.
- `organization:` IDs distinguish publisher/brand entities from their offerings; these do not assert legal incorporation or ownership.
- Other URLs lose fragments and common tracking parameters. Similar titles are not automatically merged.
- Link extraction ends a URL at a backtick, brace or backslash, and trailing ones (raw or percent-encoded) are dropped: they come from Markdown code, LaTeX or template braces and escaped strings. `localhost`, `.local`, loopback, private-network and other non-public IP addresses are local services, not resources. `discover` applies the current rules to stored candidates, so a candidate whose URL now cleans differently merges into the cleaned identity and one now rejected is dropped.
- Redirects, project renames, dataset mirrors, and model variants require continued editorial entity resolution. Source coverage is conservative and does not assume that similar names are equivalent.
- Former GitHub repository names can be recorded in `data/repository-aliases.json` after both official name endpoints identify the same numeric repository ID and canonical owner. These dated observations resolve search and exact former-ID lookups without creating another resource. They cannot map a repository to its dataset, a monorepo component, or an unreviewed target. Renew or correct the mapping when its identity evidence changes; inactive or conflicting owners fail validation rather than being silently reassigned.
- When an author explicitly identifies an accidental duplicate submission, `identifiers.preferred_arxiv` records the preferred identifier with primary evidence. The duplicate stays accessible as bibliographic provenance and cannot be promoted as another curated paper. Similar titles alone do not establish this relationship. `validate` lists papers and surveys whose titles (letters and digits, ignoring case) and author lists are identical but that no `preferred_arxiv` decision connects, so each one gets a source-backed decision; it fails if two of them are curated.

## Explicit scope review

`data/exclusions.json` records individually reviewed, out-of-scope bibliographic snapshots. These are relevance decisions based on primary abstracts, not assessments of research quality. Keywords never create an exclusion automatically. Each decision binds to the reviewed metadata fingerprint and a primary evidence receipt; changed ingested metadata, missing evidence, or a queued upstream metadata change reopens the decision and leaves the record visible as pending review.

The raw arXiv archive retains every ingested record. Applied exclusions are absent from the active catalog, search, and SQLite export, but their previous resource URLs remain accessible as `noindex` scope explanations. The generated `data/exclusion-status.json` separates applied decisions from revalidation requests. Discovery counts distinguish indexed, excluded, and unresolved identifiers.

Curated inclusion cannot conflict with an exclusion, and scope changes cannot silently break retained relationships. Correct a decision through a source-backed edit to the ledger; version control preserves its history. The input contract is `schemas/scope-decision.schema.json`.

## Evidence and unknowns

Every published record has a primary URL, retrieval timestamp, SHA-256 of the fetched response, and the fields supported by that evidence. Upstream raw responses stay in an ignored local cache; committed receipts retain attribution and fingerprints. A digest verifies identity when the response is available; it does **not** guarantee that a mutable upstream URL can recreate an old snapshot.

Some dataset cards contain only licensing metadata. For these entries, Hub metadata establishes identity and licensing while an inspected project README supports the description and scope. Editorial inputs retain these as `additional_evidence` with separate content hashes and field scopes. Refreshing either required source with changed or unavailable content revokes the verification match until another review.

`published_at` is the original arXiv publication date where available. Retrieval dates never substitute for release dates. Unknown dates, size, licenses, and pricing are null. A hub size category can refer to packaged files, so it is not interpreted as a sample count. Publisher claims and independent measurements are not interchangeable.

License declarations are scoped to code, data, weights, or documents. Repository LICENSE headers never establish permissions for weights or embedded third-party data. No blanket permissive license is inferred from public availability.

For a GitHub repository, `enrich` reads the first of `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `LICENSE.rst`, `LICENCE` and `COPYING` that exists, and records a code license only when that file opens with a standard text: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, MPL-2.0, a CC BY 4.0 legal code (including its NC, SA and ND variants), or the verbatim FSF text of GPL-2.0, GPL-3.0, AGPL-3.0, LGPL-2.1 or LGPL-3.0. Composite, custom and altered texts, and project notices that only name a license, stay unknown. A GNU license text does not say whether later versions apply; a project states that in its own notices. GNU declarations therefore use the identifier of the text (for example `AGPL-3.0`, as GitHub reports it), and their basis records that -only or -or-later is unstated.

Provider-specific API parsing checks the actual host and URL path. Harvard Dataverse records retain the dataset-version license declaration, first publication date, version release time, and file count separately. A package-file count is not a trajectory or sample count; the API does not imply a Hugging Face download path or access policy.

`mentions` edges record references found in a primary README/card. They do not establish training, evaluation, derivation, partnership, or endorsement. Stronger relations are explicit editorial assertions with evidence. `discover` adds each arXiv paper that a curated record mentions to `candidates.jsonl` under the `curated-references` source, with the citing record and its reviewed snapshot as provenance, so `harvest` verifies its bibliographic metadata. The paper then stays metadata-only until its own relevance review.

When a paper documents an implementation that is not cited back by the repository, an editorial `reviewed_relations` entry may cite the paper's retained evidence receipt. Its evidence URL must exist in the resource's evidence list. This does not imply that current code reproduces the paper's results.

## Paper versions and revision proposals

Publisher bibliography is retained in `data/publications.jsonl` under [publication-observation.schema.json](../schemas/publication-observation.schema.json). Each observation binds a publication edition and its primary receipts to one canonical resource ID. A verified match to a retained arXiv work, including metadata-only or excluded records, attaches to that identity instead of adding a second paper. Publisher-only observations seed metadata-only records; inclusion still requires a separate content-bound editorial review. `data/papers.jsonl` remains the unchanged arXiv input archive.

Publication title and author variants remain separate from the retained arXiv title and authors. Dates retain year, month or day precision in `details.publication.date_parts`; a conference event range, retrieval date, or manuscript revision does not fill a missing publication day. The default citation selects the retained source edition. Explicit publication citations use the publication's own title, authors, date and venue, so preprint and proceedings facts cannot be silently mixed.

Explicit bibliography inputs accept source-backed DOI resolver URLs through a narrow identity rule; ordinary discovery still ignores incidental DOI links. Known publisher and PDF URLs resolve to their reviewed canonical owner. DOI ownership is checked against retained identities, and publisher aliases cannot reopen an excluded work as a new URL record. Similar titles alone do not establish identity.

An already reviewed PDF can retain its content match only when a fresh successful response has the exact reviewed byte digest and a PDF signature. A changed or unreviewed PDF requires renewed review. Required supporting receipts are checked separately; an HTML verification page is never treated as that PDF.

`details.arxiv_snapshot` records facts extracted from the individual Atom entry associated with the retained API receipt. The contract is `arxivSnapshot` in `schemas/resource.schema.json`.

| Field | Meaning |
| --- | --- |
| `version`, `versioned_url` | Version observed in the Atom entry ID and its version-specific publication link. |
| `submitted_at`, `updated_at` | Exact first-submission and retrieved-version timestamps, normalized to UTC. |
| `abstract_sha256` | SHA-256 of the abstract after collapsing whitespace and encoding as UTF-8. |
| `abstract_hash_method` | `sha256-utf8-whitespace-collapsed-v1`, the explicit comparison method. |

The API distinguishes the first submission from the retrieved version through its entry-level `published` and `updated` fields. These are separate from the feed's update time and our retrieval timestamp. [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html)

The response digest identifies the fetched API body, which may contain many papers. The abstract digest identifies one paper's normalized abstract. A change elsewhere in a batched response does not by itself establish a paper revision. Full abstracts remain in the ignored response cache and are not copied into catalog records.

Harvesting, the full title search, and the scheduled recent search share the same non-overwriting merge rule. A known ID keeps its retained metadata while new versions, exact timestamp changes, abstract changes, or bibliographic changes enter `data/metadata-updates.jsonl`. This detects changes within the same calendar day. Missing or incomplete baselines and unsupported hash methods carry an explicit revalidation reason; they are not silently replaced by the latest observation. A proposal preserves its observed snapshot and source receipt for review, and is withdrawn when a later complete observation matches the retained record again. Curated content continues to describe the retained reviewed snapshot, and a pending proposal reopens an existing scope exclusion.

The completed offline migration backfilled 1,764 retained paper records from their original cached Atom receipts. It added snapshot fields and the corresponding evidence support labels while preserving existing bibliographic facts, identities, review decisions, and receipt URLs, hashes, and retrieval times. It did not fetch new versions or reapprove content.

## Coverage denominator

The coverage ledger measures how many normalized identifiers from each successfully fetched source snapshot have a catalog record. A source may include incidental or out-of-scope links. Multiple sources overlap; their counts cannot be summed into a unique field size. Failed refreshes are shown as failures; previous successful local cache data are not presented as a fresh successful fetch.

Per-source coverage counts matching discovery identifiers. Several reviewed publisher/PDF aliases, or a former GitHub name recorded in `data/repository-aliases.json`, may point to one canonical resource; `indexed_resources` records that distinct-resource count. Overall bibliography totals count active paper/survey identities and separately expose arXiv, publisher-only, and publication-metadata coverage.

The arXiv title-query population is also bounded. It misses papers with different terminology and work on other publication platforms. Neither list-union coverage nor title-query recall proves global completeness. Regional/language-specific products, closed data, unpublished systems, and detailed benchmark protocols remain active curation gaps.

The scheduled recent query covers a 14-day first-submission window ending at the current UTC midnight. A complete, successful result, including a valid zero-result feed, is reused within that UTC day with its original retrieval timestamps. Failed or partial searches are retried by a later scan. This is a local UTC cache policy following the API's recommendation to cache an identical query within its daily publication cycle; the API defines date-query bounds in GMT. [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html)

Both daily workflow runs still attempt to refresh all configured discovery documents and the Hugging Face paper searches. Recent-query reuse only skips that arXiv request. The 14-day discovery window does not provide revision monitoring for every historical paper in the archive.

## Performance comparisons

This release does not publish a unified leaderboard. A future score observation must include model/checkpoint, benchmark/version, split, metric, action/step budget, evaluator, run date, evidence, and whether it is publisher-reported or independently reproduced. Without that context, results must not be ranked together.
