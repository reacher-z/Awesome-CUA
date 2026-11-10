from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_site import build_site
from site_fixture import shared_site
from search_pages import page, resource_path
from test_search_pages import page_origin


class TrailParser(HTMLParser):
    def __init__(self,text):
        super().__init__();self.navs=0;self.inside=False;self.items=[];self.link=None
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='nav' and a.get('aria-label')=='Breadcrumb':self.navs+=1;self.inside=True
        if self.inside and tag=='a':self.link=[a['href'],'',a.get('aria-current')]
    def handle_endtag(self,tag):
        if tag=='nav':self.inside=False
        if tag=='a' and self.link:self.items.append(tuple(self.link));self.link=None
    def handle_data(self,data):
        if self.link:self.link[1]+=data


def structured_trail(text):
    lists=[node for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>',text,re.S) for node in json.loads(block).get('@graph',[]) if node.get('@type')=='BreadcrumbList']
    return [[(item['position'],item['name'],item['item']) for item in found['itemListElement']] for found in lists]


class BreadcrumbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.dest=shared_site()
        cls.pages=[item['path'] for item in json.loads((cls.dest/'data/search-manifest.json').read_text())['pages'] if item['path']!='/']
        cls.rows=[json.loads(x) for x in (Path(__file__).resolve().parents[1]/'data/catalog.jsonl').read_text().splitlines() if x.strip()]
        cls.trails={}
        for path in cls.pages:
            text=(cls.dest/path.lstrip('/')/'index.html').read_text()
            cls.trails[path]=(TrailParser(text),structured_trail(text))
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def trail(self,path):return [(href,name) for href,name,_ in self.trails[path][0].items]
    def test_visible_trail_matches_breadcrumb_list_on_every_page(self):
        for path in self.pages:
            visible,structured=self.trails[path]
            with self.subTest(path=path):
                self.assertEqual(visible.navs,1);self.assertEqual(len(structured),1)
                self.assertEqual([(i+1,name,page_origin(self.dest,path)+href) for i,(href,name,_) in enumerate(visible.items)],structured[0])
    def test_only_the_last_item_is_the_current_page(self):
        for path in self.pages:
            items=self.trails[path][0].items
            with self.subTest(path=path):
                self.assertGreaterEqual(len(items),2);self.assertEqual(items[-1][0],path);self.assertEqual(items[-1][2],'page')
                for href,_,current in items[:-1]:self.assertNotEqual(href,path);self.assertIsNone(current)
    def test_trails_follow_the_site_hierarchy(self):
        for r in self.rows:
            self.assertEqual(self.trail(resource_path(r)),[('/','AwesomeCUA'),('/catalog/','Catalog'),(f'/categories/{r["kind"]}/',self.trail(f'/categories/{r["kind"]}/')[-1][1]),(resource_path(r),r['name'])])
        guides=[path for path in self.pages if path.startswith('/guides/') and path!='/guides/']
        self.assertTrue(guides)
        for path in guides:self.assertEqual(self.trail(path)[:2],[('/','AwesomeCUA'),('/guides/','Guides')])
        self.assertEqual(self.trail('/categories/benchmark/'),[('/','AwesomeCUA'),('/catalog/','Catalog'),('/categories/benchmark/','Benchmarks')])
        self.assertEqual(self.trail('/compare/datasets/')[:2],[('/','AwesomeCUA'),('/catalog/','Catalog')])
        self.assertEqual(self.trail('/catalog/'),[('/','AwesomeCUA'),('/catalog/','Catalog')])
        self.assertEqual(self.trail('/about/')[0],('/','AwesomeCUA'));self.assertEqual(len(self.trail('/about/')),2)
        zh_topic=next(path for path in self.pages if path.startswith('/zh/topics/') and path!='/zh/topics/')
        self.assertEqual(self.trail(zh_topic)[:2],[('/zh/','AwesomeCUA'),('/zh/topics/','主题')])
        self.assertEqual(self.trail('/zh/papers/')[0],('/zh/','AwesomeCUA'));self.assertEqual(self.trail('/zh/')[0],('/','AwesomeCUA'))
    def test_trail_text_is_escaped(self):
        text=page('<b>x</b>','x','/test/','<h1>Test</h1>',crumbs=[('AwesomeCUA','/'),('<b>x</b>','/test/')])
        self.assertNotIn('<b>x</b>',text);self.assertEqual(TrailParser(text).items[-1],('/test/','<b>x</b>','page'))


if __name__=='__main__':unittest.main()
