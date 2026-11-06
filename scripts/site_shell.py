"""The site chrome shared by every page: head assets, header, footer, menu sheet and icon sprite."""
from __future__ import annotations

import html

from site_config import SITE

REPO = "https://github.com/reacher-z/Awesome-CUA"
ISSUES = REPO + "/issues/new/choose"
HF_DATASET = "https://huggingface.co/datasets/TIGER-Lab/awesome-cua"
SISTER_SITE = "https://awesomerea.org/"

# Set once per build. A page written without it (tests, partial builds) falls back to the plain labels.
SITE_REPO = "reacher-z/Awesome-CUA"
WEBSITEBENCH_REPO = "TIGER-AI-Lab/WebsiteBench"
WEBSITEBENCH_URL = f"https://github.com/{WEBSITEBENCH_REPO}"
ANNOUNCEMENT_ID = "websitebench"
CONTEXT = {"asset_version": "", "stars": {}, "last_scan": None, "has_survey": True}


def configure(*, asset_version="", stars=None, last_scan=None, has_survey=True):
    CONTEXT.update(asset_version=asset_version, stars=stars or {}, last_scan=last_scan, has_survey=has_survey)


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def fmt(number: int) -> str:
    return f"{number:,}"


def short_count(number: int) -> str:
    """Star counts round for display: 44, 1.2k, 12k. Rounds down, so a count is never overstated."""
    if number < 1000:
        return str(number)
    tenths = number * 10 // 1000
    return f"{tenths // 10}k" if tenths >= 100 or tenths % 10 == 0 else f"{tenths / 10:.1f}k"


# 24-pixel grid, 1.6 stroke, round caps. Rendered once per page as <symbol>s; site.js reuses them.
ICONS = {
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>',
    "gauge": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14a8 3 0 0 0 16 0V5"/><path d="M4 12a8 3 0 0 0 16 0"/>',
    "cube": '<path d="M21 8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4a2 2 0 0 0 1-1.7Z"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/>',
    "pointer": '<path d="M4.04 4.69a.5.5 0 0 1 .65-.65l16 6.5a.5.5 0 0 1-.06.95l-6.13 1.58a2 2 0 0 0-1.43 1.43l-1.58 6.13a.5.5 0 0 1-.95.06z"/>',
    "layers": '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94z"/>',
    "server": '<rect width="20" height="8" x="2" y="2" rx="2"/><rect width="20" height="8" x="2" y="14" rx="2"/><path d="M6 6h.01M6 18h.01"/>',
    "box": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M2 9h20M6 4v5"/>',
    "building": '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M9 22v-4h6v4M8 6h.01M12 6h.01M16 6h.01M8 10h.01M12 10h.01M16 10h.01M8 14h.01M12 14h.01M16 14h.01"/>',
    "file": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4M16 13H8M16 17H8M10 9H8"/>',
    "book": '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>',
    "cap": '<path d="M21.42 10.92a1 1 0 0 0-.02-1.84l-8.57-3.9a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.83l8.57 3.91a2 2 0 0 0 1.66 0z"/><path d="M22 10v6M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    "web": '<circle cx="12" cy="12" r="9"/><path d="M12 3a13.5 13.5 0 0 0 0 18 13.5 13.5 0 0 0 0-18M3 12h18"/>',
    "desktop": '<rect width="20" height="14" x="2" y="3" rx="2"/><path d="M8 21h8M12 17v4"/>',
    "mobile": '<rect width="12" height="20" x="6" y="2" rx="2.5"/><path d="M11 18h2"/>',
    "cross": '<rect width="13" height="10" x="2" y="4" rx="1.5"/><rect width="6" height="11" x="16" y="9" rx="1.5"/><path d="M5 18h8"/>',
    "github": '<path fill="currentColor" stroke="none" d="M12 1.5a10.5 10.5 0 0 0-3.32 20.46c.53.1.72-.23.72-.5v-1.8c-2.93.64-3.55-1.4-3.55-1.4-.48-1.22-1.17-1.54-1.17-1.54-.95-.65.08-.64.08-.64 1.06.07 1.61 1.09 1.61 1.09.94 1.6 2.46 1.14 3.06.87.1-.68.37-1.14.66-1.4-2.34-.27-4.8-1.17-4.8-5.2 0-1.15.41-2.09 1.08-2.83-.1-.27-.47-1.34.11-2.79 0 0 .88-.28 2.89 1.08a10 10 0 0 1 5.26 0c2-1.36 2.88-1.08 2.88-1.08.58 1.45.21 2.52.1 2.79.68.74 1.08 1.68 1.08 2.83 0 4.04-2.46 4.93-4.8 5.19.38.33.71.97.71 1.96v2.9c0 .28.19.61.73.5A10.5 10.5 0 0 0 12 1.5Z"/>',
    "ext": '<path d="M7 17 17 7M8 7h9v9"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>',
    "copy": '<rect width="13" height="13" x="9" y="9" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
    "moon": '<path d="M20.5 14.1A8.5 8.5 0 0 1 9.9 3.5a8.5 8.5 0 1 0 10.6 10.6Z"/>',
    "auto": '<circle cx="12" cy="12" r="9"/><path fill="currentColor" d="M12 3a9 9 0 0 1 0 18z"/>',
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "sliders": '<path d="M21 4h-7M10 4H3M21 12h-9M8 12H3M21 20h-5M12 20H3M14 2v4M8 10v4M16 18v4"/>',
    "down": '<path d="m6 9 6 6 6-6"/>',
    "right": '<path d="m9 18 6-6-6-6"/>',
    "lock": '<rect width="16" height="10" x="4" y="11" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "code": '<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
    "quote": '<path d="M6 7h4v5H6zM6 12c0 3-1 4.5-2.5 5.5M15 7h4v5h-4zM15 12c0 3-1 4.5-2.5 5.5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "enter": '<path d="M9 10 4 15l5 5"/><path d="M20 4v7a4 4 0 0 1-4 4H4"/>',
    "feed": '<path d="M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/>',
    "terminal": '<path d="m4 17 6-6-6-6M12 19h8"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
    "route": '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
    "star": '<path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.9L12 17l-5.2 2.8 1-5.9L3.5 9.7l5.9-.8z"/>',
    "hf": '<path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z"/><path d="M8.5 14.5a4.5 4.5 0 0 0 7 0M9 10h.01M15 10h.01"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "repo": '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H19a1 1 0 0 1 1 1v18a1 1 0 0 1-1 1H6.5a1 1 0 0 1 0-5H20"/><path d="M9 7h6"/>',
}


