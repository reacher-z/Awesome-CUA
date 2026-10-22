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
[![Catalog records](https://img.shields.io/badge/records-3%2C249-4856df?style=flat-square&labelColor=303447)](data/catalog.jsonl) [![Source-reviewed records](https://img.shields.io/badge/source--reviewed-1%2C671-4856df?style=flat-square&labelColor=303447)](docs/coverage.md) [![Catalog checks](https://github.com/reacher-z/Awesome-CUA/actions/workflows/catalog.yml/badge.svg?branch=main)](https://github.com/reacher-z/Awesome-CUA/actions/workflows/catalog.yml) [![MIT license](https://img.shields.io/badge/license-MIT-606779?style=flat-square&labelColor=303447)](LICENSE)
<!-- BADGES:END -->

[按任务查找](#按任务查找) · [超过三小时的任务](#超过三小时的任务) · [浏览](#浏览) · [重点资源](#重点资源) · [最新审阅](#最新审阅) · [使用数据](#使用数据)

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

## 超过三小时的任务

同时具备输入、输出，且一手来源写明耗时超过 3 小时的具体电脑操作任务，仍是覆盖缺口。目标是 1,000 条。已打开的一手来源目前支持 **29** 条。缺口是 971。短时的 GUI、网页、移动端和定位样本不计入这 29 条。

| 字段 | 来源写明的内容 |
| --- | --- |
| 任务 | Cradle，Dealer's Life 2，[`env_config_dealers.json`](https://github.com/BAAI-Agents/Cradle/blob/main/conf/env_config_dealers.json) 中的任务 id 1 |
| 输入 | 自动游玩 Dealer's Life 2，持续 7 天。在出价页面调用 `give_price` 并传入整数。在其他页面点击屏幕上给出的选项。 |
| 时长 | 该任务说明中的 7 天 |
| 输出 | 同一段说明把目标写为尽量扩大利润。该文件没有另给期望输出。 |

[![Cradle 的 Dealer's Life 2 环境说明所附起始画面：柜台前的买家、对话选项，以及游戏内日历第 1 月第 1 周第 1 天。](https://raw.githubusercontent.com/BAAI-Agents/Cradle/main/docs/envs/images/dealers/dealer_start.jpg)](https://github.com/BAAI-Agents/Cradle/blob/main/docs/envs/dealers.md)

图片仍在 Cradle 仓库中。环境说明用它表示这次运行的起始画面。7 天是任务说明里的时长；配置没有另外写明实际经过了多少小时。画面上的游戏内日历停在第 1 月第 1 周第 1 天。

Cradle 的其他环境配置没有第二条写明超过 3 小时的任务。[WorkArena README](https://raw.githubusercontent.com/ServiceNow/WorkArena/HEAD/README.md) 统计了 682 个 WorkArena++ 任务，没有给出逐条时长。其组合任务模块里的 1 天、2 天和 3 天是变更请求的排期字段。[TheAgentCompany](https://arxiv.org/abs/2412.14161) 写道，完成单个任务可能从 10 分钟到数小时不等，并且有些复杂任务的设计耗时超过 10 小时。这些句子没有指出哪一条任务的执行时间超过 3 小时。

[OmegaUse-OfficeVal](https://omegause-officeval.github.io/) 增加 28 条。它的[英文任务记录](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/data-studio/train.jsonl)用 `human_labor_time` 记录分钟数，也就是人工在不使用模型时完成该任务的平均时间。数据集说明写明单位是分钟。100 条任务的平均值是 139.42 分钟，与项目页上的 2.32 小时一致。其中 28 条超过 180 分钟。最长的 `officeval_046` 是 501 分钟，即项目页上的 8.35 小时。每条记录都有指令、输入文件地址，以及交付物评分标准。同一页面上最快模型的平均用时是每条 0.184 小时；这里不把模型运行时间算作任务时长。

| 任务 | 分钟 | 指令 |
| --- | ---: | --- |
| [officeval_001](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_001.json) | 204 | Modify the provided Word documents according to the following requirements: 1. Delete the content under "Lesson Learning Objectives" and... |
| [officeval_008](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_008.json) | 304 | Translate the English-language PDF paper into Chinese, and modify the translated paper using the formatting of the “Translated Literature... |
| [officeval_010](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_010.json) | 228 | Modify the flowchart in the document: delete the fourth row, move the text inside the boxes, and make the flowchart editable. |
| [officeval_013](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_013.json) | 227 | Check the paper's cover page, Chinese abstract, English abstract, table of contents, main text, references, and acknowledgments in accord... |
| [officeval_018](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_018.json) | 251 | Modify the “Public Notice Study Room Operations Plan” report in accordance with the formatting requirements, including the font, font siz... |
| [officeval_019](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_019.json) | 249 | Add a cover page to the exam paper (refer to the images for the specific layout); center the main title in the exam paper and set it in S... |
| [officeval_020](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_020.json) | 194 | Format the lesson plan according to the formatting requirements shown in the image. |
| [officeval_022](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_022.json) | 287 | Following the format of the “Statement of Business Operations,” reformat the “Business Operations Anomaly Investigation Submission Materi... |
| [officeval_024](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_024.json) | 211 | Make the following adjustments to my thesis in accordance with the formatting requirements in the thesis template document: 1. Adjust and... |
| [officeval_031](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_031.json) | 255 | Place the test questions from the PDF into the provided Word template, matching the question formatting in the Word document. |
| [officeval_033](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_033.json) | 307 | Replace every retail price value in the document with the value obtained by multiplying it by 1.1, keep all other formatting unchanged, a... |
| [officeval_034](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_034.json) | 188 | Format the document. For the formatting of the individual clauses, follow the layout shown in the images: use two columns, with Chinese a... |
| [officeval_040](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_040.json) | 190 | 1. Format the document title as follows: LiSu, size No. 2, bold, blue, Glow (Olive Green, 7 pt glow, Accent 3), Shadow (Offset: Top), cen... |
| [officeval_043](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_043.json) | 400 | Recreate the business card as a 2-slide PowerPoint presentation. All elements in the resulting presentation must be editable, except that... |
| [officeval_046](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_046.json) | 501 | Create a new two-slide ppt for me and replicate just these 2 pages (they must be exactly identical), centered on two 30 × 20 PPT slides w... |
| [officeval_049](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_049.json) | 240 | Recreate this image, with every element editable, and deliver it to me as a one-slide ppt with the same dimensions as the image. |
| [officeval_050](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_050.json) | 321 | Please make these two PowerPoint slides directly editable, including allowing content to be deleted, while keeping the content exactly th... |
| [officeval_054](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_054.json) | 239 | Recreate the original image as a single-slide PowerPoint presentation with content identical to the original image. It must be editable.... |
| [officeval_055](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_055.json) | 188 | Turn this image into an editable PPT, not an image. Also make the following adjustments: 1. Replace the word “assessment” in the second s... |
| [officeval_056](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_056.json) | 230 | Recreate this flowchart in a PPT using text boxes and arrow shapes. The completed flowchart must be fully editable, not an image; make it... |
| [officeval_072](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_072.json) | 187 | Turn this into a PPT with editable text; the layout, content, and colors should all be roughly the same as the original. |
| [officeval_074](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_074.json) | 237 | Translate all Chinese text in this PowerPoint into English. Do not disrupt the layout or change the image backgrounds. |
| [officeval_076](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_076.json) | 194 | Turn the following content I sent you into a PPT. Use one slide for each title section, make each level-one heading a section title slide... |
| [officeval_079](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_079.json) | 241 | Translate the content of the PPT into Mongolian. Do not change any data or layout positions. |
| [officeval_081](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_081.json) | 196 | Create an Excel spreadsheet that achieves what is demonstrated in the video: after a number is entered in one cell, the active cell autom... |
| [officeval_082](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_082.json) | 230 | In the “1111” spreadsheet, set it up so that when items on the left are checked, the selected content is automatically displayed on the r... |
| [officeval_084](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_084.json) | 344 | Could you create a macro button? In the first workbook, create a macro button so that clicking the “Print Credit Slip” button outlined by... |
| [officeval_085](https://huggingface.co/datasets/baidu-frontier-research/OmegaUse-OfficeVal/blob/main/task-en/officeval_085.json) | 213 | Could you create three charts for the three tables, styled like the S11 chart in the image? Place each completed chart in the table corre... |

<!-- STATS:START -->

**3,249 条资源记录** · **1,671 条已审阅** · **2,778 条论文与综述记录** · **54 个发现来源文档**

证据截至 `2026-10-22T04:46:45Z`。1,578 条记录仅完成书目核实；907 个已发现的标识符尚待处理，另有 136 个链接经审阅确认为非资源或已收录资源的其他地址，不计入其中。138 条范围排除记录在归档中保留原始元数据。各项计数存在重叠，详见下文。

<!-- STATS:END -->

## 浏览

<!-- EXPLORE:START -->
| 研究与训练 | 工程与产业 |
| --- | --- |
| [按主题浏览研究](docs/topics.md) · **1,181** 篇已审阅论文 · [完整论文目录](docs/papers.md) · 2,778 条论文与综述记录 | [智能体](docs/agents.md) · **45** |
| [综述](docs/surveys.md) · **19** · [学习资源](docs/learning.md) · **2** | [框架](docs/frameworks.md) · **79** |
| [数据集](docs/datasets.md) · **86** | [基础设施](docs/infrastructures.md) · **14** |
| [基准](docs/benchmarks.md) · **89** | [工具](docs/tools.md) · **22** |
| [模型与权重版本](docs/models.md) · **98** | [产品](docs/products.md) · **20** · [发布方与品牌](docs/companies.md) · **16** |

**按平台：** [Web](docs/environments/web.md) **646** · [Desktop](docs/environments/desktop.md) **334** · [Windows](docs/environments/windows.md) **65** · [macOS](docs/environments/macos.md) **30** · [Linux](docs/environments/linux.md) **54** · [Android](docs/environments/android.md) **323** · [iOS](docs/environments/ios.md) **22** · [HarmonyOS](docs/environments/harmonyos.md) **3** · [Cross-platform](docs/environments/cross-platform.md) **197**
<!-- EXPLORE:END -->

覆盖 Web、桌面、Android、iOS、Windows、macOS、Linux 和跨平台工作。主题包括 grounding、屏幕理解、规划、记忆、长流程任务、强化学习、数据生成、安全、鲁棒性和评测。环境分面可以重叠；不会根据模型的基准成绩推定框架支持。

## 重点资源

按类别列出被其他已收录资源在其已审阅一手来源（README、模型卡或数据集卡）中提及最多的已审阅资源。该计数反映目录内部的关联程度，不代表质量、流行度或基准表现；每个类别页面都列出全部已审阅条目。综述排在最前，按时间倒序。资源名称和简介保留原文。

<!-- HIGHLIGHTS:START -->
**从最新综述入门** · [全部 19 项 →](docs/surveys.md)

| 日期 | 综述 | 环境 |
| --- | --- | --- |
| 2026‑10‑14 | [Seeing, Maintaining, and Learning: The Evolution of Multimodal Agent Memory](https://arxiv.org/abs/2610.19366) | unspecified |
| 2026‑09‑02 | [Efficient GUI Agents: A Systems Survey of Observation, Memory, Action, and Runtime Optimization](https://arxiv.org/abs/2609.02309) | cross-platform |
| 2026‑08‑30 | [A Systematic Survey of Agentic Skills: Architecture, Lifecycle, and Security](https://arxiv.org/abs/2608.29596) | cross-platform |
| 2026‑04‑17 | [A Survey on Long-Term Memory Security in LLM Agents: Attacks, Defenses, and Governance Across the Memory Lifecycle](https://arxiv.org/abs/2604.16548) | unspecified |
| 2026‑02‑12 | [Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward](https://arxiv.org/abs/2602.12430) | unspecified |

**基准** · [全部 89 项 →](docs/benchmarks.md)

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

**数据集** · [全部 86 项 →](docs/datasets.md)

| 资源 | 被提及 | 环境 | 论文 | 许可 | 简介（英文） |
| --- | ---: | --- | --- | --- | --- |
| [ScreenSpot-Pro data](https://huggingface.co/datasets/likaixin/ScreenSpot-Pro) | 4 | desktop, windows, macos, linux | [2504.07981](https://arxiv.org/abs/2504.07981) (2025) | 数据 mit | High-resolution professional interface screenshots and target annotations for evaluating instruction-based GUI localization. |
| [GUI-Odyssey](https://github.com/OpenGVLab/GUI-Odyssey) | 3 | android | [2406.08451](https://arxiv.org/abs/2406.08451) (2024) | — | Human-demonstrated Android episodes for cross-app navigation, spanning six task types, 212 apps and about 1,400 app combinations, for training and evaluating agents. |
| [GUIAct](https://huggingface.co/datasets/yiye2023/GUIAct) | 3 | web, android | [2406.11317](https://arxiv.org/abs/2406.11317) (2024) | — | Web and Android GUI action-instruction data, with single-step, multi-step and smartphone partitions. |
| [GUIChat](https://huggingface.co/datasets/yiye2023/GUIChat) | 3 | unspecified | [2406.11317](https://arxiv.org/abs/2406.11317) (2024) | — | Conversational GUI supervision with text-rich images and bounding boxes, organized as single-turn questions and multi-turn dialogues. |
| [GUIEnv-local](https://huggingface.co/datasets/yiye2023/GUIEnv) | 3 | web | [2406.11317](https://arxiv.org/abs/2406.11317) (2024) | — | The released local-supervision portion of GUIEnv, pairing webpage regions and text for OCR and GUI grounding. |
| [OpenMobile-Data-v2](https://huggingface.co/datasets/OpenMobile-2/OpenMobile-Data-v2) | 3 | android, web | [2610.14157](https://arxiv.org/abs/2610.14157) (2026) | — | Mobile-agent supervision from emulator and simulator trajectories, plus executable tasks with starting states and success checks for reinforcement learning. |

**框架** · [全部 79 项 →](docs/frameworks.md)

| 资源 | 被提及 | 环境 | 论文 | 许可 | 简介（英文） |
| --- | ---: | --- | --- | --- | --- |
| [Browser Use](https://github.com/browser-use/browser-use) | 7 | web | — | 代码 MIT | Open-source browser agent library that runs locally with any LLM against a local or cloud browser, and also serves as a CLI for coding agents and as a driver for Claude's browser toolset. |
| [AgentLab](https://github.com/ServiceNow/AgentLab) | 5 | web | [2412.05467](https://arxiv.org/abs/2412.05467) (2024) | 代码 Apache-2.0 | Experiment framework for developing and evaluating browser agents. |
| [Seg2Click](https://github.com/jcwang0602/Seg2Click) | 5 | cross-platform | [2610.16234](https://arxiv.org/abs/2610.16234) (2026) | 代码 MIT | Training and inference implementation that predicts an executable-region mask and derives a GUI click from that mask. |
| [OpenMobile-2 code](https://github.com/OpenMobile2/OpenMobile2-Code) | 3 | android, web | [2610.14157](https://arxiv.org/abs/2610.14157) (2026) | 代码 Apache-2.0 | Evaluation adapters and training guidance for OpenMobile-2 across Android emulators and browser-rendered mobile simulation. |
| [UI-Genie](https://github.com/Euphoria16/UI-Genie) | 3 | android | [2505.21496](https://arxiv.org/abs/2505.21496) (2025) | — | Training and evaluation code for a mobile-agent framework that iteratively generates trajectories using agent and reward-model feedback. |
| [Computer Use OOTB](https://github.com/showlab/computer_use_ootb) | 2 | desktop | [2411.10323](https://arxiv.org/abs/2411.10323) (2024) | 代码 Apache-2.0 | Gradio desktop GUI agent for Windows and macOS that needs no Docker, using Claude 3.5 Computer Use over the API or ShowUI and UI-TARS run locally, with multi-display and phone remote control. |

**智能体** · [全部 45 项 →](docs/agents.md)

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
| 2026‑10‑20 | [Web Browser Automation with Agents (smolagents tutorial)](https://huggingface.co/docs/smolagents/examples/web_browser) | 学习资源 | web | Versioned tutorial building a vision-guided CodeAgent with Selenium/Helium browser tools, screenshot callbacks and example web-navigation tasks. |
| 2026‑10‑20 | [ORBIT framework](https://github.com/wlanderson0/orbit) | 框架 | web, desktop | Inspect-based multi-agent evaluation framework with role, scheduling and communication controls, BrowserART accessibility-tree actions, and desktop mouse, keyboard and screenshot tools. |
| 2026‑10‑20 | [Building AI Browser Agents](https://www.deeplearning.ai/courses/building-ai-browser-agents) | 学习资源 | web | Browser-agent course with worked lessons on structured web extraction and multi-step browser interaction, followed by AgentQ search and self-correction concepts. |
| 2026‑10‑20 | [Yunkai](https://github.com/solplum/yunkai) | 智能体 | android | Android phone assistant combining model-driven tool use with accessibility-tree reading, screenshots, and tap, swipe and text-entry primitives. Its documented interaction flow presents operation plans for user confirmation. |
| 2026‑10‑20 | [WinDOM code](https://github.com/ChenghengLi/WinDOM) | 框架 | web | GUI-grounding training and evaluation code with same-family distillation, GRPO recipes and point-in-box scoring, using a Windows-style web environment. |
| 2026‑10‑20 | [Web Context Bench (Python)](https://github.com/charlypoly/web-context-bench-python) | 基准 | web | Local-page benchmark comparing six browser representations on token use, factual reading and target-element selection, with deterministic answer scoring. |
| 2026‑10‑20 | [Mobster engine](https://github.com/RadishSoftware/mobster) | 智能体 | ios | iOS agent engine organized around an observe, decide, verify and act loop, using WebDriverAgent screen state and phone actions such as taps, typing, swipes and app switches. |
| 2026‑10‑20 | [GUI Grounding Evaluation Harness](https://github.com/PatrickStarL/gui-grounding-eval) | 工具 | unspecified | ScreenSpot-Pro evaluation harness with explicit coordinate transforms, prompt and crop-based inference comparisons, and per-sample grounding accuracy and cost records. |
| 2026‑10‑20 | [Activity Recorder](https://github.com/anikasomaia/local-activity-recorder) | 工具 | desktop, windows | Windows tray utility that records primary-display screenshots, keyboard key codes and mouse events as local JPEG and JSON files for training-data collection. |
| 2026‑10‑20 | [MobileForge](https://github.com/kwai/MobileForge) | 框架 | android | Android GUI-agent adaptation framework combining app exploration, generated curricula and rollout feedback with hint-conditioned step-level GRPO; the documented public training path targets Qwen3-VL-8B. |
| 2026‑10‑20 | [MemGUI-Agent](https://github.com/kwai/MemGUI-Agent) | 框架 | android | MemGUI-Agent training and offline evaluation tools provide trajectory conversion, LoRA SFT templates, and step-level checks of GUI actions, memory updates and context folding. |
| 2026‑10‑18 | [VideoCAD data](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/WX8PCK) | 数据集 | web | CAD screen recordings paired with action logs and target model images for studying precise interface control and long-horizon visual imitation. |
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
