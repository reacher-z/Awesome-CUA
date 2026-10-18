# Tool catalog

[Home](../README.md) · [Methodology](methodology.md) · [Machine-readable catalog](../data/catalog.jsonl)

Curated metadata, not a performance ranking. Each entry links its first-party evidence. Unknown facts are shown as —.

*Paper* lists reviewed `introduced_by`/`documented_by` relations with the record's year. *License* lists publisher declarations by scope (code, data, weights, document). *Evidence* links the reviewed first-party snapshot and its retrieval date.

**21 resources:** [Web (10)](#web) · [Desktop (1)](#desktop) · [Mobile (4)](#mobile) · [Cross-platform (4)](#cross-platform) · [Unspecified (2)](#unspecified)

Resources tagged with environments from more than one family are listed under *Cross-platform*; their exact environments stay in the table.

## Web

All entries in this section: web.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [Agent Browser Shield](https://github.com/pixiebrix/agent-browser-shield) | — | — | Browser extension for filtering potentially unsafe agent input. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/pixiebrix/agent-browser-shield/HEAD/README.md) |
| [agent-browser](https://github.com/vercel-labs/agent-browser) | — | code Apache-2.0 | A browser-automation command-line interface that exposes browser state and interaction commands for AI agents. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/vercel-labs/agent-browser/HEAD/README.md) |
| [Browser Use WebUI](https://github.com/browser-use/web-ui) | — | code MIT | A Gradio interface for configuring and running Browser Use agents, including persistent browser sessions and interaction recordings. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/browser-use/web-ui/HEAD/README.md) |
| [BrowserTrace](https://github.com/aaronlab/browsertrace) | — | code MIT | Local, cloud-free replay debugger that records each Browser Use step's screenshot, URL, action and model I/O as a timeline and reports the step at which a failed run diverges from a known-good one. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/aaronlab/browsertrace/HEAD/README.md) |
| [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) | — | code Apache-2.0 | MCP tools for browser control and inspection through Chrome DevTools. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/ChromeDevTools/chrome-devtools-mcp/HEAD/README.md) |
| [Playwright MCP](https://github.com/microsoft/playwright-mcp) | — | code Apache-2.0 | MCP server that lets LLM clients drive Playwright browsers through structured accessibility snapshots instead of screenshots, with opt-in vision, PDF and devtools capabilities. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/microsoft/playwright-mcp/HEAD/README.md) |
| [TAG attention-driven GUI grounding](https://github.com/HeimingX/TAG) | [2412.10840](https://arxiv.org/abs/2412.10840) (2024) | — | Grounding and evaluation code that aggregates a pretrained vision-language model’s attention maps to localize requested interface elements without fine-tuning. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/HeimingX/TAG/HEAD/README.md) |
| [Tarsier](https://github.com/reworkd/tarsier) | — | code MIT | Perception utilities for web agents that tag interactable elements with typed IDs an LLM can act on, and use OCR to render page screenshots as whitespace-structured text for models without vision. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/reworkd/tarsier/HEAD/README.md) |
| [Web-Shepherd inference and evaluation](https://github.com/kyle8581/Web-Shepherd) | — | — | Process-reward inference and benchmark-evaluation utilities that use task checklists to assess individual web-agent decisions. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/kyle8581/Web-Shepherd/HEAD/README.md) |
| [WebMarker](https://github.com/reidbarber/webmarker) | — | code MIT | A browser library that labels interactive elements and their boxes for visual prompting, preserving element mappings that automation code can use to execute selected actions. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/reidbarber/webmarker/HEAD/README.md) |

[↑ Back to top](#tool-catalog)

## Desktop

All entries in this section: desktop, macos, linux, windows.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [Sikuli legacy research implementation](https://github.com/sikuli/sikuli) | [Sikuli: Using GUI screenshots for search and automation](https://doi.org/10.1145/1622176.1622213) (2009), [GUI Testing Using Computer Vision](https://doi.org/10.1145/1753326.1753555) (2010) | code MIT | The original Sikuli source distribution combines screenshot targets with a Jython scripting library and IDE for visual GUI automation and testing. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/sikuli/sikuli/HEAD/docs/source/index.rst) |

[↑ Back to top](#tool-catalog)

## Mobile

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Mobile Harness](https://github.com/droidrun/mobile-harness) | android, ios | — | code MIT | Portable agent instructions and integration tooling for local or cloud phone control through mobilerun-core. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/droidrun/mobile-harness/HEAD/README.md) |
| [Mobile Next MCP](https://github.com/mobile-next/mobile-mcp) | android, ios | — | code Apache-2.0 | An MCP server exposing mobile accessibility snapshots, screenshots and device interactions across real devices, simulators and emulators. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/mobile-next/mobile-mcp/HEAD/README.md) |
| [Mobilerun Portal (formerly Droidrun Portal)](https://github.com/droidrun/mobilerun-portal) | android | — | code AGPL-3.0-or-later | An Android accessibility service that exposes UI-element inspection, device-control interfaces and screen feedback to mobile automation agents. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/droidrun/mobilerun-portal/HEAD/README.md) |
| [UI Defect Mocker](https://github.com/ZJU-ACES-ISE/UIDefectMocker) | android | — | code MIT | Synthesizes visual UI defects from mobile screenshots and Android layout metadata to support GUI-testing experiments. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/ZJU-ACES-ISE/UIDefectMocker/HEAD/README.md) |

[↑ Back to top](#tool-catalog)

## Cross-platform

| Resource | Environments | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- | --- |
| [Interceptor](https://github.com/Hacker-Valley-Media/Interceptor) | web, desktop, macos, windows, linux, ios | — | code Elastic-2.0 | CLI and MCP server that lets agents operate the user's signed-in Chrome, Brave or Safari, native apps via accessibility on macOS, Windows and Linux, and a physical iPhone through an XCUITest runner. | [✓ 2026‑10‑18](https://raw.githubusercontent.com/Hacker-Valley-Media/Interceptor/HEAD/README.md) |
| [OculiX (SikuliX continuation)](https://github.com/oculix-org/Oculix) | desktop, windows, macos, linux, android | — | code MIT | A maintained continuation of SikuliX that locates on-screen targets with image matching and OCR, drives desktop or Android interfaces, and exposes scripting and optional MCP interfaces. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/oculix-org/Oculix/HEAD/README.md) |
| [OmniParser](https://github.com/microsoft/OmniParser) | cross-platform | [2408.00203](https://arxiv.org/abs/2408.00203) (2024) | — | Screenshot parser that detects interactable regions and captions icons so vision-language models can ground actions, released as V1.5 and V2 weights alongside OmniTool for driving a Windows 11 VM. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/microsoft/OmniParser/HEAD/README.md) |
| [Windows-MCP](https://github.com/CursorTouch/Windows-MCP) | windows, desktop, web | — | code MIT | A Windows MCP bridge exposing application, window, keyboard and mouse operations plus native UI-state inspection for agents. | [✓ 2026‑10‑17](https://raw.githubusercontent.com/CursorTouch/Windows-MCP/HEAD/README.md) |

[↑ Back to top](#tool-catalog)

## Unspecified

All entries in this section: unspecified.

| Resource | Paper | License | Description | Evidence |
| --- | --- | --- | --- | --- |
| [AUITestAgent](https://github.com/bz-lab/AUITestAgent) | [2407.09018](https://arxiv.org/abs/2407.09018) (2024) | — | Generates mobile GUI interactions from natural-language test requirements and checks application behavior against those requirements. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/bz-lab/AUITestAgent/HEAD/README.md) |
| [Set of Mark](https://github.com/microsoft/SoM) | [2310.11441](https://arxiv.org/abs/2310.11441) (2023) | code MIT | Visual-prompting toolbox that labels image regions for multimodal reference and grounding, including GUI applications. | [✓ 2026‑10‑16](https://raw.githubusercontent.com/microsoft/SoM/HEAD/README.md) |

[↑ Back to top](#tool-catalog)

Detailed notes and separate code/data/weights license declarations are in `data/catalog.jsonl`.
