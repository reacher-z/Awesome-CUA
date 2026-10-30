# Survey manuscript and the later catalog

The English survey is a working manuscript pinned to commit `87166fe8ad9c8e832f7a90ee84b2e93c6e0e40db` and data release [v2026.10.18](https://github.com/reacher-z/Awesome-CUA/releases/tag/v2026.10.18). Its review design says the frozen inventory contained 15 curated survey records, that all 15 received primary-page metadata and a complete abstract check, and that 8 were selected for deeper comparison. This note records how that frozen set relates to catalog commit `fc2aa0c`. The manuscript text and its reading ledger stay at the published snapshot.

The manuscript publisher remains the AwesomeCUA organization.

## Eight surveys used in the prose comparison

These have `read_status` `selected_fulltext_sections_read` in `research/survey/evidence/context.json` and appear in the manuscript.

| Date | Survey | Catalog ID | Scope | Read status |
| --- | --- | --- | --- | --- |
| 2024-11-07 | [GUI Agents with Foundation Models: A Comprehensive Survey](https://arxiv.org/abs/2411.04890) | `arxiv:2411.04890` | core | `selected_fulltext_sections_read` |
| 2024-11-27 | [Large Language Model-Brained GUI Agents: A Survey](https://arxiv.org/abs/2411.18279) | `arxiv:2411.18279` | core | `selected_fulltext_sections_read` |
| 2025-01-27 | [A Comprehensive Survey of Agents for Computer Use: Foundations, Challenges, and Future Directions](https://arxiv.org/abs/2501.16150) | `arxiv:2501.16150` | core | `selected_fulltext_sections_read` |
| 2025-03-30 | [A Survey of WebAgents: Towards Next-Generation AI Agents for Web Automation with Large Foundation Models](https://arxiv.org/abs/2503.23350) | `arxiv:2503.23350` | core | `selected_fulltext_sections_read` |
| 2025-03-30 | [Towards Trustworthy GUI Agents: A Survey](https://arxiv.org/abs/2503.23434) | `arxiv:2503.23434` | core | `selected_fulltext_sections_read` |
| 2025-04-28 | [LLM-Powered GUI Agents in Phone Automation: Surveying Progress and Prospects](https://arxiv.org/abs/2504.19838) | `arxiv:2504.19838` | core | `selected_fulltext_sections_read` |
| 2025-08-06 | [OS Agents: A Survey on MLLM-based Agents for General Computing Devices Use](https://arxiv.org/abs/2508.04482) | `arxiv:2508.04482` | core | `selected_fulltext_sections_read` |
| 2026-09-02 | [Efficient GUI Agents: A Systems Survey of Observation, Memory, Action, and Runtime Optimization](https://arxiv.org/abs/2609.02309) | `arxiv:2609.02309` | core | `selected_fulltext_sections_read` |

## Seven frozen surveys checked and not used in the prose

These were already curated in the frozen catalog. The same evidence file records `primary_metadata_and_complete_abstract_only`. They are absent from the manuscript prose because they were not among the eight selected for deeper comparison. That is the stated selection boundary, not a missed metadata check.

| Date | Survey | Catalog ID | Scope | Read status |
| --- | --- | --- | --- | --- |
| 2024-11-04 | [Foundations and Recent Trends in Multimodal Mobile Agents: A Survey](https://arxiv.org/abs/2411.02006) | `arxiv:2411.02006` | core | `primary_metadata_and_complete_abstract_only` |
| 2024-11-17 | [Generalist Virtual Agents: A Survey on Autonomous Agents Across Digital Platforms](https://arxiv.org/abs/2411.10943) | `arxiv:2411.10943` | core | `primary_metadata_and_complete_abstract_only` |
| 2024-12-18 | [GUI Agents: A Survey](https://arxiv.org/abs/2412.13501) | `arxiv:2412.13501` | core | `primary_metadata_and_complete_abstract_only` |
| 2025-03-27 | [A Survey on (M)LLM-Based GUI Agents](https://arxiv.org/abs/2504.13865) | `arxiv:2504.13865` | core | `primary_metadata_and_complete_abstract_only` |
| 2025-04-29 | [A Survey on GUI Agents with Foundation Models Enhanced by Reinforcement Learning](https://arxiv.org/abs/2504.20464) | `arxiv:2504.20464` | core | `primary_metadata_and_complete_abstract_only` |
| 2025-05-16 | [A Survey on the Safety and Security Threats of Computer-Using Agents: JARVIS or Ultron?](https://arxiv.org/abs/2505.10924) | `arxiv:2505.10924` | core | `primary_metadata_and_complete_abstract_only` |
| 2026-02-12 | [Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward](https://arxiv.org/abs/2602.12430) | `arxiv:2602.12430` | adjacent | `primary_metadata_and_complete_abstract_only` |

## Four surveys curated after the snapshot

Catalog commit `fc2aa0c` has 19 curated surveys. Four were not curated surveys in the frozen catalog. All four have scope `adjacent`.

| Date | Survey | Catalog ID | Scope | Frozen catalog |
| --- | --- | --- | --- | --- |
| 2024-02-15 | [A Trembling House of Cards? Mapping Adversarial Attacks against Language Agents](https://arxiv.org/abs/2402.10196) | `arxiv:2402.10196` | adjacent | not present |
| 2026-04-17 | [A Survey on Long-Term Memory Security in LLM Agents: Attacks, Defenses, and Governance Across the Memory Lifecycle](https://arxiv.org/abs/2604.16548) | `arxiv:2604.16548` | adjacent | not present |
| 2026-08-30 | [A Systematic Survey of Agentic Skills: Architecture, Lifecycle, and Security](https://arxiv.org/abs/2608.29596) | `arxiv:2608.29596` | adjacent | not present |
| 2026-10-14 | [Seeing, Maintaining, and Learning: The Evolution of Multimodal Agent Memory](https://arxiv.org/abs/2610.19366) | `arxiv:2610.19366` | adjacent | metadata_verified paper relevance_pending |

`adjacent` is the catalog scope for supporting material. It does not by itself put a record into the manuscript comparison set. See [methodology](methodology.md).

## Selection is not a missing catalog record

The manuscript does not name every curated benchmark, model, dataset, or agent. These papers were already curated in the frozen catalog and do not appear by name in the manuscript prose: AutoGLM (`arxiv:2411.00820`), GUI-World (`arxiv:2406.10819`), VideoGUI (`arxiv:2406.10227`), ScienceBoard (`arxiv:2505.19897`), MacArena (`arxiv:2606.06560`), and OSWorld 2.0 (`arxiv:2606.29537`). Windows Agent Arena does appear. Inserting them without a new reading record would go past the manuscript evidence rule.

Tracked as [issue 4343](https://github.com/reacher-z/Awesome-CUA/issues/4343).
