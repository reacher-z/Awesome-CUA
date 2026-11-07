# Recording

[Home](../../README.md) · [All topics](../topics.md) · [Full arXiv bibliography](../papers.md)

65 source-reviewed resources tagged `recording`. Curated metadata; unknown facts are shown as —.

**Contents:** [Benchmarks (1)](#benchmarks) · [Datasets (1)](#datasets) · [Agents (3)](#agents) · [Frameworks (17)](#frameworks) · [Tools (18)](#tools) · [Infrastructure (1)](#infrastructure) · [Products (1)](#products) · [Surveys (1)](#surveys) · [Papers (22)](#papers)

## Benchmarks

All entries in this section: cross-platform, desktop, web.

| Resource | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [ScreenLeak](https://github.com/screenpipe/screenleak) | — | — | code Apache-2.0 | ScreenLeak is a multimodal benchmark for measuring sensitive-information detection and PII redaction in continuous screen recording data. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/screenpipe/screenleak/HEAD/README.md) |

## Datasets

All entries in this section: desktop.

| Resource | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [WorkDemo-350](https://huggingface.co/datasets/yuqi777/WorkDemo-350) | [2610.12984](https://arxiv.org/abs/2610.12984) (2026) | [350 demonstrations](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) · [8,388 evidence images](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) · [11,951 action records](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) | data cc-by-4.0 | Desktop demonstrations with task descriptions, videos, input logs, and action-linked screenshot evidence for studying reusable agent skills. | [✓ 2026‑10‑16](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) |

## Agents

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | desktop | — | code MIT | Tools for learning and automating workflows from desktop demonstrations. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/OpenAdaptAI/OpenAdapt/HEAD/README.md) |
| [RegionCUA](https://github.com/Region-AI/region-cua) | cross-platform, desktop, macos, windows, linux | — | code MIT | RegionCUA is a local Ollama-powered desktop agent that explores GUI applications and generates documented screenshots, videos, and replay scripts. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/Region-AI/region-cua/HEAD/README.md) |
| [ShowUI-Aloha](https://github.com/showlab/ShowUI-Aloha) | desktop, windows, macos | [2601.07181](https://arxiv.org/abs/2601.07181) (2026) | code Apache-2.0 | Desktop agent that records demonstrations, derives semantic action traces, and uses them to plan and execute related workflows. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/showlab/ShowUI-Aloha/HEAD/README.md) |

## Frameworks

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [ActionAnything](https://github.com/xxwtiancai/action-anything) | cross-platform, desktop, web | — | code MIT | Model-agnostic runtime for evaluating, approving, recording, and replaying AI agent actions across desktop and web interfaces. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/xxwtiancai/action-anything/HEAD/README.md) |
| [AgentStudio](https://github.com/skyworkai/agent-studio) | desktop, linux | [2403.17918](https://arxiv.org/abs/2403.17918) (2024) | code AGPL-3.0 | Toolkit and Ubuntu-based environment for building and evaluating generalist computer-use agents through GUI and API interaction. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/skyworkai/agent-studio/HEAD/README.md) |
| [Bridge Studio (WebMCP Browser Studio)](https://github.com/SalilBhasinOfficial/webmcp-browser-studio) | web | — | code MIT | Visible, human-governed browser workspace that converts live web workflows into reusable WebMCP tools. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/SalilBhasinOfficial/webmcp-browser-studio/main/README.md) |
| [flowcast](https://github.com/SuperMarioYL/flowcast) | web | — | code Apache-2.0 | Records browser walkthroughs once, stores structured locator cues, and replays parameterized web workflows with self-healing recovery. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/SuperMarioYL/flowcast/HEAD/README.md) |
| [Legacy UI Capability Engine](https://github.com/saitejareddi3636/legacy-ui-capability-engine) | web | — | — | Learns a legacy browser workflow once with an LLM and compiles it into a verified, reusable capability module. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/saitejareddi3636/legacy-ui-capability-engine/main/README.md) |
| [Maestro (AI-Drivable RPA)](https://github.com/rexchengm/maestro) | desktop, windows, web | — | code Apache-2.0 | Records a desktop or browser task once and lets AI optimize, parameterize, and replay it as a deterministic RPA workflow. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/rexchengm/maestro/HEAD/README.md) |
| [maponce](https://github.com/shivampatel0714/maponce) | web | — | code MIT | Uses an LLM to map or record browser automations once and replays them deterministically via Playwright without LLM calls. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/shivampatel0714/maponce/HEAD/README.md) |
| [MetaWebMCP](https://github.com/scanchila/MetaWebMCP) | web | — | code MIT | In-browser workbench to author, test, and export structured WebMCP tool definitions from live website workflows. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/scanchila/MetaWebMCP/main/README.md) |
| [Northstar (Legacy Portal CUA)](https://github.com/zoyaarief/legacy-credit-union-automation) | web | — | — | Discovers workflows on legacy credit-union web portals with an AI agent once and compiles them into deterministic scripts. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/zoyaarief/legacy-credit-union-automation/main/README.md) |
| [PageRunner](https://github.com/SAY-5/pagerunner) | web | — | code MIT | PageRunner is a browser-agent orchestration platform with bounded execution loops, deterministic replay, and golden-trace verification. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/SAY-5/pagerunner/HEAD/README.md) |
| [Project Interface (Legacy Web UI Compiler)](https://github.com/ShahaDeven/Project_interface) | web | — | — | Uses an LLM to discover how to complete a task in a legacy web UI once and distills the run into a reusable programmatic interface. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/ShahaDeven/Project_interface/HEAD/README.md) |
| [Promptwright](https://github.com/sahajamit/promptwright) | web, desktop | — | code MIT | Promptwright is an AI QA desktop agent that drives browsers from plain English or records user clicks into deterministic Playwright tests. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/sahajamit/promptwright/HEAD/README.md) |
| [RishabhP1508 Understudy](https://github.com/RishabhP1508/understudy) | web, desktop | — | — | Records a single LLM-driven exploration of a legacy UI into a typed capability artifact for deterministic zero-LLM replay. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/RishabhP1508/understudy/main/README.md) |
| [SeleniumBase](https://github.com/seleniumbase/SeleniumBase) | web | — | — | Python browser automation framework for web crawling, end-to-end testing and scraping, with a recorder that generates tests and stealth options. | [✓ 2026‑11‑06](https://raw.githubusercontent.com/seleniumbase/SeleniumBase/b806f54ab0c998c90654b59a817d959f7ff7920c/README.md) |
| [Understudy](https://github.com/understudy-ai/understudy) | desktop, macos, web | — | code MIT | Understudy observes human desktop and browser demonstrations and compiles them into parameterized, replayable computer-use skills. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/understudy-ai/understudy/HEAD/README.md) |
| [Vedanshu7 Operant](https://github.com/Vedanshu7/operant) | web, desktop | — | — | Discovers how to complete a task in a no-API application once with an LLM and compiles the trace for repeatable execution. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/Vedanshu7/operant/main/README.md) |
| [Work2Skill](https://github.com/china-qijizhifeng/Work2Skill) | desktop, macos, linux | [2610.12984](https://arxiv.org/abs/2610.12984) (2026) | code MIT | Collects human GUI demonstrations and inspects multimodal evidence to derive reusable agent workflow skills. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/china-qijizhifeng/Work2Skill/HEAD/README.md) |

## Tools

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Activity Recorder](https://github.com/anikasomaia/local-activity-recorder) | desktop, windows | — | — | Windows tray utility that records primary-display screenshots, keyboard key codes and mouse events as local JPEG and JSON files for training-data collection. | [✓ 2026‑10‑20](https://raw.githubusercontent.com/anikasomaia/local-activity-recorder/967cea087bf6496b3b82743fb96770fa29f8e203/README.md) |
| [Agent DevTools (39-tools)](https://github.com/YYDongRo/39-tools) | cross-platform, desktop, web | — | code MIT | Action-level observability, state verification, and debugging toolkit for computer-use agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/YYDongRo/39-tools/HEAD/README.md) |
| [Browser Agent Recorder](https://github.com/VelvetAbyss/browser-agent-recorder) | web | — | code MIT | Records human browser workflows and exports them as both human-readable SOP documents and machine-readable Agent Skill Packs. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/VelvetAbyss/browser-agent-recorder/HEAD/README.md) |
| [Browser Use WebUI](https://github.com/browser-use/web-ui) | web | — | code MIT | A Gradio interface for configuring and running Browser Use agents, including persistent browser sessions and interaction recordings. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/browser-use/web-ui/HEAD/README.md) |
| [Computer-Use Cache](https://github.com/rohanarun/computer-use-cache) | cross-platform, web, desktop | — | code MIT | Drop-in OpenAI-compatible caching proxy that records and replays repeated computer-use and browser-agent workflows. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/rohanarun/computer-use-cache/HEAD/README.md) |
| [doc-agent](https://github.com/samuel-as/doc-agent) | web | — | code MIT | Claude Code skill that documents a web procedure with annotated screenshots by performing it in a live browser. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/samuel-as/doc-agent/main/README.md) |
| [DuckTrack](https://github.com/TheDuckAI/DuckTrack) | cross-platform, desktop, windows, macos, linux | — | code MIT | DuckTrack records synchronized screen video and low-level mouse and keyboard events for building multimodal computer-interaction datasets. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/TheDuckAI/DuckTrack/HEAD/README.md) |
| [DXcam](https://github.com/ra1nty/DXcam) | desktop, windows | — | code MIT | DXcam is a high-frequency Python screen capture library for Windows using the Desktop Duplication API at up to 240Hz for GUI agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/ra1nty/DXcam/HEAD/README.md) |
| [Forged](https://github.com/sam-siavoshian/forged) | web | — | code MIT | Self-learning browser automation MCP server that records successful agent trajectories and replays deterministic Playwright steps. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/sam-siavoshian/forged/HEAD/README.md) |
| [Helios](https://github.com/vrtnis/helios) | cross-platform, desktop, web | — | code MIT | Observability and evaluation harness that converts H computer-use agent sessions into reviewable traces and failure findings. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/vrtnis/helios/HEAD/README.md) |
| [Inner Coordinates](https://github.com/XiaoChu-1208/inner-coordinates) | desktop, macos, ios | — | code MIT | Reverse-engineers a clickable coordinate and state map of macOS and iPhone applications once for deterministic workflow replay. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/XiaoChu-1208/inner-coordinates/HEAD/README.md) |
| [Libretto](https://github.com/cashew-labs/libretto) | web | — | code MIT | Libretto is a toolkit that gives coding agents a live browser and CLI to inspect pages, record user actions, build scripts, and debug web integrations. | [✓ 2026‑11‑06](https://raw.githubusercontent.com/cashew-labs/libretto/41ab782ccea765d7a9a3c9b56b1b2586723962e3/README.md) |
| [MacControlKit](https://github.com/tzafon/MacControlKit) | desktop, macos | — | code Apache-2.0 | MacControlKit is a Swift package by Tzafon for capturing macOS screens and dispatching native mouse and keyboard events. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/tzafon/MacControlKit/HEAD/README.md) |
| [mcp-chrome-bridge](https://github.com/wizardofweb125-lab/mcp-chrome-bridge) | web | — | code MIT | Model Context Protocol server for controlling Chrome tabs, forms, console/network logs, screenshots, and GIF recordings. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/wizardofweb125-lab/mcp-chrome-bridge/HEAD/README.md) |
| [recast](https://github.com/yagna-1/recast) | web | — | code MIT | Compiler that converts recorded AI browser-agent execution traces into deterministic, zero-token Playwright test scripts. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/yagna-1/recast/HEAD/README.md) |
| [Screenpipe](https://github.com/screenpipe/screenpipe) | cross-platform, desktop, macos, windows, linux | — | — | Screenpipe continuously captures desktop screen text via accessibility/OCR and audio transcripts into a local database for AI agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/screenpipe/screenpipe/HEAD/README.md) |
| [Windows Local Action Recorder](https://github.com/week833/windows-local-action-recorder) | desktop, windows | — | code MIT | Windows desktop action recorder and controlled replay tool that packages human UI demonstrations for Codex agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/week833/windows-local-action-recorder/main/README.md) |
| [windows-computer-use-mcp (Scan-Code & Multi-Monitor)](https://github.com/sshh12/windows-computer-use-mcp) | desktop, windows | — | code MIT | Windows computer-use MCP server supporting multi-monitor screen capture and hardware scan-code keyboard/mouse injection for desktop and 3D apps. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/sshh12/windows-computer-use-mcp/HEAD/README.md) |

## Infrastructure

All entries in this section: web, desktop, windows, macos, linux.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [BrowserOS / BrowserOS neo](https://github.com/browseros-ai/BrowserOS) | — | code AGPL-3.0 | Chromium-based browser implementations for external agent control and built-in assistant workflows, with session visibility and replay facilities. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/browseros-ai/BrowserOS/HEAD/README.md) |

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
