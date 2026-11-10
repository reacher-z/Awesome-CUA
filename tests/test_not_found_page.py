from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.parse

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_site import build_site
from site_fixture import shared_site
from search_pages import KINDS, SOURCE_REPO, SITE
from sitemaps import sitemap_urls


class NotFoundParser(HTMLParser):
    def __init__(self,text):
        super().__init__();self.links=[];self.assets=[];self.canonical=[];self.meta={};self.h1=0
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and 'href' in a:self.links.append(a['href'])
        if tag=='link' and a.get('rel')=='canonical':self.canonical.append(a['href'])
        elif tag=='link' and 'href' in a:self.assets.append(a['href'])
        if tag in {'img','script'} and 'src' in a:self.assets.append(a['src'])
        if tag=='meta' and (a.get('name') or a.get('property')):self.meta[a.get('name') or a.get('property')]=a.get('content')
        if tag=='h1':self.h1+=1


class NotFoundPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.dest=shared_site()
        cls.text=(cls.dest/'404.html').read_text();cls.page=NotFoundParser(cls.text)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_uses_site_chrome_and_root_relative_assets_for_any_depth(self):
        self.assertIn('class="site-header"',self.text);self.assertIn('<footer',self.text);self.assertEqual(self.page.h1,1)
        self.assertIn('<title>Page not found | AwesomeCUA</title>',self.text)
        for target in self.page.assets+self.page.links:
            u=urllib.parse.urlsplit(target)
            if not (u.scheme or u.netloc or target.startswith('#')):self.assertTrue(target.startswith('/'),target)
    def test_is_noindex_and_claims_no_url(self):
        self.assertIn('noindex',self.page.meta['robots'])
        self.assertEqual(self.page.canonical,[]);self.assertNotIn('og:url',self.page.meta)
    def test_links_to_search_directory_papers_categories_and_issue_tracker(self):
        links=set(self.page.links)
        for target in ['/explore/#catalog','/catalog/','/papers/',*(f'/categories/{kind}/' for kind in KINDS)]:self.assertIn(target,links)
        self.assertTrue(any(link.startswith(SOURCE_REPO+'/issues') for link in links))
        for link in links:
            u=urllib.parse.urlsplit(link)
            if u.scheme or u.netloc or link.startswith('#'):continue
            target=self.dest/u.path.lstrip('/')
            if u.path.endswith('/'):target=target/'index.html'
            self.assertTrue(target.exists(),link)
    def test_stays_out_of_manifest_and_sitemaps(self):
        manifest=json.loads((self.dest/'data/search-manifest.json').read_text())
        # Page counts, sitemaps and IndexNow submissions all derive from the manifest.
        self.assertNotIn('/404.html',{item['path'] for item in manifest['pages']})
        self.assertNotIn(SITE+'/404.html',sitemap_urls(self.dest,SITE))
        self.assertNotIn(SITE+'/404.html',(self.dest/'sitemap.txt').read_text().splitlines())


if __name__=='__main__':unittest.main()
