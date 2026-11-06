# 使用数据

下载目录、订阅源和 RAG 文档；数据中心还列出来源、审阅状态和数据规范。

- [llms.txt](https://awesomecua.com/llms.txt) - 供语言模型使用的导航文件。
- [llms-full.txt](https://awesomecua.com/llms-full.txt) - Markdown 格式的精选注释。
- 数据中心 - 分六组提供目录、RAG 文档、引用、主题、对比、来源和数据规范。
- [目录 JSONL](https://awesomecua.com/downloads/catalog.jsonl) - 完整目录，每行一个资源。
- [下载清单](https://awesomecua.com/downloads/manifest.json) - 导出文件的数量、字节数和 SHA-256 校验和。
- [Atom 订阅源](https://awesomecua.com/feed.xml) - 以 Atom 格式发布的研究更新。
- [Hugging Face 数据集](https://huggingface.co/datasets/AgPerry/awesome-cua) - Parquet 与 JSONL 镜像，每种记录类型一个 config，每 2 小时同步。
- 智能体与 RAG 指南 - 面向智能体和 RAG 系统的指南。

克隆完整目录：

```sh
git clone https://github.com/reacher-z/Awesome-CUA.git
```

[Agent 操作指南](AGENTS.md) · [检索文档](https://awesomecua.com/downloads/rag-documents.jsonl)

资源发现计划每两小时执行一次，时间为 **UTC 00:07、02:07、04:07、06:07、08:07、10:07、12:07、14:07、16:07、18:07、20:07 和 22:07**。[实际扫描结果](https://awesomecua.com/updates/) · [时间安排与保护机制](docs/maintenance.md)。

[阅读英文研究综述](https://awesomecua.com/survey/) — 连接方法、评测、人的控制权与可复用研究资产；工作稿附有固定版本书目和逐篇阅读记录。

## 数据文件与本地查询

使用 `python3 scripts/catalog.py get arxiv:2404.07972 --related --json` 可按稳定 ID 取得完整记录与已核实关联。[BibTeX](https://awesomecua.com/downloads/citations.bib) 和 [CSL JSON](https://awesomecua.com/downloads/citations.csl.json) 提供已审阅论文引用；每条资源页面也有可直接读取的 `record.json`。

打开[交互式网站](https://awesomecua.com/)，可以搜索和筛选全部资源、查看来源证据、切换中英文界面，或下载完整目录。网站开发与发布见 [website.md](docs/website.md)。

中文数据中心与[English data hub](https://awesomecua.com/data/)按六组组织公开下载：完整目录、RAG 检索文档、论文引用、主题与对比、来源与审阅状态、数据规范（schema）。克隆仓库仍可取得同一套完整源目录；数据中心提供其已发布快照的导出文件。

下载清单为每个列出的导出记录实际数量及单位、范围、精确字节数和 SHA-256 指纹。不同格式和视图可能包含相同资源，单位也可能不同，不能把这些数量相加。混合使用下载文件前，请比较各清单的 `catalog_sha256`，确认它们属于同一目录快照。

已审阅研究（[English](https://awesomecua.com/papers/)） · [Computer-use agent 指南](https://awesomecua.com/guides/) · [静态资源目录](https://awesomecua.com/catalog/) · [搜索与 AI 发现](docs/search-discovery.md)

- [目录 JSONL](https://github.com/reacher-z/Awesome-CUA/blob/main/data/catalog.jsonl) - 每行一个资源，包含稳定 ID、类型化字段、来源证据、按范围区分的许可和审阅状态。
- [引用图](https://github.com/reacher-z/Awesome-CUA/blob/main/data/references.jsonl) - 一手来源中的对外引用。`mentions` 与 `trained_on`、`evaluated_on` 是各自独立的关系。
- [发现来源登记](https://github.com/reacher-z/Awesome-CUA/blob/main/data/sources.json) - 来源快照，以及每个标识符的发现位置（另见 [候选条目](data/candidates.jsonl)）。
- [待审队列](https://github.com/reacher-z/Awesome-CUA/blob/main/data/review-queue.jsonl) - 未解决的证据、尚未收录的发现，以及需要编辑处理的提议。经审阅确认为非资源或已收录资源其他地址的链接仍保留在队列中，并注明 `resolution` 与理由。
- [JSON Schema](https://github.com/reacher-z/Awesome-CUA/blob/main/schemas/resource.schema.json) - 可机器检查的数据契约和覆盖度统计（另见 [覆盖度 JSON](data/coverage.json)）。

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
