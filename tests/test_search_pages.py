import hashlib
import html
from contextlib import closing
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_site import build_site
from site_fixture import code_only, shared_site
import home_page
from search_pages import SITE, eligible, listing, resource_path, resource_schema, page, incoming_relations, zh_resource_path
from sitemaps import sitemap_urls

ROOT=Path(__file__).resolve().parents[1]


def copy_survey_source_inputs(destination):
    """Isolated script-version fixtures retain the reviewed survey's declared input bytes."""
    manifest = ROOT/'web/survey/build-manifest.json'
    if manifest.exists():
        for name in json.loads(manifest.read_text(encoding='utf-8'))['input_sha256']:
            target = destination/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name, target)


def page_origin(site,path):
    # The reviewed survey bundle keeps the origin it was built for (SITE or a former origin) until it is rebuilt.
    if path=='/survey/':return json.loads((site/'survey/build-manifest.json').read_text(encoding='utf-8'))['canonical_location_intended'].removesuffix(path)
    return SITE


class PageParser(HTMLParser):
    def __init__(self,text):
        super().__init__();self.canonical=[];self.robots=[];self.links=[];self.scripts=[];self.heading_count=0
        self.alternates={};self.language=None
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a['href'])
        if tag=='link' and a.get('rel')=='alternate' and 'hreflang' in a:self.alternates[a['hreflang']]=a['href']
        if tag=='html':self.language=a.get('lang')
        if tag=='meta' and a.get('name')=='robots':self.robots.append(a['content'])
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag=='script' and 'src' in a:self.scripts.append(a['src'])
        if tag=='h1':self.heading_count+=1


class ListingRowTests(unittest.TestCase):
    def test_a_featured_row_without_a_catalog_record_links_to_its_repository(self):
        row=listing([home_page.WEBSITEBENCH])
        self.assertIn(f'<a href="{home_page.WEBSITEBENCH["url"]}"',row)
        self.assertNotIn('/resources/',row)
        self.assertIn(home_page.WEBSITEBENCH['summary'],row)

    def test_a_catalog_record_links_to_its_resource_page(self):
        record={**home_page.WEBSITEBENCH,'review_status':'source-reviewed'}
        del record['href']
        self.assertIn(f'<a href="{resource_path(record)}"',listing([record]))


class SearchPagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.dest=shared_site()
        cls.rows=[json.loads(x) for x in (ROOT/'data/catalog.jsonl').read_text().splitlines()]
        cls.manifest=json.loads((cls.dest/'data/search-manifest.json').read_text())
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_permalink_identity_survives_display_name_change(self):
        r=self.rows[0];self.assertEqual(resource_path(r),resource_path({**r,'name':'A renamed resource'}))
        self.assertEqual(len({resource_path(r) for r in self.rows}),len(self.rows))
    def test_paper_document_license_is_visible_without_granting_code_permissions(self):
        records=[r for r in self.rows if r['kind']=='paper' and r['licenses']['document']]
        self.assertTrue(records)
        for r in records:
            with self.subTest(r['id']):
                text=(self.dest/resource_path(r).lstrip('/')/'index.html').read_text()
                license=r['licenses']['document']
                self.assertIn('What licenses are recorded?',text)
                self.assertIn(html.escape(license['declared']),text)
                self.assertIn(html.escape(license['url'],quote=True),text)
                for slot in ('code','data','weights'):
                    if r['licenses'][slot] is None:
                        self.assertIn(f'<dt>{slot.title()}</dt><dd>Not recorded</dd>',text)
    def test_every_page_has_matching_canonical_robots_and_visible_heading(self):
        for item in self.manifest['pages']:
            text=(self.dest/item['path'].lstrip('/')/'index.html').read_text();p=PageParser(text)
            self.assertEqual(p.canonical,[page_origin(self.dest,item['path'])+item['path']],item['path'])
            self.assertEqual(p.heading_count,1,item['path'])
            self.assertEqual('noindex' in p.robots[0],not item['indexable'],item['path'])
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>',text,re.S):
                value=json.loads(block);self.assertEqual(value['@context'],'https://schema.org')
    def test_sitemaps_list_exactly_the_reviewed_indexable_pages(self):
        urls=sitemap_urls(self.dest,SITE)
        expected={SITE+p['path'] for p in self.manifest['pages'] if p['indexable']}
        self.assertEqual(set(urls),expected);self.assertEqual(len(urls),len(set(urls)))
        for row in self.rows:self.assertEqual(SITE+resource_path(row) in urls,eligible(row))
        self.assertEqual(sorted((self.dest/'sitemap.txt').read_text().splitlines()),sorted(urls))
    def test_static_pages_link_to_real_local_destinations(self):
        for item in self.manifest['pages']:
            p=PageParser((self.dest/item['path'].lstrip('/')/'index.html').read_text())
            for link in p.links:
                u=urllib.parse.urlsplit(link)
                if u.scheme or u.netloc:continue
                path=urllib.parse.urlsplit(urllib.parse.urljoin(SITE+item['path'],link)).path
                target=self.dest/path.lstrip('/')
                if path.endswith('/'):target=target/'index.html'
                self.assertTrue(target.exists(),f'{item["path"]} -> {link}')
    def category_rows(self,path):
        text=(self.dest/path).read_text()
        return text,re.findall(r'<h3 class="row-name"><a [^>]*>([^<]*)</a>',text)
    def category_pages(self,kind,lang):
        prefix='zh/categories/' if lang=='zh' else 'categories/'
        paths,number=[],1
        while (self.dest/prefix/f'{kind}/index.html' if number==1 else self.dest/prefix/f'{kind}/page/{number}/index.html').is_file():
            paths.append(prefix+f'{kind}/index.html' if number==1 else prefix+f'{kind}/page/{number}/index.html')
            number+=1
        return paths

    def test_homepage_search_form_submits_to_the_explorer_in_its_language(self):
        form='<form class="field" role="search" action="/explore/#catalog" method="get" data-finder-form>'
        self.assertIn(form,(self.dest/'index.html').read_text())
        self.assertNotIn('name="lang"',(self.dest/'index.html').read_text())
        self.assertIn(form+'<input type="hidden" name="lang" value="zh">',(self.dest/'zh/index.html').read_text())

    def test_every_reviewed_resource_has_a_chinese_twin_that_names_its_english_page(self):
        urls=set(sitemap_urls(self.dest,SITE))
        translations=json.loads((ROOT/'data/translations.zh-CN.json').read_text())
        for row in self.rows:
            english,chinese=resource_path(row),zh_resource_path(row)
            folder=self.dest/chinese.lstrip('/')
            with self.subTest(row['id']):
                self.assertEqual((folder/'index.html').is_file(),eligible(row))
                if not eligible(row):continue
                self.assertTrue((folder/'index.md').is_file())
                self.assertIn(SITE+chinese,urls)
                for path in (english,chinese):
                    head=(self.dest/path.lstrip('/')/'index.html').read_text().split('</head>',1)[0]
                    self.assertIn(f'hreflang="en" href="{SITE}{english}"',head)
                    self.assertIn(f'hreflang="zh-CN" href="{SITE}{chinese}"',head)
                    self.assertIn(f'hreflang="x-default" href="{SITE}{english}"',head)
                text=(folder/'index.html').read_text()
                self.assertIn('<html lang="zh-CN"',text)
                if row['id'] in translations:self.assertIn(html.escape(translations[row['id']]['summary'],quote=True),text)

    def test_home_pages_declare_the_site_search(self):
        for path in ('index.html','zh/index.html'):
            graph=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',(self.dest/path).read_text(),re.S).group(1))['@graph']
            website=next(item for item in graph if item['@type']=='WebSite')
            action=website['potentialAction']
            self.assertEqual(action['@type'],'SearchAction',path)
            self.assertEqual(action['target']['urlTemplate'],SITE+'/explore/?q={search_term_string}#catalog')
            self.assertEqual(action['query-input'],'required name=search_term_string')
            self.assertIn('Organization',{item['@type'] for item in graph})

    def test_chinese_navigation_opens_the_chinese_catalog(self):
        text=(self.dest/'zh/index.html').read_text()
        self.assertIn('href="/zh/catalog/"',text)
        self.assertTrue((self.dest/'zh/catalog/index.html').is_file())

    def test_chinese_directory_pages_are_in_the_categories_sitemap_with_english_pairs(self):
        listed=(self.dest/'sitemap-categories.xml').read_text()
        other=(self.dest/'sitemap-pages.xml').read_text()
        for english,chinese in (('/catalog/','/zh/catalog/'),('/categories/benchmark/','/zh/categories/benchmark/')):
            self.assertIn(f'<loc>{SITE}{chinese}</loc>',listed)
            self.assertNotIn(f'<loc>{SITE}{chinese}</loc>',other)
            self.assertNotIn(f'{SITE}{chinese}"',other)
            for path in (english,chinese):
                text=(self.dest/path.strip('/')/'index.html').read_text()
                self.assertIn(f'hreflang="en" href="{SITE}{english}"',text)
                self.assertIn(f'hreflang="zh-CN" href="{SITE}{chinese}"',text)
                self.assertIn(f'hreflang="x-default" href="{SITE}{english}"',text)
        self.assertNotIn(f'{SITE}/zh/categories/paper/',listed)

    def test_directory_pages_describe_themselves_for_search_in_both_languages(self):
        for path in ('catalog','zh/catalog','categories/benchmark','zh/categories/benchmark','categories/tool','zh/categories/tool'):
            text=(self.dest/path/'index.html').read_text()
            description=html.unescape(re.search(r'<meta name="description" content="([^"]*)"',text).group(1))
            self.assertTrue(70<=len(description)<=160,(path,len(description)))
            graph=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',text,re.S).group(1))['@graph']
            types={item['@type'] for item in graph}
            self.assertIn('CollectionPage',types,path)
            self.assertIn('BreadcrumbList',types,path)
            if 'categories' in path:self.assertIn('ItemList',types,path)

    def test_category_pages_keep_every_row_in_the_html_in_mention_order(self):
        view=home_page.catalog_view(self.rows,[row for row in self.rows if eligible(row)],json.loads((ROOT/'data/coverage.json').read_text()),ROOT)
        for kind in {row['kind'] for row in self.rows if eligible(row)}-{'paper'}:
            selected=[row for row in self.rows if eligible(row) and row['kind']==kind]
            expected=[row['name'] for row in sorted(selected,key=lambda row:(-len(view['mentions'].get(row['id'],())),row['name'].casefold()))]
            for lang in ('en','zh'):
                pages=self.category_pages(kind,lang)
                names,ids=[],[]
                for path in pages:
                    text,rows=self.category_rows(path)
                    names+=[html.unescape(name) for name in rows]
                    ids+=re.findall(r'<li class="row" id="([^"]+)"',text)
                    self.assertIn('hreflang="zh-CN"',text)
                # Featured rows repeat above the full list; the list itself remains in mention order across pages.
                self.assertEqual(names[-len(expected):],expected,(kind,lang))
                self.assertEqual(len(ids),len(set(ids)),(kind,lang))

    def test_category_pages_open_with_a_definition_a_comparison_table_and_questions(self):
        import category_guides
        for kind in {row['kind'] for row in self.rows if eligible(row)}-{'paper'}:
            count=sum(eligible(row) and row['kind']==kind for row in self.rows)
            for lang in ('en','zh'):
                pages=self.category_pages(kind,lang)
                text=(self.dest/pages[0]).read_text()
                intro=html.unescape(re.sub(r'<[^>]+>','',re.search(r'<p class="list-intro">(.*?)</p>',text,re.S).group(1)))
                self.assertTrue(intro.startswith(category_guides.definition(kind,lang=='zh')),(kind,lang))
                if lang=='en':self.assertLessEqual(len(intro.split()),60,kind)
                guide=text.index('<section class="wrap cat-guide"')
                self.assertLess(text.index('<p class="list-intro">'),guide)
                self.assertLess(guide,text.index('data-list-rows'))
                table=re.search(r'<div class="choose"><table>(.*?)</table>',text,re.S).group(1)
                self.assertEqual(table.count('<th scope="row">'),min(category_guides.ROWS,count),(kind,lang))
                graph=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',text,re.S).group(1))['@graph']
                faq=[item for item in graph if item['@type']=='FAQPage']
                self.assertEqual(len(faq),1,(kind,lang))
                questions=faq[0]['mainEntity']
                self.assertTrue(3<=len(questions)<=5,(kind,lang,len(questions)))
                visible=html.unescape(re.sub(r'<[^>]+>','',text[guide:text.index('data-list-rows')]))
                for question in questions:
                    self.assertIn(question['name'],visible)
                    self.assertIn(question['acceptedAnswer']['text'],visible)
                for later in pages[1:]:
                    self.assertNotIn('FAQPage',(self.dest/later).read_text())
                    self.assertNotIn('cat-guide',(self.dest/later).read_text())
                markdown=(self.dest/pages[0].replace('index.html','index.md')).read_text()
                self.assertIn(category_guides.definition(kind,lang=='zh'),markdown)
                for question in questions:self.assertIn('### '+question['name'],markdown)

    def test_benchmarks_feature_websitebench_then_clawbench_above_the_full_list(self):
        for path,heading in (('categories/benchmark/index.html','Featured'),('zh/categories/benchmark/index.html','精选')):
            text,names=self.category_rows(path)
            self.assertLess(text.index(f'>{heading}</h2>'),text.index('data-list-rows'))
            self.assertEqual(names[:2],['WebsiteBench','ClawBench'])
            self.assertIn('data-list-filter',text)
            self.assertIn('class="list-tools js-only"',text)
            self.assertRegex(text,r'<script type="module" src="/listing\.js\?v=[0-9a-f]+"></script>')

    def test_only_the_homepage_hides_the_header_search(self):
        for path in ('index.html','zh/index.html'):
            self.assertIn('<body class="home">',(self.dest/path).read_text())
        for path in ('data/index.html','zh/data/index.html'):
            self.assertIn('<body class="home list-page">',(self.dest/path).read_text())
        css=(self.dest/'assets/site.css').read_text()
        self.assertIn('.home.list-page .search-trigger{opacity:1;pointer-events:auto;transform:none}',css)
    def test_homepage_is_useful_without_javascript(self):
        text=(self.dest/'index.html').read_text();p=PageParser(text)
        self.assertIn('/papers/',p.links);self.assertIn('/catalog/',p.links);self.assertIn('/data/',p.links)
        reviewed=[row for row in self.rows if eligible(row)]
        self.assertIn(f'<b>{len(reviewed):,}</b>',text)
        explorer=(self.dest/'explore/index.html').read_text()
        self.assertIn(f'id="stat-curated">{len(reviewed):,}</span>',explorer)
        self.assertNotIn('id="stat-resources"',explorer)
        for identity in ('stat-pending','stat-candidates','stat-sources'):self.assertRegex(explorer,f'id="{identity}">[0-9][0-9,]*</span>')
        self.assertIn('Computer-use agent research and resources',text)
    def test_bilingual_libraries_preserve_the_complete_reviewed_paper_set(self):
        expected={row['id'] for row in self.rows if eligible(row) and row['kind'] in {'paper','survey'}}
        for prefix in ['/papers/','/zh/papers/']:
            ids=[]
            for path in [item['path'] for item in self.manifest['pages'] if item['path'].startswith(prefix)]:
                markup=(self.dest/path.lstrip('/')/'index.html').read_text()
                page_ids=[html.unescape(value) for value in re.findall(r'data-resource-id="([^"]+)"',markup)]
                schema=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',markup,re.S)[1])
                collection=next(item for item in schema['@graph'] if item['@type']=='ItemList')
                self.assertEqual(collection['numberOfItems'],len(page_ids),path)
                self.assertEqual([item['url'] for item in collection['itemListElement']],
                                 [SITE+('/zh' if prefix=='/zh/papers/' else '')+resource_path({'id':rid}) for rid in page_ids],path)
                self.assertIn('href="/downloads/citations.bib"',markup)
                self.assertIn('href="/downloads/citations.csl.json"',markup)
                ids+=page_ids
            self.assertEqual(set(ids),expected,prefix)
            self.assertEqual(len(ids),len(expected),prefix)
    def test_topic_pages_exports_and_bilingual_structured_data_share_exact_membership(self):
        manifest=json.loads((self.dest/'downloads/topics.json').read_text())
        expected_topics={topic for row in self.rows if eligible(row) for topic in row['topics']}
        self.assertEqual({item['id'] for item in manifest['topics']},expected_topics)
        self.assertEqual(manifest['catalog_sha256'],hashlib.sha256((ROOT/'data/catalog.jsonl').read_bytes()).hexdigest())
        for item in manifest['topics']:
            expected={row['id']:row for row in self.rows if eligible(row) and item['id'] in row['topics']}
            self.assertEqual(set(item['resource_ids']),set(expected))
            for export in item['exports']:
                content=(self.dest/export['url'].lstrip('/')).read_bytes()
                self.assertEqual(hashlib.sha256(content).hexdigest(),export['sha256'])
                if export['url'].endswith('records.jsonl'):
                    self.assertEqual({r['id']:r for r in map(json.loads,content.splitlines())},expected)
            for language,first in item['pages'].items():
                ids=[]
                for path in [p['path'] for p in self.manifest['pages'] if re.fullmatch(re.escape(first)+r'(?:page/\d+/)?',p['path'])]:
                    markup=(self.dest/path.lstrip('/')/'index.html').read_text()
                    page_ids=[html.unescape(value) for value in re.findall(r'data-resource-id="([^"]+)"',markup)]
                    graph=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',markup,re.S)[1])['@graph']
                    listing=next(entity for entity in graph if entity['@type']=='ItemList')
                    self.assertEqual([entry['url'] for entry in listing['itemListElement']],
                                     [SITE+(zh_resource_path(expected[rid]) if language=='zh' else resource_path(expected[rid])) for rid in page_ids],path)
                    self.assertEqual(listing['numberOfItems'],len(page_ids),path)
                    ids+=page_ids
                self.assertEqual(set(ids),set(expected),first)
                self.assertEqual(len(ids),len(expected),first)
                self.assertTrue((self.dest/first.lstrip('/')/'index.md').exists())
    def test_script_versions_match_output_bytes_and_final_page_manifest(self):
        pages={item['path']:item for item in self.manifest['pages']}
        for path,script in [('/explore/', 'app.js'),('/compare/benchmarks/','compare.js'),('/compare/datasets/','compare.js'),
                            ('/data/','downloads.js'),('/zh/data/','downloads.js')]:
            content=(self.dest/path.lstrip('/')/'index.html').read_bytes()
            # Every page also loads the shared shell script, which carries its own version.
            sources=[source for source in PageParser(content.decode('utf-8')).scripts if not source.startswith('/assets/site.js')]
            self.assertEqual(len(sources),1,path)
            url=urllib.parse.urlsplit(sources[0])
            self.assertEqual(Path(url.path).name,script)
            self.assertEqual(urllib.parse.parse_qs(url.query),{'v':[hashlib.sha256((self.dest/script).read_bytes()).hexdigest()]})
            self.assertEqual(pages[path]['sha256'],hashlib.sha256(content).hexdigest())
        for script in ('app.js','compare.js'):
            imports=re.findall(r'''\bfrom\s+['"]([^'"]+)['"]''',(self.dest/script).read_text())
            core=[urllib.parse.urlsplit(url) for url in imports if urllib.parse.urlsplit(url).path=='./catalog-core.js']
            self.assertEqual(len(core),1,script)
            self.assertEqual(urllib.parse.parse_qs(core[0].query),{'v':[hashlib.sha256((self.dest/'catalog-core.js').read_bytes()).hexdigest()]})
    def test_data_hub_pages_have_complete_downloads_and_reciprocal_language_links(self):
        download_manifest=json.loads((self.dest/'downloads/manifest.json').read_text())
        pages={item['path']:item for item in self.manifest['pages']}
        expected_alternates={'en':SITE+'/data/','zh-CN':SITE+'/zh/data/','x-default':SITE+'/data/'}
        for path,language in [('/data/','en'),('/zh/data/','zh-CN')]:
            with self.subTest(path=path):
                content=(self.dest/path.lstrip('/')/'index.html').read_bytes()
                markup=content.decode();parsed=PageParser(markup)
                self.assertEqual(parsed.language,language)
                self.assertEqual(parsed.canonical,[SITE+path])
                self.assertEqual(parsed.alternates,expected_alternates)
                self.assertIn('/zh/data/' if language=='en' else '/data/',parsed.links)
                self.assertIn('/downloads/manifest.json',parsed.links)
                self.assertEqual(pages[path]['sha256'],hashlib.sha256(content).hexdigest())
                self.assertTrue(pages[path]['indexable'])
                self.assertEqual(set(re.findall(r'data-artifact-id="([^"]+)"',markup)),
                                 {item['id'] for item in download_manifest['artifacts']})
                for item in download_manifest['artifacts']:
                    self.assertIn(item['path'],parsed.links)
                    self.assertTrue((self.dest/item['path'].lstrip('/')).is_file())
                    self.assertIn(item['sha256'],markup)
                for link in parsed.links:
                    url=urllib.parse.urlsplit(urllib.parse.urljoin(SITE+path,link))
                    if url.netloc!=urllib.parse.urlsplit(SITE).netloc:continue
                    target=self.dest/url.path.lstrip('/')
                    if url.path.endswith('/'):target=target/'index.html'
                    self.assertTrue(target.exists(),f'{path} -> {link}')
                graph=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',markup,re.S)[1])['@graph']
                dataset=next(item for item in graph if item['@type']=='Dataset')
                self.assertEqual(dataset['url'],SITE+path)
                self.assertEqual({item['contentUrl'] for item in dataset['distribution']},
                                 {SITE+'/downloads/catalog.jsonl',SITE+'/data/records.json',SITE+'/downloads/catalog.sqlite'})
        self.assertIn('href="/zh/data/" aria-current=page>数据</a>',(self.dest/'zh/data/index.html').read_text())
        self.assertIn(SITE+'/downloads/manifest.json',(self.dest/'llms.txt').read_text())

    @code_only
    def test_download_script_change_versions_only_data_hub_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source';source.mkdir()
            for name in ('web','data','schemas'):shutil.copytree(ROOT/name,source/name)
            for name in ('LICENSE','AGENTS.md'):shutil.copy2(ROOT/name,source/name)
            copy_survey_source_inputs(source)
            destination=Path(directory)/'site'
            def snapshot():
                return {item['path']:item['sha256'] for item in
                        json.loads((destination/'data/search-manifest.json').read_text())['pages']}
            with mock.patch('build_site.ROOT',source):
                build_site(destination);before=snapshot()
                script=source/'web/downloads.js'
                script.write_bytes(script.read_bytes()+b'\n// Clipboard dependency version fixture.\n')
                build_site(destination);after=snapshot()
                self.assertEqual({path for path in before if before[path]!=after[path]}, {'/data/','/zh/data/'})
                expected=hashlib.sha256((destination/'downloads.js').read_bytes()).hexdigest()
                for path in ('data/index.html','zh/data/index.html'):
                    parsed=PageParser((destination/path).read_text())
                    self.assertEqual([source for source in parsed.scripts if not source.startswith('/assets/site.js')],['/downloads.js?v='+expected])
                build_site(destination)
                self.assertEqual(snapshot(),after)
    @code_only
    def test_core_change_updates_only_consumer_pages_and_rebuild_is_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source';source.mkdir()
            shutil.copytree(ROOT/'web',source/'web');shutil.copytree(ROOT/'data',source/'data')
            shutil.copytree(ROOT/'schemas',source/'schemas')
            shutil.copy2(ROOT/'LICENSE',source/'LICENSE');shutil.copy2(ROOT/'AGENTS.md',source/'AGENTS.md')
            copy_survey_source_inputs(source)
            destination=Path(directory)/'site'
            def snapshot():
                manifest=json.loads((destination/'data/search-manifest.json').read_text())
                return {item['path']:item['sha256'] for item in manifest['pages']}
            with mock.patch('build_site.ROOT',source):
                build_site(destination);before=snapshot()
                original_app=(destination/'app.js').read_bytes()
                core=source/'web/catalog-core.js';core.write_bytes(core.read_bytes()+b'\n// Dependency version regression fixture.\n')
                build_site(destination);after=snapshot()
                self.assertNotEqual((destination/'app.js').read_bytes(),original_app)
                self.assertEqual({path for path in before if before[path]!=after[path]},{'/explore/','/compare/benchmarks/','/compare/datasets/'})
                scripts={name:(destination/name).read_bytes() for name in ('app.js','compare.js')}
                build_site(destination)
                self.assertEqual(snapshot(),after)
                self.assertEqual({name:(destination/name).read_bytes() for name in scripts},scripts)
    def test_machine_navigation_and_verified_files_exist(self):
        config=json.loads((ROOT/'data/site-discovery.json').read_text())
        self.assertEqual((self.dest/(config['indexnow_key']+'.txt')).read_text(),config['indexnow_key'])
        self.assertEqual((self.dest/'CNAME').read_text(),urllib.parse.urlsplit(SITE).hostname+'\n')
        self.assertEqual((self.dest/config['google_verification_file']).read_bytes(),(ROOT/'web'/config['google_verification_file']).read_bytes())
        self.assertIn('/papers/',(self.dest/'llms.txt').read_text())
        ET.parse(self.dest/'feed.xml')
        robots=urllib.robotparser.RobotFileParser();robots.parse((self.dest/'robots.txt').read_text().splitlines())
        for bot in ['Googlebot','bingbot','OAI-SearchBot','PerplexityBot','Claude-SearchBot']:
            self.assertTrue(robots.can_fetch(bot,SITE+'/papers/'))
    def test_agent_guides_and_rag_downloads_share_the_actual_catalog(self):
        command='git clone https://github.com/reacher-z/Awesome-CUA.git'
        for path in ['explore/index.html','agents/index.html','zh/agents/index.html','data/index.html','AGENTS.md','llms.txt']:
            self.assertIn(command,(self.dest/path).read_text(),path)
        manifest=json.loads((self.dest/'downloads/rag-manifest.json').read_text())
        self.assertEqual(manifest['catalog_sha256'],hashlib.sha256((self.dest/'downloads/catalog.jsonl').read_bytes()).hexdigest())
        for item in manifest['exports']:
            raw=(self.dest/'downloads'/item['file']).read_bytes()
            docs=[json.loads(line) for line in raw.splitlines()]
            self.assertEqual(hashlib.sha256(raw).hexdigest(),item['sha256'])
            expected={row['id']:row for row in self.rows if item['includes_metadata_only'] or row['review_status']=='curated'}
            self.assertEqual(len(docs),len(expected));self.assertEqual(item['records'],len(docs))
            for doc in docs:
                row=expected[doc['id']];self.assertEqual(doc['metadata']['details'],row['details'])
                self.assertEqual(doc['metadata']['review_status'],row['review_status'])
                self.assertEqual(doc['metadata']['citation_url'],SITE+resource_path(row))
        index=json.loads((self.dest/'data/index.json').read_text())
        expected={row['id']:row for row in self.rows}
        for row in index['records']:
            snapshot=expected[row['id']]['details'].get('arxiv_snapshot',{})
            self.assertEqual(row['paper_version'],snapshot.get('version'))
            self.assertEqual(row['paper_source_url'],snapshot.get('versioned_url'))
    def test_full_exports_and_pages_preserve_paper_snapshots(self):
        expected={row['id']:row for row in self.rows}
        exports=[json.loads((self.dest/'data/records.json').read_text()),
                 [json.loads(line) for line in (self.dest/'downloads/catalog.jsonl').read_text().splitlines()]]
        with closing(sqlite3.connect((self.dest/'downloads/catalog.sqlite').as_uri()+'?mode=ro',uri=True)) as database:
            exports.append([json.loads(row[0]) for row in database.execute('SELECT record_json FROM resources')])
        for rows in exports:
            self.assertEqual(len(rows),len(expected))
            self.assertEqual({row['id']:row for row in rows},expected)
        index=json.loads((self.dest/'data/index.json').read_text())['records']
        self.assertEqual(len(index),len(expected))
        self.assertEqual({r['id']:r['review_status'] for r in index},
                         {rid:r['review_status'] for rid,r in expected.items()})
        archive=[json.loads(line) for line in (self.dest/'downloads/arxiv-archive.jsonl').read_text().splitlines()]
        self.assertEqual(archive,[json.loads(line) for line in (ROOT/'data/papers.jsonl').read_text().splitlines()])
        archived={row['id']:row for row in archive}
        for item in self.manifest['pages']:
            body=(self.dest/item['path'].lstrip('/')/'index.html').read_bytes()
            self.assertEqual(item['sha256'],hashlib.sha256(body).hexdigest(),item['path'])
        for rid,row in expected.items():
            if not rid.startswith('arxiv:'):continue
            snapshot=row['details'].get('arxiv_snapshot')
            self.assertEqual(snapshot,archived[rid]['details'].get('arxiv_snapshot'),rid)
            if snapshot is None:continue
            target=self.dest/resource_path(row).lstrip('/')
            markup=(target/'index.html').read_text();markdown=(target/'index.md').read_text()
            for field in ['versioned_url','updated_at','abstract_sha256']:
                if snapshot.get(field) is not None:
                    self.assertIn(html.escape(str(snapshot[field]),quote=True),markup,(rid,field))
            for field in ['versioned_url','submitted_at','updated_at','abstract_sha256','abstract_hash_method']:
                if snapshot.get(field) is not None:self.assertIn(str(snapshot[field]),markdown,(rid,field))
            self.assertIn('- Version: '+(str(snapshot['version']) if snapshot.get('version') else 'not recorded'),markdown,rid)
        # Full annotations of reviewed papers sit in the research-library Markdown, other kinds in their category Markdown.
        snapshots=lambda kinds:sum(eligible(row) and row['kind'] in kinds and bool(row['details'].get('arxiv_snapshot')) for row in self.rows)
        library=sum(path.read_text().count('### Recorded arXiv snapshot') for path in [self.dest/'papers/index.md',*(self.dest/'papers/page').glob('*/index.md')])
        self.assertEqual(library,snapshots({'paper','survey'}))
        others={kind for kind in {row['kind'] for row in self.rows}}-{'paper','survey'}
        self.assertEqual(sum((self.dest/'categories'/kind/'index.md').read_text().count('### Recorded arXiv snapshot') for kind in others),snapshots(others))
    def test_resource_schema_uses_original_authorship_not_catalog_authorship(self):
        for r in self.rows:
            schema=resource_schema(r)
            self.assertEqual(schema['sameAs'],r['url'])
            if r['authors']:self.assertEqual([a['name'] for a in schema['author']],r['authors'])
            if schema['@type']=='Dataset':self.assertGreaterEqual(len(schema['description']),50)
    def test_reviewed_relationships_are_navigable_in_both_directions(self):
        incoming=incoming_relations(self.rows)
        paper=next(r for r in self.rows if r['id']=='arxiv:2508.09123')
        assets={r['source_id'] for r in incoming[paper['id']]}
        self.assertIn('github:xlang-ai/opencua',assets)
        self.assertTrue(any(r['name']=='AgentNet' and r['id'] in assets for r in self.rows))
        text=(self.dest/resource_path(paper).lstrip('/')/'index.html').read_text()
        self.assertIn('Connected assets',text);self.assertIn('AgentNet',text)
        export=json.loads((self.dest/'downloads/relationships.json').read_text())
        self.assertEqual(export['relation_count'],sum(len(r['relations']) for r in self.rows))
        self.assertTrue(any(e['type']=='documented_by' for e in export['relations']))
        self.assertNotIn('mentions',{e['type'] for e in export['relations']})
    def test_jsonld_and_titles_escape_untrusted_text(self):
        text=page('</script><script>alert(1)</script>','x','/test/','<h1>Test</h1>',{'@type':'CreativeWork','name':'</script><script>alert(1)</script>'})
        blocks=re.findall(r'<script type="application/ld\+json">(.*?)</script>',text,re.S)
        self.assertEqual(len(blocks),1);json.loads(blocks[0])
        self.assertNotIn('<script>alert(1)</script>',text)

    def test_scope_exclusions_keep_traceable_nonindexed_pages_and_archive(self):
        report=json.loads((self.dest/'downloads/exclusions.json').read_text())
        active={row['id'] for row in self.rows}
        archive={json.loads(line)['id'] for line in (self.dest/'downloads/arxiv-archive.jsonl').read_text().splitlines()}
        pages={item['path']:item for item in self.manifest['pages']}
        excluded=[row for row in report['decisions'] if row['status']=='excluded']
        self.assertEqual(len(excluded),report['excluded_records'])
        for row in excluded:
            self.assertNotIn(row['id'],active)
            self.assertIn(row['id'],archive)
            path=resource_path(row);item=pages[path]
            self.assertFalse(item['indexable']);self.assertTrue(item['scope_excluded'])
            content=(self.dest/path.lstrip('/')/'index.html').read_text()
            parsed=PageParser(content)
            self.assertIn('noindex',parsed.robots[0]);self.assertIn(row['url'],parsed.links)
            self.assertIn(html.escape(row['reason'],quote=True),content)
            markdown=(self.dest/path.lstrip('/')/'index.md').read_text()
            self.assertIn('excluded from the active CUA catalog',markdown)
            self.assertTrue(markdown.endswith('\n'))
            self.assertFalse(markdown.endswith('\n\n'))
        self.assertEqual(self.manifest['excluded_pages'],len(excluded))
        self.assertEqual(self.manifest['metadata_only_pages'],sum(row['review_status']=='metadata_verified' for row in self.rows))


if __name__=='__main__':unittest.main()
