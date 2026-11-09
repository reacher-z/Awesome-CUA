# Scientific workflows

[Home](../../README.md) · [All topics](../topics.md) · [Full arXiv bibliography](../papers.md)

44 source-reviewed resources tagged `science`. Curated metadata; unknown facts are shown as —.

**Contents:** [Benchmarks (3)](#benchmarks) · [Datasets (2)](#datasets) · [Models (6)](#models) · [Agents (1)](#agents) · [Frameworks (3)](#frameworks) · [Tools (3)](#tools) · [Infrastructure (3)](#infrastructure) · [Papers (23)](#papers)

## Benchmarks

| Resource | Environments | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| [MedSPOT](https://github.com/Tajamul21/MedSPOT) | unspecified | [2603.19993](https://arxiv.org/abs/2603.19993) (2026) | — | — | A sequential GUI grounding benchmark covering 10 medical imaging applications. It evaluates target localization across multi-step workflows and provides model evaluation scripts. | [✓ 2026‑11‑09](https://raw.githubusercontent.com/Tajamul21/MedSPOT/HEAD/README.md) |
| [OSWorld-Science](https://github.com/DiscoAILab/OSWorld-Science) | desktop, linux, windows | [2609.39903](https://arxiv.org/abs/2609.39903) (2026) | [146 tasks](https://raw.githubusercontent.com/DiscoAILab/OSWorld-Science/HEAD/README.md) | code CC-BY-4.0 | Benchmark harness that runs computer-use agents on scientific-software tasks in per-domain VMs and scores the resulting application states and deliverables with task-specific executable evaluators. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/DiscoAILab/OSWorld-Science/HEAD/README.md) |
| [ScienceBoard](https://github.com/OS-Copilot/ScienceBoard) | desktop | [2505.19897](https://arxiv.org/abs/2505.19897) (2025) | [169 VM task definitions](https://api.github.com/repos/OS-Copilot/ScienceBoard/git/trees/main?recursive=1) · [6 application families](https://raw.githubusercontent.com/OS-Copilot/ScienceBoard/HEAD/docs/verifier-audit.md) | code MIT | Scientific-workflow tasks for multimodal agents in desktop software such as ChimeraX, KAlgebra, Celestia, Grass GIS and Lean 4, with apps modified to expose state for evaluation. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/OS-Copilot/ScienceBoard/HEAD/README.md) |

## Datasets

All entries in this section: desktop, linux.

| Resource | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [OSWorld-Science task data](https://huggingface.co/datasets/SciAILab/OSWorld-Science-data) | [2609.39903](https://arxiv.org/abs/2609.39903) (2026) | [153 task-definition JSON files](https://huggingface.co/api/datasets/SciAILab/OSWorld-Science-data/revision/9b8de9ad9325c87fbeba90e0676e8d640be70681) · [115 translated task files](https://huggingface.co/api/datasets/SciAILab/OSWorld-Science-data/revision/9b8de9ad9325c87fbeba90e0676e8d640be70681) · [11 QCOW2 VM images](https://huggingface.co/api/datasets/SciAILab/OSWorld-Science-data/revision/9b8de9ad9325c87fbeba90e0676e8d640be70681) · [2,759 files](https://huggingface.co/api/datasets/SciAILab/OSWorld-Science-data/revision/9b8de9ad9325c87fbeba90e0676e8d640be70681) | data cc-by-nc-4.0 | Gated Hub release of OSWorld-Science task definitions, staged inputs, grader references and prepared Ubuntu VM images for computer-use agents working in scientific software. | [✓ 2026‑10‑18](https://huggingface.co/api/datasets/SciAILab/OSWorld-Science-data/revision/9b8de9ad9325c87fbeba90e0676e8d640be70681) |
| [ScienceBoard evaluation trajectories](https://huggingface.co/datasets/OS-Copilot/ScienceBoard-Traj) | [2505.19897](https://arxiv.org/abs/2505.19897) (2025) | — | — | Archives of ScienceBoard agent evaluation runs, separated by agent configuration and screenshot, accessibility-tree or set-of-marks observation mode. | [✓ 2026‑10‑17](https://huggingface.co/api/datasets/OS-Copilot/ScienceBoard-Traj) |

## Models

All entries in this section: desktop.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [ScaleCUA (THUDM) GLM-4.6V-Flash ScienceBoard](https://huggingface.co/extreme1228/ScaleCUA-glm4.6v-scienceboard) | [2607.11185](https://arxiv.org/abs/2607.11185) (2026) | weights other | GLM-4.6V-Flash computer-use agent checkpoint from THUDM's ScaleCUA, trained with online RL from a released SFT start point for ScienceBoard scientific-software tasks. | [✓ 2026‑10‑18](https://huggingface.co/extreme1228/ScaleCUA-glm4.6v-scienceboard/raw/3b089b66c9d0ffd3e56477fce32b31ab5ad56361/README.md) |
| [ScaleCUA (THUDM) GLM-4.6V-Flash ScienceBoard SFT](https://huggingface.co/extreme1228/ScaleCUA-glm4.6v-scienceboard-sft) | [2607.11185](https://arxiv.org/abs/2607.11185) (2026) | weights other | Supervised GLM-4.6V-Flash checkpoint from THUDM's ScaleCUA, released as the start point that online RL initializes from for its ScienceBoard computer-use agent. | [✓ 2026‑10‑18](https://huggingface.co/extreme1228/ScaleCUA-glm4.6v-scienceboard-sft/raw/2bcf77b8a30c161d9ed2e075276877275319d1ad/README.md) |
| [ScaleCUA (THUDM) Qwen3-VL-8B ScienceBoard](https://huggingface.co/extreme1228/ScaleCUA-qwen3-vl-scienceboard) | [2607.11185](https://arxiv.org/abs/2607.11185) (2026) | weights other | Qwen3-VL-8B computer-use agent checkpoint from THUDM's ScaleCUA, trained with online RL for ScienceBoard scientific-software tasks after an SFT start point and served through an OpenAI-compatible endpoint. | [✓ 2026‑10‑18](https://huggingface.co/extreme1228/ScaleCUA-qwen3-vl-scienceboard/raw/13947f05bff0742e09784310b6c68ae39bff67e5/README.md) |
| [ScaleCUA (THUDM) Qwen3-VL-8B ScienceBoard SFT](https://huggingface.co/extreme1228/ScaleCUA-qwen3-vl-scienceboard-sft) | [2607.11185](https://arxiv.org/abs/2607.11185) (2026) | weights other | Supervised Qwen3-VL-8B checkpoint from THUDM's ScaleCUA, released as the start point that online RL initializes from for its ScienceBoard computer-use agent. | [✓ 2026‑10‑18](https://huggingface.co/extreme1228/ScaleCUA-qwen3-vl-scienceboard-sft/raw/48c39bb30e1920e02c440fc256f5bb4e1d44765b/README.md) |
| [ScaleCUA (THUDM) Qwen3.5-9B ScienceBoard](https://huggingface.co/extreme1228/ScaleCUA-qwen3.5-scienceboard) | [2607.11185](https://arxiv.org/abs/2607.11185) (2026) | weights other | Qwen3.5-9B computer-use agent checkpoint from THUDM's ScaleCUA, trained with online RL for ScienceBoard scientific-software tasks after an SFT start point and served through an OpenAI-compatible endpoint. | [✓ 2026‑10‑19](https://huggingface.co/extreme1228/ScaleCUA-qwen3.5-scienceboard/raw/ca2bc686c6d428fde67b114e002dd69e4eeb59b5/README.md) |
| [ScaleCUA (THUDM) Qwen3.5-9B ScienceBoard SFT](https://huggingface.co/extreme1228/ScaleCUA-qwen3.5-scienceboard-sft) | [2607.11185](https://arxiv.org/abs/2607.11185) (2026) | weights other | Supervised Qwen3.5-9B checkpoint from THUDM's ScaleCUA, released as the start point that online RL initializes from for its ScienceBoard computer-use agent. | [✓ 2026‑10‑18](https://huggingface.co/extreme1228/ScaleCUA-qwen3.5-scienceboard-sft/raw/f697d10e7c30cbc7b88d677a81336210b80827d3/README.md) |

## Agents

All entries in this section: desktop.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [GERALLT](https://github.com/DLR-SC/GERALLT) | — | — | An LLM-driven system for testing RCE through its graphical interface, using separate models to control actions, assess problems, and describe icons. | [✓ 2026‑11‑09](https://raw.githubusercontent.com/DLR-SC/GERALLT/HEAD/README.md) |

## Frameworks

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [CODA](https://github.com/OpenIXCLab/CODA) | desktop, linux | [2508.20096](https://arxiv.org/abs/2508.20096) (2025) | — | CODA coordinates a trainable planner ('Cerebrum') with a grounded GUI executor ('Cerebellum') via decoupled reinforcement learning on ScienceBoard. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/OpenIXCLab/CODA/HEAD/README.md) |
| [device-use](https://github.com/labclaw/device-use) | desktop, windows, linux, macos | — | code Apache-2.0 | device-use enables AI agents to operate scientific laboratory instruments through their native desktop GUI software without hardware APIs. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/labclaw/device-use/HEAD/README.md) |
| [WellSet WebMCP](https://github.com/kinhikars/wellset-webmcp) | web | — | code MIT | Shared 96-well laboratory experiment canvas built on WebMCP where scientists and browser agents co-design protocols. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/kinhikars/wellset-webmcp/main/README.md) |

## Tools

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Blender Computer Use Artist](https://github.com/xiaof631/blender-computer-use-artist) | desktop, macos, windows, linux | — | code MIT | Codex computer-use skill for automating Blender 3D modeling, rendering, animation, and visual QA. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/xiaof631/blender-computer-use-artist/HEAD/README.md) |
| [ChimeraX-SessionStates](https://github.com/ShiinaHiiragi/chimerax-states) | desktop, linux | — | — | ChimeraX plugin used by ScienceBoard to expose internal molecular-visualization session state for deterministic benchmark evaluation. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/ShiinaHiiragi/chimerax-states/HEAD/README.md) |
| [mcp-vroid](https://github.com/nhodges/mcp-vroid) | desktop, linux | — | code MIT | Model Context Protocol server that drives VRoid Studio 3D character creation via Linux Wayland GUI automation. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/nhodges/mcp-vroid/main/README.md) |

## Infrastructure

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [grass-gui](https://github.com/ShiinaHiiragi/grass-gui) | desktop, linux | — | — | ScienceBoard's replacement GRASS GIS 8.4 wxPython GUI with an embedded Flask server that loads mapsets and layers, runs GRASS commands and returns layer, region and console state as JSON for task checks. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/ShiinaHiiragi/grass-gui/HEAD/manual.md) |
| [kalgebra-kai](https://github.com/ShiinaHiiragi/kalgebra) | desktop, linux | — | code GPL-2.0 | Modified KAlgebra build from ScienceBoard with a local HTTP server that reports variables and plotted 2D and 3D functions and can switch tabs or add calculations and plots, so the benchmark can check math tasks. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/ShiinaHiiragi/kalgebra/HEAD/manual.md) |
| [ScienceBoard VMware environment](https://huggingface.co/OS-Copilot/ScienceBoard-Env) | linux, desktop | [2505.19897](https://arxiv.org/abs/2505.19897) (2025) | — | A prebuilt Ubuntu virtual-machine archive containing the software environment used for ScienceBoard scientific computer-use tasks. | [✓ 2026‑10‑17](https://huggingface.co/OS-Copilot/ScienceBoard-Env/raw/main/README.md) |

## Papers

| Date | Resource | Environments | Description |
| --- | --- | --- | --- |
| 2026‑11‑02 | [Computer-Use Agents Gain Little Benefit from a World Model When Conditioned on Tutorials](https://arxiv.org/abs/2611.04073) | unspecified | RAG-PolicyJudge selects computer-use actions proposed with task-specific tutorials; the study compares its decisions with and without world-model rollouts. |
| 2026‑11‑02 | [MAGAR: Multimodal Agents for GUI-Based 3D Mechanical Assembly and Minimal Rework](https://arxiv.org/abs/2611.02472) | unspecified | Introduces MAGAR-Bench for GUI-based 3D mechanical assembly decisions and recovery, and MAGAR, a selective correction method for assembly outputs and actions. |
| 2026‑11‑02 | [ScienceCUA: Resource-to-Skill Construction and Execution-Guided Skill Evolution for Scientific Computer Use Agents](https://arxiv.org/abs/2611.03238) | unspecified | Introduces ScienceCUA, which turns scientific software documentation into reusable agent skills and revises them using execution feedback, with two audited evaluation variants. |
| 2026‑10‑03 | [MedImageOSWorld: Benchmarking GUI Agents for Medical Image Consoles](https://arxiv.org/abs/2610.04800) | desktop | Evaluates GUI agents in simulated medical-imaging consoles, separately checking workflow completion and acquisition outcomes against hidden anatomical targets. |
| 2026‑09‑30 | [OSWorld-Science: A Benchmark of Computer Use Agents for Learning and Using Scientific Software](https://arxiv.org/abs/2609.39903) | desktop | Benchmarks computer agents on scientific-software workflows with task-specific checks of application states and generated research artifacts. |
| 2026‑09‑29 | [EngiWorld: What Can Frontier Agents Deliver in Professional Engineering Environments?](https://arxiv.org/abs/2609.37686) | desktop | Introduces professional engineering tasks across software domains, with GUI and CLI access and artifact checks for geometric, physical, and design validity. |
| 2026‑09‑29 | [MatToolBench: Benchmarking Multimodal Agents in Real-World Materials Science Workflows](https://arxiv.org/abs/2609.37053) | desktop, windows | Introduces MatToolBench, a Windows-based materials-science benchmark combining GUI operation, scientific-software scripting, and database queries. Expert-defined subcriteria support partial-credit scoring, while the evaluation examines domain knowledge gaps and cross-tool handoff failures. |
| 2026‑09‑14 | [CADWorld: Computer-Use Benchmark for Long-Horizon Computer-Aided Design](https://arxiv.org/abs/2609.16251) | desktop | CADWorld evaluates screenshot-and-GUI agents on long FreeCAD workflows, from modeling and assembly to manufacturing and simulation. Executable checks inspect saved engineering artifacts for geometry, constraints, construction structure and downstream state. |
| 2026‑08‑11 | [DSAgentBench: Can Agents Automate End-to-End Data-Science Workflows in Real Computer Environments?](https://arxiv.org/abs/2608.10366) | desktop, linux | DSAgentBench evaluates end-to-end data-science workflows spanning analysis, modeling and visualization inside a real desktop environment. Task evaluators check produced analytical and visual artifacts, while the released interface supports screenshot or accessibility observations and GUI actions. |
| 2026‑06‑15 | [LabOSBench: Benchmarking Computer Use Agents for Scientific Instrument Control](https://arxiv.org/abs/2606.16802) | web | LabOSBench evaluates GUI agents on browser-based scientific instrument simulators with configurable tasks and execution-based checks. Its subtask and end-to-end tests examine feedback-driven adjustment and long workflows without controlling physical instruments. |
| 2026‑06‑12 | [Running the Gauntlet: Hard Agentic Tasks](https://arxiv.org/abs/2606.14397) | web | Introduces GauntletBench, a web-based benchmark of vision-intensive tasks in five professional applications for assessing agent perception, 3D reasoning, and generalisation. |
| 2026‑06‑11 | [ComAct: Reframing Professional Software Manipulation via COM-as-Action Paradigm](https://arxiv.org/abs/2606.13239) | desktop, windows | ComAct proposes COM program synthesis as an alternative interface for manipulating professional software and introduces ComCADBench with GUI-based comparison agents. ComActor adds a staged training and correction approach, supported by a Windows-container training platform. |
| 2026‑06‑02 | [MedCUA-Bench: A Screenshot-Only Benchmark for Clinical Computer-Use Agents](https://arxiv.org/abs/2606.03203) | unspecified | MedCUA-Bench evaluates screenshot-only clinical interface workflows using paired intent- and step-level goals. It combines reconstructed medical interfaces with completion and clinical-safety checks, and separately reports results on a real OpenEMR system. |
| 2026‑04‑30 | [Exploring LLM Agent Designs and Interaction Modalities for Scientific Visualization](https://arxiv.org/abs/2604.27996) | unspecified | This study compares specialized, computer-use and coding agents on scientific visualization workflows. It examines GUI, CLI, code and tool-call interaction modes, including how persistent memory changes performance across repeated trials. |
| 2025‑12‑30 | [ProSoftArena: Benchmarking Hierarchical Capabilities of Multimodal Agents in Professional Software Environments](https://arxiv.org/abs/2601.02399) | windows, desktop | ProSoftArena evaluates 436 professional-software tasks across six disciplines and 13 applications in a Windows 11 virtual-machine environment. Its capability hierarchy, execution-based checks, and human-in-the-loop evaluation cover precise GUI operations and multi-software workflows. |
| 2025‑10‑22 | [SheetBrain: A Neuro-Symbolic Agent for Accurate Reasoning over Complex and Large Spreadsheets](https://arxiv.org/abs/2510.19247) | unspecified | Introduces SheetBrain, a spreadsheet question-answering and manipulation agent that uses a Python sandbox and Excel tools, plus the SheetBench benchmark. |
| 2025‑10‑06 | [3Dify: a Framework for Procedural 3D-CG Generation Assisted by LLMs Using MCP and RAG](https://arxiv.org/abs/2510.04536) | unspecified | Introduces 3Dify, a natural-language 3D graphics framework that operates creation tools through MCP and uses a computer-using agent for GUI operations when MCP is unavailable. |
| 2025‑08‑27 | [CODA: Coordinating the Cerebrum and Cerebellum for a Dual-Brain Computer Use Agent with Decoupled Reinforcement Learning](https://arxiv.org/abs/2508.20096) | desktop | CODA combines a generalist planner with a specialist GUI executor and trains application-specific planners through decoupled GRPO. Successful specialist trajectories then support supervised training of a consolidated planner, evaluated across four ScienceBoard applications. |
| 2025‑05‑30 | [VideoCAD: A Dataset and Model for Learning Long-Horizon 3D CAD UI Interactions from Video](https://arxiv.org/abs/2505.24838) | web | Introduces synthetic CAD interaction videos, a model for learning interface actions from video, and evaluation tasks for spatial and long-horizon reasoning. |
| 2025‑05‑26 | [ScienceBoard: Evaluating Multimodal Autonomous Agents in Realistic Scientific Workflows](https://arxiv.org/abs/2505.19897) | desktop | ScienceBoard combines an interactive environment with professional scientific software and 169 human-curated tasks in areas including biochemistry, astronomy, and geoinformatics. It evaluates computer-use agents on visually rich research workflows and analyzes their execution limitations. |
| 2025‑05‑23 | [Automated Testing of the GUI of a Real-Life Engineering Software using Large Language Models](https://arxiv.org/abs/2505.17839) | unspecified | GERALLT uses LLMs to explore the GUI of engineering software and produce a list of confusing or inconsistent interface areas for developers to inspect. |
| 2024‑12‑18 | [CAD-Assistant: Tool-Augmented VLLMs as Generic CAD Task Solvers](https://arxiv.org/abs/2412.13810) | unspecified | CAD-Assistant plans CAD tasks and executes actions through FreeCAD's Python API, using the changing design state to guide later commands. |
| 2024‑07‑15 | [Spider2-V: How Far Are Multimodal Agents From Automating Data Science and Engineering Workflows?](https://arxiv.org/abs/2407.10956) | desktop, web | Benchmarks multimodal agents on data-science and engineering workflows involving enterprise applications, code, and GUI operations in real computer environments. |
