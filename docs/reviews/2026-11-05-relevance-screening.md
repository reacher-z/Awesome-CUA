# Relevance screening of metadata-only papers: 5–6 November 2026

Before this screening, 1,962 active records were arXiv papers with bibliographic verification only (`relevance_pending`). Title queries and discovery sources had added them. A title match such as "computation using" or "mobile agent" does not establish that a paper concerns computer-use agents, and the catalog's headline numbers had counted all of them as resources. Headline numbers now count curated records only. This screening reads every paper's complete abstract and records where it belongs: outside the scope, in the review queue for an annotation, or on hold for a full-text scope decision. Nothing is approved as curated here.

## Population and evidence

- **Population:** every record with scope `relevance_pending` at source commit `aa2c141b`: 1,962 arXiv papers. Papers indexed after that commit stay pending for the next screening.
- **Abstracts:** 40 official arXiv API `id_list` requests of up to 50 identifiers, sent one at a time 3.1 s apart on 5 November 2026, 23:00–23:04 UTC and listed with their response digests in [requests.json](2026-11-05-relevance-screening/requests.json). 1,947 abstracts hash to the retained `abstract_sha256` with the catalog's `sha256-utf8-whitespace-collapsed-v1` method; 15 are newer arXiv versions. Full abstracts stay in the ignored response cache and are not copied into the repository.
- **Existing decisions:** 15 of these papers already had an unapproved editorial entry. Those entries and their recorded reasons were left unchanged.

## Method

The scope boundary is the [inclusion boundary](../methodology.md#inclusion-boundary), read together with the catalog's adjacent precedents. **Core** work concerns agents that observe and act on graphical interfaces, web pages, desktop applications or mobile devices. It also covers their grounding and screen understanding, data and trajectories, benchmarks and environments, safety, and LLM-agent GUI testing. **Adjacent** work includes:

- application automation through scripts or APIs;
- terminal and claw-style computer agents;
- research agents that browse and read web pages;
- UI design and accessibility analysis;
- general agent methods evaluated on a named web or GUI environment.

Out of scope are unrelated science and engineering, general foundation models, generic agent frameworks, tool-calling agents and their safety work without web-page or GUI interaction, coding agents, robotics and game-API agents, and search-only question answering. Those two lists meet at tool use, so the line is explicit: a general tool-calling method with no named application setting stays out of scope, while a paper about agents carrying out tasks in named applications or business domains, or automating a workflow, through scripts, APIs or tools is held when its abstract does not settle whether it counts as application automation.

1. **First reading.** An AI-assisted screener read each complete title and abstract in 14 independent batches. It recorded `in_scope`, `adjacent`, `out_of_scope` or `borderline` with an original one-line reason. A screener who was unsure had to choose `borderline`; an unclear paper is never excluded.
2. **Second reading.** A different screener read every first-reading `out_of_scope` paper again, in a different batch mix and without the first decision.
3. **Final rule.** A paper is excluded only when both readings agree. These cases become reviewer holds instead:
   - the two readings disagree;
   - an open pull request proposes the opposite decision;
   - the paper would be excluded, but its retained metadata snapshot is older than the abstract that was read, because a scope decision binds to the retained snapshot.
   - Codex review disputed the exclusion and the abstract does not clearly settle it, or the paper belongs to the same class as one disputed.
   A core/adjacent split counts as adjacent.
4. **Application,** through the documented inputs:
   - an exclusion is a [scope decision](../scope-review.md#authoring-a-decision) in `data/exclusions.json` (`primary_abstract_review`, the retained receipt and metadata fingerprint);
   - an in-scope or adjacent paper is an unapproved proposal with a [`relevance_screen`](../editorial-input.md#relevance-screening), whose evidence is the API response the abstract was read from and whose `reviewed_sha256` binds the note to it. It waits in the review queue as `annotation_pending`. When the version read is newer than the retained record, the note says so, and the metadata must be reconciled before approval;
   - a borderline paper is the same proposal without `relevance_screen`: a `reviewer_hold` whose note says what is unclear.

## Outcome

| Final decision | Papers | Applied as |
| --- | ---: | --- |
| Out of scope, both readings agree | 1,168 | Scope exclusion |
| In scope (core) | 311 | Proposal, `annotation_pending` |
| Adjacent | 183 | Proposal, `annotation_pending` |
| Borderline or disputed | 300 | Proposal, `reviewer_hold` |
| **Total** | **1,962** | |

The second reading confirmed 1,191 of 1,224 first-reading exclusions (97.3%); the other 33 are held. Codex review then disputed 4 agreed exclusions; those and 10 more of the same class are held rather than excluded, and their `hold_basis` column says so. Before applying, 6 out-of-scope papers whose retained snapshot differs from the abstract read are held instead, and 15 papers keep their earlier editorial entry. Applied so far:

| Applied as | Papers |
| --- | ---: |
| proposal: annotation_pending | 492 |
| proposal: reviewer_hold | 5 |
| scope exclusion | 1,155 |

**Open pull requests.** 788 of these papers had an open one-paper pull request from 19–20 October 2026. The screening agreed with 611 of their proposals. Every paper whose screening disagrees with its pull request (177 papers) is held, and its note names the pull request; queued proposals name an open curation pull request too. An agreed exclusion supersedes that pull request's change. Those pull requests were left open for the maintainers.

## Decision tables

Each CSV lists one applied batch. It records the identifier, title, final decision and how it was applied, the reason, any `hold_basis`, both screeners' labels, any open pull request and its proposal, the abstract version and digest, whether the digest matches the retained snapshot, the API request number in `requests.json`, and the screening time.

- [01.csv](2026-11-05-relevance-screening/01.csv): 388 papers — 1 proposal: reviewer_hold, 387 scope exclusion
- [02.csv](2026-11-05-relevance-screening/02.csv): 387 papers — 2 proposal: reviewer_hold, 385 scope exclusion
- [03.csv](2026-11-05-relevance-screening/03.csv): 385 papers — 2 proposal: reviewer_hold, 383 scope exclusion
- [04.csv](2026-11-05-relevance-screening/04.csv): 492 papers — 492 proposal: annotation_pending

## Limits

- This is an abstract screening, not curation. A queued paper still needs a source-reviewed annotation, and a hold still needs a full-text scope decision.
- The screeners were AI-assisted. Reasons are original summaries of what each abstract states; no experiment was reproduced, and a decision says nothing about research quality.
- A general agent method whose abstract names no web, GUI or device setting was excluded even if its full text evaluates one. Correct such a case with a source-backed edit to `data/exclusions.json`; Git keeps the earlier decision.
