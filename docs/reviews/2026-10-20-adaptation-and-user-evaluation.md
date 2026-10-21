# Recent arXiv source review: adaptation and user evaluation

Four metadata-only papers received content review on 20 October 2026. The review
used complete retained official abstracts and selected exact-v1 methods,
evaluation and limitation sections. Each annotation had an independent second
source review. Original bibliography, versions and API receipt times remain
unchanged.

| Paper | Reviewed contribution | Conditions retained in the annotation |
| --- | --- | --- |
| [MAGE: Adaptation of Computer Use Agents to New Software with User Manuals](https://arxiv.org/html/2610.23012v1), 16 October | Manual retrieval supplies a fixed execution plan; a separate task-generation and rollout pipeline trains application-specific policies with GRPO. | Plans stay fixed within an episode. Screenshot-based success judgments can miss task conditions, and OSWorld tasks may overlap backbone training data. |
| [WebMix: Don't Retrain, Remix](https://arxiv.org/html/2610.22539v1), 15 October | An interface scout supplies a manual to a router that combines source-trained adapters. | Target-time adaptation makes no gradient updates. Source components are trained, and domain scouting uses target task intents and answer-stripped reference procedures; version scouting is task-free. |
| [PersonaCUABench](https://arxiv.org/html/2610.22990v1), 16 October | Fixed web tasks receive different simulated user requests and clarification dialogues; evaluation separates completion, requirement handling and satisfaction. | Main interactions and satisfaction ratings use simulated personas. Human annotations validate selected outputs. The acting harness observes page text; screenshots serve auditing. Demographic findings do not generalize to real populations. |
| [MobileJailBench](https://arxiv.org/html/2610.23303v1), 16 October | Feedback-driven attack evaluation and separately admitted task expansion accompany evidence-based outcome diagnosis. | The runtime is a browser-based Android-like simulator. The attacker controls instructions and designated carriers, with no privileged simulator or system access. Diagnostic labels describe observable expressions/actions, and unresolved episodes are excluded from rate denominators. |

The two evaluation papers use `web` as their recorded execution environment.
MobileJailBench's mobile-navigation topic describes its simulated mobile tasks;
it does not establish Android process isolation or live-service execution.
PersonaCUABench's human-in-the-loop topic describes the clarification workflow,
while the annotation identifies its simulated participants.

All four reviews were adopted. No experiments were independently reproduced, no
project code was executed, and code, data, weights and license releases were not
verified in this review. The source reads add no new search-query population or
duplicate paper identities.
