# Candidate query vocabulary review: 20 October 2026

Eight exact GitHub topic spellings are added to the existing nine discovery
queries. Each has a retained official GitHub API observation on an already
reviewed CUA repository identity. The examples establish use of the spelling;
they do not approve other repositories with the same tag.

| Additional query topic | Retained example | Direct interface connection |
| --- | --- | --- |
| `computer-use-agent` | [Agent-S](https://github.com/simular-ai/Agent-S), repository ID 870189331 | Computer-use agent framework |
| `computer-use-agents` | [ScaleCUA](https://github.com/OpenGVLab/ScaleCUA), ID 1053524611 | Cross-platform computer-use models |
| `gui-grounding` | [UI-Ins](https://github.com/alibaba/UI-Ins), ID 1085411982 | Locating interface elements |
| `browser-use` | [Nanobrowser](https://github.com/nanobrowser/nanobrowser), ID 910418754 | Operating a browser through an agent |
| `web-agent` | [Nanobrowser](https://github.com/nanobrowser/nanobrowser), ID 910418754 | Singular browser-agent terminology |
| `web-agents` | [UGround](https://github.com/OSU-NLP-Group/UGround), ID 837299429 | Visual grounding for GUI agents |
| `desktop-agent` | [WindowsAgentArena](https://github.com/microsoft/WindowsAgentArena), ID 835317697 | Evaluating agents in desktop software |
| `mobile-agent` | [MobileUse](https://github.com/MadeAgents/mobile-use), ID 939915733 | Operating Android GUIs |

The decision uses the observation snapshot at source commit
[`e291b8723b2893f1b7f3a07a10282b9de29cbe25`](https://github.com/reacher-z/Awesome-CUA/tree/e291b8723b2893f1b7f3a07a10282b9de29cbe25).
Its `github-candidates.jsonl` SHA-256 is
`df5d5b1ca5452cfd1d536870e99099d4b502dbcfedd92880c1c031db94e68ebc`.
The examples' official response bytes were reread from the retained cache and
checked against these receipts:

| Examples | Response SHA-256 | Retrieved at (UTC) |
| --- | --- | --- |
| Agent-S, ScaleCUA, UI-Ins, UGround | `54fc8ade91cb7ca7da7afe8afaf18988f640b30d7039b19702f90624ae9dffcf` | 2026-10-19 19:10:32 |
| Nanobrowser | `0058f21d673aea8d1fd66447162548d23fed8bc295d017a1de5460d9e3904925` | 2026-10-20 02:36:44 |
| WindowsAgentArena | `24cc7b171344e491976f0c77cea48e0e025b0765fc02a8e292ea99324810726f` | 2026-10-18 13:11:38 |
| MobileUse | `0ba9cb9c4839b003a8aead46322dfad580554b0a08ec589170341f33e5cc1718` | 2026-10-20 09:19:09 |

The matching observation rows retain the exact API URLs, response sizes and
timestamps. No new network request was made for this decision. The original
offline proposal used an earlier 8,555-repository snapshot; the reviewed source
commit contains 8,576. Neither population estimates how many additional
repositories these queries will discover. The sample was already selected by
the old queries, and topic groups overlap.

The selected terms name computer, browser, desktop or mobile agents, or GUI
grounding. Generic AI, agent, automation, scraping and framework tags are not
added. More weakly supported terms such as `ui-grounding`, `gui-world-model` and
`screen-understanding` remain unscheduled. Even the selected terms can retrieve
wrappers, catalogs, API-only tools or unrelated uses of “mobile agent”; every
result remains `candidate` / `relevance_pending` until its own source review.
The decision does not infer licenses, released artifacts or independent projects.

Each query keeps `is:public fork:false`, numeric-ID deduplication and the existing
transport restrictions. The candidate phase remains limited to 30 attempts and
220 seconds, within the shared 180-attempt/600-second network round. New topics
receive additive historical backfills, while incomplete older queries and all
their receipts remain available for repair. A bounded live pilot can measure
actual progress after review; this vocabulary change makes no discovery-yield
or global-completeness claim.
