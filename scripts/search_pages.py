"""Server-rendered, evidence-backed discovery pages for the static website."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
from collections import Counter, defaultdict
from field_labels import COUNT_BASIS, FIELD_LABELS, field_label
from specifications import PROFILE_KEYS, comparison_body, profile_export, resource_profile_html, count_text, safe_href
from agent_pages import agent_guide_body, RELEASES_URL
from export_citations import citation_bibtex, citation_csl
from paper_library import PAGE_SIZE, PLATFORMS, library_pages, library_path, library_years, paper_library, reviewed_papers
from publication_metadata import AUTHORS_OMITTED, authors_omitted, publication, format_date_parts, record_date_text, record_year
from topic_pages import KIND_LABELS, write_topic_exports, topic_index_body, topic_body, topic_counts, topic_markdown, topic_name, topic_page_count, topic_path
from data_hub import build_download_manifest, data_hub_body
from data_hub import data_hub_markdown
from site_config import SITE, scan_schedule
import home_page
import category_guides
from zh_summaries import zh_summary
import site_shell
from agent_files import FULL_ORDER, catalog_markdown, category_title, compact_entry, home_markdown, kind_markdown, library_markdown, link, llms_full, llms_txt, paper_hub_markdown
from survey_bundle import apply_site_shell
from discovery_files import FEED_SIZE, FEED_TITLE, feed_entry, robots_txt, write_feeds
from site_data import PAPER_KINDS, catalog_counts, eligible, latest, newest_reviewed, record_modified, review_dates
from static_api import API_SUMMARY, API_TITLE, api_docs_body, api_docs_markdown, write_api
from sitemaps import write_sitemaps

REPO = "https://github.com/AwesomeCUA/awesomecua.github.io"
SOURCE_REPO = "https://github.com/reacher-z/Awesome-CUA"
KIND_SINGULAR = {"paper":"Research paper", "survey":"Survey", "learning":"Learning resource", "model":"Model or checkpoint", "dataset":"Dataset", "benchmark":"Benchmark", "agent":"Agent", "framework":"Framework", "infrastructure":"Infrastructure", "tool":"Tool", "product":"Product", "company":"Publisher"}
ENVIRONMENT_LABELS = {"web":"Web", "desktop":"Desktop", "windows":"Windows", "linux":"Linux", "macos":"macOS", "android":"Android", "ios":"iOS", "harmonyos":"HarmonyOS", "cross-platform":"Cross-platform"}
TOPIC_CATALOG = json.loads((Path(__file__).resolve().parents[1]/"data/topics.json").read_text(encoding="utf-8"))
KINDS = {"paper":"Research papers", "survey":"Surveys", "learning":"Learning resources", "model":"Models and checkpoints", "dataset":"Datasets", "benchmark":"Benchmarks", "agent":"Agents", "framework":"Frameworks", "infrastructure":"Infrastructure", "tool":"Tools", "product":"Products", "company":"Publishers"}
CATEGORY_PAGE_SIZE = 100
TITLE_LIMIT = 60
TITLE_SUFFIX = ' | AwesomeCUA'
# Search snippets: 70-160 characters in English, 50-160 in Chinese.
DESCRIPTION_BOUNDS = {'en': (70, 160), 'zh-CN': (50, 160)}
DESCRIPTION_CONTEXT = {'en': 'AwesomeCUA links every computer-use agent resource to its primary sources and review status.',
                       'zh-CN': 'AwesomeCUA 收录计算机使用智能体的论文、模型、数据集、评测基准与工具，每条记录都附一手来源、许可证与审阅状态。'}
CJK_BREAKS = '，、；：。！？）'


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def clip(text, limit=300):
    # Search snippets must end on a whole word; the ellipsis counts toward the limit.
    if len(text)<=limit:return text
    head=re.match(r'(.*\S)\s',text[:limit],re.S)
    return re.sub(r'[\s,;:.]+$','',head[1] if head else text[:limit-1])+'…'


def shorten(text, limit):
    """At most `limit` characters ending in an ellipsis: cut at a space, or in Chinese text after punctuation or any character."""
    text = ' '.join(text.split())
    if len(text) <= limit:return text
    head = text[:limit-1]
    breaks = [head.rfind(' ')] + [head.rfind(mark) + 1 for mark in CJK_BREAKS if mark in head]
    cut = max(breaks)
    if cut < limit // 2:cut = limit - 1
    return re.sub(r'[\s,;:.，、；：。]+$', '', head[:cut]) + '…'


def page_title(title):
    """The <title>: the page name, shortened to fit, then the brand once."""
    if 'AwesomeCUA' in title:return shorten(title, TITLE_LIMIT)
    return shorten(title, TITLE_LIMIT-len(TITLE_SUFFIX)) + TITLE_SUFFIX


def sentence_ends(text, zh):
    if zh:return [i + 1 for i, char in enumerate(text) if char in '。！？；']
    return [i + 1 for i, char in enumerate(text) if char in '.!?' and (i + 1 == len(text) or text[i + 1] == ' ' and text[i + 2:i + 3].isupper())]


def meta_description(summary, lang='en', context=''):
    """A search snippet inside the language's bounds: whole sentences where they fit, then a word boundary."""
    zh = lang.startswith('zh')
    low, high = DESCRIPTION_BOUNDS['zh-CN' if zh else 'en']
    text = ' '.join(str(summary).split())
    for extra in (context, DESCRIPTION_CONTEXT['zh-CN' if zh else 'en']):
        if len(text) >= low:break
        if extra and extra not in text:text = (text + ('' if zh or not text else ' ') + extra).strip()
    if len(text) <= high:return text
    fitting = [end for end in sentence_ends(text, zh) if low <= end <= high]
    return text[:fitting[-1]] if fitting else shorten(text, high)


def clean_text(text):
    # Publication runs `git diff --check`: no line may end in whitespace and no blank line may end the file.
    lines=[line.rstrip(" \t\r") for line in text.split("\n")]
    while len(lines)>1 and lines[-1]==lines[-2]=="":lines.pop()
    return "\n".join(lines)


def resource_path(record):
    # IDs, rather than mutable display names, keep permalinks stable through renames.
    slug = re.sub(r"[^a-z0-9]+", "-", record["id"].lower()).strip("-")
    return f"/resources/{slug}/"


def guide_path(guide):
    # Guide slugs become output directories and canonical URLs, so they cannot carry path or markup characters.
    if not isinstance(guide.get("slug"),str) or not re.fullmatch(r"[a-z0-9-]+",guide["slug"]):raise ValueError(f"Invalid guide slug: {guide.get('slug')!r}")
    return f"/guides/{guide['slug']}/"


def alternate_map(alternatives):
    """Language versions of a page as {hreflang: path}; True names the home page pair."""
    if isinstance(alternatives, dict):return dict(alternatives)
    return {'en':'/','zh-CN':'/zh/','x-default':'/'} if alternatives else {}


def sitemap_section(path, kind_by_path):
    """Child sitemap for an indexable page: resource and paper entries, collection pages, or everything else."""
    if path in kind_by_path:return 'papers' if kind_by_path[path] in PAPER_KINDS else 'resources'
    if path.startswith(('/papers/','/zh/papers/','/survey/')):return 'papers'
    if path.startswith(('/catalog/','/zh/catalog/','/categories/','/zh/categories/','/topics/','/zh/topics/','/compare/')):return 'categories'
    return 'pages'


def resource_titles(rows):
    # Indexable pages must not share a <title>: a shared name gains its kind, or its source address when the kind is shared too.
    named=defaultdict(list)
    for r in rows:
        if eligible(r):named[r['name']].append(r)
    titles={}
    for name,members in named.items():
        if len(members)<2:continue
        kinds=Counter(r['kind'] for r in members)
        for r in members:
            label=('publisher' if r['kind']=='company' else r['kind']) if kinds[r['kind']]==1 else re.sub(r'^https?://(www\.)?','',r['url']).rstrip('/')
            titles[r['id']]=f'{name} ({label})'
    return distinct_titles(rows, titles, lambda r:r['name'])


def distinct_titles(rows, titles, base, separator=' · '):
    """Shortening can make two titles equal; a shared shortened title then ends with the record's own identifier."""
    room = TITLE_LIMIT - len(TITLE_SUFFIX)
    eligible_rows = [r for r in rows if eligible(r)]
    shown = {r['id']: shorten(titles.get(r['id'], base(r)), room) for r in eligible_rows}
    counts = Counter(shown.values())
    for r in eligible_rows:
        if counts[shown[r['id']]] > 1:
            tag = r['id'].split(':', 1)[-1]
            titles[r['id']] = shorten(base(r), max(12, room - len(tag) - 3)) + f' ({tag})'
    return titles


def zh_resource_titles(rows, titles):
    """Chinese resource titles add the Chinese kind; a name shared within one kind keeps the English source-address suffix."""
    room=TITLE_LIMIT-len(TITLE_SUFFIX)
    named={r['id']:(r['name'],home_page.KINDS[r['kind']][2]) for r in rows if eligible(r)}
    shared=Counter(named.values())
    # The kind stays visible when a long name is shortened.
    zh={key:f'{shorten(titles.get(key,name) if shared[(name,kind)]>1 else name,room-len(kind)-3)} · {kind}' for key,(name,kind) in named.items()}
    counts=Counter(zh.values())
    for r in rows:
        if r['id'] in zh and counts[zh[r['id']]]>1:
            tag=r['id'].split(':',1)[-1];kind=named[r['id']][1]
            zh[r['id']]=f'{shorten(r["name"],max(12,room-len(kind)-len(tag)-6))} ({tag}) · {kind}'
    return zh


def description(record):
    provider='arXiv' if record['id'].startswith('arxiv:') else 'retained publication sources'
    return record.get("summary") or f"Bibliographic record for {record['name']}. Title, authors and dates checked against {provider}; relevance and findings await editorial review."


