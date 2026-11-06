"""The homepage hero, command window and sections, plus the compact client-side search index they read."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import re

import home_art as art
from paper_library import library_years
from publication_metadata import record_date_text, record_year
from site_config import SITE
from site_shell import CONTEXT, HF_DATASET, ISSUES, WEBSITEBENCH_REPO, WEBSITEBENCH_URL, ic, esc, fmt, star_button, star_count, star_note

# Tab and icon order. The labels stay beside the icons so the rows, tabs and search results agree.
KINDS = {  # key: (singular, plural, zh label, icon)
    "benchmark": ("Benchmark", "Benchmarks", "评测基准", "gauge"),
    "dataset": ("Dataset", "Datasets", "数据集", "database"),
    "model": ("Model", "Models", "模型", "cube"),
    "agent": ("Agent", "Agents", "智能体", "pointer"),
    "framework": ("Framework", "Frameworks", "框架", "layers"),
    "tool": ("Tool", "Tools", "工具", "wrench"),
    "infrastructure": ("Infrastructure", "Infrastructure", "基础设施", "server"),
    "product": ("Product", "Products", "产品", "box"),
    "company": ("Publisher", "Publishers", "发布方", "building"),
    "paper": ("Paper", "Papers", "论文", "file"),
    "survey": ("Survey", "Surveys", "综述", "book"),
    "learning": ("Learning", "Learning", "学习资源", "cap"),
}
KIND_ORDER = list(KINDS)
TABS = [("all", "All", "全部"), ("benchmark", "Benchmarks", "评测基准"), ("dataset", "Datasets", "数据集"),
        ("model", "Models", "模型"), ("agent", "Agents", "智能体"), ("framework", "Frameworks", "框架"),
        ("paper", "Papers", "论文"), ("tool", "Tools", "工具"), ("infrastructure", "Infrastructure", "基础设施"),
        ("product", "Products", "产品"), ("company", "Publishers", "发布方"), ("learning", "Learning", "学习")]
MAIN_TABS = ("all", "benchmark", "dataset", "model", "agent", "framework", "paper")
ENV_GROUPS = {"web": {"web"}, "desktop": {"desktop", "windows", "linux", "macos"},
              "mobile": {"android", "ios", "harmonyos"}, "cross": {"cross-platform"}}
ENV_LABEL = {"web": "Web", "desktop": "Desktop", "mobile": "Mobile", "cross": "Cross-platform"}
ENV_ZH = {"web": "网页", "desktop": "桌面", "mobile": "手机", "cross": "跨平台"}
ENV_BIT = {"web": 1, "desktop": 2, "mobile": 4, "cross": 8}
ENV_ICON = {"web": "web", "desktop": "desktop", "mobile": "mobile", "cross": "cross"}

# Pinned editorially; WebsiteBench has no catalog record yet, so it keeps the Unreviewed stamp and links to its repository.
CLAWBENCH = "github:tiger-ai-lab/clawbench"
WEBSITEBENCH = {"id": "github:tiger-ai-lab/websitebench", "name": "WebsiteBench", "kind": "benchmark",
                "summary": "Rebuild full-stack websites through browser exploration.", "environments": ["web"],
                "url": "https://github.com/TIGER-AI-Lab/WebsiteBench", "href": "https://github.com/TIGER-AI-Lab/WebsiteBench",
                "relations": [], "details": {}, "review_status": "candidate"}
# Examples are shown only when a reviewed record of that name exists.
TASKS = [
    ("gauge", "Evaluate an agent", "评测一个智能体", ("benchmark",), None, "Benchmarks", "评测基准", ["OSWorld", "WebArena", "AndroidWorld"]),
    ("route", "Train on GUI trajectories", "用 GUI 轨迹训练", ("dataset",), None, "Datasets", "数据集", ["GUI-Odyssey", "GUIAct", "AndroidControl"]),
    ("target", "Ground clicks on screen", "在屏幕上定位点击", ("model",), None, "Models", "模型", ["SeeClick", "UI-TARS", "OS-Atlas"]),
    ("layers", "Build or run an agent", "构建或运行智能体", ("framework",), None, "Frameworks", "框架", ["BrowserGym", "Agent S", "OpenCUA"]),
    ("server", "Sandbox agents safely", "在沙箱中运行", ("infrastructure", "tool"), None, "Tools and infrastructure", "工具与基础设施", ["E2B", "Cua", "AndroidEnv"]),
    ("shield", "Check safety and security", "检查安全性", (), "safety-security", "Safety research", "安全研究", ["SafeArena", "AgentDAM", "RiOSWorld"]),
]


def slug(record_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", record_id.lower()).strip("-")


def resource_href(record) -> str:
    return record.get("href") or f"/resources/{slug(record['id'])}/"


def clip(text, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    head = re.match(r"(.*\S)\s", text[:limit], re.S)
    return re.sub(r"[\s,;:.]+$", "", head[1] if head else text[:limit - 1]) + "…"


def clean_title(text) -> str:
    """Display form of a title: LaTeX wrappers retained from arXiv metadata are dropped."""
    text = re.sub(r"\\(?:textsc|textbf|textit|emph|texttt|mathrm|mathbf)\{([^{}]*)\}", r"\1", text or "")
    text = re.sub(r"\$([^$]*)\$", r"\1", text)
    return text.replace("\\&", "&").replace("~", " ").replace("\\", "")


def env_facets(environments) -> list:
    return [key for key, raw in ENV_GROUPS.items() if raw & set(environments)]


def identity(record) -> str:
    """The short identity shown beside a name: owner/repo, arXiv ID, Hugging Face ID or host."""
    url = record.get("url") or ""
    if record["id"].startswith("arxiv:"):
        return "arXiv " + record["id"].split(":", 1)[1]
    match = re.match(r"https?://github\.com/([^/]+/[^/#?]+)", url)
    if match:
        return match[1]
    match = re.match(r"https?://huggingface\.co/(?:datasets/|spaces/)?([^/]+/[^/#?]+)", url)
    if match:
        return "hf " + match[1]
    return re.sub(r"^https?://(www\.)?", "", url).split("/")[0]


def mention_sets(root, by_id):
    """Distinct catalog records whose reviewed source mentions each record."""
    mentions = defaultdict(set)
    path = root / "data/enrichment.jsonl"
    if not path.exists():
        return mentions
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        for reference in entry.get("references", []):
            if reference["target_id"] in by_id and reference["target_id"] != entry["id"]:
                mentions[reference["target_id"]].add(entry["id"])
    return mentions


def review_times(root, reviewed):
    """Editorial review time per reviewed record, matched by ID or primary URL."""
    path = root / "data/editorial.json"
    if not path.exists():
        return {}
    by_url = {record["url"]: record["id"] for record in reviewed}
    times = {}
    for entry in json.loads(path.read_text(encoding="utf-8")):
        if entry.get("editorial_reviewed") and entry.get("reviewed_at"):
            key = entry.get("id") or by_url.get(entry.get("url"))
            if key:
                times[key] = max(times.get(key, ""), entry["reviewed_at"])
    return times


def paper_of(record, by_id):
    for relation in record["relations"]:
        if relation["type"] in ("introduced_by", "documented_by"):
            target = by_id.get(relation["target_id"])
            if target and target["kind"] in ("paper", "survey"):
                return target
            if relation["target_id"].startswith("arxiv:"):
                return {"id": relation["target_id"], "published_at": None}
    return None


def year_of(record, by_id) -> int:
    if record.get("published_at"):
        return int(record["published_at"][:4])
    paper = paper_of(record, by_id)
    if paper and paper.get("published_at"):
        return int(paper["published_at"][:4])
    return 0


def licence_of(record) -> str:
    for scope in ("code", "data", "weights", "document"):
        declared = (record["licenses"].get(scope) or {}).get("declared")
        if declared:
            return declared if isinstance(declared, str) else "/".join(declared)
    return ""


def catalog_view(rows, reviewed, coverage, root):
    """Every number and list the home page shows, derived from the reviewed records of this build."""
    by_id = {record["id"]: record for record in rows}
    kinds = Counter(record["kind"] for record in reviewed)
    env_counts = Counter()
    for record in reviewed:
        env_counts.update(env_facets(record["environments"]))
    mentions = mention_sets(root, by_id)
    review_at = review_times(root, reviewed)
    is_paper = lambda record: record["kind"] in ("paper", "survey")
    first_seen = {}
    candidates_path = root / "data/candidates.jsonl"
    if candidates_path.is_file():
        for line in candidates_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                candidate = json.loads(line)
                if candidate.get("first_discovered_at"):
                    first_seen[candidate["id"]] = candidate["first_discovered_at"]
    pending = (record for record in rows if record["review_status"] != "curated" and record["id"] in first_seen)
    return {"by_id": by_id, "reviewed": reviewed, "kinds": kinds, "env_counts": env_counts, "mentions": mentions,
            "reviewed_at": review_at, "papers": kinds["paper"] + kinds["survey"],
            "recent_reviewed": sorted((record for record in reviewed if not is_paper(record) and review_at.get(record["id"])),
                                      key=lambda record: (review_at[record["id"]], record["name"].casefold()), reverse=True),
            "recent_papers": sorted((record for record in reviewed if is_paper(record) and record_date_text(record)),
                                    key=lambda record: (record_date_text(record), record["name"]), reverse=True),
            # Same date helper as the library, so a year-only publisher date still counts.
            "years": Counter(int(record_year(record)) for record in reviewed if is_paper(record) and record_year(record)),
            "year_links": {"en": library_years(rows, "en"), "zh": library_years(rows, "zh")},
            "first_seen": first_seen,
            "scan_new": sorted(pending, key=lambda record: (first_seen[record["id"]], record["id"]), reverse=True),
            "candidates": coverage["unindexed_candidates"],
            "leaderboards": sum(bool(record["details"].get("leaderboard_url")) for record in reviewed)}


def search_index(view):
    """Compact array index for the search field and palette: reviewed records only.

    Row: [id, name, kindIndex, envBits, year, flags, summary, mentions, topicIdx[], ident, reviewedDay, licence, extra?]
    flags: 1 = curated, 2 = official leaderboard, 4 = authors omitted
    extra: {"a": aliases, "p": arXiv ID of the documenting paper, "l": leaderboard URL, "u": primary source URL when the
    ID does not give it}, present only when non-empty.
    """
    reviewed, by_id = view["reviewed"], view["by_id"]
    topic_keys = sorted({topic for record in reviewed for topic in record["topics"]})
    licences = Counter(licence_of(record) for record in reviewed)
    licence_keys = [key for key, _ in licences.most_common() if key]
    rows = []
    for record in sorted(reviewed, key=lambda item: item["id"]):
        bits = sum(ENV_BIT[env] for env in env_facets(record["environments"]))
        leaderboard = record["details"].get("leaderboard_url")
        flags = 1 | (2 if leaderboard else 0) | (4 if record.get("authors_omitted") else 0)
        reviewed_day = (view["reviewed_at"].get(record["id"]) or record["last_verified_at"] or "")[:10].replace("-", "")
        licence = licence_of(record)
        is_paper = record["kind"] in ("paper", "survey")
        paper = None if is_paper else paper_of(record, by_id)
        extra = {}
        if not record["id"].startswith(("github:", "arxiv:")) or is_paper:
            extra["u"] = record["url"]
        if record["aliases"]:
            extra["a"] = record["aliases"]
        if paper and paper["id"].startswith("arxiv:"):
            extra["p"] = paper["id"].split(":", 1)[1]
        if leaderboard:
            extra["l"] = leaderboard
        rows.append([record["id"], clean_title(record["name"]), KIND_ORDER.index(record["kind"]), bits,
                     year_of(record, by_id), flags, "" if is_paper else clip(record["summary"], 120),
                     len(view["mentions"][record["id"]]), [topic_keys.index(topic) for topic in record["topics"]],
                     identity(record), int(reviewed_day or 0), licence_keys.index(licence) if licence else -1]
                    + ([extra] if extra else []))
    return {"v": 1, "kinds": KIND_ORDER, "topics": topic_keys, "licences": licence_keys, "rows": rows}


def kind_count(view, kind) -> int:
    if kind == "all":
        return len(view["reviewed"])
    if kind == "paper":
        return view["papers"]
    return view["kinds"][kind]


def kind_tag(kind, zh=False) -> str:
    return f'<span class="kind">{ic(KINDS[kind][3])}{KINDS[kind][2] if zh else KINDS[kind][0]}</span>'


def env_tag(environments, zh=False) -> str:
    facets = env_facets(environments)
    if not facets:
        return ""
    label = (ENV_ZH if zh else ENV_LABEL)[facets[0]]
    more = len(facets) - 1
    extra = f'<span aria-hidden="true">+{more}</span> <span class="vh">and {more} more</span>' if more else ""
    return f'<span class="env">{ic(ENV_ICON[facets[0]])}{label}{extra}</span>'


def stamp(state, zh=False) -> str:
    """The review state as words as well as colour."""
    if state == "curated":
        return f'<span class="stamp stamp-ok">{ic("check")}{"已审核" if zh else "Reviewed"}</span>'
    if state == "metadata_verified":
        return f'<span class="stamp stamp-info">{"仅元数据" if zh else "Metadata only"}</span>'
    return f'<span class="stamp stamp-new">{"未审核" if zh else "Unreviewed"}</span>'


def compact_row(record, zh=False) -> str:
    source = record.get("url") or ""
    return f'''<li class="row" id="r-{slug(record["id"])}">
{kind_tag(record["kind"], zh)}
<div class="row-main"><h3 class="row-name"><a href="{esc(resource_href(record))}" data-src="{esc(source)}">{esc(clean_title(record["name"]))}</a><span class="row-id">{esc(identity(record))}</span></h3>
<p class="row-desc">{esc(record.get("summary") or "")}</p></div>
<div class="row-side">{env_tag(record["environments"], zh)}{stamp(record["review_status"], zh)}</div>
</li>'''


def most_mentioned(view, count, exclude=()):
    candidates = [record for record in view["reviewed"]
                  if record["kind"] not in ("paper", "survey", "company") and record["id"] not in exclude]
    return sorted(candidates, key=lambda record: (-len(view["mentions"][record["id"]]), record["name"].casefold()))[:count]


def default_rows(view, zh=False) -> str:
    """The window is never empty: pinned benchmarks first, then what the catalog mentions most."""
    # A reviewed WebsiteBench record, once it exists, replaces the hand-written row.
    pinned = [view["by_id"].get(WEBSITEBENCH["id"], WEBSITEBENCH)]
    if CLAWBENCH in view["by_id"]:
        pinned.append(view["by_id"][CLAWBENCH])
    top = most_mentioned(view, 2, {record["id"] for record in pinned})
    return (f'<li class="row-cap">{"精选" if zh else "Featured"}</li>' + "".join(compact_row(record, zh) for record in pinned) +
            f'<li class="row-cap">{"目录中被提及最多" if zh else "Most mentioned across the catalog"}</li>' +
            "".join(compact_row(record, zh) for record in top))


def tab_href(kind, zh=False) -> str:
    if kind == "all":
        return "/catalog/"
    if kind == "paper":
        return "/zh/papers/" if zh else "/papers/"
    return f"/categories/{kind}/"


def finder(view, zh=False) -> str:
    """The command window: title bar with the live URL, search field, one control row, results, status bar."""
    total = kind_count(view, "all")
    tab = lambda key, label, zh_label, cls="tab": (
        f'<a class="{cls}" href="{tab_href(key, zh)}" data-kind="{key}"{" aria-current=true" if key == "all" else ""}>'
        f'{zh_label if zh else label} <span class="n" data-count="{key}">{fmt(kind_count(view, key))}</span></a>')
    tabs = "".join(tab(*item) for item in TABS if item[0] in MAIN_TABS)
    tabs += "".join(tab(*item, "tab tail") for item in TABS if item[0] not in MAIN_TABS)
    more_items = "".join(tab(*item, "more-item") for item in TABS if item[0] not in MAIN_TABS)
    more_count = sum(kind_count(view, item[0]) for item in TABS if item[0] not in MAIN_TABS)
    env_chips = "".join(
        f'<button class="chip" type="button" aria-pressed="false" data-env="{env}">{ic(ENV_ICON[env], "i i-sm env-ic")}{ic("check", "i i-sm ck")}'
        f'{(ENV_ZH if zh else ENV_LABEL)[env]} <span class="n" data-count="env-{env}">{fmt(view["env_counts"][env])}</span></button>'
        for env in ("web", "desktop", "mobile", "cross"))
    text = {
        "label": "搜索已审核的记录" if zh else f"Search {fmt(total)} reviewed records",
        "placeholder": "搜索，例如 OSWorld、WebArena、UI-TARS" if zh else "Search the catalog: try OSWorld, WebArena or UI-TARS",
        "short": "搜索 OSWorld、UI-TARS…" if zh else "Try OSWorld, WebArena, UI-TARS",
        "clear": "清除" if zh else "Clear search", "tabs": "资源类型" if zh else "Resource kinds", "more": "更多" if zh else "More",
        "leaderboard": "有官方排行榜" if zh else "Leaderboard", "sort": "排序" if zh else "Sort", "filters": "筛选" if zh else "Filters",
        "move": "移动" if zh else "move", "open": "打开" if zh else "open", "source": "打开来源" if zh else "source", "esc": "清除" if zh else "clear",
        "all": f"浏览全部 {fmt(total)} 条" if zh else f"Browse all {fmt(total)} records",
        "left": "向左滚动" if zh else "Scroll kinds left", "right": "向右滚动" if zh else "Scroll kinds right",
    }
    sort_options = "".join(f'<option value="{value}">{zh_label if zh else label}</option>' for value, label, zh_label in [
        ("mentions", "Most mentioned", "提及最多"), ("relevance", "Relevance", "相关度"),
        ("reviewed", "Recently reviewed", "最近审核"), ("year", "Newest", "最新")])
    address = '<output data-address><b>awesomecua.com</b>/' + ('zh/' if zh else '') + '</output>'
    copy_label = "复制链接" if zh else "Copy link"
    return f'''<div class="window finder" id="finder">
<div class="titlebar"><span class="lights" aria-hidden="true"><i></i><i></i><i></i></span><div class="address">{ic("lock")}{address}</div><button class="copy-url js-only" type="button" data-copy-url aria-label="{copy_label}">{ic("link")}<span>{copy_label}</span></button></div>
<span id="catalog"></span>
<form class="field" role="search" action="/catalog/" method="get" data-finder-form>
<label class="vh" for="q">{text["label"]}</label>{ic("search")}
<input id="q" name="q" type="search" placeholder="{text["placeholder"]}" data-ph-short="{text["short"]}" autocomplete="off" autocapitalize="off" spellcheck="false" enterkeyhint="search" aria-describedby="q-count">
<span class="count" id="q-count" aria-live="polite" aria-atomic="true"></span>
<button class="clear" type="button" aria-label="{text["clear"]}">{ic("x")}</button><kbd aria-hidden="true">/</kbd>
<span class="cursor-land" aria-hidden="true"><svg viewBox="0 0 26 26" width="24" height="24"><path d="M3 2 22 11.2l-8.2 2.2-3.6 8.6z" fill="#FFA69E" stroke="#7A3A36" stroke-width="1.4" stroke-linejoin="round"/></svg></span>
</form>
<div class="controls">
<div class="tabstrip" data-tabstrip><button class="tab-arrow prev" type="button" aria-label="{text["left"]}" hidden>{ic("right", "i i-sm flip")}</button>
<nav class="tabs" aria-label="{text["tabs"]}">{tabs}</nav>
<button class="tab-arrow next" type="button" aria-label="{text["right"]}" hidden>{ic("right", "i i-sm")}</button></div>
<details class="more-kinds" data-more><summary class="tab"><span data-more-label>{text["more"]}</span> <span class="n" data-more-n>{fmt(more_count)}</span>{ic("down", "i i-sm")}</summary><div class="menu-pop">{more_items}</div></details>
<div class="ctl-right js-only">
<button class="chip filters-btn" type="button" data-open-filters aria-expanded="false" aria-controls="filter-panel">{ic("sliders", "i i-sm")}{text["filters"]} <span class="n" data-filter-n></span></button>
<span class="select sort"><label class="vh" for="sort">{text["sort"]}</label><select id="sort" name="sort" data-sort>{sort_options}</select>{ic("down")}</span>
</div>
</div>
<div class="filterbar" id="filter-panel" hidden>
<span class="chip-group" role="group" aria-label="{"运行环境" if zh else "Environment"}">{env_chips}</span>
<span class="sep" aria-hidden="true"></span>
<button class="chip lb-chip" type="button" aria-pressed="false" data-lb>{ic("trophy", "i i-sm env-ic")}{ic("check", "i i-sm ck")}{text["leaderboard"]} <span class="n">{view["leaderboards"]}</span></button>
</div>
<h2 class="vh">{"结果" if zh else "Results"}</h2>
<ol class="rows rows-compact" id="results" aria-label="{"搜索结果" if zh else "Results"}" data-default>{default_rows(view, zh)}</ol>
<div class="statusbar"><span class="keys" aria-hidden="true"><span><kbd>↑</kbd><kbd>↓</kbd>{text["move"]}</span><span><kbd>↵</kbd>{text["open"]}</span><span><kbd>⌘</kbd><kbd>↵</kbd>{text["source"]}</span><span><kbd>esc</kbd>{text["esc"]}</span></span>
<a class="see-all" href="/catalog/" data-see-all>{text["all"]}{ic("right", "i i-sm")}</a></div>
</div>'''


def cursor_trail() -> str:
    """Geometry comes from site.js and the live layout: from the box around the headline word, through step 2, into
    the field. Without the script, and under 768 px, the box and .cursor-land carry the signature instead."""
    return ('<svg class="trail" aria-hidden="true" focusable="false"><path d="M0 0"/></svg>'
            '<div class="step step-2" aria-hidden="true"><b>2</b><span data-l></span></div>'
            '<div class="step step-3" aria-hidden="true"><b>3</b><span data-l>type("osworld")</span></div>'
            '<div class="cursor" aria-hidden="true"><svg viewBox="0 0 26 30" width="26" height="30">'
            '<circle class="ripple" cx="3" cy="2" r="9" fill="none" stroke="#FFA69E" stroke-width="2"/>'
            '<path d="M3 2 22 11.2l-8.2 2.2-3.6 8.6z" fill="#FFA69E" stroke="#7A3A36" stroke-width="1.4" stroke-linejoin="round"/>'
            '</svg></div>')


BBOX = '<i class="bbox-f" aria-hidden="true" data-l="click(412, 148)"></i>'


def hero(view, last_scan, zh=False) -> str:
    total, papers, candidates = fmt(kind_count(view, "all")), fmt(view["papers"]), fmt(view["candidates"])
    scanned = ""
    if last_scan:
        label = f'<time datetime="{esc(last_scan)}" data-ago>{esc(last_scan[:10])}</time>'
        scanned = (f'<span class="hs-opt"><i class="live" aria-hidden="true"></i>{label}扫描</span>' if zh else
                   f'<span class="hs-opt"><i class="live" aria-hidden="true"></i>Scanned {label}</span>')
    if zh:
        stats = (f'<span>已审核 <b>{total}</b> 条</span><span>其中论文与综述 <b>{papers}</b> 篇</span>'
                 f'<span class="hs-opt">尚未收录的扫描发现 <b>{candidates}</b> 条</span>')
        title, lede = f'计算机使用<span class="bbox-w"><span class="bbox">智能体{BBOX}</span>，</span>一站检索。', "收录面向计算机使用智能体的评测基准、数据集、模型与论文，每一条都核对过一手来源。"
    else:
        stats = (f'<span><b>{total}</b> reviewed records</span><span><b>{papers}</b> papers and surveys</span>'
                 f'<span class="hs-opt"><b>{candidates}</b> scan finds not yet in the catalog</span>')
        title, lede = f'Computer-use <span class="bbox">agents{BBOX}</span>, indexed.', "Benchmarks, datasets, models and papers for agents that use computers, each checked against its primary source."
    return f'''<section class="screen" aria-labelledby="hero-h"><div class="screen-in" data-screen>
<div class="wrap hero">
<h1 id="hero-h">{title}</h1>
<p class="hero-lede">{lede}</p>
<div class="hero-acts">{star_button(zh, live=True, cls="star-hero")}<p class="hero-stats">{stats}{scanned}</p></div>
{finder(view, zh)}
</div>
{cursor_trail()}
</div></section>'''


DEVICES = (("web", art.device_web), ("desktop", art.device_desktop), ("mobile", art.device_mobile))


def task_tiles(view, zh=False) -> str:
    """Six filled tiles, one job each. Examples are only those present in the catalog."""
    names = {record["name"].casefold(): record["name"] for record in view["reviewed"]}
    tiles = []
    for number, (_icon, title, zh_title, kinds, topic, label, zh_label, examples) in enumerate(TASKS, 1):
        if topic:
            count = sum(topic in record["topics"] for record in view["reviewed"])
            href = f"/zh/topics/{topic}/" if zh else f"/topics/{topic}/"
        else:
            count = sum(view["kinds"][kind] for kind in kinds)
            href = f"/categories/{kinds[0]}/"
        shown = ", ".join(names[example.casefold()] for example in examples if example.casefold() in names)
        drawing = art.VIGNETTES[topic or kinds[0]]()
        tiles.append(f'<a class="r3-tile r3-f{number}" href="{href}"><span class="r3-tile-n"><b>{fmt(count)}</b> {esc(zh_label if zh else label)}</span>{drawing}'
                     f'<b class="r3-tile-t">{esc(zh_title if zh else title)}</b><span class="r3-tile-eg">{esc(shown)}</span></a>')
    return f'<div class="r3-tiles">{"".join(tiles)}</div>'


def environments(view, zh=False) -> str:
    counts = view["env_counts"]
    suffix = "&amp;lang=zh" if zh else ""
    cells = "".join(f'<li><a href="/explore/?platform={env}{suffix}#catalog">{draw()}<span class="r3-env-n">{fmt(counts[env])}</span>'
                    f'<span class="r3-env-l">{(ENV_ZH if zh else ENV_LABEL)[env]}</span></a></li>' for env, draw in DEVICES)
    heading = "智能体在哪里操作" if zh else "Where the agent acts"
    more = f'/explore/?platform=cross-platform{suffix}#catalog'
    note = (f'另有 <a href="{more}">{fmt(counts["cross"])} 条</a>跨多个平台。' if zh else
            f'<a href="{more}">{fmt(counts["cross"])} more</a> span several platforms.')
    return f'<div class="r3-envs"><h3>{heading}</h3><ul>{cells}</ul><p>{note}</p></div>'


def tasks(view, zh=False) -> str:
    heading = "从一个任务开始" if zh else "Start from a task"
    lede = "每个入口都直达已筛选的列表。" if zh else "Each one opens the catalog already filtered for the job."
    return f'''<section class="section wrap r3-tasks" aria-labelledby="start-h">
<div class="sec-head"><div><h2 id="start-h">{heading}</h2><p>{lede}</p></div></div>
{task_tiles(view, zh)}
{environments(view, zh)}
</section>'''


def _feature(*, name, repo, url, summary, leaderboard, project, lead, zh, live) -> str:
    star = f"为 {name} 点 Star" if zh else f"Star {name}"
    tags = f'{kind_tag("benchmark", zh)}{env_tag(["web"], zh)}<span class="feature-tag">{"精选" if zh else "Featured"}</span>'
    return f'''<article class="feature-body{" feature-lead" if lead else ""}"><div class="ident-tags">{tags}</div>
<h3><a href="{esc(url)}">{name}</a></h3>
<p>{esc(summary)}</p>
<div class="feature-actions"><a class="btn {"btn-star" if lead else "btn-ghost"}" href="{esc(url)}">{ic("star")}{star}{star_count(repo, live)}</a>
<a class="btn btn-quiet" href="{esc(leaderboard)}">{ic("trophy")}{"排行榜" if zh else "Leaderboard"}</a>
<a class="btn btn-quiet" href="{esc(project)}">{ic("ext")}{"项目主页" if zh else "Project page"}</a></div></article>'''


def benchmark_band(view, zh=False, live=True) -> str:
    """The two featured benchmarks, largest first, then every reviewed record with an official leaderboard."""
    reviewed_with_board = sorted((record for record in view["reviewed"] if record["details"].get("leaderboard_url")),
                                 key=lambda record: (-len(view["mentions"].get(record["id"], ())), record["name"].casefold()))
    clawbench = view["by_id"].get(CLAWBENCH)
    website = _feature(name="WebsiteBench", repo=WEBSITEBENCH_REPO, url=WEBSITEBENCH_URL,
                       summary="AI 智能体能否通过浏览器探索重建网站？" if zh else "Can AI agents rebuild websites through browser exploration?",
                       leaderboard="https://website-bench.com/#results", project="https://website-bench.com/", lead=True, zh=zh, live=live)
    claw = "" if not clawbench else _feature(
        name="ClawBench", repo="TIGER-AI-Lab/ClawBench", url=clawbench["url"],
        summary="面向浏览器智能体的真实网站日常任务评测基准。" if zh else "An everyday-task benchmark for browser agents on live websites.",
        leaderboard=clawbench["details"].get("leaderboard_url") or "https://claw-bench.com", project="https://claw-bench.com", lead=False, zh=zh, live=live)
    rows = "".join(
        f'<li><a class="nm" href="{esc(resource_href(record))}">{esc(clean_title(record["name"]))}</a>{env_tag(record["environments"], zh)}'
        f'<a class="lb" href="{esc(record["details"]["leaderboard_url"])}" aria-label="{esc(clean_title(record["name"]))} {"排行榜" if zh else "leaderboard"}">{ic("trophy")}</a></li>'
        for record in reviewed_with_board)
    benchmarks = fmt(view["kinds"]["benchmark"])
    heading, lede, more, board, note = (
        ("评测基准", "精选评测基准，下方是目录中所有发布官方排行榜的已审核记录。", f"全部 {benchmarks} 项评测基准", "官方排行榜", f"{len(reviewed_with_board)} 项，按目录提及次数排序") if zh else
        ("Benchmarks", "Featured benchmarks, then every reviewed record that publishes an official leaderboard.", f"All {benchmarks} benchmarks", "Official leaderboards", f"{len(reviewed_with_board)} records, sorted by catalog mentions"))
    return f'''<section class="r3-band" aria-labelledby="feat-h"><div class="wrap">
<div class="sec-head"><div><h2 id="feat-h">{heading}</h2><p>{lede}</p></div>
<a class="more" href="/categories/benchmark/">{more}{ic("right", "i i-sm")}</a></div>
<div class="r3-band-feat">{website}{claw}</div>
<div class="lb-table"><div class="lb-head"><h3>{board}</h3><p>{note}</p></div>
<ul class="lb-list">{rows}</ul></div>
</div></section>'''


def latest(view, zh=False) -> str:
    reviewed = view["recent_reviewed"][:4]
    if not reviewed:
        return ""
    reviewed_items = "".join(
        f'<li><time datetime="{view["reviewed_at"][record["id"]][:10]}">{view["reviewed_at"][record["id"]][:10]}</time>'
        f'<a href="{esc(resource_href(record))}">{esc(clean_title(record["name"]))}</a>{stamp("curated", zh)}</li>' for record in reviewed)
    found = view["scan_new"][:4]
    found_items = "".join(
        f'<li><time datetime="{view["first_seen"][record["id"]]}">{view["first_seen"][record["id"]][:16].replace("T", " ")}</time>'
        f'<a href="{esc(record["url"])}">{esc(clip(clean_title(record["name"]), 92))}</a>{stamp(record["review_status"], zh)}</li>' for record in found)
    batch = max(view["reviewed_at"].values())[:10]  # Papers count here, though the list below shows other resources.
    heading, lede, more, done, new = (
        ("最新动态", f"最新审核批次：{batch}。扫描每小时运行一次，发现的条目在审核前始终带有标注。", "全部更新", "最近审核的资源", "最新扫描发现") if zh else
        ("Latest", f"Newest review batch: {batch}. Scans run every hour; their finds stay labelled until reviewed.", "All updates", "Recently reviewed resources", "From the latest scans"))
    scan_log = f'<div class="r3-log"><h3>{ic("clock")}{new} <span>UTC</span></h3><ol>{found_items}</ol></div>' if found else ""
    return f'''<section class="section wrap r3-latest" aria-labelledby="latest-h">
<div class="sec-head"><div><h2 id="latest-h">{heading}</h2><p>{lede}</p></div>
<a class="more" href="/updates/">{more}{ic("right", "i i-sm")}</a></div>
<div class="r3-logs"><div class="r3-log"><h3>{ic("check")}{done}</h3><ol>{reviewed_items}</ol></div>{scan_log}</div></section>'''


BENTO = (("paper", 3), ("benchmark", 2), ("model", 2), ("dataset", 2), ("framework", 2), ("agent", 2), ("survey", 2),
         ("tool", 2), ("infrastructure", 2), ("product", 2), ("company", 2), ("learning", 2))


def categories(view, zh=False) -> str:
    cells = []
    for kind, link_count in BENTO:
        if kind not in view["kinds"]:
            continue
        label, zh_label = KINDS[kind][1], KINDS[kind][2]
        if kind == "paper":
            recent = sorted(view["years"], reverse=True)[:3]
            year_links = view["year_links"]["zh" if zh else "en"]
            links = " ".join(f'<a href="{esc(year_links[str(year)])}">{year}</a>' for year in recent)
        else:
            top = sorted((record for record in view["reviewed"] if record["kind"] == kind),
                         key=lambda record: (-len(view["mentions"].get(record["id"], ())), record["name"].casefold()))[:link_count]
            links = ", ".join(f'<a href="{esc(resource_href(record))}">{esc(clip(clean_title(record["name"]), 26))}</a>' for record in top)
        drawing = {"paper": art.vig_paper, "benchmark": art.vig_rank}.get(kind)
        cells.append(f'<li class="r3-cell r3-c-{kind}"><a class="r3-cell-name" href="/categories/{kind}/">{zh_label if zh else label}</a>'
                     f'<span class="r3-cell-n">{fmt(view["kinds"][kind])}</span>{drawing() if drawing else ""}<p class="r3-cell-eg">{links}</p></li>')
    heading, more = ("按类别浏览", "打开目录") if zh else ("Browse by category", "Open the catalog")
    return f'''<section class="section wrap r3-cats" aria-labelledby="cats-h">
<div class="sec-head"><div><h2 id="cats-h">{heading}</h2></div>
<a class="more" href="/catalog/">{more}{ic("right", "i i-sm")}</a></div>
<ul class="r3-bento">{"".join(cells)}</ul></section>'''


def year_chart(view, zh=False) -> str:
    """One series, one hue, a direct label on every bar; the latest year is the indigo one."""
    year_links = view["year_links"]["zh" if zh else "en"]
    recent = [(str(year), count, year_links[str(year)]) for year, count in sorted(view["years"].items()) if year >= 2022]
    older = sum(count for year, count in view["years"].items() if year < 2022)
    bars = ([("更早" if zh else "Earlier", older, "/zh/papers/" if zh else "/papers/")] if older else []) + recent
    top = max(count for _, count, _ in bars)
    latest_year = recent[-1][0]
    records = "条记录" if zh else "records"
    items = "".join(f'<li{" class=now" if label == latest_year else ""}><a href="{href}" aria-label="{label}: {fmt(count)} {records}" style="--h:{max(2, round(100 * count / top))}%">'
                    f'<span class="c">{fmt(count)}</span><span class="bar"><i></i></span><span class="y">{label}</span></a></li>' for label, count, href in bars)
    heading = "按年份统计的已审核论文与综述" if zh else "Reviewed papers and surveys by year"
    note = f"按发表年份统计。{latest_year} 年仍在进行中。" if zh else f"Publication year. {latest_year} is the year so far."
    return f'<nav class="r3-years" aria-labelledby="years-h"><h3 id="years-h">{heading}</h3><ol>{items}</ol><p>{note}</p></nav>'


def papers(view, zh=False) -> str:
    if not view["recent_papers"]:
        return ""
    rows = []
    for record in view["recent_papers"][:3]:
        venue = (record["details"].get("publication") or {}).get("venue")
        if record.get("authors_omitted") or not record["authors"]:
            authors = f'<span>{"作者：见论文" if zh else "Authors: see the paper"}</span>'
        else:
            authors = f'<span>{esc(record["authors"][0])}{" 等" if zh and len(record["authors"]) > 1 else " et al." if len(record["authors"]) > 1 else ""}</span>'
        paper_id = record["id"].split(":", 1)[1] if record["id"].startswith("arxiv:") else None
        # Link the version that was reviewed; the bare ID can later resolve to a newer one.
        version = (record["details"].get("arxiv_snapshot") or {}).get("version")
        cited = f"{paper_id}v{version}" if paper_id and version else paper_id
        links = (f'<a href="https://arxiv.org/abs/{cited}">{ic("file")}arXiv {paper_id}</a><a href="https://arxiv.org/pdf/{cited}">PDF</a>' if paper_id else
                 f'<a href="{esc(record["url"])}">{ic("ext", "i i-sm")}{"来源" if zh else "Source"}</a>')
        rows.append(f'<li><time datetime="{record_date_text(record)}">{record_date_text(record)}</time><div><a class="paper-t" href="{esc(resource_href(record))}">{esc(clean_title(record["name"]))}</a>'
                    f'<div class="paper-m">{f"<span>{esc(venue)}</span>" if venue else ""}{authors}{links}</div></div></li>')
    count = fmt(view["papers"])
    heading, lede, more = (("论文", f"{count} 篇已审核论文与综述，按时间倒序。书目信息已与 arXiv 或出版方核对。", "阅读综述") if zh else
                           ("Papers", f"{count} reviewed papers and surveys, newest first. Bibliographic details are checked against arXiv or the publisher.", "Read the survey"))
    # The survey is a separately published bundle, so a build without it must not link to it.
    survey_link = f'<a class="more" href="/survey/">{more}{ic("right", "i i-sm")}</a>' if CONTEXT["has_survey"] else ""
    return f'''<section class="section wrap r3-papers" aria-labelledby="papers-h">
<div class="sec-head"><div><h2 id="papers-h">{heading}</h2><p>{lede}</p></div>
{survey_link}</div>
<div class="r3-papers-grid">{year_chart(view, zh)}<ol class="paper-list">{"".join(rows)}</ol></div></section>'''


def developers(zh=False) -> str:
    comment = lambda text: f'<span class="c"># {text}</span>'
    prompt = '<span class="p"></span>'
    key = lambda text: f'<span class="k">{text}</span>'
    jsonl_filter = """jq -r 'select(.kind=="benchmark" and .review_status=="curated") | .name'"""
    snippets = (
        ("jsonl", "JSONL", comment("每条记录一行 JSON" if zh else "Every record, one JSON object per line") +
         f"\n{prompt}curl -s {SITE}/downloads/catalog.jsonl \\\n  | {esc(jsonl_filter)}"),
        ("python", "Hugging Face", f'''{key("from")} datasets {key("import")} load_dataset

ds = load_dataset({key(chr(34) + HF_DATASET.rsplit("/datasets/", 1)[1] + chr(34))}, {key('"resources"')}, split={key('"train"')})
benchmarks = ds.filter({key("lambda")} r: r[{key('"kind"')}] == {key('"benchmark"')})
print(benchmarks[0][{key('"name"')}], benchmarks[0][{key('"url"')}])'''),
        ("llms", "llms.txt", f'''{comment("面向语言模型的站点索引" if zh else "An index of the site for language models")}
{prompt}curl -s {SITE}/llms.txt'''),
        ("cite", "Cite" if not zh else "引用", f'''@misc{{awesomecua,
  title  = {{Awesome CUA: a source-backed catalog of computer-use agent resources}},
  author = {{{{Awesome CUA}}}},
  url    = {{{SITE}}}
}}'''),
    )
    tabs = "".join(f'<button class="tab" type="button" role="tab" id="t-{name}" aria-controls="p-{name}" aria-selected="{"true" if number == 0 else "false"}" tabindex="{0 if number == 0 else -1}">{label}</button>'
                   for number, (name, label, _) in enumerate(snippets))
    panels = "".join(f'<pre id="p-{name}" role="tabpanel" aria-labelledby="t-{name}" tabindex="0"{" hidden" if number else ""}><code>{code}</code></pre>'
                     for number, (name, _, code) in enumerate(snippets))
    copy_label, licence = ("复制", "随每次扫描更新。许可：MIT。") if zh else ("Copy", "Updated with every scan. Licence: MIT.")
    links = (("/llms.txt", "terminal", "llms.txt", "面向语言模型的站点地图", "A map of the site for language models"),
             ("/data/", "code", "数据下载" if zh else "Download data", "JSONL、SQLite 与模式说明", "JSONL, SQLite and a schema, every record with its evidence"),
             (HF_DATASET, "hf", "Hugging Face 数据集" if zh else "Hugging Face dataset", "从 GitHub 同步", "Synced from GitHub"),
             ("/feed.xml", "feed", "Atom 订阅" if zh else "Atom feed", "审核后的新记录", "New records as they are reviewed"))
    items = "".join(f'<li><a href="{href}">{ic(icon)}<b>{title}</b><span>{zh_line if zh else line}</span></a></li>' for href, icon, title, zh_line, line in links)
    heading, lede = (("面向智能体与开发者", "整个目录都是开放数据。可以导入笔记本、检索索引或你自己的智能体；每条记录都保留证据链接和审核状态。") if zh else
                     ("For agents and developers", "The whole catalog is open data. Pull it into a notebook, a retrieval index or your own agent; every record keeps its evidence links and review state."))
    return f'''<section class="r3-term" aria-labelledby="dev-h"><div class="wrap">
<div class="dev"><div><h2 id="dev-h">{heading}</h2><p style="margin-top:12px;max-width:52ch">{lede}</p><ul>{items}</ul></div>
<div class="window term"><div class="titlebar"><span class="lights" aria-hidden="true"><i></i><i></i><i></i></span><div class="address">{ic("lock")}<output><b>awesomecua.com</b>/data/</output></div></div>
<div class="tabs" role="tablist" aria-label="{"使用数据的方式" if zh else "Ways to use the data"}">{tabs}</div>{panels}
<div class="panel-foot"><span>{licence}</span><button class="btn btn-ghost js-only" type="button" data-copy-panel style="min-height:36px">{ic("copy")}{copy_label}</button>{star_note(zh, ' data-after-copy hidden')}</div></div></div></div></section>'''


DIRECTORY = (
    ("read", (("/papers/", "Research papers"), ("/topics/", "Browse by topic"), ("/guides/", "Guides"), ("/categories/learning/", "Learning resources"))),
    ("browse", (("/catalog/", "Resource directory"), ("/categories/model/", "Models"), ("/categories/dataset/", "Datasets"), ("/categories/benchmark/", "Benchmarks"), ("/categories/framework/", "Frameworks"), ("/categories/product/", "Products"))),
    ("compare", (("/compare/benchmarks/", "Compare benchmarks"), ("/compare/datasets/", "Compare datasets"), ("/connections/", "Papers \u2192 code & data"))),
    ("reference", (("/data/", "Download data"), ("/updates/", "Updates every hour"), ("/coverage/", "Coverage"), ("/about/", "Editorial policy"))),
)
DIRECTORY_ZH = (
    ("研究", (("/zh/papers/", "论文与综述阅读列表"), ("/zh/topics/", "按主题浏览论文、数据与工具"), ("/categories/learning/", "学习资源"))),
    ("训练与评测", (("/categories/dataset/", "训练数据集"), ("/compare/datasets/", "对比数据规格"), ("/categories/benchmark/", "GUI、桌面、网页与手机评测基准"), ("/compare/benchmarks/", "对比评测协议"), ("/categories/model/", "模型与权重版本"))),
    ("工程", (("/categories/agent/", "智能体"), ("/categories/framework/", "开发与训练框架"), ("/categories/product/", "产品"), ("/catalog/", "浏览全部分类"))),
    ("数据", (("/explore/?lang=zh#catalog", "打开中文搜索目录"), ("/zh/data/", "下载数据"), ("/coverage/", "覆盖台账"), ("/about/", "编辑方法"))),
)
START = (("/guides/what-are-computer-use-agents/", "Understand computer-use agents"),
         ("/guides/gui-agent-benchmarks/", "Choose a benchmark for the capability you need"),
         ("/guides/gui-agent-training-data/", "Find training data with the right supervision and license"))


def directory_strip(zh=False, note="") -> str:
    """Crawlable site directory, also useful without JavaScript. It stays compact because the footer and sections repeat much of it."""
    rows = "".join(
        f'<div class="dir-row"><dt>{esc(label)}</dt><dd>' + "".join(f'<a href="{esc(href)}">{esc(text)}</a>' for href, text in links) + "</dd></div>"
        for label, links in (DIRECTORY_ZH if zh else DIRECTORY))
    if zh:
        lead = ("Computer-Use Agent 研究与资源", note)
        foot = ('<div class="dir-qa"><div><h3>如何理解“已核验”？</h3><p>已审阅条目经过一手来源编辑检查。论文元数据仅核实标题、作者和日期，不代表研究结论或实验已复现。代码、数据、权重与文档许可分别记录，未知信息保留为空。</p></div>'
                '<div><h3>是否已经全球最全？</h3><p>全面覆盖是目标，目前没有足够证据证明已达到全球最全。请查看<a href="/coverage/">覆盖台账</a>和<a href="/about/">编辑方法</a>了解边界与缺口。</p></div></div>')
    else:
        lead = ("Computer-use agent research and resources",
                "Browse source-backed pages directly, with or without JavaScript. Reviewed entries include concise annotations, provenance, and separate license declarations.")
        steps = "".join(f'<li><a href="{esc(href)}"><b aria-hidden="true">{n}</b>{esc(text)}</a></li>' for n, (href, text) in enumerate(START, 1))
        foot = f'<div class="dir-start"><h3>Where should I start?</h3><ol>{steps}</ol></div>'
    other = '<a class="dir-lang" href="/">English</a>' if zh else '<a class="dir-lang" href="/zh/" lang="zh-CN">中文指南</a>'
    return (f'<section class="wrap dir-strip" aria-labelledby="dir-h"><div class="dir-lead"><h2 id="dir-h">{esc(lead[0])}</h2><p>{lead[1]}</p>{other}</div>'
            f'<dl class="dir-rows">{rows}</dl>{foot}</section>')


def contribute(zh=False) -> str:
    if zh:
        heading, lede, suggest, correct = ("知道应该收录的资源？", "审核者会先阅读一手来源，收录记录也会链接到它。", "提交资源", "报告更正")
    else:
        heading, lede, suggest, correct = ("Know a resource that belongs here?", "A reviewer reads the primary source first, and the record links to it.", "Suggest a resource", "Report a correction")
    return f'''<section class="r3-cta" aria-labelledby="contrib-h">
<div class="wrap contribute"><div><h2 id="contrib-h">{heading}</h2>
<p>{lede}</p></div>
<div class="acts"><a class="btn btn-primary" href="{ISSUES}">{ic("plus")}{suggest}</a><a class="btn btn-ghost" href="{ISSUES}">{correct}</a></div></div>
</section>'''


def legacy_redirect_script() -> str:
    """Addresses of the old interactive home catalog keep working: they move, with their state, to the explorer page."""
    return ("<script>(function(){var s=location.search,h=location.hash;"
            "if(/[?&](platform|review|topic|year|page|record|lang|view)=/.test(s)||/[?&]sort=(name|newest)/.test(s)||(h==='#catalog'&&s)||/^#(coverage|about)$/.test(h))"
            "location.replace('/explore/'+s+h)})()</script>")
