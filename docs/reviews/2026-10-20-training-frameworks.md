# Source review: MemGUI-Agent and MobileForge

Two implementation repositories were reviewed on 2026-10-20. Their papers were
already in the catalog; these entries identify the documented software assets,
without counting either paper again. The review read each complete root README,
the relevant evaluation or training README, and the root license text. Retained
official GitHub metadata establishes the numeric repository identities. Each
catalog record carries the exact source URLs, timestamps and SHA-256 receipts.

| Repository | Reviewed scope | Code-license finding |
| --- | --- | --- |
| [MemGUI-Agent](https://github.com/kwai/MemGUI-Agent) | Trajectory preparation, LoRA supervised fine-tuning templates, and step-level offline checks of GUI actions and memory. The [evaluator documentation](https://github.com/kwai/MemGUI-Agent/blob/main/evaluation/memgui3k_offline_eval/README.md) describes Android task context and explicitly separates this evaluator from live Android rollouts. | The README declares Apache-2.0, but the inspected [LICENSE](https://github.com/kwai/MemGUI-Agent/blob/main/LICENSE) contains a short notice and link rather than the complete terms. The catalog retains the declaration in its review explanation and leaves the code-license slot unconfirmed. |
| [MobileForge](https://github.com/kwai/MobileForge) | Android-agent adaptation through exploration, generated curricula, rollout feedback and hint-conditioned step-level GRPO. The [public training instructions](https://github.com/kwai/MobileForge/blob/main/training/README.md) specifically cover the Qwen3-VL-8B experiment. | The complete root [LICENSE](https://github.com/kwai/MobileForge/blob/main/LICENSE) supports an Apache-2.0 declaration for repository code. |

The README paper links support `introduced_by` relations to
[MemGUI](https://arxiv.org/abs/2606.19926) and
[MobileForge](https://arxiv.org/abs/2606.19930), respectively. Existing
bibliographic records and versions remain unchanged.

Both repositories are classified as frameworks for their documented training
and evaluation workflows. The Android facet describes the agent task surface;
it is not a claim that the review executed an Android environment. No project
code, benchmark, model weights or external dataset files were run or downloaded
for this review. Linked artifacts, executable release completeness and reported
scores remain unverified. Data, weight and document license slots remain unknown;
the repository code declaration does not transfer to those assets or to
third-party dependencies.