def sprite() -> str:
    body = "".join(f'<symbol id="i-{name}" viewBox="0 0 24 24">{paths}</symbol>' for name, paths in ICONS.items())
    return f'<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>{body}</defs></svg>'


def ic(name: str, cls: str = "i") -> str:
    return f'<svg class="{cls}" aria-hidden="true" focusable="false"><use href="#i-{name}"/></svg>'


LOGO = ('<svg viewBox="0 0 28 28" aria-hidden="true" focusable="false">'
        '<rect x="2.5" y="4.5" width="21" height="16" rx="3.5" fill="none" stroke="currentColor" stroke-width="1.7"/>'
        '<path d="M2.5 9h21" stroke="currentColor" stroke-width="1.5"/>'
        '<circle cx="5.7" cy="6.8" r="1" fill="currentColor"/><circle cx="8.6" cy="6.8" r="1" fill="currentColor"/>'
        '<path d="M15.2 13.2 25 17.4l-4.2 1.1-1.2 4.3z" fill="#FFA69E" stroke="#9D4E49" stroke-width="1.1" '
        'stroke-linejoin="round"/></svg>')

THEME_SCRIPT = ("<script>var h=document.documentElement;h.classList.add('js');try{var t=localStorage.getItem('cua-theme');"
                "if(t==='light'||t==='dark')h.setAttribute('data-theme',t);"
                f"if(localStorage.getItem('cua-announce')==='{ANNOUNCEMENT_ID}')h.classList.add('announce-off')}}catch(e){{}}</script>")


def asset(path: str) -> str:
    version = CONTEXT["asset_version"]
    return f"{path}?v={version}" if version else path


def head_assets(lang="en") -> str:
    """The inline theme script stays first, so the theme is set before the first paint."""
    return (THEME_SCRIPT +
            # Sends only the origin, so the repository's traffic report can show visits from this site.
            '<meta name="referrer" content="strict-origin-when-cross-origin">'
            '<meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)">'
            '<meta name="theme-color" content="#0C1023" media="(prefers-color-scheme: dark)">'
            '<link rel="preload" href="/assets/fonts/eb-garamond.woff2" as="font" type="font/woff2" crossorigin>'
            '<link rel="preload" href="/assets/fonts/inter.woff2" as="font" type="font/woff2" crossorigin>'
            f'<link rel="stylesheet" href="{asset("/assets/site.css")}">'
            f'<script src="{asset("/assets/site.js")}" defer></script>')


