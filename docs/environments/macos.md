# macOS

[Home](../../README.md) · [All platforms](../environments.md) · [Research by topic](../topics.md)

30 source-reviewed resources tagged `macos`. Curated metadata, not a performance ranking; unknown facts are shown as —.

**Contents:** [Benchmarks (3)](#benchmarks) · [Datasets (2)](#datasets) · [Models (4)](#models) · [Agents (2)](#agents) · [Frameworks (1)](#frameworks) · [Tools (2)](#tools) · [Infrastructure (2)](#infrastructure) · [Papers (14)](#papers)

Benchmarks, datasets, models and systems are ordered by *Mentions*: how many other cataloged resources mention them in their reviewed first-party source (connectedness inside this catalog, not quality or benchmark performance; `·` means none). ✓ links the reviewed source snapshot; hover it for the retrieval date. Papers are newest first.

## Benchmarks

| Resource | Mentions | Other platforms | Scale | Description |
| --- | ---: | --- | --- | --- |
| [OSWorld](https://github.com/xlang-ai/OSWorld) · [leaderboard](https://os-world.github.io/) [✓](https://raw.githubusercontent.com/xlang-ai/OSWorld/HEAD/README.md "Source checked 2026-10-16")<br>[2404.07972](https://arxiv.org/abs/2404.07972) (2024) · code Apache‑2.0 | 21 | Desktop, Linux, Windows | [369 task definitions](https://raw.githubusercontent.com/xlang-ai/OSWorld/HEAD/evaluation_examples/test_all.json) | Execution-based evaluation of agents performing tasks in real desktop environments. |
| [ScreenSpot Pro](https://github.com/likaixin2000/ScreenSpot-Pro-GUI-Grounding) · [leaderboard](https://gui-agent.github.io/grounding-leaderboard) [✓](https://raw.githubusercontent.com/likaixin2000/ScreenSpot-Pro-GUI-Grounding/HEAD/readme.md "Source checked 2026-10-16")<br>code MIT | 8 | Desktop, Windows, Linux | [1,581 target annotations](https://huggingface.co/datasets/likaixin/ScreenSpot-Pro/raw/main/README.md) | GUI grounding benchmark focused on professional high-resolution interfaces. |
| [MacAgentBench](https://github.com/JetAstra/MacAgentBench) · [leaderboard](https://jetastra.github.io/MacAgentBench/) [✓](https://raw.githubusercontent.com/JetAstra/MacAgentBench/HEAD/README.md "Source checked 2026-10-16")<br>[2606.22557](https://arxiv.org/abs/2606.22557) (2026) · code MIT | · | Desktop | [676 tasks](https://raw.githubusercontent.com/JetAstra/MacAgentBench/HEAD/README.md) · [25 applications](https://raw.githubusercontent.com/JetAstra/MacAgentBench/HEAD/README.md) | 676 macOS tasks across 25 applications, each run in its own Docker container and scored by deterministic rule-based checks with multiple checkpoints. |

## Datasets

| Resource | Mentions | Other platforms | Scale | Description |
| --- | ---: | --- | --- | --- |
| [ScreenSpot-Pro data](https://huggingface.co/datasets/likaixin/ScreenSpot-Pro) [✓](https://huggingface.co/datasets/likaixin/ScreenSpot-Pro/raw/main/README.md "Source checked 2026-10-16")<br>[2504.07981](https://arxiv.org/abs/2504.07981) (2025) · data mit | 4 | Desktop, Windows, Linux | [1,581 target annotations](https://huggingface.co/datasets/likaixin/ScreenSpot-Pro/raw/main/README.md) | High-resolution professional interface screenshots and target annotations for evaluating instruction-based GUI localization. |
| [GUI-R1 data bundle](https://huggingface.co/datasets/ritzzai/GUI-R1) [✓](https://huggingface.co/datasets/ritzzai/GUI-R1/raw/main/README.md "Source checked 2026-10-17")<br>[2504.10458](https://arxiv.org/abs/2504.10458) (2025) · data mit | 2 | Desktop, Windows, Linux, Android, Web | — | Training and evaluation Parquet bundles accompanying GUI-R1, including GUI grounding and mobile/web action-prediction data. |

## Models

| Resource | Mentions | Other platforms | Description |
| --- | ---: | --- | --- |
| [GUI-R1 checkpoint bundle](https://huggingface.co/ritzzai/GUI-R1) [✓](https://huggingface.co/ritzzai/GUI-R1/raw/main/README.md "Source checked 2026-10-17")<br>[2504.10458](https://arxiv.org/abs/2504.10458) (2025) · weights mit | 1 | Desktop, Windows, Linux, Android, Web | A single Hub release containing GUI-R1 3B and 7B action-model checkpoints trained with reinforcement learning across interface platforms. |
| [CogAgent 9B 20241220](https://huggingface.co/zai-org/cogagent-9b-20241220) [✓](https://huggingface.co/zai-org/cogagent-9b-20241220/raw/main/README.md "Source checked 2026-10-17")<br>weights other | · | Desktop, Windows, Cross‑platform | A bilingual GLM-4V-based execution model that uses screenshots, task instructions and action history to predict GUI operations. |
| [OpenCUA 32B](https://huggingface.co/xlangai/OpenCUA-32B) [✓](https://huggingface.co/xlangai/OpenCUA-32B/raw/main/README.md "Source checked 2026-10-17")<br>[2508.09123](https://arxiv.org/abs/2508.09123) (2025) · weights mit | · | Desktop, Linux, Windows | A Qwen2.5-VL-based computer-use checkpoint that combines screenshot history with planning and grounded executable actions. |
| [OpenCUA 72B](https://huggingface.co/xlangai/OpenCUA-72B) [✓](https://huggingface.co/xlangai/OpenCUA-72B/raw/main/README.md "Source checked 2026-10-17")<br>[2508.09123](https://arxiv.org/abs/2508.09123) (2025) · weights mit | · | Desktop, Linux, Windows | A Qwen2.5-VL-based computer-use checkpoint that combines screenshot history and reflective reasoning to predict executable desktop actions. |

## Agents

| Resource | Mentions | Other platforms | Description |
| --- | ---: | --- | --- |
| [ShowUI-Aloha](https://github.com/showlab/ShowUI-Aloha) [✓](https://raw.githubusercontent.com/showlab/ShowUI-Aloha/HEAD/README.md "Source checked 2026-10-16")<br>[2601.07181](https://arxiv.org/abs/2601.07181) (2026) · code Apache‑2.0 | 1 | Desktop, Windows | Desktop agent that records demonstrations, derives semantic action traces, and uses them to plan and execute related workflows. |
| [PC-Agent (X-PLUG component)](https://github.com/X-PLUG/MobileAgent/tree/main/PC-Agent) [✓](https://raw.githubusercontent.com/X-PLUG/MobileAgent/HEAD/PC-Agent/README.md "Source checked 2026-10-18")<br>[2502.14282](https://arxiv.org/abs/2502.14282) (2025) · code MIT | · | Desktop, Windows | Multi-agent desktop automation component for Windows and macOS, combining active perception, task decomposition and reflection for workflows spanning applications. |

## Frameworks

| Resource | Mentions | Other platforms | Description |
| --- | ---: | --- | --- |
| [Work2Skill](https://github.com/china-qijizhifeng/Work2Skill) [✓](https://raw.githubusercontent.com/china-qijizhifeng/Work2Skill/HEAD/README.md "Source checked 2026-10-16")<br>[2610.12984](https://arxiv.org/abs/2610.12984) (2026) · code MIT | 1 | Desktop, Linux | Collects human GUI demonstrations and inspects multimodal evidence to derive reusable agent workflow skills. |

## Tools

| Resource | Mentions | Other platforms | Description |
| --- | ---: | --- | --- |
| [OculiX (SikuliX continuation)](https://github.com/oculix-org/Oculix) [✓](https://raw.githubusercontent.com/oculix-org/Oculix/HEAD/README.md "Source checked 2026-10-17")<br>code MIT | · | Desktop, Windows, Linux, Android | A maintained continuation of SikuliX that locates on-screen targets with image matching and OCR, drives desktop or Android interfaces, and exposes scripting and optional MCP interfaces. |
| [Sikuli legacy research implementation](https://github.com/sikuli/sikuli) [✓](https://raw.githubusercontent.com/sikuli/sikuli/HEAD/docs/source/index.rst "Source checked 2026-10-17")<br>[Sikuli: Using GUI screenshots for search and automation](https://doi.org/10.1145/1622176.1622213) (2009), [GUI Testing Using Computer Vision](https://doi.org/10.1145/1753326.1753555) (2010) · code MIT | · | Desktop, Linux, Windows | The original Sikuli source distribution combines screenshot targets with a Jython scripting library and IDE for visual GUI automation and testing. |

## Infrastructure

| Resource | Mentions | Other platforms | Description |
| --- | ---: | --- | --- |
| [BrowserOS / BrowserOS neo](https://github.com/browseros-ai/BrowserOS) [✓](https://raw.githubusercontent.com/browseros-ai/BrowserOS/HEAD/README.md "Source checked 2026-10-17")<br>code AGPL‑3.0 | · | Web, Desktop, Windows, Linux | Chromium-based browser implementations for external agent control and built-in assistant workflows, with session visibility and replay facilities. |
| [Lume](https://github.com/trycua/lume) [✓](https://raw.githubusercontent.com/trycua/lume/HEAD/README.md "Source checked 2026-10-16")<br>code MIT | · | Desktop, Linux | Virtual machine management for local computer-use environments. |

## Papers

| Date | Resource | Environments | Description |
| --- | --- | --- | --- |
| 2026‑10‑01 | [AutoGUIWorld: Image Generators as Visual World Models for GUI Agent](https://arxiv.org/abs/2610.01215) | desktop, linux, windows, macos, web | Introduces AutoGUIWorld, which combines task planning and image editing to synthesize action-grounded GUI trajectories without running the depicted software. It filters generated transitions and tests whether training on them improves agents operating real desktop and scientific applications. |
| 2026‑09‑18 | [RecreationWorld: Scalable and Verifiable Environments for Hybrid Computer-Use Agents](https://arxiv.org/abs/2609.22000) | desktop, linux, macos, windows, android, web | RecreationWorld gives hybrid agents running reference applications to explore and recreate using native GUI controls and coding tools. Its multi-platform benchmark checks interaction-dependent behavior with programmatic and visual assertions, while trajectory-training transfer is evaluated separately. |
| 2026‑07‑16 | [Tactile: Giving Computer-Using Agents Hands and Feet](https://arxiv.org/abs/2607.14443) | desktop, macos | Tactile turns accessibility, OCR and visual evidence into explicit desktop targets with executable actions and verification cues. Its execution loop chooses semantic actions or coordinate fallbacks while retaining provenance for replay and diagnosis. |
| 2026‑06‑23 | [Reinforcement Learning for Computer-Use Agents with Autonomous Evaluation](https://arxiv.org/abs/2606.24515) | desktop, macos, windows | The framework uses a vision-language judge’s final-screen assessment as a terminal reward for GUI reinforcement learning. It models evaluator noise and corrects the reward estimator used by PPO across desktop benchmarks. |
| 2026‑06‑21 | [MacAgentBench: Benchmarking AI Agents on Real-World macOS Desktop](https://arxiv.org/abs/2606.22557) | desktop, macos | Introduces macOS tasks spanning GUI and command-line interaction, with deterministic checks and intermediate-progress scoring for application workflows. |
| 2026‑06‑04 | [MacArena: Benchmarking Computer Use Agents on an Online macOS Environment](https://arxiv.org/abs/2606.06560) | desktop, macos | MacArena runs computer-use tasks through Apple’s virtualization framework on Apple Silicon, combining task ports with macOS-native workloads. It distinguishes the ported and native subsets when examining agent performance and cross-platform transfer. |
| 2026‑05‑28 | [Syll: Open-Source Personal Automation with Cross-Surface Execution](https://arxiv.org/abs/2606.07594) | desktop, macos | Syll combines tool calls, shell execution and visual GUI control in a personal-automation runtime. It turns user demonstrations into reusable skills and exposes execution logs, keyframes and approval checkpoints for inspection. |
| 2026‑03‑11 | [CUAAudit: Meta-Evaluation of Vision-Language Models as Auditors of Autonomous Computer-Use Agents](https://arxiv.org/abs/2603.10577) | desktop, macos, windows, linux | CUAAudit examines vision-language models that judge computer-use task completion from an instruction and final environment state. Across macOS, Windows and Linux benchmarks, it measures accuracy, confidence calibration and disagreement between auditors. |
| 2026‑03‑10 | [Video-Based Reward Modeling for Computer-Use Agents](https://arxiv.org/abs/2603.10178) | desktop, linux, macos, windows, android | Builds ExeVR-53k from execution-video, instruction and reward triplets, including negative instructions with step annotations. A reward model uses spatiotemporal token pruning to judge task completion from the instruction and execution keyframes. |
| 2025‑11‑25 | ["Are We Done Yet?": A Vision-Based Judge for Autonomous Task Completion of Computer Use Agents](https://arxiv.org/abs/2511.20067) | desktop, macos | This study tests vision-language models as task-completion judges using screenshots and instructions from 42 built-in macOS applications. It evaluates judgment accuracy on human-labeled tasks and separately studies how judge feedback affects agent task success. |
| 2025‑10‑16 | [GUIrilla: A Scalable Framework for Automated Desktop UI Exploration](https://arxiv.org/abs/2510.16051) | macos, desktop | GUIrilla systematically explores macOS interfaces to collect interaction traces and accessibility metadata for downstream GUI research. It organizes these observations into hierarchical MacApp Trees and describes an accessibility-driven collection library. |
| 2025‑07‑25 | [MMBench-GUI: Hierarchical Multi-Platform Evaluation Framework for GUI Agents](https://arxiv.org/abs/2507.19478) | web, desktop, windows, macos, linux, ios, android, cross-platform | MMBench-GUI evaluates interface understanding, element grounding, task automation, and collaboration across six named desktop, mobile, and web platforms. It introduces the Efficiency-Quality Area metric for examining execution efficiency alongside task quality in online GUI automation. |
| 2025‑06‑04 | [macOSWorld: A Multilingual Interactive Benchmark for GUI Agents](https://arxiv.org/abs/2506.04135) | macos, desktop | macOSWorld provides 202 interactive tasks across 30 applications, with instructions and operating-system interfaces in five languages. It evaluates GUI agents on macOS workflows and includes a separate subset for deception-attack testing. |
| 2024‑04‑11 | [OSWorld: Benchmarking Multimodal Agents for Open-Ended Tasks in Real Computer Environments](https://arxiv.org/abs/2404.07972) | desktop, linux, windows, macos | Introduces a real-computer evaluation environment with execution-based checks for tasks spanning desktop applications and operating-system state. |
