# Recording

[Home](../../README.md) · [All topics](../topics.md) · [Full arXiv bibliography](../papers.md)

56 source-reviewed resources tagged `recording`. Curated metadata; unknown facts are shown as —.

**Contents:** [Benchmarks (1)](#benchmarks) · [Datasets (1)](#datasets) · [Agents (3)](#agents) · [Frameworks (8)](#frameworks) · [Tools (18)](#tools) · [Infrastructure (1)](#infrastructure) · [Products (1)](#products) · [Surveys (1)](#surveys) · [Papers (22)](#papers)

## Benchmarks

All entries in this section: web.

| Resource | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [browser-eval](https://github.com/lexmount/browser-eval) | — | — | code Apache-2.0 | browser-eval is an evaluation harness for web fetching, deterministic browser trajectory replay, and autonomous web agent benchmarking. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/lexmount/browser-eval/HEAD/README.md) |

## Datasets

All entries in this section: desktop.

| Resource | Paper | Scale | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [WorkDemo-350](https://huggingface.co/datasets/yuqi777/WorkDemo-350) | [2610.12984](https://arxiv.org/abs/2610.12984) (2026) | [350 demonstrations](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) · [8,388 evidence images](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) · [11,951 action records](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) | data cc-by-4.0 | Desktop demonstrations with task descriptions, videos, input logs, and action-linked screenshot evidence for studying reusable agent skills. | [✓ 2026‑10‑16](https://huggingface.co/datasets/yuqi777/WorkDemo-350/raw/main/README.md) |

## Agents

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | desktop | — | code MIT | Tools for learning and automating workflows from desktop demonstrations. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/OpenAdaptAI/OpenAdapt/HEAD/README.md) |
| [Ruyi (如意)](https://github.com/icesword0760/ruyi) | web | — | code AGPL-3.0 | Ruyi streams remote Chrome sessions to the user's browser for collaborative human-AI control and compiles actions into self-healing scripts. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/icesword0760/ruyi/HEAD/README.md) |
| [ShowUI-Aloha](https://github.com/showlab/ShowUI-Aloha) | desktop, windows, macos | [2601.07181](https://arxiv.org/abs/2601.07181) (2026) | code Apache-2.0 | Desktop agent that records demonstrations, derives semantic action traces, and uses them to plan and execute related workflows. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/showlab/ShowUI-Aloha/HEAD/README.md) |

## Frameworks

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [AgentStudio](https://github.com/skyworkai/agent-studio) | desktop, linux | [2403.17918](https://arxiv.org/abs/2403.17918) (2024) | code AGPL-3.0 | Toolkit and Ubuntu-based environment for building and evaluating generalist computer-use agents through GUI and API interaction. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/skyworkai/agent-studio/HEAD/README.md) |
| [Appwalk](https://github.com/kubstack/appwalk) | web | — | code MIT | AI-powered CLI that explores a web application in a browser and compiles the run into verified Playwright test suites. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/kubstack/appwalk/main/README.md) |
| [Deterministic Computer-Use Automation](https://github.com/joncody/computer-use-automation) | cross-platform, desktop, web | — | code MIT | Two-phase computer-use automation framework that compiles LLM-driven UI discovery into deterministic replay scripts. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/joncody/computer-use-automation/HEAD/README.md) |
| [Lightfeed Replayable Browser Agent](https://github.com/lightfeed/browser-agent) | web | — | code MIT | TypeScript browser agent library that uses an LLM to complete a web navigation workflow once and replays cached selectors with zero LLM tokens. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/lightfeed/browser-agent/HEAD/README.md) |
| [RecordAgent (ButvanAgent)](https://github.com/Kavanio/RecordAgent) | cross-platform, desktop, windows, macos, linux | — | — | Local-first Tauri and AgentScope desktop agent workbench with permission approvals, tool orchestration, and workflow recording. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/Kavanio/RecordAgent/main/README.md) |
| [screen2gym](https://github.com/marc-saouda/screen2gym) | cross-platform, desktop, web | — | code MIT | screen2gym compiles raw action-labeled screen recordings into resettable, programmatically gradable RL environments for computer-use agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/marc-saouda/screen2gym/HEAD/README.md) |
| [SeleniumBase](https://github.com/seleniumbase/SeleniumBase) | web | — | — | Python browser automation framework for web crawling, end-to-end testing and scraping, with a recorder that generates tests and stealth options. | [✓ 2026‑11‑06](https://raw.githubusercontent.com/seleniumbase/SeleniumBase/b806f54ab0c998c90654b59a817d959f7ff7920c/README.md) |
| [Work2Skill](https://github.com/china-qijizhifeng/Work2Skill) | desktop, macos, linux | [2610.12984](https://arxiv.org/abs/2610.12984) (2026) | code MIT | Collects human GUI demonstrations and inspects multimodal evidence to derive reusable agent workflow skills. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/china-qijizhifeng/Work2Skill/HEAD/README.md) |

## Tools

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Activity Recorder](https://github.com/anikasomaia/local-activity-recorder) | desktop, windows | — | — | Windows tray utility that records primary-display screenshots, keyboard key codes and mouse events as local JPEG and JSON files for training-data collection. | [✓ 2026‑10‑20](https://raw.githubusercontent.com/anikasomaia/local-activity-recorder/967cea087bf6496b3b82743fb96770fa29f8e203/README.md) |
| [Agent VCR](https://github.com/ixchio/agent-vcr) | cross-platform, web, desktop | — | code MIT | Agent VCR records, replays, and diffs deterministic cassettes of multi-turn agent tool calls, state transitions, and execution traces. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/ixchio/agent-vcr/HEAD/README.md) |
| [AI Computer Interaction Logger](https://github.com/hemangjoshi37a/AIComputerInteractionLogger) | cross-platform, desktop, windows, macos, linux | — | code MIT | AI Computer Interaction Logger records synchronized screen video, active window metadata, and mouse/keyboard events for CUA imitation learning. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/hemangjoshi37a/AIComputerInteractionLogger/HEAD/readme.md) |
| [Bflow (browser-automation-cli)](https://github.com/KhBayazidAhmed/browser-automation-cli) | web | — | — | Zero-dependency browser automation CLI and visual workflow recorder. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/KhBayazidAhmed/browser-automation-cli/main/README.md) |
| [Browser Use WebUI](https://github.com/browser-use/web-ui) | web | — | code MIT | A Gradio interface for configuring and running Browser Use agents, including persistent browser sessions and interaction recordings. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/browser-use/web-ui/HEAD/README.md) |
| [COCO4GUI](https://github.com/harpreetsahota204/gui_dataset_creator) | cross-platform, desktop, web | — | code Apache-2.0 | COCO4GUI is an interactive screen capture and bounding-box annotation tool for building COCO-formatted GUI grounding datasets. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/harpreetsahota204/gui_dataset_creator/HEAD/README.md) |
| [dsh-browser-ops](https://github.com/lirui1024k/dsh-browser-ops) | web | — | code MIT | DeepSeek Harness plugin combining agent-driven real-browser control with workflow recording. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/lirui1024k/dsh-browser-ops/main/README.md) |
| [dsh-record-replay](https://github.com/humblebanana/dsh-record-replay) | desktop, macos | — | code MIT | DeepSeek Harness plugin that records macOS desktop demonstrations via Open Record/Replay and compiles them into agent skills. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/humblebanana/dsh-record-replay/HEAD/README.md) |
| [Libretto](https://github.com/cashew-labs/libretto) | web | — | code MIT | Libretto is a toolkit that gives coding agents a live browser and CLI to inspect pages, record user actions, build scripts, and debug web integrations. | [✓ 2026‑11‑06](https://raw.githubusercontent.com/cashew-labs/libretto/41ab782ccea765d7a9a3c9b56b1b2586723962e3/README.md) |
| [Open Codex Computer History](https://github.com/hqhq1025/open-codex-computer-history) | desktop, macos | — | code MIT | Clean-room macOS implementation of event-stream interaction recording using Accessibility hit-testing, CGEvent taps, and SkyLight window snapshots. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/hqhq1025/open-codex-computer-history/HEAD/README.md) |
| [Open Codex Record & Replay](https://github.com/hqhq1025/open-codex-record-and-replay) | desktop, macos | — | code MIT | Clean-room macOS implementation of semantic UI workflow recording and deterministic Accessibility-tree replay with visual template fallback. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/hqhq1025/open-codex-record-and-replay/HEAD/README.md) |
| [Open Record/Replay](https://github.com/humblebanana/open-record-replay) | desktop, macos | — | code MIT | Open Record/Replay records macOS user demonstrations with Accessibility metadata and compiles them into reusable agent skills. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/humblebanana/open-record-replay/HEAD/README.md) |
| [screencast-desktop](https://github.com/JHamidun/screencast-desktop) | desktop, windows | — | code MIT | Claude Code plugin where an agent drives a Windows desktop application and records the session as a narrated screencast. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/JHamidun/screencast-desktop/main/README.md) |
| [skillproof](https://github.com/hccccc01333/skillproof) | web | — | code MIT | skillproof records a human browser demonstration once and compiles it into a replayable agent skill paired with an explicit completion verifier. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/hccccc01333/skillproof/HEAD/README.md) |
| [Taprun (tap)](https://github.com/LeonTing1010/tap) | web | — | code MIT | Captures a logged-in browser task demonstration once and compiles it into a deterministic zero-token replay skill. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/LeonTing1010/tap/HEAD/README.md) |
| [TERX](https://github.com/ixchio/terx) | web | — | code MIT | Browser-agent procedural memory and MCP server that compiles repeated web workflows into deterministic zero-token replays. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/ixchio/terx/HEAD/README.md) |
| [UnderPixel](https://github.com/Leluth/underpixel) | web | — | code MIT | Chrome extension and MCP server that correlates timestamped visual screen interactions with underlying network API calls. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/Leluth/underpixel/HEAD/README.md) |
| [Zhubi (朱笔)](https://github.com/icesword0760/zhubi) | cross-platform, desktop, web | — | code AGPL-3.0 | Zhubi is a self-hosted bounding-box annotation and fine-tuning workbench for training Florence-2 and YOLO GUI detector models. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/icesword0760/zhubi/HEAD/README.md) |

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
