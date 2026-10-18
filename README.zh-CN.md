<p align="center">
  <a href="https://awesomecua.github.io/">
    <img src="assets/badges/featured-by-awesome-cua.svg" alt="Featured by Awesome CUA" width="220">
  </a>
</p>

# Awesome Computer-Use Agents

收集面向电脑操作智能体的论文、模型、数据集、评测基准与工具，每条资源保留原始来源。

[English](README.md) · **简体中文**

<a href="https://awesomecua.github.io/?lang=zh"><img src="assets/readme-banner.zh-CN.svg" alt="Awesome CUA — Computer-Use 智能体资源合集，连接论文、数据、工具与原始来源" width="960"></a>

**[搜索与筛选](https://awesomecua.github.io/?lang=zh)** · **[研究论文](https://awesomecua.github.io/zh/papers/)** · **[按主题浏览](https://awesomecua.github.io/zh/topics/)** · **[数据与 Agent](https://awesomecua.github.io/zh/data/)**

[阅读英文研究综述](https://awesomecua.github.io/survey/) — 连接方法、评测、人的控制权与可复用研究资产；工作稿附有固定版本书目和逐篇阅读记录。

<!-- BADGES:START -->
[![Catalog records](https://img.shields.io/badge/records-3%2C176-4856df?style=flat-square&labelColor=303447)](data/catalog.jsonl) [![Source-reviewed records](https://img.shields.io/badge/source--reviewed-1%2C615-4856df?style=flat-square&labelColor=303447)](docs/coverage.md) [![Catalog checks](https://github.com/reacher-z/Awesome-CUA/actions/workflows/catalog.yml/badge.svg?branch=main)](https://github.com/reacher-z/Awesome-CUA/actions/workflows/catalog.yml) [![MIT license](https://img.shields.io/badge/license-MIT-606779?style=flat-square&labelColor=303447)](LICENSE)
<!-- BADGES:END -->

[按任务查找](#按任务查找) · [浏览](#浏览) · [重点资源](#重点资源) · [最新审阅](#最新审阅) · [使用数据](#使用数据)

[覆盖台账](docs/coverage.md) · [参与贡献](CONTRIBUTING.md) · [GitHub 组织](https://github.com/AwesomeCUA) · [网站](https://awesomecua.github.io/) · [中文主页](https://awesomecua.github.io/zh/)

资源发现计划每日执行三次，时间为 **UTC 00:17、08:17 和 16:17**。[实际扫描结果](https://awesomecua.github.io/updates/) · [时间安排与保护机制](docs/maintenance.md)。

**供人、RAG 系统和智能体使用——克隆完整目录：**

```sh
git clone https://github.com/reacher-z/Awesome-CUA.git
```

[Agent 操作指南](AGENTS.md) · [RAG 与智能体指南](https://awesomecua.github.io/zh/agents/)（[English](https://awesomecua.github.io/agents/)） · [完整 JSONL](https://awesomecua.github.io/downloads/catalog.jsonl) · [检索文档](https://awesomecua.github.io/downloads/rag-documents.jsonl)

目标是全面覆盖公开的研究和产业资源，并提供可检查的来源证据。论文、模型、训练数据、评测环境、框架、基础设施、产品和发布方都收录在同一个可检索目录中。

**“全球最全”是建设目标，而不是已经核实的结论。** 我们公开来源范围、审阅状态和剩余缺口。核实书目元数据不等于审阅了资源的相关性或质量。

使用 `python3 scripts/catalog.py get arxiv:2404.07972 --related --json` 可按稳定 ID 取得完整记录与已核实关联。[BibTeX](https://awesomecua.github.io/downloads/citations.bib) 和 [CSL JSON](https://awesomecua.github.io/downloads/citations.csl.json) 提供已审阅论文引用；每条资源页面也有可直接读取的 `record.json`。

[按主题浏览](https://awesomecua.github.io/zh/topics/)（[English](https://awesomecua.github.io/topics/)） · [主题子集与指纹](https://awesomecua.github.io/downloads/topics.json)

<!-- TASKS:START -->
## 按任务查找

| 你的任务 | 从这里开始 | 可以找到什么 |
| --- | --- | --- |
| 查找论文 | [论文库](https://awesomecua.github.io/zh/papers/) · [研究主题](https://awesomecua.github.io/zh/topics/) | 按年份和主题阅读已审阅论文，查看原始来源。 |
| 选择评测基准 | [基准指南](https://awesomecua.github.io/guides/gui-agent-benchmarks/) | 核对平台、任务、评估器和版本。 |
| 寻找训练数据 | [训练数据指南](https://awesomecua.github.io/guides/gui-agent-training-data/) | 比较监督形式、划分、样本单位和数据许可。 |
| 构建智能体 | [智能体](https://awesomecua.github.io/categories/agent/) · [框架](https://awesomecua.github.io/categories/framework/) | 找到实现入口、支持的平台和论文依据。 |
| 接入 RAG 或 Agent | [使用指南](https://awesomecua.github.io/zh/agents/) · [数据中心](https://awesomecua.github.io/zh/data/) | 下载完整记录或检索文档，保留审阅状态和来源。 |
| 追溯论文与资产 | [论文—资产关系](https://awesomecua.github.io/connections/) | 查看经一手来源支持的代码、数据和模型关联。 |

<details>
<summary>本地检索示例（克隆后运行；Python 3.11+，无需安装依赖）</summary>

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

**3,176 条资源记录** · **1,615 条已审阅** · **2,715 条论文与综述记录** · **54 个发现来源文档**

证据截至 `2026-10-18T16:02:15Z`。1,561 条记录仅完成书目核实；904 个已发现的标识符尚待处理，另有 133 个链接经审阅确认为非资源或已收录资源的其他地址，不计入其中。136 条范围排除记录在归档中保留原始元数据。各项计数存在重叠，详见下文。

<!-- STATS:END -->

## 浏览

<!-- EXPLORE:START -->
| 研究与训练 | 工程与产业 |
| --- | --- |
| [按主题浏览研究](docs/topics.md) · **1,136** 篇已审阅论文 · [完整论文目录](docs/papers.md) · 2,715 条论文与综述记录 | [智能体](docs/agents.md) · **43** |
| [综述](docs/surveys.md) · **18** | [框架](docs/frameworks.md) · **75** |
| [数据集](docs/datasets.md) · **87** | [基础设施](docs/infrastructures.md) · **14** |
| [基准](docs/benchmarks.md) · **88** | [工具](docs/tools.md) · **20** |
| [模型与权重版本](docs/models.md) · **98** | [产品](docs/products.md) · **20** · [发布方与品牌](docs/companies.md) · **16** |

**按平台：** [Web](docs/environments/web.md) **622** · [Desktop](docs/environments/desktop.md) **322** · [Windows](docs/environments/windows.md) **63** · [macOS](docs/environments/macos.md) **30** · [Linux](docs/environments/linux.md) **49** · [Android](docs/environments/android.md) **300** · [iOS](docs/environments/ios.md) **21** · [HarmonyOS](docs/environments/harmonyos.md) **3** · [Cross-platform](docs/environments/cross-platform.md) **197**
<!-- EXPLORE:END -->

覆盖 Web、桌面、Android、iOS、Windows、macOS、Linux 和跨平台工作。主题包括 grounding、屏幕理解、规划、记忆、长流程任务、强化学习、数据生成、安全、鲁棒性和评测。环境分面可以重叠；不会根据模型的基准成绩推定框架支持。

## 重点资源

按类别列出被其他已收录资源在其已审阅一手来源（README、模型卡或数据集卡）中提及最多的已审阅资源。该计数反映目录内部的关联程度，不代表质量、流行度或基准表现；每个类别页面都列出全部已审阅条目。综述排在最前，按时间倒序。资源名称和简介保留原文。

<!-- HIGHLIGHTS:START -->
**从最新综述入门** · [全部 18 项 →](docs/surveys.md)

| 日期 | 综述 | 环境 |
| --- | --- | --- |
| 2026‑09‑02 | [Efficient GUI Agents: A Systems Survey of Observation, Memory, Action, and Runtime Optimization](https://arxiv.org/abs/2609.02309) | cross-platform |
| 2026‑08‑30 | [A Systematic Survey of Agentic Skills: Architecture, Lifecycle, and Security](https://arxiv.org/abs/2608.29596) | cross-platform |
| 2026‑04‑17 | [A Survey on Long-Term Memory Security in LLM Agents: Attacks, Defenses, and Governance Across the Memory Lifecycle](https://arxiv.org/abs/2604.16548) | unspecified |
| 2026‑02‑12 | [Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward](https://arxiv.org/abs/2602.12430) | unspecified |
| 2025‑08‑06 | [OS Agents: A Survey on MLLM-based Agents for General Computing Devices Use](https://arxiv.org/abs/2508.04482) | cross-platform |

**基准** · [全部 88 项 →](docs/benchmarks.md)

| 资源 | 被提及 | 环境 | 论文 | 许可 | 简介（英文） |
| --- | ---: | --- | --- | --- | --- |
| [OSWorld](https://github.com/xlang-ai/OSWorld) | 21 | desktop, linux, windows, macos | [2404.07972](https://arxiv.org/abs/2404.07972) (2024) | 代码 Apache-2.0 | Execution-based evaluation of agents performing tasks in real desktop environments. |
| [WebArena](https://github.com/web-arena-x/webarena) | 15 | web | [2307.13854](https://arxiv.org/abs/2307.13854) (2023) | 代码 Apache-2.0 | Self-hosted web environments and tasks for evaluating autonomous web agents. |
| [BrowserGym](https://github.com/ServiceNow/BrowserGym) | 8 | web | [2412.05467](https://arxiv.org/abs/2412.05467) (2024) | 代码 Apache-2.0 | Unified interfaces for browser-agent tasks and benchmark environments. |
| [ScreenSpot Pro](https://github.com/likaixin2000/ScreenSpot-Pro-GUI-Grounding) | 8 | desktop, windows, macos, linux | — | 代码 MIT | GUI grounding benchmark focused on professional high-resolution interfaces. |
| [VisualWebArena](https://github.com/web-arena-x/visualwebarena) | 7 | web | [2401.13649](https://arxiv.org/abs/2401.13649) (2024) | — | Visually grounded web tasks extending the WebArena evaluation setting. |
| [AndroidWorld](https://github.com/google-research/android_world) | 6 | android | [2405.14573](https://arxiv.org/abs/2405.14573) (2024) | 代码 Apache-2.0 | Android environment with programmatic task evaluation for mobile agents. |

**模型** · [全部 98 项 →](docs/models.md)

| 资源 | 被提及 | 环境 | 论文 | 许可 | 简介（英文） |
| --- | ---: | --- | --- | --- | --- |
| [SeeClick](https://github.com/njucckevin/SeeClick) | 9 | cross-platform | [2401.10935](https://arxiv.org/abs/2401.10935) (2024) | 代码 Apache-2.0 | GUI grounding model trained to locate visual interface elements. |
| [Aguvis](https://github.com/xlang-ai/aguvis) | 5 | cross-platform | [2412.04454](https://arxiv.org/abs/2412.04454) (2024) | — | Vision-based GUI agent models with unified action representations. |
| [UI-TARS](https://github.com/bytedance/UI-TARS) | 5 | cross-platform | [2501.12326](https://arxiv.org/abs/2501.12326) (2025) | 代码 Apache-2.0 | Native GUI agent models; UI-TARS-1.5 adds reinforcement-learned reasoning before acting and an open 7B checkpoint, and UI-TARS-2 extends to games, code and tool use. |
| [OpenCUA](https://github.com/xlang-ai/OpenCUA) | 3 | desktop | [2508.09123](https://arxiv.org/abs/2508.09123) (2025) | 代码 MIT | Open computer-use research stack including models and training resources. |
| [OS-Atlas](https://github.com/OS-Copilot/OS-Atlas) | 3 | cross-platform | [2410.23218](https://arxiv.org/abs/2410.23218) (2024) | 代码 Apache-2.0 | OS-Atlas GUI action models, including grounding bases fine-tuned from InternVL2-4B and Qwen2-VL-7B-Instruct that accept any image size and output 0-1000 relative coordinates. |
| [ShowUI](https://github.com/showlab/ShowUI) | 3 | cross-platform | [2411.17465](https://arxiv.org/abs/2411.17465) (2024) | 代码 Apache-2.0 | Lightweight GUI-agent vision-language-action model from Show Lab and Microsoft, released with UI-guided token selection, training code, the ShowUI-web and ShowUI-desktop datasets and vLLM inference. |

**数据集** · [全部 87 项 →](docs/datasets.md)

| 资源 | 被提及 | 环境 | 论文 | 许可 | 简介（英文） |
| --- | ---: | --- | --- | --- | --- |
| [ScreenSpot-Pro data](https://huggingface.co/datasets/likaixin/ScreenSpot-Pro) | 4 | desktop, windows, macos, linux | [2504.07981](https://arxiv.org/abs/2504.07981) (2025) | 数据 mit | High-resolution professional interface screenshots and target annotations for evaluating instruction-based GUI localization. |
| [GUI-Odyssey](https://github.com/OpenGVLab/GUI-Odyssey) | 3 | android | [2406.08451](https://arxiv.org/abs/2406.08451) (2024) | — | Human-demonstrated Android episodes for cross-app navigation, spanning six task types, 212 apps and about 1,400 app combinations, for training and evaluating agents. |
| [GUIAct](https://huggingface.co/datasets/yiye2023/GUIAct) | 3 | web, android | [2406.11317](https://arxiv.org/abs/2406.11317) (2024) | — | Web and Android GUI action-instruction data, with single-step, multi-step and smartphone partitions. |
| [GUIChat](https://huggingface.co/datasets/yiye2023/GUIChat) | 3 | unspecified | [2406.11317](https://arxiv.org/abs/2406.11317) (2024) | — | Conversational GUI supervision with text-rich images and bounding boxes, organized as single-turn questions and multi-turn dialogues. |
| [GUIEnv-local](https://huggingface.co/datasets/yiye2023/GUIEnv) | 3 | web | [2406.11317](https://arxiv.org/abs/2406.11317) (2024) | — | The released local-supervision portion of GUIEnv, pairing webpage regions and text for OCR and GUI grounding. |
| [OpenMobile-Data-v2](https://huggingface.co/datasets/OpenMobile-2/OpenMobile-Data-v2) | 3 | android, web | [2610.14157](https://arxiv.org/abs/2610.14157) (2026) | — | Mobile-agent supervision from emulator and simulator trajectories, plus executable tasks with starting states and success checks for reinforcement learning. |

**框架** · [全部 75 项 →](docs/frameworks.md)

| 资源 | 被提及 | 环境 | 论文 | 许可 | 简介（英文） |
| --- | ---: | --- | --- | --- | --- |
| [Browser Use](https://github.com/browser-use/browser-use) | 7 | web | — | 代码 MIT | Open-source browser agent library that runs locally with any LLM against a local or cloud browser, and also serves as a CLI for coding agents and as a driver for Claude's browser toolset. |
| [AgentLab](https://github.com/ServiceNow/AgentLab) | 5 | web | [2412.05467](https://arxiv.org/abs/2412.05467) (2024) | 代码 Apache-2.0 | Experiment framework for developing and evaluating browser agents. |
| [Seg2Click](https://github.com/jcwang0602/Seg2Click) | 5 | cross-platform | [2610.16234](https://arxiv.org/abs/2610.16234) (2026) | 代码 MIT | Training and inference implementation that predicts an executable-region mask and derives a GUI click from that mask. |
| [OpenMobile-2 code](https://github.com/OpenMobile2/OpenMobile2-Code) | 3 | android, web | [2610.14157](https://arxiv.org/abs/2610.14157) (2026) | 代码 Apache-2.0 | Evaluation adapters and training guidance for OpenMobile-2 across Android emulators and browser-rendered mobile simulation. |
| [UI-Genie](https://github.com/Euphoria16/UI-Genie) | 3 | android | [2505.21496](https://arxiv.org/abs/2505.21496) (2025) | — | Training and evaluation code for a mobile-agent framework that iteratively generates trajectories using agent and reward-model feedback. |
| [Computer Use OOTB](https://github.com/showlab/computer_use_ootb) | 2 | desktop | [2411.10323](https://arxiv.org/abs/2411.10323) (2024) | 代码 Apache-2.0 | Gradio desktop GUI agent for Windows and macOS that needs no Docker, using Claude 3.5 Computer Use over the API or ShowUI and UI-TARS run locally, with multi-display and phone remote control. |

**智能体** · [全部 43 项 →](docs/agents.md)

| 资源 | 被提及 | 环境 | 论文 | 许可 | 简介（英文） |
| --- | ---: | --- | --- | --- | --- |
| [Mobile-Agent](https://github.com/X-PLUG/MobileAgent) | 9 | android, cross-platform | [2401.16158](https://arxiv.org/abs/2401.16158) (2024), [2406.01014](https://arxiv.org/abs/2406.01014) (2024), [2508.15144](https://arxiv.org/abs/2508.15144) (2025), [2602.16855](https://arxiv.org/abs/2602.16855) (2026) | 代码 MIT | Mobile device agent family using visual interface interaction. |
| [Agent S](https://github.com/simular-ai/Agent-S) | 2 | desktop | [2410.08164](https://arxiv.org/abs/2410.08164) (2024), [2504.00906](https://arxiv.org/abs/2504.00906) (2025) | 代码 Apache-2.0 | Simular's open-source framework for computer-use agents that click, type and scroll through desktop and web apps on macOS, Windows and Linux; its third generation, Agent S3, reports 72.6% on OSWorld. |
| [SeeAct](https://github.com/OSU-NLP-Group/SeeAct) | 2 | web | [2401.01614](https://arxiv.org/abs/2401.01614) (2024) | — | Generalist web agent framework for large multimodal models such as GPT-4V, with a Playwright tool that runs agents on live websites, text-choice and set-of-mark grounding, and a crawler mode. |
| [AppAgent](https://github.com/TencentQQGYLab/AppAgent) | 1 | android | [2312.13771](https://arxiv.org/abs/2312.13771) (2023) | 代码 MIT | Multimodal agent that operates Android apps through taps and swipes without back-end access, building a reusable knowledge base from autonomous exploration or from watching human demonstrations. |
| [Auto-GUI / Auto-UI](https://github.com/cooelf/Auto-GUI) | 1 | android | [2309.11436](https://arxiv.org/abs/2309.11436) (2023) | 代码 Apache-2.0 | Screenshot-based mobile agent implementation with training and inference code for chain-of-action prediction. |
| [MagenticLite / Magentic UI](https://github.com/microsoft/magentic-ui) | 1 | web | — | 代码 MIT | Microsoft agent application combining orchestration with browser interaction; successor to Magentic UI. |

<!-- HIGHLIGHTS:END -->

## 最新审阅

按时间倒序列出最新通过编辑审阅的模型、数据集、基准、系统和工具；新论文按日期列在[主题页面](docs/topics.md)中。

<!-- RECENT:START -->
| 审阅日期 | 资源 | 类型 | 环境 | 简介（英文） |
| --- | --- | --- | --- | --- |
| 2026‑10‑18 | [Multimodal-Mind2Web](https://huggingface.co/datasets/osunlp/Multimodal-Mind2Web) | 数据集 | web | Mind2Web action steps aligned with the matching webpage screenshot, plus raw and cleaned HTML, candidate elements and the target operation, in a train split and test splits held out by task, website and domain. |
| 2026‑10‑18 | [VideoCAD data](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/WX8PCK) | 数据集 | web | CAD screen recordings paired with action logs and target model images for studying precise interface control and long-horizon visual imitation. |
| 2026‑10‑18 | [VeriSafe Agent](https://github.com/VeriSafeAgent/VeriSafeAgent) | 框架 | android | Runtime verification framework for Android GUI agents that checks proposed actions against logical rules derived from user instructions and developer-defined app states. |
| 2026‑10‑18 | [VeriOS](https://github.com/Wuzheng02/VeriOS) | 框架 | unspecified | Research code for proactive human–GUI-agent verification, including offline interaction-loop and dual-agent evaluation scripts plus LLaMA-Factory fine-tuning configurations. |
| 2026‑10‑18 | [SheetCopilot](https://github.com/BraveGroup/SheetCopilot) | 智能体 | desktop, windows, linux | Spreadsheet automation agent for Windows/Excel, with benchmark assets and a separately released headless Ubuntu evaluation backend. |
| 2026‑10‑18 | [MONDAY](https://github.com/runamu/monday) | 数据集 | android, ios, cross-platform | Cross-platform mobile GUI trajectory dataset derived from instructional videos, with released data-processing helpers and example evaluation code for Android and iOS data. |
| 2026‑10‑18 | [LearnAct](https://github.com/lgy0404/LearnAct) | 智能体 | unspecified | Released inference and evaluation code for demonstration-conditioned mobile GUI agents on LearnGUI-Offline. The repository describes a multi-agent adaptation method and links the LearnGUI demonstrations. |
| 2026‑10‑18 | [BrowserART](https://github.com/scaleapi/browser-art) | 基准 | web | Red-teaming benchmark and test suite from Scale AI evaluating whether refusal-trained language models can be jailbroken when deployed as browser agents. |
| 2026‑10‑18 | [AgentStudio](https://github.com/skyworkai/agent-studio) | 框架 | desktop, linux | Toolkit and Ubuntu-based environment for building and evaluating generalist computer-use agents through GUI and API interaction. |
| 2026‑10‑18 | [VideoCAD training and evaluation code](https://github.com/ghadinehme/VideoCAD) | 框架 | web | VideoCADFormer training, action-log preprocessing and evaluation code for learning CAD interface action sequences from screen recordings of browser-based Onshape. |
| 2026‑10‑18 | [GUIPivot](https://github.com/ZrW00/GUIPivot) | 框架 | android | Query-inference training tools connecting screenshot grounding with GUI action reasoning, including preprocessing, query refinement and offline single-step evaluation on AndroidControl and AITZ. |
| 2026‑10‑18 | [MLA-Trust](https://github.com/thu-ml/MLA-Trust) | 基准 | web, android, cross-platform | Unified evaluation framework measuring truthfulness, controllability, safety, and privacy of multimodal LLM agents across interactive web and mobile GUI tasks. |
<!-- RECENT:END -->

## 使用数据

打开[交互式网站](https://awesomecua.github.io/)，可以搜索和筛选全部资源、查看来源证据、切换中英文界面，或下载完整目录。网站开发与发布见 [website.md](docs/website.md)。

[中文数据中心](https://awesomecua.github.io/zh/data/)与[English data hub](https://awesomecua.github.io/data/)按六组组织公开下载：完整目录、RAG 检索文档、论文引用、主题与对比、来源与审阅状态、数据规范（schema）。克隆仓库仍可取得同一套完整源目录；数据中心提供其已发布快照的导出文件。

[下载清单](https://awesomecua.github.io/downloads/manifest.json)为每个列出的导出记录实际数量及单位、范围、精确字节数和 SHA-256 指纹。不同格式和视图可能包含相同资源，单位也可能不同，不能把这些数量相加。混合使用下载文件前，请比较各清单的 `catalog_sha256`，确认它们属于同一目录快照。

[已审阅研究](https://awesomecua.github.io/zh/papers/)（[English](https://awesomecua.github.io/papers/)） · [Computer-use agent 指南](https://awesomecua.github.io/guides/) · [静态资源目录](https://awesomecua.github.io/catalog/) · [搜索与 AI 发现](docs/search-discovery.md)

- **[目录 JSONL](data/catalog.jsonl)：** 每行一个资源，包含稳定 ID、类型化字段、来源证据、按范围区分的许可和审阅状态。
- **[引用图](data/references.jsonl)：** 一手来源中的对外引用。`mentions` 不等于 `trained_on` 或 `evaluated_on`。
- **[发现来源登记](data/sources.json)** 和 **[候选条目](data/candidates.jsonl)：** 来源快照，以及每个标识符的发现位置。
- **[待审队列](data/review-queue.jsonl)：** 未解决的证据、尚未收录的发现，以及需要编辑处理的提议。经审阅确认为非资源或已收录资源其他地址的链接仍保留在队列中，并注明 `resolution` 与理由。
- **[JSON Schema](schemas/resource.schema.json)** 和 **[覆盖度 JSON](data/coverage.json)：** 可机器检查的数据契约和覆盖度统计。

```bash
# Python 3.11+。搜索和导出只需要标准库。
cd Awesome-CUA
python3 scripts/catalog.py search "grounding" --kind model
python3 scripts/catalog.py search --kind dataset --environment android
python3 scripts/catalog.py search --kind product --status curated --json
python3 scripts/catalog.py get arxiv:2404.07972 --related --json
python3 scripts/catalog.py build
# 生成 dist/catalog.sqlite 和 dist/catalog.json，不发起网络请求。
python3 scripts/export_rag.py --output dist/rag-documents.jsonl
python3 scripts/export_citations.py --format bibtex --output dist/citations.bib
# 加 --include-metadata 可包含全部当前记录，并保留各自的审阅状态。
```

用 SQLite 联查资源、环境/主题分面和已审阅关系，示例见[查询指南](docs/query-guide.md)。`data/catalog.jsonl` 已提交到仓库；SQLite 和 JSON 数组导出是可复现的本地构建产物。

## “已核实”的含义

| 状态 | 已检查的内容 | 尚未确认的内容 |
| --- | --- | --- |
| `curated` | 基于一手来源快照的 AI 辅助编辑审阅，涵盖名称、范围、摘要和分类 | 独立复现、普遍可用性或背书 |
| `metadata_verified` | 对照保留的 arXiv 或出版来源核实书目身份、标题、作者和已记录日期 | 主题相关性、方法、结论，或是否属于核心领域 |
| `candidate` | 发现了规范化的 URL 或标识符 | 是否收录、是否正确或是否可用；不计入公开目录 |

计数指的是**资源**，而不是独立项目。论文、仓库、数据集发布、模型权重版本、产品和发布方可以是彼此关联的不同资源。模型系列与具体权重版本在审阅后会显式关联。

代码、数据、权重和文档的许可分别记录。缺失值为 `null`。数据集归档文件数不会被换算成训练样本数。来自不同基准版本、数据划分、动作预算或评测器的分数不会合并成排行榜。

## 维护与验证

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

这些命令与 [Catalog quality](.github/workflows/catalog.yml) 在每次推送和拉取请求时运行的检查一致，顺序也相同。需要 Python 3.11+ 和 Node.js 24+，即 `package.json` 中 `engines` 声明的版本（CI 使用 Python 3.12 和 Node.js 24）。网页测试只使用 Node.js 内置的测试运行器，无需用 npm 安装任何依赖。`npm run test:web` 和 `npm run build:web` 分别是最后两条命令的快捷方式。

网络发现和核实需要显式运行相应命令；常规构建不联网。一手来源快照发生变化后，必须重新进行编辑审阅才能发布。[维护指南](docs/maintenance.md) · [方法说明](docs/methodology.md) · [数据字典](docs/data-dictionary.md)

## 致谢与复用

[来源登记](data/sources.json)列出了用于发现资源的社区合集和综述。书目记录依据保留的 arXiv、出版方及作者来源；出版记录分别保留各版本的题名、作者和日期精度。部分资源还会对照发布方的仓库、文档以及模型/数据集卡片核查。上游 README、论文、模型权重和数据集不在本仓库中再分发。

本仓库的原创代码和标注采用 [MIT 许可](LICENSE)。被链接的资源保留各自的条款；本仓库不对其重新授权。

引用本目录时，请使用 [CITATION.cff](CITATION.cff) 或 GitHub 的“Cite this repository”按钮。数据随每次扫描更新，请固定所用的确切版本。每个 `v*` 标签都有一个[数据发布](https://github.com/reacher-z/Awesome-CUA/releases)，提供由该标签所指提交构建的版本化下载：JSONL、JSON 和 SQLite 格式的目录、覆盖台账、主题与规格导出，以及它们的 `SHA256SUMS`。请引用发布标签，或在克隆中用 `git rev-parse HEAD` 记录提交，或链接该提交下的文件，例如 `https://github.com/reacher-z/Awesome-CUA/blob/<commit>/data/catalog.jsonl`。[如何发布版本](docs/maintenance.md#versioned-data-releases)。
