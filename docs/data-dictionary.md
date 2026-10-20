# Data dictionary

The executable contract is [resource.schema.json](../schemas/resource.schema.json). It checks each record on its own, including the rules for curated records and kind-specific `details`; `catalog.py validate` and `build` also enforce rules that need other fields, other records or `data/topics.json`, such as canonical URL identities, the topic vocabulary, relation targets and evidence receipts. All text files are UTF-8. JSONL has one resource per line; file ordering is by stable ID.

| Field | Meaning |
| --- | --- |
| `id` | Stable resource identity; prefixes distinguish arXiv, repositories, URLs, components, and publishers. An `arxiv:`, `github:` or `url:` ID must be the canonical identity of `url`, and an `arxiv:` ID must equal `identifiers.arxiv`; editors assign `component:` and `organization:` IDs, whose URLs resolve elsewhere |
| `name`, `aliases` | Display name and explicitly reviewed alternative names; former GitHub and Hugging Face names recorded in `repository-aliases.json` are added here with their identity receipts |
| `kind` | Primary resource type; model families and checkpoints are distinguished by details/relations |
| `url` | Primary landing page; not necessarily a direct binary download |
| `scope` | `core`, `adjacent`, or `relevance_pending` |
| `review_status` | `curated` or `metadata_verified`; candidates live outside the catalog |
| `environments` | Reviewed platform facets, following the [environment facet rules](#environment-facets); `cross-platform` is not a claim of support for every OS |
| `topics` | Editorial topic facets from the [topic vocabulary](#topic-vocabulary); empty for unreviewed bibliography entries |
| `summary` | Original concise annotation; null for metadata-only entries |
| `published_at`, `updated_at` | Exact calendar dates where established, otherwise null; a known year/month remains in `details.publication.date_parts` |
| `authors`, `identifiers` | Official bibliographic attribution and IDs |
| `links` | Typed links, starting with a primary or paper link |
| `relations` | Explicit semantic assertions: introduced by, documented by, published by, component of, variant of, etc. |
| `licenses` | Four separate nullable declarations: code, data, weights, document |
| `evidence` | Primary source URL, retrieval time in UTC, response digest, method, supported fields |
| `last_verified_at` | Time of the primary identity/content check; not a promise of current runtime availability |
| `details` | Kind-specific facts, with unknown quantities preserved as null; see [kind-specific details](#kind-specific-details) |
| `notes` | Renames, historical context, and material limitations |

## Kind-specific details

The schema checks `dataset_profile`, `benchmark_protocol`, `leaderboard_url`, `arxiv_snapshot` and `publication` and accepts any other key, so this table lists every `details` key that catalog records use. Origins:

- **Editorial**: the `details` object of an [editorial input](editorial-input.md), checked against its retained receipts.
- **Hub API** and **Dataverse API**: extracted by `catalog.py enrich` from the record's primary Hugging Face or Harvard Dataverse API receipt. An extracted value replaces an editorial value under the same key.
- **License review**: `catalog.py build` copies each `reviewed_licenses` decision's reason and evidence URLs here; the value itself goes in `licenses`.
- **Bibliography**: copied from the retained arXiv archive (`papers.jsonl`) or from publication observations (`publications.jsonl`).

| Key | Kinds | Meaning | Origin |
| --- | --- | --- | --- |
| `arxiv_snapshot` | paper, survey | Version, first-submission and version timestamps, and abstract digest from the retained arXiv Atom entry; see [paper versions and revision proposals](methodology.md#paper-versions-and-revision-proposals) | Bibliography (`papers.jsonl`) |
| `publication` | paper, survey | Publication edition: title, literal authors, type, venue, publisher, DOI and `date_parts`; see `details.publication` below | Bibliography (`publications.jsonl`) |
| `dataset_profile` | dataset | Supervision, modalities, formats, splits, notes, evidence URLs and `counts`; see [dataset and benchmark specifications](specifications.md) | Editorial |
| `benchmark_protocol` | benchmark | Focus, setting, observations, actions, evaluation, notes, evidence URLs and `counts`; see [dataset and benchmark specifications](specifications.md) | Editorial |
| `sample_count` | dataset | Number of samples, in `sample_unit` | Editorial (legacy) |
| `sample_unit` | dataset | What `sample_count` counts, such as `episodes` or `screen summaries` | Editorial (legacy) |
| `example_count` | dataset | Publisher-stated number of examples, a different unit from `sample_unit` | Editorial |
| `screen_count` | dataset | Number of distinct UI screens the samples refer to | Editorial |
| `reported_scale` | dataset | One publisher-stated size as `{value, unit, comparison}`; `comparison` (`approximately`, `>`) keeps the source's precision | Editorial |
| `task_count` | benchmark | Number of tasks, in `task_unit` when given | Editorial (legacy) |
| `task_unit` | benchmark | What `task_count` counts, such as `parameterized task definitions` | Editorial (legacy) |
| `metrics` | benchmark | Metric names the publisher reports, such as `task success` | Editorial (legacy) |
| `evaluation_type` | benchmark | How results are judged, such as `programmatic state checks` or `rubric-based` | Editorial (legacy) |
| `leaderboard_url` | benchmark | HTTPS address of the official leaderboard that the reviewed primary source links; the benchmark table links it after the name | Editorial |
| `modalities` | benchmark, dataset, model | Data modalities, such as `screenshot` or `instruction` | Hub API (`modality:` tags), or editorial |
| `languages` | benchmark, dataset, model | Natural-language codes, such as `en` | Hub API (card `language`), or editorial |
| `download_url` | benchmark, dataset, infrastructure, model | Download landing page, not a direct file; the Hub API sets the repository's file tree | Hub API, or editorial |
| `hub_id` | benchmark, dataset, infrastructure, model | Hugging Face repository ID as the API reports it | Hub API, or editorial |
| `gated` | benchmark, dataset, infrastructure, model | Hub access gate: `false`, `"auto"` (approved automatically) or `"manual"` (approved by the publisher) | Hub API, or editorial |
| `disabled` | benchmark, dataset, infrastructure, model | Whether Hugging Face has disabled the repository | Hub API, or editorial |
| `size_category_reported` | benchmark, dataset, model | Hub size band, such as `10K<n<100K`, or null; it can count files, so it is never a sample count | Hub API |
| `dataverse` | dataset | Dataverse publisher, persistent URL, publication date, version number, minor number and state, release time, verbatim license object, and file count | Dataverse API |
| `license_review` | agent, benchmark, dataset, framework, infrastructure, model, tool | Per license slot, the `reason` and `evidence_urls` of a reviewed license decision | License review |
| `license_name` | dataset, model | License the publisher names without an SPDX identifier, such as `qwen-research` | Editorial |
| `license_conflict` | framework | Conflicting license declarations that remain unresolved | Editorial |
| `license_components_note` | framework, tool | Component or dependency notices that differ from the root project license | Editorial |
| `artifact_type` | infrastructure, model | What the artifact is, such as `model-checkpoint` or `Ubuntu VMware image`; family relations keep a checkpoint from counting as an independent project | Editorial |
| `base_model` | model | Hub ID of the model a checkpoint was trained from | Editorial |
| `architecture` | model | Architecture class in the model configuration, such as `LlamaForCausalLM` | Editorial |
| `parameter_label` | model | Parameter size as the publisher labels it, such as `8B` | Editorial |
| `training_data_note` | model | What the publisher states about training data | Editorial |
| `listed_weight_files` | model | Weight file names in the inspected Hub manifest | Editorial |
| `artifact_inspection` | model | How far the artifact was inspected, such as the file manifest only | Editorial |
| `hub_revision` | benchmark, dataset, model | Hub commit for the inspected release metadata or files; for checkpoints, the manifest that gave `listed_weight_files` | Editorial |
| `release_revision` | benchmark, dataset, model | Hub commit of the inspected release | Editorial |
| `repository_revision` | agent, benchmark, dataset, framework, infrastructure, tool | Git commit of the inspected source tree | Editorial |
| `repository_id` | framework | Numeric repository identity from the retained official GitHub API response; a fork has its own ID, and a matching name or file tree does not establish a rename | Editorial |
| `repository_tree_sha` | agent, benchmark, framework | Git tree object SHA from the inspected repository file listing; distinct from a commit SHA | Editorial |
| `repository_url` | agent, benchmark, dataset, framework, model | Related implementation repository or component URL; this link alone does not establish a license or a separate resource identity | Editorial |
| `release_tag` | agent, benchmark, framework, infrastructure, tool | Inspected release tag, such as `v0.8.8` | Editorial |
| `package_version` | agent, tool | Inspected package version, such as an npm release | Editorial |
| `dataset_release` | benchmark | DOI of a separately published data release | Editorial |
| `component_path` | agent, framework | Path of a component record inside its repository | Editorial |
| `availability` | agent, benchmark, dataset, framework, infrastructure, model, product, tool | What is publicly released and what is missing, such as source without checkpoints | Editorial |
| `access` | dataset, product | How access is obtained, such as `publisher-managed` | Editorial |
| `pricing_url` | product | Official pricing page, or null when not established | Editorial |
| `maintenance_status` | infrastructure, tool | Publisher-stated status, such as `archived and deprecated` | Editorial |
| `evaluation_caution` | framework | Evaluation behaviour that can distort reported results | Editorial |
| `platform_constraints` | framework | Map from an environment key to a stated support limit | Editorial |

The flat `sample_count`, `sample_unit`, `task_count`, `task_unit`, `metrics` and `evaluation_type` keys are legacy editorial fields, superseded by the profiles: a record has them only where an editor set them, which few records do, and the build adds no null or empty placeholders. Add new counts, units and evaluation methods to the profile instead. The authoritative quantities are the `counts` in `dataset_profile` and `benchmark_protocol`, where each count carries its own unit, precision qualifier, population, basis and evidence URL. A flat count is a single editorial figure without that context; when both exist, use the profile. Counts of episodes, actions, screenshots, tasks, and instructions are different units and are never summed.

## Environment facets

`environments` lists the platforms that the reviewed primary source names for the resource. Facets overlap. `catalog.py validate` and `build` reject a record that breaks these rules.

| Facet | Rule |
| --- | --- |
| `web` | Websites or web applications operated through a browser. A browser-hosted phone simulation is `web`, the surface the agent operates, and its notes say so |
| `desktop` | Desktop operating systems. `windows`, `macos` and `linux` refine it and are always listed with `desktop`; `desktop` alone means the source names no particular OS |
| `android`, `ios`, `harmonyos` | Listed only when the source names that operating system. Mobile work whose source names none stays `unspecified`; its `mobile-navigation` topic carries the domain, so an Android or iOS filter does not include it |
| `cross-platform` | The source presents the resource as spanning several platform families or as platform-independent. It is additive: platforms the source names are listed beside it |
| `unspecified` | No platform is asserted: the record awaits review, or the reviewed source names no platform. It is never combined with another facet |

A `web-navigation` topic requires `web` or `cross-platform`. A `mobile-navigation` topic cannot rest on desktop facets alone: it needs `android`, `ios`, `harmonyos`, `cross-platform`, `web` for a browser-hosted simulation, or `unspecified`.

## Topic vocabulary

`data/topics.json` is the only list of topic keys. It gives each key its English and Chinese label and a one-line definition. `catalog.py validate` and `build` reject a catalog record or `editorial.json` entry that uses any other key. The Markdown topic hubs, the website and its static topic pages all take their labels from this file. To add or rename a topic, edit the file and run `catalog.py build`, which regenerates the table below.

<!-- TOPICS:START -->
| Topic | English label | Chinese label | Meaning |
| --- | --- | --- | --- |
| `action-prediction` | Action prediction | 动作预测 | Predicting the next UI action or action sequence from an instruction and the current screen. |
| `automation` | Automation | 自动化 | Automating repetitive GUI tasks with scripts, programs, or agents. |
| `cross-app` | Cross-app | 跨应用 | Tasks that carry information or control across several applications or websites. |
| `data-generation` | Data generation | 数据生成 | Collecting, synthesizing, or annotating screens, instructions, and trajectories for training or evaluation. |
| `efficiency` | Efficiency | 效率 | Reducing the latency, tokens, steps, or compute an agent needs to perceive, plan, or act. |
| `evaluation` | Evaluation | 评测 | Benchmarks, metrics, and evaluation methods for agents and their components. |
| `grounding` | GUI grounding | GUI 定位 | Locating the on-screen element or coordinates that an instruction refers to. |
| `history` | Historical | 历史 | Archived, legacy, or discontinued resources kept for historical context. |
| `human-in-the-loop` | Human in the loop | 人机协作 | Agents that ask people, learn from them, or are corrected by them during a task. |
| `imitation-learning` | Imitation learning | 模仿学习 | Learning policies from human or synthetic demonstrations. |
| `industry` | Industry | 产业 | Companies, commercial deployments, and enterprise or industrial application domains. |
| `interaction-history` | Interaction history | 交互历史 | Using earlier screens, actions, or trajectories as context for the next decision. |
| `long-horizon` | Long-horizon tasks | 长任务 | Tasks that need many dependent steps, subgoals, or long-term planning. |
| `memory` | Memory | 记忆 | Storing and retrieving experience, app knowledge, or skills across steps or tasks. |
| `mobile-navigation` | Mobile navigation | 手机操作 | Operating smartphone and tablet apps. |
| `observability` | Observability | 可观测性 | Inspecting agent runs through traces, intermediate progress, failure analysis, and diagnostics. |
| `planning` | Planning | 规划 | Decomposing goals into subtasks and choosing action sequences. |
| `recording` | Recording | 录制 | Capturing human screen sessions, input events, or interaction traces. |
| `reinforcement-learning` | Reinforcement learning | 强化学习 | Training agents from rewards with online or offline reinforcement learning. |
| `reward-models` | Reward models | 奖励模型 | Models or signals that score actions, steps, or outcomes for training or guidance. |
| `robustness` | Robustness | 鲁棒性 | Reliability under perturbations, distribution shift, errors, or changing interfaces. |
| `safety-security` | Safety & security | 安全与防护 | Attacks, defenses, privacy, policy compliance, and the risks of agent actions. |
| `sandbox` | Sandboxes | 沙箱 | Isolated, reproducible environments such as virtual machines, emulators, and browsers for running agents. |
| `science` | Scientific workflows | 科学工作流 | Agents for scientific, engineering, and data-science software. |
| `screen-understanding` | Screen understanding | 界面理解 | Perceiving and describing interface layouts, elements, text, and structure. |
| `self-reflection` | Self-reflection | 自我反思 | Agents that critique, verify, or revise their own actions and plans. |
| `state-tracking` | State tracking | 状态追踪 | Estimating and monitoring interface or task state, including whether an action took effect. |
| `survey` | Survey | 综述 | Literature surveys and overviews of the field. |
| `tool-integration` | Tool integration | 工具集成 | Combining GUI actions with APIs, code, terminals, or other tools. |
| `training-free` | Training-free methods | 无需训练的方法 | Improving agents through prompting or inference-time methods without training. |
| `ui-design` | UI design | 界面设计 | How interface design affects agents and users, and agents that evaluate or generate interfaces. |
| `video` | Video | 视频 | Learning from, or evaluating on, screen recordings and tutorial videos. |
| `web-navigation` | Web navigation | 网页导航 | Operating websites and web applications in a browser. |
| `workflow` | Workflows | 工作流 | Multi-step procedures, business processes, and reusable task workflows. |
| `world-models` | World models | 世界模型 | Predicting how an interface changes after an action, for planning or training. |
<!-- TOPICS:END -->

`references.jsonl` is a separate discovery graph. Its `mentions` relation only means a URL was found in the source. `target_in_catalog` distinguishes indexed and unresolved targets. Strong reviewed relations remain inside each resource record and in the SQLite `relations` table.

[Authored and generated files](#authored-and-generated-files) lists every file in `data/` and every generated view, with the command that writes it. The ignored `.cache/` directory is not needed to reproduce an offline build.

`repository-aliases.json` records former GitHub names and their canonical owners, following [repository-alias.schema.json](../schemas/repository-alias.schema.json). Each mapping has two official API observations: the former-name URL and the canonical-name URL must identify the same numeric repository ID and canonical `full_name`. Case normalization, similar titles, a shared project, or a repository-to-dataset link cannot establish a migration. Mappings must point directly to an active reviewed repository; conflicting owners, cycles, chains and active records under the former ID fail validation.

A Hugging Face mapping (`basis: official_huggingface_repository_id`) pairs the `/api/models/` or `/api/datasets/` responses for two names of one model or dataset. Both must return the same repository object `_id` (recorded as `repository_id`) and the same current `id` (`full_name`), and `resolved_url` records where the API redirected. Hub `url:` IDs hash the path with its case, so a renamed or re-cased repository splits into several IDs; the mapping points the other name's ID at the existing record, whichever name that record's URL uses, and keeps its ID stable. `validate` lists a curated record whose Hub API `details.hub_id` differs from its URL path without a mapping for that name.

The materializer adds verified former IDs, names and URLs to the owner's `aliases`, with primary `github_repository_identity` or `huggingface_repository_identity` receipts that support only that field. It preserves the canonical ID, content review, licenses and relationships. `get` accepts exact recorded former IDs, and `search` resolves recorded former repository URLs. Both return the canonical resource; no additional record is created. Discovery and mention inputs keep their observed identifiers. Coverage resolves matching identifiers while `indexed_resources` counts distinct owners.

The [English data hub](https://awesomecua.github.io/data/) and [中文数据中心](https://awesomecua.github.io/zh/data/) expose downloads from the same source catalog available by cloning the repository. Their [download manifest](https://awesomecua.github.io/downloads/manifest.json) follows [download-manifest.schema.json](../schemas/download-manifest.schema.json). Its `artifacts` array records each listed export's `path`, format, group, actual `count.value` and `count.unit`, `scope`, exact `bytes`, and file `sha256`. The top-level `catalog_sha256` identifies the source catalog snapshot; compare it with the RAG, citation and topic manifests before combining artifacts.

| Manifest group | Contents |
| --- | --- |
| `catalog` | Complete active records as JSONL, a JSON array, and SQLite |
| `rag` | Reviewed or metadata-inclusive retrieval documents and their manifest |
| `citations` | Retained-source and publication-edition citations, with selection and edition metadata |
| `research` | Topic subsets, benchmark/dataset profiles, and reviewed relationships |
| `provenance` | Sources, coverage, review decisions, repository identities, retained arXiv archive, and publication observations |
| `contracts` | Machine-readable JSON Schemas |

An artifact count measures its declared unit and population, not extra catalog resources. JSONL and SQLite can contain the same records; reviewed RAG documents overlap the active corpus; topic memberships and citation editions also overlap. Do not sum artifact counts or mix units. `scope` distinguishes active records, reviewed selections, publication editions, the retained archive, provenance, and contracts. A matching SHA-256 identifies file bytes; it does not add editorial approval or permissions to the underlying resources.

`papers.jsonl` remains the arXiv archive. Each `publications.jsonl` observation has `id`, `publication`, `evidence`, and `last_verified_at`, following [publication-observation.schema.json](../schemas/publication-observation.schema.json). An existing arXiv ID receives publication metadata without replacing its original title, authors, dates or version. A new publisher URL identity creates a metadata-only record; relevance approval is still a separate editorial decision. A known publisher or PDF alias resolves to the same resource instead of adding another paper.

`details.publication` retains the publication edition's title, literal authors, type, venue, publisher, DOI, volume/issue/pages and source receipts. `date_parts` is `[year]`, `[year, month]`, `[year, month, day]`, or null. Unknown components are never filled with `01`; event dates are kept separately. `published_at IS NULL` therefore does not necessarily mean the publication year is unknown. Catalogue years use the retained arXiv submission date for arXiv identities, and the publication's recorded precision for publisher-only identities. Undated records sort last; partial dates sort after more precise dates in the same year/month, without asserting an earlier calendar day.

Coverage counts distinguish `bibliographic_records` (all active papers/surveys), `arxiv_active_records`, `non_arxiv_bibliographic_records`, and `publication_metadata_records` (including publication attachments to arXiv). The arXiv archive count remains separate. Per-source `indexed` counts matched discovery identifiers; `indexed_resources` counts distinct canonical resources, so multiple publisher/PDF aliases or former GitHub names cannot inflate the catalog's resource total.

The website's `downloads/topics.json` is a derived index of reviewed topic membership, tied to the source catalog SHA-256. Each topic lists canonical resource IDs, counts, bilingual page URLs, and export fingerprints. `resources_with_topics` counts distinct reviewed resources across all topics; individual topic totals overlap and must not be summed. Per-topic JSONL preserves the complete source records, including evidence, license scopes and review state. Shared tags are not reviewed resource relationships. Rebuilds remove obsolete generated topic pages and exports when a topic loses all reviewed members.

Reviewed `documented_by` links connect an implementation or dataset to a paper named by its first-party source. They do not imply a training or evaluation dependency. Resource pages expose both outgoing relations and incoming connected assets. The [connections directory](https://awesomecua.github.io/connections/) and [relationship export](https://awesomecua.github.io/downloads/relationships.json) provide a consolidated view.

A relation points from the record that holds it to `target_id` and cites one of that record's primary receipts whose `supports` include `relations`. Choose the type from what that source states; when it states none of these, record no relation.

| Type | The cited source states that | Editorial key |
| --- | --- | --- |
| `documented_by` | a paper describes the resource, for example by linking or citing it as the resource's paper. This is the default paper link and stays correct when the paper also introduced the resource | `documented_by` |
| `introduced_by` | the resource, typically a dataset or benchmark, originates in that paper | `paper_ids` |
| `published_by` | the target organization publishes the resource | `publisher_id` |
| `variant_of` | the resource is a checkpoint or variant of a model family; the target is the family's record or the repository that releases the family | `family_url` |
| `component_of` | the resource, such as a dataset, benchmark data or a tool, is released as part of the target project | `component_of` |
| `trained_on` | the model was trained or fine-tuned on the target dataset | `reviewed_relations` |
| `uses` | the resource depends on a separate resource, such as a framework that runs a benchmark's tasks. A checkpoint never `uses` its own code repository; that link is `variant_of` | `reviewed_relations` |
| `evaluates` | the resource, such as a benchmark or evaluation harness, measures the target | `reviewed_relations` |

The citation exports retain literal source authors, source dates at their known precision, review status, and stable catalog identity. The default arXiv citation keeps its retained preprint version; `--edition publication` explicitly selects the publication's own title/authors/date/venue/DOI. Publisher-only records cite their publication in either mode. Unknown facts are omitted. Publication citation IDs can have an edition suffix while `custom.catalog_id` retains the canonical resource ID. The export manifest records editions, counts and file SHA-256 values, tied to the source catalog SHA-256.

`catalog.py get` returns an exact active record with its stable ID. `--related` adds only source-backed reviewed semantic relations; raw reference mentions are not promoted. A scope-excluded ID returns its applied decision and a nonzero exit code, preserving the boundary between the active catalog and retained archive.

## Authored and generated files

Edit authored files by hand and review them in a pull request. Do not hand-edit command or build outputs: rerun the command, because hand edits are overwritten on the next run, and `build --check` fails when a build output is stale. All paths are in `data/` unless shown otherwise.

| File | Type | Written by |
| --- | --- | --- |
| `editorial.json` | Authored | Editorial proposals and approvals; see [editorial input](editorial-input.md) |
| `exclusions.json` | Authored | Scope decisions; see [scope review](scope-review.md) |
| `publications.jsonl` | Authored | Reviewed publication observations |
| `repository-aliases.json` | Authored | Paired official GitHub or Hugging Face identity observations for reviewed former or other repository names |
| `candidate-reviews.json` | Authored | Discovered links reviewed as non-resources or as other addresses of active records; see [methodology](methodology.md#identity-and-deduplication) |
| `sources.json` | Authored | Discovery-source registry read by `catalog.py discover` |
| `paper-discovery-queries.json` | Authored | Hugging Face search registry read by `discover_papers.py` |
| `scan-config.json` | Authored | Scan schedule and limits read by `scan.py` and the website status page |
| `site-guides.json`, `site-discovery.json` | Authored | Website guides and search-discovery settings read by `build_site.py` and `submit_indexnow.py` |
| `conference-discovery.json`, `discovery-audits.json` | Authored | Records of a manual proceedings sweep and an arXiv query audit; no script rewrites them |
| `topics.json` | Authored | Topic vocabulary read by `catalog.py validate`, `catalog.py build`, `build_site.py` and the website; see [topic vocabulary](#topic-vocabulary) |
| `search-submissions.json` | Authored | Hand-recorded search-console receipts; `submit_indexnow.py --submit` with default paths also appends here |
| `primary-evidence.jsonl` | Command output | `catalog.py verify` |
| `enrichment.jsonl` | Command output | `catalog.py enrich` |
| `arxiv-search.json` | Command output | `catalog.py search-arxiv` |
| `candidates.jsonl` | Command output | `catalog.py discover`, `discover_papers.py`, `catalog.py search-arxiv`, `scan.py` |
| `papers.jsonl`, `metadata-updates.jsonl` | Command output | `catalog.py harvest`, `catalog.py search-arxiv`, `scan.py`; `backfill_arxiv_snapshots.py --write` also writes `papers.jsonl` |
| `harvest-failures.jsonl` | Command output | `catalog.py harvest`, run by `scan.py` |
| `discovery-runs.json` | Command output | `catalog.py discover`, run by `scan.py` |
| `research-discovery.json`, `paper-discovery-status.json` | Command output | `discover_papers.py`, run by `scan.py` |
| `recent-paper-search.json`, `scan-status.json`, `scan-history.jsonl` | Command output | `scan.py` |
| `github-candidates.jsonl`, `github-candidates-manifest.json` | Command output | `export_candidates.py` prepares sanitized, unreviewed GitHub observations; after an explicit bootstrap, `scan.py` adopts verified incremental updates independently of the active catalog |
| `github-candidate-progress.json` | Command output | `candidate_state.py` prepares the initial checkpoint from retained evidence; `scan.py` advances the fingerprint-bound query/epoch cursors and receipts. No repository descriptions, owner/contact objects or raw API bodies belong here |
| `catalog.jsonl`, `coverage.json`, `exclusion-status.json`, `references.jsonl`, `review-queue.jsonl` | Build output | `catalog.py build` |
| `docs/agents.md`, `docs/benchmarks.md`, `docs/companies.md`, `docs/datasets.md`, `docs/frameworks.md`, `docs/infrastructures.md`, `docs/models.md`, `docs/products.md`, `docs/surveys.md`, `docs/tools.md` | Build output | `catalog.py build` |
| `docs/papers.md`, `docs/coverage.md`, `docs/topics.md`, `docs/topics/*.md` | Build output | `catalog.py build` |
| `BADGES`, `STATS`, `EXPLORE`, `HIGHLIGHTS`, and `RECENT` blocks in `README.md` and `README.zh-CN.md` | Build output | `catalog.py build` replaces the text between each block's `START` and `END` markers; the rest of both READMEs is authored |
| `TOPICS` block in `docs/data-dictionary.md` | Build output | `catalog.py build` regenerates the topic table from `topics.json`; the rest of this file is authored |
| `dist/catalog.sqlite`, `dist/catalog.json`, `dist/site/` | Ignored build output | `catalog.py build` and `build_site.py`; never committed |

The scheduled scan runs `discover`, `discover_papers.py`, the recent arXiv search, `harvest`, bounded GitHub candidate continuation, and `build`. It commits everything it changes under `data/`, `docs/`, and both READMEs, so it can rewrite any command output above except `primary-evidence.jsonl`, `enrichment.jsonl`, and `arxiv-search.json`, and any committed build output. Candidate observations remain outside the active catalog and default RAG exports. Their public JSONL, manifest and operational checkpoint must stay together in a source commit; raw response bodies remain in ignored run directories. See [candidate continuation](public-candidate-scan.md#durable-progress-across-fresh-checkouts). The other docs in `docs/` and the text outside the generated blocks are authored. [CONTRIBUTING](../CONTRIBUTING.md#resolving-conflicts-with-the-scheduled-scan) explains how to resolve the resulting conflicts.
