from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_site import build_site
from site_fixture import shared_site
from search_pages import page, resource_titles


class TitleParser(HTMLParser):
    def __init__(self,text):
        super().__init__();self.title='';self.og=None;self.inside=False
        self.feed(text.split('</head>',1)[0])
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);self.inside=tag=='title'
        if tag=='meta' and a.get('property')=='og:title':self.og=a['content']
    def handle_endtag(self,tag):self.inside=False
    def handle_data(self,data):
        if self.inside:self.title+=data


def record(id,name,kind,url,status='curated',scope='core'):
    return {'id':id,'name':name,'kind':kind,'url':url,'review_status':status,'scope':scope}


class ResourceTitleTests(unittest.TestCase):
    def test_shared_names_gain_kind_then_source_address(self):
        rows=[record('organization:manus','Manus','company','https://manus.im/'),
              record('url:1','Manus','product','https://manus.im/app'),
              record('github:deepmind/android_env','AndroidEnv','infrastructure','https://github.com/deepmind/android_env'),
              record('github:google-deepmind/android_env','AndroidEnv','infrastructure','https://www.github.com/google-deepmind/android_env/'),
              record('arxiv:1','Unique','paper','https://arxiv.org/abs/1'),
              record('arxiv:2','Unique','paper','https://arxiv.org/abs/2',status='metadata_verified')]
        self.assertEqual(resource_titles(rows),{'organization:manus':'Manus (publisher)','url:1':'Manus (product)',
            'github:deepmind/android_env':'AndroidEnv (github.com/deepmind/android_env)',
            'github:google-deepmind/android_env':'AndroidEnv (github.com/google-deepmind/android_env)'})
    def test_brand_is_not_repeated(self):
        for title,expected in [('About AwesomeCUA and editorial policy','About AwesomeCUA and editorial policy'),('Manus (product)','Manus (product) | AwesomeCUA')]:
            parsed=TitleParser(page(title,'x','/test/','<h1>Test</h1>'))
            self.assertEqual((parsed.title,parsed.og),(expected,expected))


class GeneratedTitleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.dest=shared_site()
        cls.pages=json.loads((cls.dest/'data/search-manifest.json').read_text())['pages']
        cls.titles={item['path']:TitleParser((cls.dest/item['path'].lstrip('/')/'index.html').read_text()) for item in cls.pages}
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_indexable_pages_have_unique_titles(self):
        counts=Counter(self.titles[item['path']].title for item in self.pages if item['indexable'])
        self.assertEqual([title for title,n in counts.items() if n>1],[])
    def test_titles_fit_sixty_characters(self):
        self.assertEqual([path for path,parsed in self.titles.items() if len(parsed.title)>60],[])
    def test_pages_declare_their_markdown_twin(self):
        for item in self.pages:
            folder=self.dest/item['path'].lstrip('/')
            if not item['path'].endswith('/') or item['path']=='/survey/' or not (folder/'index.md').is_file():continue
            with self.subTest(item['path']):
                self.assertIn(f'<link rel="alternate" type="text/markdown" href="{item["path"]}index.md">',(folder/'index.html').read_text().split('</head>',1)[0])
    def test_titles_name_the_brand_once(self):
        for path,parsed in self.titles.items():
            self.assertEqual(parsed.title.count('AwesomeCUA')+parsed.title.count('Awesome CUA'),1,path)
            if path!='/':self.assertEqual(parsed.og,parsed.title,path)


if __name__=='__main__':unittest.main()
