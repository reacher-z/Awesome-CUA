# Expansion review — 18 October 2026

The expansion was checked against retained primary sources before release. The
review covered 47 proposed approvals: 17 annotations were retained, 26 were
revised, and four were held for further review. A separate review also withdrew
the earlier adjacent-scope approval for the Agent-SafetyBench paper.

At this review snapshot, the generated catalog contains **3,175 active records**:
**1,614 curated** and **1,561 metadata-only**. The curated records comprise
1,154 papers and surveys and 460 other resources. These are resource records,
not a count of independent projects or a claim of complete field coverage.

## Evidence checked

- All 47 proposals matched their retained primary-response SHA-256 values.
- All 34 paper proposals matched the retained arXiv title, authors, dates,
  version and abstract fingerprint. Complete abstracts were read; selected
  full-text sections were additionally checked where scope was unclear.
- The 123 added archive records reparsed from their retained Atom responses.
- The seven added discovery sources matched their retained response receipts.
- Fourteen new exclusion decisions were checked against complete abstracts.

No benchmark results were reproduced, and linked repository code was not run.
An available source file or a successful HTTP response does not establish that
a released system works as described.

## Scope and release corrections

| Resource | Reviewed boundary |
| --- | --- |
| [Progent](https://arxiv.org/html/2504.11703v3) | Held as bibliographic metadata. Section 9 explicitly places graphical-interface tool calls outside the current method. |
| [PrivacyLens](https://arxiv.org/html/2409.00138v3) | Held as bibliographic metadata. Sections 3.2–3.3 describe emulated tool trajectories and final-action privacy evaluation; a specific GUI connection remains unestablished. |
| [Agent-SafetyBench paper](https://arxiv.org/html/2412.14470v2) and [repository](https://github.com/thu-coai/Agent-SafetyBench) | Paper approval withdrawn; repository proposal held. The reviewed method uses JSON-schema tools and simulated Python environments. An adjacent-scope rationale still needs evidence. |
| [AgentAttack](https://github.com/OSU-NLP-Group/AgentAttack) | Repository proposal held: the retained release is a position-paper companion and related-work list, not a released executable benchmark. |
| [A Trembling House of Cards](https://arxiv.org/html/2402.10196v1) | Retained as adjacent conceptual work. Its hypothetical web-navigation attack scenarios are distinguished from implemented evaluations. |
| [WebThinker](https://arxiv.org/html/2504.21776v2) | Retained as adjacent web research. The explorer uses search and URL-content retrieval rather than visual browser control. |
| [MONDAY](https://github.com/runamu/monday) | The annotation distinguishes released processing/evaluation helpers from the full generation pipeline, training scripts and checkpoints marked pending. |
| [LearnAct](https://github.com/lgy0404/LearnAct) | The annotation describes released offline inference/evaluation; online and real-world deployment code was marked coming soon. |
| [AgentStudio](https://github.com/skyworkai/agent-studio) | Environment tags were narrowed to the supported Ubuntu/Linux desktop environment. |
| [VeriSafe Agent](https://arxiv.org/html/2503.18492v2) | The annotation records developer-supplied app-state predicates and binds the paper–repository relation to the exact-version paper. |

The five holds are **not scope exclusions**. Paper bibliography records remain
available with metadata-only status; held repository proposals remain in the
review queue. Other platform tags were narrowed where the reviewed source did
not establish a specific operating system. Broad surveys retain explicit
adjacent-scope notes rather than implying a GUI implementation.

## Unresolved license declarations

Two official source pairs disagree, so their code-license fields remain `null`:

- [SheetCopilot README](https://github.com/BraveGroup/SheetCopilot/blob/HEAD/README.md)
  states a noncommercial restriction, while its
  [LICENSE](https://github.com/BraveGroup/SheetCopilot/blob/HEAD/LICENSE) contains
  GPL-3.0 text. The Windows/Excel agent and later Ubuntu evaluation backend are
  also described separately.
- [BrowserART README](https://github.com/scaleapi/browser-art/blob/HEAD/README.md)
  states MIT, while its
  [LICENSE](https://github.com/scaleapi/browser-art/blob/HEAD/LICENSE) contains
  CC-BY-NC-ND-4.0 text.

The records retain both source receipts and the reason for uncertainty. These
observations do not infer permissions for datasets, weights or linked content.

## Pipeline correction

A stale candidate set-aside decision must not suppress an explicit refresh of
an already archived arXiv identity. Harvest now gives retained archive records
precedence, while still skipping absent identifiers that were set aside. A
regression test checks both cases and preservation of retained metadata.

The unresolved AdbGPT link is described using the actual evidence: the requested
identifier had no matching entry in the retained API response. No replacement
identifier or unsupported claim about the end of an arXiv numbering range is
inferred.

Source changes are in `data/editorial.json` and `data/candidate-reviews.json`;
catalog, coverage, reference and documentation views were regenerated. Individual
record evidence and the review queue retain the corresponding review boundaries.
