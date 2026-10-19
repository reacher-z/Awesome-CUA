<p align="center">
  <a href="https://awesomecua.github.io/">
    <img src="assets/badges/featured-by-awesome-cua.svg" alt="Featured by Awesome CUA" width="220">
  </a>
</p>

# Awesome Computer-Use Agents

A source-backed collection of papers, models, datasets, benchmarks and tools for agents that use computers.

**English** · [简体中文](README.zh-CN.md)

<a href="https://awesomecua.github.io/"><img src="assets/readme-banner.svg" alt="Awesome CUA — computer-use agent research, data and tools connected to original sources" width="960"></a>

**[Search & filter](https://awesomecua.github.io/)** · **[Research papers](https://awesomecua.github.io/papers/)** · **[Browse topics](https://awesomecua.github.io/topics/)** · **[Data & agents](https://awesomecua.github.io/data/)**

[Read the research survey](https://awesomecua.github.io/survey/) — Methods, evaluation, human agency, and reusable research assets. English working manuscript with a versioned bibliography and reading register.

<!-- BADGES:START -->
[![Catalog records](https://img.shields.io/badge/records-3%2C178-4856df?style=flat-square&labelColor=303447)](data/catalog.jsonl) [![Source-reviewed records](https://img.shields.io/badge/source--reviewed-1%2C614-4856df?style=flat-square&labelColor=303447)](docs/coverage.md) [![Catalog checks](https://github.com/reacher-z/Awesome-CUA/actions/workflows/catalog.yml/badge.svg?branch=main)](https://github.com/reacher-z/Awesome-CUA/actions/workflows/catalog.yml) [![MIT license](https://img.shields.io/badge/license-MIT-606779?style=flat-square&labelColor=303447)](LICENSE)
<!-- BADGES:END -->

[Find by task](#find-by-task) · [Explore](#explore) · [Highlights](#highlights) · [Recently reviewed](#recently-reviewed) · [Use the data](#use-the-data)

[Coverage ledger](docs/coverage.md) · [Contribute](CONTRIBUTING.md) · [GitHub organization](https://github.com/AwesomeCUA)

Discovery is scheduled three times daily at **00:17, 08:17 and 16:17 UTC**. [Actual scan results](https://awesomecua.github.io/updates/) · [Schedule and safeguards](docs/maintenance.md).

**For people, RAG systems, and agents — clone the complete catalog:**

```sh
git clone https://github.com/reacher-z/Awesome-CUA.git
```

[Agent instructions](AGENTS.md) · [RAG and agent guide](https://awesomecua.github.io/agents/) · [Complete JSONL](https://awesomecua.github.io/downloads/catalog.jsonl) · [Retrieval documents](https://awesomecua.github.io/downloads/rag-documents.jsonl)

The goal is comprehensive coverage of public research and industry resources, with provenance that can be inspected. Papers, models, training data, evaluation environments, frameworks, infrastructure, products, and publishers belong in the same searchable catalog.

**Global completeness is a goal, not a verified claim.** We publish the source populations, review states, and remaining gaps. Bibliographic metadata verification is different from reviewing a resource's relevance or quality.

[Browse by topic](https://awesomecua.github.io/topics/) · [Topic subsets and fingerprints](https://awesomecua.github.io/downloads/topics.json)

<!-- TASKS:START -->
## Find by task

| Your task | Start here | What you can find |
| --- | --- | --- |
| Find papers | [Research library](https://awesomecua.github.io/papers/) · [Topics](https://awesomecua.github.io/topics/) | Reviewed papers by year and topic, with original sources. |
| Choose a benchmark | [Benchmark guide](https://awesomecua.github.io/guides/gui-agent-benchmarks/) | Platforms, tasks, evaluators, and versions to compare. |
| Find training data | [Training-data guide](https://awesomecua.github.io/guides/gui-agent-training-data/) | Supervision, splits, count units, and data licenses. |
| Build an agent | [Agents](https://awesomecua.github.io/categories/agent/) · [Frameworks](https://awesomecua.github.io/categories/framework/) | Implementation entry points, supported platforms, and papers. |
| Use RAG or an agent | [Agent guide](https://awesomecua.github.io/agents/) · [Data hub](https://awesomecua.github.io/data/) | Complete records or retrieval documents with review states and sources. |
| Trace papers to assets | [Paper–asset connections](https://awesomecua.github.io/connections/) | Code, datasets, and models linked through reviewed primary evidence. |

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

**3,178 resource records** · **1,614 curated** · **2,718 paper and survey records** · **54 discovery documents**

Evidence through `2026-10-19T06:02:31Z`. 1,564 records have bibliographic verification only; 905 discovered identifiers remain unresolved, not counting 133 links reviewed as non-resources or other addresses of indexed resources. 136 scope exclusions retain their original metadata in the archive. Counts overlap as explained below.

<!-- STATS:END -->

## Explore

<!-- EXPLORE:START -->
| Research and training | Engineering and industry |
| --- | --- |
| [Research by topic](docs/topics.md) · **1,136** reviewed papers · [Full bibliography](docs/papers.md) · 2,718 paper and survey records | [Agents](docs/agents.md) · **43** |
| [Surveys](docs/surveys.md) · **18** | [Frameworks](docs/frameworks.md) · **75** |
| [Datasets](docs/datasets.md) · **86** | [Infrastructure](docs/infrastructures.md) · **14** |
| [Benchmarks](docs/benchmarks.md) · **88** | [Tools](docs/tools.md) · **20** |
| [Models and checkpoint releases](docs/models.md) · **98** | [Products](docs/products.md) · **20** · [Publishers and brands](docs/companies.md) · **16** |

**By platform:** [Web](docs/environments/web.md) **621** · [Desktop](docs/environments/desktop.md) **322** · [Windows](docs/environments/windows.md) **63** · [macOS](docs/environments/macos.md) **30** · [Linux](docs/environments/linux.md) **49** · [Android](docs/environments/android.md) **300** · [iOS](docs/environments/ios.md) **21** · [HarmonyOS](docs/environments/harmonyos.md) **3** · [Cross-platform](docs/environments/cross-platform.md) **197**
<!-- EXPLORE:END -->

Coverage spans web, desktop, Android, iOS, Windows, macOS, Linux, and cross-platform work. Topics include grounding, screen understanding, planning, memory, long-horizon workflows, reinforcement learning, data generation, safety, robustness, and evaluation. Environment facets overlap; framework support is not assumed from a model's benchmark results.

## Highlights

The most-mentioned curated resources per category: the count is how many other cataloged resources mention each one in their reviewed first-party source (README, model or dataset card). It reflects connectedness inside this catalog, not quality, popularity, or benchmark performance. Every category page lists all reviewed entries. Surveys come first, newest first.

<!-- HIGHLIGHTS:START -->
**Start with the newest surveys** · [all 18 →](docs/surveys.md)

| Date | Survey | Environments |
| --- | --- | --- |
| 2026‑09‑02 | [Efficient GUI Agents: A Systems Survey of Observation, Memory, Action, and Runtime Optimization](https://arxiv.org/abs/2609.02309) | cross-platform |
| 2026‑08‑30 | [A Systematic Survey of Agentic Skills: Architecture, Lifecycle, and Security](https://arxiv.org/abs/2608.29596) | cross-platform |
| 2026‑04‑17 | [A Survey on Long-Term Memory Security in LLM Agents: Attacks, Defenses, and Governance Across the Memory Lifecycle](https://arxiv.org/abs/2604.16548) | unspecified |
| 2026‑02‑12 | [Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward](https://arxiv.org/abs/2602.12430) | unspecified |
| 2025‑08‑06 | [OS Agents: A Survey on MLLM-based Agents for General Computing Devices Use](https://arxiv.org/abs/2508.04482) | cross-platform |

**Benchmarks** · [all 88 →](docs/benchmarks.md)

| Resource | Mentions | Environments | Paper | License | Description |
| --- | ---: | --- | --- | --- | --- |
| [OSWorld](https://github.com/xlang-ai/OSWorld) | 21 | desktop, linux, windows, macos | [2404.07972](https://arxiv.org/abs/2404.07972) (2024) | code Apache-2.0 | Execution-based evaluation of agents performing tasks in real desktop environments. |
| [WebArena](https://github.com/web-arena-x/webarena) | 15 | web | [2307.13854](https://arxiv.org/abs/2307.13854) (2023) | code Apache-2.0 | Self-hosted web environments and tasks for evaluating autonomous web agents. |
| [BrowserGym](https://github.com/ServiceNow/BrowserGym) | 8 | web | [2412.05467](https://arxiv.org/abs/2412.05467) (2024) | code Apache-2.0 | Unified interfaces for browser-agent tasks and benchmark environments. |
| [ScreenSpot Pro](https://github.com/likaixin2000/ScreenSpot-Pro-GUI-Grounding) | 8 | desktop, windows, macos, linux | — | code MIT | GUI grounding benchmark focused on professional high-resolution interfaces. |
| [VisualWebArena](https://github.com/web-arena-x/visualwebarena) | 7 | web | [2401.13649](https://arxiv.org/abs/2401.13649) (2024) | — | Visually grounded web tasks extending the WebArena evaluation setting. |
| [AndroidWorld](https://github.com/google-research/android_world) | 6 | android | [2405.14573](https://arxiv.org/abs/2405.14573) (2024) | code Apache-2.0 | Android environment with programmatic task evaluation for mobile agents. |

**Models** · [all 98 →](docs/models.md)

| Resource | Mentions | Environments | Paper | License | Description |
| --- | ---: | --- | --- | --- | --- |
| [SeeClick](https://github.com/njucckevin/SeeClick) | 9 | cross-platform | [2401.10935](https://arxiv.org/abs/2401.10935) (2024) | code Apache-2.0 | GUI grounding model trained to locate visual interface elements. |
| [Aguvis](https://github.com/xlang-ai/aguvis) | 5 | cross-platform | [2412.04454](https://arxiv.org/abs/2412.04454) (2024) | — | Vision-based GUI agent models with unified action representations. |
| [UI-TARS](https://github.com/bytedance/UI-TARS) | 5 | cross-platform | [2501.12326](https://arxiv.org/abs/2501.12326) (2025) | code Apache-2.0 | Native GUI agent models; UI-TARS-1.5 adds reinforcement-learned reasoning before acting and an open 7B checkpoint, and UI-TARS-2 extends to games, code and tool use. |
| [OpenCUA](https://github.com/xlang-ai/OpenCUA) | 3 | desktop | [2508.09123](https://arxiv.org/abs/2508.09123) (2025) | code MIT | Open computer-use research stack including models and training resources. |
| [OS-Atlas](https://github.com/OS-Copilot/OS-Atlas) | 3 | cross-platform | [2410.23218](https://arxiv.org/abs/2410.23218) (2024) | code Apache-2.0 | OS-Atlas GUI action models, including grounding bases fine-tuned from InternVL2-4B and Qwen2-VL-7B-Instruct that accept any image size and output 0-1000 relative coordinates. |
| [ShowUI](https://github.com/showlab/ShowUI) | 3 | cross-platform | [2411.17465](https://arxiv.org/abs/2411.17465) (2024) | code Apache-2.0 | Lightweight GUI-agent vision-language-action model from Show Lab and Microsoft, released with UI-guided token selection, training code, the ShowUI-web and ShowUI-desktop datasets and vLLM inference. |

**Datasets** · [all 86 →](docs/datasets.md)

| Resource | Mentions | Environments | Paper | License | Description |
| --- | ---: | --- | --- | --- | --- |
| [ScreenSpot-Pro data](https://huggingface.co/datasets/likaixin/ScreenSpot-Pro) | 4 | desktop, windows, macos, linux | [2504.07981](https://arxiv.org/abs/2504.07981) (2025) | data mit | High-resolution professional interface screenshots and target annotations for evaluating instruction-based GUI localization. |
| [GUI-Odyssey](https://github.com/OpenGVLab/GUI-Odyssey) | 3 | android | [2406.08451](https://arxiv.org/abs/2406.08451) (2024) | — | Human-demonstrated Android episodes for cross-app navigation, spanning six task types, 212 apps and about 1,400 app combinations, for training and evaluating agents. |
| [GUIAct](https://huggingface.co/datasets/yiye2023/GUIAct) | 3 | web, android | [2406.11317](https://arxiv.org/abs/2406.11317) (2024) | — | Web and Android GUI action-instruction data, with single-step, multi-step and smartphone partitions. |
| [GUIChat](https://huggingface.co/datasets/yiye2023/GUIChat) | 3 | unspecified | [2406.11317](https://arxiv.org/abs/2406.11317) (2024) | — | Conversational GUI supervision with text-rich images and bounding boxes, organized as single-turn questions and multi-turn dialogues. |
| [GUIEnv-local](https://huggingface.co/datasets/yiye2023/GUIEnv) | 3 | web | [2406.11317](https://arxiv.org/abs/2406.11317) (2024) | — | The released local-supervision portion of GUIEnv, pairing webpage regions and text for OCR and GUI grounding. |
| [OpenMobile-Data-v2](https://huggingface.co/datasets/OpenMobile-2/OpenMobile-Data-v2) | 3 | android, web | [2610.14157](https://arxiv.org/abs/2610.14157) (2026) | — | Mobile-agent supervision from emulator and simulator trajectories, plus executable tasks with starting states and success checks for reinforcement learning. |

**Frameworks** · [all 75 →](docs/frameworks.md)

| Resource | Mentions | Environments | Paper | License | Description |
| --- | ---: | --- | --- | --- | --- |
| [Browser Use](https://github.com/browser-use/browser-use) | 7 | web | — | code MIT | Open-source browser agent library that runs locally with any LLM against a local or cloud browser, and also serves as a CLI for coding agents and as a driver for Claude's browser toolset. |
| [AgentLab](https://github.com/ServiceNow/AgentLab) | 5 | web | [2412.05467](https://arxiv.org/abs/2412.05467) (2024) | code Apache-2.0 | Experiment framework for developing and evaluating browser agents. |
| [Seg2Click](https://github.com/jcwang0602/Seg2Click) | 5 | cross-platform | [2610.16234](https://arxiv.org/abs/2610.16234) (2026) | code MIT | Training and inference implementation that predicts an executable-region mask and derives a GUI click from that mask. |
| [OpenMobile-2 code](https://github.com/OpenMobile2/OpenMobile2-Code) | 3 | android, web | [2610.14157](https://arxiv.org/abs/2610.14157) (2026) | code Apache-2.0 | Evaluation adapters and training guidance for OpenMobile-2 across Android emulators and browser-rendered mobile simulation. |
| [UI-Genie](https://github.com/Euphoria16/UI-Genie) | 3 | android | [2505.21496](https://arxiv.org/abs/2505.21496) (2025) | — | Training and evaluation code for a mobile-agent framework that iteratively generates trajectories using agent and reward-model feedback. |
| [Computer Use OOTB](https://github.com/showlab/computer_use_ootb) | 2 | desktop | [2411.10323](https://arxiv.org/abs/2411.10323) (2024) | code Apache-2.0 | Gradio desktop GUI agent for Windows and macOS that needs no Docker, using Claude 3.5 Computer Use over the API or ShowUI and UI-TARS run locally, with multi-display and phone remote control. |

**Agents** · [all 43 →](docs/agents.md)

| Resource | Mentions | Environments | Paper | License | Description |
| --- | ---: | --- | --- | --- | --- |
| [Mobile-Agent](https://github.com/X-PLUG/MobileAgent) | 9 | android, cross-platform | [2401.16158](https://arxiv.org/abs/2401.16158) (2024), [2406.01014](https://arxiv.org/abs/2406.01014) (2024), [2508.15144](https://arxiv.org/abs/2508.15144) (2025), [2602.16855](https://arxiv.org/abs/2602.16855) (2026) | code MIT | Mobile device agent family using visual interface interaction. |
| [Agent S](https://github.com/simular-ai/Agent-S) | 2 | desktop | [2410.08164](https://arxiv.org/abs/2410.08164) (2024), [2504.00906](https://arxiv.org/abs/2504.00906) (2025) | code Apache-2.0 | Simular's open-source framework for computer-use agents that click, type and scroll through desktop and web apps on macOS, Windows and Linux; its third generation, Agent S3, reports 72.6% on OSWorld. |
| [SeeAct](https://github.com/OSU-NLP-Group/SeeAct) | 2 | web | [2401.01614](https://arxiv.org/abs/2401.01614) (2024) | — | Generalist web agent framework for large multimodal models such as GPT-4V, with a Playwright tool that runs agents on live websites, text-choice and set-of-mark grounding, and a crawler mode. |
| [AppAgent](https://github.com/TencentQQGYLab/AppAgent) | 1 | android | [2312.13771](https://arxiv.org/abs/2312.13771) (2023) | code MIT | Multimodal agent that operates Android apps through taps and swipes without back-end access, building a reusable knowledge base from autonomous exploration or from watching human demonstrations. |
| [Auto-GUI / Auto-UI](https://github.com/cooelf/Auto-GUI) | 1 | android | [2309.11436](https://arxiv.org/abs/2309.11436) (2023) | code Apache-2.0 | Screenshot-based mobile agent implementation with training and inference code for chain-of-action prediction. |
| [MagenticLite / Magentic UI](https://github.com/microsoft/magentic-ui) | 1 | web | — | code MIT | Microsoft agent application combining orchestration with browser interaction; successor to Magentic UI. |

<!-- HIGHLIGHTS:END -->

## Recently reviewed

Newest editorial approvals of models, datasets, benchmarks, systems, and tools (newest first). New papers appear by date in the [topic hubs](docs/topics.md).

<!-- RECENT:START -->
| Reviewed | Resource | Kind | Environments | Description |
| --- | --- | --- | --- | --- |
| 2026‑10‑18 | [VideoCAD data](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/WX8PCK) | dataset | web | CAD screen recordings paired with action logs and target model images for studying precise interface control and long-horizon visual imitation. |
| 2026‑10‑18 | [VeriSafe Agent](https://github.com/VeriSafeAgent/VeriSafeAgent) | framework | android | Runtime verification framework for Android GUI agents that checks proposed actions against logical rules derived from user instructions and developer-defined app states. |
| 2026‑10‑18 | [VeriOS](https://github.com/Wuzheng02/VeriOS) | framework | unspecified | Research code for proactive human–GUI-agent verification, including offline interaction-loop and dual-agent evaluation scripts plus LLaMA-Factory fine-tuning configurations. |
| 2026‑10‑18 | [SheetCopilot](https://github.com/BraveGroup/SheetCopilot) | agent | desktop, windows, linux | Spreadsheet automation agent for Windows/Excel, with benchmark assets and a separately released headless Ubuntu evaluation backend. |
| 2026‑10‑18 | [MONDAY](https://github.com/runamu/monday) | dataset | android, ios, cross-platform | Cross-platform mobile GUI trajectory dataset derived from instructional videos, with released data-processing helpers and example evaluation code for Android and iOS data. |
| 2026‑10‑18 | [LearnAct](https://github.com/lgy0404/LearnAct) | agent | unspecified | Released inference and evaluation code for demonstration-conditioned mobile GUI agents on LearnGUI-Offline. The repository describes a multi-agent adaptation method and links the LearnGUI demonstrations. |
| 2026‑10‑18 | [BrowserART](https://github.com/scaleapi/browser-art) | benchmark | web | Red-teaming benchmark and test suite from Scale AI evaluating whether refusal-trained language models can be jailbroken when deployed as browser agents. |
| 2026‑10‑18 | [AgentStudio](https://github.com/skyworkai/agent-studio) | framework | desktop, linux | Toolkit and Ubuntu-based environment for building and evaluating generalist computer-use agents through GUI and API interaction. |
| 2026‑10‑18 | [VideoCAD training and evaluation code](https://github.com/ghadinehme/VideoCAD) | framework | web | VideoCADFormer training, action-log preprocessing and evaluation code for learning CAD interface action sequences from screen recordings of browser-based Onshape. |
| 2026‑10‑18 | [GUIPivot](https://github.com/ZrW00/GUIPivot) | framework | android | Query-inference training tools connecting screenshot grounding with GUI action reasoning, including preprocessing, query refinement and offline single-step evaluation on AndroidControl and AITZ. |
| 2026‑10‑18 | [MLA-Trust](https://github.com/thu-ml/MLA-Trust) | benchmark | web, android, cross-platform | Unified evaluation framework measuring truthfulness, controllability, safety, and privacy of multimodal LLM agents across interactive web and mobile GUI tasks. |
| 2026‑10‑18 | [ST-WebAgentBench](https://github.com/segev-shlomov/ST-WebAgentBench) | benchmark | web | BrowserGym-based benchmark for evaluating the safety and policy compliance of enterprise web agents across six trustworthiness risk dimensions. |
<!-- RECENT:END -->

## Use the data

Browse the [interactive website](https://awesomecua.github.io/) to search and filter all resources, inspect source evidence, switch between English and Chinese, or download the complete catalog. [Website development and publishing](docs/website.md).

The [English data hub](https://awesomecua.github.io/data/) and [中文数据中心](https://awesomecua.github.io/zh/data/) organize public downloads into six groups: complete catalog, RAG documents, citations, topics and comparisons, sources and review status, and schemas. Cloning still gives you the complete source catalog; the hub provides exports from its published snapshot.

The [download manifest](https://awesomecua.github.io/downloads/manifest.json) records each listed export's actual count and unit, scope, byte size, and SHA-256 fingerprint. These are different formats and overlapping views of the catalog, so their counts must not be added together. Compare `catalog_sha256` across manifests before combining files from different downloads.

[Reviewed research](https://awesomecua.github.io/papers/) · [Computer-use agent guides](https://awesomecua.github.io/guides/) · [Static resource directory](https://awesomecua.github.io/catalog/) · [Search and AI discovery](docs/search-discovery.md)

- **[Catalog JSONL](data/catalog.jsonl):** one resource per line, with stable IDs, typed fields, provenance, scoped licenses, and review status.
- **[Reference graph](data/references.jsonl):** outbound references from primary sources. `mentions` does not mean `trained_on` or `evaluated_on`.
- **[Discovery registry](data/sources.json)** and **[candidates](data/candidates.jsonl):** source snapshots and where each identifier was found.
- **[Review queue](data/review-queue.jsonl):** unresolved evidence, unindexed discoveries, and proposals requiring editorial work. Discovered links reviewed as non-resources or as other addresses of indexed resources stay listed with a `resolution` and their reason.
- **[JSON Schema](schemas/resource.schema.json)** and **[coverage JSON](data/coverage.json):** machine-checkable contracts and coverage accounting.
- **[BibTeX](https://awesomecua.github.io/downloads/citations.bib)** and **[CSL JSON](https://awesomecua.github.io/downloads/citations.csl.json):** reviewed-paper citations with recorded authors, dates, and versions. Each resource page also provides its own `record.json`.

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

| State | What has been checked | What has not been established |
| --- | --- | --- |
| `curated` | AI-assisted editorial review against a first-party source snapshot, with name, scope, summary, and taxonomy | Independent reproduction, universal availability, or endorsement |
| `metadata_verified` | Bibliographic identity, title, authors, and recorded dates checked against retained arXiv or publication sources | Topic relevance, methodology, findings, or inclusion in the core field |
| `candidate` | A normalized URL or identifier was discovered | Inclusion, correctness, or availability; excluded from the published catalog |

Counts refer to **resources**, not unique projects. A paper, repository, dataset release, model checkpoint, product, and publisher can be separate related resources. Model families and individual checkpoints are explicitly linked where reviewed.

Code, data, weights, and document licenses are separate. Missing values are `null`. Dataset archive counts are not converted into training-example counts. Scores from different benchmark versions, splits, action budgets, or evaluators are not combined into a ranking.

## Maintain and verify

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.txt
.venv/bin/python scripts/catalog.py validate
.venv/bin/python scripts/catalog.py build --check
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/catalog.py build
node --test tests/web.test.mjs
.venv/bin/python scripts/build_site.py
```

These commands match the checks that [Catalog quality](.github/workflows/catalog.yml) runs on every push and pull request, in the same order. They need Python 3.11+ and Node.js 24+, the `engines` version in `package.json` (CI uses Python 3.12 and Node.js 24). The web tests use only the built-in Node.js test runner, so nothing needs to be installed with npm. `npm run test:web` and `npm run build:web` are shortcuts for the last two commands.

Network discovery and verification are explicit commands; ordinary builds are offline. Changed primary snapshots require another editorial review before publication. [Maintenance guide](docs/maintenance.md) · [Methodology](docs/methodology.md) · [Data dictionary](docs/data-dictionary.md)

## Acknowledgments and reuse

The [source registry](data/sources.json) credits the community collections and surveys used for discovery. Bibliographic records use retained arXiv, publisher, and author sources; publication observations preserve edition-specific titles, authors, and date precision. Selected assets are checked against publisher repositories, documentation, and model/dataset cards. Upstream READMEs, papers, model weights, and datasets are not redistributed here.

Original repository code and annotations use the [MIT license](LICENSE). Linked resources retain their own terms; this repository does not relicense them.

To cite the catalog, use [CITATION.cff](CITATION.cff) or GitHub's "Cite this repository" button. The data changes with every scan, so pin the exact version you used. Each `v*` tag has a [data release](https://github.com/reacher-z/Awesome-CUA/releases) with versioned downloads built from the tagged commit: the catalog as JSONL, JSON and SQLite, the coverage ledger, topic and profile exports, and their `SHA256SUMS`. Cite the release tag, or record the commit from `git rev-parse HEAD` in your clone, or link files at that commit, such as `https://github.com/reacher-z/Awesome-CUA/blob/<commit>/data/catalog.jsonl`. [Cutting a release](docs/maintenance.md#versioned-data-releases).
