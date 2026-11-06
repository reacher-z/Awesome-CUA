<h1 align="center"><a href="https://awesomecua.com/"><picture><source media="(prefers-color-scheme: dark)" srcset="assets/brand/wordmark-dark.svg"><img src="assets/brand/wordmark-light.svg" alt="Awesome Computer-Use Agents" width="560"></picture></a></h1>

<div align="center">

<picture><source media="(prefers-color-scheme: dark)" srcset="assets/brand/tagline-dark.svg"><img src="assets/brand/tagline-light.svg" alt="Papers, models, datasets, benchmarks and tools for agents that use computers, each linked to its primary source"></picture>

<!-- BADGES:START -->
[![Website](assets/brand/badges/website.svg)](https://awesomecua.com/) [![Papers](assets/brand/badges/papers.svg)](https://awesomecua.com/papers/) [![Benchmarks](assets/brand/badges/benchmarks.svg)](https://awesomecua.com/compare/benchmarks/) [![Data](assets/brand/badges/data.svg)](https://awesomecua.com/data/) [![Hugging Face](assets/brand/badges/huggingface.svg)](https://huggingface.co/datasets/AgPerry/awesome-cua) [![Star on GitHub](assets/brand/badges/star.svg)](https://github.com/reacher-z/Awesome-CUA)
<!-- BADGES:END -->

[Browse](#explore) · [Data](docs/data.md) · [Papers](docs/papers.md) · [Topics](docs/topics.md) · [Docs](docs/README.md) · [Cite](CITATION.cff) · [中文](README.zh-CN.md) · [Awesome REA](https://github.com/reacher-z/Awesome-REA) · [WebsiteBench](https://github.com/TIGER-AI-Lab/WebsiteBench)

</div>

## Featured benchmarks

| Website reverse engineering                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Browser agents                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| <a href="https://github.com/TIGER-AI-Lab/WebsiteBench"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/TIGER-AI-Lab/WebsiteBench/78f5558e8197bb91b3bab63428c12b92060ddc6f/assets/wordmark-dark.svg"><img src="https://raw.githubusercontent.com/TIGER-AI-Lab/WebsiteBench/78f5558e8197bb91b3bab63428c12b92060ddc6f/assets/wordmark-light.svg" alt="WebsiteBench" height="32"></picture></a><br>Can AI agents rebuild websites through browser exploration?<br><a href="https://github.com/TIGER-AI-Lab/WebsiteBench">★ Star on GitHub</a> | <a href="https://github.com/TIGER-AI-Lab/ClawBench"><picture><source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/TIGER-AI-Lab/ClawBench/c8409629f4f2f9768731350d764aeb3035946c5d/assets/brand/wordmark-dark.svg"><img src="https://raw.githubusercontent.com/TIGER-AI-Lab/ClawBench/c8409629f4f2f9768731350d764aeb3035946c5d/assets/brand/wordmark-light.svg" alt="ClawBench" height="32"></picture></a><br>Open-source benchmark for browser AI agents on daily tasks.<br><a href="https://github.com/TIGER-AI-Lab/ClawBench">★ Star on GitHub</a> |

<!-- TASKS:START -->
## Find by task

| Your task           | Start here                                                                                                                   | What you can find                                                                                                                            |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Find papers         | Research library · [Topics](https://awesomecua.com/topics/) · [Paper–asset connections](https://awesomecua.com/connections/) | Reviewed papers by year and topic, with original sources and the code, datasets and models linked to them through reviewed primary evidence. |
| Choose a benchmark  | [Benchmark guide](https://awesomecua.com/guides/gui-agent-benchmarks/)                                                       | Platforms, tasks, evaluators, and versions to compare.                                                                                       |
| Find training data  | [Training-data guide](https://awesomecua.com/guides/gui-agent-training-data/)                                                | Supervision, splits, count units, and data licenses.                                                                                         |
| Build an agent      | [Agents](https://awesomecua.com/categories/agent/) · [Frameworks](https://awesomecua.com/categories/framework/)              | Implementation entry points, supported platforms, and papers.                                                                                |
| Use RAG or an agent | [Agent guide](https://awesomecua.com/agents/) · Data hub                                                                     | Complete records or retrieval documents with review states and sources.                                                                      |

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

**1,863 curated resources** · **1,391 reviewed papers and surveys** · **103 discovery documents**

<!-- STATS:END -->

## Explore

<!-- EXPLORE:START -->
| Browse                                           | What you find                                                 | Entries |
| ------------------------------------------------ | ------------------------------------------------------------- | ------: |
| Research by topic                                | Reviewed papers grouped by topic                              |   1,368 |
| Full bibliography                                | All paper and survey records, including those awaiting review |   2,018 |
| [Surveys](docs/surveys.md)                       | Surveys of computer-use agent research                        |      23 |
| [Learning resources](docs/learning.md)           | Courses and tutorials                                         |       2 |
| [Datasets](docs/datasets.md)                     | Training and evaluation data for GUI agents                   |      86 |
| [Benchmarks](docs/benchmarks.md)                 | Evaluation environments and task suites                       |      90 |
| [Models and checkpoint releases](docs/models.md) | Checkpoints and model families                                |      98 |
| [Agents](docs/agents.md)                         | Open implementations that act on a computer                   |      45 |
| [Frameworks](docs/frameworks.md)                 | Code for building and evaluating agents                       |      79 |
| [Infrastructure](docs/infrastructures.md)        | Sandboxes, VMs, device farms and environments                 |      14 |
| [Tools](docs/tools.md)                           | Evaluation harnesses, recorders and other utilities           |      22 |
| [Products](docs/products.md)                     | Computer-use products from vendors and projects               |      20 |
| [Publishers and brands](docs/companies.md)       | Publishers and brands connected to cataloged resources        |      16 |

**By platform:** [Web](docs/environments/web.md) **733** · [Desktop](docs/environments/desktop.md) **342** · [Windows](docs/environments/windows.md) **66** · [macOS](docs/environments/macos.md) **32** · [Linux](docs/environments/linux.md) **55** · [Android](docs/environments/android.md) **332** · [iOS](docs/environments/ios.md) **24** · [HarmonyOS](docs/environments/harmonyos.md) **3** · [Cross-platform](docs/environments/cross-platform.md) **200**
<!-- EXPLORE:END -->

The most-mentioned resources and the newest reviews are on [Highlights and recently reviewed](docs/highlights.md).

Coverage spans web, desktop, Android, iOS, Windows, macOS, Linux, and cross-platform work. Topics include grounding, screen understanding, planning, memory, long-horizon workflows, reinforcement learning, data generation, safety, robustness, and evaluation. Environment facets overlap; framework support is not assumed from a model's benchmark results.

## What “verified” means

| State               | What has been checked                                                                                            | What has not been established                                                |
| ------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `curated`           | AI-assisted editorial review against a first-party source snapshot, with name, scope, summary, and taxonomy      | Independent reproduction, universal availability, or endorsement             |
| `metadata_verified` | Bibliographic identity, title, authors, and recorded dates checked against retained arXiv or publication sources | Topic relevance, methodology, findings, or inclusion in the core field       |
| `candidate`         | A normalized URL or identifier was discovered                                                                    | Inclusion, correctness, or availability; excluded from the published catalog |

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

Network discovery and verification are explicit commands; ordinary builds are offline. Changed primary snapshots require another editorial review before publication. Maintenance guide · [Methodology](docs/methodology.md) · [Data dictionary](docs/data-dictionary.md)

## Acknowledgments and reuse

The [source registry](data/sources.json) credits the community collections and surveys used for discovery. Bibliographic records use retained arXiv, publisher, and author sources; publication observations preserve edition-specific titles, authors, and date precision. Selected assets are checked against publisher repositories, documentation, and model/dataset cards. Upstream READMEs, papers, model weights, and datasets are not redistributed here.

Original repository code and annotations use the [MIT license](LICENSE). Linked resources keep their own terms.

To cite the catalog, use CITATION.cff or GitHub's "Cite this repository" button. The data changes with every scan, so pin the exact version you used. Each `v*` tag has a [data release](https://github.com/reacher-z/Awesome-CUA/releases) with versioned downloads built from the tagged commit: the catalog as JSONL, JSON and SQLite, the coverage ledger, topic and profile exports, and their `SHA256SUMS`. Cite the release tag, or record the commit from `git rev-parse HEAD` in your clone, or link files at that commit, such as `https://github.com/reacher-z/Awesome-CUA/blob/<commit>/data/catalog.jsonl`. [Cutting a release](docs/maintenance.md#versioned-data-releases).
