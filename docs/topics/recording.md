# Recording

[Home](../../README.md) · [All topics](../topics.md) · [Full arXiv bibliography](../papers.md)

23 source-reviewed resources tagged `recording`. Curated metadata, not a performance ranking; unknown facts are shown as —.

**Contents:** [Datasets (1)](#datasets) · [Agents (2)](#agents) · [Frameworks (2)](#frameworks) · [Tools (1)](#tools) · [Infrastructure (1)](#infrastructure) · [Products (1)](#products) · [Papers (15)](#papers)

Benchmarks, datasets, models and systems are ordered by *Mentions*: how many other cataloged resources mention them in their reviewed first-party source (connectedness inside this catalog, not quality or benchmark performance; `·` means none). ✓ links the reviewed source snapshot; hover it for the retrieval date. Papers are newest first.

## Datasets

All entries in this section: Desktop.

| Resource | Mentions | Scale | Description |
| --- | ---: | --- | --- |
| [WorkDemo-350](https://huggingface.co/datasets/yuqi777/WorkDemo-350) [✓](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md "Source checked 2026-10-16")<br>[2610.12984](https://arxiv.org/abs/2610.12984) (2026) · data cc‑by‑4.0 | 1 | [350 demonstrations](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) · [8,388 evidence images](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) · [11,951 action records](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) | Desktop demonstrations with task descriptions, videos, input logs, and action-linked screenshot evidence for studying reusable agent skills. |

## Agents

| Resource | Mentions | Platforms | Description |
| --- | ---: | --- | --- |
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) [✓](https://raw.githubusercontent.com/OpenAdaptAI/OpenAdapt/HEAD/README.md "Source checked 2026-10-16")<br>code MIT | 1 | Desktop | Tools for learning and automating workflows from desktop demonstrations. |
| [ShowUI-Aloha](https://github.com/showlab/ShowUI-Aloha) [✓](https://raw.githubusercontent.com/showlab/ShowUI-Aloha/HEAD/README.md "Source checked 2026-10-16")<br>[2601.07181](https://arxiv.org/abs/2601.07181) (2026) · code Apache‑2.0 | 1 | Desktop, Windows, macOS | Desktop agent that records demonstrations, derives semantic action traces, and uses them to plan and execute related workflows. |

## Frameworks

| Resource | Mentions | Platforms | Description |
| --- | ---: | --- | --- |
| [Work2Skill](https://github.com/china-qijizhifeng/Work2Skill) [✓](https://raw.githubusercontent.com/china-qijizhifeng/Work2Skill/HEAD/README.md "Source checked 2026-10-16")<br>[2610.12984](https://arxiv.org/abs/2610.12984) (2026) · code MIT | 1 | Desktop, macOS, Linux | Collects human GUI demonstrations and inspects multimodal evidence to derive reusable agent workflow skills. |
| [AgentStudio](https://github.com/skyworkai/agent-studio) [✓](https://raw.githubusercontent.com/skyworkai/agent-studio/HEAD/README.md "Source checked 2026-10-18")<br>[2403.17918](https://arxiv.org/abs/2403.17918) (2024) · code AGPL‑3.0 | · | Desktop, Linux | Toolkit and Ubuntu-based environment for building and evaluating generalist computer-use agents through GUI and API interaction. |

## Tools

All entries in this section: Web.

| Resource | Mentions | Description |
| --- | ---: | --- |
| [Browser Use WebUI](https://github.com/browser-use/web-ui) [✓](https://raw.githubusercontent.com/browser-use/web-ui/HEAD/README.md "Source checked 2026-10-17")<br>code MIT | · | A Gradio interface for configuring and running Browser Use agents, including persistent browser sessions and interaction recordings. |

## Infrastructure

All entries in this section: Web, Desktop, Windows, macOS, Linux.

| Resource | Mentions | Description |
| --- | ---: | --- |
| [BrowserOS / BrowserOS neo](https://github.com/browseros-ai/BrowserOS) [✓](https://raw.githubusercontent.com/browseros-ai/BrowserOS/HEAD/README.md "Source checked 2026-10-17")<br>code AGPL‑3.0 | · | Chromium-based browser implementations for external agent control and built-in assistant workflows, with session visibility and replay facilities. |

## Products

All entries in this section: Desktop, Web.

| Resource | Mentions | Publisher | Description |
| --- | ---: | --- | --- |
| [Scribe](https://scribehow.com/) [✓](https://scribehow.com/ "Source checked 2026-10-16") | · | — | Workflow recording and documentation product adjacent to agent data collection. |

## Papers

| Date | Resource | Environments | Description |
| --- | --- | --- | --- |
| 2026‑10‑09 | [Work2Skill: Capturing Human GUI Experience for Reusable Agent Skill Induction](https://arxiv.org/abs/2610.12984) | desktop | Aligns human screen recordings, input events, and accessibility information to derive reusable workflow skills from desktop demonstrations. |
| 2026‑09‑02 | [OmegaUse-SOP: SOP Engineering for Professional Computer Use from Human Demonstrations](https://arxiv.org/abs/2609.02149) | unspecified | OmegaUse-SOP converts expert GUI demonstrations into configurable procedures and refines them with domain rules and human input. It records, abstracts, grounds and verifies live execution, with a case study of photovoltaic simulation workflows in PVsyst 7.2. |
| 2026‑08‑20 | [Inducing Task Models from Computer-Use Traces](https://arxiv.org/abs/2608.20319) | unspecified | Task Model Induction disentangles concurrent activities in screenshot and mouse/keyboard traces, then constructs hierarchical goals and procedural control flow for each task. Evaluation tests reconstruction of observed execution and reuse of derived skills on held-out tasks. |
| 2026‑08‑14 | [LegacyWorld: Atomicity-Aware Evaluation of GUI Agents for Legacy Workflows](https://arxiv.org/abs/2608.14131) | desktop, windows | LegacyWorld evaluates Windows GUI workflows under an atomicity criterion: finish correctly or fail without persistent unintended changes. It compares expert prompts with prompts derived from recorded golden paths and separates useful completion, safe failure and non-atomic side effects. |
| 2026‑06‑17 | [HANSEL: Extracting Breadcrumbs from Web Agent Trajectories for Interactive Verification](https://arxiv.org/abs/2606.18671) | web | HANSEL extracts evidence pages and snippets from browser-agent traces and preserves relevant page state in interactive verification views. It flags untraceable answers and evaluates evidence selection and human verification effort separately. |
| 2026‑06‑16 | [PreAct: Computer-Using Agents that Get Faster on Repeated Tasks](https://arxiv.org/abs/2606.17929) | cross-platform | PreAct compiles successful screen-interaction runs into guarded state-machine programs for repeated tasks. It validates programs from clean states before storage and returns control to the agent when replayed screen expectations fail, with tests across mobile, desktop and web. |
| 2026‑05‑28 | [Syll: Open-Source Personal Automation with Cross-Surface Execution](https://arxiv.org/abs/2606.07594) | desktop, macos | Syll combines tool calls, shell execution and visual GUI control in a personal-automation runtime. It turns user demonstrations into reusable skills and exposes execution logs, keyframes and approval checkpoints for inspection. |
| 2026‑01‑12 | [ShowUI-Aloha: Human-Taught GUI Agent](https://arxiv.org/abs/2601.07181) | desktop | Transforms human screen recordings and input events into annotated demonstrations used by planning and execution components for GUI tasks. |
| 2025‑10‑16 | [GUIrilla: A Scalable Framework for Automated Desktop UI Exploration](https://arxiv.org/abs/2510.16051) | macos, desktop | GUIrilla systematically explores macOS interfaces to collect interaction traces and accessibility metadata for downstream GUI research. It organizes these observations into hierarchical MacApp Trees and describes an accessibility-driven collection library. |
| 2025‑04‑12 | [Explorer: Robust Collection of Interactable GUI Elements](https://arxiv.org/abs/2504.09352) | android, web | Explorer collects interactable GUI elements from a live target application and records user sessions for application-specific model training. It links repeated interface states into a navigation map that supports path planning and voice-directed interaction. |
| 2024‑12‑23 | [PC Agent: While You Sleep, AI Works -- A Cognitive Journey into Digital World](https://arxiv.org/abs/2412.17589) | desktop | Combines PC Tracker interaction capture, completion of action and reasoning annotations, and planning and grounding agents for desktop workflows. |
| 2018 | [Rousillon: Scraping Distributed Hierarchical Web Data](https://doi.org/10.1145/3242587.3242661) | web | Introduces Rousillon, which generalizes a demonstration of collecting one hierarchical data row into a browser-automation program that traverses related pages. The paper develops relation-selection and generalization methods and evaluates users building such scripts. |
| 2017 | [SUGILITE: Creating Multimodal Smartphone Automation by Demonstration](https://doi.org/10.1145/3025453.3025483) | android | Introduces SUGILITE, which combines spoken instructions, demonstrated Android actions, and UI hierarchies to generate reusable automation scripts. Its interface includes context checking and repairs for unfamiliar situations and changing app interfaces. |
| 2016‑11 | [Ringer: Web Automation by Demonstration](https://doi.org/10.1145/2983990.2984020) | web | Introduces Ringer, which converts demonstrated webpage interactions into scripts combining actions, target selectors, and waiting conditions. It evaluates replay robustness on tasks recorded from real websites. |
| 2007 | [Koala: Capture, Share, Automate, Personalize Business Processes on the Web](https://doi.org/10.1145/1240624.1240767) | web | Introduces Koala, a collaborative web automation system that records browser interactions as editable pseudo-natural-language scripts. Scripts are shared through a wiki and instantiated with personal or corporate data for reuse by other users. |