NAV = [("Catalog", "目录", "/catalog/", "/zh/catalog/"), ("Papers", "论文", "/papers/", "/zh/papers/"),
       ("Benchmarks", "评测基准", "/categories/benchmark/", "/zh/categories/benchmark/"),
       ("Topics", "主题", "/topics/", "/zh/topics/"), ("Guides", "指南", "/guides/", "/guides/"),
       ("Data", "数据", "/data/", "/zh/data/")]


def active_nav(path: str):
    if path.startswith(("/papers/", "/zh/papers/", "/categories/paper/", "/categories/survey/", "/zh/categories/survey/", "/survey/")):
        return "Papers"
    if path.startswith(("/categories/benchmark/", "/zh/categories/benchmark/", "/compare/benchmarks/")):
        return "Benchmarks"
    if path.startswith(("/catalog/", "/zh/catalog/", "/categories/", "/zh/categories/", "/compare/", "/explore/", "/resources/")):
        return "Catalog"
    if path.startswith(("/topics/", "/zh/topics/")):
        return "Topics"
    if path.startswith("/guides/"):
        return "Guides"
    if path.startswith(("/data/", "/zh/data/")):
        return "Data"
    return None


def nav_links(lang: str):
    zh = lang.startswith("zh")
    return [(zh_label if zh else label, label, zh_href if zh else href) for label, zh_label, href, zh_href in NAV]


def star_count(repo, live=False) -> str:
    """A build-time count. Landing pages carry it in the HTML; other pages read /data/site-stamp.json, so a new star
    does not rewrite thousands of pages on every scan. Without a count the label still reads and links correctly."""
    count = CONTEXT["stars"].get(repo)
    if not count:  # No slot at all, so the label stays centred.
        return ""
    return f'<span class="star-n" data-star-count="{esc(repo)}">{short_count(count) if live else ""}</span>'


def star_button(zh=False, live=False, cls="") -> str:
    """The site's own GitHub star: indigo fill, coral star, live count. The label shortens with the width in CSS."""
    label = "在 GitHub 上点 Star" if zh else "Star on GitHub"
    return (f'<a class="star-btn{" " + cls if cls else ""}" href="{REPO}">{ic("star", "i")}<span class="star-long">{label}</span><span class="star-short">Star</span>'
            f'<span class="vh"> Awesome CUA</span>{star_count(SITE_REPO, live)}</a>')


def announcement(*, lang="en", live=False) -> str:
    zh = lang.startswith("zh")
    text = "新发布：<b>WebsiteBench。</b>AI 智能体能否通过浏览器探索重建网站？" if zh else "New: <b>WebsiteBench.</b> Can AI agents rebuild websites through browser exploration?"
    cta = "在 GitHub 上点 Star" if zh else "Star on GitHub"
    return f'''<div class="announce" role="region" aria-label="{"公告" if zh else "Announcement"}"><div class="wrap">
<a class="announce-link" href="{WEBSITEBENCH_URL}"><span class="announce-long">{text}</span><b class="announce-short">WebsiteBench</b>
<span class="announce-cta">{ic("star", "i i-sm")}<span class="announce-long">{cta}</span><span class="announce-short">Star</span>{star_count(WEBSITEBENCH_REPO, live)}</span></a>
<button class="announce-x js-only" type="button" data-dismiss-announce aria-label="{"关闭公告" if zh else "Dismiss announcement"}">{ic("x", "i i-sm")}</button>
</div></div>'''


