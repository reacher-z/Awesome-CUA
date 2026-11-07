# Recording

[Home](../../README.md) · [All topics](../topics.md) · [Full arXiv bibliography](../papers.md)

52 source-reviewed resources tagged `recording`. Curated metadata; unknown facts are shown as —.

**Contents:** [Datasets (2)](#datasets) · [Agents (3)](#agents) · [Frameworks (11)](#frameworks) · [Tools (10)](#tools) · [Infrastructure (2)](#infrastructure) · [Products (1)](#products) · [Surveys (1)](#surveys) · [Papers (22)](#papers)

## Datasets

| Resource | Environments | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| [PSAI Computer Use Dataset](https://github.com/anaishowland/computeruse-data-psai) | cross-platform, desktop, web | — | — | code MIT | PSAI Computer Use Dataset provides 3,167 human-computer interaction trajectories with synchronized screen video, input events, and DOM/AX snapshots. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/anaishowland/computeruse-data-psai/HEAD/README.md) |
| [WorkDemo-350](https://huggingface.co/datasets/yuqi777/WorkDemo-350) | desktop | [2610.12984](https://arxiv.org/abs/2610.12984) (2026) | [350 demonstrations](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) · [8,388 evidence images](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) · [11,951 action records](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) | data cc-by-4.0 | Desktop demonstrations with task descriptions, videos, input logs, and action-linked screenshot evidence for studying reusable agent skills. | [✓ 2026‑10‑16](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) |

## Agents

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Apprentice](https://github.com/bluzername/apprentice) | desktop, macos | — | code Apache-2.0 | Apprentice is a local-first macOS agent that observes repeated user routines across allowlisted apps and replays them with click-by-click approval. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/bluzername/apprentice/HEAD/README.md) |
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | desktop | — | code MIT | Tools for learning and automating workflows from desktop demonstrations. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/OpenAdaptAI/OpenAdapt/HEAD/README.md) |
| [ShowUI-Aloha](https://github.com/showlab/ShowUI-Aloha) | desktop, windows, macos | [2601.07181](https://arxiv.org/abs/2601.07181) (2026) | code Apache-2.0 | Desktop agent that records demonstrations, derives semantic action traces, and uses them to plan and execute related workflows. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/showlab/ShowUI-Aloha/HEAD/README.md) |

## Frameworks

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [19ska Computer-Use Automation](https://github.com/19ska/computer-use-automation) | web, desktop | — | — | Uses an LLM to discover a UI workflow once and compiles the trajectory into a deterministic replay script. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/19ska/computer-use-automation/main/README.md) |
| [Agent Hands](https://github.com/Ashishkosana/agent-hands) | web, desktop | — | code MIT | Computer-use automation infrastructure for legacy financial software that compiles LLM-discovered UI flows into deterministic replays. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/Ashishkosana/agent-hands/main/README.md) |
| [AgentStudio](https://github.com/skyworkai/agent-studio) | desktop, linux | [2403.17918](https://arxiv.org/abs/2403.17918) (2024) | code AGPL-3.0 | Toolkit and Ubuntu-based environment for building and evaluating generalist computer-use agents through GUI and API interaction. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/skyworkai/agent-studio/HEAD/README.md) |
| [bgivenb Typed UI Capabilities](https://github.com/bgivenb/computer-use-automation) | web, desktop | — | code MIT | Model-guided UI workflow discovery framework with signed human review and deterministic replay. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/bgivenb/computer-use-automation/main/README.md) |
| [Operant](https://github.com/AlpharomeroJL/operant) | cross-platform, desktop, macos, windows, linux | — | code Apache-2.0 | Local-first desktop agent runtime that compiles exploratory AI trajectories into deterministic, invariant-gated skills. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/AlpharomeroJL/operant/HEAD/README.md) |
| [Protean](https://github.com/AIBrain-Mnemis/Protean) | cross-platform, desktop, web | — | code MIT | Protean turns everyday human desktop and browser demonstrations into reusable, adaptive agent skills. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/AIBrain-Mnemis/Protean/HEAD/README.md) |
| [Replay AI](https://github.com/bryansbtian/replay-ai) | cross-platform, desktop, web | — | — | Discovers UI workflows once using a local LLM and compiles the successful trajectory into a deterministic replay script. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/bryansbtian/replay-ai/main/README.md) |
| [rote](https://github.com/bhuvanb3110/rote) | web, desktop | — | — | Record-once, replay-many computer-use automation framework for legacy banking and back-office web applications lacking APIs. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/bhuvanb3110/rote/HEAD/README.md) |
| [SeleniumBase](https://github.com/seleniumbase/SeleniumBase) | web | — | — | Python browser automation framework for web crawling, end-to-end testing and scraping, with a recorder that generates tests and stealth options. | [✓ 2026‑11‑06](https://raw.githubusercontent.com/seleniumbase/SeleniumBase/b806f54ab0c998c90654b59a817d959f7ff7920c/README.md) |
| [TraceFact](https://github.com/Alex0AI/tracefact) | cross-platform, desktop, web | — | code Apache-2.0 | Evidence-first reliability reporting and deterministic replay framework for coding and browser agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/Alex0AI/tracefact/main/README.md) |
| [Work2Skill](https://github.com/china-qijizhifeng/Work2Skill) | desktop, macos, linux | [2610.12984](https://arxiv.org/abs/2610.12984) (2026) | code MIT | Collects human GUI demonstrations and inspects multimodal evidence to derive reusable agent workflow skills. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/china-qijizhifeng/Work2Skill/HEAD/README.md) |

## Tools

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Activity Recorder](https://github.com/anikasomaia/local-activity-recorder) | desktop, windows | — | — | Windows tray utility that records primary-display screenshots, keyboard key codes and mouse events as local JPEG and JSON files for training-data collection. | [✓ 2026‑10‑20](https://raw.githubusercontent.com/anikasomaia/local-activity-recorder/967cea087bf6496b3b82743fb96770fa29f8e203/README.md) |
| [Apache Maka](https://github.com/apache/maka) | desktop, macos | — | code Apache-2.0 | Apache Maka is an agent workspace for macOS that records verifiable execution traces across browser, terminal, and GUI actions. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/apache/maka/HEAD/README.md) |
| [Browser Use WebUI](https://github.com/browser-use/web-ui) | web | — | code MIT | A Gradio interface for configuring and running Browser Use agents, including persistent browser sessions and interaction recordings. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/browser-use/web-ui/HEAD/README.md) |
| [Captr for macOS](https://github.com/anaishowland/Captr_MacOS) | desktop, macos | — | code MIT | Captr for macOS records synchronized screen video, keyboard/mouse input, DOM snapshots, and macOS accessibility trees for CUA datasets. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/anaishowland/Captr_MacOS/HEAD/README.md) |
| [Captr for Windows](https://github.com/anaishowland/Captr_Windows) | desktop, windows | — | code MIT | Captr for Windows records synchronized screen video, mouse/keyboard events, DOM snapshots, and Windows accessibility trees for CUA datasets. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/anaishowland/Captr_Windows/HEAD/README.md) |
| [clickcast](https://github.com/AlexKay28/clickcast) | web | — | code MIT | Playwright browser automation, screenshot, and GIF/MP4/WebP session-recording toolkit and MCP server for AI agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/AlexKay28/clickcast/HEAD/README.md) |
| [Computer Use Data Collection](https://github.com/bobcoi03/computeruse-data-collection) | cross-platform, desktop, windows, macos, linux | — | code MIT | Computer Use Data Collection is a desktop recorder that captures synchronized screenshots, mouse clicks, and keystrokes for training CUA models. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/bobcoi03/computeruse-data-collection/HEAD/README.md) |
| [Libretto](https://github.com/cashew-labs/libretto) | web | — | code MIT | Libretto is a toolkit that gives coding agents a live browser and CLI to inspect pages, record user actions, build scripts, and debug web integrations. | [✓ 2026‑11‑06](https://raw.githubusercontent.com/cashew-labs/libretto/41ab782ccea765d7a9a3c9b56b1b2586723962e3/README.md) |
| [MergeProof](https://github.com/bukacdan/MergeProof) | web | — | code MIT | Installable Agent Skill that records live browser verification demos and attaches them to pull requests. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/bukacdan/MergeProof/main/README.md) |
| [Product Demo Video Skill](https://github.com/Afnanksalal/product-demo-video-skill) | web, desktop | — | code MIT | Codex and Claude Agent Skill that drives live web products in a browser to record truth-linked walkthrough demo videos. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/Afnanksalal/product-demo-video-skill/main/README.md) |

## Infrastructure

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [BrowserOS / BrowserOS neo](https://github.com/browseros-ai/BrowserOS) | web, desktop, windows, macos, linux | — | code AGPL-3.0 | Chromium-based browser implementations for external agent control and built-in assistant workflows, with session visibility and replay facilities. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/browseros-ai/BrowserOS/HEAD/README.md) |
| [Neo Lab](https://github.com/belarusian/neo-lab) | desktop, macos | — | code MIT | Neo Lab is a macOS computer-use sandbox for recording demonstrations, replaying skills, and testing GUI automation plans. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/belarusian/neo-lab/HEAD/README.md) |

## Products

All entries in this section: desktop, web.

| Resource | Publisher | Description | Evidence |
| --- | --- | --- | --- |
| [Scribe](https://scribehow.com/) | — | Workflow recording and documentation product adjacent to agent data collection. | [✓ 2026‑10‑16](https://scribehow.com/) |

## Surveys

All entries in this section: unspecified.

| Date | Resource | Description |
| --- | --- | --- |
| 2023‑10‑20 | [Vision-Based Mobile App GUI Testing: A Survey](https://arxiv.org/abs/2310.13518) | Surveys vision-based mobile app GUI testing across test generation, record-and-replay and testing frameworks, drawing on 271 papers including 92 vision-based studies. |

## Papers

| Date | Resource | Environments | Description |
| --- | --- | --- | --- |
| 2026‑10‑20 | [InterWebCoder: Learning Interactive Webpage Generation from Executable Tests via Reinforcement Learning](https://arxiv.org/abs/2610.28610) | web | InterWebCoder trains models to generate interactive webpage code using recorded interactions, executable tests and repair feedback, an adjacent web interface task. |
| 2026‑10‑09 | [Work2Skill: Capturing Human GUI Experience for Reusable Agent Skill Induction](https://arxiv.org/abs/2610.12984) | desktop | Aligns human screen recordings, input events, and accessibility information to derive reusable workflow skills from desktop demonstrations. |
| 2026‑09‑02 | [OmegaUse-SOP: SOP Engineering for Professional Computer Use from Human Demonstrations](https://arxiv.org/abs/2609.02149) | unspecified | OmegaUse-SOP converts expert GUI demonstrations into configurable procedures and refines them with domain rules and human input. It records, abstracts, grounds and verifies live execution, with a case study of photovoltaic simulation workflows in PVsyst 7.2. |
| 2026‑08‑20 | [Inducing Task Models from Computer-Use Traces](https://arxiv.org/abs/2608.20319) | unspecified | Task Model Induction disentangles concurrent activities in screenshot and mouse/keyboard traces, then constructs hierarchical goals and procedural control flow for each task. Evaluation tests reconstruction of observed execution and reuse of derived skills on held-out tasks. |
| 2026‑08‑14 | [LegacyWorld: Atomicity-Aware Evaluation of GUI Agents for Legacy Workflows](https://arxiv.org/abs/2608.14131) | desktop, windows | LegacyWorld evaluates Windows GUI workflows under an atomicity criterion: finish correctly or fail without persistent unintended changes. It compares expert prompts with prompts derived from recorded golden paths and separates useful completion, safe failure and non-atomic side effects. |
| 2026‑08‑06 | [Activity Frames: Deterministic Screen-Activity Compilation for Agent Memory and Replay](https://arxiv.org/abs/2608.05784) | unspecified | Introduces Activity Frames, a deterministic pipeline that turns captured screen activity into typed episodes for computer-use agent memory and routine replay. |
| 2026‑06‑17 | [HANSEL: Extracting Breadcrumbs from Web Agent Trajectories for Interactive Verification](https://arxiv.org/abs/2606.18671) | web | HANSEL extracts evidence pages and snippets from browser-agent traces and preserves relevant page state in interactive verification views. It flags untraceable answers and evaluates evidence selection and human verification effort separately. |
| 2026‑06‑16 | [PreAct: Computer-Using Agents that Get Faster on Repeated Tasks](https://arxiv.org/abs/2606.17929) | cross-platform | PreAct compiles successful screen-interaction runs into guarded state-machine programs for repeated tasks. It validates programs from clean states before storage and returns control to the agent when replayed screen expectations fail, with tests across mobile, desktop and web. |
| 2026‑06‑02 | [Demo2Tutorial: From Human Experience to Multimodal Software Tutorials](https://arxiv.org/abs/2606.03951) | unspecified | Introduces Demo2Tutorial, which turns recorded software interactions into multimodal tutorials with task graphs and reports benefits for GUI-agent planning. |
| 2026‑05‑28 | [Syll: Open-Source Personal Automation with Cross-Surface Execution](https://arxiv.org/abs/2606.07594) | desktop, macos | Syll combines tool calls, shell execution and visual GUI control in a personal-automation runtime. It turns user demonstrations into reusable skills and exposes execution logs, keyframes and approval checkpoints for inspection. |
| 2026‑05‑19 | [CutVerse: A Compositional GUI Agents Benchmark for Media Post-Production Editing](https://arxiv.org/abs/2605.19484) | unspecified | Cutverse benchmarks GUI agents on long editing workflows across professional media applications and parses recordings and input logs into grounded action trajectories. |
| 2026‑05‑14 | [Known By Their Actions: Fingerprinting LLM Browser Agents via UI Traces](https://arxiv.org/abs/2605.14786) | web | A study shows that websites can infer the model behind a browser agent from passively recorded UI actions and timing traces across web tasks. |
| 2026‑05‑04 | [cotomi Act: Learning to Automate Work by Watching You](https://arxiv.org/abs/2605.03231) | web | cotomi Act is a browser agent that executes multi-step tasks and turns observed user browsing into persistent knowledge shared with users. |
| 2026‑04‑15 | [AppAgent-Claw: CLI Is All You Need for GUI Automation](https://arxiv.org/abs/2606.05171) | unspecified | Introduces AppAgent-Claw, which records demonstrated GUI workflows as reusable OpenClaw skills, locates visual targets during replay and checks intended on-screen effects. |
| 2026‑01‑12 | [ShowUI-Aloha: Human-Taught GUI Agent](https://arxiv.org/abs/2601.07181) | desktop | Transforms human screen recordings and input events into annotated demonstrations used by planning and execution components for GUI tasks. |
| 2025‑10‑16 | [GUIrilla: A Scalable Framework for Automated Desktop UI Exploration](https://arxiv.org/abs/2510.16051) | macos, desktop | GUIrilla systematically explores macOS interfaces to collect interaction traces and accessibility metadata for downstream GUI research. It organizes these observations into hierarchical MacApp Trees and describes an accessibility-driven collection library. |
| 2025‑04‑12 | [Explorer: Robust Collection of Interactable GUI Elements](https://arxiv.org/abs/2504.09352) | android, web | Explorer collects interactable GUI elements from a live target application and records user sessions for application-specific model training. It links repeated interface states into a navigation map that supports path planning and voice-directed interaction. |
| 2024‑12‑23 | [PC Agent: While You Sleep, AI Works -- A Cognitive Journey into Digital World](https://arxiv.org/abs/2412.17589) | desktop | Combines PC Tracker interaction capture, completion of action and reasoning annotations, and planning and grounding agents for desktop workflows. |
| 2018 | [Rousillon: Scraping Distributed Hierarchical Web Data](https://doi.org/10.1145/3242587.3242661) | web | Introduces Rousillon, which generalizes a demonstration of collecting one hierarchical data row into a browser-automation program that traverses related pages. The paper develops relation-selection and generalization methods and evaluates users building such scripts. |
| 2017 | [SUGILITE: Creating Multimodal Smartphone Automation by Demonstration](https://doi.org/10.1145/3025453.3025483) | android | Introduces SUGILITE, which combines spoken instructions, demonstrated Android actions, and UI hierarchies to generate reusable automation scripts. Its interface includes context checking and repairs for unfamiliar situations and changing app interfaces. |
| 2016‑11 | [Ringer: Web Automation by Demonstration](https://doi.org/10.1145/2983990.2984020) | web | Introduces Ringer, which converts demonstrated webpage interactions into scripts combining actions, target selectors, and waiting conditions. It evaluates replay robustness on tasks recorded from real websites. |
| 2007 | [Koala: Capture, Share, Automate, Personalize Business Processes on the Web](https://doi.org/10.1145/1240624.1240767) | web | Introduces Koala, a collaborative web automation system that records browser interactions as editable pseudo-natural-language scripts. Scripts are shared through a wiki and instantiated with personal or corporate data for reuse by other users. |
