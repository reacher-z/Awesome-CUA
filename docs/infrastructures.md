# Infrastructure catalog

[Home](../README.md) · [Methodology](methodology.md) · [Machine-readable catalog](../data/catalog.jsonl)

Curated metadata. Each entry links its first-party evidence. Unknown facts are shown as —.

*Paper* lists reviewed `introduced_by`/`documented_by` relations with the record's year. *License* lists publisher declarations by scope (code, data, weights, document). *Evidence* links the reviewed first-party snapshot and its retrieval date.

**26 resources:** [Web (3)](#web) · [Desktop (10)](#desktop) · [Mobile (3)](#mobile) · [Cross-platform (10)](#cross-platform)

Resources tagged with environments from more than one family are listed under *Cross-platform*; their exact environments stay in the table.

## Web

All entries in this section: web.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [Gobii Platform](https://github.com/gobii-ai/gobii-platform) | — | code MIT | Self-hostable platform for always-on agents based on browser-use, adding headed browsers, persistent profiles, proxy-aware routing, schedules and event triggers. | [✓ 2026‑11‑06](https://raw.githubusercontent.com/gobii-ai/gobii-platform/c9929bf8ea59b4695b99dcab59aa6c97a09c5bdb/README.md) |
| [Playwright](https://github.com/microsoft/playwright) | — | code Apache-2.0 | Browser automation library used as an execution layer by agents. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/microsoft/playwright/HEAD/README.md) |
| [Steel Browser](https://github.com/steel-dev/steel-browser) | — | code Apache-2.0 | Open-source browser API managing Chrome sessions for agents, reachable through Puppeteer, Playwright or Selenium over CDP, with persisted cookies, proxy rotation, stealth and a session debugging UI. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/steel-dev/steel-browser/HEAD/README.md) |

[↑ Back to top](#infrastructure-catalog)

## Desktop

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [AgentDesk](https://github.com/agentsea/agentdesk) | desktop | — | code MIT | Desktop environments that AI agents control programmatically, run locally with Docker or remotely on Kubernetes, built on the agentd REST daemon and offering a coordinate-grid overlay for LMM input. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/agentsea/agentdesk/HEAD/README.md) |
| [AIOS](https://github.com/agiresearch/AIOS) | desktop | — | — | AIOS is an agent operating system whose computer-use architecture provides a virtual machine controller and MCP server for agents interacting with graphical computer environments. | [✓ 2026‑11‑06](https://raw.githubusercontent.com/agiresearch/AIOS/292d98f78c835499df18cdb6de6325bba1895862/README.md) |
| [Boxcar](https://github.com/Status-Labs/boxcar) | desktop, windows, linux | — | code MIT | Boxcar provisions disposable Windows 11 and Ubuntu desktop virtual-machine sandboxes for LLM computer-use agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/Status-Labs/boxcar/HEAD/README.md) |
| [Computer Use VM](https://github.com/ZimengXiong/computer-use-vm) | desktop, macos | — | code MIT | Provisions disposable, headless macOS virtual machines so computer-use agents can operate isolated desktops without window switching. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/ZimengXiong/computer-use-vm/HEAD/README.md) |
| [E2B Desktop](https://github.com/e2b-dev/desktop) | desktop, linux | — | code Apache-2.0 | Open-source, isolated Linux Xfce desktop sandboxes for computer-use agents, driven from Python or JavaScript SDKs with screen streaming, mouse, keyboard and window control, screenshots and shell. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/e2b-dev/desktop/HEAD/README.md) |
| [Lume](https://github.com/trycua/lume) | desktop, macos, linux | — | code MIT | Virtual machine management for local computer-use environments. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/trycua/lume/HEAD/README.md) |
| [Nut.js](https://github.com/nut-tree/nut.js) | desktop | — | — | Desktop automation library for keyboard, mouse, and screen interaction. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/nut-tree/nut.js/HEAD/README.md) |
| [PyAutoGUI](https://github.com/asweigart/pyautogui) | desktop | — | — | Cross-platform Python module for scripted mouse and keyboard control, message boxes and screenshots with on-screen image search, working on the primary monitor under Windows, macOS and Linux. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/asweigart/pyautogui/HEAD/README.md) |
| [Sandbox0](https://github.com/sandbox0-ai/sandbox0) | desktop, linux | — | code Apache-2.0 | Sandbox0 is an open-source cloud sandbox platform with persistent storage volumes and sub-second microVM/container resume for AI agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/sandbox0-ai/sandbox0/HEAD/README.md) |
| [ScienceBoard VMware environment](https://huggingface.co/OS-Copilot/ScienceBoard-Env) | linux, desktop | [2505.19897](https://arxiv.org/abs/2505.19897) (2025) | — | A prebuilt Ubuntu virtual-machine archive containing the software environment used for ScienceBoard scientific computer-use tasks. | [✓ 2026‑10‑17](https://huggingface.co/OS-Copilot/ScienceBoard-Env/raw/main/README.md) |

[↑ Back to top](#infrastructure-catalog)

## Mobile

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [AndroidEnv](https://github.com/google-deepmind/android_env) | android | [2105.13231](https://arxiv.org/abs/2105.13231) (2021) | code Apache-2.0 | Android device-control platform with screenshots, accessibility telemetry, input actions, and an optional reinforcement-learning task interface. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/google-deepmind/android_env/HEAD/README.md) |
| [Appium](https://github.com/appium/appium) | android, ios | — | code Apache-2.0 | Open-source WebDriver-based automation server for mobile, desktop and IoT apps, extended by per-platform drivers for iOS, Android, macOS and Windows, plugins, and clients in Java, Python, Ruby and C#. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/appium/appium/HEAD/README.md) |
| [Mobile Env](https://github.com/X-LANCE/Mobile-Env) | android | [2305.08144](https://arxiv.org/abs/2305.08144) (2023) | code Apache-2.0 | AndroidEnv-based platform for building GUI agent benchmarks and training agents, where task definition files emit instructions, rewards and episode ends from screen text, view hierarchy or log events. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/X-LANCE/Mobile-Env/HEAD/README.md) |

[↑ Back to top](#infrastructure-catalog)

## Cross-platform

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Agent Infra Sandbox](https://github.com/agent-infra/sandbox) | desktop, web | — | code Apache-2.0 | Sandbox environments supporting computer and browser interaction. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/agent-infra/sandbox/HEAD/README.md) |
| [BrowserOS / BrowserOS neo](https://github.com/browseros-ai/BrowserOS) | web, desktop, windows, macos, linux | — | code AGPL-3.0 | Chromium-based browser implementations for external agent control and built-in assistant workflows, with session visibility and replay facilities. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/browseros-ai/BrowserOS/HEAD/README.md) |
| [Computer Use (gVisor Cloud REPL)](https://github.com/r33drichards/computer-use) | desktop, web, linux | — | code Apache-2.0 | Provides a gVisor-isolated Linux desktop and Chromium container with persistent storage driven through a single JavaScript REPL MCP tool. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/r33drichards/computer-use/HEAD/README.md) |
| [Gloria](https://github.com/sh7vansh/gloria) | desktop, linux, web | — | code MIT | Remote Chromium workstation for AI agents and human operators exposed over Model Context Protocol and noVNC. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/sh7vansh/gloria/main/README.md) |
| [Gloria Headless](https://github.com/sh7vansh/gloria-headless) | desktop, linux, web | — | code MIT | Containerized headless Chromium environment with native Model Context Protocol integration for autonomous web agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/sh7vansh/gloria-headless/main/README.md) |
| [Harborage](https://github.com/vadym-iefremov/harborage) | web, desktop, linux | — | code MIT | On-demand pool manager providing isolated headless browser sessions for concurrent AI web agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/vadym-iefremov/harborage/main/README.md) |
| [SentinelDesk](https://github.com/sentineldesk/desktop) | desktop, linux, web | — | code Apache-2.0 | Collaborative Linux desktop streamed to the browser where humans and AI agents share a workspace. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/sentineldesk/desktop/main/README.md) |
| [Tailorec Browser Orchestrator](https://github.com/Tailorec/tailorec-browser-orch) | web, desktop, linux | — | — | Run-isolated browser orchestration service that converts webpages into semantic snapshots with stable element references. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/Tailorec/tailorec-browser-orch/HEAD/README.md) |
| [Universe legacy GUI interaction client](https://github.com/openai/universe) | web, desktop | — | code MIT | An archived Gym-compatible client that exposes screen observations and keyboard/mouse actions over VNC for remote application and browser environments, including the historical World of Bits integration. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/openai/universe/HEAD/README.rst) |
| [UseAgent](https://github.com/useagenthq/useagent) | desktop, linux, web | — | code AGPL-3.0 | Open-source cloud and local sandbox platform for running Claude Code, Codex, or OpenCode with a full desktop and browser. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/useagenthq/useagent/main/README.md) |

[↑ Back to top](#infrastructure-catalog)

Detailed notes and separate code/data/weights/document license declarations are in `data/catalog.jsonl`.
