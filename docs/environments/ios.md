# iOS

[Home](../../README.md) · [All platforms](../environments.md) · [Research by topic](../topics.md)

58 source-reviewed resources tagged `ios`. Curated metadata; unknown facts are shown as —.

**Contents:** [Benchmarks (1)](#benchmarks) · [Datasets (2)](#datasets) · [Models (4)](#models) · [Agents (9)](#agents) · [Frameworks (14)](#frameworks) · [Tools (14)](#tools) · [Infrastructure (1)](#infrastructure) · [Surveys (1)](#surveys) · [Papers (12)](#papers)

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
| [AppClaw](https://github.com/appclawhq/AppClaw) | android, ios | — | code Apache-2.0 | AppClaw is a mobile automation agent for Android and iOS that executes natural-language tasks by inspecting accessibility trees and tapping screens. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/appclawhq/AppClaw/HEAD/README.md) |
| [ESP32 iPhone Agent](https://github.com/onehumanbeing/esp32-iphone-agent) | ios | — | code MIT | ESP32 iPhone Agent controls unmodified iPhones via Bluetooth HID mouse/keyboard emulation from an ESP32 paired with vision-language screen parsing. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/onehumanbeing/esp32-iphone-agent/HEAD/README.md) |
| [iPhone CUA](https://github.com/masone/iphone-cua) | ios, desktop, macos | — | — | iPhone CUA steers physical iPhones from macOS by pairing an iPhone screen/control bridge with OpenAI Computer-Using Agent models. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/masone/iphone-cua/HEAD/README.md) |
| [Minitap mobile-use](https://github.com/minitap-ai/mobile-use) | android, ios | [2602.07787](https://arxiv.org/abs/2602.07787) (2026) | code Apache-2.0 | Minitap mobile-use is a multi-agent mobile automation system that controls physical and emulated Android and iOS devices from natural language. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/minitap-ai/mobile-use/HEAD/README.md) |
| [Mobster engine](https://github.com/RadishSoftware/mobster) | ios | — | code MIT | iOS agent engine organized around an observe, decide, verify and act loop, using WebDriverAgent screen state and phone actions such as taps, typing, swipes and app switches. | [✓ 2026‑10‑20](https://raw.githubusercontent.com/RadishSoftware/mobster/738cecdd3eacb9df88d48efb9efa53507bb4aeb4/README.md) |
| [nanoMuse](https://github.com/nano-muse/nanoMuse) | cross-platform, desktop, web, android, ios, macos, linux, windows | [2610.08699](https://arxiv.org/abs/2610.08699) (2026) | code GPL-3.0 | nanoMuse is an open-source personal agent that maintains persistent cross-device memory and executes browser, desktop, and mobile tasks. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/nano-muse/nanoMuse/HEAD/README.md) |
| [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) | android, ios | — | code Apache-2.0 | Phone agent model and framework with device interaction tooling. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/zai-org/Open-AutoGLM/HEAD/README.md) |
| [PhysiClaw](https://github.com/physiclaw/PhysiClaw) | android, ios | — | code MIT | PhysiClaw uses an overhead camera and a 3-axis capacitive stylus gantry to physically tap and swipe unmodified smartphones. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/physiclaw/PhysiClaw/HEAD/README.md) |
| [Pocketwatch](https://github.com/psamme/pocketwatch) | ios, desktop, macos | — | code Apache-2.0 | AI beta-testing agent for physical iPhone applications that drives user journeys over macOS iPhone Mirroring. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/psamme/pocketwatch/HEAD/README.md) |

## Frameworks

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [App Use](https://github.com/erickjtorres/app-use) | android, ios | — | code MIT | App Use is a Python framework that connects LLM agents to Android and iOS mobile applications via Appium and accessibility-tree inspection. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/erickjtorres/app-use/HEAD/README.md) |
| [Cactus](https://github.com/cactus-compute/cactus) | cross-platform, android, ios, desktop, macos, linux | — | — | Cactus is a cross-platform on-device LLM and VLM inference framework for mobile and edge AI agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/cactus-compute/cactus/HEAD/README.md) |
| [Fathom](https://github.com/DrizzDev/fathom) | android, ios | — | — | Fathom is an execution harness for mobile computer-use agents that translates plain-English goals into grounded actions on iOS and Android. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/DrizzDev/fathom/HEAD/README.md) |
| [flutter_copilot](https://github.com/anasfik/flutter_copilot) | android, ios, web, desktop | — | code MIT | In-app SDK that exposes Flutter widget trees and semantic actions directly to AI agents without screenshots or OCR. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/anasfik/flutter_copilot/HEAD/README.md) |
| [glassbox](https://github.com/yoyicue/glassbox) | ios, desktop, macos | — | code MIT | glassbox is an iOS and iPadOS computer-use runtime that drives physical iPhones and iPads from screen observations and hardware/bridge control. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/yoyicue/glassbox/HEAD/README.md) |
| [iOS Agent Harness](https://github.com/a178960320/ios-agent-harness) | ios | — | code MIT | iOS Agent Harness runs a Manager-Executor-Reflector GUI agent loop on iPhones to automate cross-app tasks from natural language. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/a178960320/ios-agent-harness/HEAD/README.md) |
| [Mobile Agent Guardian](https://github.com/salus-ryan/mobile-agent-guardian) | android, ios | — | code Apache-2.0 | Five-level safety and action-verification layer for mobile GUI agents that classifies and gates risky phone operations. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/salus-ryan/mobile-agent-guardian/HEAD/README.md) |
| [Mobilerun (formerly Droidrun)](https://github.com/droidrun/mobilerun) | android, ios | — | code MIT | A framework that combines screenshots and accessibility state with agent tools for mobile-device tasks through command-line and Python interfaces. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/droidrun/mobilerun/HEAD/README.md) |
| [Napaxi](https://github.com/antgroup/Napaxi) | android, ios | — | code GPL-3.0 | Mobile-native agent SDK by Ant Group for building on-device AI agents with sandboxed skill execution. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/antgroup/Napaxi/HEAD/README.md) |
| [Nuphus](https://github.com/mrpulor-gh/nuphus) | cross-platform, desktop, android, ios, windows, macos, linux | — | code Apache-2.0 | Local-first desktop AI agent platform with real desktop GUI execution and a companion mobile second-screen controller. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/mrpulor-gh/nuphus/main/README.md) |
| [Optics Framework](https://github.com/mozarkai/optics-framework) | cross-platform, web, android, ios | — | code Apache-2.0 | Optics Framework is a self-healing test automation engine for mobile, web, and TV interfaces with Vision/OCR fallback and an MCP server. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/mozarkai/optics-framework/HEAD/README.md) |
| [Orquestrador de Features](https://github.com/gustavo-em/orchestrator-features) | android, ios, desktop | — | — | Multi-agent loop that plans React Native mobile features, writes code, drives the simulator UI, and verifies visual results. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/gustavo-em/orchestrator-features/main/README.md) |
| [PhoneClaw](https://github.com/kellyvv/PhoneClaw) | ios, android | — | code Apache-2.0 | PhoneClaw turns iOS and Android smartphones into local AI agent runtimes with on-device model inference and native system skills. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/kellyvv/PhoneClaw/HEAD/README.md) |
| [Qirabot](https://github.com/qirabot/qirabot) | cross-platform, web, desktop, android, ios | — | code MIT | Qirabot is a pure-vision multimodal GUI automation framework for operating browsers, mobile apps, desktops, and games without DOM selectors. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/qirabot/qirabot/HEAD/README.md) |

## Tools

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [agent-qa](https://github.com/vostride/agent-qa) | cross-platform, web, android, ios | — | — | QA runner for web, Android and iOS with natural-language tests, CLI/MCP integration, persistent memidex memory and self-improvement from verified run evidence. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/vostride/agent-qa/HEAD/README.md) |
| [Agentrooms](https://github.com/baryhuang/claude-code-by-agents) | desktop, macos, ios | — | code MIT | Agentrooms is a native macOS and iOS application for coordinating multiple local and remote coding agents in shared multi-agent workspaces. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/baryhuang/claude-code-by-agents/HEAD/README.md) |
| [ascript-mcp](https://github.com/ascript-cn/ascript-mcp) | cross-platform, android, ios, desktop, windows | — | code MIT | Model Context Protocol server for automating real Android, iOS, and Windows devices from Claude, Cursor, and MCP clients. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/ascript-cn/ascript-mcp/HEAD/README.md) |
| [debug-kit](https://github.com/dxiongya/debug-kit) | cross-platform, desktop, web, macos, ios, android, windows, linux | — | code MIT | Cross-platform Agent Skill for driving, inspecting, and testing applications across macOS, iOS, Android, Web, Electron, Windows, and Linux. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/dxiongya/debug-kit/HEAD/README.md) |
| [Inner Coordinates](https://github.com/XiaoChu-1208/inner-coordinates) | desktop, macos, ios | — | code MIT | Reverse-engineers a clickable coordinate and state map of macOS and iPhone applications once for deterministic workflow replay. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/XiaoChu-1208/inner-coordinates/HEAD/README.md) |
| [iphone-control (iPhone Mirroring Skill)](https://github.com/CHARLESMORGANSOFTWARE/iphone-control) | ios, desktop, macos | — | code MIT | macOS skill and CoreGraphics controller for driving a paired iPhone through Apple's macOS iPhone Mirroring app. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/CHARLESMORGANSOFTWARE/iphone-control/HEAD/README.md) |
| [iphone-use](https://github.com/leeguooooo/iphone-use) | ios, desktop, macos | — | — | MCP server and CLI that lets Claude Code, Codex, and MCP agents read real iPhone screens as structured text and execute taps/swipes. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/leeguooooo/iphone-use/HEAD/README.md) |
| [macos-desktop-control](https://github.com/d-wwei/macos-desktop-control) | desktop, macos, ios | — | code MIT | Native macOS desktop automation MCP server providing screen capture, mouse/keyboard input, window management, and iOS Simulator control. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/d-wwei/macos-desktop-control/HEAD/README.md) |
| [Mobile Harness](https://github.com/droidrun/mobile-harness) | android, ios | — | code MIT | Portable agent instructions and integration tooling for local or cloud phone control through mobilerun-core. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/droidrun/mobile-harness/HEAD/README.md) |
| [Mobile Next MCP](https://github.com/mobile-next/mobile-mcp) | android, ios | — | code Apache-2.0 | An MCP server exposing mobile accessibility snapshots, screenshots and device interactions across real devices, simulators and emulators. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/mobile-next/mobile-mcp/HEAD/README.md) |
| [pi-iphone-mirroring](https://github.com/aniruddha-adhikary/pi-iphone-mirroring) | ios, desktop, macos | — | code MIT | Vision-first iPhone Mirroring control package for the Pi coding agent on macOS. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/aniruddha-adhikary/pi-iphone-mirroring/main/README.md) |
| [Safari iOS Web Inspector MCP](https://github.com/rodneyrdx/safari-ios-webinspector-mcp) | ios, desktop, macos, web | — | code MIT | TypeScript Model Context Protocol server for inspecting and debugging live iPhone Safari WebKit sessions from macOS. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/rodneyrdx/safari-ios-webinspector-mcp/main/README.md) |
| [tail-aside](https://github.com/quino0627/tail-aside) | web, android, ios | — | code MIT | Remote mobile controller for monitoring and steering the Aside browser agent over Tailscale. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/quino0627/tail-aside/main/README.md) |
| [ToolArks Remote Login Relay](https://github.com/zdayang/remote-login-relay) | web, android, ios | — | — | Self-hosted one-tab mobile handoff relay that lets a human remotely solve login, 2FA, or CAPTCHA walls for an AI browser agent. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/zdayang/remote-login-relay/main/README.md) |

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
| 2026‑10‑29 | [Online Dense Reinforcement Learning with Planning-Grounding Agent for UI Navigation on Live IOS Apps](https://arxiv.org/abs/2610.39264) | ios | Introduces online RL training for agents navigating live iOS apps, separating planning from UI grounding and using step-level and task-completion rewards. |
| 2026‑10‑26 | [iPrefBench: A User-Centric Benchmark for Personalized Mobile Use Agents](https://arxiv.org/abs/2610.34735) | ios | Introduces iPrefBench, an iOS benchmark for mobile agents that tests when they infer missing user preferences from activity history and when they ask the user. |
| 2026‑07‑14 | [KnowAct-GUIClaw: Know Deeply, Act Perfectly, Personal GUI Assistant with Self-Evolving Memory and Skill](https://arxiv.org/abs/2607.12625) | desktop, android, ios, harmonyos, windows | KnowAct-GUIClaw combines a host planner with pluggable GUI subagents, attributable experience memory and an evolving skill library. It uses user profiles and feedback for task decomposition and evaluates transfer across Android, iOS, HarmonyOS and Windows. |
| 2026‑06‑08 | [iOSWorld: A Benchmark for Personally Intelligent Phone Agents](https://arxiv.org/abs/2606.09764) | ios | Introduces a native iOS simulator benchmark with persistent user data, multi-app tasks, and personalization-dependent phone workflows. |
| 2026‑04‑13 | [ClawGUI: A Unified Framework for Training, Evaluating, and Deploying GUI Agents](https://arxiv.org/abs/2604.11784) | android, harmonyos, ios | Presents ClawGUI, a shared harness for GUI-agent reinforcement learning, benchmark evaluation and deployment on mobile devices. It combines parallel virtual and physical environments, process rewards, and hybrid CLI-GUI execution with persistent memory. |
| 2025‑10‑30 | [GUI Knowledge Bench: Revealing the Knowledge Gap of VLMs in GUI Tasks](https://arxiv.org/abs/2510.26098) | web, desktop, windows, macos, linux, android, ios, cross-platform | GUI Knowledge Bench tests knowledge of widgets, interactions, and procedures across six named platforms and 292 applications to assess VLMs used for GUI tasks. |
| 2025‑07‑25 | [MMBench-GUI: Hierarchical Multi-Platform Evaluation Framework for GUI Agents](https://arxiv.org/abs/2507.19478) | web, desktop, windows, macos, linux, ios, android, cross-platform | MMBench-GUI evaluates interface understanding, element grounding, task automation, and collaboration across six named desktop, mobile, and web platforms. It introduces the Efficiency-Quality Area metric for examining execution efficiency alongside task quality in online GUI automation. |
| 2025‑05‑23 | [TransBench: Breaking Barriers for Transferable Graphical User Interface Agents in Dynamic Digital Environments](https://arxiv.org/abs/2505.17629) | ios, android, web, cross-platform | Introduces TransBench to evaluate GUI grounding transfer across app versions, iOS, Android, Web, and functionally distinct applications. |
| 2024‑10‑24 | [Ferret-UI 2: Mastering Universal User Interface Understanding Across Platforms](https://arxiv.org/abs/2410.18967) | ios, android, web, cross-platform | Extends Ferret-UI across device platforms with adaptive visual scaling and synthetic data for referring, grounding, and user-centered UI tasks. |
| 2024‑03‑08 | [UI Semantic Group Detection: Grouping UI Elements with Similar Semantics in Mobile Graphical User Interface](https://arxiv.org/abs/2403.04984) | android, ios | UISCGD detects semantic groups of adjacent text and non-text UI elements. It learns from Android and iOS screenshots to support interface retrieval, UI-to-code structure and screen-reader accessibility. |
| 2023‑11‑13 | [GPT-4V in Wonderland: Large Multimodal Models for Zero-Shot Smartphone GUI Navigation](https://arxiv.org/abs/2311.07562) | ios, android | Studies MM-Navigator, a multimodal agent that interprets smartphone screenshots and predicts localized actions without task-specific training. |
| 2021‑01‑13 | [Screen Recognition: Creating Accessibility Metadata for Mobile Applications from Pixels](https://arxiv.org/abs/2101.04893) | ios | Infers UI elements and accessibility metadata from mobile screenshots to support screen-reader interaction with iOS applications. |
