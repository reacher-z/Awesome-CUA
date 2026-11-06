# Candidate query vocabulary review: 5 November 2026

Eleven exact GitHub topic spellings are added to the seventeen existing
candidate queries. They come from a coverage comparison against 27 outside
reference sources (awesome lists, survey bibliographies, leaderboards, Hub
collections, arXiv queries and GitHub topics). The comparison found in-scope
repositories that these spellings tag and that no configured topic or source
had reached.

| Additional query topic | Repositories with the tag | Reviewed as in scope | Retained example on a reviewed CUA identity |
| --- | ---: | ---: | --- |
| `cua` | 101 | 82 | [Cua](https://github.com/trycua/cua), repository ID 925270205; [Agent-S](https://github.com/simular-ai/Agent-S), ID 870189331 |
| `computer-control` | 43 | 27 | [Cradle](https://github.com/BAAI-Agents/Cradle), ID 766445602 (topic page only) |
| `computer-agent` | 9 | 7 | none |
| `os-agent` | 7 | 4 | none |
| `os-agents` | 1 | 1 | none |
| `mobile-agents` | 23 | 15 | [Mobile-Agent](https://github.com/X-PLUG/MobileAgent), ID 748674684 (topic page only) |
| `android-agent` | 25 | 13 | [MobileUse](https://github.com/MadeAgents/mobile-use), ID 939915733 |
| `phone-use` | 14 | 12 | [Midscene](https://github.com/web-infra-dev/midscene), ID 832452447 |
| `mobile-use` | 11 | 10 | [UI-Venus](https://github.com/inclusionAI/UI-Venus), ID 1038544352; [MAI-UI](https://github.com/Tongyi-MAI/MAI-UI), ID 1116665379 |
| `screen-understanding` | 10 | 7 | none |
| `ui-agent` | 3 | 3 | none |

"Repositories with the tag" is the `total_count` of one public GitHub search
per topic (`topic:<name>`, sorted by stars, two pages of 100), retrieved on
5 November 2026 between 18:37 and 18:38 UTC; every returned repository was read. "Reviewed as in scope" counts the
returned repositories whose name, description and topics describe an agent or
tool that observes and operates a GUI, browser, desktop or phone, or a GUI
grounding resource. Those are AI-assisted relevance readings of publisher
metadata, not source reviews. They measure the precision of a tag, not the
relevance of any one repository.

The examples marked with an ID were reread from the observation snapshot at
source commit
[`094d8e1b689c037b863e4cdca45ffc2f8c262c52`](https://github.com/reacher-z/Awesome-CUA/tree/094d8e1b689c037b863e4cdca45ffc2f8c262c52),
whose `github-candidates.jsonl` SHA-256 is
`ae8f5ffec93dd09d676db751ddf754023a14f23325bf81b2fe604faf981dd9dc`. Each
row's `github_topics` contains the added spelling:

| Examples | Response SHA-256 | Retrieved at (UTC) |
| --- | --- | --- |
| Cua, Agent-S | `810c7d7209d7af6ff5506d38f09ccef04898f826074ec6fa4e730d94917dfbec` | 2026-10-20 11:16:06 |
| MobileUse | `01f97a863952373bd10a1f849d79706344be63f5774fe7e0cfe9ba774e41d213` | 2026-10-20 11:06:00 |
| Midscene | `93971252aabff6a70c1991451b0a6138fbf504f75234d57d8af786a31e4390bc` | 2026-10-20 11:52:28 |
| UI-Venus, MAI-UI | `f1f7bd7ea99b82d515f6f998e595f40083313ce8ea302fa634ac9ed19faa0bf7` | 2026-10-20 11:16:20 |

Cradle and Mobile-Agent appear only in the 5 November topic pages (response
SHA-256 `4f98a98dbe4e7c7d617f7077cd93016ac1b5090e0499fcd0f0044cb0e4b72d3f` for
`computer-control` and
`cf4863acc1aae2954f542a282dbdba39dff4bce2d516a55367e36ab3978ceb4b` for
`mobile-agents`). These pages are not retained in this repository. The five
spellings without an example have small populations. Their measured share in
scope is the whole basis for scheduling them, and each costs one search page
per backfill.

`cua` also tags repositories about IBM Common User Access keyboard conventions.
`android-agent` and `mobile-agents` include on-device assistants that do not
operate other applications. `computer-control` includes remote-control and
voice tools. The previous review's exclusions stay in force: generic AI, agent,
automation, scraping and framework tags are not added. `phone-agent` (12 of 44
in scope), `web-navigation` (8 of 31) and `ui-agents` (0 of 2) tag mostly voice
telephony agents, site menus and unrelated projects and remain unscheduled.

Each query keeps `is:public fork:false`, numeric-ID deduplication and the
existing transport restrictions. New topics receive additive historical
backfills inside the unchanged 30-attempt, 220-second candidate phase. Every
result remains `candidate` / `relevance_pending` until its own source review.
This vocabulary change makes no discovery-yield or completeness claim, and it
infers no licenses, released artifacts or independent projects.
