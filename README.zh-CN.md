<h1 align="center"><a href="https://awesomecua.com/zh/"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/brand/wordmark-dark.svg"><img src="assets/brand/wordmark-light.svg" alt="Awesome Computer-Use Agents" width="560"></picture></a></h1>

<div align="center">

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/brand/tagline-dark.svg"><img src="assets/brand/tagline-light.svg" alt="面向电脑操作智能体的论文、模型、数据集、基准和工具，每条都链接一手来源"></picture>

<!-- BADGES:START -->
[![Website](assets/brand/badges/website.svg)](https://awesomecua.com/) [![Papers](assets/brand/badges/papers.svg)](https://awesomecua.com/papers/) [![Benchmarks](assets/brand/badges/benchmarks.svg)](https://awesomecua.com/compare/benchmarks/) [![Data](assets/brand/badges/data.svg)](https://awesomecua.com/data/) [![Hugging Face](assets/brand/badges/huggingface.svg)](https://huggingface.co/datasets/AgPerry/awesome-cua) [![Star on GitHub](assets/brand/badges/star.svg)](https://github.com/reacher-z/Awesome-CUA)
<!-- BADGES:END -->

[浏览](#explore) · [数据](docs/data.zh-CN.md) · [论文](docs/papers.md) · [主题](docs/topics.md) · [文档](docs/README.md) · [引用](CITATION.cff) · [English](README.md) · [Awesome REA](https://github.com/reacher-z/Awesome-REA) · [WebsiteBench](https://github.com/TIGER-AI-Lab/WebsiteBench)

</div>

## 推荐基准

| 网站逆向工程                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 浏览器智能体                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| <a href="https://github.com/TIGER-AI-Lab/WebsiteBench"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/TIGER-AI-Lab/WebsiteBench/78f5558e8197bb91b3bab63428c12b92060ddc6f/assets/wordmark-dark.svg"><img src="https://raw.githubusercontent.com/TIGER-AI-Lab/WebsiteBench/78f5558e8197bb91b3bab63428c12b92060ddc6f/assets/wordmark-light.svg" alt="WebsiteBench" height="32"></picture></a><br>AI 智能体能否通过浏览器探索重建网站？<br><a href="https://github.com/TIGER-AI-Lab/WebsiteBench">★ 在 GitHub 上点星</a> | <a href="https://github.com/TIGER-AI-Lab/ClawBench"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/TIGER-AI-Lab/ClawBench/c8409629f4f2f9768731350d764aeb3035946c5d/assets/brand/wordmark-dark.svg"><img src="https://raw.githubusercontent.com/TIGER-AI-Lab/ClawBench/c8409629f4f2f9768731350d764aeb3035946c5d/assets/brand/wordmark-light.svg" alt="ClawBench" height="32"></picture></a><br>面向日常任务的开源浏览器 AI 智能体基准。<br><a href="https://github.com/TIGER-AI-Lab/ClawBench">★ 在 GitHub 上点星</a> |

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

**1,863 条已审阅资源** · **1,391 篇已审阅论文与综述** · **103 个发现来源文档**

<!-- STATS:END -->

## 浏览

<!-- EXPLORE:START -->
| 浏览                              | 内容               |    条目 |
| ------------------------------- | ---------------- | ----: |
| 按主题浏览研究                         | 按主题整理的已审阅论文      | 1,368 |
| 完整论文目录                          | 全部论文与综述记录，含待审阅记录 | 2,018 |
| [综述](docs/surveys.md)           | 电脑操作智能体研究综述      |    23 |
| [学习资源](docs/learning.md)        | 课程与教程            |     2 |
| [数据集](docs/datasets.md)         | GUI 智能体的训练与评测数据  |    86 |
| [基准](docs/benchmarks.md)        | 评测环境与任务集         |    90 |
| [模型与权重版本](docs/models.md)       | 模型权重版本与模型系列      |    98 |
| [智能体](docs/agents.md)           | 可操作电脑的公开实现       |    45 |
| [框架](docs/frameworks.md)        | 用于构建和评测智能体的代码    |    79 |
| [基础设施](docs/infrastructures.md) | 沙箱、虚拟机、设备集群与运行环境 |    14 |
| [工具](docs/tools.md)             | 评测工具、录制工具及其他实用工具 |    22 |
| [产品](docs/products.md)          | 厂商和项目提供的电脑操作产品   |    20 |
| [发布方与品牌](docs/companies.md)     | 与已收录资源相关的发布方和品牌  |    16 |

**按平台：** [Web](docs/environments/web.md) **733** · [Desktop](docs/environments/desktop.md) **342** · [Windows](docs/environments/windows.md) **66** · [macOS](docs/environments/macos.md) **32** · [Linux](docs/environments/linux.md) **55** · [Android](docs/environments/android.md) **332** · [iOS](docs/environments/ios.md) **24** · [HarmonyOS](docs/environments/harmonyos.md) **3** · [Cross-platform](docs/environments/cross-platform.md) **200**
<!-- EXPLORE:END -->

最常被提及的资源与最新审阅见[重点资源与最新审阅](docs/highlights.zh-CN.md)。

覆盖 Web、桌面、Android、iOS、Windows、macOS、Linux 和跨平台工作。主题包括 grounding、屏幕理解、规划、记忆、长流程任务、强化学习、数据生成、安全、鲁棒性和评测。环境分面可以重叠；不会根据模型的基准成绩推定框架支持。

## “已核实”的含义

| 状态                  | 已检查的内容                              | 尚未确认的内容                |
| ------------------- | ----------------------------------- | ---------------------- |
| `curated`           | 基于一手来源快照的 AI 辅助编辑审阅，涵盖名称、范围、摘要和分类   | 独立复现、普遍可用性或背书          |
| `metadata_verified` | 对照保留的 arXiv 或出版来源核实书目身份、标题、作者和已记录日期 | 主题相关性、方法、结论，或是否属于核心领域  |
| `candidate`         | 发现了规范化的 URL 或标识符                    | 是否收录、是否正确或是否可用；不计入公开目录 |

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

网络发现和核实需要显式运行相应命令；常规构建不联网。一手来源快照发生变化后，必须重新进行编辑审阅才能发布。维护指南 · [方法说明](docs/methodology.md) · [数据字典](docs/data-dictionary.md)

## 致谢与复用

[来源登记](data/sources.json)列出了用于发现资源的社区合集和综述。书目记录依据保留的 arXiv、出版方及作者来源；出版记录分别保留各版本的题名、作者和日期精度。部分资源还会对照发布方的仓库、文档以及模型/数据集卡片核查。上游 README、论文、模型权重和数据集不在本仓库中再分发。

本仓库的原创代码和标注采用 [MIT 许可](LICENSE)。被链接的资源保留各自的条款。

引用本目录时，请使用 CITATION.cff 或 GitHub 的“Cite this repository”按钮。数据随每次扫描更新，请固定所用的确切版本。每个 `v*` 标签都有一个[数据发布](https://github.com/reacher-z/Awesome-CUA/releases)，提供由该标签所指提交构建的版本化下载：JSONL、JSON 和 SQLite 格式的目录、覆盖台账、主题与规格导出，以及它们的 `SHA256SUMS`。请引用发布标签，或在克隆中用 `git rev-parse HEAD` 记录提交，或链接该提交下的文件，例如 `https://github.com/reacher-z/Awesome-CUA/blob/<commit>/data/catalog.jsonl`。[如何发布版本](docs/maintenance.md#versioned-data-releases)。
