from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_site import build_site
from search_pages import SITE


class AlternateParser(HTMLParser):
    def __init__(self,text):
        super().__init__();self.alternates={}
        self.feed(text.split('</head>',1)[0])
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='link' and a.get('rel')=='alternate' and a.get('hreflang'):self.alternates[a['hreflang']]=a['href']


class HreflangAlternateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();dest=build_site(cls.temp.name)
        cls.pages={}
        for file in dest.rglob('index.html'):
            path='/' if file.parent==dest else '/'+file.parent.relative_to(dest).as_posix()+'/'
            cls.pages[path]=AlternateParser(file.read_text(encoding='utf-8')).alternates
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_agent_guides_declare_each_other(self):
        expected={'en':SITE+'/agents/','zh-CN':SITE+'/zh/agents/','x-default':SITE+'/agents/'}
        self.assertEqual(self.pages['/agents/'],expected)
        self.assertEqual(self.pages['/zh/agents/'],expected)

    def test_every_alternate_exists_and_links_back(self):
        declaring=[path for path,alternates in self.pages.items() if alternates]
        self.assertGreater(len(declaring),2)
        for path in declaring:
            alternates=self.pages[path]
            self.assertIn(SITE+path,alternates.values(),f'{path} does not list itself among its alternates')
            for locale,href in alternates.items():
                self.assertTrue(href.startswith(SITE+'/'),href)
                target=href[len(SITE):]
                self.assertIn(target,self.pages,f'{path} declares a missing {locale} alternate {href}')
                self.assertIn(SITE+path,self.pages[target].values(),f'{target} does not link back to {path}')


if __name__=='__main__':
    unittest.main()
