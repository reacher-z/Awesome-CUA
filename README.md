<h1 align="center"><a href="https://awesomecua.com/"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/brand/readme-banner-dark.svg"><img src="assets/brand/readme-banner-light.svg" alt="Awesome CUA: computer-use agent research, data and tools connected to original sources" width="960"></picture></a></h1>

A source-backed collection of papers, models, datasets, benchmarks and tools for agents that use computers.

**English** · [简体中文](README.zh-CN.md)

**[Search the website](https://awesomecua.com/)** · **[Papers](https://awesomecua.com/papers/)** · **[Topics](https://awesomecua.com/topics/)** · **[Data](https://awesomecua.com/data/)** · **[Agent guide](https://awesomecua.com/agents/)** · **[Contribute](CONTRIBUTING.md)**

If this collection is useful, a [star on GitHub](https://github.com/reacher-z/Awesome-CUA) helps others find it.

<!-- BADGES:START -->
[![Curated resources](https://img.shields.io/badge/curated%20resources-5%2C215-4352E8?style=flat-square&labelColor=1E2233)](docs/coverage.md) [![Reviewed papers and surveys](https://img.shields.io/badge/reviewed%20papers%20and%20surveys-1%2C718-4352E8?style=flat-square&labelColor=1E2233)](docs/papers.md) [![Last successful scan](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Freacher-z%2FAwesome-CUA%2Fstatus%2Fscan-badge.json&style=flat-square&labelColor=1E2233)](docs/maintenance.md#scan-badge) [![Hugging Face dataset](https://img.shields.io/badge/dataset-Hugging%20Face-4352E8?style=flat-square&labelColor=1E2233)](https://huggingface.co/datasets/TIGER-Lab/AwesomeCUA) [![MIT license](https://img.shields.io/badge/license-MIT-5E6472?style=flat-square&labelColor=1E2233)](LICENSE)
<!-- BADGES:END -->

Curated entries were reviewed against a first-party source snapshot; records awaiting review have their bibliographic identity checked; candidates are discovered identifiers awaiting resolution. [What “verified” means](#what-verified-means) · [Coverage ledger](docs/coverage.md)

## Featured benchmarks

| Website reconstruction                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Browser agents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| <a href="https://github.com/TIGER-AI-Lab/WebsiteBench"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/TIGER-AI-Lab/WebsiteBench/78f5558e8197bb91b3bab63428c12b92060ddc6f/assets/wordmark-dark.svg"><img src="https://raw.githubusercontent.com/TIGER-AI-Lab/WebsiteBench/78f5558e8197bb91b3bab63428c12b92060ddc6f/assets/wordmark-light.svg" alt="WebsiteBench" height="32"></picture></a><br>Can AI agents rebuild websites through browser exploration?<br>[★ Star on GitHub](https://github.com/TIGER-AI-Lab/WebsiteBench) | <a href="https://github.com/TIGER-AI-Lab/ClawBench"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/TIGER-AI-Lab/ClawBench/c8409629f4f2f9768731350d764aeb3035946c5d/assets/brand/wordmark-dark.svg"><img src="https://raw.githubusercontent.com/TIGER-AI-Lab/ClawBench/c8409629f4f2f9768731350d764aeb3035946c5d/assets/brand/wordmark-light.svg" alt="ClawBench" height="32"></picture></a><br>Open-source benchmark for browser AI agents on daily tasks.<br>[★ Star on GitHub](https://github.com/TIGER-AI-Lab/ClawBench) |

**Featured:** [Awesome Reverse Engineering Anything](https://github.com/reacher-z/Awesome-REA) — a collection of tools, case studies and research for reverse-engineering websites, games, apps, native binaries, firmware and protocols.

<!-- TASKS:START -->
## Find by task

| Your task           | Start here                                                                                                                                                     | What you can find                                                                                                                            |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Find papers         | [Research library](https://awesomecua.com/papers/) · [Topics](https://awesomecua.com/topics/) · [Paper–asset connections](https://awesomecua.com/connections/) | Reviewed papers by year and topic, with original sources and the code, datasets and models linked to them through reviewed primary evidence. |
| Choose a benchmark  | [Benchmark guide](https://awesomecua.com/guides/gui-agent-benchmarks/)                                                                                         | Platforms, tasks, evaluators, and versions to compare.                                                                                       |
| Find training data  | [Training-data guide](https://awesomecua.com/guides/gui-agent-training-data/)                                                                                  | Supervision, splits, count units, and data licenses.                                                                                         |
| Build an agent      | [Agents](https://awesomecua.com/categories/agent/) · [Frameworks](https://awesomecua.com/categories/framework/)                                                | Implementation entry points, supported platforms, and papers.                                                                                |
| Use RAG or an agent | [Agent guide](https://awesomecua.com/agents/) · [Data hub](https://awesomecua.com/data/)                                                                       | Complete records or retrieval documents with review states and sources.                                                                      |

<details>
<summary>Local examples (after cloning; Python 3.11+, no dependencies required)</summary>

```sh
cd Awesome-CUA
python3 scripts/catalog.py search "grounding" --kind paper --status curated --limit 0 --json
python3 scripts/catalog.py search --kind benchmark --environment web --status curated --limit 0 --json
python3 scripts/catalog.py search --kind dataset --environment android --status curated --limit 0 --json
python3 scripts/catalog.py search --kind framework --status curated --limit 0 --json
python3 scripts/export_rag.py --output dist/rag-documents.jsonl
python3 scripts/catalog.py get arxiv:2404.07972 --related --json
```

</details>

<!-- TASKS:END -->

<!-- STATS:START -->

**5,215 curated resources** · **1,718 reviewed papers and surveys** · **104 discovery documents**

Evidence through `2026-11-10T03:01:53Z`. **906 records awaiting review** have verified bibliographic metadata, and **525 discovered candidates** await resolution. 1,774 candidates have an out-of-scope review. 1,308 scope exclusions retain their original metadata in the archive.

<!-- STATS:END -->

## Explore

<!-- EXPLORE:START -->
| Browse                                           | What you find                                                 | Entries |
| ------------------------------------------------ | ------------------------------------------------------------- | ------: |
| [Research by topic](docs/topics.md)              | Reviewed papers grouped by topic                              |   1,681 |
| [Full bibliography](docs/papers.md)              | All paper and survey records, including those awaiting review |   2,624 |
| [Surveys](docs/surveys.md)                       | Surveys of computer-use agent research                        |      37 |
| [Learning resources](docs/learning.md)           | Courses and tutorials                                         |      36 |
| [Datasets](docs/datasets.md)                     | Training and evaluation data for GUI agents                   |     267 |
| [Benchmarks](docs/benchmarks.md)                 | Evaluation environments and task suites                       |     305 |
| [Models and checkpoint releases](docs/models.md) | Checkpoints and model families                                |     454 |
| [Agents](docs/agents.md)                         | Open implementations that act on a computer                   |     475 |
| [Frameworks](docs/frameworks.md)                 | Code for building and evaluating agents                       |     665 |
| [Infrastructure](docs/infrastructures.md)        | Sandboxes, VMs, device farms and environments                 |     117 |
| [Tools](docs/tools.md)                           | Evaluation harnesses, recorders and other utilities           |   1,084 |
| [Products](docs/products.md)                     | Computer-use products from vendors and projects               |      75 |
| [Publishers and brands](docs/companies.md)       | Publishers and brands connected to cataloged resources        |      19 |

**By platform:** [Web](docs/environments/web.md) **2,678** · [Desktop](docs/environments/desktop.md) **1,801** · [Windows](docs/environments/windows.md) **571** · [macOS](docs/environments/macos.md) **582** · [Linux](docs/environments/linux.md) **533** · [Android](docs/environments/android.md) **720** · [iOS](docs/environments/ios.md) **105** · [HarmonyOS](docs/environments/harmonyos.md) **7** · [Cross-platform](docs/environments/cross-platform.md) **756**
<!-- EXPLORE:END -->

Coverage spans web, desktop, Android, iOS, Windows, macOS, Linux, and cross-platform work. Topics include grounding, screen understanding, planning, memory, long-horizon workflows, reinforcement learning, data generation, safety, robustness, and evaluation.

## Use the data

Download the catalog, feeds and RAG documents; the data hub also lists sources, review states and schemas.

- [llms.txt](https://awesomecua.com/llms.txt) - Navigation file for language models.
- [llms-full.txt](https://awesomecua.com/llms-full.txt) - Curated annotations in Markdown.
- [Data hub](https://awesomecua.com/data/) - Catalog, RAG documents, citations, topics, comparisons, sources and schemas in six groups.
- [Catalog JSONL](https://awesomecua.com/downloads/catalog.jsonl) - Complete catalog with one resource per line.
- [Download manifest](https://awesomecua.com/downloads/manifest.json) - Export counts, byte sizes and SHA-256 checksums.
- [Atom feed](https://awesomecua.com/feed.xml) - Research updates as an Atom feed.
- [Hugging Face dataset](https://huggingface.co/datasets/TIGER-Lab/AwesomeCUA) - Read-only mirror; metadata_only and github_candidates are unreviewed.
- [Agent and RAG guide](https://awesomecua.com/agents/) - Guide for agents and RAG systems.

Clone the complete catalog:

```sh
git clone https://github.com/reacher-z/Awesome-CUA.git
```

[Agent instructions](AGENTS.md) · [Retrieval documents](https://awesomecua.com/downloads/rag-documents.jsonl)

Discovery is scheduled **at 00:07, 08:07 and 16:07 UTC**. [Actual scan results](https://awesomecua.com/updates/) · [Schedule and safeguards](docs/maintenance.md).

[Read the research survey](https://awesomecua.com/survey/) — Methods, evaluation, human agency, and reusable research assets. English working manuscript with a versioned bibliography and reading register.

## Highlights

The most-mentioned curated resources per category: the count is how many other cataloged resources mention each one in their reviewed first-party source (README, model or dataset card). It reflects connectedness inside this catalog. Every category page lists all reviewed entries. Surveys come first, newest first.

<details>
<summary>Show the highlights tables</summary>

<!-- HIGHLIGHTS:START -->
**Start with the newest surveys** · [all 37 →](docs/surveys.md)

| Date       | Survey                                                                                                                                  | Environments   |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| 2026‑11‑04 | [GUI Grounding for Computer-Use Agents: A Survey](https://doi.org/10.20944/preprints202611.0431.v1)                                     | unspecified    |
| 2026‑10‑21 | [Multimodal Embodied Agents: A Unified Capability-centric Perspective from Computer-Use to Robot-Use](https://arxiv.org/abs/2610.30108) | unspecified    |
| 2026‑10‑14 | [Seeing, Maintaining, and Learning: The Evolution of Multimodal Agent Memory](https://arxiv.org/abs/2610.19366)                         | unspecified    |
| 2026‑09‑02 | [Efficient GUI Agents: A Systems Survey of Observation, Memory, Action, and Runtime Optimization](https://arxiv.org/abs/2609.02309)     | cross-platform |
| 2026‑08‑30 | [A Systematic Survey of Agentic Skills: Architecture, Lifecycle, and Security](https://arxiv.org/abs/2608.29596)                        | cross-platform |

**Benchmarks** · [all 305 →](docs/benchmarks.md)

| Resource                                                                       | Mentions | Environments                   | Paper                                                 | License         | Description                                                                         |
| ------------------------------------------------------------------------------ | -------: | ------------------------------ | ----------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------- |
| [OSWorld](https://github.com/xlang-ai/OSWorld)                                 |       60 | desktop, linux, windows, macos | [2404.07972](https://arxiv.org/abs/2404.07972) (2024) | code Apache-2.0 | Execution-based evaluation of agents performing tasks in real desktop environments. |
| [WebArena](https://github.com/web-arena-x/webarena)                            |       31 | web                            | [2307.13854](https://arxiv.org/abs/2307.13854) (2023) | code Apache-2.0 | Self-hosted web environments and tasks for evaluating autonomous web agents.        |
| [AndroidWorld](https://github.com/google-research/android_world)               |       21 | android                        | [2405.14573](https://arxiv.org/abs/2405.14573) (2024) | code Apache-2.0 | Android environment with programmatic task evaluation for mobile agents.            |
| [BrowserGym](https://github.com/ServiceNow/BrowserGym)                         |       16 | web                            | [2412.05467](https://arxiv.org/abs/2412.05467) (2024) | code Apache-2.0 | Unified interfaces for browser-agent tasks and benchmark environments.              |
| [ScreenSpot Pro](https://github.com/likaixin2000/ScreenSpot-Pro-GUI-Grounding) |       15 | desktop, windows, macos, linux | —                                                     | code MIT        | GUI grounding benchmark focused on professional high-resolution interfaces.         |
| [VisualWebArena](https://github.com/web-arena-x/visualwebarena)                |       14 | web                            | [2401.13649](https://arxiv.org/abs/2401.13649) (2024) | —               | Visually grounded web tasks extending the WebArena evaluation setting.              |

**Models** · [all 454 →](docs/models.md)

| Resource                                                                 | Mentions | Environments   | Paper                                                 | License            | Description                                                                                                                                                           |
| ------------------------------------------------------------------------ | -------: | -------------- | ----------------------------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [UI-TARS](https://github.com/bytedance/UI-TARS)                          |       25 | cross-platform | [2501.12326](https://arxiv.org/abs/2501.12326) (2025) | code Apache-2.0    | Native GUI agent models; UI-TARS-1.5 adds reinforcement-learned reasoning before acting and an open 7B checkpoint, and UI-TARS-2 extends to games, code and tool use. |
| [SeeClick](https://github.com/njucckevin/SeeClick)                       |       18 | cross-platform | [2401.10935](https://arxiv.org/abs/2401.10935) (2024) | code Apache-2.0    | GUI grounding model trained to locate visual interface elements.                                                                                                      |
| [Qwen2-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct) |       11 | unspecified    | —                                                     | weights apache-2.0 | An instruction-tuned 7B multimodal model for image and video understanding; its card describes visually guided operation of mobile devices.                           |
| [Aguvis](https://github.com/xlang-ai/aguvis)                             |        8 | cross-platform | [2412.04454](https://arxiv.org/abs/2412.04454) (2024) | —                  | Vision-based GUI agent models with unified action representations.                                                                                                    |
| [GUI-Actor](https://github.com/microsoft/GUI-Actor)                      |        7 | cross-platform | [2506.03143](https://arxiv.org/abs/2506.03143) (2025) | code MIT           | GUI grounding model with attention-based action localization.                                                                                                         |
| [OpenCUA](https://github.com/xlang-ai/OpenCUA)                           |        7 | desktop        | [2508.09123](https://arxiv.org/abs/2508.09123) (2025) | code MIT           | Open computer-use research stack including models and training resources.                                                                                             |

**Datasets** · [all 267 →](docs/datasets.md)

| Resource                                                                       | Mentions | Environments                          | Paper                                                 | License         | Description                                                                                                                                                                                 |
| ------------------------------------------------------------------------------ | -------: | ------------------------------------- | ----------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [ScreenSpot-Pro data](https://huggingface.co/datasets/likaixin/ScreenSpot-Pro) |       12 | desktop, windows, macos, linux        | [2504.07981](https://arxiv.org/abs/2504.07981) (2025) | data mit        | High-resolution professional interface screenshots and target annotations for evaluating instruction-based GUI localization.                                                                |
| [OS-Genesis](https://github.com/OS-Copilot/OS-Genesis)                         |       11 | cross-platform                        | [2412.19723](https://arxiv.org/abs/2412.19723) (2024) | —               | Interaction-driven pipeline that synthesizes mobile and web GUI agent trajectories without human supervision or predefined tasks, via reverse task synthesis and a trajectory reward model. |
| [AMEX dataset release](https://huggingface.co/datasets/Yuxiang007/AMEX)        |        7 | android                               | [2407.17490](https://arxiv.org/abs/2407.17490) (2024) | data cc-by-4.0  | Official Hub release of AMEX: Android app screenshots annotated for interactive-element grounding, screen and element functionality, and instructions with stepwise GUI-action chains.      |
| [Holo4 Trajectories](https://huggingface.co/datasets/Hcompany/trajectories)    |        6 | web, desktop, android, cross-platform | —                                                     | data apache-2.0 | Dataset of 7,366 computer-use agent execution trajectories from Holo4 27B and Holo4 35B-A3B, recording step-level reasoning, actions, tool results, and screenshots.                        |
| [GroundCUA dataset](https://huggingface.co/datasets/ServiceNow/GroundCUA)      |        5 | desktop, windows, macos, linux        | [2511.07332](https://arxiv.org/abs/2511.07332) (2025) | data mit        | Desktop GUI-grounding data from the GroundCUA project: PNG screenshots of 87 applications paired by hash with JSON lists of element boxes, visible text and optional coarse categories.     |
| [GUI-Actor data](https://huggingface.co/datasets/cckevinn/GUI-Actor-Data)      |        5 | unspecified                           | [2506.03143](https://arxiv.org/abs/2506.03143) (2025) | —               | A processed screenshot and bounding-box collection released for training GUI-Actor visual grounding models.                                                                                 |

**Frameworks** · [all 665 →](docs/frameworks.md)

| Resource                                                                                             | Mentions | Environments | Paper                                                 | License  | Description                                                                                                                                                                                       |
| ---------------------------------------------------------------------------------------------------- | -------: | ------------ | ----------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Browser Use](https://github.com/browser-use/browser-use)                                            |       58 | web          | —                                                     | code MIT | Open-source browser agent library that runs locally with any LLM against a local or cloud browser, and also serves as a CLI for coding agents and as a driver for Claude's browser toolset.       |
| [Cua](https://github.com/trycua/cua)                                                                 |       41 | desktop      | —                                                     | code MIT | Monorepo behind Cua Spaces, which gives agents full macOS or Linux desktops, plus Cua Driver for operating native apps, Lume for Apple Silicon VMs, Cua Bench and the CUA-S1 decision models.     |
| [Epic EHR Browser Automation](https://github.com/Browser-Automation-Hub/epic-ehr-browser-automation) |       13 | web          | —                                                     | code MIT | A browser automation scaffold for Epic EHR workflows such as appointments, patient lookup, notes and messaging. It documents authentication, sessions and example actions.                        |
| [SCALE-CUA (THUDM)](https://github.com/THUDM/SCALE-CUA)                                              |       12 | desktop      | [2607.11185](https://arxiv.org/abs/2607.11185) (2026) | —        | Computer-use training framework with VeriGen task synthesis, adaptive rollout sampling, and visual-context segmentation.                                                                          |
| [Stagehand](https://github.com/browserbase/stagehand)                                                |        9 | web          | —                                                     | code MIT | Browser automation framework combining code and natural-language actions.                                                                                                                         |
| [WebMCP](https://github.com/webmachinelearning/webmcp)                                               |        9 | web          | —                                                     | —        | A client-side web API proposal that lets pages expose structured JavaScript tools to browser agents. Agents can invoke page functions while sharing the visible interface and context with users. |

**Agents** · [all 475 →](docs/agents.md)

| Resource                                                     | Mentions | Environments                                        | Paper                                                                                                                                                                                                                      | License         | Description                                                                                                                                                                                             |
| ------------------------------------------------------------ | -------: | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Mobile-Agent](https://github.com/X-PLUG/MobileAgent)        |       27 | android, cross-platform                             | [2401.16158](https://arxiv.org/abs/2401.16158) (2024), [2406.01014](https://arxiv.org/abs/2406.01014) (2024), [2508.15144](https://arxiv.org/abs/2508.15144) (2025), [2602.16855](https://arxiv.org/abs/2602.16855) (2026) | code MIT        | Mobile device agent family using visual interface interaction.                                                                                                                                          |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) |       26 | cross-platform, desktop, web, linux, macos, windows | —                                                                                                                                                                                                                          | code MIT        | Hermes Agent is a self-improving autonomous agent by Nous Research with procedural skill synthesis, browser control, and multi-platform sandboxes.                                                      |
| [OpenAI Codex CLI](https://github.com/openai/codex)          |       16 | cross-platform, desktop, macos, linux, windows      | —                                                                                                                                                                                                                          | code Apache-2.0 | OpenAI Codex CLI is a local terminal and desktop coding agent that executes commands and edits files inside OS-enforced sandboxes.                                                                      |
| [OpenClaw](https://github.com/openclaw/openclaw)             |       16 | cross-platform, desktop, web, macos, windows, linux | —                                                                                                                                                                                                                          | code MIT        | OpenClaw is an open-source personal computer-use assistant that executes browser, desktop, terminal, and messaging workflows across local devices.                                                      |
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt)        |       11 | desktop                                             | —                                                                                                                                                                                                                          | code MIT        | Tools for learning and automating workflows from desktop demonstrations.                                                                                                                                |
| [Agent S](https://github.com/simular-ai/Agent-S)             |       10 | desktop                                             | [2410.08164](https://arxiv.org/abs/2410.08164) (2024), [2504.00906](https://arxiv.org/abs/2504.00906) (2025), [2510.02250](https://arxiv.org/abs/2510.02250) (2025)                                                        | code Apache-2.0 | Simular's open-source framework for computer-use agents that click, type and scroll through desktop and web apps on macOS, Windows and Linux; its third generation, Agent S3, reports 72.6% on OSWorld. |

<!-- HIGHLIGHTS:END -->

</details>

## Recently reviewed

Newest editorial approvals of models, datasets, benchmarks, systems, and tools (newest first). New papers appear by date in the [topic hubs](docs/topics.md).

<details>
<summary>Show the recently reviewed table</summary>

<!-- RECENT:START -->
| Reviewed   | Resource                                                                                                         | Kind      | Environments | Description                                                                                                                                                                                                         |
| ---------- | ---------------------------------------------------------------------------------------------------------------- | --------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026‑11‑10 | [UXAgent](https://uxagent.hailab.io)                                                                             | framework | web          | Usability-testing system that generates simulated user personas, has LLM agents work through a target website via a browser connector, and shows their survey answers and action logs in a result viewer.           |
| 2026‑11‑10 | [Muse Spark 1.1](https://ai.meta.com/blog/introducing-muse-spark-meta-model-api)                                 | model     | desktop, web | Meta Superintelligence Labs multimodal reasoning model for agentic work, trained to choose between writing scripts and clicking in computer-use workflows that span several applications.                           |
| 2026‑11‑10 | [Indeed-UI-8B](https://www.modelscope.cn/models/IntellgenceIndeed/Indeed-UI-8B)                                  | model     | unspecified  | GUI grounding model fine-tuned from GUI-Owl 1.5-8B with grounding data and high-resolution training; the card reports 73.4 on ScreenSpot-Pro, 94.4 on ScreenSpot-V2 and 68.3 on OSWorld-G.                          |
| 2026‑11‑10 | [GPT-6 Astra](https://openai.com/index/gpt-6-astra)                                                              | model     | desktop, web | General OpenAI model whose launch post covers computer use and browsing; OpenAI reports 72.6% on OSWorld 2.0 at about 40 minutes per task, plus ScreenSpot-Pro and Mind2Web results.                                |
| 2026‑11‑10 | [Adept Fuyu-Heavy](https://www.adept.ai/blog/adept-fuyu-heavy)                                                   | model     | unspecified  | Adept multimodal model that scales up the Fuyu architecture for digital agents, aimed mainly at UI understanding; Adept reports MMMU, VQAv2, AI2D and ChartQA scores against Gemini models.                         |
| 2026‑11‑10 | [webarena-world-model-rlvr](https://huggingface.co/thuml/webarena-world-model-rlvr)                              | model     | web          | A language world model for web page state prediction on WebArena, post-trained with RLVR from an SFT checkpoint and used for model predictive control of web agents.                                                |
| 2026‑11‑10 | [TimeWarp-GPT5-Traces](https://huggingface.co/datasets/sparklabutah/TimeWarp-GPT5-Traces)                        | dataset   | web          | GPT-5 teacher trajectories on the TimeWarp web benchmark, grouped by UI version, with SoM-annotated screenshots for each step and experiment logs, used to fine-tune web agents with LlamaFactory.                  |
| 2026‑11‑10 | [TianXi_Action_Grounding_7B](https://huggingface.co/tangliang/TianXi_Action_Grounding_7B)                        | model     | desktop      | A 7B GUI action-grounding model from the SEA computer-use agent work, released as Qwen2_5_VL safetensors weights; its GitHub repository runs it on ScreenSpot-Pro across instruction styles and languages.          |
| 2026‑11‑10 | [Qwen3-VL-8B-Instruct-MobileWorld-SFT](https://huggingface.co/jacklishufan/Qwen3-VL-8B-Instruct-MobileWorld-SFT) | model     | android      | Qwen3-VL-8B-Instruct fine-tuned on the MobileWorld dataset as a semantic world model that describes in natural language how a mobile GUI screen changes after an action, for planning by mobile agents.             |
| 2026‑11‑10 | [OpenWebVoyager-opt-2](https://huggingface.co/OpenWebVoyager/OpenWebVoyager-opt-2)                               | model     | web          | The second optimization-iteration checkpoint of OpenWebVoyager, an idefics2-8b multimodal web agent trained by imitation learning and then refined on successful real-website trajectories kept by GPT-4o feedback. |
| 2026‑11‑10 | [OpenPhone_dataset](https://huggingface.co/datasets/hkuds/OpenPhone_dataset)                                     | dataset   | android      | Training data for the OpenPhone mobile agent: the AndroidLab training archive plus a Hugging Face vision-language set with LLM-generated reasoning and reflection chains, formatted for GRPO training.              |
| 2026‑11‑10 | [InternVL3_5-2B](https://huggingface.co/OpenGVLab/InternVL3_5-2B)                                                | model     | unspecified  | InternVL3.5-2B checkpoint with a 0.3B vision encoder and 2.0B language model, from a multimodal family trained with Cascade RL that lists GUI interaction among its capabilities.                                   |
<!-- RECENT:END -->

</details>

## Data files and local queries

Browse the [interactive website](https://awesomecua.com/) to search and filter all resources, inspect source evidence, switch between English and Chinese, or download the complete catalog. [Website development and publishing](docs/website.md).

The [English data hub](https://awesomecua.com/data/) and [中文数据中心](https://awesomecua.com/zh/data/) organize public downloads into six groups: complete catalog, RAG documents, citations, topics and comparisons, sources and review status, and schemas. Cloning still gives you the complete source catalog; the hub provides exports from its published snapshot.

The [download manifest](https://awesomecua.com/downloads/manifest.json) records each listed export's actual count and unit, scope, byte size, and SHA-256 fingerprint. Compare `catalog_sha256` across manifests before combining files from different downloads.

[Reviewed research](https://awesomecua.com/papers/) · [Computer-use agent guides](https://awesomecua.com/guides/) · [Static resource directory](https://awesomecua.com/catalog/) · [Search and AI discovery](docs/search-discovery.md)

- **[Catalog JSONL](https://github.com/reacher-z/Awesome-CUA/blob/main/data/catalog.jsonl):** one resource per line, with stable IDs, typed fields, provenance, scoped licenses, and review status.
- **[Reference graph](https://github.com/reacher-z/Awesome-CUA/blob/main/data/references.jsonl):** outbound references from primary sources.
- **[Discovery registry](https://github.com/reacher-z/Awesome-CUA/blob/main/data/sources.json)** and **[candidates](data/candidates.jsonl):** source snapshots and where each identifier was found.
- **[Review queue](https://github.com/reacher-z/Awesome-CUA/blob/main/data/review-queue.jsonl):** unresolved evidence, unindexed discoveries, and proposals requiring editorial work. Discovered links reviewed as non-resources or as other addresses of indexed resources stay listed with a `resolution` and their reason.
- **[JSON Schema](https://github.com/reacher-z/Awesome-CUA/blob/main/schemas/resource.schema.json)** and **[coverage JSON](data/coverage.json):** machine-checkable contracts and coverage accounting.
- **[BibTeX](https://awesomecua.com/downloads/citations.bib)** and **[CSL JSON](https://awesomecua.com/downloads/citations.csl.json):** reviewed-paper citations with recorded authors, dates, and versions. Each resource page also provides its own `record.json`.

```bash
# Python 3.11+. Search and export require only the standard library.
cd Awesome-CUA
python3 scripts/catalog.py search "grounding" --kind model
python3 scripts/catalog.py search --kind dataset --environment android
python3 scripts/catalog.py search --kind product --status curated --json
python3 scripts/catalog.py get arxiv:2404.07972 --related --json
python3 scripts/catalog.py build
# Creates dist/catalog.sqlite and dist/catalog.json, with no network calls.
python3 scripts/export_rag.py --output dist/rag-documents.jsonl
python3 scripts/export_citations.py --format bibtex --output dist/citations.bib
# Add --include-metadata to include every active record, with its review state intact.
```

Use SQLite to join resources, environment/topic facets, and reviewed relations. See [query examples](docs/query-guide.md). `data/catalog.jsonl` is committed; SQLite and JSON array exports are reproducible local build products.

## What “verified” means

| State               | What has been checked                                                                                            |
| ------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `curated`           | Name, scope, summary, and taxonomy reviewed against a first-party source snapshot                                |
| `metadata_verified` | Bibliographic identity, title, authors, and recorded dates checked against retained arXiv or publication sources |
| `candidate`         | A normalized URL or identifier was discovered                                                                    |

A paper, repository, dataset release, model checkpoint, product, and publisher can be separate related resources. Model families and individual checkpoints are explicitly linked where reviewed.

Code, data, weights, and document licenses are separate. Missing values are `null`.

## Maintain and verify

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.txt
.venv/bin/python scripts/catalog.py validate
.venv/bin/python scripts/catalog.py build --check
.venv/bin/python scripts/run_tests.py
.venv/bin/python scripts/catalog.py build
node --test tests/web.test.mjs
.venv/bin/python scripts/build_site.py
```

These commands match the checks that [Catalog quality](.github/workflows/catalog.yml) runs on every push and pull request, in the same order. They need Python 3.11+ and Node.js 24+, the `engines` version in `package.json` (CI uses Python 3.12 and Node.js 24). The web tests use only the built-in Node.js test runner, so nothing needs to be installed with npm. `npm run test:web` and `npm run build:web` are shortcuts for the last two commands.

Network discovery and verification are explicit commands; ordinary builds are offline. Changed primary snapshots require another editorial review before publication. [Maintenance guide](docs/maintenance.md) · [Methodology](docs/methodology.md) · [Data dictionary](docs/data-dictionary.md)

## Acknowledgments and reuse

The [source registry](data/sources.json) credits the community collections and surveys used for discovery. Bibliographic records use retained arXiv, publisher, and author sources; publication observations preserve edition-specific titles, authors, and date precision. Selected assets are checked against publisher repositories, documentation, and model/dataset cards. Upstream READMEs, papers, model weights, and datasets are not redistributed here.

Original repository code and annotations use the [MIT license](LICENSE). Linked resources retain their own terms.

To cite the catalog, use [CITATION.cff](CITATION.cff) or GitHub's "Cite this repository" button. The data changes with every scan, so pin the exact version you used. Each `v*` tag has a [data release](https://github.com/reacher-z/Awesome-CUA/releases) with versioned downloads built from the tagged commit: the catalog as JSONL, JSON and SQLite, the coverage ledger, topic and profile exports, and their `SHA256SUMS`. Cite the release tag, or record the commit from `git rev-parse HEAD` in your clone, or link files at that commit, such as `https://github.com/reacher-z/Awesome-CUA/blob/<commit>/data/catalog.jsonl`. [Cutting a release](docs/maintenance.md#versioned-data-releases).

<!-- STAR_HISTORY:START -->

## Star History

<a href="https://www.star-history.com/#reacher-z/Awesome-CUA&amp;Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=reacher-z/Awesome-CUA&amp;type=Date&amp;theme=dark">
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=reacher-z/Awesome-CUA&amp;type=Date">
    <img src="https://api.star-history.com/svg?repos=reacher-z/Awesome-CUA&amp;type=Date" alt="GitHub star count over time for Awesome-CUA" width="100%">
  </picture>
</a>

[View Awesome-CUA on Star History](https://www.star-history.com/#reacher-z/Awesome-CUA&Date)

<!-- STAR_HISTORY:END -->
