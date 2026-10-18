# Agent catalog

[Home](../README.md) · [Methodology](methodology.md) · [Machine-readable catalog](../data/catalog.jsonl)

Curated metadata, not a performance ranking. Each entry links its first-party evidence. Unknown facts are shown as —.

*Paper* lists reviewed `introduced_by`/`documented_by` relations with the record's year. *License* lists publisher declarations by scope (code, data, weights, document). *Evidence* links the reviewed first-party snapshot and its retrieval date.

**44 resources:** [Web (11)](#web) · [Desktop (15)](#desktop) · [Mobile (15)](#mobile) · [Cross-platform (2)](#cross-platform) · [Unspecified (1)](#unspecified)

Resources tagged with environments from more than one family are listed under *Cross-platform*; their exact environments stay in the table.

## Web

All entries in this section: web.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [Agent E](https://github.com/EmergenceAI/Agent-E) | [2407.13032](https://arxiv.org/abs/2407.13032) (2024) | code MIT | Browser automation agent on the AG2 framework that pairs a planner agent with a browser navigation agent to fill forms, search shops and work through sites, also callable over a local HTTP API. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/EmergenceAI/Agent-E/HEAD/README.md) |
| [AutoWebGLM](https://github.com/THUDM/AutoWebGLM) | — | code Apache-2.0 | Web navigation agent built on ChatGLM3-6B that simplifies HTML for the model, is trained on hybrid human and AI data with RL and rejection sampling, and comes with the bilingual AutoWebBench. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/THUDM/AutoWebGLM/HEAD/README.md) |
| [Browser Agent (uiuing)](https://github.com/uiuing/browser-agent) | — | code MIT | Chrome side-panel agent whose page engine reads a whole-page semantic DOM snapshot, re-grounds targets by element fingerprints, dispatches DOM events and checks post-conditions before reporting success. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/uiuing/browser-agent/HEAD/README.md) |
| [CAAP Agent](https://github.com/caap-agent/caap-agent) | [2406.06947](https://arxiv.org/abs/2406.06947) (2024) | code AGPL-3.0 | Screenshot-driven agent implementation for MiniWoB++ and WebShop, using a visual observer and context-aware prompts to issue mouse and keyboard actions. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/caap-agent/caap-agent/HEAD/README.md) |
| [Lumen browser agent](https://github.com/omxyz/lumen) | — | code MIT | A screenshot-driven browser agent over Chrome DevTools Protocol, with resumable sessions, context compression, action replay and configurable completion checks. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/omxyz/lumen/HEAD/README.md) |
| [MagenticLite / Magentic UI](https://github.com/microsoft/magentic-ui) | — | code MIT | Microsoft agent application combining orchestration with browser interaction; successor to Magentic UI. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/microsoft/magentic-ui/HEAD/README.md) |
| [Nanobrowser](https://github.com/nanobrowser/nanobrowser) | — | code Apache-2.0 | A browser-extension agent that reads pages, interacts with elements and moves between tabs from a side-panel task interface. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/nanobrowser/nanobrowser/HEAD/README.md) |
| [OpenAgents Web Agent](https://github.com/xlang-ai/OpenAgents/tree/main/real_agents/web_agent) | [2310.10634](https://arxiv.org/abs/2310.10634) (2023) | code Apache-2.0 | The OpenAgents browser-control component, connecting a Chrome extension to a web agent and local chat platform for navigating sites and completing interface tasks. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/xlang-ai/OpenAgents/HEAD/README.md) |
| [RCI Agent](https://github.com/posgnu/rci-agent) | [2303.17491](https://arxiv.org/abs/2303.17491) (2023) | code MIT | A MiniWoB++ agent that uses explicit and implicit recursive criticism-and-improvement prompts to refine action plans and ground actions to browser state. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/posgnu/rci-agent/HEAD/README.md) |
| [SeeAct](https://github.com/OSU-NLP-Group/SeeAct) | [2401.01614](https://arxiv.org/abs/2401.01614) (2024) | — | Generalist web agent framework for large multimodal models such as GPT-4V, with a Playwright tool that runs agents on live websites, text-choice and set-of-mark grounding, and a crawler mode. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/OSU-NLP-Group/SeeAct/HEAD/README.md) |
| [Surf New](https://github.com/steel-dev/surf.new) | — | code MIT | Next.js and FastAPI playground from Steel for trying web agents in a controlled browser environment, with live views of browser interaction and support for providers such as Claude and GPT-4. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/steel-dev/surf.new/HEAD/README.md) |

[↑ Back to top](#agent-catalog)

## Desktop

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Agent S](https://github.com/simular-ai/Agent-S) | desktop | [2410.08164](https://arxiv.org/abs/2410.08164) (2024), [2504.00906](https://arxiv.org/abs/2504.00906) (2025) | code Apache-2.0 | Simular's open-source framework for computer-use agents that click, type and scroll through desktop and web apps on macOS, Windows and Linux; its third generation, Agent S3, reports 72.6% on OSWorld. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/simular-ai/Agent-S/HEAD/README.md) |
| [AssistGUI](https://github.com/showlab/assistgui) | desktop | — | — | LLM-based assistant for automating work in desktop productivity software by watching the screen and issuing mouse and keyboard commands; its repository says the code will be released later. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/showlab/assistgui/HEAD/README.md) |
| [Bytebot](https://github.com/bytebot-ai/bytebot) | desktop | — | code Apache-2.0 | Open-source desktop agent that works inside its own Ubuntu Linux virtual desktop, with a web task interface, REST APIs for tasks and direct control, a takeover mode and password-manager logins. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/bytebot-ai/bytebot/HEAD/README.md) |
| [COLA demo](https://github.com/Alokia/COLA-demo) | desktop, windows | [2503.09263](https://arxiv.org/abs/2503.09263) (2025) | — | Research demonstration of collaborative Windows GUI automation with dynamic task scheduling and recovery mechanisms. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/Alokia/COLA-demo/HEAD/README.md) |
| [Cradle](https://github.com/BAAI-Agents/Cradle) | desktop | [2403.03186](https://arxiv.org/abs/2403.03186) (2024) | code MIT | Framework in which foundation models control games and software from screenshots alone, acting through keyboard and mouse, shown on RDR2, Stardew Valley, Cities: Skylines and Dealer's Life 2. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/BAAI-Agents/Cradle/HEAD/README.md) |
| [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter) | desktop | — | code Apache-2.0 | Assistant framework combining code execution and computer interaction. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/OpenInterpreter/open-interpreter/HEAD/README.md) |
| [OpenAdapt](https://github.com/OpenAdaptAI/OpenAdapt) | desktop | — | code MIT | Tools for learning and automating workflows from desktop demonstrations. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/OpenAdaptAI/OpenAdapt/HEAD/README.md) |
| [OS-Copilot](https://github.com/OS-Copilot/OS-Copilot) | desktop | [2402.07456](https://arxiv.org/abs/2402.07456) (2024) | code MIT | Open-source library for generalist agents acting on an operating system's web, terminals, files and third-party apps, with the FRIDAY assistant, which takes custom tools and self-learns Excel tasks. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/OS-Copilot/OS-Copilot/HEAD/README.md) |
| [PC-Agent](https://github.com/GAIR-NLP/PC-Agent) | desktop | [2412.17589](https://arxiv.org/abs/2412.17589) (2024) | code MIT | Human-cognition-transfer framework for PC agents: PC Tracker logs human computer use, cognition completion turns logs into cognitive trajectories, and a planner works with a grounding agent. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/GAIR-NLP/PC-Agent/HEAD/README.md) |
| [PC-Agent (X-PLUG component)](https://github.com/X-PLUG/MobileAgent/tree/main/PC-Agent) | desktop, windows, macos | [2502.14282](https://arxiv.org/abs/2502.14282) (2025) | code MIT | Multi-agent desktop automation component for Windows and macOS, combining active perception, task decomposition and reflection for workflows spanning applications. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/X-PLUG/MobileAgent/HEAD/PC-Agent/README.md) |
| [ScreenAgent](https://github.com/niuzaisheng/ScreenAgent) | desktop | [2402.07945](https://arxiv.org/abs/2402.07945) (2024) | — | Environment and agent in which a vision-language model controls real desktops over VNC with mouse and keyboard in plan, act and reflect stages, plus a hand-annotated dataset of daily computer tasks. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/niuzaisheng/ScreenAgent/HEAD/README.md) |
| [Self Operating Computer](https://github.com/OthersideAI/self-operating-computer) | desktop | — | code MIT | Framework, released in November 2023, in which a multimodal model views the screen and picks mouse and keyboard actions toward a goal, with backends such as GPT-4o, Claude 3, Gemini and LLaVA. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/OthersideAI/self-operating-computer/HEAD/README.md) |
| [SheetCopilot](https://github.com/BraveGroup/SheetCopilot) | desktop, windows, linux | [2305.19308](https://arxiv.org/abs/2305.19308) (2023) | — | Spreadsheet automation agent for Windows/Excel, with benchmark assets and a separately released headless Ubuntu evaluation backend. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/BraveGroup/SheetCopilot/HEAD/README.md) |
| [ShowUI-Aloha](https://github.com/showlab/ShowUI-Aloha) | desktop, windows, macos | [2601.07181](https://arxiv.org/abs/2601.07181) (2026) | code Apache-2.0 | Desktop agent that records demonstrations, derives semantic action traces, and uses them to plan and execute related workflows. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/showlab/ShowUI-Aloha/HEAD/README.md) |
| [UFO](https://github.com/microsoft/UFO) | windows, desktop | [2402.07939](https://arxiv.org/abs/2402.07939) (2024) | — | Windows agent framework for application and desktop automation. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/microsoft/UFO/HEAD/README.md) |

[↑ Back to top](#agent-catalog)

## Mobile

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [AppAgent](https://github.com/TencentQQGYLab/AppAgent) | android | [2312.13771](https://arxiv.org/abs/2312.13771) (2023) | code MIT | Multimodal agent that operates Android apps through taps and swipes without back-end access, building a reusable knowledge base from autonomous exploration or from watching human demonstrations. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/TencentQQGYLab/AppAgent/HEAD/README.md) |
| [AppAgent Pro](https://github.com/LaoKuiZe/AppAgent-Pro) | android | [2508.18689](https://arxiv.org/abs/2508.18689) (2025) | code MIT | Proactive Android agent built on AppAgent that uses GPT-4o to decide whether YouTube or Amazon content would help, operates those apps over ADB, and merges what it finds into its answer. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/LaoKuiZe/AppAgent-Pro/HEAD/README.md) |
| [AppAgentX](https://github.com/Westlake-AGI-Lab/AppAgentX) | android | [2503.02268](https://arxiv.org/abs/2503.02268) (2025) | — | Mobile agent research using accumulated interaction experience. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/Westlake-AGI-Lab/AppAgentX/HEAD/README.md) |
| [Auto-GUI / Auto-UI](https://github.com/cooelf/Auto-GUI) | android | [2309.11436](https://arxiv.org/abs/2309.11436) (2023) | code Apache-2.0 | Screenshot-based mobile agent implementation with training and inference code for chain-of-action prediction. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/cooelf/Auto-GUI/HEAD/README.md) |
| [AutoDroid](https://github.com/MobileLLM/AutoDroid) | android | [2308.15272](https://arxiv.org/abs/2308.15272) (2023) | — | LLM-powered Android task automation built on DroidBot, released with DroidTask, a dataset of per-app screenshots, view hierarchies, exploration records and ground-truth task files. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/MobileLLM/AutoDroid/HEAD/README.md) |
| [AutoDroid V2](https://github.com/MobileLLM/AutoDroid-V2) | android | [2412.18116](https://arxiv.org/abs/2412.18116) (2024) | — | An Android automation implementation that builds app documentation from exploration traces and evaluates language-model-generated execution code in emulator workflows. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/MobileLLM/AutoDroid-V2/HEAD/README_minimal.md) |
| [CoCo-Agent](https://github.com/xbmxb/CoCo-Agent) | android | [2402.11941](https://arxiv.org/abs/2402.11941) (2024) | — | Research implementation combining screen and layout perception with conditional action prediction for smartphone automation. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/xbmxb/CoCo-Agent/HEAD/README.md) |
| [MobA](https://github.com/OpenDFM/MobA) | android | [2410.13757](https://arxiv.org/abs/2410.13757) (2024) | — | An Android agent that combines global task planning and memory with a local action executor, using reflection to revise mobile interaction steps. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/OpenDFM/MobA/HEAD/README.md) |
| [Mobile Use](https://github.com/MadeAgents/mobile-use) | android | [2507.16853](https://arxiv.org/abs/2507.16853) (2025) | code MIT | Android GUI agent that operates real phones through ADB with hierarchical reflection and a multi-agent framework, run from a web interface or Python and evaluated on AndroidWorld and AndroidLab. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/MadeAgents/mobile-use/HEAD/README.md) |
| [Mobile-Agent-E code component](https://github.com/X-PLUG/MobileAgent/tree/main/Mobile-Agent-E) | android | [2501.11733](https://arxiv.org/abs/2501.11733) (2025) | code MIT | Android automation component with hierarchical planning, reflection and persistent tips/shortcuts learned across task sequences. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/X-PLUG/MobileAgent/HEAD/Mobile-Agent-E/README.md) |
| [MobileAgent (Alipay)](https://github.com/alipay/mobile-agent) | android | [2401.04124](https://arxiv.org/abs/2401.04124) (2024) | — | Mobile-control research implementation combining operating-procedure context with human interaction for personalized task execution. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/alipay/mobile-agent/HEAD/README.md) |
| [MobileGPT](https://github.com/fclab-skku/MobileGPT) | android | [2312.03003](https://arxiv.org/abs/2312.03003) (2023) | code Apache-2.0 | An Android client and Python-server agent that learns reusable app subtasks through exploration, selection, derivation and memory recall. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/fclab-skku/MobileGPT/HEAD/README.md) |
| [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) | android, ios | — | code Apache-2.0 | Phone agent model and framework with device interaction tooling. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/zai-org/Open-AutoGLM/HEAD/README.md) |
| [OS-Kairos](https://github.com/Wuzheng02/OS-Kairos) | android | [2503.16465](https://arxiv.org/abs/2503.16465) (2025) | — | Android GUI-agent research implementation that uses confidence-guided interaction to choose between autonomous actions and human assistance. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/Wuzheng02/OS-Kairos/HEAD/README.md) |
| [VisionTasker](https://github.com/AkimotoAyako/VisionTasker) | android | [2312.11190](https://arxiv.org/abs/2312.11190) (2023) | code GPL-3.0 | An Android automation implementation that translates screenshot-based UI understanding into language descriptions for step-by-step LLM planning and action execution. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/AkimotoAyako/VisionTasker/HEAD/readme.md) |

[↑ Back to top](#agent-catalog)

## Cross-platform

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Mobile-Agent](https://github.com/X-PLUG/MobileAgent) | android, cross-platform | [2401.16158](https://arxiv.org/abs/2401.16158) (2024), [2406.01014](https://arxiv.org/abs/2406.01014) (2024), [2508.15144](https://arxiv.org/abs/2508.15144) (2025), [2602.16855](https://arxiv.org/abs/2602.16855) (2026) | code MIT | Mobile device agent family using visual interface interaction. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/X-PLUG/MobileAgent/HEAD/README.md) |
| [UI-TARS Desktop](https://github.com/bytedance/UI-TARS-desktop) | desktop, web | — | code Apache-2.0 | Desktop app for a local GUI agent driven by UI-TARS and Seed-1.5-VL/1.6 models, offering local and remote operators for computers and browsers; the repository also ships the Agent TARS CLI and web UI. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/bytedance/UI-TARS-desktop/HEAD/README.md) |

[↑ Back to top](#agent-catalog)

## Unspecified

All entries in this section: unspecified.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [LearnAct](https://github.com/lgy0404/LearnAct) | [2504.13805](https://arxiv.org/abs/2504.13805) (2025) | — | Released inference and evaluation code for demonstration-conditioned mobile GUI agents on LearnGUI-Offline. The repository describes a multi-agent adaptation method and links the LearnGUI demonstrations. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/lgy0404/LearnAct/HEAD/README.md) |

[↑ Back to top](#agent-catalog)

Detailed notes and separate code/data/weights license declarations are in `data/catalog.jsonl`.
