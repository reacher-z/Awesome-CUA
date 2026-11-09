# VideoCAD and GUIPivot source review — 18 October 2026

This review corrects two code-resource descriptions and related VideoCAD evidence using public GitHub and arXiv sources. Repository popularity was a selection aid, not an inclusion or quality criterion. Source files were inspected; no project was installed, executed, or independently reproduced.

## VideoCAD: select the author repository, preserve the fork's history

The [VideoCAD paper, arXiv v2](https://arxiv.org/html/2505.24838v2), explicitly links [ghadinehme/VideoCAD](https://github.com/ghadinehme/VideoCAD). GitHub identifies that repository as numeric ID `1079441024`. The previously indexed [UDGOK/videocad](https://github.com/UDGOK/videocad) is a distinct fork, numeric ID `1108132573`, rather than an earlier name of the same repository.

The inspected revisions are `2d69eeaf0ac44210c76dcab2d08b4d4610be236c` for the author repository and `c737b428ea3cd95729bf284cbb60eb13ccf7bfc2` for the fork. Their complete Git trees contain 30 identical file blobs; the upstream adds a LICENSE and changes its README. These facts support choosing the author's code resource without treating the copied fork as a second original implementation.

The resulting identities are handled as follows:

- `github:ghadinehme/videocad` becomes the active, reviewed code resource, with its own content-bound README, file-tree, paper and license evidence.
- `github:udgok/videocad` retains its original editorial object and primary receipt. Its `editorial_reviewed` flag is false, and its explicit `review_note` explains the fork decision. It therefore remains in the generated review queue as a `reviewer_hold`, outside the active catalog.
- No repository alias or candidate alias connects these different repository IDs. The old ID does not resolve to the author repository as a rename. The paper exclusion ledger and original discovery records are unchanged.

The paper describes Onshape as browser-based CAD software, supporting the `web` environment tag. This does not establish a particular host operating system. The [author repository's inspected LICENSE](https://github.com/ghadinehme/VideoCAD/blob/2d69eeaf0ac44210c76dcab2d08b4d4610be236c/LICENSE) declares MIT for its code. That declaration is not retroactively assigned to the old fork or extended to externally hosted datasets or weights. The existing VideoCAD dataset identity and its separately reviewed Dataverse evidence are unchanged.

A follow-up check of Sections 1 and 3 of the same v2 paper aligns the paper and dataset records with that `web` environment. The dataset's supporting README evidence now points to the inspected author revision instead of the fork; the paper explicitly describes the recorded interface as browser-based Onshape. The Dataverse primary receipt, dataset identity, reported quantities and separate data-license declaration are preserved.

## GUIPivot: make the evaluation and data boundary explicit

The [GUIPivot repository](https://github.com/ZrW00/GUIPivot) remains at its recorded revision `b02e8efdbe02ab82169a2c54d724e33b4037330e`. Its [paper, arXiv v2](https://arxiv.org/html/2503.00401v2), and released evaluator describe offline single-step action prediction and matching on AndroidControl and AITZ. The summary now states that scope explicitly rather than leaving “mobile-agent evaluation” open to interpretation as live task execution.

The repository releases preprocessing, query-refinement and evaluation source, training configurations, and multipart annotation archives. Its README directly links a UIBERT training-JSON path that is absent as a standalone file in the inspected revision. The notes distinguish that path from the actual `data/GUI.z01`, `data/GUI.z02`, and `data/GUI.zip` archives and their dataset manifest. Original images remain separately obtained inputs; this record does not assert a released trained checkpoint.

The repository's GPL-3.0 code declaration is retained. No dataset or weight license is inferred from it. The Android environment, framework kind, core scope and paper relationship remain unchanged.

## Verification boundary

The source corrections use retained successful public responses whose bytes were rechecked against their recorded SHA-256 fingerprints. The repository verifier was applied only to the two current code resources using those retained responses and their actual retrieval times; no network refresh or whole-catalog source scan was performed. A failed direct-file request is not represented as a successful release receipt: the complete, successful repository-tree response supports the absent-path observation.

This identity correction replaces one active resource with one active resource; the description and environment corrections update existing records in place. It therefore preserves the input population of 3,177 active records and 1,619 curated records. The separate [expansion review](2026-10-18-expansion-review.md) records subsequent approval holds and the final combined counts. Counts describe catalog resources, not independent projects.