def header(*, path="/", lang="en", lang_href=None, live=False) -> str:
    zh = lang.startswith("zh")
    current = active_nav(path)
    nav = "".join(f'<a href="{esc(href)}"{" aria-current=page" if key == current else ""}>{esc(label)}</a>'
                  for label, key, href in nav_links(lang))
    search_label = "搜索…" if zh else "Search the catalog"
    theme_label = "颜色主题：跟随系统" if zh else "Color theme: follows system"
    home = "/zh/" if zh else "/"
    other = lang_href or ("/" if zh else "/zh/")
    lang_text, lang_attr = ("English", 'lang="en" hreflang="en"') if zh else ("中文", 'lang="zh-CN" hreflang="zh-CN"')
    menu_label = "菜单" if zh else "Menu"
    return f'''<header class="site-header" id="top"><div class="wrap">
<a class="brand" href="{home}" aria-label="Awesome CUA home">{LOGO}<b>Awesome <span>CUA</span></b></a>
<nav class="nav" aria-label="{"主导航" if zh else "Main navigation"}">{nav}</nav>
<div class="head-tools">
<button class="search-trigger js-only" type="button" data-open-palette aria-label="{search_label}">{ic("search")}<span>{search_label}</span><kbd>⌘K</kbd></button>
<a class="icon-btn lang" href="{esc(other)}" {lang_attr}><span class="lang-full">{lang_text}</span><span class="vh">{"切换语言" if zh else "Switch language"}</span></a>
<button class="icon-btn js-only" type="button" data-theme-toggle aria-label="{theme_label}">{ic("auto")}</button>
{star_button(zh, live)}
<button class="icon-btn menu-btn js-only" type="button" data-open-menu aria-label="{menu_label}" aria-haspopup="dialog">{ic("menu")}</button>
</div>
</div></header>'''


def star_note(zh=False, attrs="", live=False) -> str:
    """The one quiet request after something useful. A page carries at most one."""
    text = "有帮助？在 GitHub 上为 Awesome CUA 点 Star" if zh else "Useful? Star Awesome CUA on GitHub"
    return f'<p class="star-note"{attrs}><a href="{REPO}">{ic("star", "i i-sm")}<span>{text}</span>{star_count(SITE_REPO, live)}</a></p>'


MAINTAINER_REPOS = (
    (WEBSITEBENCH_REPO, "WebsiteBench", "Can AI agents rebuild websites through browser exploration?", "AI 智能体能否通过浏览器探索重建网站？"),
    ("TIGER-AI-Lab/ClawBench", "ClawBench", "An everyday-task benchmark for browser agents on live websites.", "面向浏览器智能体的真实网站日常任务评测基准。"),
    (SITE_REPO, "Awesome CUA", "This catalog: computer-use research, data and tools, reviewed.", "本目录：经审核的计算机使用研究、数据与工具。"),
    ("reacher-z/Awesome-REA", "Awesome REA", "A catalog of resources for reverse engineering anything.", "面向逆向工程一切的资源目录。"),
)


def maintainer_cards(zh=False, live=False) -> str:
    cards = "".join(
        f'<li><a href="https://github.com/{repo}"><b>{name}</b><span class="more-line">{zh_line if zh else line}</span>'
        f'<span class="more-star">{ic("star", "i i-sm")}Star{star_count(repo, live)}</span></a></li>'
        for repo, name, line, zh_line in MAINTAINER_REPOS)
    return f'<section class="foot-more" aria-labelledby="foot-more-h"><h2 id="foot-more-h">{"精选" if zh else "Featured"}</h2><ul>{cards}</ul></section>'


FOOTER_COLUMNS = [
    ("Browse", "浏览", [("Catalog", "目录", "/catalog/", "/zh/catalog/"),
                        ("Explore every record", "检索全部记录", "/explore/", "/explore/?lang=zh"),
                        ("Benchmarks", "评测基准", "/categories/benchmark/", "/zh/categories/benchmark/"),
                        ("Datasets", "数据集", "/categories/dataset/", "/zh/categories/dataset/"),
                        ("Papers", "论文", "/papers/", "/zh/papers/"),
                        ("Survey", "综述", "/survey/", "/survey/")]),
    ("Use the data", "使用数据", [("Download data", "下载数据", "/data/", "/zh/data/"),
                                  ("Agent and RAG guide", "Agent 与 RAG 指南", "/agents/", "/zh/agents/"),
                                  ("llms.txt", "llms.txt", "/llms.txt", "/llms.txt"),
                                  ("Hugging Face dataset", "Hugging Face 数据集", HF_DATASET, HF_DATASET),
                                  ("Atom feed", "Atom 订阅", "/feed.xml", "/feed.xml"),
                                  ("Cite the catalog", "引用本目录", REPO + "/blob/main/CITATION.cff", REPO + "/blob/main/CITATION.cff")]),
    ("Project", "项目", [("Editorial policy", "收录方法", "/about/", "/about/"),
                         ("Coverage", "覆盖台账", "/coverage/", "/coverage/"),
                         ("Updates", "更新记录", "/updates/", "/updates/"),
                         ("Resource badges", "资源徽章", "/badges/", "/badges/"),
                         ("Suggest a resource", "提交资源", ISSUES, ISSUES),
                         ("Source repository", "源代码仓库", REPO, REPO),
                         ("Sitemap", "站点地图", "/sitemap.xml", "/sitemap.xml")]),
]


