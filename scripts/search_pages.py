"""Server-rendered, evidence-backed discovery pages for the static website."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from specifications import PROFILE_KEYS, comparison_body, profile_export, resource_profile_html, count_text, safe_href
from agent_pages import agent_guide_body, RELEASES_URL
from export_citations import citation_bibtex, citation_csl
from paper_library import library_pages, library_path, library_years, paper_library
from publication_metadata import publication, format_date_parts, record_date_text, record_year
from topic_pages import write_topic_exports, topic_index_body, topic_body, topic_counts, topic_markdown, topic_name, topic_page_count, topic_path
from data_hub import build_download_manifest, data_hub_body

SITE = "https://awesomecua.github.io"
REPO = "https://github.com/AwesomeCUA/awesomecua.github.io"
SOURCE_REPO = "https://github.com/reacher-z/Awesome-CUA"
KINDS = {"paper":"Research papers", "survey":"Surveys", "model":"Models and checkpoints", "dataset":"Datasets", "benchmark":"Benchmarks", "agent":"Agents", "framework":"Frameworks", "infrastructure":"Infrastructure", "tool":"Tools", "product":"Products", "company":"Publishers"}


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def clip(text, limit=300):
    # Search snippets must end on a whole word; the ellipsis counts toward the limit.
    if len(text)<=limit:return text
    head=re.match(r'(.*\S)\s',text[:limit],re.S)
    return re.sub(r'[\s,;:.]+$','',head[1] if head else text[:limit-1])+'…'


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


def eligible(record):
    return record["review_status"] == "curated" and record["scope"] in {"core", "adjacent"}


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
    return titles


def description(record):
    provider='arXiv' if record['id'].startswith('arxiv:') else 'retained publication sources'
    return record.get("summary") or f"Bibliographic record for {record['name']}. Title, authors and dates checked against {provider}; relevance and findings await editorial review."


def jsonld(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def organization():
    return {"@type":"Organization", "@id":SITE+"/#organization", "name":"AwesomeCUA", "url":SITE+"/", "sameAs":["https://github.com/AwesomeCUA", SOURCE_REPO, REPO]}


def page(title, summary, path, body, main=None, index=True, lang="en", alternatives=False, crumbs=None, canonical=True):
    url=SITE+path
    # One list renders both the visible trail and BreadcrumbList, so they cannot disagree.
    crumbs=crumbs or [("AwesomeCUA","/zh/" if lang=="zh-CN" and path!="/zh/" else "/"),(title,path)]
    graph=[organization(), {"@type":"WebPage", "@id":url+"#page", "url":url, "name":title, "description":summary, "inLanguage":lang, "isPartOf":{"@id":SITE+"/#website"}, "publisher":{"@id":SITE+"/#organization"}}]
    if main:
        main={"@id":url+"#entity", **main}
        graph.append(main);graph[1]["mainEntity"]={"@id":main["@id"]}
    if path!="/":
        graph.append({"@type":"BreadcrumbList", "itemListElement":[{"@type":"ListItem","position":i+1,"name":name,"item":SITE+target} for i,(name,target) in enumerate(crumbs)]})
    trail=''.join(f'<li><a href="{esc(target)}">{esc(name)}</a></li>' for name,target in crumbs[:-1])+f'<li><a href="{esc(crumbs[-1][1])}" aria-current="page">{esc(crumbs[-1][0])}</a></li>'
    alternate_paths = alternatives if isinstance(alternatives, dict) else {'en': '/', 'zh-CN': '/zh/', 'x-default': '/'} if alternatives else {}
    alternate=''.join(f'<link rel="alternate" hreflang="{esc(locale)}" href="{SITE}{esc(target)}">' for locale,target in alternate_paths.items())
    robots="index,follow,max-image-preview:large" if index else "noindex,follow"
    # The not-found page is served at every missing address, so it claims no URL of its own.
    identity=f'<link rel="canonical" href="{url}">' if canonical else ''
    og_url=f'<meta property="og:url" content="{url}">' if canonical else ''
    full_title=title if 'AwesomeCUA' in title else title+' | AwesomeCUA'
    document=f'''<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(full_title)}</title><meta name="description" content="{esc(clip(summary))}"><meta name="robots" content="{robots}">{identity}{alternate}<meta property="og:title" content="{esc(full_title)}"><meta property="og:description" content="{esc(clip(summary))}">{og_url}<meta property="og:type" content="website"><meta property="og:site_name" content="AwesomeCUA"><meta property="og:locale" content="{"zh_CN" if lang=="zh-CN" else "en_US"}"><meta property="og:image" content="{SITE}/social.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="AwesomeCUA: The next interface is an agent. Research, models, data, and tools in one source-backed index."><meta name="twitter:card" content="summary_large_image"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/pages.css"><link rel="alternate" type="application/atom+xml" href="/feed.xml" title="AwesomeCUA research updates"><script type="application/ld+json">{jsonld({"@context":"https://schema.org","@graph":graph})}</script></head><body><a class="skip-link" href="#content">Skip to content</a><header class="site-header"><div class="header-inner"><a class="brand" href="/"><img src="/favicon.svg" width="32" height="32" alt=""><span>Awesome<span class="brand-cua">CUA</span></span></a><nav aria-label="Main navigation"><a href="/catalog/">Catalog</a><a href="/papers/">Papers</a><a href="/topics/">Topics</a><a href="/guides/">Guides</a><a href="/data/">Data</a></nav><a class="github-link" href="{SOURCE_REPO}">GitHub ↗</a></div></header><main id="content" class="reading-shell"><nav class="breadcrumbs" aria-label="Breadcrumb"><ol>{trail}</ol></nav>{body}</main><footer class="shell"><a class="brand" href="/">AwesomeCUA</a><a href="/about/">Editorial policy</a><a href="/coverage/">Coverage</a><a href="/data/">Download data</a><a href="/llms.txt">Machine-readable guide</a><a href="{SOURCE_REPO}">Source repository ↗</a></footer></body></html>'''

    if lang.startswith('zh'):
        chrome={'Skip to content':'跳到正文','Catalog':'目录','Papers':'论文','Topics':'主题','Guides':'指南','Data':'数据','Editorial policy':'收录方法','Coverage':'覆盖台账','Download data':'下载数据','Machine-readable guide':'机器读取指南','GitHub organization ↗':'GitHub 组织 ↗','Source repository ↗':'源代码仓库 ↗'}
        for english,chinese in chrome.items():
            document=document.replace('>'+english+'</a>','>'+chinese+'</a>')
        document=document.replace('href="/papers/">论文</a>', 'href="/zh/papers/">论文</a>')
        document=document.replace('href="/topics/">主题</a>', 'href="/zh/topics/">主题</a>')
        document=document.replace('href="/data/">数据</a>', 'href="/zh/data/">数据</a>')
        document=document.replace('href="/data/">下载数据</a>', 'href="/zh/data/">下载数据</a>')
    return document


def resource_schema(record):
    entity={"@type":"ScholarlyArticle" if record["kind"] in {"paper","survey"} else "CreativeWork", "name":record["name"], "description":description(record), "url":SITE+resource_path(record), "sameAs":record["url"], "identifier":record["id"]}
    if record["authors"]:entity["author"]=[{"@type":"Person","name":name} for name in record["authors"]]
    if record["published_at"]:entity["datePublished"]=record["published_at"]
    if record["updated_at"]:entity["dateModified"]=record["updated_at"]
    if record["topics"]:entity["keywords"]=record["topics"]
    if record["kind"]=="dataset" and len(description(record))>=50:entity["@type"]="Dataset"
    return entity


def listing(rows):
    return '<div class="reading-list">'+"".join(f'<article><div class="list-overline">{esc(KINDS[r["kind"]])} · {esc(r["review_status"])}</div><h2><a href="{resource_path(r)}">{esc(r["name"])}</a></h2><p>{esc(description(r))}</p><small>{esc(record_date_text(r) or "Release date not recorded")} · {esc(", ".join(r["environments"]))}</small></article>' for r in rows)+'</div>'


def publication_body(record):
    pub=publication(record)
    if not pub:return ''
    facts=[('Title',pub['title']),('Authors',', '.join(pub['authors'])),
           ('Publication date (recorded precision)',format_date_parts(pub['date_parts'])),
           ('Venue',pub.get('venue')),('Publisher',pub.get('publisher')),('Series',pub.get('series')),
           ('Volume',pub.get('volume')),('Issue',pub.get('issue')),('Pages',pub.get('pages')),('DOI',pub.get('doi'))]
    body='<section class="publication-record"><h2>Publication record</h2><dl class="page-facts">'+''.join('<div><dt>'+esc(key)+'</dt><dd>'+esc(value)+'</dd></div>' for key,value in facts if value)+'</dl>'
    body+='<p><a href="'+safe_href(pub['url'])+'">Publication source ↗</a>'
    if pub.get('pdf_url'):body+=' · <a href="'+safe_href(pub['pdf_url'])+'">Publisher or author PDF ↗</a>'
    body+='</p><p><a href="'+resource_path(record)+'publication-citation.bib" download>Publication BibTeX</a> · <a href="'+resource_path(record)+'publication-citation.csl.json" download>Publication CSL JSON</a></p>'
    if record['id'].startswith('arxiv:'):
        body+='<p>This publication is a separately recorded edition of the same work. Its citation uses its own title, authors and date; the retained arXiv citation above is unchanged.</p>'
    for key,label in [('date_basis','Date source'),('event_dates','Event dates (not substituted for publication)'),('notes','Source notes')]:
        if pub.get(key):body+='<p>'+label+': '+esc(pub[key])+'</p>'
    body+='</section>'
    return body


def incoming_relations(rows):
    incoming=defaultdict(list)
    for source in rows:
        for relation in source['relations']:
            incoming[relation['target_id']].append({'source_id':source['id'],**relation})
    return incoming


def resource_body(record, lookup, incoming=None):
    r=record
    status="AI-assisted editorial review against a primary source" if eligible(r) else "Bibliographic metadata verified; topic relevance and research findings have not been reviewed"
    body=f'<div class="eyebrow">{esc(KINDS[r["kind"]])}</div><h1>{esc(r["name"])}</h1><p class="answer-lead">{esc(description(r))}</p><p class="review-notice">{esc(status)}. This is a catalog annotation, not an independent reproduction or endorsement.</p><div class="page-actions"><a class="button primary" href="{safe_href(r["url"])}">Original source ↗</a><a class="button secondary" href="{resource_path(r)}index.md">Read as Markdown</a><a class="button secondary" href="{resource_path(r)}record.json">Record JSON</a></div>'
    from paper_library import PLATFORMS  # local import keeps this change clear of the module's import block
    platforms=", ".join(PLATFORMS[e][0] if e in PLATFORMS else "Not specified" if e=="unspecified" else e for e in r["environments"])
    topics=", ".join(f'<a href="{topic_path(t)}">{esc(topic_name(t))}</a>' for t in r["topics"]) or "Not assigned"
    # Values are HTML: labels, topic links and times are built from escaped parts.
    facts=[("Category",f'<a href="/categories/{r["kind"]}/">{esc(KINDS[r["kind"]])}</a>'),("Platforms",esc(platforms)),("Topics",topics),("Record publication date",esc(record_date_text(r) or "Not recorded")),("Evidence retrieved",utc_time(r["last_verified_at"])),("Resource ID",f'<code>{esc(r["id"])}</code>')]
    body+='<h2>What is this resource?</h2><dl class="page-facts">'+''.join(f'<div><dt>{esc(k)}</dt><dd>{v}</dd></div>' for k,v in facts)+'</dl>'
    body+=connected_assets_html(r,lookup,incoming)
    snapshot=r['details'].get('arxiv_snapshot')
    if snapshot:
        version=(f'<a href="{safe_href(snapshot["versioned_url"])}">arXiv v{esc(snapshot["version"])}</a>' if snapshot.get('versioned_url') else 'Version not recorded')
        body+='<h2>Recorded paper version</h2><p>'+version+'</p>'
        if snapshot.get('updated_at'):body+='<p>Version updated: '+utc_time(snapshot['updated_at'])+'.</p>'
        body+='<p>This identifies the retained arXiv metadata snapshot; newly observed changes require separate review.</p>'
        if snapshot.get('abstract_sha256'):body+='<details><summary>Abstract fingerprint</summary><code>'+esc(snapshot['abstract_sha256'])+'</code></details>'
    if r["authors"]:body+='<h2>Authors</h2><p>'+esc(', '.join(r["authors"]))+'</p>'
    preferred='arxiv:'+r['identifiers']['preferred_arxiv'] if r['identifiers'].get('preferred_arxiv') else None
    if preferred and preferred in lookup:
        body+='<h2>Preferred paper record</h2><p>The retained source identifies this as an alternate bibliographic record. Follow <a href="'+resource_path(lookup[preferred])+'">'+esc(lookup[preferred]['name'])+'</a> for the preferred arXiv identity. These records should not be counted as independent works.</p>'
    if r['kind'] in {'paper','survey'}:
        body+='<h2>Cite this paper</h2><p><a href="'+resource_path(r)+'citation.bib" download>Download BibTeX</a> · <a href="'+resource_path(r)+'citation.csl.json" download>Download CSL JSON</a></p><p>Citations preserve the selected source edition, its authors and recorded date precision. Unrecorded venues and identifiers are omitted.</p>'
        body+=publication_body(r)
    if r["kind"] not in {"paper","survey"}:
        body+='<h2>What licenses are recorded?</h2><p>Code, training data, weights, and documents can have different terms. A blank declaration means unknown, not unrestricted use.</p><dl class="page-facts">'
        for slot,l in r["licenses"].items():
            value=f'<a href="{safe_href(l["url"])}">{esc(l["declared"] if isinstance(l["declared"],str) else ", ".join(l["declared"]))}</a> ({esc(l["basis"])})' if l else "Not recorded"
            body+=f'<div><dt>{esc(slot.title())}</dt><dd>{value}</dd></div>'
        body+='</dl>'
    if r['details'].get('license_review'):
        body+='<h2>License review notes</h2><ul>'+''.join('<li><strong>'+esc(slot.title())+':</strong> '+esc(review['reason'])+' '+''.join(f'<a href="{safe_href(url)}">Source {i+1}</a> ' for i,url in enumerate(review['evidence_urls']))+'</li>' for slot,review in r['details']['license_review'].items())+'</ul>'
    body+=resource_profile_html(r)
    details=[(k,v) for k,v in r["details"].items() if k not in {*PROFILE_KEYS.values(),'arxiv_snapshot','publication','license_review'} and v is not None and v!=[] and v!=""]
    if details:
        body+='<h2>Recorded specifications</h2><dl class="page-facts">'+''.join(f'<div><dt>{esc(k.replace("_"," "))}</dt><dd>{esc(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,bool)) else v)}</dd></div>' for k,v in details)+'</dl>'
    if r["notes"]:body+='<h2>Scope and limitations</h2><p>'+esc(r["notes"])+'</p>'
    if r["relations"]:
        body+='<h2>Related resources</h2><ul>'+''.join(f'<li>{esc(rel["type"].replace("_"," "))}: <a href="{resource_path(lookup[rel["target_id"]])}">{esc(lookup[rel["target_id"]]["name"])}</a></li>' for rel in r["relations"] if rel["target_id"] in lookup)+'</ul>'
    body+='<h2>Primary evidence and verification</h2><p>Source retrieval is separate from experiment reproduction. Use the original publication or publisher page when citing claims about the resource.</p><ol class="source-list">'
    for ev in r["evidence"]:
        body+=f'<li><a href="{safe_href(ev["url"])}">{esc(ev["method"].replace("_"," "))}</a><p>Retrieved {utc_time(ev["retrieved_at"])}. Supports: {esc(", ".join(ev["supports"]))}.</p><details><summary>Content fingerprint</summary><code>{esc(ev["sha256"])}</code></details></li>'
    body+='</ol><h2>Suggest a correction</h2><p><a href="'+SOURCE_REPO+'/issues/new?template=resource.yml">Open a source-backed correction</a>. Include this record ID and the original source. Read our <a href="/about/">editorial policy</a> and <a href="/coverage/">coverage boundaries</a>.</p>'
    return body


def utc_time(stamp):
    # Evidence timestamps read as "2026-10-16 06:31 UTC"; the exact recorded value stays in the datetime attribute.
    try:
        moment=dt.datetime.fromisoformat(stamp).astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return esc(stamp)
    return f'<time datetime="{esc(stamp)}">{moment:%Y-%m-%d %H:%M} UTC</time>'


def connected_assets_html(r, lookup, incoming):
    # Reviewed links from code, data and model records sit right under the facts, where readers of a paper look for them.
    backlinks=(incoming or {}).get(r['id'],[])
    if not backlinks:return ''
    labels={'documented_by':'Documented resource','introduced_by':'Introduced resource','published_by':'Published resource','variant_of':'Model variant','component_of':'Component'}
    body='<h2 id="connected-assets">Connected assets</h2><p>These links come from reviewed resource records. A documentation link does not imply a training-data or evaluation dependency.</p><ul>'
    for rel in backlinks:
        source=lookup[rel['source_id']]
        body+=f'<li>{esc(labels.get(rel["type"],rel["type"].replace("_"," ")))}: <a href="{resource_path(source)}">{esc(source["name"])}</a> · {esc(KINDS[source["kind"]])} · <a href="{safe_href(rel["evidence_url"])}">relationship evidence</a></li>'
    return body+'</ul>'


def resource_markdown(r):
    lines=[f'# {r["name"]}', '', description(r), '', f'- Catalog URL: {SITE}{resource_path(r)}', f'- Original source: {r["url"]}', f'- Kind: {r["kind"]}', f'- Review: {r["review_status"]}', f'- Scope: {r["scope"]}', f'- Environments: {", ".join(r["environments"])}', f'- Topics: {", ".join(r["topics"])}', f'- Evidence checked: {r["last_verified_at"]}', f'- ID: {r["id"]}', '', '## Limitations', '', r["notes"] or 'Inclusion does not establish reproducibility or endorsement.']
    lines+=['',f'- Record JSON: {SITE}{resource_path(r)}record.json']
    if r["authors"]:lines+=['','## Authors','',', '.join(r["authors"])]
    if r['kind'] in {'paper','survey'}:
        lines+=['','## Citation exports','',f'- BibTeX: {SITE}{resource_path(r)}citation.bib',f'- CSL JSON: {SITE}{resource_path(r)}citation.csl.json']
    pub=publication(r)
    if pub:
        lines+=['','## Publication record','', '- Title: '+pub['title'], '- Authors: '+', '.join(pub['authors']),
                '- Publication date (recorded precision): '+(format_date_parts(pub['date_parts']) or 'not recorded'),
                '- Publication source: '+pub['url'],
                '- Publication BibTeX: '+SITE+resource_path(r)+'publication-citation.bib',
                '- Publication CSL JSON: '+SITE+resource_path(r)+'publication-citation.csl.json']
        for key in ('venue','publisher','series','volume','issue','pages','doi','date_basis','event_dates','identity_basis','notes'):
            if pub.get(key):lines.append('- '+key.replace('_',' ')+': '+pub[key])
        lines+=['- Publication evidence: '+', '.join(pub['evidence_urls'])]
    snapshot=r['details'].get('arxiv_snapshot')
    if snapshot:
        lines+=['','## Recorded arXiv snapshot','',
                '- Version: '+(str(snapshot['version']) if snapshot.get('version') else 'not recorded'),
                '- Version source: '+(snapshot.get('versioned_url') or 'not recorded'),
                '- First submission: '+(snapshot.get('submitted_at') or 'not recorded'),
                '- Version updated: '+(snapshot.get('updated_at') or 'not recorded'),
                '- Abstract SHA-256: '+(snapshot.get('abstract_sha256') or 'not recorded'),
                '- Abstract hash normalization: '+snapshot['abstract_hash_method']]
    profile=r['details'].get(PROFILE_KEYS.get(r['kind']))
    if profile:
        lines+=['','## Structured profile','']
        for key,value in profile.items():
            if key in {'counts','evidence_urls','notes'}:continue
            lines.append('- '+key.replace('_',' ')+': '+(', '.join(value) if isinstance(value,list) and value else str(value) if value else 'not recorded'))
        lines+=['','### Count observations','']
        lines += [f'- {count_text(c)} ({c["basis"]}; source: {c.get("reference_url") or c["evidence_url"]})' for c in profile['counts']] or ['No count recorded.']
        lines+=['',profile['notes']]
    lines+=['','## License declarations','']
    for slot,license in r["licenses"].items():lines.append(f'- {slot}: '+(f'{license["declared"]} — {license["url"]}' if license else 'not recorded'))
    for slot,review in r['details'].get('license_review',{}).items():
        lines+=['',f'- {slot} review: '+review['reason'],'  Sources: '+', '.join(review['evidence_urls'])]
    lines+=['','## Primary evidence','']+[f'- {ev["url"]} (retrieved {ev["retrieved_at"]}; SHA-256 {ev["sha256"]})' for ev in r["evidence"]]
    return '\n'.join(line.rstrip() for line in lines)+'\n'


def build_search_pages(destination, rows, coverage, root, *, survey_page=None):
    lookup={r["id"]:r for r in rows}
    incoming=incoming_relations(rows)
    titles=resource_titles(rows)
    reviewed=[r for r in rows if eligible(r)]
    latest=coverage["as_of_utc"]
    manifest=[]
    if survey_page:
        # The reviewed standalone article is already final: never normalize its bytes.
        if survey_page != {'path':'/survey/','indexable':True,'sha256':hashlib.sha256((destination/'survey/index.html').read_bytes()).hexdigest()}:
            raise ValueError('Survey page does not match its copied bytes')
        manifest.append(dict(survey_page))
    script_versions={name:hashlib.sha256((destination/name).read_bytes()).hexdigest() for name in ('app.js','compare.js','downloads.js')}
    script_src=re.compile(r'''(?P<start><script\b[^>]*\bsrc\s*=\s*)(?P<quote>["'])(?P<path>(?:\./|/)(?:app|compare|downloads)\.js)(?:\?[^"'\r\n]*)?(?P=quote)''')
    def version_script_src(match):
        version=script_versions[Path(match['path']).name]
        return f"{match['start']}{match['quote']}{match['path']}?v={version}{match['quote']}"
    def emit(path,content,index=True,excluded=False):
        # Hash the final bytes, after replacing only the scripts this page uses.
        content=script_src.sub(version_script_src,clean_text(content)).encode('utf-8')
        target=destination/path.lstrip('/')/'index.html' if path.endswith('/') else destination/path.lstrip('/')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
        item={"path":path,"indexable":index,"sha256":hashlib.sha256(content).hexdigest()}
        if excluded:item["scope_excluded"]=True
        manifest.append(item)
    for r in rows:
        path=resource_path(r)
        emit(path,page(titles.get(r["id"],r["name"]),description(r),path,resource_body(r,lookup,incoming),resource_schema(r),eligible(r),crumbs=[("AwesomeCUA","/"),("Catalog","/catalog/"),(KINDS[r["kind"]],f'/categories/{r["kind"]}/'),(r["name"],path)]),eligible(r))
        (destination/path.lstrip('/')/'index.md').write_text(clean_text(resource_markdown(r)),encoding='utf-8')
        (destination/path.lstrip('/')/'record.json').write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
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
    category_links='<ul class="category-directory">'+''.join(f'<li><a href="/categories/{kind}/">{esc(name)}</a><span>{sum(r["kind"]==kind for r in rows):,} resources</span></li>' for kind,name in KINDS.items())+'</ul>'
    overview=f'<div class="eyebrow">COMPUTER-USE AGENT DIRECTORY</div><h1>Explore the computer-use agent ecosystem</h1><p class="answer-lead">AwesomeCUA connects research papers, GUI models, training datasets, benchmarks, engineering tools, products, and publishers with their original sources.</p><p>This snapshot has {len(rows):,} resource records, including {len(reviewed):,} reviewed entries. Counts are resources, not independent projects.</p><a class="button primary" href="/#catalog">Search and filter all resources</a><h2>Browse by resource type</h2>{category_links}<h2>Research and practical guides</h2><ul><li><a href="/topics/">Browse research and assets by topic</a></li><li><a href="/papers/">Reviewed computer-use and GUI-agent research papers</a></li><li><a href="/guides/">Guides to agents, benchmarks, and training data</a></li><li><a href="/data/">Download the source-backed catalog</a></li><li><a href="/coverage/">Inspect coverage and unresolved gaps</a></li></ul>'
    emit('/catalog/',page('Computer-use agent resource directory','Browse source-backed computer-use agent papers, models, datasets, benchmarks, tools, products, and publishers.','/catalog/',overview,{"@type":"CollectionPage","name":"AwesomeCUA resource directory"},crumbs=[("AwesomeCUA","/"),("Catalog","/catalog/")]))
    # GitHub Pages serves /404.html for any missing path; writing it outside emit() keeps it out of the manifest, sitemaps and IndexNow.
    missing=f'<div class="eyebrow">PAGE NOT FOUND</div><h1>This page is not in the catalog</h1><p class="answer-lead">The address may be mistyped, or the page may have been removed, for example when duplicate resource records were merged.</p><div class="page-actions"><a class="button primary" href="/#catalog">Search the catalog</a><a class="button secondary" href="/catalog/">Resource directory</a><a class="button secondary" href="/papers/">Research papers</a></div><h2>Browse by resource type</h2>{category_links}<h2>Report a broken link</h2><p>If a link led you here, <a href="{SOURCE_REPO}/issues/new/choose">open an issue</a> with the address you followed and the page that linked to it. Scope decisions are recorded in the <a href="/coverage/">coverage ledger</a>.</p>'
    (destination/'404.html').write_text(clean_text(page('Page not found','This address does not match a current AwesomeCUA page. Search the catalog, browse resource categories, or report the broken link.','/404.html',missing,index=False,canonical=False)),encoding='utf-8')
    for kind,label in KINDS.items():
        selected=sorted([r for r in reviewed if r['kind']==kind],key=lambda r:r['name'].lower())
        body=f'<div class="eyebrow">RESOURCE CATEGORY</div><h1>Computer-use agent {esc(label.lower())}</h1><p class="answer-lead">Browse {len(selected)} reviewed {esc(label.lower())} connected to computer-use, GUI, web, and mobile agents. Each entry links to primary evidence and records its scope.</p><p>Review means AI-assisted editorial inspection, not independent reproduction. Unknown licenses and specifications remain unknown.</p>'
        if kind=='paper':body+='<p>The complete bibliography includes metadata-only discoveries awaiting relevance review. They remain accessible in the <a href="/?kind=paper#catalog">interactive catalog</a> and data downloads.</p>'
        if kind in PROFILE_KEYS:body+=f'<p><a href="/compare/{"benchmarks" if kind=="benchmark" else "datasets"}/">Compare source-reviewed specifications</a></p>'
        if kind=='paper':
            # The paginated /papers/ library is the one indexable list of reviewed papers; this category is a hub into it.
            years=Counter(record_year(r) or 'undated' for r in selected);year_links=library_years(rows);topics=Counter(t for r in selected for t in r['topics'])
            body+='<p>The <a href="/papers/">research library</a> lists every reviewed paper and survey once, newest first, with authors, annotations and citations. Start from a publication year or a topic.</p><div class="page-actions"><a class="button primary" href="/papers/">Open the research library</a><a class="button secondary" href="/categories/survey/">Surveys</a></div>'
            body+='<h2>Papers by publication year</h2><nav class="paper-years" aria-label="Papers by publication year">'+''.join(f'<a href="{year_links[y]}">{"Date not recorded" if y=="undated" else y}<span>{years[y]:,}</span></a>' for y in sorted(years,key=lambda y:(y!='undated',y),reverse=True))+'</nav>'
            body+='<h2>Papers by topic</h2><div class="library-topics">'+''.join(f'<a href="{topic_path(t)}">{esc(topic_name(t))} ({n:,})</a>' for t,n in topics.most_common())+'</div>'
            schema={"@type":"CollectionPage","name":f'Computer-use agent {label.lower()}'}
        else:
            body+=listing(selected)
            schema={"@type":"ItemList","name":f'Computer-use agent {label.lower()}',"numberOfItems":len(selected),"itemListElement":[{"@type":"ListItem","position":i+1,"url":SITE+resource_path(r),"name":r['name']} for i,r in enumerate(selected)]}
        body+=f'<p><a href="/?kind={kind}#catalog">Search all records in this category</a> · <a href="/catalog/">All categories</a></p>'
        emit(f'/categories/{kind}/',page(f'Computer-use agent {label.lower()}',f'Reviewed {label.lower()} for computer-use and GUI agents, with original sources, platform tags, and license evidence.',f'/categories/{kind}/',body,schema,crumbs=[("AwesomeCUA","/"),("Catalog","/catalog/"),(label,f'/categories/{kind}/')]))
    for kind,plural,title in [('benchmark','benchmarks','Compare GUI-agent benchmark protocols'),('dataset','datasets','Compare GUI-agent training datasets')]:
        path=f'/compare/{plural}/'
        export=profile_export(rows,kind)
        (destination/f'downloads/{plural}-profiles.json').write_text(json.dumps(export,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        emit(path,page(title,f'Compare {plural} by source-reviewed interfaces, scope, counting units, and access information.',path,comparison_body(rows,kind,resource_path),{'@type':'CollectionPage','name':title},crumbs=[("AwesomeCUA","/"),("Catalog","/catalog/"),(title,path)]))
    papers=sorted([r for r in reviewed if r['kind'] in {'paper','survey'}],key=record_date_text,reverse=True)
    library_count=library_pages(rows)
    for language,title,summary in [
        ('en','Computer-use agent papers and surveys','Browse reviewed computer-use research by publication year, author, environment and topic, with original papers and BibTeX citations.'),
        ('zh','Computer-Use 论文库：按年份浏览论文与综述','按发表年份浏览经过来源审阅的 Computer-Use 与 GUI Agent 论文，查看作者、平台、研究主题和原论文，下载 BibTeX 引用。')]:
        root_crumb=("AwesomeCUA","/zh/" if language=='zh' else "/")
        for number in range(1,library_count+1):
            path=library_path(number,language)
            body,schema=paper_library(rows,resource_path,language=language,site_url=SITE,number=number,survey_available=bool(survey_page))
            numbered=(f'{title}, page {number}' if language=='en' else f'{title}（第 {number} 页）') if number>1 else title
            crumbs=[root_crumb,(title,library_path(1,language)),(f'Page {number}' if language=='en' else f'第 {number} 页',path)] if number>1 else None
            alternatives={'en':library_path(number),'zh-CN':library_path(number,'zh'),'x-default':library_path(number)}
            emit(path,page(numbered,summary,path,body,schema,lang='zh-CN' if language=='zh' else 'en',alternatives=alternatives,crumbs=crumbs))
    topic_manifest,topic_groups=write_topic_exports(destination,rows,(root/'data/catalog.jsonl').read_bytes())
    for language in ('en','zh'):
        path=topic_path(language=language)
        body,schema=topic_index_body(topic_manifest,language=language,site_url=SITE)
        title='Computer-use research topics' if language=='en' else 'Computer-Use 主题目录'
        summary='Explore source-reviewed computer-use papers, models, datasets, benchmarks and tools by topic.' if language=='en' else '按研究主题浏览已审阅的 Computer-Use 论文、模型、数据、基准与工具，并下载完整主题记录。'
        emit(path,page(title,summary,path,body,schema,lang='zh-CN' if language=='zh' else 'en',alternatives={'en':'/topics/','zh-CN':'/zh/topics/','x-default':'/topics/'}))
        for topic,members in topic_groups.items():
            first=topic_path(topic,language)
            title=topic_name(topic,language)+(' — computer-use research and resources' if language=='en' else '：Computer-Use 研究与资源')
            summary=(f'{len(members)} reviewed resources for {topic_name(topic)}, with original sources, full records and citations.' if language=='en' else f'{len(members)} 条已审阅的{topic_name(topic,language)}资源，包含原始来源、完整记录与论文引用。')
            for number in range(1,topic_page_count(topic_counts(members))+1):
                path=topic_path(topic,language,number)
                body,schema=topic_body(topic,members,resource_path,language=language,site_url=SITE,number=number)
                numbered=(f'{title}, page {number}' if language=='en' else f'{title}（第 {number} 页）') if number>1 else title
                alternatives={'en':topic_path(topic,'en',number),'zh-CN':topic_path(topic,'zh',number),'x-default':topic_path(topic,'en',number)}
                trail=[("AwesomeCUA","/zh/" if language=='zh' else "/"),("主题" if language=='zh' else "Topics",topic_path(language=language)),(topic_name(topic,language),first)]+([(f'Page {number}' if language=='en' else f'第 {number} 页',path)] if number>1 else [])
                emit(path,page(numbered,summary,path,body,schema,lang='zh-CN' if language=='zh' else 'en',alternatives=alternatives,crumbs=trail))
            (destination/first.lstrip('/')/'index.md').write_text(clean_text(topic_markdown(topic,members,resource_path,language=language,site_url=SITE)),encoding='utf-8')
    linked_papers=[r for r in papers if any(e['type'] in {'documented_by','introduced_by'} for e in incoming.get(r['id'],[]))]
    body='<div class="eyebrow">FOLLOW THE RESEARCH TO THE ASSETS</div><h1>Computer-use papers, code, and datasets</h1><p class="answer-lead">Find the implementations, benchmarks, and datasets connected to reviewed research papers. Every relationship below has a primary-source evidence link.</p><p>Connections describe publication documentation or introduction. They do not automatically mean that a model was trained on a dataset or evaluated on a benchmark.</p><div class="reading-list">'
    for paper in linked_papers:
        body+=f'<article><h2><a href="{resource_path(paper)}">{esc(paper["name"])}</a></h2><p>{esc(description(paper))}</p><ul>'
        for rel in incoming[paper['id']]:
            source=lookup[rel['source_id']]
            body+=f'<li><a href="{resource_path(source)}">{esc(source["name"])}</a> — {esc(KINDS[source["kind"]])} · <a href="{safe_href(rel["evidence_url"])}">source evidence</a></li>'
        body+='</ul></article>'
    body+='</div><p><a href="/downloads/relationships.json">Download reviewed relationships as JSON</a> · <a href="/about/">Editorial policy</a></p>'
    emit('/connections/',page('Computer-use papers, code, and datasets','Trace computer-use agent papers to documented implementations, GUI benchmarks, and training datasets using reviewed primary-source relationships.','/connections/',body))
    edges=[{'source_id':r['id'],'source_name':r['name'],'source_kind':r['kind'],**rel} for r in rows for rel in r['relations']]
    (destination/'downloads/relationships.json').write_text(json.dumps({'relation_count':len(edges),'semantics':'Reviewed semantic links only. Documentation does not establish training or evaluation dependency.','relations':edges},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sources=''.join(f'<tr><td><a href="{safe_href(s["url"])}">{esc(s["name"])}</a></td><td>{s["discovered"]}</td><td>{s["indexed"]}</td><td>{s["curated"]}</td><td>{s["excluded"]}</td></tr>' for s in coverage['sources'])
    body=f'<h1>Coverage and verification ledger</h1><p class="answer-lead">{len(rows):,} resource records: {len(reviewed):,} curated and {coverage["metadata_only_records"]:,} with bibliographic metadata verification only.</p><p>Evidence snapshot: {esc(latest)}. Resource types can refer to different parts of the same project. Source populations overlap and cannot be summed into a global field size.</p><h2>Discovery-source coverage</h2><div class="table-scroll"><table class="coverage-table"><thead><tr><th>Source</th><th>Found</th><th>Indexed</th><th>Curated</th><th>Excluded</th></tr></thead><tbody>{sources}</tbody></table></div><h2>Explicit scope exclusions</h2><p>{coverage["excluded_records"]} records are excluded after individual scope review. The original {coverage["arxiv_archive_records"]:,}-record arXiv metadata archive is retained. <a href="/downloads/exclusions.json">Inspect decisions and source evidence</a> · <a href="/downloads/arxiv-archive.jsonl">Download the raw archive</a>.</p><p>Unresolved-candidate counts exclude these completed scope decisions. A changed or unconfirmed exclusion returns to review; it cannot silently suppress a resource.</p><h2>What remains unverified?</h2><p>Most bibliography entries still require relevance review. Closed datasets, unpublished systems, and regional resources are not exhaustively represented. Asset sizes, model licenses, availability, and experiment protocols need continuing curation. Global completeness has not been established.</p><p>{coverage["unindexed_candidates"]} discovered identifiers remain unresolved, excluding applied scope decisions and {coverage.get("non_resource_candidates",0)+coverage.get("alias_candidates",0)} links reviewed as non-resources or other addresses of indexed resources.</p><p><a href="/downloads/coverage.json">Download the complete coverage ledger</a> · <a href="/about/">Editorial policy</a></p>'
    emit('/coverage/',page('Coverage and verification ledger','Inspect AwesomeCUA source populations, editorial review states, bibliographic verification, unresolved identifiers, and explicit coverage gaps.','/coverage/',body))
    for language,path,title,desc in [
        ('en','/agents/','Use AwesomeCUA with agents and RAG','Clone the complete computer-use catalog, search locally, and ingest citation-preserving retrieval documents with review states and source evidence.'),
        ('zh','/zh/agents/','AwesomeCUA：Agents 与 RAG 使用指南','一行克隆完整目录，本地检索或接入 RAG，保留资源引用、审阅状态、论文版本和来源指纹。')]:
        emit(path,page(title,desc,path,agent_guide_body(language),{'@type':'Article','headline':title,'description':desc,'author':{'@id':SITE+'/#organization'}},lang='zh-CN' if language=='zh' else 'en'))
    scan_config=json.loads((root/'data/scan-config.json').read_text(encoding='utf-8'))
    scan_path=root/'data/scan-status.json'
    scan=json.loads(scan_path.read_text(encoding='utf-8')) if scan_path.exists() else None
    schedule=', '.join(scan_config['scan_times_local'])+' '+scan_config['timezone']
    publication_schedule=', '.join(scan_config['publish_times_local'])+' '+scan_config['timezone']
    body=f'<div class="eyebrow">DISCOVERY ACTIVITY</div><h1>Catalog updates three times daily</h1><p class="answer-lead">Public sources are scheduled for scanning three times a day. New paper identities are checked against arXiv; editorial annotations and approvals remain separate.</p><dl class="page-facts"><div><dt>Configured scan times</dt><dd>{esc(schedule)}</dd></div><div><dt>Website rebuild times</dt><dd>{esc(publication_schedule)}</dd></div></dl><p>GitHub scheduling can be delayed. The completion times below record what actually ran, rather than assuming that a scheduled job executed.</p>'
    body+=f'<h2>Current published catalog</h2><dl class="page-facts"><div><dt>Reviewed papers and surveys</dt><dd>{len(papers):,}</dd></div><div><dt>Other reviewed resources</dt><dd>{len(reviewed)-len(papers):,}</dd></div><div><dt>Total resource records</dt><dd>{len(rows):,}</dd></div></dl><p>These counts include editorial work completed after the scan below. <a href="/papers/">Browse reviewed research</a> or <a href="/coverage/">inspect full coverage</a>.</p>'
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
    body+='<h2>What automation does and does not establish</h2><p>A scan can discover a source or verify bibliographic fields. It does not reproduce experiments, approve a resource’s relevance, establish dataset permissions, or add editorial summaries. Existing reviewed snapshots are preserved; observed metadata changes are queued for review.</p><p><a href="https://github.com/reacher-z/Awesome-CUA/actions/workflows/scan.yml">Discovery workflow</a> · <a href="'+REPO+'/actions/workflows/publish.yml">Publication workflow</a> · <a href="/coverage/">Coverage ledger</a></p>'
    body+='<p><a href="'+REPO+'/blob/main/.indexnow/submissions.json">Search notification receipts</a> record which changed pages were submitted after publication and the response received. Submission is separate from search indexing.</p>'
    discovery=coverage.get('paper_discovery',{})
    if discovery:
        body+=f'<h2>Latest paper-discovery pass</h2><p>{esc(discovery.get("finished_at") or "In progress")} · {discovery.get("successful_query_count",0)} / {discovery.get("configured_query_count",0)} query windows succeeded · {discovery.get("unique_identifiers",0):,} distinct identifiers · {discovery.get("new_candidate_count",0):,} new candidates.</p><p>Ranked search windows overlap and do not measure global completeness. Newly found identifiers still need primary metadata verification and relevance review.</p><div class="table-scroll"><table><thead><tr><th>Area / query</th><th>Unique hits</th><th>New candidates</th><th>Window limit</th><th>State</th></tr></thead><tbody>'
        for item in discovery.get('queries',[]):
            ok=item.get('state')=='success'
            body+=f'<tr><td>{esc(item["area"])}<br><small>{esc(item["query"])}</small></td><td>{item.get("unique_count",0) if ok else "—"}</td><td>{item.get("new_candidate_count",0) if ok else "—"}</td><td>{item["limit"]}</td><td>{esc(item["state"])}</td></tr>'
        body+='</tbody></table></div><p>Per-query new counts depend on query order and count first discovery in this pass. <a href="/downloads/paper-discovery-queries.json">Query registry</a> · <a href="/downloads/paper-discovery-status.json">Results and source receipts</a></p>'
    conference_file=root/'data/conference-discovery.json'
    if conference_file.exists():
        conference=json.loads(conference_file.read_text(encoding='utf-8'))
        body+=f'<h2>Conference proceedings sweep</h2><p>{conference["title_candidate_count"]} keyword-selected titles were inspected across {conference["source_count"]} official proceedings snapshots. This is a separate bounded sweep, not a complete conference census. Title candidates and possible renamed papers remain unapproved pending identity and scope review.</p><p><a href="/downloads/conference-discovery.json">Inspect the selected titles, review boundaries, and primary receipts</a>.</p>'
    emit('/updates/',page('Catalog updates three times daily','Inspect the actual completion, discoveries, and source gaps from the AwesomeCUA three daily public-source scans.','/updates/',body))
    badge_papers=sum(r['kind'] in {'paper','survey'} for r in reviewed)
    (destination/'badges').mkdir(exist_ok=True)
    badge=f'<svg xmlns="http://www.w3.org/2000/svg" width="590" height="30" role="img" aria-label="{len(rows)} resources, {len(reviewed)} reviewed resources, {badge_papers} reviewed papers"><rect width="590" height="30" rx="5" fill="#4856df"/><g fill="#fff" font-family="Arial,sans-serif" font-size="12" text-anchor="middle"><text x="85" y="20">{len(rows):,} resources</text><text x="270" y="20">{len(reviewed):,} reviewed resources</text><text x="485" y="20">{badge_papers:,} reviewed papers</text></g></svg>'
    (destination/'badges/catalog.svg').write_text(badge,encoding='utf-8')
    featured_badges=[('featured-by-awesomecua-laurel.svg','Purple laurel, CUA shield, and serif lettering',480,106),('featured-by-awesomecua.svg','Light badge',200,40),('featured-by-awesomecua-dark.svg','Dark badge',200,40),('awesomecua-featured-seal.svg','Featured seal',140,156)]
    if all((destination/'badges'/name).is_file() for name,_,_,_ in featured_badges):
        body='<h1>Featured by AwesomeCUA</h1><p class="answer-lead">SVG badges for project pages, GitHub READMEs, and release notes. Link a badge to your resource’s AwesomeCUA entry so readers can inspect its sources.</p><div class="badge-gallery">'
        for name,label,width,height in featured_badges:
            body+=f'<figure><div class="badge-preview{" badge-preview-dark" if "dark" in name else ""}"><img src="/badges/{name}" width="{width}" height="{height}" alt="{esc(label)}: Featured by AwesomeCUA"></div><figcaption><strong>{esc(label)}</strong> · <a href="/badges/{name}" download>Download SVG</a></figcaption></figure>'
        body+='</div><h2>Add a badge to your README</h2><p>Replace <code>YOUR_RESOURCE_URL</code> with the link to your listed resource. The image is hosted here; no third-party image service is required.</p><pre><code>[![Featured by AwesomeCUA](https://awesomecua.github.io/badges/featured-by-awesomecua-laurel.svg)](YOUR_RESOURCE_URL)</code></pre><p>“Featured” indicates a catalog listing, not certification of performance, security, or reuse rights. Check the resource’s review state and primary evidence. The original SVG artwork is available under the <a href="'+SOURCE_REPO+'/blob/main/LICENSE">MIT license</a>.</p><p><a href="/catalog/">Find your resource</a> · <a href="/about/">Editorial policy</a></p>'
        emit('/badges/',page('Featured resource badges','Download original AwesomeCUA SVG badges and link them to a source-backed resource entry.','/badges/',body))
    body='<h1>About AwesomeCUA and its editorial policy</h1><p class="answer-lead">AwesomeCUA is a source-backed catalog of resources for agents that operate computer interfaces. Its purpose is to make research and engineering assets easier to find, compare, and trace to their original publishers.</p><h2>Who maintains the catalog?</h2><p>The AwesomeCUA project publishes the catalog through its <a href="https://github.com/AwesomeCUA">GitHub organization</a>. Annotations and taxonomy are produced with AI-assisted editorial review. This is not a claim of independent peer review, benchmark reproduction, or affiliation with listed publishers.</p><h2>What is included?</h2><p>GUI and hybrid GUI/code agents, visual grounding, web and mobile navigation, training data, evaluation environments, execution infrastructure, safety research, and relevant products. Supporting tools may be marked adjacent.</p><h2>How are claims checked?</h2><p>Community lists and semantic searches discover candidates. Retained arXiv and publication sources support bibliographic facts. Official papers, repositories, documentation, and model/dataset cards support curated annotations. Every record retains source URLs, retrieval timestamps, and content hashes. Source refreshes do not silently inherit editorial approval.</p><h2>What do review states mean?</h2><ul><li><strong>Curated:</strong> a primary source was inspected for identity, scope, and the concise annotation.</li><li><strong>Metadata verified:</strong> bibliographic fields were checked; relevance, taxonomy, and findings are still pending.</li><li><strong>Candidate:</strong> an identifier was discovered but is not a published catalog record.</li></ul><h2>Licenses and corrections</h2><p>Code, data, weights, and document licenses are separate. Public availability does not establish reuse rights. Original catalog annotations and code use MIT; upstream resources keep their own terms. Report errors through <a href="'+SOURCE_REPO+'/issues/new?template=resource.yml">a source-backed correction</a>.</p><h2>Indexing policy</h2><p>Reviewed resource pages and useful collection pages are eligible for indexing. Metadata-only resource pages remain accessible, with <code>noindex,follow</code> until their relevance is reviewed. The full bibliography remains searchable and downloadable.</p><p><a href="/coverage/">Coverage ledger</a> · <a href="/data/">Data and provenance</a></p>'
    emit('/about/',page('About AwesomeCUA and editorial policy','Learn what AwesomeCUA includes, how primary-source review works, what verification does and does not mean, and how to suggest corrections.','/about/',body))
    desc='A structured catalog of computer-use agent research papers, models, datasets, benchmarks, tools, products, and publishers, including original annotations, review states, source evidence, scoped license declarations, and resource relationships.'
    dataset={"@type":"Dataset","name":"AwesomeCUA computer-use agent resource catalog","description":desc,"url":SITE+'/data/',"creator":{"@id":SITE+'/#organization'},"license":SOURCE_REPO+'/blob/main/LICENSE',"dateModified":latest,"keywords":["computer-use agents","GUI agents","browser agents","datasets","benchmarks"],"distribution":[{"@type":"DataDownload","encodingFormat":"application/x-ndjson","contentUrl":SITE+'/downloads/catalog.jsonl'},{"@type":"DataDownload","encodingFormat":"application/json","contentUrl":SITE+'/data/records.json'},{"@type":"DataDownload","encodingFormat":"application/vnd.sqlite3","contentUrl":SITE+'/downloads/catalog.sqlite'}],"isAccessibleForFree":True}
    download_manifest=build_download_manifest(destination,rows,(root/'data/catalog.jsonl').read_bytes())
    data_alternatives={'en':'/data/','zh-CN':'/zh/data/','x-default':'/data/'}
    for language,path,title,summary in [
        ('en','/data/','AwesomeCUA data downloads for people and agents',desc),
        ('zh','/zh/data/','AwesomeCUA 数据中心：完整目录、RAG 与论文引用','下载完整 Computer-Use 资源目录、RAG 检索文档、论文引用和来源文件，查看实际条数、文件大小与 SHA-256 指纹。')]:
        body=data_hub_body(download_manifest,language=language,site_url=SITE)
        data_schema={**dataset,'url':SITE+path,'description':summary}
        emit(path,page(title,summary,path,body,data_schema,lang='zh-CN' if language=='zh' else 'en',alternatives=data_alternatives))
    guides=json.loads((root/'data/site-guides.json').read_text(encoding='utf-8'))
    for guide in guides:
        emit(guide_path(guide),page(guide['title'],guide['description'],guide_path(guide),guide['body'],{"@type":"Article","headline":guide['title'],"description":guide['description'],"author":{"@id":SITE+'/#organization'}},crumbs=[("AwesomeCUA","/"),("Guides","/guides/"),(guide['title'],guide_path(guide))]))
    body='<h1>Guides to computer-use agents</h1><p class="answer-lead">Practical reading guides with direct answers and primary research references. These guides help distinguish interface grounding, task execution, training data, and evaluation.</p><div class="reading-list">'+''.join(f'<article><h2><a href="{guide_path(g)}">{esc(g["title"])}</a></h2><p>{esc(g["description"])}</p></article>' for g in guides)+'</div>'
    emit('/guides/',page('Computer-use agent guides','Understand computer-use agents, choose GUI-agent benchmarks, and find training datasets with clearly scoped primary-source references.','/guides/',body))
    zh=f'<div class="eyebrow">COMPUTER-USE AGENT 资源指南</div><h1>AwesomeCUA：可追溯的智能体资源目录</h1><p class="answer-lead">连接论文、模型、数据集、评测基准、框架、工具、产品与发布方。每条资源保留一手来源与审阅状态。</p><p>当前有 {len(rows):,} 条资源，{len(reviewed):,} 条经过 AI 辅助编辑审阅。数量以资源为单位，不代表独立项目总数。</p><div class="page-actions"><a class="button primary" href="/?lang=zh#catalog">打开中文搜索目录</a><a class="button secondary" href="/zh/data/">下载数据</a></div><h2>研究与训练</h2><ul><li><a href="/zh/topics/">按主题浏览论文、数据与工具</a></li><li><a href="/zh/papers/">论文与综述阅读列表</a></li><li><a href="/categories/dataset/">训练数据集</a> · <a href="/compare/datasets/">对比数据规格</a></li><li><a href="/categories/benchmark/">GUI、桌面、网页与手机评测基准</a> · <a href="/compare/benchmarks/">对比评测协议</a></li><li><a href="/categories/model/">模型与权重版本</a></li></ul><h2>产业与工程</h2><ul><li><a href="/categories/agent/">智能体</a></li><li><a href="/categories/framework/">开发与训练框架</a></li><li><a href="/categories/product/">产品</a></li><li><a href="/catalog/">浏览全部分类</a></li></ul><h2>如何理解“已核验”？</h2><p>已审阅条目经过一手来源编辑检查。论文元数据仅核实标题、作者和日期，不代表研究结论或实验已复现。代码、数据、权重与文档许可分别记录，未知信息保留为空。</p><h2>是否已经全球最全？</h2><p>全面覆盖是目标，目前没有足够证据证明已达到全球最全。请查看<a href="/coverage/">覆盖台账</a>和<a href="/about/">编辑方法</a>了解边界与缺口。</p>'
    emit('/zh/',page('AwesomeCUA 中文主页：Computer-Use Agent 资源目录','浏览可搜索、可追溯的 Computer-Use Agent 论文、模型、数据集、基准、框架与产品，查看来源证据并下载结构化目录。','/zh/',zh,lang='zh-CN',alternatives=True))
    # A static, visible directory is useful to visitors even when JavaScript is unavailable.
    home=(destination/'index.html').read_text(encoding='utf-8')
    home=re.sub(r'<!-- SURVEY:START -->(.*?)<!-- SURVEY:END -->',lambda m:m[1] if survey_page else '',home,flags=re.S)
    extra=f'<link rel="canonical" href="{SITE}/"><meta name="robots" content="index,follow,max-image-preview:large"><meta property="og:url" content="{SITE}/"><link rel="alternate" hreflang="en" href="{SITE}/"><link rel="alternate" hreflang="zh-CN" href="{SITE}/zh/"><link rel="alternate" hreflang="x-default" href="{SITE}/"><link rel="alternate" type="application/atom+xml" href="{SITE}/feed.xml" title="AwesomeCUA research updates"><link rel="stylesheet" href="./pages.css">'
    home=home.replace('</head>',extra+f'<script type="application/ld+json">{jsonld({"@context":"https://schema.org","@graph":[organization(),{"@type":"WebSite","@id":SITE+"/#website","url":SITE+"/","name":"AwesomeCUA","description":"Source-backed computer-use and GUI-agent resource catalog","publisher":{"@id":SITE+"/#organization"}}]})}</script></head>')
    for identity,value in [('stat-resources',len(rows)),('stat-curated',len(reviewed)),('stat-kinds',len(KINDS)),('stat-sources',len(coverage['sources']))]:
        home=re.sub(f'(id="{identity}">).*?(</span>)',lambda m:m.group(1)+format(value,',')+m.group(2),home)
    home=home.replace('id="snapshot-date">—','id="snapshot-date">'+latest[:10])
    static='<section class="shell static-directory" aria-labelledby="static-directory-title"><div class="eyebrow" data-i18n="directoryEyebrow">READ, EXPLORE, AND CITE</div><h2 id="static-directory-title" data-i18n="directoryHeading">Computer-use agent research and resources</h2><p data-i18n="directoryCopy">Browse source-backed pages directly, with or without JavaScript. Reviewed entries include concise annotations, provenance, and separate license declarations.</p><div class="directory-links"><a href="/catalog/" data-i18n="directoryTitle">Resource directory</a><a href="/papers/" data-paper-library data-i18n="directoryPapers">Research papers</a><a href="/topics/" data-topic-directory data-i18n="directoryTopics">Browse by topic</a><a href="/connections/" data-i18n="directoryConnections">Papers → code & data</a><a href="/updates/" data-i18n="directoryUpdates">Three daily updates</a><a href="/categories/model/" data-i18n="directoryModels">Models</a><a href="/categories/dataset/" data-i18n="directoryDatasets">Datasets</a><a href="/categories/benchmark/" data-i18n="directoryBenchmarks">Benchmarks</a><a href="/compare/benchmarks/" data-i18n="compareBenchmarks">Compare benchmarks</a><a href="/compare/datasets/" data-i18n="compareDatasets">Compare datasets</a><a href="/categories/framework/" data-i18n="directoryFrameworks">Frameworks</a><a href="/categories/product/" data-i18n="directoryProducts">Products</a><a href="/guides/" data-i18n="navGuides">Guides</a><a href="/data/" data-i18n="directoryData">Download data</a><a href="/coverage/" data-i18n="navCoverage">Coverage</a><a href="/about/" data-i18n="editorialPolicy">Editorial policy</a><a href="/zh/" lang="zh-CN">中文指南</a></div><h3 data-i18n="startHeading">Where should I start?</h3><p><a href="/guides/what-are-computer-use-agents/" data-i18n="startConcepts">Understand computer-use agents</a><span data-i18n="listComma">, </span><a href="/guides/gui-agent-benchmarks/" data-i18n="startBenchmarks">choose a benchmark for the capability you need</a><span data-i18n="listOr">, or </span><a href="/guides/gui-agent-training-data/" data-i18n="startData">find training data with the right supervision and license</a><span data-i18n="sentenceEnd">.</span></p></section>'
    home=home.replace('</main>',static+'</main>')
    emit('/',home)
    feed=ET.Element('feed',xmlns='http://www.w3.org/2005/Atom')
    for key,value in [('title','AwesomeCUA research reading list'),('id',SITE+'/papers/'),('updated',latest)]:ET.SubElement(feed,key).text=value
    ET.SubElement(feed,'link',href=SITE+'/feed.xml',rel='self');ET.SubElement(feed,'link',href=SITE+'/papers/')
    for r in papers[:50]:
        entry=ET.SubElement(feed,'entry')
        for key,value in [('title',r['name']),('id',SITE+resource_path(r)),('updated',r['last_verified_at']),('summary',description(r))]:ET.SubElement(entry,key).text=value
        ET.SubElement(entry,'link',href=SITE+resource_path(r));author=ET.SubElement(entry,'author');ET.SubElement(author,'name').text='AwesomeCUA'
    (destination/'feed.xml').write_bytes(clean_text(ET.tostring(feed,encoding='utf-8',xml_declaration=True).decode()).encode())
    llms=['# AwesomeCUA','', '> A source-backed computer-use agent resource catalog. Distinguish curated entries from metadata-only bibliography records.','', 'Resource counts are not independent project counts. Primary-source retrieval does not establish reproducibility. Code, data, weights, and document licenses are separate.','', '## Start here','',f'- [Catalog]({SITE}/catalog/): resource categories',f'- [Research]({SITE}/papers/): reviewed papers and surveys',f'- [中文论文库]({SITE}/zh/papers/): 按年份浏览论文与综述',f'- [Guides]({SITE}/guides/): definitions and practical reading guides',f'- [Editorial policy]({SITE}/about/): review states and limits',f'- [Coverage]({SITE}/coverage/): source populations and known gaps',f'- [Data downloads]({SITE}/data/): structured catalog with provenance','', '## Machine-readable access','',f'- [Full catalog JSONL]({SITE}/downloads/catalog.jsonl)',f'- [Curated annotations in Markdown]({SITE}/llms-full.txt)',f'- [Research Atom feed]({SITE}/feed.xml)','', 'Resource HTML pages have a companion `index.md` at the same path. This file is an optional navigation aid, not an indexing requirement or a request to rank this site.']
    llms += ['', '## Compare source-reviewed specifications', '', f'- [Benchmark protocols]({SITE}/compare/benchmarks/)', f'- [Dataset profiles]({SITE}/compare/datasets/)', f'- [Benchmark profiles JSON]({SITE}/downloads/benchmarks-profiles.json)', f'- [Dataset profiles JSON]({SITE}/downloads/datasets-profiles.json)']
    llms.extend(['', '## Agent and RAG access', '', '```sh', 'git clone https://github.com/reacher-z/Awesome-CUA.git', '```', '', f'- [Agent instructions]({SITE}/AGENTS.md)', f'- [Human and agent guide]({SITE}/agents/)', f'- [中文指南]({SITE}/zh/agents/)', f'- [Reviewed retrieval documents]({SITE}/downloads/rag-documents.jsonl)', f'- [All retrieval documents]({SITE}/downloads/rag-all-records.jsonl)', f'- [Export manifest]({SITE}/downloads/rag-manifest.json)'])
    llms.extend(['', '## Individual records and citations', '', 'Each active resource page serves its complete record at `record.json`. Scope-excluded resources return a JSON object with `status: excluded`, not an active record.', '', f'- [Reviewed paper BibTeX]({SITE}/downloads/citations.bib)', f'- [Reviewed paper CSL JSON]({SITE}/downloads/citations.csl.json)', f'- [Citation manifest]({SITE}/downloads/citations-manifest.json)'])
    llms.extend(['', '## Publication editions', '', 'Default arXiv citations retain the recorded preprint. Publication editions use their own title/authors/date and do not create extra catalog papers. Date components keep their recorded precision.', '', f'- [Reviewed publication BibTeX]({SITE}/downloads/publication-citations.bib)', f'- [Reviewed publication CSL JSON]({SITE}/downloads/publication-citations.csl.json)', f'- [Publication observations]({SITE}/downloads/publications.jsonl)', f'- [Publication observation schema]({SITE}/schemas/publication-observation.schema.json)', '', 'Resources with publication metadata also serve `publication-citation.bib` and `publication-citation.csl.json` next to their retained-source citation files.'])
    llms.extend(['', '## Topic collections', '', f'- [Topic directory]({SITE}/topics/)', f'- [中文主题目录]({SITE}/zh/topics/)', f'- [Topic manifest]({SITE}/downloads/topics.json): exact reviewed resource IDs, counts, subset URLs and SHA-256 fingerprints. Topic memberships overlap; counts must not be summed.', '', 'The first page of each topic has an index.md listing all of its resources. Each /downloads/topics/<topic>/ directory serves records.jsonl, citations.bib and citations.csl.json. Pass records.jsonl to export_rag.py --input to build a topic-specific retrieval corpus.'])
    llms.extend(['', '## Repository identity', '', f'- [Verified former repository names]({SITE}/downloads/repository-aliases.json): paired official API observations with the same GitHub or Hugging Face repository ID. Use the canonical returned ID for retrieval upserts; aliases add no resources. Record fields and RAG documents retain former names and their alias-scoped evidence.', f'- [Repository identity schema]({SITE}/schemas/repository-alias.schema.json)'])
    llms.extend(['', '## Download inventory', '', f'- [Bilingual data hub]({SITE}/data/)', f'- [中文数据中心]({SITE}/zh/data/)', f'- [Download manifest]({SITE}/downloads/manifest.json): file paths, exact byte sizes, SHA-256 fingerprints, counts and units. Compare catalog_sha256 with the RAG, citation and topic manifests before combining artifacts.', f'- [Download manifest schema]({SITE}/schemas/download-manifest.schema.json)'])
    llms.extend(['', '## Versioned data', '', f'- [Tagged data releases]({RELEASES_URL}): complete data bundles containing catalog, RAG, citations and topic subsets. Verify SHA256SUMS and retain release-manifest.json, source_commit and catalog_sha256. Repository CLI commands require a source clone at the recorded commit.'])
    survey_navigation=''
    if survey_page:
        llms.extend(['', '## English research survey', '', f'- [Computer-use agent survey]({SITE}/survey/): working manuscript with a separately frozen research inventory; not an additional catalog record.', f'- [Survey bibliography]({SITE}/survey/references.bib)', f'- [Survey references JSON]({SITE}/survey/references.json)', f'- [Source reading register]({SITE}/survey/evidence/reading-index.json)', f'- [Survey file manifest]({SITE}/survey/build-manifest.json)'])
        survey_navigation=f'Related reading: [English research survey]({SITE}/survey/). This working manuscript uses its own frozen inventory; its text is separate from the catalog annotations below.\n\n'
    (destination/'llms.txt').write_text(clean_text('\n'.join(llms)+'\n'),encoding='utf-8')
    (destination/'llms-full.txt').write_text(clean_text('# AwesomeCUA curated resource annotations\n\n'+f'Evidence snapshot: {latest}. These records were reviewed with AI assistance; experiments are not independently reproduced.\n\n'+survey_navigation+'\n---\n\n'.join(resource_markdown(r) for r in reviewed)),encoding='utf-8')
    robots='User-agent: *\nAllow: /\n\n'+''.join(f'User-agent: {bot}\nAllow: /\n\n' for bot in ['Googlebot','bingbot','OAI-SearchBot','PerplexityBot','Claude-SearchBot'])+f'Sitemap: {SITE}/sitemap.xml\nSitemap: {SITE}/sitemap.txt\n'
    (destination/'robots.txt').write_text(clean_text(robots),encoding='utf-8')
    sitemap=ET.Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for item in sorted(manifest,key=lambda x:x['path']):
        if item['indexable']:
            node=ET.SubElement(sitemap,'url');ET.SubElement(node,'loc').text=SITE+item['path']
            # No synthetic build-time lastmod; upstream evidence time is not page modification time.
    ET.indent(sitemap,space='  ')
    (destination/'sitemap.xml').write_bytes(clean_text(ET.tostring(sitemap,encoding='utf-8',xml_declaration=True).decode()).encode())
    (destination/'sitemap.txt').write_text(clean_text(''.join(SITE+item['path']+'\n' for item in sorted(manifest,key=lambda x:x['path']) if item['indexable'])),encoding='utf-8')
    (destination/'data/search-manifest.json').write_text(json.dumps({'site_url':SITE,'indexable_pages':sum(x['indexable'] for x in manifest),'metadata_only_pages':sum(not x['indexable'] and not x.get('scope_excluded') for x in manifest),'excluded_pages':sum(bool(x.get('scope_excluded')) for x in manifest),'pages':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    config=json.loads((root/'data/site-discovery.json').read_text(encoding='utf-8'))
    key=config['indexnow_key'];(destination/(key+'.txt')).write_text(key,encoding='utf-8')
    return manifest
