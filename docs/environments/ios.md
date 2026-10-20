# iOS

[Home](../../README.md) · [All platforms](../environments.md) · [Research by topic](../topics.md)

21 source-reviewed resources tagged `ios`. Curated metadata, not a performance ranking; unknown facts are shown as —.

**Contents:** [Benchmarks (1)](#benchmarks) · [Datasets (2)](#datasets) · [Models (4)](#models) · [Agents (1)](#agents) · [Frameworks (1)](#frameworks) · [Tools (2)](#tools) · [Infrastructure (1)](#infrastructure) · [Surveys (1)](#surveys) · [Papers (8)](#papers)

Benchmarks, datasets, models and systems are ordered by *Mentions*: how many other cataloged resources mention them in their reviewed first-party source (connectedness inside this catalog, not quality or benchmark performance; `·` means none). ✓ links the reviewed source snapshot; hover it for the retrieval date. Papers are newest first.

## Benchmarks

| Resource | Mentions | Scale | Description |
| --- | ---: | --- | --- |
| [iOSWorld](https://github.com/ljang0/iOSWorld) [✓](https://raw.githubusercontent.com/ljang0/iOSWorld/HEAD/README.md "Source checked 2026-10-16")<br>code Apache‑2.0 | · | [133 tasks](https://raw.githubusercontent.com/ljang0/iOSWorld/HEAD/README.md) · [26 applications](https://raw.githubusercontent.com/ljang0/iOSWorld/HEAD/README.md) | Native iPhone-simulator benchmark with shared user data, application workflows, agent runners, and rubric-based scoring. |

## Datasets

| Resource | Mentions | Other platforms | Scale | Description |
| --- | ---: | --- | --- | --- |
| [MONDAY annotations](https://huggingface.co/datasets/runamu/MONDAY) [✓](https://huggingface.co/datasets/runamu/MONDAY/raw/main/README.md "Source checked 2026-10-17")<br>[2505.12632](https://arxiv.org/abs/2505.12632) (2025) | 1 | Android | [19,725 video annotation records](https://huggingface.co/datasets/runamu/MONDAY/raw/main/README.md) · [≈ 333,000 detected scenes](https://huggingface.co/datasets/runamu/MONDAY/raw/main/README.md) · [≈ 313,000 identified actions](https://huggingface.co/datasets/runamu/MONDAY/raw/main/README.md) | Video-derived mobile navigation annotations that pair scene boundaries and screen or element boxes with action labels for training and evaluating GUI agents. |
| [MONDAY](https://github.com/runamu/monday) [✓](https://raw.githubusercontent.com/runamu/monday/HEAD/README.md "Source checked 2026-10-18")<br>[2505.12632](https://arxiv.org/abs/2505.12632) (2025) · code Apache‑2.0 | · | Android, Cross‑platform | — | Cross-platform mobile GUI trajectory dataset derived from instructional videos, with released data-processing helpers and example evaluation code for Android and iOS data. |

## Models

| Resource | Mentions | Other platforms | Description |
| --- | ---: | --- | --- |
| [AutoGLM Phone 9B Multilingual](https://huggingface.co/zai-org/AutoGLM-Phone-9B-Multilingual) [✓](https://huggingface.co/api/models/zai-org/AutoGLM-Phone-9B-Multilingual "Source checked 2026-10-16")<br>weights mit | 2 | Android | Multilingual variant of the AutoGLM phone-agent checkpoint for Open-AutoGLM, likewise fine-tuned from GLM-4.1V-9B-Base with about 10.3B BF16 parameters. |
| [AutoGLM Phone 9B](https://huggingface.co/zai-org/AutoGLM-Phone-9B) [✓](https://huggingface.co/api/models/zai-org/AutoGLM-Phone-9B "Source checked 2026-10-16")<br>weights mit | 1 | Android | AutoGLM phone-agent checkpoint for Open-AutoGLM, fine-tuned from GLM-4.1V-9B-Base with about 10.3B BF16 parameters and tagged for Chinese. |
| [Ferret-UI](https://github.com/apple/ml-ferret) [✓](https://raw.githubusercontent.com/apple-aiml-research/ml-ferret/main/ferretui/README.md "Source checked 2026-10-16")<br>[2404.05719](https://arxiv.org/abs/2404.05719) (2024) | · | Android | Screen understanding research within the Ferret model family. |
| [SeeClick checkpoint](https://huggingface.co/cckevinn/SeeClick) [✓](https://huggingface.co/api/models/cckevinn/SeeClick "Source checked 2026-10-17")<br>[2401.10935](https://arxiv.org/abs/2401.10935) (2024) | · | Web, Desktop, Android | The released SeeClick visual grounding checkpoint for mapping an interface screenshot and referring instruction to a point or bounding box. |

## Agents

| Resource | Mentions | Other platforms | Description |
| --- | ---: | --- | --- |
| [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) [✓](https://raw.githubusercontent.com/zai-org/Open-AutoGLM/HEAD/README.md "Source checked 2026-10-16")<br>code Apache‑2.0 | 1 | Android | Phone agent model and framework with device interaction tooling. |

## Frameworks

| Resource | Mentions | Other platforms | Description |
| --- | ---: | --- | --- |
| [Mobilerun (formerly Droidrun)](https://github.com/droidrun/mobilerun) [✓](https://raw.githubusercontent.com/droidrun/mobilerun/HEAD/README.md "Source checked 2026-10-17")<br>code MIT | · | Android | A framework that combines screenshots and accessibility state with agent tools for mobile-device tasks through command-line and Python interfaces. |

## Tools

| Resource | Mentions | Other platforms | Description |
| --- | ---: | --- | --- |
| [Mobile Harness](https://github.com/droidrun/mobile-harness) [✓](https://raw.githubusercontent.com/droidrun/mobile-harness/HEAD/README.md "Source checked 2026-10-16")<br>code MIT | 1 | Android | Portable agent instructions and integration tooling for local or cloud phone control through mobilerun-core. |
| [Mobile Next MCP](https://github.com/mobile-next/mobile-mcp) [✓](https://raw.githubusercontent.com/mobile-next/mobile-mcp/HEAD/README.md "Source checked 2026-10-17")<br>code Apache‑2.0 | · | Android | An MCP server exposing mobile accessibility snapshots, screenshots and device interactions across real devices, simulators and emulators. |

## Infrastructure

| Resource | Mentions | Other platforms | Description |
| --- | ---: | --- | --- |
| [Appium](https://github.com/appium/appium) [✓](https://raw.githubusercontent.com/appium/appium/HEAD/README.md "Source checked 2026-10-16")<br>code Apache‑2.0 | · | Android | Open-source WebDriver-based automation server for mobile, desktop and IoT apps, extended by per-platform drivers for iOS, Android, macOS and Windows, plugins, and clients in Java, Python, Ruby and C#. |

## Surveys

All entries in this section: android, ios.

| Date | Resource | Description |
| --- | --- | --- |
| 2025‑04‑28 | [LLM-Powered GUI Agents in Phone Automation: Surveying Progress and Prospects](https://arxiv.org/abs/2504.19838) | Reviews LLM-driven phone GUI agents with a taxonomy of agent frameworks, prompt- and training-based modeling, datasets, and benchmarks. |

## Papers

| Date | Resource | Environments | Description |
| --- | --- | --- | --- |
| 2026‑07‑14 | [KnowAct-GUIClaw: Know Deeply, Act Perfectly, Personal GUI Assistant with Self-Evolving Memory and Skill](https://arxiv.org/abs/2607.12625) | desktop, android, ios, harmonyos, windows | KnowAct-GUIClaw combines a host planner with pluggable GUI subagents, attributable experience memory and an evolving skill library. It uses user profiles and feedback for task decomposition and evaluates transfer across Android, iOS, HarmonyOS and Windows. |
| 2026‑06‑08 | [iOSWorld: A Benchmark for Personally Intelligent Phone Agents](https://arxiv.org/abs/2606.09764) | ios | Introduces a native iOS simulator benchmark with persistent user data, multi-app tasks, and personalization-dependent phone workflows. |
| 2026‑04‑13 | [ClawGUI: A Unified Framework for Training, Evaluating, and Deploying GUI Agents](https://arxiv.org/abs/2604.11784) | android, harmonyos, ios | Presents ClawGUI, a shared harness for GUI-agent reinforcement learning, benchmark evaluation and deployment on mobile devices. It combines parallel virtual and physical environments, process rewards, and hybrid CLI-GUI execution with persistent memory. |
| 2025‑07‑25 | [MMBench-GUI: Hierarchical Multi-Platform Evaluation Framework for GUI Agents](https://arxiv.org/abs/2507.19478) | web, desktop, windows, macos, linux, ios, android, cross-platform | MMBench-GUI evaluates interface understanding, element grounding, task automation, and collaboration across six named desktop, mobile, and web platforms. It introduces the Efficiency-Quality Area metric for examining execution efficiency alongside task quality in online GUI automation. |
| 2024‑10‑24 | [Ferret-UI 2: Mastering Universal User Interface Understanding Across Platforms](https://arxiv.org/abs/2410.18967) | ios, android, web, cross-platform | Extends Ferret-UI across device platforms with adaptive visual scaling and synthetic data for referring, grounding, and user-centered UI tasks. |
| 2024‑03‑08 | [UI Semantic Group Detection: Grouping UI Elements with Similar Semantics in Mobile Graphical User Interface](https://arxiv.org/abs/2403.04984) | android, ios | UISCGD detects semantic groups of adjacent text and non-text UI elements. It learns from Android and iOS screenshots to support interface retrieval, UI-to-code structure and screen-reader accessibility. |
| 2023‑11‑13 | [GPT-4V in Wonderland: Large Multimodal Models for Zero-Shot Smartphone GUI Navigation](https://arxiv.org/abs/2311.07562) | ios, android | Studies MM-Navigator, a multimodal agent that interprets smartphone screenshots and predicts localized actions without task-specific training. |
| 2021‑01‑13 | [Screen Recognition: Creating Accessibility Metadata for Mobile Applications from Pixels](https://arxiv.org/abs/2101.04893) | ios | Infers UI elements and accessibility metadata from mobile screenshots to support screen-reader interaction with iOS applications. |
