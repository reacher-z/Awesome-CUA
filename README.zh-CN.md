<h1 align="center"><a href="https://awesomecua.com/zh/"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/brand/readme-banner-dark.svg"><img src="assets/brand/readme-banner-light.svg" alt="Awesome CUA — 面向电脑操作智能体的研究、数据与工具，每条都链接原始来源" width="960"></picture></a></h1>

收集面向电脑操作智能体的论文、模型、数据集、评测基准与工具，每条资源保留原始来源。

[English](README.md) · **简体中文**

**[网站搜索](https://awesomecua.com/zh/)** · **[论文](https://awesomecua.com/zh/papers/)** · **[主题](https://awesomecua.com/zh/topics/)** · **[数据](https://awesomecua.com/zh/data/)** · **[智能体指南](https://awesomecua.com/zh/agents/)** · **[参与贡献](CONTRIBUTING.md)**

觉得有用？欢迎在 GitHub 上[点星支持本合集](https://github.com/reacher-z/Awesome-CUA)，让更多人找到它。

<!-- BADGES:START -->
[![Curated resources](https://img.shields.io/badge/curated%20resources-4%2C587-4352E8?style=flat-square&labelColor=1E2233)](docs/coverage.md) [![Reviewed papers and surveys](https://img.shields.io/badge/reviewed%20papers%20and%20surveys-1%2C718-4352E8?style=flat-square&labelColor=1E2233)](docs/papers.md) [![Evidence through](https://img.shields.io/badge/evidence%20through-2026--11--09%2011%3A08%20UTC-4352E8?style=flat-square&labelColor=1E2233)](docs/maintenance.md) [![Hugging Face dataset](https://img.shields.io/badge/dataset-Hugging%20Face-4352E8?style=flat-square&labelColor=1E2233)](https://huggingface.co/datasets/TIGER-Lab/AwesomeCUA) [![MIT license](https://img.shields.io/badge/license-MIT-5E6472?style=flat-square&labelColor=1E2233)](LICENSE)
<!-- BADGES:END -->

已审阅条目依据一手来源快照审阅；待审阅记录已核实书目信息；候选是已发现的标识符，尚待处理。[“已核实”的含义](#已核实的含义) · [覆盖台账](docs/coverage.md)

## 推荐基准

| 网站重建                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 浏览器智能体                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| <a href="https://github.com/TIGER-AI-Lab/WebsiteBench"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/TIGER-AI-Lab/WebsiteBench/78f5558e8197bb91b3bab63428c12b92060ddc6f/assets/wordmark-dark.svg"><img src="https://raw.githubusercontent.com/TIGER-AI-Lab/WebsiteBench/78f5558e8197bb91b3bab63428c12b92060ddc6f/assets/wordmark-light.svg" alt="WebsiteBench" height="32"></picture></a><br>AI 智能体能否通过浏览器探索重建网站？<br>[★ 在 GitHub 上点星](https://github.com/TIGER-AI-Lab/WebsiteBench) | <a href="https://github.com/TIGER-AI-Lab/ClawBench"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/TIGER-AI-Lab/ClawBench/c8409629f4f2f9768731350d764aeb3035946c5d/assets/brand/wordmark-dark.svg"><img src="https://raw.githubusercontent.com/TIGER-AI-Lab/ClawBench/c8409629f4f2f9768731350d764aeb3035946c5d/assets/brand/wordmark-light.svg" alt="ClawBench" height="32"></picture></a><br>面向日常任务的开源浏览器 AI 智能体基准。<br>[★ 在 GitHub 上点星](https://github.com/TIGER-AI-Lab/ClawBench) |

**精选：** [Awesome Reverse Engineering Anything](https://github.com/reacher-z/Awesome-REA) — 工具、案例与研究论文合集，涵盖网站、游戏、应用、原生二进制、固件和通信协议。

<!-- TASKS:START -->
## 按任务查找

| 你的任务           | 从这里开始                                                                                                                                 | 可以找到什么                                     |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| 查找论文           | [论文库](https://awesomecua.com/zh/papers/) · [研究主题](https://awesomecua.com/zh/topics/) · [论文—资产关系](https://awesomecua.com/connections/) | 按年份和主题阅读已审阅论文，查看原始来源，以及经一手来源支持的代码、数据和模型关联。 |
| 选择评测基准         | [基准指南](https://awesomecua.com/guides/gui-agent-benchmarks/)                                                                           | 核对平台、任务、评估器和版本。                            |
| 寻找训练数据         | [训练数据指南](https://awesomecua.com/guides/gui-agent-training-data/)                                                                      | 比较监督形式、划分、样本单位和数据许可。                       |
| 构建智能体          | [智能体](https://awesomecua.com/categories/agent/) · [框架](https://awesomecua.com/categories/framework/)                                  | 找到实现入口、支持的平台和论文依据。                         |
| 接入 RAG 或 Agent | [使用指南](https://awesomecua.com/zh/agents/) · [数据中心](https://awesomecua.com/zh/data/)                                                   | 下载完整记录或检索文档，保留审阅状态和来源。                     |

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

**4,587 条已审阅资源** · **1,718 篇已审阅论文与综述** · **104 个发现来源文档**

证据截至 `2026-11-09T11:08:26Z`。**883 条待审阅记录**已完成书目核实；**2,255 个已发现候选**尚待处理。463 个候选已完成范围外审阅。1,308 条范围排除记录在归档中保留原始元数据。

<!-- STATS:END -->

## 浏览

<!-- EXPLORE:START -->
| 浏览                              | 内容               |    条目 |
| ------------------------------- | ---------------- | ----: |
| [按主题浏览研究](docs/topics.md)       | 按主题整理的已审阅论文      | 1,681 |
| [完整论文目录](docs/papers.md)        | 全部论文与综述记录，含待审阅记录 | 2,601 |
| [综述](docs/surveys.md)           | 电脑操作智能体研究综述      |    37 |
| [学习资源](docs/learning.md)        | 课程与教程            |    26 |
| [数据集](docs/datasets.md)         | GUI 智能体的训练与评测数据  |   195 |
| [基准](docs/benchmarks.md)        | 评测环境与任务集         |   264 |
| [模型与权重版本](docs/models.md)       | 模型权重版本与模型系列      |   283 |
| [智能体](docs/agents.md)           | 可操作电脑的公开实现       |   413 |
| [框架](docs/frameworks.md)        | 用于构建和评测智能体的代码    |   625 |
| [基础设施](docs/infrastructures.md) | 沙箱、虚拟机、设备集群与运行环境 |    90 |
| [工具](docs/tools.md)             | 评测工具、录制工具及其他实用工具 |   884 |
| [产品](docs/products.md)          | 厂商和项目提供的电脑操作产品   |    70 |
| [发布方与品牌](docs/companies.md)     | 与已收录资源相关的发布方和品牌  |    19 |

**按平台：** [Web](docs/environments/web.md) **2,349** · [Desktop](docs/environments/desktop.md) **1,554** · [Windows](docs/environments/windows.md) **487** · [macOS](docs/environments/macos.md) **476** · [Linux](docs/environments/linux.md) **439** · [Android](docs/environments/android.md) **652** · [iOS](docs/environments/ios.md) **73** · [HarmonyOS](docs/environments/harmonyos.md) **5** · [Cross-platform](docs/environments/cross-platform.md) **663**
<!-- EXPLORE:END -->

覆盖 Web、桌面、Android、iOS、Windows、macOS、Linux 和跨平台工作。主题包括 grounding、屏幕理解、规划、记忆、长流程任务、强化学习、数据生成、安全、鲁棒性和评测。环境分面可以重叠；不会根据模型的基准成绩推定框架支持。

## 使用数据

下载目录、订阅源和 RAG 文档；数据中心还列出来源、审阅状态和数据规范。

- [llms.txt](https://awesomecua.com/llms.txt) - 供语言模型使用的导航文件。
- [llms-full.txt](https://awesomecua.com/llms-full.txt) - Markdown 格式的精选注释。
- [数据中心](https://awesomecua.com/zh/data/) - 分六组提供目录、RAG 文档、引用、主题、对比、来源和数据规范。
- [目录 JSONL](https://awesomecua.com/downloads/catalog.jsonl) - 完整目录，每行一个资源。
- [下载清单](https://awesomecua.com/downloads/manifest.json) - 导出文件的数量、字节数和 SHA-256 校验和。
- [Atom 订阅源](https://awesomecua.com/feed.xml) - 以 Atom 格式发布的研究更新。
- [Hugging Face 数据集](https://huggingface.co/datasets/TIGER-Lab/AwesomeCUA) - 只读镜像；metadata_only 和 github_candidates 不是精选条目。
- [智能体与 RAG 指南](https://awesomecua.com/zh/agents/) - 面向智能体和 RAG 系统的指南。

克隆完整目录：

```sh
git clone https://github.com/reacher-z/Awesome-CUA.git
```

[Agent 操作指南](AGENTS.md) · [检索文档](https://awesomecua.com/downloads/rag-documents.jsonl)

资源发现计划**每天 00:07、08:07 和 16:07（UTC）**执行一次。[实际扫描结果](https://awesomecua.com/updates/) · [时间安排与保护机制](docs/maintenance.md)。

[阅读英文研究综述](https://awesomecua.com/survey/) — 连接方法、评测、人的控制权与可复用研究资产；工作稿附有固定版本书目和逐篇阅读记录。

## 重点资源

按类别列出被其他已收录资源在其已审阅一手来源（README、模型卡或数据集卡）中提及最多的已审阅资源。该计数反映目录内部的关联程度；每个类别页面都列出全部已审阅条目。综述排在最前，按时间倒序。资源名称和简介保留原文。

<details>
<summary>展开重点资源表</summary>

<!-- HIGHLIGHTS:START -->
**从最新综述入门** · [全部 37 项 →](docs/surveys.md)

| 日期         | 综述                                                                                                                                      | 环境             |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| 2026‑11‑04 | [GUI Grounding for Computer-Use Agents: A Survey](https://doi.org/10.20944/preprints202611.0431.v1)                                     | unspecified    |
| 2026‑10‑21 | [Multimodal Embodied Agents: A Unified Capability-centric Perspective from Computer-Use to Robot-Use](https://arxiv.org/abs/2610.30108) | unspecified    |
| 2026‑10‑14 | [Seeing, Maintaining, and Learning: The Evolution of Multimodal Agent Memory](https://arxiv.org/abs/2610.19366)                         | unspecified    |
| 2026‑09‑02 | [Efficient GUI Agents: A Systems Survey of Observation, Memory, Action, and Runtime Optimization](https://arxiv.org/abs/2609.02309)     | cross-platform |
| 2026‑08‑30 | [A Systematic Survey of Agentic Skills: Architecture, Lifecycle, and Security](https://arxiv.org/abs/2608.29596)                        | cross-platform |

**基准** · [全部 264 项 →](docs/benchmarks.md)

| 资源                                                                             | 被提及 | 环境                             | 论文                                                    | 许可            | 简介（英文）                                                                              |
| ------------------------------------------------------------------------------ | --: | ------------------------------ | ----------------------------------------------------- | ------------- | ----------------------------------------------------------------------------------- |
| [OSWorld](https://github.com/xlang-ai/OSWorld)                                 |  56 | desktop, linux, windows, macos | [2404.07972](https://arxiv.org/abs/2404.07972) (2024) | 代码 Apache-2.0 | Execution-based evaluation of agents performing tasks in real desktop environments. |
| [WebArena](https://github.com/web-arena-x/webarena)                            |  28 | web                            | [2307.13854](https://arxiv.org/abs/2307.13854) (2023) | 代码 Apache-2.0 | Self-hosted web environments and tasks for evaluating autonomous web agents.        |
| [AndroidWorld](https://github.com/google-research/android_world)               |  21 | android                        | [2405.14573](https://arxiv.org/abs/2405.14573) (2024) | 代码 Apache-2.0 | Android environment with programmatic task evaluation for mobile agents.            |
| [BrowserGym](https://github.com/ServiceNow/BrowserGym)                         |  15 | web                            | [2412.05467](https://arxiv.org/abs/2412.05467) (2024) | 代码 Apache-2.0 | Unified interfaces for browser-agent tasks and benchmark environments.              |
| [ScreenSpot Pro](https://github.com/likaixin2000/ScreenSpot-Pro-GUI-Grounding) |  14 | desktop, windows, macos, linux | —                                                     | 代码 MIT        | GUI grounding benchmark focused on professional high-resolution interfaces.         |
| [Mind2Web](https://github.com/OSU-NLP-Group/Mind2Web)                          |  11 | web                            | [2306.06070](https://arxiv.org/abs/2306.06070) (2023) | 代码 MIT        | Human demonstrations and tasks for generalist web navigation research.              |

**模型** · [全部 283 项 →](docs/models.md)

| 资源                                                                       | 被提及 | 环境                           | 论文                                                    | 许可              | 简介（英文）                                                                                                                                                                                             |
| ------------------------------------------------------------------------ | --: | ---------------------------- | ----------------------------------------------------- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [UI-TARS](https://github.com/bytedance/UI-TARS)                          |  23 | cross-platform               | [2501.12326](https://arxiv.org/abs/2501.12326) (2025) | 代码 Apache-2.0   | Native GUI agent models; UI-TARS-1.5 adds reinforcement-learned reasoning before acting and an open 7B checkpoint, and UI-TARS-2 extends to games, code and tool use.                              |
| [SeeClick](https://github.com/njucckevin/SeeClick)                       |  18 | cross-platform               | [2401.10935](https://arxiv.org/abs/2401.10935) (2024) | 代码 Apache-2.0   | GUI grounding model trained to locate visual interface elements.                                                                                                                                   |
| [Qwen2-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct) |  11 | unspecified                  | —                                                     | 权重 apache-2.0   | An instruction-tuned 7B multimodal model for image and video understanding; its card describes visually guided operation of mobile devices.                                                        |
| [Aguvis](https://github.com/xlang-ai/aguvis)                             |   8 | cross-platform               | [2412.04454](https://arxiv.org/abs/2412.04454) (2024) | —               | Vision-based GUI agent models with unified action representations.                                                                                                                                 |
| [GUI-Actor](https://github.com/microsoft/GUI-Actor)                      |   7 | cross-platform               | [2506.03143](https://arxiv.org/abs/2506.03143) (2025) | 代码 MIT          | GUI grounding model with attention-based action localization.                                                                                                                                      |
| [Holo4 27B BF16](https://huggingface.co/Hcompany/Holo4-27B)              |   7 | web, desktop, cross-platform | —                                                     | 权重 CC-BY-NC-4.0 | Dense 27B computer-use checkpoint from H Company built on Qwen3.8-27B; an external harness sends it screenshots and tool results and executes the clicks, typing, code and tool calls it requests. |

**数据集** · [全部 195 项 →](docs/datasets.md)

| 资源                                                                             | 被提及 | 环境                                    | 论文                                                    | 许可            | 简介（英文）                                                                                                                                                                                      |
| ------------------------------------------------------------------------------ | --: | ------------------------------------- | ----------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [ScreenSpot-Pro data](https://huggingface.co/datasets/likaixin/ScreenSpot-Pro) |  12 | desktop, windows, macos, linux        | [2504.07981](https://arxiv.org/abs/2504.07981) (2025) | 数据 mit        | High-resolution professional interface screenshots and target annotations for evaluating instruction-based GUI localization.                                                                |
| [OS-Genesis](https://github.com/OS-Copilot/OS-Genesis)                         |  11 | cross-platform                        | [2412.19723](https://arxiv.org/abs/2412.19723) (2024) | —             | Interaction-driven pipeline that synthesizes mobile and web GUI agent trajectories without human supervision or predefined tasks, via reverse task synthesis and a trajectory reward model. |
| [AMEX dataset release](https://huggingface.co/datasets/Yuxiang007/AMEX)        |   7 | android                               | [2407.17490](https://arxiv.org/abs/2407.17490) (2024) | 数据 cc-by-4.0  | Official Hub release of AMEX: Android app screenshots annotated for interactive-element grounding, screen and element functionality, and instructions with stepwise GUI-action chains.      |
| [Holo4 Trajectories](https://huggingface.co/datasets/Hcompany/trajectories)    |   6 | web, desktop, android, cross-platform | —                                                     | 数据 apache-2.0 | Dataset of 7,366 computer-use agent execution trajectories from Holo4 27B and Holo4 35B-A3B, recording step-level reasoning, actions, tool results, and screenshots.                        |
| [GroundCUA dataset](https://huggingface.co/datasets/ServiceNow/GroundCUA)      |   5 | desktop, windows, macos, linux        | [2511.07332](https://arxiv.org/abs/2511.07332) (2025) | 数据 mit        | Desktop GUI-grounding data from the GroundCUA project: PNG screenshots of 87 applications paired by hash with JSON lists of element boxes, visible text and optional coarse categories.     |
| [GUI-Actor data](https://huggingface.co/datasets/cckevinn/GUI-Actor-Data)      |   5 | unspecified                           | [2506.03143](https://arxiv.org/abs/2506.03143) (2025) | —             | A processed screenshot and bounding-box collection released for training GUI-Actor visual grounding models.                                                                                 |

**框架** · [全部 625 项 →](docs/frameworks.md)

| 资源                                                                                                   | 被提及 | 环境             | 论文                                                    | 许可            | 简介（英文）                                                                                                                                                                                        |
| ---------------------------------------------------------------------------------------------------- | --: | -------------- | ----------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Browser Use](https://github.com/browser-use/browser-use)                                            |  52 | web            | —                                                     | 代码 MIT        | Open-source browser agent library that runs locally with any LLM against a local or cloud browser, and also serves as a CLI for coding agents and as a driver for Claude's browser toolset.   |
| [Cua](https://github.com/trycua/cua)                                                                 |  37 | desktop        | —                                                     | 代码 MIT        | Monorepo behind Cua Spaces, which gives agents full macOS or Linux desktops, plus Cua Driver for operating native apps, Lume for Apple Silicon VMs, Cua Bench and the CUA-S1 decision models. |
| [Epic EHR Browser Automation](https://github.com/Browser-Automation-Hub/epic-ehr-browser-automation) |  13 | web            | —                                                     | 代码 MIT        | A browser automation scaffold for Epic EHR workflows such as appointments, patient lookup, notes and messaging. It documents authentication, sessions and example actions.                    |
| [SCALE-CUA (THUDM)](https://github.com/THUDM/SCALE-CUA)                                              |  12 | desktop        | [2607.11185](https://arxiv.org/abs/2607.11185) (2026) | —             | Computer-use training framework with VeriGen task synthesis, adaptive rollout sampling, and visual-context segmentation.                                                                      |
| [AgentLab](https://github.com/ServiceNow/AgentLab)                                                   |   7 | web            | [2412.05467](https://arxiv.org/abs/2412.05467) (2024) | 代码 Apache-2.0 | Experiment framework for developing and evaluating browser agents.                                                                                                                            |
| [Midscene.js](https://github.com/web-infra-dev/midscene)                                             |   7 | cross-platform | —                                                     | 代码 MIT        | Visual automation toolkit for web, mobile, and desktop interfaces.                                                                                                                            |

**智能体** · [全部 413 项 →](docs/agents.md)

| 资源                                                           | 被提及 | 环境                                                  | 论文                                                                                                                                                                                                                         | 许可            | 简介（英文）                                                                                                                                             |
| ------------------------------------------------------------ | --: | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Mobile-Agent](https://github.com/X-PLUG/MobileAgent)        |  27 | android, cross-platform                             | [2401.16158](https://arxiv.org/abs/2401.16158) (2024), [2406.01014](https://arxiv.org/abs/2406.01014) (2024), [2508.15144](https://arxiv.org/abs/2508.15144) (2025), [2602.16855](https://arxiv.org/abs/2602.16855) (2026) | 代码 MIT        | Mobile device agent family using visual interface interaction.                                                                                     |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) |  21 | cross-platform, desktop, web, linux, macos, windows | —                                                                                                                                                                                                                          | 代码 MIT        | Hermes Agent is a self-improving autonomous agent by Nous Research with procedural skill synthesis, browser control, and multi-platform sandboxes. |
| [OpenAI Codex CLI](https://github.com/openai/codex)          |  14 | cross-platform, desktop, macos, linux, windows      | —                                                                                                                                                                                                                          | 代码 Apache-2.0 | OpenAI Codex CLI is a local terminal and desktop coding agent that executes commands and edits files inside OS-enforced sandboxes.                 |
| [OpenClaw](https://github.com/openclaw/openclaw)             |  14 | cross-platform, desktop, web, macos, windows, linux | —                                                                                                                                                                                                                          | 代码 MIT        | OpenClaw is an open-source personal computer-use assistant that executes browser, desktop, terminal, and messaging workflows across local devices. |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli)    |   9 | cross-platform, desktop, macos, linux, windows      | —                                                                                                                                                                                                                          | 代码 Apache-2.0 | Gemini CLI is Google's open-source terminal agent providing shell execution, file manipulation, web search, and MCP tool integration.              |
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt)        |   9 | desktop                                             | —                                                                                                                                                                                                                          | 代码 MIT        | Tools for learning and automating workflows from desktop demonstrations.                                                                           |

<!-- HIGHLIGHTS:END -->

</details>

## 最新审阅

按时间倒序列出最新通过编辑审阅的模型、数据集、基准、系统和工具；新论文按日期列在[主题页面](docs/topics.md)中。

<details>
<summary>展开最新审阅表</summary>

<!-- RECENT:START -->
| 审阅日期       | 资源                                                                                                                                                     | 类型   | 环境                                                                | 简介（英文）                                                                                                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026‑11‑09 | [WildClawBench](https://github.com/InternLM/WildClawBench)                                                                                             | 基准   | cross-platform, web                                               | WildClawBench evaluates agents on 60 tasks in a live tool environment that includes browser use, email, files and coding. It releases evaluation code and links to task data and trajectories. |
| 2026‑11‑09 | [Rico Dataset](https://www.interactionmining.org)                                                                                                      | 数据集  | unspecified                                                       | Rico Dataset is a collection of mobile app interaction and design data presented through Interaction Mining, with 70k screens and 10k user flows across 5k apps.                               |
| 2026‑11‑09 | [OpenAdapt Agent](https://github.com/OpenAdaptAI/openadapt-agent)                                                                                      | 工具   | cross-platform, web, desktop, windows                             | OpenAdapt Agent exposes demonstrated application workflows as callable tools for AI agents. It enters values in an app and checks the record before and after saving.                          |
| 2026‑11‑09 | [ToL Hierarchical GUI region detection](https://github.com/llv22/tol_gui_region_detection)                                                             | 工具   | android                                                           | Code and configurations for training a hierarchical Android GUI region detector with DINO and running region inference on the ScreenPR benchmark.                                              |
| 2026‑11‑09 | [MiniMax M3](https://www.minimaxi.com/blog/minimax-m3)                                                                                                 | 模型   | desktop                                                           | MiniMax M3 is a multimodal model whose release page describes desktop operation from visual input and cross-application tasks through MiniMax Code.                                            |
| 2026‑11‑09 | [Code2World](https://github.com/AMAP-ML/Code2World)                                                                                                    | 工具   | android                                                           | Code2World provides code for predicting the next Android GUI screen from a screenshot and proposed action through renderable code, with an AndroidWorld agent integration.                     |
| 2026‑11‑09 | [Cerner PowerChart Browser Automation](https://github.com/Browser-Automation-Hub/cerner-powerchart-browser-automation)                                 | 工具   | web                                                               | A browser automation scaffold for Cerner PowerChart with actions for login, patient search, results, orders, and documentation export, plus a selector reference.                              |
| 2026‑11‑09 | [WAREX Supplementary Code](https://github.com/SumanKNath/WABER)                                                                                        | 工具   | web, desktop, linux                                               | WAREX supplementary code uses mitmproxy add-ons to inject popups or server and network errors into web-agent tests and record token use and latency.                                           |
| 2026‑11‑09 | [The OS X Accessibility Model](https://developer.apple.com/library/archive/documentation/Accessibility/Conceptual/AccessibilityMacOSX/OSXAXmodel.html) | 学习资源 | desktop, macos                                                    | Apple's OS X guide explains how accessibility clients inspect an app's element hierarchy, read control properties, invoke actions and receive interface-change notifications.                  |
| 2026‑11‑09 | [SkillPacks](https://github.com/agentsea/skillpacks)                                                                                                   | 工具   | desktop                                                           | SkillPacks records and approves agent tool actions for retrieval and later training, illustrated with a desktop-control example.                                                               |
| 2026‑11‑09 | [SE-GUI](https://github.com/YXB-NKU/SE-GUI)                                                                                                            | 框架   | unspecified                                                       | SE-GUI provides training and evaluation code for a GUI-grounding model refined with location-based rewards and attention feedback; its README links separate weights and seed data.            |
| 2026‑11‑09 | [OpenGVLab/MMBench-GUI](https://huggingface.co/datasets/OpenGVLab/MMBench-GUI)                                                                         | 数据集  | cross-platform, desktop, windows, macos, linux, ios, android, web | MMBench-GUI releases annotations and offline images for evaluating interface understanding and grounding within a GUI-agent benchmark spanning desktop, mobile and web platforms.              |
<!-- RECENT:END -->

</details>

## 数据文件与本地查询

使用 `python3 scripts/catalog.py get arxiv:2404.07972 --related --json` 可按稳定 ID 取得完整记录与已核实关联。[BibTeX](https://awesomecua.com/downloads/citations.bib) 和 [CSL JSON](https://awesomecua.com/downloads/citations.csl.json) 提供已审阅论文引用；每条资源页面也有可直接读取的 `record.json`。

打开[交互式网站](https://awesomecua.com/)，可以搜索和筛选全部资源、查看来源证据、切换中英文界面，或下载完整目录。网站开发与发布见 [website.md](docs/website.md)。

[中文数据中心](https://awesomecua.com/zh/data/)与[English data hub](https://awesomecua.com/data/)按六组组织公开下载：完整目录、RAG 检索文档、论文引用、主题与对比、来源与审阅状态、数据规范（schema）。克隆仓库仍可取得同一套完整源目录；数据中心提供其已发布快照的导出文件。

[下载清单](https://awesomecua.com/downloads/manifest.json)为每个列出的导出记录实际数量及单位、范围、精确字节数和 SHA-256 指纹。混合使用下载文件前，请比较各清单的 `catalog_sha256`，确认它们属于同一目录快照。

[已审阅研究](https://awesomecua.com/zh/papers/)（[English](https://awesomecua.com/papers/)） · [Computer-use agent 指南](https://awesomecua.com/guides/) · [静态资源目录](https://awesomecua.com/catalog/) · [搜索与 AI 发现](docs/search-discovery.md)

- **[目录 JSONL](https://github.com/reacher-z/Awesome-CUA/blob/main/data/catalog.jsonl)：** 每行一个资源，包含稳定 ID、类型化字段、来源证据、按范围区分的许可和审阅状态。
- **[引用图](https://github.com/reacher-z/Awesome-CUA/blob/main/data/references.jsonl)：** 一手来源中的对外引用。
- **[发现来源登记](https://github.com/reacher-z/Awesome-CUA/blob/main/data/sources.json)** 和 **[候选条目](data/candidates.jsonl)：** 来源快照，以及每个标识符的发现位置。
- **[待审队列](https://github.com/reacher-z/Awesome-CUA/blob/main/data/review-queue.jsonl)：** 未解决的证据、尚未收录的发现，以及需要编辑处理的提议。经审阅确认为非资源或已收录资源其他地址的链接仍保留在队列中，并注明 `resolution` 与理由。
- **[JSON Schema](https://github.com/reacher-z/Awesome-CUA/blob/main/schemas/resource.schema.json)** 和 **[覆盖度 JSON](data/coverage.json)：** 可机器检查的数据契约和覆盖度统计。

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

| 状态                  | 已检查的内容                              |
| ------------------- | ----------------------------------- |
| `curated`           | 基于一手来源快照的 AI 辅助编辑审阅，涵盖名称、范围、摘要和分类   |
| `metadata_verified` | 对照保留的 arXiv 或出版来源核实书目身份、标题、作者和已记录日期 |
| `candidate`         | 发现了规范化的 URL 或标识符                    |

论文、仓库、数据集发布、模型权重版本、产品和发布方可以是彼此关联的不同资源。模型系列与具体权重版本在审阅后会显式关联。

代码、数据、权重和文档的许可分别记录。缺失值为 `null`。

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

本仓库的原创代码和标注采用 [MIT 许可](LICENSE)。被链接的资源保留各自的条款。

引用本目录时，请使用 [CITATION.cff](CITATION.cff) 或 GitHub 的“Cite this repository”按钮。数据随每次扫描更新，请固定所用的确切版本。每个 `v*` 标签都有一个[数据发布](https://github.com/reacher-z/Awesome-CUA/releases)，提供由该标签所指提交构建的版本化下载：JSONL、JSON 和 SQLite 格式的目录、覆盖台账、主题与规格导出，以及它们的 `SHA256SUMS`。请引用发布标签，或在克隆中用 `git rev-parse HEAD` 记录提交，或链接该提交下的文件，例如 `https://github.com/reacher-z/Awesome-CUA/blob/<commit>/data/catalog.jsonl`。[如何发布版本](docs/maintenance.md#versioned-data-releases)。

<!-- STAR_HISTORY:START -->

## Star 历史

<a href="https://www.star-history.com/#reacher-z/Awesome-CUA&amp;Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=reacher-z/Awesome-CUA&amp;type=Date&amp;theme=dark">
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=reacher-z/Awesome-CUA&amp;type=Date">
    <img src="https://api.star-history.com/svg?repos=reacher-z/Awesome-CUA&amp;type=Date" alt="Awesome-CUA 的 GitHub Star 数量随时间变化趋势" width="100%">
  </picture>
</a>

[在 Star History 查看 Awesome-CUA 的 Star 历史](https://www.star-history.com/#reacher-z/Awesome-CUA&Date)

<!-- STAR_HISTORY:END -->