def jsonld(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def organization():
    return {"@type":"Organization", "@id":SITE+"/#organization", "name":"AwesomeCUA", "url":SITE+"/", "sameAs":["https://github.com/AwesomeCUA", SOURCE_REPO, REPO]}


def page(title, summary, path, body, main=None, index=True, lang="en", alternatives=False, crumbs=None, canonical=True, landing=False, extra_graph=(), context=''):
    url=SITE+path
    # One list renders both the visible trail and BreadcrumbList, so they cannot disagree.
    crumbs=crumbs or [("AwesomeCUA","/zh/" if lang=="zh-CN" and path!="/zh/" else "/"),(title,path)]
    graph=[organization(), {"@type":"WebPage", "@id":url+"#page", "url":url, "name":title, "description":summary, "inLanguage":lang, "isPartOf":{"@id":SITE+"/#website"}, "publisher":{"@id":SITE+"/#organization"}}]
    if main:
        main={"@id":url+"#entity", **main}
        graph.append(main);graph[1]["mainEntity"]={"@id":main["@id"]}
        if main["@type"]=="ItemList":graph[1]["@type"]="CollectionPage"
    graph.extend(extra_graph)
    if path!="/":
        graph.append({"@type":"BreadcrumbList", "itemListElement":[{"@type":"ListItem","position":i+1,"name":name,"item":SITE+target} for i,(name,target) in enumerate(crumbs)]})
    trail=''.join(f'<li><a href="{esc(target)}">{esc(name)}</a></li>' for name,target in crumbs[:-1])+f'<li><a href="{esc(crumbs[-1][1])}" aria-current="page">{esc(crumbs[-1][0])}</a></li>'
    alternate_paths = alternate_map(alternatives)
    alternate=''.join(f'<link rel="alternate" hreflang="{esc(locale)}" href="{SITE}{esc(target)}">' for locale,target in alternate_paths.items())
    alternate+=f'<link rel="alternate" type="application/atom+xml" href="/feed.xml" title="{FEED_TITLE}"><link rel="alternate" type="application/feed+json" href="/feed.json" title="{FEED_TITLE}">'
    robots="index,follow,max-image-preview:large" if index else "noindex,follow"
    # The not-found page is served at every missing address, so it claims no URL of its own.
    identity=f'<link rel="canonical" href="{url}">' if canonical else ''
    og_url=f'<meta property="og:url" content="{url}">' if canonical else ''
    full_title=page_title(title)
    snippet=meta_description(summary,lang,context)
    switch_to=alternate_paths.get('en' if lang.startswith('zh') else 'zh-CN') or None
    breadcrumbs=f'<nav class="breadcrumbs{" vh" if landing else ""}" aria-label="Breadcrumb"><ol>{trail}</ol></nav>'
    # A landing page lays out its own full-width sections; everything else shares the reading column.
    content=f'<main id="content" tabindex="-1">{"" if path=="/" else breadcrumbs}{body}</main>' if landing else f'<main id="content" class="reading-shell">{breadcrumbs}{body}</main>'
    skip='跳到正文' if lang.startswith('zh') else 'Skip to content'
    # Only the homepage has its own search window; other wide pages keep the header search.
    body_class=''if not landing else ' class="home"' if path in ('/','/zh/') else ' class="home list-page"'
    document=f'''<!doctype html><html lang="{lang}" data-site="cua"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(full_title)}</title>{site_shell.head_assets(lang)}<meta name="description" content="{esc(snippet)}"><meta name="robots" content="{robots}">{identity}{alternate}<meta property="og:title" content="{esc(full_title)}"><meta property="og:description" content="{esc(snippet)}">{og_url}<meta property="og:type" content="website"><meta property="og:site_name" content="AwesomeCUA"><meta property="og:locale" content="{"zh_CN" if lang=="zh-CN" else "en_US"}"><meta property="og:image" content="{SITE}/social.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="AwesomeCUA — Computer-use agents. Papers, data, and tools."><meta name="twitter:card" content="summary_large_image"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{site_shell.asset("/pages.css")}"><script type="application/ld+json">{jsonld({"@context":"https://schema.org","@graph":graph})}</script>{home_page.legacy_redirect_script() if path=="/" else ""}</head><body{body_class}><a class="skip" href="#content">{skip}</a>{site_shell.top(path=path,lang=lang,lang_href=switch_to,live=landing)}{content}{site_shell.bottom(lang=lang,lang_href=switch_to,live=landing)}</body></html>'''
    return document


def resource_schema(record, zh=False):
    entity={"@type":"ScholarlyArticle" if record["kind"] in {"paper","survey"} else "CreativeWork", "name":record["name"], "description":zh_summary(record) if zh else description(record), "url":SITE+(zh_resource_path(record) if zh else resource_path(record)), "sameAs":record["url"], "identifier":record["id"]}
    if zh:entity["inLanguage"]="zh-CN"
    if record["authors"]:entity["author"]=[{"@type":"Person","name":name} for name in record["authors"]]
    if record["published_at"]:entity["datePublished"]=record["published_at"]
    if record["updated_at"]:entity["dateModified"]=record["updated_at"]
    if record["topics"]:entity["keywords"]=record["topics"]
    if record["kind"]=="dataset" and len(description(record))>=50:entity["@type"]="Dataset"
    return entity


def listing(rows,*,zh=False,anchor=True):
    """Reviewed records as the rows of the homepage search window; a category does not label them by kind."""
    def row(r):
        # The filter reads the visible name, repo and platform label; data-env adds the platforms a "+2" label hides.
        facets=home_page.env_facets(r['environments'])
        words=dict.fromkeys([*r['environments'],*(home_page.ENV_ZH[f] if zh else home_page.ENV_LABEL[f] for f in facets)])
        attrs=f' data-env="{esc(" ".join(words).lower())}"' if words else ''
        return home_page.compact_row({**r,'href':r.get('href') or localized_path(r,zh),'summary':description(r)},zh,date=record_date_text(r) or '',attrs=attrs,anchor=anchor,kind=False)
    return ''.join(row(r) for r in rows)


def list_head(title,intro,links):
    return f'<header class="wrap list-head"><h1>{esc(title)}</h1><p class="list-intro">{intro}</p><div class="list-stats">{links}</div></header>'


def category_body(kind,label,selected,featured,*,zh=False,total=None,pager='',guide=''):
    """One category: its head with the definition, the guide (page 1), the featured rows if it has any, then every reviewed record with an in-page filter."""
    tr=lambda en,cn:cn if zh else en
    name=home_page.KINDS[kind][2] if zh else label.lower()
    count=f'{total if total is not None else len(selected):,}'
    links=f'<span><strong>{count}</strong> {tr("reviewed","条已审核")}</span>'
    if kind in PROFILE_KEYS:links+=f'<a href="/compare/{"benchmarks" if kind=="benchmark" else "datasets"}/">{tr("Compare specifications","比较规格")}</a>'
    wider=f'/explore/?{"lang=zh&" if zh else ""}kind={kind}#catalog'
    search=tr('Search all records in this category','搜索此类别的全部记录')
    links+=f'<a href="{esc(wider)}">{search}</a><a href="{"/zh/catalog/" if zh else "/catalog/"}">{tr("All categories","全部类别")}</a>'
    intro=tr(f'{esc(category_guides.definition(kind,False))} The catalog lists {count} reviewed {esc(name)}, each linked to its primary evidence.',f'{esc(category_guides.definition(kind,True))}目录收录 {count} 条已审核{esc(name)}，每条都链接到一手证据。')
    body=list_head(category_title(name,'zh' if zh else 'en'),intro,links)+guide
    if featured:
        body+=f'<section class="wrap list-all" aria-labelledby="list-featured-h" data-list-featured><div class="sec-head"><div><h2 id="list-featured-h">{tr("Featured","精选")}</h2></div></div><ul class="rows list-rows" data-single>{listing(featured,zh=zh,anchor=False)}</ul></section>'
    tools=''
    # A short list needs no filter.
    if len(selected)>=8:
        hint=tr('Filter by name, repo or platform','按名称、仓库或平台筛选')
        tools=(f'<div class="list-tools js-only"><span class="list-filter">{site_shell.ic("search")}<label class="vh" for="list-filter">{hint}</label><input id="list-filter" type="search" data-list-filter placeholder="{hint}" autocomplete="off"></span>'
               f'<span class="select sort"><label class="vh" for="list-sort">{tr("Sort","排序")}</label><select id="list-sort" data-list-sort><option value="mentions">{tr("Most mentioned","提及最多")}</option><option value="name">A–Z</option></select>{site_shell.ic("down")}</span></div>')
    template=tr(f'{{n}} of {{total}} {esc(name)}',f'{{total}} 条{esc(name)}中的 {{n}} 条')
    empty=tr(f'No {esc(name)} match that filter.',f'没有符合筛选条件的{esc(name)}。')
    body+=(f'<section class="wrap list-all" aria-labelledby="list-h" data-list><div class="sec-head list-all-head"><div><h2 id="list-h">{tr(f"All {esc(name)}",f"全部{esc(name)}")}</h2></div>{tools}</div>'
           f'<p class="list-status" role="status" data-list-status data-template="{template}"></p><ul class="rows list-rows" data-single data-list-rows>{listing(selected,zh=zh)}</ul>'
           f'<p class="list-empty" data-list-empty hidden>{empty} <a href="{esc(wider)}">{search}</a></p></section>')
    if pager:body+=pager
    if tools:body+='<script type="module" src="/listing.js"></script>'
    return body


def catalog_body(reviewed,awaiting,candidates,*,zh=False):
    tr=lambda en,cn:cn if zh else en
    def href(kind):
        if zh:return '/zh/papers/' if kind=='paper' else f'/zh/categories/{kind}/'
        return f'/categories/{kind}/'
    types='<ul class="cat-tiles">'+''.join(f'<li><a href="{href(kind)}">{site_shell.ic(home_page.KINDS[kind][3])}<b>{esc(home_page.KINDS[kind][2] if zh else name)}</b><span>{sum(r["kind"]==kind for r in reviewed):,} {tr("reviewed","条已审核")}</span></a></li>' for kind,name in KINDS.items())+'</ul>'
    guides=[('/zh/topics/','主题','按主题浏览研究与资源'),('/zh/papers/','论文','已审核的计算机使用与 GUI 智能体研究论文'),('/guides/','指南','智能体、评测基准与训练数据'),('/zh/data/','数据','下载有来源依据的目录'),('/coverage/','覆盖','覆盖情况与未解决的缺口')] if zh else [('/topics/','Topics','Research and assets by topic'),('/papers/','Papers','Reviewed computer-use and GUI-agent research papers'),('/guides/','Guides','Agents, benchmarks, and training data'),('/data/','Data','Download the source-backed catalog'),('/coverage/','Coverage','Coverage and unresolved gaps')]
    guide_tiles='<ul class="cat-tiles cat-tiles-5">'+''.join(f'<li><a href="{target}"><b>{title}</b><span>{text}</span></a></li>' for target,title,text in guides)+'</ul>'
    stats=f'<span><strong>{len(reviewed):,}</strong> {tr("reviewed records","条已审核记录")}</span><span><strong>{awaiting:,}</strong> {tr("catalog records awaiting review","条目录记录待审核")}</span>'
    stats+=f'<span>尚未收录的扫描发现 <strong>{candidates:,}</strong> 条</span>' if zh else f'<span><strong>{candidates:,}</strong> scan finds not yet in the catalog</span>'
    stats+=f'<a href="{"/explore/?lang=zh#catalog" if zh else "/explore/#catalog"}">{tr("Search and filter every record","搜索和筛选全部记录")}</a>'
    body=list_head(tr('Explore the computer-use agent ecosystem','探索计算机使用智能体生态'),tr('AwesomeCUA connects research papers, GUI models, training datasets, benchmarks, learning resources, engineering tools, products, and publishers with their original sources.','AwesomeCUA 将研究论文、GUI 模型、训练数据集、评测基准、学习资源、工程工具、产品和发布方与其一手来源连接起来。'),stats)
    body+=f'<section class="wrap list-all" aria-labelledby="cat-types-h"><div class="sec-head"><div><h2 id="cat-types-h">{tr("Browse by resource type","按资源类型浏览")}</h2></div></div>{types}</section>'
    body+=f'<section class="wrap list-all" aria-labelledby="cat-guides-h"><div class="sec-head"><div><h2 id="cat-guides-h">{tr("Research and practical guides","研究与实用指南")}</h2></div></div>{guide_tiles}</section>'
    return body


def publication_body(record, zh=False):
    pub=publication(record)
    if not pub:return ''
    tr=lambda en,cn:cn if zh else en
    language='zh' if zh else 'en'
    label=lambda key:field_label(key,language)
    omitted=AUTHORS_OMITTED[1 if zh else 0]
    facts=[(label('title'),pub['title']),(label('authors'),None if authors_omitted(record) else ', '.join(pub['authors'])),
           (tr('Publication date (recorded precision)','发表日期（按记录精度）'),format_date_parts(pub['date_parts']))]
    facts+=[(label(key),pub.get(key)) for key in ('venue','publisher','series','volume','issue','pages','doi')]
    rows=[(key,esc(value)) for key,value in facts if value]
    if authors_omitted(record):rows.insert(1,(label('authors'),'<a href="'+safe_href(pub['url'])+'">'+esc(omitted)+'</a>'))
    body='<section class="publication-record"><h2>'+tr('Publication record','发表记录')+'</h2><dl class="page-facts">'+''.join('<div><dt>'+esc(key)+'</dt><dd>'+value+'</dd></div>' for key,value in rows)+'</dl>'
    body+='<p><a href="'+safe_href(pub['url'])+'">'+tr('Publication source ↗','发表来源 ↗')+'</a>'
    if pub.get('pdf_url'):body+=' · <a href="'+safe_href(pub['pdf_url'])+'">'+tr('Publisher or author PDF ↗','出版方或作者 PDF ↗')+'</a>'
    body+='</p><p><a href="'+resource_path(record)+'publication-citation.bib" download>'+tr('Publication BibTeX','发表版 BibTeX')+'</a> · <a href="'+resource_path(record)+'publication-citation.csl.json" download>'+tr('Publication CSL JSON','发表版 CSL JSON')+'</a></p>'
    if record['id'].startswith('arxiv:'):
        body+='<p>'+tr('This publication is a separately recorded edition of the same work. Its citation uses its own title, authors and date; the retained arXiv citation above is unchanged.','该发表版本是同一作品单独记录的版本，引用时使用其自身的标题、作者和日期；上方保留的 arXiv 引用保持不变。')+'</p>'
    for key in ('date_basis','event_dates','notes'):
        if pub.get(key):body+='<p>'+label(key)+tr(': ','：')+esc(pub[key])+'</p>'
    body+='</section>'
    return body


def incoming_relations(rows):
    incoming=defaultdict(list)
    for source in rows:
        for relation in source['relations']:
            incoming[relation['target_id']].append({'source_id':source['id'],**relation})
    return incoming


def reviewer_hold(record, decision):
    """Display only a current ledger hold for this metadata-only identity."""
    if (record.get('review_status') == 'metadata_verified' and isinstance(decision, dict)
            and decision.get('id') == record['id'] and decision.get('cause') == 'reviewer_hold'
            and isinstance(decision.get('reason'), str) and decision['reason'].strip()):
        return decision['reason']
    return None


def markdown_literal(text):
    """Keep a plain-text editorial reason literal in the Markdown reading view."""
    return re.sub(r'([\\`*_{}\[\]()#+\-.!|~=])', r'\\\1', html.escape(text, quote=False))


RELATION_LABELS = {'documented_by':('documented by','文档来源'),'introduced_by':('introduced by','提出于'),'published_by':('published by','发布方'),
                   'variant_of':('variant of','变体来源'),'component_of':('component of','所属项目'),'uses':('uses','使用'),
                   'trained_on':('trained on','训练数据'),'evaluates':('evaluates','评测对象')}
INCOMING_LABELS = {'documented_by':('Documented resource','相关文档资源'),'introduced_by':('Introduced resource','提出的资源'),'published_by':('Published resource','发布的资源'),
                   'variant_of':('Model variant','模型变体'),'component_of':('Component','组成部分'),'uses':('uses','使用方'),
                   'trained_on':('trained on','以此训练'),'evaluates':('evaluates','评测方')}
LICENSE_SLOTS = {'code':('Code','代码'),'data':('Data','数据'),'weights':('Weights','权重'),'document':('Document','文档')}
EVIDENCE_METHODS = {'editorial_primary_review':'编辑一手来源审阅','arxiv_api':'arXiv API','license_header':'许可证文件头',
                    'huggingface_card':'Hugging Face 卡片','huggingface_api':'Hugging Face API','github_repository_identity':'GitHub 仓库身份',
                    'huggingface_repository_identity':'Hugging Face 仓库身份','dataverse_api':'Dataverse API'}


def zh_resource_path(record):
    """The Chinese twin of a resource page; only reviewed, in-scope records have one."""
    return '/zh'+resource_path(record)


def localized_path(record, zh=False):
    # Chinese pages link to the Chinese twin when it exists and to the English page otherwise.
    return zh_resource_path(record) if zh and eligible(record) else resource_path(record)


def kind_crumb(kind, zh=False):
    if not zh:return (KINDS[kind],f'/categories/{kind}/')
    return (home_page.KINDS[kind][2],'/zh/papers/' if kind=='paper' else f'/zh/categories/{kind}/')


def resource_crumbs(record, zh=False):
    if zh:return [("AwesomeCUA","/zh/"),("目录","/zh/catalog/"),kind_crumb(record["kind"],True),(record["name"],zh_resource_path(record))]
    return [("AwesomeCUA","/"),("Catalog","/catalog/"),kind_crumb(record["kind"]),(record["name"],resource_path(record))]


def resource_context(record, zh=False):
    """A sentence that lengthens a short resource summary into a usable search snippet."""
    if zh:
        environments='、'.join(PLATFORMS.get(env,(env,env))[1] for env in record['environments'] if env!='unspecified')
        return f'{home_page.KINDS[record["kind"]][2]}' + (f'，运行环境：{environments}' if environments else '') + '。附一手来源、许可证记录与审阅状态。'
    environments=', '.join(ENVIRONMENT_LABELS.get(env,env) for env in record['environments'] if env!='unspecified')
    return f'{KIND_SINGULAR[record["kind"]]} for {environments + " " if environments else ""}computer-use agents, with primary sources, license records and review status.'


def resource_body(record, lookup, incoming=None, pending_review=None, zh=False):
    r=record
    tr=lambda en,cn:cn if zh else en
    sep=tr(', ','、')
    own=localized_path(r,zh)
    kind_label=home_page.KINDS[r["kind"]][2] if zh else KIND_SINGULAR[r["kind"]]
    status=tr("AI-assisted editorial review against a primary source","已对照一手来源完成 AI 辅助编辑审阅") if eligible(r) else tr("Bibliographic metadata verified; editorial approval is pending","书目元数据已核实，编辑审阅待完成")
    lead=zh_summary(r) if zh else description(r)
    body=f'<div class="eyebrow">{esc(kind_label)}</div><h1>{esc(r["name"])}</h1><p class="answer-lead">{esc(lead)}</p><p class="review-notice">{esc(status)}{tr(".","。")}</p><div class="page-actions"><a class="button primary" href="{safe_href(r["url"])}">{tr("Original source ↗","原始来源 ↗")}</a><a class="button secondary" href="{own}index.md">{tr("Read as Markdown","Markdown 版本")}</a><a class="button secondary" href="{resource_path(r)}record.json">{tr("Record JSON","记录 JSON")}</a></div>'
    hold=reviewer_hold(r,pending_review)
    if hold:
        body+='<details class="review-hold" open><summary>'+tr('Recorded reviewer hold','审阅暂缓记录')+'</summary><p>'+esc(hold)+'</p><p><a href="/downloads/coverage.json">'+tr('Review ledger','审阅台账')+'</a></p></details>'
    environments=[PLATFORMS.get(env,(env,env))[1] if zh else ENVIRONMENT_LABELS.get(env,env) for env in r["environments"] if env!="unspecified"]
    topic_labels=TOPIC_CATALOG
    topics=[topic_name(topic,'zh') for topic in r["topics"]] if zh else [topic_labels.get(topic,{}).get("en") or topic.replace("-"," ").capitalize() for topic in r["topics"]]
    # A row with nothing to say is left out rather than shown as "Not recorded".
    facts=[(tr("Resource type","资源类型"),kind_label),(tr("Environment","运行环境"),sep.join(environments)),(tr("Topics","主题"),sep.join(topics)),(tr("Record publication date","记录的发布日期"),record_date_text(r)),(tr("Evidence retrieved","证据获取日期"),(r["last_verified_at"] or "")[:10]),(tr("Resource ID","资源 ID"),r["id"])]
    facts=[(label,value) for label,value in facts if value]
    body+='<h2>'+tr('What is this resource?','这是什么资源？')+'</h2><dl class="page-facts">'+''.join(f'<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k,v in facts)+'</dl>'
    snapshot=r['details'].get('arxiv_snapshot')
    if snapshot:
        version=(f'<a href="{safe_href(snapshot["versioned_url"])}">arXiv v{esc(snapshot["version"])}</a>' if snapshot.get('versioned_url') else tr('Version not recorded','未记录版本'))
        body+='<h2>'+tr('Recorded paper version','记录的论文版本')+'</h2><p>'+version+'</p>'
        if snapshot.get('updated_at'):body+='<p>'+tr('Version updated: ','版本更新于 ')+esc(snapshot['updated_at'])+tr('.','。')+'</p>'
        body+='<p>'+tr('This identifies the retained arXiv metadata snapshot; newly observed changes require separate review.','此处标识保留的 arXiv 元数据快照；之后发现的变更另行审阅。')+'</p>'
        if snapshot.get('abstract_sha256'):body+='<details><summary>'+tr('Abstract fingerprint','摘要指纹')+'</summary><code>'+esc(snapshot['abstract_sha256'])+'</code></details>'
    if authors_omitted(r):body+='<h2>'+tr('Authors','作者')+'</h2><p class="authors-omitted"><a href="'+safe_href((snapshot or {}).get('versioned_url') or r["url"])+'">'+esc(AUTHORS_OMITTED[1 if zh else 0])+'</a></p>'
    elif r["authors"]:body+='<h2>'+tr('Authors','作者')+'</h2><p>'+esc(', '.join(r["authors"]))+'</p>'
    preferred='arxiv:'+r['identifiers']['preferred_arxiv'] if r['identifiers'].get('preferred_arxiv') else None
    if preferred and preferred in lookup:
        target='<a href="'+localized_path(lookup[preferred],zh)+'">'+esc(lookup[preferred]['name'])+'</a>'
        body+='<h2>'+tr('Preferred paper record','首选论文记录')+'</h2><p>'+tr('The retained source identifies this as an alternate bibliographic record. Follow '+target+' for the preferred arXiv identity.','保留的来源将此记录标为备用书目记录。首选的 arXiv 身份见 '+target+'。')+'</p>'
    if r['kind'] in {'paper','survey'}:
        body+='<h2>'+tr('Cite this paper','引用本文')+'</h2><p><a href="'+resource_path(r)+'citation.bib" download>'+tr('Download BibTeX','下载 BibTeX')+'</a> · <a href="'+resource_path(r)+'citation.csl.json" download>'+tr('Download CSL JSON','下载 CSL JSON')+'</a></p><p>'+tr('Citations preserve the selected source edition, its authors and recorded date precision. Unrecorded venues and identifiers are omitted.','引用文件保留所选来源版本、其作者和记录的日期精度；未记录的发表场所和标识符不写入。')+'</p>'
        if authors_omitted(r):body+='<p>'+tr('This catalog does not list the authors, so these citation files omit them; take the author list from the paper.','本目录不列出作者，引用文件也不含作者；作者列表请以论文为准。')+'</p>'
        body+=publication_body(r,zh)
    if r["kind"] not in {"paper","survey"} or any(r["licenses"].values()):
        body+='<h2>'+tr('What licenses are recorded?','记录了哪些许可证？')+'</h2><p>'+tr('Code, training data, weights, and documents each have their own entry. A blank entry means the license is unknown.','代码、训练数据、权重和文档各自单独记录许可证。“未记录”表示许可证未知。')+'</p><dl class="page-facts">'
        for slot,l in r["licenses"].items():
            value=f'<a href="{safe_href(l["url"])}">{esc(l["declared"] if isinstance(l["declared"],str) else ", ".join(l["declared"]))}</a> {tr("(","（")}{esc(l["basis"])}{tr(")","）")}' if l else tr("Not recorded","未记录")
            body+=f'<div><dt>{esc(LICENSE_SLOTS.get(slot,(slot.title(),slot))[1 if zh else 0])}</dt><dd>{value}</dd></div>'
        body+='</dl>'
    if r['details'].get('license_review'):
        body+='<h2>'+tr('License review notes','许可证审阅备注')+'</h2><ul>'+''.join('<li><strong>'+esc(LICENSE_SLOTS.get(slot,(slot.title(),slot))[1 if zh else 0])+tr(':','：')+'</strong> '+esc(review['reason'])+' '+''.join(f'<a href="{safe_href(url)}">{tr("Source","来源")} {i+1}</a> ' for i,url in enumerate(review['evidence_urls']))+'</li>' for slot,review in r['details']['license_review'].items())+'</ul>'
    body+=resource_profile_html(r,zh)
    details=[(k,v) for k,v in r["details"].items() if k not in {*PROFILE_KEYS.values(),'arxiv_snapshot','publication','license_review'} and v is not None and v!=[] and v!=""]
    if details:
        body+='<h2>'+tr('Recorded specifications','记录的规格')+'</h2><dl class="page-facts">'+''.join(f'<div><dt>{esc(k.replace("_"," "))}</dt><dd>{esc(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,bool)) else v)}</dd></div>' for k,v in details)+'</dl>'
    if eligible(r) and r['topics']:
        language='zh' if zh else 'en'
        body+='<h2>'+tr('Explore related topics','相关主题')+'</h2><div class="library-topics">'+''.join('<a href="'+topic_path(topic,language)+'">'+esc(topic_name(topic,language))+'</a>' for topic in r['topics'])+'</div>'
    if r["notes"]:body+='<h2>'+tr('Scope and limitations','范围与局限')+'</h2><p>'+esc(r["notes"])+'</p>'
    if r["relations"]:
        body+='<h2>'+tr('Related resources','相关资源')+'</h2><ul>'+''.join(f'<li>{esc(RELATION_LABELS.get(rel["type"],(rel["type"].replace("_"," "),)*2)[1 if zh else 0])}{tr(": ","：")}<a href="{localized_path(lookup[rel["target_id"]],zh)}">{esc(lookup[rel["target_id"]]["name"])}</a></li>' for rel in r["relations"] if rel["target_id"] in lookup)+'</ul>'
    backlinks=(incoming or {}).get(r['id'],[])
    if backlinks:
        body+='<h2 id="connected-assets">'+tr('Connected assets','关联资源')+'</h2><p>'+tr('These links come from reviewed resource records.','这些链接来自已审阅的资源记录。')+'</p><ul>'
        for rel in backlinks:
            source=lookup[rel['source_id']]
            relation=INCOMING_LABELS.get(rel['type'],(rel['type'].replace('_',' '),)*2)[1 if zh else 0]
            kind=home_page.KINDS[source["kind"]][2] if zh else KINDS[source["kind"]]
            body+=f'<li>{esc(relation)}{tr(": ","：")}<a href="{localized_path(source,zh)}">{esc(source["name"])}</a> · {esc(kind)} · <a href="{safe_href(rel["evidence_url"])}">{tr("relationship evidence","关系证据")}</a></li>'
        body+='</ul>'
    body+='<h2>'+tr('Primary evidence and verification','一手证据与核查')+'</h2><p>'+tr('Use the original publication or publisher page when citing claims about the resource.','引用与该资源有关的说法时，请以原始论文或发布方页面为准。')+'</p><ol class="source-list">'
    for ev in r["evidence"]:
        method=EVIDENCE_METHODS.get(ev["method"],ev["method"].replace("_"," ")) if zh else ev["method"].replace("_"," ")
        retrieved=tr(f'Retrieved {esc(ev["retrieved_at"])}. Supports: {esc(", ".join(ev["supports"]))}.',f'获取于 {esc(ev["retrieved_at"])}。支持字段：{esc("、".join(ev["supports"]))}。')
        body+=f'<li><a href="{safe_href(ev["url"])}">{esc(method)}</a><p>{retrieved}</p><details><summary>{tr("Content fingerprint","内容指纹")}</summary><code>{esc(ev["sha256"])}</code></details></li>'
    body+='</ol><h2>'+tr('Suggest a correction','提交更正')+'</h2><p>'
    body+=tr('<a href="'+SOURCE_REPO+'/issues/new?template=resource.yml">Open a source-backed correction</a>. Include this record ID and the original source. Read our <a href="/about/">editorial policy</a> and <a href="/coverage/">coverage boundaries</a>.',
             '<a href="'+SOURCE_REPO+'/issues/new?template=resource.yml">提交有来源依据的更正</a>，并附上此记录 ID 和原始来源。另见<a href="/about/">收录方法</a>与<a href="/coverage/">覆盖范围</a>。')+'</p>'
    return body+site_shell.star_note(zh)


def resource_markdown(r, pending_review=None, level=1):
    # `level` is the record's heading level: 1 in its own index.md, 2 inside a per-kind or library file.
    h1,h2,h3='#'*level,'#'*(level+1),'#'*(level+2)
    lines=[f'{h1} {r["name"]}', '', description(r), '', f'- Catalog URL: {SITE}{resource_path(r)}', f'- Original source: {r["url"]}', f'- Kind: {r["kind"]}', f'- Review: {r["review_status"]}', f'- Scope: {r["scope"]}', f'- Environments: {", ".join(r["environments"])}', f'- Topics: {", ".join(r["topics"])}', f'- Evidence checked: {r["last_verified_at"]}', f'- ID: {r["id"]}']
    if r["notes"]:lines+=['', h2+' Limitations', '', r["notes"]]
    lines+=['',f'- Record JSON: {SITE}{resource_path(r)}record.json']
    hold=reviewer_hold(r,pending_review)
    if hold:
        lines+=['',h2+' Recorded reviewer hold','',markdown_literal(hold),'',f'- Review ledger: {SITE}/downloads/coverage.json']
    if authors_omitted(r):lines+=['',h2+' Authors','',f'[{AUTHORS_OMITTED[0]}]({(r["details"].get("arxiv_snapshot") or {}).get("versioned_url") or r["url"]})']
    elif r["authors"]:lines+=['',h2+' Authors','',', '.join(r["authors"])]
    if r['kind'] in {'paper','survey'}:
        lines+=['',h2+' Citation exports','',f'- BibTeX: {SITE}{resource_path(r)}citation.bib',f'- CSL JSON: {SITE}{resource_path(r)}citation.csl.json']
    pub=publication(r)
    if pub:
        lines+=['',h2+' Publication record','', '- '+field_label('title')+': '+pub['title'], '- '+(AUTHORS_OMITTED[0]+' ('+pub['url']+')' if authors_omitted(r) else field_label('authors')+': '+', '.join(pub['authors'])),
                '- Publication date (recorded precision): '+(format_date_parts(pub['date_parts']) or 'not recorded'),
                '- Publication source: '+pub['url'],
                '- Publication BibTeX: '+SITE+resource_path(r)+'publication-citation.bib',
                '- Publication CSL JSON: '+SITE+resource_path(r)+'publication-citation.csl.json']
        for key in ('venue','publisher','series','volume','issue','pages','doi','date_basis','event_dates','identity_basis','notes'):
            if pub.get(key):lines.append('- '+field_label(key)+': '+pub[key])
        lines+=['- Publication evidence: '+', '.join(pub['evidence_urls'])]
    snapshot=r['details'].get('arxiv_snapshot')
    if snapshot:
        lines+=['',h2+' Recorded arXiv snapshot','',
                '- Version: '+(str(snapshot['version']) if snapshot.get('version') else 'not recorded'),
                '- Version source: '+(snapshot.get('versioned_url') or 'not recorded'),
                '- First submission: '+(snapshot.get('submitted_at') or 'not recorded'),
                '- Version updated: '+(snapshot.get('updated_at') or 'not recorded'),
                '- Abstract SHA-256: '+(snapshot.get('abstract_sha256') or 'not recorded'),
                '- Abstract hash normalization: '+snapshot['abstract_hash_method']]
    profile=r['details'].get(PROFILE_KEYS.get(r['kind']))
    if profile:
        lines+=['',h2+' Structured profile','']
        for key,value in profile.items():
            if key in {'counts','evidence_urls','notes'}:continue
            lines.append('- '+field_label(key)+': '+(', '.join(value) if isinstance(value,list) and value else str(value) if value else 'not recorded'))
        lines+=['',h3+' Count observations','']
        lines += [f'- {count_text(c)} ({c["basis"]}; source: {c.get("reference_url") or c["evidence_url"]})' for c in profile['counts']] or ['No count recorded.']
        lines+=['',profile['notes']]
    lines+=['',h2+' License declarations','']
    for slot,license in r["licenses"].items():lines.append(f'- {slot}: '+(f'{license["declared"]} — {license["url"]}' if license else 'not recorded'))
    for slot,review in r['details'].get('license_review',{}).items():
        lines+=['',f'- {slot} review: '+review['reason'],'  Sources: '+', '.join(review['evidence_urls'])]
    lines+=['',h2+' Primary evidence','']+[f'- {ev["url"]} (retrieved {ev["retrieved_at"]}; SHA-256 {ev["sha256"]})' for ev in r["evidence"]]
    return '\n'.join(line.rstrip() for line in lines)+'\n'


def zh_resource_markdown(record, pending_review=None, level=2, *, paper=False):
    """Keep the full source facts and record order while matching Chinese list summaries."""
    body = resource_markdown(record, pending_review, level)
    body = body.replace('\n' + description(record) + '\n', '\n' + (description(record) if paper else zh_summary(record)) + '\n', 1)
    headings = {'Limitations': '范围记录', 'Recorded reviewer hold': '审核暂缓记录',
                'Authors': '作者', 'Citation exports': '引用文件', 'Publication record': '发表记录',
                'Recorded arXiv snapshot': 'arXiv 版本记录', 'Structured profile': '结构化规格',
                'Count observations': '数量记录', 'License declarations': '许可证信息',
                'Primary evidence': '一手证据'}
    for source, target in headings.items():
        body = re.sub(r'(?m)^(#+) ' + re.escape(source) + r'$', lambda match: match[1] + ' ' + target, body)
    labels = {'Catalog URL': '目录页面', 'Original source': '原始来源', 'Kind': '类型',
              'Review': '审核状态', 'Scope': '范围', 'Environments': '运行环境',
              'Topics': '主题', 'Evidence checked': '证据核查日期', 'ID': 'ID',
              'Record JSON': '完整记录 JSON', 'Review ledger': '审核记录',
              'BibTeX': 'BibTeX', 'CSL JSON': 'CSL JSON', 'Version': '版本',
              'Version source': '版本来源', 'First submission': '首次提交',
              'Version updated': '版本更新日期', 'Abstract SHA-256': '摘要 SHA-256',
              'Abstract hash normalization': '摘要哈希规范化方式',
              'Publication date (recorded precision)': '发表日期', 'Publication source': '发表来源',
              'Publication BibTeX': '发表版 BibTeX', 'Publication CSL JSON': '发表版 CSL JSON',
              'Publication evidence': '发表证据', 'Licenses': '许可证'}
    labels.update(FIELD_LABELS.values())
    for source, target in sorted(labels.items(), key=lambda item: -len(item[0])):
        body = re.sub(r'(?m)^(- )' + re.escape(source) + r':\s?', lambda match: match[1] + target + '：', body)
    values = {
        '类型': home_page.KINDS[record['kind']][2],
        '审核状态': {'curated': '已审核', 'metadata_verified': '仅元数据'}[record['review_status']],
        '范围': {'core': '核心', 'adjacent': '相关研究', 'relevance_pending': '相关性待审阅'}[record['scope']],
        '运行环境': '、'.join(PLATFORMS.get(value, (value, value))[1] for value in record['environments']),
        '主题': '、'.join(topic_name(value, 'zh') for value in record['topics']),
    }
    for label, value in values.items():
        body = re.sub(r'(?m)^(- ' + label + r'：).*$', lambda match: match[1] + value, body)
    slots = {'code': '代码', 'data': '数据', 'document': '文档', 'weights': '权重'}
    body = re.sub(r'(?m)^- (code|data|document|weights): not recorded$', lambda match: f'- {slots[match[1]]}：未记录', body)
    body = re.sub(r'(?m)^- (code|data|document|weights): ', lambda match: f'- {slots[match[1]]}：', body)
    body = re.sub(r'(?m)^- (code|data|document|weights) review: ', lambda match: f'- {slots[match[1]]}审核：', body)
    body = re.sub(r'(?m)^  Sources: ', '  来源：', body)
    body = re.sub(r'(?m)^(- [^：\n]+：)not recorded$', r'\1未记录', body)
    if eligible(record):
        body = body.replace(f'- 目录页面：{SITE}{resource_path(record)}\n', f'- 目录页面：{SITE}{zh_resource_path(record)}\n', 1)
    body = re.sub(r'(?m)^(- .+?)(?: \(computed\))? \((reported|computed); source: (\S+)\)$', lambda match: f'{match[1]}（{COUNT_BASIS[match[2]][1]}；来源：{match[3]}）', body)
    body = body.replace('\nNo count recorded.\n', '\n未记录数量。\n')
    body = re.sub(r'(?m)^(- \S+) \(retrieved ([^;]+); SHA-256 ([0-9a-f]+)\)$', r'\1（获取于 \2；SHA-256：\3）', body)
    return body


def zh_resource_page_markdown(record, pending_review=None):
    """The Chinese page's own Markdown twin: the Chinese record, pointing at the Chinese page and its English twin."""
    body = zh_resource_markdown(record, pending_review, level=1)
    page_line = f'- 目录页面：{SITE}{zh_resource_path(record)}\n'
    if page_line not in body:raise ValueError('Chinese resource Markdown lacks its page line: '+record['id'])
    return body.replace(page_line, page_line + f'- English：{SITE}{resource_path(record)}index.md\n', 1)


def repository_stars():
    """Star counts the publication workflow read at build time; without them every star link shows its label alone."""
    try:
        values=json.loads(os.environ.get('AWESOMECUA_REPO_STARS') or '{}')
    except json.JSONDecodeError:
        return {}
    if not isinstance(values,dict):
        return {}
    return {repo:count for repo,count in values.items() if type(count) is int and count>0}


def asset_version(destination):
    # Page URLs carry this fingerprint, so a stylesheet or script change reaches every page despite the CDN cache.
    digest=hashlib.sha256()
    for name in ('assets/site.css','assets/site.js','pages.css'):
        digest.update((destination/name).read_bytes())
    return digest.hexdigest()[:12]


def declare_markdown_twins(destination, manifest):
    """Name each page's index.md in its <head> once the build has written every twin, then refresh the page fingerprint."""
    for item in manifest:
        path=item['path']
        twin=destination/path.lstrip('/')/'index.md'
        if not path.endswith('/') or path=='/survey/' or not twin.is_file():continue
        target=destination/path.lstrip('/')/'index.html'
        content=target.read_bytes()
        link=f'<link rel="alternate" type="text/markdown" href="{path}index.md">'.encode()
        if link in content:continue
        content=content.replace(b'</head>',link+b'</head>',1)
        target.write_bytes(content)
        item['sha256']=hashlib.sha256(content).hexdigest()


def build_search_pages(destination, rows, coverage, root, *, survey_page=None):
    lookup={r["id"]:r for r in rows}
    pending_reviews={item['id']:item for item in coverage.get('pending_editorial',[])}
    incoming=incoming_relations(rows)
    titles=resource_titles(rows)
    zh_titles=zh_resource_titles(rows,titles)
    reviewed=[r for r in rows if eligible(r)]
    # Headline counts are curated resources; records awaiting review and discovered candidates are labelled separately.
    awaiting,candidates=coverage['metadata_only_records'],coverage['unindexed_candidates']
    snapshot=coverage["as_of_utc"]
    review_times=review_dates(root)
    def modified(records):return latest(records,review_times)
    candidate_manifest=root/'data/github-candidates-manifest.json'
    counts=catalog_counts(rows,coverage,json.loads(candidate_manifest.read_text(encoding='utf-8')) if candidate_manifest.exists() else None)
    def full_markdown(record,level):return resource_markdown(record,pending_reviews.get(record['id']),level)
    def zh_category_markdown(record,level):return zh_resource_markdown(record,pending_reviews.get(record['id']),level)
    def zh_paper_markdown(record,level):return zh_resource_markdown(record,pending_reviews.get(record['id']),level,paper=True)
    manifest=[]
    # Sitemap facts per page, kept beside the manifest so its schema and fingerprints stay unchanged.
    sitemap_facts={}
    scan_path=root/'data/scan-status.json'
    scan=json.loads(scan_path.read_text(encoding='utf-8')) if scan_path.exists() else None
    last_scan=scan['finished_at'] if scan else None
    stars=repository_stars()
    site_shell.configure(asset_version=asset_version(destination),stars=stars,last_scan=last_scan,has_survey=bool(survey_page))
    # Stars and scan time change far more often than most pages, so those pages read them from this one small file.
    (destination/'data/site-stamp.json').write_text(json.dumps({'stars':stars,'last_scan':last_scan})+'\n',encoding='utf-8')
    view=home_page.catalog_view(rows,reviewed,coverage,root)
    for filename,zh in (('search-index.json',False),('search-index.zh.json',True)):
        (destination/'data'/filename).write_text(json.dumps(home_page.search_index(view,zh=zh),ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    if survey_page:
        # The reviewed article gains the site header and footer here and is otherwise never normalized.
        survey_page=apply_site_shell(destination/'survey',head=site_shell.head_assets('en'),top=site_shell.top(path='/survey/'),bottom=site_shell.bottom())
        if survey_page != {'path':'/survey/','indexable':True,'sha256':hashlib.sha256((destination/'survey/index.html').read_bytes()).hexdigest()}:
            raise ValueError('Survey page does not match its copied bytes')
        manifest.append(dict(survey_page))
    script_versions={name:hashlib.sha256((destination/name).read_bytes()).hexdigest() for name in ('app.js','compare.js','downloads.js','listing.js')}
    script_src=re.compile(r'''(?P<start><script\b[^>]*\bsrc\s*=\s*)(?P<quote>["'])(?P<path>(?:\./|/)(?:app|compare|downloads|listing)\.js)(?:\?[^"'\r\n]*)?(?P=quote)''')
    def version_script_src(match):
        version=script_versions[Path(match['path']).name]
        return f"{match['start']}{match['quote']}{match['path']}?v={version}{match['quote']}"
    def emit(path,content,index=True,excluded=False,utility=False,lastmod=None,alternates=None):
        # Hash the final bytes, after replacing only the scripts this page uses.
        content=script_src.sub(version_script_src,clean_text(content)).encode('utf-8')
        target=destination/path.lstrip('/')/'index.html' if path.endswith('/') else destination/path.lstrip('/')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
        item={"path":path,"indexable":index,"sha256":hashlib.sha256(content).hexdigest()}
        if excluded:item["scope_excluded"]=True
        if utility:item["utility"]=True
        manifest.append(item)
        # lastmod comes from recorded data times of what the page shows; pages without data dates omit it.
        sitemap_facts[path]={'lastmod':lastmod,'alternates':alternate_map(alternates)}
    for r in rows:
        path=resource_path(r)
        pending_review=pending_reviews.get(r['id'])
        # Connected assets listed on the page come from the records that point at this one.
        shown=[r]+[lookup[rel['source_id']] for rel in incoming.get(r['id'],[]) if rel['source_id'] in lookup]
        # Reviewed records have a Chinese twin; the pair names each other, and x-default is the English page.
        pair={'en':path,'zh-CN':zh_resource_path(r),'x-default':path} if eligible(r) else None
        emit(path,page(titles.get(r["id"],r["name"]),description(r),path,resource_body(r,lookup,incoming,pending_review),resource_schema(r),eligible(r),crumbs=resource_crumbs(r),alternatives=pair,context=resource_context(r)),eligible(r),lastmod=modified(shown),alternates=pair)
        (destination/path.lstrip('/')/'index.md').write_text(clean_text(resource_markdown(r,pending_review)),encoding='utf-8')
        if pair:
            zh_path=pair['zh-CN']
            emit(zh_path,page(zh_titles[r['id']],zh_summary(r),zh_path,resource_body(r,lookup,incoming,pending_review,zh=True),resource_schema(r,zh=True),lang='zh-CN',crumbs=resource_crumbs(r,zh=True),alternatives=pair,context=resource_context(r,zh=True)),lastmod=modified(shown),alternates=pair)
            (destination/zh_path.lstrip('/')/'index.md').write_text(clean_text(zh_resource_page_markdown(r,pending_review)),encoding='utf-8')
        (destination/path.lstrip('/')/'record.json').write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',', ':'))+'\n',encoding='utf-8')
        if r['kind'] in {'paper','survey'}:
            (destination/path.lstrip('/')/'citation.bib').write_text(citation_bibtex(r),encoding='utf-8')
            (destination/path.lstrip('/')/'citation.csl.json').write_text(json.dumps(citation_csl(r),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        else:
            for name in ('citation.bib','citation.csl.json'):(destination/path.lstrip('/')/name).unlink(missing_ok=True)
        if publication(r):
            (destination/path.lstrip('/')/'publication-citation.bib').write_text(citation_bibtex(r,edition='publication'),encoding='utf-8')
            (destination/path.lstrip('/')/'publication-citation.csl.json').write_text(json.dumps(citation_csl(r,edition='publication'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        else:
            for name in ('publication-citation.bib','publication-citation.csl.json'):(destination/path.lstrip('/')/name).unlink(missing_ok=True)
    scope_status=json.loads((root/'data/exclusion-status.json').read_text(encoding='utf-8'))
    for decision in scope_status['decisions']:
        if decision['status']!='excluded':continue
        if decision['id'] in lookup:raise ValueError('An excluded record is present in the active catalog')
        path=resource_path(decision)
        evidence=decision['evidence']
        target=destination/path.lstrip('/')
        target.mkdir(parents=True,exist_ok=True)
        (target/'record.json').write_text(json.dumps({'status':'excluded','id':decision['id'],'reason':decision['reason'],'decision':decision,'ledger_url':SITE+'/downloads/exclusions.json'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        for name in ('citation.bib','citation.csl.json','publication-citation.bib','publication-citation.csl.json'):(target/name).unlink(missing_ok=True)
        body=f'<div class="eyebrow">SCOPE REVIEW</div><h1>{esc(decision["name"])}</h1><p class="answer-lead">This bibliographic record is outside the active AwesomeCUA catalog after a primary-abstract scope review.</p><p>{esc(decision["reason"])}</p><p>The decision concerns relevance to computer-use agents, not research quality. Original metadata remains available in the archive.</p><div class="page-actions"><a class="button primary" href="{safe_href(decision["url"])}">Original paper ↗</a><a class="button secondary" href="/coverage/">Catalog coverage</a></div><dl class="page-facts"><div><dt>Record ID</dt><dd>{esc(decision["id"])}</dd></div><div><dt>Scope reviewed</dt><dd>{esc(decision["reviewed_at"])}</dd></div><div><dt>Source retrieved</dt><dd>{esc(evidence["retrieved_at"])}</dd></div></dl><p><a href="{safe_href(evidence["url"])}">Primary abstract evidence</a> · <a href="/downloads/exclusions.json">Scope-decision ledger</a> · <a href="/downloads/arxiv-archive.jsonl">Raw metadata archive</a></p><details><summary>Source content fingerprint</summary><code>{esc(evidence["sha256"])}</code></details><p>Decisions can be revised through a <a href="'+SOURCE_REPO+'/issues/new?template=resource.yml">source-backed correction</a>.</p>'
        emit(path,page(decision['name'],'A source-backed catalog scope decision; original bibliographic metadata remains preserved.',path,body,index=False,crumbs=[("AwesomeCUA","/"),("Coverage","/coverage/"),(decision['name'],path)]),index=False,excluded=True)
        (destination/path.lstrip('/')/'index.md').write_text(clean_text('\n'.join(['# '+decision['name'],'','Status: excluded from the active CUA catalog after scope review.','',decision['reason'],'','Original paper: '+decision['url'],'Evidence: '+evidence['url'],'Reviewed: '+decision['reviewed_at'],'','Scope decisions: '+SITE+'/downloads/exclusions.json','Raw metadata archive: '+SITE+'/downloads/arxiv-archive.jsonl'])+'\n'),encoding='utf-8')
    category_links='<ul class="category-directory">'+''.join(f'<li><a href="/categories/{kind}/">{esc(name)}</a><span>{sum(r["kind"]==kind for r in reviewed):,} reviewed</span></li>' for kind,name in KINDS.items())+'</ul>'
    catalog_alternatives={'en':'/catalog/','zh-CN':'/zh/catalog/','x-default':'/catalog/'}
    emit('/catalog/',page('Computer-use agent resource directory','Browse source-backed computer-use agent papers, models, datasets, benchmarks, learning resources, tools, products, and publishers.','/catalog/',catalog_body(reviewed,awaiting,candidates),{"@type":"CollectionPage","name":"AwesomeCUA resource directory"},crumbs=[("AwesomeCUA","/"),("Catalog","/catalog/")],alternatives=catalog_alternatives,landing=True),lastmod=modified(rows),alternates=catalog_alternatives)
    emit('/zh/catalog/',page('计算机使用智能体资源目录','浏览有来源依据的计算机使用智能体论文、模型、数据集、评测基准、学习资源、工具、产品和发布方。每条记录都链接到原始来源并标明审核状态，可按类别浏览或搜索全部记录。','/zh/catalog/',catalog_body(reviewed,awaiting,candidates,zh=True),{"@type":"CollectionPage","name":"AwesomeCUA 资源目录"},lang='zh-CN',crumbs=[("AwesomeCUA","/zh/"),("目录","/zh/catalog/")],alternatives=catalog_alternatives,landing=True),lastmod=modified(rows),alternates=catalog_alternatives)
    # GitHub Pages serves /404.html for any missing path; writing it outside emit() keeps it out of the manifest, sitemaps and IndexNow.
    missing=f'<div class="eyebrow">PAGE NOT FOUND</div><h1>This page is not in the catalog</h1><p class="answer-lead">The address may be mistyped, or the page may have been removed, for example when duplicate resource records were merged.</p><div class="page-actions"><a class="button primary" href="/explore/#catalog">Search the catalog</a><a class="button secondary" href="/catalog/">Resource directory</a><a class="button secondary" href="/papers/">Research papers</a></div><h2>Browse by resource type</h2>{category_links}<h2>Report a broken link</h2><p>If a link led you here, <a href="{SOURCE_REPO}/issues/new/choose">open an issue</a> with the address you followed and the page that linked to it. Scope decisions are recorded in the <a href="/coverage/">coverage ledger</a>.</p>'
    (destination/'404.html').write_text(clean_text(page('Page not found','This address does not match a current AwesomeCUA page. Search the catalog, browse resource categories, or report the broken link.','/404.html',missing,index=False,canonical=False)),encoding='utf-8')
    for kind,label in KINDS.items():
        selected=sorted([r for r in reviewed if r['kind']==kind],key=lambda r:r['name'].lower())
        if kind=='paper':
            body=f'<div class="eyebrow">RESOURCE CATEGORY</div><h1>{esc(category_title(label))}</h1><p class="answer-lead">Browse {len(selected)} reviewed {esc(label.lower())} connected to computer-use, GUI, web, and mobile agents. Each entry links to primary evidence and records its scope.</p>'
            body+='<p>The complete bibliography includes metadata-only discoveries awaiting relevance review. They remain accessible in the <a href="/explore/?kind=paper#catalog">interactive catalog</a> and data downloads.</p>'
            # The paginated /papers/ library is the one indexable list of reviewed papers; this category is a hub into it.
            years=Counter(record_year(r) or 'undated' for r in selected);year_links=library_years(rows);topics=Counter(t for r in selected for t in r['topics'])
            body+='<p>The <a href="/papers/">research library</a> lists every reviewed paper and survey once, newest first, with authors, annotations and citations. Start from a publication year or a topic.</p><div class="page-actions"><a class="button primary" href="/papers/">Open the research library</a><a class="button secondary" href="/categories/survey/">Surveys</a></div>'
            body+='<h2>Papers by publication year</h2><nav class="paper-years" aria-label="Papers by publication year">'+''.join(f'<a href="{year_links[y]}">{"Date not recorded" if y=="undated" else y}<span>{years[y]:,}</span></a>' for y in sorted(years,key=lambda y:(y!='undated',y),reverse=True))+'</nav>'
            body+='<h2>Papers by topic</h2><div class="library-topics">'+''.join(f'<a href="{topic_path(t)}">{esc(topic_name(t))} ({n:,})</a>' for t,n in topics.most_common())+'</div>'
            schema={"@type":"CollectionPage","name":category_title(label)}
        if kind=='paper':
            body+=f'<p><a href="/explore/?kind={kind}#catalog">Search all records in this category</a> · <a href="/catalog/">All categories</a></p>'
            pages=[selected]
        else:
            # Most mentioned first, the same order as the homepage; the page offers A-Z.
            selected=sorted(selected,key=lambda r:(-len(view['mentions'].get(r['id'],())),r['name'].casefold()))
            featured=home_page.featured_records(view) if kind=='benchmark' else []
            (destination/f'categories/{kind}').mkdir(parents=True,exist_ok=True)
            (destination/f'categories/{kind}/index.md').write_text(clean_text(kind_markdown(kind,label,selected,site=SITE,snapshot=snapshot,full_markdown=full_markdown,definition=category_guides.definition(kind,False),guide=category_guides.guide_markdown(kind,selected,view,zh=False,snapshot=snapshot))),encoding='utf-8')
            zh_label=home_page.KINDS[kind][2]
            zh_first=destination/f'zh/categories/{kind}/index.md'
            zh_first.parent.mkdir(parents=True,exist_ok=True)
            zh_first.write_text(clean_text(kind_markdown(kind,zh_label,selected,site=SITE,snapshot=snapshot,full_markdown=zh_category_markdown,language='zh',definition=category_guides.definition(kind,True),guide=category_guides.guide_markdown(kind,selected,view,zh=True,snapshot=snapshot))),encoding='utf-8')
            # Long categories split into pages that stay inside the per-page byte budget; the filter works on each page.
            pages=([selected[i:i+CATEGORY_PAGE_SIZE] for i in range(0,len(selected),CATEGORY_PAGE_SIZE)] or [[]])
        for number,members in enumerate(pages,1):
            path=f'/categories/{kind}/' if number==1 else f'/categories/{kind}/page/{number}/'
            zh_path=f'/zh/categories/{kind}/' if number==1 else f'/zh/categories/{kind}/page/{number}/'
            alternatives=None if kind=='paper' else {'en':path,'zh-CN':zh_path,'x-default':path}
            if number>1:
                (destination/path.lstrip('/')).mkdir(parents=True,exist_ok=True)
                markdown=[f'# {category_title(label)}, page {number}','',f'HTML page: {SITE}{path}','',f'Full category annotations: {SITE}/categories/{kind}/index.md','']
                markdown += [f'- {link(r["name"],SITE + resource_path(r))}' for r in members]
                (destination/path.lstrip('/')/'index.md').write_text(clean_text('\n'.join(markdown)+'\n'),encoding='utf-8')
                zh_markdown=[f'# {category_title(home_page.KINDS[kind][2],"zh")}：第 {number} 页', '',
                             f'HTML 页面：{SITE}{zh_path} · {link("English", SITE + path + "index.md")}', '',
                             f'完整类别注释：{SITE}/zh/categories/{kind}/index.md', '']
                zh_markdown += [f'- {link(r["name"],SITE + localized_path(r,True))}：{zh_summary(r)}' for r in members]
                zh_target=destination/zh_path.lstrip('/')/'index.md'
                zh_target.parent.mkdir(parents=True,exist_ok=True)
                zh_target.write_text(clean_text('\n'.join(zh_markdown)+'\n'),encoding='utf-8')
            if kind!='paper':
                def category_link(n,zh=False):
                    prefix='/zh' if zh else ''
                    return f'{prefix}/categories/{kind}/' if n==1 else f'{prefix}/categories/{kind}/page/{n}/'
                en_pager='' if len(pages)==1 else '<nav class="pager" aria-label="Category pages">'+''.join(
                    f'<a href="{category_link(n)}"' + (' aria-current="page"' if n==number else '') + f'>Page {n}</a>' for n in range(1,len(pages)+1))+'</nav>'
                zh_pager='' if len(pages)==1 else '<nav class="pager" aria-label="类别分页">'+''.join(
                    f'<a href="{category_link(n,zh=True)}"' + (' aria-current="page"' if n==number else '') + f'>第 {n} 页</a>' for n in range(1,len(pages)+1))+'</nav>'
                guide,faq_node,_=category_guides.guide(kind,selected,view,zh=False,snapshot=snapshot,url=SITE+path) if number==1 else ('',None,None)
                page_body=category_body(kind,label,members,featured if number==1 else [],total=len(selected),pager=en_pager,guide=guide)
                schema={"@type":"ItemList","name":category_title(label),"numberOfItems":len(members),"itemListElement":[{"@type":"ListItem","position":(number-1)*CATEGORY_PAGE_SIZE+i+1,"url":SITE+resource_path(r),"name":r['name']} for i,r in enumerate(members)]}
            else:
                page_body=body;faq_node=None
            crumbs=[("AwesomeCUA","/"),("Catalog","/catalog/"),(label,f'/categories/{kind}/')]
            if number>1:
                crumbs.append((f'Page {number}',path))
            title=category_title(label)+(f', page {number}' if number>1 else '')
            emit(path,page(title,f'Reviewed {label.lower()} for computer-use and GUI agents, with original sources, platform tags, and license evidence.',path,page_body,schema,crumbs=crumbs,alternatives=alternatives,landing=kind!='paper',extra_graph=[faq_node] if faq_node else ()),lastmod=modified(selected),alternates=alternatives)
            if kind!='paper':
                zh_name=home_page.KINDS[kind][2]
                zh_schema={**schema,"name":category_title(zh_name,"zh")}
                zh_crumbs=[("AwesomeCUA","/zh/"),("目录","/zh/catalog/"),(zh_name,f'/zh/categories/{kind}/')]
                if number>1:
                    zh_crumbs.append((f'第 {number} 页',zh_path))
                zh_title=category_title(zh_name,'zh')+(f'（第 {number} 页）' if number>1 else '')
                zh_guide,zh_faq,_=category_guides.guide(kind,selected,view,zh=True,snapshot=snapshot,url=SITE+zh_path) if number==1 else ('',None,None)
                zh_body=category_body(kind,label,members,featured if number==1 else [],zh=True,total=len(selected),pager=zh_pager,guide=zh_guide)
                emit(zh_path,page(zh_title,f'面向计算机使用与 GUI 智能体的已审核{zh_name}，按目录提及次数排序。每条记录都链接到原始来源，并附平台标签、许可证据与审核状态，便于比较和引用。',zh_path,zh_body,zh_schema,lang='zh-CN',crumbs=zh_crumbs,alternatives=alternatives,landing=True,extra_graph=[zh_faq] if zh_faq else ()),lastmod=modified(selected),alternates=alternatives)
    for kind,plural,title in [('benchmark','benchmarks','Compare GUI-agent benchmark protocols'),('dataset','datasets','Compare GUI-agent training datasets')]:
        path=f'/compare/{plural}/'
        export=profile_export(rows,kind)
        (destination/f'downloads/{plural}-profiles.json').write_text(json.dumps(export,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        emit(path,page(title,f'Compare {plural} by source-reviewed interfaces, scope, counting units, and access information.',path,comparison_body(rows,kind,resource_path),{'@type':'CollectionPage','name':title},crumbs=[("AwesomeCUA","/"),("Catalog","/catalog/"),(title,path)]),lastmod=modified([r for r in rows if r['kind']==kind]))
    papers=sorted([r for r in reviewed if r['kind'] in {'paper','survey'}],key=record_date_text,reverse=True)
    library_count=library_pages(rows)
    for language,title,summary in [
        ('en','Computer-use agent papers and surveys','Browse reviewed computer-use research by publication year, author, environment and topic, with original papers and BibTeX citations.'),
        ('zh','Computer-Use 论文库：按年份浏览论文与综述','按发表年份浏览经过来源审阅的 Computer-Use 与 GUI Agent 论文，查看作者、平台、研究主题和原论文，下载 BibTeX 引用。')]:
        root_crumb=("AwesomeCUA","/zh/" if language=='zh' else "/")
        for number in range(1,library_count+1):
            path=library_path(number,language)
            body,schema=paper_library(rows,lambda r:localized_path(r,language=='zh'),language=language,site_url=SITE,number=number,survey_available=bool(survey_page))
            numbered=(f'{title}, page {number}' if language=='en' else f'{title}（第 {number} 页）') if number>1 else title
            crumbs=[root_crumb,(title,library_path(1,language)),(f'Page {number}' if language=='en' else f'第 {number} 页',path)] if number>1 else None
            alternatives={'en':library_path(number),'zh-CN':library_path(number,'zh'),'x-default':library_path(number)}
            visible=reviewed_papers(rows)[(number-1)*PAGE_SIZE:number*PAGE_SIZE]
            (destination/path.lstrip('/')).mkdir(parents=True,exist_ok=True)
            (destination/path.lstrip('/')/'index.md').write_text(clean_text(library_markdown(number,library_count,visible,len(reviewed_papers(rows)),site=SITE,path_for=lambda n: library_path(n,language),full_markdown=full_markdown if language=='en' else zh_paper_markdown,language=language)),encoding='utf-8')
            # Every library page shows totals and year links over all reviewed papers, so all share their latest date.
            emit(path,page(numbered,summary,path,body,schema,lang='zh-CN' if language=='zh' else 'en',alternatives=alternatives,crumbs=crumbs),lastmod=modified(papers),alternates=alternatives)
    topic_manifest,topic_groups=write_topic_exports(destination,rows,(root/'data/catalog.jsonl').read_bytes())
    for language in ('en','zh'):
        path=topic_path(language=language)
        body,schema=topic_index_body(topic_manifest,language=language,site_url=SITE)
        title='Computer-use research topics' if language=='en' else 'Computer-Use 主题目录'
        summary='Explore source-reviewed computer-use papers, models, datasets, benchmarks and tools by topic.' if language=='en' else '按研究主题浏览已审阅的 Computer-Use 论文、模型、数据、基准与工具，并下载完整主题记录。'
        emit(path,page(title,summary,path,body,schema,lang='zh-CN' if language=='zh' else 'en',alternatives={'en':'/topics/','zh-CN':'/zh/topics/','x-default':'/topics/'}),lastmod=modified([r for members in topic_groups.values() for r in members]),alternates={'en':'/topics/','zh-CN':'/zh/topics/','x-default':'/topics/'})
        for topic,members in topic_groups.items():
            first=topic_path(topic,language)
            title=topic_name(topic,language)+(' — computer-use research and resources' if language=='en' else '：Computer-Use 研究与资源')
            summary=(f'{len(members)} reviewed resources for {topic_name(topic)}, with original sources, full records and citations.' if language=='en' else f'{len(members)} 条已审阅的{topic_name(topic,language)}资源，包含原始来源、完整记录与论文引用。')
            for number in range(1,topic_page_count(topic_counts(members))+1):
                path=topic_path(topic,language,number)
                body,schema=topic_body(topic,members,lambda r:localized_path(r,language=='zh'),language=language,site_url=SITE,number=number)
                numbered=(f'{title}, page {number}' if language=='en' else f'{title}（第 {number} 页）') if number>1 else title
                alternatives={'en':topic_path(topic,'en',number),'zh-CN':topic_path(topic,'zh',number),'x-default':topic_path(topic,'en',number)}
                trail=[("AwesomeCUA","/zh/" if language=='zh' else "/"),("主题" if language=='zh' else "Topics",topic_path(language=language)),(topic_name(topic,language),first)]+([(f'Page {number}' if language=='en' else f'第 {number} 页',path)] if number>1 else [])
                emit(path,page(numbered,summary,path,body,schema,lang='zh-CN' if language=='zh' else 'en',alternatives=alternatives,crumbs=trail),lastmod=modified(members),alternates=alternatives)
            (destination/first.lstrip('/')/'index.md').write_text(clean_text(topic_markdown(topic,members,lambda r:localized_path(r,language=='zh'),language=language,site_url=SITE)),encoding='utf-8')
    library_ranges=[]
    ordered_papers=reviewed_papers(rows)
    for number in range(1,library_count+1):
        visible=ordered_papers[(number-1)*PAGE_SIZE:number*PAGE_SIZE]
        library_ranges.append((number,library_path(number),record_date_text(visible[0]) or 'date not recorded',record_date_text(visible[-1]) or 'date not recorded'))
    paper_topics=Counter(t for r in ordered_papers if r['kind']=='paper' for t in r['topics'])
    (destination/'categories/paper/index.md').write_text(clean_text(paper_hub_markdown(sum(r['kind']=='paper' for r in ordered_papers),sum(r['kind']=='survey' for r in ordered_papers),library_ranges,
        [(topic_name(t),n,topic_path(t)) for t,n in paper_topics.most_common()],site=SITE,snapshot=snapshot)),encoding='utf-8')
    topic_rows=[(topic,topic_name(topic),len(members),topic_path(topic)) for topic,members in topic_groups.items()]
    kind_rows=[(label,counts['curated']['by_kind'].get(kind,0),f'/categories/{kind}/index.md') for kind,label in ((k,KINDS[k]) for k in FULL_ORDER)]
    (destination/'catalog/index.md').write_text(clean_text(catalog_markdown(kind_rows,[(name,n,path) for _,name,n,path in topic_rows],site=SITE,counts=counts)),encoding='utf-8')
    zh_kind_rows=[(home_page.KINDS[kind][2],count,('/zh/papers/index.md' if kind=='paper' else f'/zh/categories/{kind}/index.md')) for (label,count,path),kind in zip(kind_rows,FULL_ORDER)]
    (destination/'zh/catalog/index.md').write_text(clean_text(catalog_markdown(zh_kind_rows,[(topic_name(topic,'zh'),len(members),topic_path(topic,'zh')) for topic,members in topic_groups.items()],site=SITE,counts=counts,language='zh')),encoding='utf-8')
    linked_papers=[r for r in papers if any(e['type'] in {'documented_by','introduced_by'} for e in incoming.get(r['id'],[]))]
    body='<div class="eyebrow">FOLLOW THE RESEARCH TO THE ASSETS</div><h1>Computer-use papers, code, and datasets</h1><p class="answer-lead">Find the implementations, benchmarks, and datasets connected to reviewed research papers. Every relationship below has a primary-source evidence link.</p><p>Connections describe publication documentation or introduction.</p><div class="reading-list">'
    for paper in linked_papers:
        body+=f'<article><h2><a href="{resource_path(paper)}">{esc(paper["name"])}</a></h2><p>{esc(description(paper))}</p><ul>'
        for rel in incoming[paper['id']]:
            source=lookup[rel['source_id']]
            body+=f'<li><a href="{resource_path(source)}">{esc(source["name"])}</a> — {esc(KINDS[source["kind"]])} · <a href="{safe_href(rel["evidence_url"])}">source evidence</a></li>'
        body+='</ul></article>'
    body+='</div><p><a href="/downloads/relationships.json">Download reviewed relationships as JSON</a> · <a href="/about/">Editorial policy</a></p>'
    emit('/connections/',page('Computer-use papers, code, and datasets','Trace computer-use agent papers to documented implementations, GUI benchmarks, and training datasets using reviewed primary-source relationships.','/connections/',body),lastmod=modified(linked_papers+[lookup[rel['source_id']] for paper in linked_papers for rel in incoming[paper['id']]]))
    edges=[{'source_id':r['id'],'source_name':r['name'],'source_kind':r['kind'],**rel} for r in rows for rel in r['relations']]
    (destination/'downloads/relationships.json').write_text(json.dumps({'relation_count':len(edges),'semantics':'Reviewed semantic links.','relations':edges},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sources=''.join(f'<tr><td><a href="{safe_href(s["url"])}">{esc(s["name"])}</a></td><td>{s["discovered"]}</td><td>{s["indexed"]}</td><td>{s["curated"]}</td><td>{s["excluded"]}</td><td>{s.get("set_aside",0)}</td><td>{s.get("out_of_scope",0)}</td><td>{s["unindexed"]}</td></tr>' for s in coverage['sources'])
    body=f'<h1>Coverage and verification ledger</h1><p class="answer-lead">{len(reviewed):,} curated resources and {awaiting:,} records with verified bibliographic metadata awaiting review.</p><p>Evidence snapshot: {esc(snapshot)}. Resource types can refer to different parts of the same project.</p><h2>Discovery-source coverage</h2><div class="table-scroll"><table class="coverage-table"><thead><tr><th>Source</th><th>Found</th><th>Indexed</th><th>Curated</th><th>Excluded</th><th>Set aside</th><th>Out of scope</th><th>Unresolved</th></tr></thead><tbody>{sources}</tbody></table></div><h2>Explicit scope exclusions</h2><p>{coverage["excluded_records"]} records are excluded after individual scope review. The original {coverage["arxiv_archive_records"]:,}-record arXiv metadata archive is retained. <a href="/downloads/exclusions.json">Inspect decisions and source evidence</a> · <a href="/downloads/arxiv-archive.jsonl">Download the raw archive</a>.</p><p>A changed or unconfirmed exclusion returns to review.</p><h2>What is still in progress?</h2><p>Most bibliography entries still require relevance review. Asset sizes, model licenses, availability, and experiment protocols need continuing curation.</p><p>{coverage["unindexed_candidates"]} discovered identifiers remain unresolved. {coverage.get("out_of_scope_candidates",0)} candidates have an out-of-scope review.</p><p><a href="/downloads/coverage.json">Download the complete coverage ledger</a> · <a href="/about/">Editorial policy</a></p>'
    emit('/coverage/',page('Coverage and verification ledger','Inspect AwesomeCUA source populations, editorial review states, bibliographic verification, unresolved identifiers, and explicit coverage gaps.','/coverage/',body),lastmod=max(snapshot,modified(rows) or snapshot))
    agent_alternatives={'en':'/agents/','zh-CN':'/zh/agents/','x-default':'/agents/'}
    for language,path,title,desc in [
        ('en','/agents/','Use AwesomeCUA with agents and RAG','Clone the complete computer-use catalog, search locally, and ingest citation-preserving retrieval documents with review states and source evidence.'),
        ('zh','/zh/agents/','AwesomeCUA：Agents 与 RAG 使用指南','一行克隆完整目录，本地检索或接入 RAG，保留资源引用、审阅状态、论文版本和来源指纹。')]:
        emit(path,page(title,desc,path,agent_guide_body(language),{'@type':'Article','headline':title,'description':desc,'author':{'@id':SITE+'/#organization'}},lang='zh-CN' if language=='zh' else 'en',alternatives=agent_alternatives),alternates=agent_alternatives)
    scan_config=json.loads((root/'data/scan-config.json').read_text(encoding='utf-8'))
    schedule=scan_schedule(scan_config)
    publication_schedule='at '+' and '.join(f':{minute:02d}' for minute in scan_config['publish_check_minutes'])+' past each hour '+scan_config['timezone']+'; a check rebuilds only when the source catalog has a new commit'
    body=f'<div class="eyebrow">DISCOVERY ACTIVITY</div><h1>Scan activity</h1><p class="answer-lead">Public sources are scheduled for scanning every eight hours. New paper identities are checked against arXiv; editorial annotations and approvals remain separate.</p><dl class="page-facts"><div><dt>Configured scan schedule</dt><dd>{esc(schedule[0].upper()+schedule[1:])}</dd></div><div><dt>Website publication checks</dt><dd>{esc(publication_schedule)}</dd></div></dl><p>GitHub scheduling can be delayed. The completion times below record what actually ran, rather than assuming that a scheduled job executed. A scan that finds nothing new publishes no receipt; a new receipt appears at least every {scan_config["scan_commit_heartbeat_hours"]} hours.</p>'
    body+=f'<h2>Current published catalog</h2><dl class="page-facts"><div><dt>Reviewed papers and surveys</dt><dd>{len(papers):,}</dd></div><div><dt>Other reviewed resources</dt><dd>{len(reviewed)-len(papers):,}</dd></div><div><dt>Records awaiting review</dt><dd>{awaiting:,}</dd></div><div><dt>Discovered candidates</dt><dd>{candidates:,}</dd></div></dl><p>These counts include editorial work completed after the scan below. <a href="/papers/">Browse reviewed research</a> or <a href="/coverage/">inspect full coverage</a>.</p>'
    if scan:
        body+=f'<h2>Latest completed scan</h2><dl class="page-facts"><div><dt>Status</dt><dd>{esc(scan["status"])}</dd></div><div><dt>Started</dt><dd>{esc(scan["started_at"])}</dd></div><div><dt>Finished</dt><dd>{esc(scan["finished_at"])}</dd></div><div><dt>Discovery documents fetched</dt><dd>{scan["source_fetches"]["successful"]} / {scan["source_fetches"]["total"]}</dd></div><div><dt>New paper metadata</dt><dd>{len(scan["new_papers"])}</dd></div><div><dt>New candidate identifiers</dt><dd>{scan["new_candidate_count"]}</dd></div><div><dt>Reviewed papers at scan completion</dt><dd>{scan["after"]["curated_papers"]}</dd></div><div><dt>Pending metadata changes</dt><dd>{scan["pending_metadata_changes"]}</dd></div></dl>'
        if scan.get('run_url'):body+=f'<p><a href="{safe_href(scan["run_url"])}">Inspect the workflow run and logs</a></p>'
        if scan['warnings']:body+='<h3>Recorded gaps</h3><ul>'+''.join('<li>'+esc(w)+'</li>' for w in scan['warnings'])+'</ul>'
        if scan['new_papers']:
            body+='<h2>New to the bibliography</h2><p>These are newly discovered bibliographic records. Relevance and findings still require editorial review.</p><ul>'+''.join(f'<li><a href="{resource_path(r)}">{esc(r["name"])}</a> · metadata verified</li>' for r in scan['new_papers'][:30])+'</ul>'
        (destination/'downloads/scan-status.json').write_text(json.dumps(scan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        body+='<p><a href="/downloads/scan-status.json">Download the full scan receipt</a></p>'
    else:
        body+='<h2>First scan pending</h2><p>The schedule is configured in the source repository. No completed automated-scan receipt has been recorded yet.</p>'
    body+='<h2>What the scans do</h2><p>Scans find new sources and verify bibliographic fields. Editors decide relevance, record dataset permissions, and write summaries. Reviewed snapshots stay as they are, and observed metadata changes go to the review queue.</p><p><a href="https://github.com/reacher-z/Awesome-CUA/actions/workflows/scan.yml">Discovery workflow</a> · <a href="'+REPO+'/actions/workflows/publish.yml">Publication workflow</a> · <a href="/coverage/">Coverage ledger</a></p>'
    body+='<p><a href="'+REPO+'/blob/main/.indexnow/submissions.json">Search notification receipts</a> record which changed pages were submitted after publication and the response received. Submission is separate from search indexing.</p>'
    discovery=coverage.get('paper_discovery',{})
    if discovery:
        body+=f'<h2>Latest paper-discovery pass</h2><p>{esc(discovery.get("finished_at") or "In progress")} · {discovery.get("successful_query_count",0)} / {discovery.get("configured_query_count",0)} query windows succeeded · {discovery.get("unique_identifiers",0):,} distinct identifiers · {discovery.get("new_candidate_count",0):,} new candidates.</p><p>Newly found identifiers go through primary metadata verification and relevance review.</p><div class="table-scroll"><table><thead><tr><th>Area / query</th><th>Unique hits</th><th>New candidates</th><th>Window limit</th><th>State</th></tr></thead><tbody>'
        for item in discovery.get('queries',[]):
            ok=item.get('state')=='success'
            body+=f'<tr><td>{esc(item["area"])}<br><small>{esc(item["query"])}</small></td><td>{item.get("unique_count",0) if ok else "—"}</td><td>{item.get("new_candidate_count",0) if ok else "—"}</td><td>{item["limit"]}</td><td>{esc(item["state"])}</td></tr>'
        body+='</tbody></table></div><p>Per-query new counts depend on query order and count first discovery in this pass. <a href="/downloads/paper-discovery-queries.json">Query registry</a> · <a href="/downloads/paper-discovery-status.json">Results and source receipts</a></p>'
    conference_file=root/'data/conference-discovery.json'
    if conference_file.exists():
        conference=json.loads(conference_file.read_text(encoding='utf-8'))
        body+=f'<h2>Conference proceedings sweep</h2><p>{conference["title_candidate_count"]} keyword-selected titles were inspected across {conference["source_count"]} official proceedings snapshots. Title candidates and possible renamed papers await identity and scope review.</p><p><a href="/downloads/conference-discovery.json">Inspect the selected titles, review boundaries, and primary receipts</a>.</p>'
    emit('/updates/',page('Scan activity','Inspect the actual completion, discoveries, and source gaps from the AwesomeCUA public-source scans that run every eight hours.','/updates/',body),lastmod=max(filter(None,[snapshot,modified(rows),scan and scan.get('finished_at')])))
    badge_papers=sum(r['kind'] in {'paper','survey'} for r in reviewed)
    (destination/'badges').mkdir(exist_ok=True)
    badge=f'<svg xmlns="http://www.w3.org/2000/svg" width="590" height="30" role="img" aria-label="{len(reviewed)} curated resources, {badge_papers} reviewed papers, {awaiting} records awaiting review"><rect width="590" height="30" rx="5" fill="#4856df"/><g fill="#fff" font-family="Arial,sans-serif" font-size="12" text-anchor="middle"><text x="95" y="20">{len(reviewed):,} curated resources</text><text x="290" y="20">{badge_papers:,} reviewed papers</text><text x="480" y="20">{awaiting:,} awaiting review</text></g></svg>'
    (destination/'badges/catalog.svg').write_text(badge,encoding='utf-8')
    featured_badges=[('featured-by-awesomecua-laurel.svg','Purple laurel, CUA shield, and serif lettering',480,106),('featured-by-awesomecua.svg','Light badge',200,40),('featured-by-awesomecua-dark.svg','Dark badge',200,40),('awesomecua-featured-seal.svg','Featured seal',140,156)]
    if all((destination/'badges'/name).is_file() for name,_,_,_ in featured_badges):
        body='<h1>Featured by AwesomeCUA</h1><p class="answer-lead">SVG badges for project pages, GitHub READMEs, and release notes. Link a badge to your resource’s AwesomeCUA entry so readers can inspect its sources.</p><div class="badge-gallery">'
        for name,label,width,height in featured_badges:
            body+=f'<figure><div class="badge-preview{" badge-preview-dark" if "dark" in name else ""}"><img src="/badges/{name}" width="{width}" height="{height}" alt="{esc(label)}: Featured by AwesomeCUA"></div><figcaption><strong>{esc(label)}</strong> · <a href="/badges/{name}" download>Download SVG</a></figcaption></figure>'
        body+='</div><h2>Add a badge to your README</h2><p>Replace <code>YOUR_RESOURCE_URL</code> with the link to your listed resource. The image is hosted here; no third-party image service is required.</p><pre><code>[![Featured by AwesomeCUA]('+SITE+'/badges/featured-by-awesomecua-laurel.svg)](YOUR_RESOURCE_URL)</code></pre><p>“Featured” indicates a catalog listing. Each listing shows its review state and primary evidence. The original SVG artwork is available under the <a href="'+SOURCE_REPO+'/blob/main/LICENSE">MIT license</a>.</p><p><a href="/catalog/">Find your resource</a> · <a href="/about/">Editorial policy</a></p>'
        emit('/badges/',page('Featured resource badges','Download original AwesomeCUA SVG badges and link them to a source-backed resource entry.','/badges/',body))
    body='<h1>About AwesomeCUA and its editorial policy</h1><p class="answer-lead">AwesomeCUA is a source-backed catalog of resources for agents that operate computer interfaces. Its purpose is to make research and engineering assets easier to find, compare, and trace to their original publishers.</p><h2>Who maintains the catalog?</h2><p>The AwesomeCUA project publishes the catalog through its <a href="https://github.com/AwesomeCUA">GitHub organization</a>. Annotations and taxonomy are produced with AI-assisted editorial review.</p><h2>What is included?</h2><p>GUI and hybrid GUI/code agents, visual grounding, web and mobile navigation, training data, evaluation environments, execution infrastructure, safety research, and relevant products. Supporting tools may be marked adjacent.</p><h2>How are claims checked?</h2><p>Community lists and semantic searches discover candidates. Retained arXiv and publication sources support bibliographic facts. Official papers, repositories, documentation, and model/dataset cards support curated annotations. Every record retains source URLs, retrieval timestamps, and content hashes. A changed source returns to editorial review.</p><h2>What do review states mean?</h2><ul><li><strong>Curated:</strong> a primary source was inspected for identity, scope, and the concise annotation.</li><li><strong>Metadata verified:</strong> bibliographic fields were checked; relevance review is pending.</li><li><strong>Candidate:</strong> a discovered identifier awaiting resolution.</li></ul><h2>Licenses and corrections</h2><p>Code, data, weights, and document licenses are separate. Original catalog annotations and code use MIT; upstream resources keep their own terms. Report errors through <a href="'+SOURCE_REPO+'/issues/new?template=resource.yml">a source-backed correction</a>.</p><h2>Indexing policy</h2><p>Reviewed resource pages and useful collection pages are eligible for indexing. Metadata-only resource pages remain accessible, with <code>noindex,follow</code> until their relevance is reviewed. The full bibliography remains searchable and downloadable.</p><p><a href="/coverage/">Coverage ledger</a> · <a href="/data/">Data and provenance</a></p>'
    emit('/about/',page('About AwesomeCUA and editorial policy','Learn what AwesomeCUA includes, how primary-source review works, what verification means, and how to suggest corrections.','/about/',body))
    desc='A structured catalog of computer-use agent research papers, models, datasets, benchmarks, tools, products, and publishers, including original annotations, review states, source evidence, scoped license declarations, and resource relationships.'
    dataset={"@type":"Dataset","name":"AwesomeCUA computer-use agent resource catalog","description":desc,"url":SITE+'/data/',"creator":{"@id":SITE+'/#organization'},"license":SOURCE_REPO+'/blob/main/LICENSE',"dateModified":snapshot,"keywords":["computer-use agents","GUI agents","browser agents","datasets","benchmarks"],"distribution":[{"@type":"DataDownload","encodingFormat":"application/x-ndjson","contentUrl":SITE+'/downloads/catalog.jsonl'},{"@type":"DataDownload","encodingFormat":"application/json","contentUrl":SITE+'/data/records.json'},{"@type":"DataDownload","encodingFormat":"application/vnd.sqlite3","contentUrl":SITE+'/downloads/catalog.sqlite'}],"isAccessibleForFree":True}
    download_manifest=build_download_manifest(destination,rows,(root/'data/catalog.jsonl').read_bytes())
    data_alternatives={'en':'/data/','zh-CN':'/zh/data/','x-default':'/data/'}
    # One real record shows what a row of the catalog holds; the full record stays one link away.
    sample=next((r for r in rows if r['id']=='github:xlang-ai/osworld'),None) or next(r for r in rows if r['review_status']=='curated')
    data_preview={'path':resource_path(sample)+'record.json','fields':len(sample),'record':{name:sample[name] for name in ('id','name','kind','url','review_status','scope','summary','environments','topics','last_verified_at')}}
    for language,path,title,summary in [
        ('en','/data/','AwesomeCUA data downloads for people and agents',desc),
        ('zh','/zh/data/','AwesomeCUA 数据中心：完整目录、RAG 与论文引用','下载完整 Computer-Use 资源目录、RAG 检索文档、论文引用和来源文件，查看实际条数、文件大小与 SHA-256 指纹。')]:
        body=data_hub_body(download_manifest,language=language,site_url=SITE,updated=str(snapshot)[:10],preview=data_preview)
        twin=destination/path.lstrip('/')/'index.md'
        twin.parent.mkdir(parents=True,exist_ok=True)
        twin.write_text(clean_text(data_hub_markdown(download_manifest,language=language,site_url=SITE,updated=str(snapshot)[:10])),encoding='utf-8')
        data_schema={**dataset,'url':SITE+path,'description':summary}
        emit(path,page(title,summary,path,body,data_schema,lang='zh-CN' if language=='zh' else 'en',alternatives=data_alternatives,landing=True),lastmod=max(snapshot,modified(rows) or snapshot),alternates=data_alternatives)
    guides=json.loads((root/'data/site-guides.json').read_text(encoding='utf-8'))
    for guide in guides:
        emit(guide_path(guide),page(guide['title'],guide['description'],guide_path(guide),guide['body'],{"@type":"Article","headline":guide['title'],"description":guide['description'],"author":{"@id":SITE+'/#organization'}},crumbs=[("AwesomeCUA","/"),("Guides","/guides/"),(guide['title'],guide_path(guide))]))
    body='<h1>Guides to computer-use agents</h1><p class="answer-lead">Practical reading guides with direct answers and primary research references. These guides help distinguish interface grounding, task execution, training data, and evaluation.</p><div class="reading-list">'+''.join(f'<article><h2><a href="{guide_path(g)}">{esc(g["title"])}</a></h2><p>{esc(g["description"])}</p></article>' for g in guides)+'</div>'
    emit('/guides/',page('Computer-use agent guides','Understand computer-use agents, choose GUI-agent benchmarks, and find training datasets with clearly scoped primary-source references.','/guides/',body))
    zh_note=f'当前有 {len(reviewed):,} 条经过 AI 辅助编辑审阅的资源；另有 {awaiting:,} 条书目记录待审阅、{candidates:,} 个已发现候选待核实。'
    zh_body=home_page.hero(view,last_scan,zh=True)+home_page.benchmark_band(view,zh=True)+home_page.tasks(view,zh=True)+home_page.latest(view,zh=True)+home_page.categories(view,zh=True)+home_page.papers(view,zh=True)+home_page.developers(zh=True)+home_page.directory_strip(zh=True,note=zh_note)+home_page.contribute(zh=True)
    emit('/zh/',page('AwesomeCUA 中文主页：Computer-Use Agent 资源目录','浏览可搜索、可追溯的 Computer-Use Agent 论文、模型、数据集、基准、框架与产品，查看来源证据并下载结构化目录。','/zh/',zh_body,lang='zh-CN',alternatives=True,landing=True),lastmod=modified(rows),alternates=True)
    # The explorer keeps a static, visible directory for visitors without JavaScript.
    static='<section class="shell static-directory" aria-labelledby="static-directory-title"><div class="eyebrow" data-i18n="directoryEyebrow">READ, EXPLORE, AND CITE</div><h2 id="static-directory-title" data-i18n="directoryHeading">Computer-use agent research and resources</h2><p data-i18n="directoryCopy">Browse source-backed pages directly, with or without JavaScript. Reviewed entries include concise annotations, provenance, and separate license declarations.</p><div class="directory-links"><a href="/catalog/" data-i18n="directoryTitle">Resource directory</a><a href="/papers/" data-paper-library data-i18n="directoryPapers">Research papers</a><a href="/topics/" data-topic-directory data-i18n="directoryTopics">Browse by topic</a><a href="/connections/" data-i18n="directoryConnections">Papers → code & data</a><a href="/updates/" data-i18n="directoryUpdates">Scan updates</a><a href="/categories/model/" data-i18n="directoryModels">Models</a><a href="/categories/dataset/" data-i18n="directoryDatasets">Datasets</a><a href="/categories/benchmark/" data-i18n="directoryBenchmarks">Benchmarks</a><a href="/compare/benchmarks/" data-i18n="compareBenchmarks">Compare benchmarks</a><a href="/compare/datasets/" data-i18n="compareDatasets">Compare datasets</a><a href="/categories/learning/" data-i18n="directoryLearning">Learning resources</a><a href="/categories/framework/" data-i18n="directoryFrameworks">Frameworks</a><a href="/categories/product/" data-i18n="directoryProducts">Products</a><a href="/guides/" data-i18n="navGuides">Guides</a><a href="/data/" data-i18n="directoryData">Download data</a><a href="/coverage/" data-i18n="navCoverage">Coverage</a><a href="/about/" data-i18n="editorialPolicy">Editorial policy</a><a href="/zh/" lang="zh-CN">中文指南</a></div><h3 data-i18n="startHeading">Where should I start?</h3><p><a href="/guides/what-are-computer-use-agents/" data-i18n="startConcepts">Understand computer-use agents</a><span data-i18n="listComma">, </span><a href="/guides/gui-agent-benchmarks/" data-i18n="startBenchmarks">choose a benchmark for the capability you need</a><span data-i18n="listOr">, or </span><a href="/guides/gui-agent-training-data/" data-i18n="startData">find training data with the right supervision and license</a><span data-i18n="sentenceEnd">.</span></p></section>'
    website={"@type":"WebSite","@id":SITE+"/#website","url":SITE+"/","name":"AwesomeCUA","description":"Source-backed computer-use and GUI-agent resource catalog","publisher":{"@id":SITE+"/#organization"}}
    home_body=home_page.hero(view,last_scan)+home_page.benchmark_band(view)+home_page.tasks(view)+home_page.latest(view)+home_page.categories(view)+home_page.papers(view)+home_page.developers()+home_page.directory_strip()+home_page.contribute()
    emit('/',page('AwesomeCUA — Computer-use research, data, and tools','Find research, models, benchmarks, and software for web, desktop, and mobile agents. Filter by task or platform, then inspect the primary sources.','/',home_body,alternatives=True,landing=True,extra_graph=[website]),lastmod=modified(rows),alternates=True)
    # Feeds announce curated records as they pass source review, newest review first.
    entries=[feed_entry(r,site=SITE,page_path=resource_path(r),reviewed_at=review_times[r['id']],modified=record_modified(r,review_times),summary=description(r),kind_label=KINDS[r['kind']]) for r in newest_reviewed(rows,review_times,FEED_SIZE)]
    write_feeds(destination,entries,site=SITE,updated=max((entry['updated'] for entry in entries),default=snapshot))
    # The explorer holds the complete interactive catalog, including records awaiting review; it needs JavaScript.
    explorer_source=destination/'explore.html'
    explorer=explorer_source.read_text(encoding='utf-8')
    explorer_source.unlink()
    explorer=re.sub(r'<!-- SURVEY:START -->(.*?)<!-- SURVEY:END -->',lambda m:m[1] if survey_page else '',explorer,flags=re.S)
    extra=f'<link rel="canonical" href="{SITE}/explore/"><meta name="robots" content="noindex,follow"><meta property="og:url" content="{SITE}/explore/"><link rel="alternate" type="application/atom+xml" href="/feed.xml" title="{FEED_TITLE}"><link rel="alternate" type="application/feed+json" href="/feed.json" title="{FEED_TITLE}">'
    explorer=explorer.replace('</head>',extra+f'<script type="application/ld+json">{jsonld({"@context":"https://schema.org","@graph":[organization(),website]})}</script></head>')
    for identity,value in [('stat-curated',len(reviewed)),('stat-pending',awaiting),('stat-candidates',candidates),('stat-sources',len(coverage['sources']))]:
        explorer=re.sub(f'(id="{identity}">).*?(</span>)',lambda m:m.group(1)+format(value,',')+m.group(2),explorer)
    explorer=explorer.replace('id="snapshot-date">—','id="snapshot-date">'+snapshot[:10])
    explorer=explorer.replace('</main>',static+'</main>')
    explorer_trail=[('AwesomeCUA','/'),('Explore every record','/explore/')]
    explorer=explorer.replace('<main class="explore">','<main class="explore"><nav class="breadcrumbs shell" aria-label="Breadcrumb"><ol><li><a href="/">AwesomeCUA</a></li><li><a href="/explore/" aria-current="page">Explore every record</a></li></ol></nav>')
    explorer=explorer.replace('</head>','<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@graph':[{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i+1,'name':name,'item':SITE+target} for i,(name,target) in enumerate(explorer_trail)]}]},ensure_ascii=False)+'</script></head>')
    explorer=explorer.replace('<!-- SHELL:HEAD -->',site_shell.head_assets())
    explorer=explorer.replace('<!-- SHELL:STYLES -->',f'<link rel="stylesheet" href="{site_shell.asset("/pages.css")}"><link rel="stylesheet" href="{site_shell.asset("/styles.css")}">')
    explorer=explorer.replace('<!-- SHELL:TOP -->',site_shell.top(path='/explore/',lang_href='/explore/?lang=zh'))
    explorer=explorer.replace('<!-- SHELL:BOTTOM -->',site_shell.bottom(lang_href='/explore/?lang=zh'))
    emit('/explore/',explorer,index=False,utility=True)
    # Static API: compact, versioned JSON and CSV that link each record's complete record.json instead of copying it.
    api_index=write_api(destination,rows=rows,coverage=coverage,root=root,site=SITE,resource_path=resource_path,review_times=review_times,counts=counts,
                        catalog_sha256=hashlib.sha256((root/'data/catalog.jsonl').read_bytes()).hexdigest(),kinds=KINDS,kind_labels=KIND_LABELS,
                        topic_groups=topic_groups,topic_name=topic_name,topic_path=topic_path)
    emit('/api/',page(API_TITLE,API_SUMMARY,'/api/',api_docs_body(api_index,site=SITE,esc=esc),{'@type':'TechArticle','headline':API_TITLE,'description':API_SUMMARY,'author':{'@id':SITE+'/#organization'}}),lastmod=snapshot)
    (destination/'api/index.md').write_text(clean_text(api_docs_markdown(api_index,site=SITE)),encoding='utf-8')
    newest=newest_reviewed(rows,review_times,20)
    (destination/'index.md').write_text(clean_text(home_markdown([(r['name'],SITE+resource_path(r),KINDS[r['kind']],review_times[r['id']],description(r)) for r in newest],kind_rows,site=SITE,counts=counts,snapshot=snapshot)),encoding='utf-8')
    (destination/'zh/index.md').write_text(clean_text(home_markdown([(r['name'],SITE+localized_path(r,True),home_page.KINDS[r['kind']][2],review_times[r['id']],zh_summary(r)) for r in newest],zh_kind_rows,site=SITE,counts=counts,snapshot=snapshot,language='zh')),encoding='utf-8')
    survey_links=[]
    survey_line=''
    if survey_page:
        survey_links=[('Computer-use agent survey',f'{SITE}/survey/','working manuscript with a separately frozen research inventory; not an additional catalog record'),
                      ('Survey bibliography',f'{SITE}/survey/references.bib',''),('Survey references JSON',f'{SITE}/survey/references.json',''),
                      ('Source reading register',f'{SITE}/survey/evidence/reading-index.json',''),('Survey file manifest',f'{SITE}/survey/build-manifest.json','')]
        survey_line=f'Related reading: [English research survey]({SITE}/survey/). This working manuscript uses its own frozen inventory; its text is separate from the catalog annotations below.'
    notes={'paper':f'listed {PAGE_SIZE} per page in the research library below','survey':''}
    llms_kinds=[(label,count,path,notes.get(kind,'')) for (label,count,path),kind in zip(kind_rows,FULL_ORDER)]
    guide_rows=[(g['title'],guide_path(g),g['description']) for g in guides]+[('Editorial policy','/about/','review states, inclusion boundary and corrections'),('Coverage ledger','/coverage/','source populations and known gaps'),('Catalog updates','/updates/','scan schedule and the latest completed scan')]
    (destination/'llms.txt').write_text(clean_text(llms_txt(site=SITE,counts=counts,kinds=llms_kinds,zh_kinds=zh_kind_rows,library=library_ranges,topics=[(name,n,path) for _,name,n,path in topic_rows],
        api_endpoints=[(item['name'],item['json'],item['csv'],item['description']) for item in api_index['endpoints']],guides=guide_rows,survey_links=survey_links,releases_url=RELEASES_URL)),encoding='utf-8')
    groups=[]
    for kind in FULL_ORDER:
        members=sorted((r for r in reviewed if r['kind']==kind),key=lambda r:(r['name'].casefold(),r['id']))
        if members:groups.append((KINDS[kind],[compact_entry(r,site=SITE,page_path=resource_path(r),summary=description(r)) for r in members]))
    kind_files=[(KINDS[kind],f'/categories/{kind}/index.md') for kind in FULL_ORDER if kind!='paper']+[('Research library',library_path(1)+'index.md')]
    (destination/'llms-full.txt').write_text(clean_text(llms_full(groups,site=SITE,snapshot=snapshot,counts=counts,survey_line=survey_line,kind_files=kind_files)),encoding='utf-8')
    (destination/'robots.txt').write_text(robots_txt(SITE),encoding='utf-8')
    if survey_page:
        survey_date=json.loads((destination/'survey/build-manifest.json').read_text(encoding='utf-8')).get('working_manuscript_date')
        sitemap_facts['/survey/']={'lastmod':survey_date,'alternates':{}}
    declare_markdown_twins(destination,manifest)
    kind_by_path={**{resource_path(r):r['kind'] for r in rows},**{zh_resource_path(r):r['kind'] for r in rows if eligible(r)}}
    write_sitemaps(destination,SITE,[{'path':item['path'],'section':sitemap_section(item['path'],kind_by_path),**sitemap_facts[item['path']]} for item in manifest if item['indexable']])
    (destination/'data/search-manifest.json').write_text(json.dumps({'site_url':SITE,'indexable_pages':sum(x['indexable'] for x in manifest),'metadata_only_pages':sum(not x['indexable'] and not x.get('scope_excluded') and not x.get('utility') for x in manifest),'excluded_pages':sum(bool(x.get('scope_excluded')) for x in manifest),'pages':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    config=json.loads((root/'data/site-discovery.json').read_text(encoding='utf-8'))
    key=config['indexnow_key'];(destination/(key+'.txt')).write_text(key,encoding='utf-8')
    return manifest