def scan_stamp(zh=False, live=False) -> str:
    """Last completed scan. A dated footer on every page would rewrite thousands of files on every scan, so pages
    that change rarely link to the scan record and site.js fills in the date from /data/site-stamp.json."""
    label = "最近扫描" if zh else "Last scan"
    last_scan = CONTEXT["last_scan"]
    if live and last_scan:
        when = last_scan[:16].replace("T", " ") + " UTC"
        return f'<a href="/updates/">{label} <time data-last-scan datetime="{esc(last_scan)}">{esc(when)}</time></a>'
    return f'<a href="/updates/">{label}<span data-last-scan-slot></span></a>'


def footer(*, lang="en", live=False) -> str:
    zh = lang.startswith("zh")
    columns = "".join(
        f'<div><h2>{zh_title if zh else title}</h2><ul>' + "".join(
            f'<li><a href="{esc(zh_href if zh else href)}">{zh_label if zh else label}</a></li>'
            # The survey is a separately published bundle, so a build without it must not link to it.
            for label, zh_label, href, zh_href in links if href != "/survey/" or CONTEXT["has_survey"]) + '</ul></div>'
        for title, zh_title, links in FOOTER_COLUMNS)
    blurb = ("面向计算机使用智能体的评测基准、数据集、模型与论文目录。每条记录都链接到一手来源。" if zh else
             "A catalog of benchmarks, datasets, models and papers for computer-use agents. Every record links to its primary source.")
    sister = "姊妹站" if zh else "Sister catalog"
    reverse = "逆向工程资源目录" if zh else "Reverse engineering anything"
    licence = "代码与数据以 MIT 许可发布" if zh else "Code and data under the MIT License"
    home = "/zh/" if zh else "/"
    return f'''<footer class="site-footer"><div class="wrap">
{maintainer_cards(zh, live)}
<div class="foot">
<div><a class="brand" href="{home}" aria-label="Awesome CUA home">{LOGO}<b>Awesome <span>CUA</span></b></a>
<p>{blurb}</p>
<a class="sister" href="{SISTER_SITE}"><span>{sister}</span><b>Awesome REA</b><span class="vh">{reverse}</span>{ic("ext", "i i-sm")}</a></div>
{columns}
</div>
<div class="colophon"><span>{licence} · <a href="{REPO}/blob/main/LICENSE">LICENSE</a></span><span>{scan_stamp(zh, live)}</span></div>
</div><div class="foot-word" aria-hidden="true" data-w="Awesome CUA"></div></footer>'''


def menu_sheet(*, lang="en", lang_href=None) -> str:
    zh = lang.startswith("zh")
    links = "".join(f'<a href="{esc(href)}">{esc(label)}{ic("right")}</a>' for label, _, href in nav_links(lang))
    other = lang_href or ("/" if zh else "/zh/")
    links += f'<button class="sheet-theme" type="button" data-sheet-theme>{"颜色主题" if zh else "Color theme"}{ic("auto")}</button>'
    links += f'<a href="{esc(other)}" lang="{"en" if zh else "zh-CN"}">{"English" if zh else "中文"}{ic("right")}</a>'
    links += f'<a href="{REPO}">{"GitHub 仓库" if zh else "GitHub repository"}{ic("ext")}</a>'
    return f'''<div class="sheet" id="menu-sheet" role="dialog" aria-modal="true" aria-label="{"菜单" if zh else "Menu"}" hidden>
<div class="sheet-panel"><div class="sheet-grip"></div><div class="sheet-head"><h2>{"浏览" if zh else "Browse"}</h2><button class="icon-btn" type="button" data-close-sheet aria-label="{"关闭" if zh else "Close"}">{ic("x")}</button></div>
<nav class="sheet-nav" aria-label="{"移动导航" if zh else "Mobile navigation"}">{links}</nav></div></div>'''


def top(*, path="/", lang="en", lang_href=None, live=False) -> str:
    return sprite() + announcement(lang=lang, live=live) + header(path=path, lang=lang, lang_href=lang_href, live=live)


def bottom(*, lang="en", lang_href=None, live=False) -> str:
    return (footer(lang=lang, live=live) + menu_sheet(lang=lang, lang_href=lang_href) +
            '<div class="site-toast" id="site-toast" role="status" aria-live="polite"></div>')
