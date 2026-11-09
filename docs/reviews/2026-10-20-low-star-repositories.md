# Low-star repository source review: 20 October 2026

Six candidates were selected using dated GitHub identity and star observations.
Curation then used pinned primary documentation, relevant implementation files
and an independent second source review. No repository code, models, uploaders
or device tests were executed.

| Resource | Reviewed contribution | Scope retained |
| --- | --- | --- |
| [Web Context Bench (Python)](https://github.com/charlypoly/web-context-bench-python/tree/58d604bfaaac60ad42f02013f53f9fb301c1dcda) | Compares browser representations using static-page reading, target selection and token accounting. | This measures answer/target correctness on fixed observations. It does not measure live multi-step agent completion. Third-party snapshot redistribution remains unresolved. |
| [WinDOM code](https://github.com/ChenghengLi/WinDOM/tree/ab52acffe2003fd0c98943a542b4114ef929de0d) | GUI-grounding training and evaluation code, including distillation and point-in-box scoring. | The Windows-style environment is a web simulation. The final corpus harvester is absent, and evaluator prompt modes must accompany any score comparison. Its explicit paper link is recorded separately. |
| [GUI Grounding Evaluation Harness](https://github.com/PatrickStarL/gui-grounding-eval/tree/d92b059caa0e0acf8db76f2164dd7be2617ccc72) | Coordinate conversion, prompt/crop comparisons and per-sample grounding metrics. | This is an independent evaluation tool using ScreenSpot-Pro. OS support and code, data and weight licenses remain unestablished in this review. |
| [Yunkai](https://github.com/solplum/yunkai/tree/2aa6cd83165bfc201b0128c250e80892895d63af) | Android accessibility observations and phone actions within a documented model-driven confirmation flow. | The HarmonyOS accessibility extension remains an initial scaffold. An external HDC test driver does not establish feature parity. A configured model endpoint is required. |
| [Activity Recorder](https://github.com/anikasomaia/local-activity-recorder/tree/967cea087bf6496b3b82743fb96770fa29f8e203) | Windows tray-based screenshot and input-event collection. | Manual upload uses a preset third-party demonstration endpoint. Successful uploads move local files into subfolders; automatic expiry was not established. Sensitive-app filters are prospective and code permission remains unknown. |
| [Mobster engine](https://github.com/RadishSoftware/mobster/tree/738cecdd3eacb9df88d48efb9efa53507bb4aeb4) | An iOS observation/action engine using WebDriverAgent. | The separate Mac product includes modules outside this repository. The reference example requires a WDA runner and model service. Evaluation subsets and dated results are separate populations. |

Complete inspected MIT texts support four repository-code declarations:
Web Context Bench, WinDOM, Yunkai and Mobster. Other license scopes remain
unknown. No dataset or model license was inferred from a repository license.

Web Context Bench also receives a source-backed `benchmark_protocol`, covering
representation inputs, READ/ACT output forms, deterministic scoring and
comparison conditions. Counts remain unrecorded. Its `offline` setting refers
to fixed local-page observations and does not imply API-free execution.

Two Activity Recorder source files were reconstructed from a retained commit
diff and matched by Git blob SHA-1 against their current root-tree entries.
Their supporting receipts identify the actual commit/tree responses; no
unperformed raw-file request is claimed.

The six source-reviewed resources remain distinct from the candidate metadata
pool. Their existing numeric identities were already represented in discovery,
so approving them does not add six new identities to the cross-source scan
total. Existing catalog records, paper bibliography and scope decisions are
preserved.
