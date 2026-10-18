# iOS

[Home](../../README.md) · [All platforms](../environments.md) · [Research by topic](../topics.md)

22 source-reviewed resources tagged `ios`. Curated metadata, not a performance ranking; unknown facts are shown as —.

**Contents:** [Benchmarks (1)](#benchmarks) · [Datasets (2)](#datasets) · [Models (4)](#models) · [Agents (2)](#agents) · [Frameworks (1)](#frameworks) · [Tools (2)](#tools) · [Infrastructure (1)](#infrastructure) · [Surveys (1)](#surveys) · [Papers (8)](#papers)

## Benchmarks

All entries in this section: ios.

| Resource | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [iOSWorld](https://github.com/ljang0/iOSWorld) | — | [133 tasks](https://raw.githubusercontent.com/ljang0/iOSWorld/HEAD/README.md) · [26 applications](https://raw.githubusercontent.com/ljang0/iOSWorld/HEAD/README.md) | code Apache-2.0 | Native iPhone-simulator benchmark with shared user data, application workflows, agent runners, and rubric-based scoring. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/ljang0/iOSWorld/HEAD/README.md) |

## Datasets

| Resource | Environments | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| [MONDAY](https://github.com/runamu/monday) | android, ios, cross-platform | [2505.12632](https://arxiv.org/abs/2505.12632) (2025) | — | code Apache-2.0 | Cross-platform mobile GUI trajectory dataset derived from instructional videos, with released data-processing helpers and example evaluation code for Android and iOS data. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/runamu/monday/HEAD/README.md) |
| [MONDAY annotations](https://huggingface.co/datasets/runamu/MONDAY) | android, ios | [2505.12632](https://arxiv.org/abs/2505.12632) (2025) | [19,725 video annotation records](https://huggingface.co/datasets/runamu/MONDAY/raw/main/README.md) · [≈ 333,000 detected scenes](https://huggingface.co/datasets/runamu/MONDAY/raw/main/README.md) · [≈ 313,000 identified actions](https://huggingface.co/datasets/runamu/MONDAY/raw/main/README.md) | — | Video-derived mobile navigation annotations that pair scene boundaries and screen or element boxes with action labels for training and evaluating GUI agents. | [✓ 2026‑10‑17](https://huggingface.co/datasets/runamu/MONDAY/raw/main/README.md) |

## Models

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [AutoGLM Phone 9B](https://huggingface.co/zai-org/AutoGLM-Phone-9B) | android, ios | — | weights mit | AutoGLM phone-agent checkpoint for Open-AutoGLM, fine-tuned from GLM-4.1V-9B-Base with about 10.3B BF16 parameters and tagged for Chinese. | [✓ 2026‑10‑16](https://huggingface.co/api/models/zai-org/AutoGLM-Phone-9B) |
| [AutoGLM Phone 9B Multilingual](https://huggingface.co/zai-org/AutoGLM-Phone-9B-Multilingual) | android, ios | — | weights mit | Multilingual variant of the AutoGLM phone-agent checkpoint for Open-AutoGLM, likewise fine-tuned from GLM-4.1V-9B-Base with about 10.3B BF16 parameters. | [✓ 2026‑10‑16](https://huggingface.co/api/models/zai-org/AutoGLM-Phone-9B-Multilingual) |
| [Ferret-UI](https://github.com/apple/ml-ferret) | android, ios | [2404.05719](https://arxiv.org/abs/2404.05719) (2024) | — | Screen understanding research within the Ferret model family. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/apple-aiml-research/ml-ferret/main/ferretui/README.md) |
| [SeeClick checkpoint](https://huggingface.co/cckevinn/SeeClick) | web, desktop, android, ios | [2401.10935](https://arxiv.org/abs/2401.10935) (2024) | — | The released SeeClick visual grounding checkpoint for mapping an interface screenshot and referring instruction to a point or bounding box. | [✓ 2026‑10‑17](https://huggingface.co/api/models/cckevinn/SeeClick) |

## Agents

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) | android, ios | — | code Apache-2.0 | Phone agent model and framework with device interaction tooling. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/zai-org/Open-AutoGLM/HEAD/README.md) |
| [PhysiClaw](https://github.com/physiclaw/PhysiClaw) | ios | — | code MIT | Agent that operates an unmodified iPhone from outside, reading the screen through a camera with OCR and icon detection and tapping or swiping with a serial-driven stylus robot, plus playbooks for known app flows. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/physiclaw/PhysiClaw/HEAD/README.md) |

## Frameworks

All entries in this section: android, ios.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [Mobilerun (formerly Droidrun)](https://github.com/droidrun/mobilerun) | — | code MIT | A framework that combines screenshots and accessibility state with agent tools for mobile-device tasks through command-line and Python interfaces. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/droidrun/mobilerun/HEAD/README.md) |

## Tools

All entries in this section: android, ios.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [Mobile Harness](https://github.com/droidrun/mobile-harness) | — | code MIT | Portable agent instructions and integration tooling for local or cloud phone control through mobilerun-core. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/droidrun/mobile-harness/HEAD/README.md) |
| [Mobile Next MCP](https://github.com/mobile-next/mobile-mcp) | — | code Apache-2.0 | An MCP server exposing mobile accessibility snapshots, screenshots and device interactions across real devices, simulators and emulators. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/mobile-next/mobile-mcp/HEAD/README.md) |

## Infrastructure

All entries in this section: android, ios.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [Appium](https://github.com/appium/appium) | — | code Apache-2.0 | Open-source WebDriver-based automation server for mobile, desktop and IoT apps, extended by per-platform drivers for iOS, Android, macOS and Windows, plugins, and clients in Java, Python, Ruby and C#. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/appium/appium/HEAD/README.md) |

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
