# Infrastructure catalog

[Home](../README.md) · [Methodology](methodology.md) · [Machine-readable catalog](../data/catalog.jsonl)

Curated metadata. Each entry links its first-party evidence. Unknown facts are shown as —.

*Paper* lists reviewed `introduced_by`/`documented_by` relations with the record's year. *License* lists publisher declarations by scope (code, data, weights, document). *Evidence* links the reviewed first-party snapshot and its retrieval date.

**26 resources:** [Web (4)](#web) · [Desktop (9)](#desktop) · [Mobile (4)](#mobile) · [Cross-platform (9)](#cross-platform)

Resources tagged with environments from more than one family are listed under *Cross-platform*; their exact environments stay in the table.

## Web

All entries in this section: web.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [browser-gateway](https://github.com/browser-gateway/browser-gateway) | — | code MIT | browser-gateway is an open control plane and router across cloud browser providers with failover, persistent profiles, session replay, and MCP. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/browser-gateway/browser-gateway/HEAD/README.md) |
| [Gobii Platform](https://github.com/gobii-ai/gobii-platform) | — | code MIT | Self-hostable platform for always-on agents based on browser-use, adding headed browsers, persistent profiles, proxy-aware routing, schedules and event triggers. | [✓ 2026‑11‑06](https://raw.githubusercontent.com/gobii-ai/gobii-platform/c9929bf8ea59b4695b99dcab59aa6c97a09c5bdb/README.md) |
| [Playwright](https://github.com/microsoft/playwright) | — | code Apache-2.0 | Browser automation library used as an execution layer by agents. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/microsoft/playwright/HEAD/README.md) |
| [Steel Browser](https://github.com/steel-dev/steel-browser) | — | code Apache-2.0 | Open-source browser API managing Chrome sessions for agents, reachable through Puppeteer, Playwright or Selenium over CDP, with persisted cookies, proxy rotation, stealth and a session debugging UI. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/steel-dev/steel-browser/HEAD/README.md) |

[↑ Back to top](#infrastructure-catalog)

## Desktop

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [AgentDesk](https://github.com/agentsea/agentdesk) | desktop | — | code MIT | Desktop environments that AI agents control programmatically, run locally with Docker or remotely on Kubernetes, built on the agentd REST daemon and offering a coordinate-grid overlay for LMM input. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/agentsea/agentdesk/HEAD/README.md) |
| [AIOS](https://github.com/agiresearch/AIOS) | desktop | — | — | AIOS is an agent operating system whose computer-use architecture provides a virtual machine controller and MCP server for agents interacting with graphical computer environments. | [✓ 2026‑11‑06](https://raw.githubusercontent.com/agiresearch/AIOS/292d98f78c835499df18cdb6de6325bba1895862/README.md) |
| [Browser Use macOS Harness](https://github.com/browser-use/macos-harness) | desktop, macos | — | code MIT | Official Browser Use harness for provisioning and driving isolated macOS virtual machines and desktop sessions. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/browser-use/macos-harness/main/README.md) |
| [E2B Desktop](https://github.com/e2b-dev/desktop) | desktop, linux | — | code Apache-2.0 | Open-source, isolated Linux Xfce desktop sandboxes for computer-use agents, driven from Python or JavaScript SDKs with screen streaming, mouse, keyboard and window control, screenshots and shell. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/e2b-dev/desktop/HEAD/README.md) |
| [Lume](https://github.com/trycua/lume) | desktop, macos, linux | — | code MIT | Virtual machine management for local computer-use environments. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/trycua/lume/HEAD/README.md) |
| [Neo Lab](https://github.com/belarusian/neo-lab) | desktop, macos | — | code MIT | Neo Lab is a macOS computer-use sandbox for recording demonstrations, replaying skills, and testing GUI automation plans. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/belarusian/neo-lab/HEAD/README.md) |
| [Nut.js](https://github.com/nut-tree/nut.js) | desktop | — | — | Desktop automation library for keyboard, mouse, and screen interaction. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/nut-tree/nut.js/HEAD/README.md) |
| [PyAutoGUI](https://github.com/asweigart/pyautogui) | desktop | — | — | Cross-platform Python module for scripted mouse and keyboard control, message boxes and screenshots with on-screen image search, working on the primary monitor under Windows, macOS and Linux. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/asweigart/pyautogui/HEAD/README.md) |
| [ScienceBoard VMware environment](https://huggingface.co/OS-Copilot/ScienceBoard-Env) | linux, desktop | [2505.19897](https://arxiv.org/abs/2505.19897) (2025) | — | A prebuilt Ubuntu virtual-machine archive containing the software environment used for ScienceBoard scientific computer-use tasks. | [✓ 2026‑10‑17](https://huggingface.co/OS-Copilot/ScienceBoard-Env/raw/main/README.md) |

[↑ Back to top](#infrastructure-catalog)

## Mobile

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [AndroidEnv](https://github.com/google-deepmind/android_env) | android | [2105.13231](https://arxiv.org/abs/2105.13231) (2021) | code Apache-2.0 | Android device-control platform with screenshots, accessibility telemetry, input actions, and an optional reinforcement-learning task interface. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/google-deepmind/android_env/HEAD/README.md) |
| [Appium](https://github.com/appium/appium) | android, ios | — | code Apache-2.0 | Open-source WebDriver-based automation server for mobile, desktop and IoT apps, extended by per-platform drivers for iOS, Android, macOS and Windows, plugins, and clients in Java, Python, Ruby and C#. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/appium/appium/HEAD/README.md) |
| [DroidFleet](https://github.com/c00l-k1D/DroidFleet) | android | — | code MIT | Open-source Android device fleet management and orchestration platform for mobile automation and testing. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/c00l-k1D/DroidFleet/main/README.md) |
| [Mobile Env](https://github.com/X-LANCE/Mobile-Env) | android | [2305.08144](https://arxiv.org/abs/2305.08144) (2023) | code Apache-2.0 | AndroidEnv-based platform for building GUI agent benchmarks and training agents, where task definition files emit instructions, rewards and episode ends from screen text, view hierarchy or log events. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/X-LANCE/Mobile-Env/HEAD/README.md) |

[↑ Back to top](#infrastructure-catalog)

## Cross-platform

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Aegis (Hardened Computer-Use Sandbox)](https://github.com/ArihantDeva/Aegis) | desktop, linux, web | — | code MIT | Aegis is an off-screen, capability-dropped Docker browser and desktop sandbox for isolating computer-use agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/ArihantDeva/Aegis/HEAD/README.md) |
| [Agent Infra Sandbox](https://github.com/agent-infra/sandbox) | desktop, web | — | code Apache-2.0 | Sandbox environments supporting computer and browser interaction. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/agent-infra/sandbox/HEAD/README.md) |
| [BrowserOS / BrowserOS neo](https://github.com/browseros-ai/BrowserOS) | web, desktop, windows, macos, linux | — | code AGPL-3.0 | Chromium-based browser implementations for external agent control and built-in assistant workflows, with session visibility and replay facilities. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/browseros-ai/BrowserOS/HEAD/README.md) |
| [BryantVanOrden OpenAgentFleet](https://github.com/BryantVanOrden/OpenAgentFleet) | desktop, linux, web | — | code MIT | Self-hosted fleet orchestrator provisioning sandboxed Linux desktop containers for autonomous computer-use agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/BryantVanOrden/OpenAgentFleet/master/README.md) |
| [Celesto](https://github.com/CelestoAI/celesto) | desktop, linux, web | — | code Apache-2.0 | Celesto provisions secure, persistent virtual desktop computers and browser sandboxes for AI agents. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/CelestoAI/celesto/HEAD/README.md) |
| [DeskSwarm](https://github.com/ahmedvnabil/deskswarm) | desktop, linux, web | — | code MIT | Self-hosted fleet manager for provisioning and dispatching natural-language tasks across parallel XFCE Linux desktop sandboxes. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/ahmedvnabil/deskswarm/HEAD/README.md) |
| [modal-computer-use](https://github.com/ashtonchew/modal-computer-use) | desktop, linux, web | — | code MIT | Provides daemon-first computer-use primitives for provisioning and controlling GUI desktops inside Modal cloud sandboxes. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/ashtonchew/modal-computer-use/HEAD/README.md) |
| [QuickDesk](https://github.com/barry-ran/QuickDesk) | cross-platform, desktop, windows, macos, linux | — | code MIT | QuickDesk is an AI-native remote desktop client and host with a built-in MCP server for streaming screens and controlling remote computers. | [✓ 2026‑11‑04](https://raw.githubusercontent.com/barry-ran/QuickDesk/HEAD/README.md) |
| [Universe legacy GUI interaction client](https://github.com/openai/universe) | web, desktop | — | code MIT | An archived Gym-compatible client that exposes screen observations and keyboard/mouse actions over VNC for remote application and browser environments, including the historical World of Bits integration. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/openai/universe/HEAD/README.rst) |

[↑ Back to top](#infrastructure-catalog)

Detailed notes and separate code/data/weights/document license declarations are in `data/catalog.jsonl`.
