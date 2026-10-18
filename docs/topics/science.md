# Scientific workflows

[Home](../../README.md) · [All topics](../topics.md) · [Full arXiv bibliography](../papers.md)

19 source-reviewed resources tagged `science`. Curated metadata, not a performance ranking; unknown facts are shown as —.

**Contents:** [Benchmarks (1)](#benchmarks) · [Datasets (1)](#datasets) · [Agents (1)](#agents) · [Infrastructure (1)](#infrastructure) · [Papers (15)](#papers)

## Benchmarks

All entries in this section: desktop.

| Resource | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [ScienceBoard](https://github.com/OS-Copilot/ScienceBoard) | [2505.19897](https://arxiv.org/abs/2505.19897) (2025) | [169 VM task definitions](https://api.github.com/repos/OS-Copilot/ScienceBoard/git/trees/main?recursive=1) · [6 application families](https://raw.githubusercontent.com/OS-Copilot/ScienceBoard/HEAD/docs/verifier-audit.md) | code MIT | Scientific-workflow tasks for multimodal agents in desktop software such as ChimeraX, KAlgebra, Celestia, Grass GIS and Lean 4, with apps modified to expose state for evaluation. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/OS-Copilot/ScienceBoard/HEAD/README.md) |

## Datasets

All entries in this section: desktop, linux.

| Resource | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [ScienceBoard evaluation trajectories](https://huggingface.co/datasets/OS-Copilot/ScienceBoard-Traj) | [2505.19897](https://arxiv.org/abs/2505.19897) (2025) | — | — | Archives of ScienceBoard agent evaluation runs, separated by agent configuration and screenshot, accessibility-tree or set-of-marks observation mode. | [✓ 2026‑10‑17](https://huggingface.co/api/datasets/OS-Copilot/ScienceBoard-Traj) |

## Agents

All entries in this section: desktop, linux.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [CODA](https://github.com/OpenIXCLab/CODA) | [2508.20096](https://arxiv.org/abs/2508.20096) (2025) | — | Inference code for CODA, which pairs a CODA-PLANNER-TARS-32B planner served with vLLM and a UI-TARS-1.5-7B executor on ScienceBoard scientific-software tasks in Ubuntu virtual machines. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/OpenIXCLab/CODA/HEAD/README.md) |

## Infrastructure

All entries in this section: linux, desktop.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [ScienceBoard VMware environment](https://huggingface.co/OS-Copilot/ScienceBoard-Env) | [2505.19897](https://arxiv.org/abs/2505.19897) (2025) | — | A prebuilt Ubuntu virtual-machine archive containing the software environment used for ScienceBoard scientific computer-use tasks. | [✓ 2026‑10‑17](https://huggingface.co/OS-Copilot/ScienceBoard-Env/raw/main/README.md) |

## Papers

| Date | Resource | Environments | Description |
| --- | --- | --- | --- |
| 2026‑10‑03 | [MedImageOSWorld: Benchmarking GUI Agents for Medical Image Consoles](https://arxiv.org/abs/2610.04800) | desktop | Evaluates GUI agents in simulated medical-imaging consoles, separately checking workflow completion and acquisition outcomes against hidden anatomical targets. |
| 2026‑09‑30 | [OSWorld-Science: A Benchmark of Computer Use Agents for Learning and Using Scientific Software](https://arxiv.org/abs/2609.39903) | desktop | Benchmarks computer agents on scientific-software workflows with task-specific checks of application states and generated research artifacts. |
| 2026‑09‑29 | [EngiWorld: What Can Frontier Agents Deliver in Professional Engineering Environments?](https://arxiv.org/abs/2609.37686) | desktop | Introduces professional engineering tasks across software domains, with GUI and CLI access and artifact checks for geometric, physical, and design validity. |
| 2026‑09‑29 | [MatToolBench: Benchmarking Multimodal Agents in Real-World Materials Science Workflows](https://arxiv.org/abs/2609.37053) | desktop, windows | Introduces MatToolBench, a Windows-based materials-science benchmark combining GUI operation, scientific-software scripting, and database queries. Expert-defined subcriteria support partial-credit scoring, while the evaluation examines domain knowledge gaps and cross-tool handoff failures. |
| 2026‑09‑14 | [CADWorld: Computer-Use Benchmark for Long-Horizon Computer-Aided Design](https://arxiv.org/abs/2609.16251) | desktop | CADWorld evaluates screenshot-and-GUI agents on long FreeCAD workflows, from modeling and assembly to manufacturing and simulation. Executable checks inspect saved engineering artifacts for geometry, constraints, construction structure and downstream state. |
| 2026‑08‑11 | [DSAgentBench: Can Agents Automate End-to-End Data-Science Workflows in Real Computer Environments?](https://arxiv.org/abs/2608.10366) | desktop, linux | DSAgentBench evaluates end-to-end data-science workflows spanning analysis, modeling and visualization inside a real desktop environment. Task evaluators check produced analytical and visual artifacts, while the released interface supports screenshot or accessibility observations and GUI actions. |
| 2026‑06‑15 | [LabOSBench: Benchmarking Computer Use Agents for Scientific Instrument Control](https://arxiv.org/abs/2606.16802) | web | LabOSBench evaluates GUI agents on browser-based scientific instrument simulators with configurable tasks and execution-based checks. Its subtask and end-to-end tests examine feedback-driven adjustment and long workflows without controlling physical instruments. |
| 2026‑06‑11 | [ComAct: Reframing Professional Software Manipulation via COM-as-Action Paradigm](https://arxiv.org/abs/2606.13239) | desktop, windows | ComAct proposes COM program synthesis as an alternative interface for manipulating professional software and introduces ComCADBench with GUI-based comparison agents. ComActor adds a staged training and correction approach, supported by a Windows-container training platform. |
| 2026‑06‑02 | [MedCUA-Bench: A Screenshot-Only Benchmark for Clinical Computer-Use Agents](https://arxiv.org/abs/2606.03203) | unspecified | MedCUA-Bench evaluates screenshot-only clinical interface workflows using paired intent- and step-level goals. It combines reconstructed medical interfaces with completion and clinical-safety checks, and separately reports results on a real OpenEMR system. |
| 2026‑04‑30 | [Exploring LLM Agent Designs and Interaction Modalities for Scientific Visualization](https://arxiv.org/abs/2604.27996) | unspecified | This study compares specialized, computer-use and coding agents on scientific visualization workflows. It examines GUI, CLI, code and tool-call interaction modes, including how persistent memory changes performance across repeated trials. |
| 2025‑12‑30 | [ProSoftArena: Benchmarking Hierarchical Capabilities of Multimodal Agents in Professional Software Environments](https://arxiv.org/abs/2601.02399) | windows, desktop | ProSoftArena evaluates 436 professional-software tasks across six disciplines and 13 applications in a Windows 11 virtual-machine environment. Its capability hierarchy, execution-based checks, and human-in-the-loop evaluation cover precise GUI operations and multi-software workflows. |
| 2025‑08‑27 | [CODA: Coordinating the Cerebrum and Cerebellum for a Dual-Brain Computer Use Agent with Decoupled Reinforcement Learning](https://arxiv.org/abs/2508.20096) | desktop | CODA combines a generalist planner with a specialist GUI executor and trains application-specific planners through decoupled GRPO. Successful specialist trajectories then support supervised training of a consolidated planner, evaluated across four ScienceBoard applications. |
| 2025‑05‑30 | [VideoCAD: A Dataset and Model for Learning Long-Horizon 3D CAD UI Interactions from Video](https://arxiv.org/abs/2505.24838) | web | Introduces synthetic CAD interaction videos, a model for learning interface actions from video, and evaluation tasks for spatial and long-horizon reasoning. |
| 2025‑05‑26 | [ScienceBoard: Evaluating Multimodal Autonomous Agents in Realistic Scientific Workflows](https://arxiv.org/abs/2505.19897) | desktop | ScienceBoard combines an interactive environment with professional scientific software and 169 human-curated tasks in areas including biochemistry, astronomy, and geoinformatics. It evaluates computer-use agents on visually rich research workflows and analyzes their execution limitations. |
| 2024‑07‑15 | [Spider2-V: How Far Are Multimodal Agents From Automating Data Science and Engineering Workflows?](https://arxiv.org/abs/2407.10956) | desktop, web | Benchmarks multimodal agents on data-science and engineering workflows involving enterprise applications, code, and GUI operations in real computer environments. |
