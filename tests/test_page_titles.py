from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_site import build_site
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
        for title,expected in [('About AwesomeCUA and editorial policy','About AwesomeCUA and editorial policy'),
                               ('Awesome CUA — Papers and tools','Awesome CUA — Papers and tools'),
                               ('Awesome Computer-Use Agents','Awesome Computer-Use Agents'),
                               ('Manus (product)','Manus (product) | AwesomeCUA')]:
            parsed=TitleParser(page(title,'x','/test/','<h1>Test</h1>'))
            self.assertEqual((parsed.title,parsed.og),(expected,expected))


class GeneratedTitleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.dest=build_site(cls.temp.name)
        cls.pages=json.loads((cls.dest/'data/search-manifest.json').read_text())['pages']
        cls.titles={item['path']:TitleParser((cls.dest/item['path'].lstrip('/')/'index.html').read_text()) for item in cls.pages}
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_indexable_pages_have_unique_titles(self):
        counts=Counter(self.titles[item['path']].title for item in self.pages if item['indexable'])
        self.assertEqual([title for title,n in counts.items() if n>1],[])
    def test_titles_name_the_brand_once(self):
        # Keep the expected aliases independent of the renderer's identity constants.
        names=('Awesome CUA','AwesomeCUA','Awesome Computer-Use Agents')
        for path,parsed in self.titles.items():
            self.assertEqual(sum(parsed.title.count(name) for name in names),1,path)
            if path!='/':self.assertEqual(parsed.og,parsed.title,path)


class GeneratedTitleAssertionTests(unittest.TestCase):
    def check_title(self,path,parsed):
        # Exercise the generated-page assertion without its full-site build fixture.
        case=GeneratedTitleTests('test_titles_name_the_brand_once')
        case.titles={path:parsed}
        case.test_titles_name_the_brand_once()

    def test_supported_aliases_on_home_and_non_home_routes(self):
        for path in ('/','/zh/','/guides/catalog-identity/','/zh/guides/catalog-identity/'):
            for title in ('Awesome CUA — Papers and tools',
                          'About AwesomeCUA and editorial policy',
                          'Awesome Computer-Use Agents'):
                with self.subTest(path=path,title=title):
                    parsed=TitleParser(page(title,'x',path,'<h1>Test</h1>',
                                            lang='zh-CN' if path.startswith('/zh/') else 'en'))
                    self.assertEqual((parsed.title,parsed.og),(title,title))
                    self.check_title(path,parsed)

    def test_repeated_and_mixed_brands_are_rejected(self):
        names=('Awesome CUA','AwesomeCUA','Awesome Computer-Use Agents')
        for path in ('/','/zh/','/guides/catalog-identity/','/zh/guides/catalog-identity/'):
            for first in names:
                for second in names:
                    title=f'{first} | {second}'
                    with self.subTest(path=path,title=title):
                        parsed=TitleParser(f'<title>{title}</title><meta property="og:title" content="{title}">')
                        with self.assertRaises(AssertionError):
                            self.check_title(path,parsed)

    def test_missing_brand_is_rejected(self):
        for path in ('/','/zh/','/guides/catalog-identity/','/zh/guides/catalog-identity/'):
            for title in ('Papers and tools',''):
                with self.subTest(path=path,title=title):
                    parsed=TitleParser(f'<title>{title}</title><meta property="og:title" content="{title}">')
                    with self.assertRaises(AssertionError):
                        self.check_title(path,parsed)

    def test_non_root_og_title_must_match(self):
        for path in ('/zh/','/guides/catalog-identity/','/zh/guides/catalog-identity/'):
            for og in ('','<meta property="og:title" content="A different title">'):
                with self.subTest(path=path,og=og):
                    parsed=TitleParser(f'<title>Awesome CUA — Papers and tools</title>{og}')
                    with self.assertRaises(AssertionError):
                        self.check_title(path,parsed)


if __name__=='__main__':unittest.main()
