from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_site import build_site
from search_pages import clip, paged_summary


class HeadParser(HTMLParser):
    def __init__(self,text):
        super().__init__();self.meta={}
        self.feed(text.split('</head>',1)[0])
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);key=a.get('name') or a.get('property')
        if tag=='meta' and key:self.meta[key]=a.get('content')


class PagedSummaryTests(unittest.TestCase):
    def test_first_page_keeps_its_summary(self):
        self.assertEqual(paged_summary('Browse papers.',1,19),'Browse papers.')
        self.assertEqual(paged_summary('浏览论文。',1,19,'zh'),'浏览论文。')

    def test_later_pages_state_their_position(self):
        self.assertEqual(paged_summary('Browse papers.',2,19),'Browse papers. Page 2 of 19.')
        self.assertEqual(paged_summary('浏览论文。',19,19,'zh'),'浏览论文。第 19/19 页。')

    def test_long_summaries_keep_the_position_within_the_clip(self):
        text=' '.join(['word']*100)
        result=paged_summary(text,3,4)
        self.assertLessEqual(len(result),300)
        self.assertTrue(result.endswith('… Page 3 of 4.'),result)
        self.assertEqual(clip(result),result)


class BuiltDescriptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();dest=build_site(cls.temp.name)
        cls.pages={}
        for file in dest.rglob('index.html'):
            path='/' if file.parent==dest else '/'+file.parent.relative_to(dest).as_posix()+'/'
            cls.pages[path]=HeadParser(file.read_text(encoding='utf-8')).meta
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_indexable_pages_have_unique_descriptions(self):
        shared=defaultdict(list)
        for path,meta in self.pages.items():
            if meta.get('robots','').startswith('index'):shared[meta['description']].append(path)
        duplicates={text:paths for text,paths in shared.items() if len(paths)>1}
        self.assertEqual(duplicates,{})

    def test_paginated_listings_name_their_page(self):
        later=[path for path in self.pages if '/page/' in path]
        self.assertTrue(any(path.startswith('/papers/page/') for path in later))
        self.assertTrue(any(path.startswith('/zh/topics/') for path in later))
        for path in later:
            meta=self.pages[path];number=path.rstrip('/').rsplit('/',1)[1]
            marker=f'第 {number}/' if path.startswith('/zh/') else f'Page {number} of '
            self.assertIn(marker,meta['description'],path)
            self.assertEqual(meta['description'],meta['og:description'],path)


if __name__=='__main__':
    unittest.main()
