from html.parser import HTMLParser
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_site import build_site
from site_fixture import shared_site
from test_search_pages import page_origin


class HeadParser(HTMLParser):
    def __init__(self,text):
        super().__init__();self.lang=None;self.meta={}
        self.feed(text.split('</head>',1)[0])
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='html':self.lang=a.get('lang')
        key=a.get('property') or a.get('name')
        if tag=='meta' and key:self.meta.setdefault(key,[]).append(a.get('content'))


class SocialPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.dest=shared_site()
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_every_page_advertises_a_raster_preview_that_exists(self):
        pages=json.loads((self.dest/'data/search-manifest.json').read_text())['pages']
        self.assertIn('/',{item['path'] for item in pages});locales={}
        for item in pages:
            target=self.dest/item['path'].lstrip('/')
            if item['path'].endswith('/'):target=target/'index.html'
            head=HeadParser(target.read_text());meta=head.meta;locales[item['path']]=meta.get('og:locale')
            with self.subTest(path=item['path']):
                self.assertEqual(meta['og:image'],[page_origin(self.dest,item['path'])+'/social.png'])
                self.assertEqual(meta['twitter:card'],['summary_large_image'])
                self.assertEqual(meta['og:site_name'],['AwesomeCUA'])
                self.assertEqual(meta['og:locale'],['zh_CN' if head.lang=='zh-CN' else 'en_US'])
                self.assertEqual((meta['og:image:width'],meta['og:image:height']),(['1200'],['630']))
                self.assertTrue(meta['og:image:alt'][0])
        self.assertEqual((locales['/'],locales['/zh/']),(['en_US'],['zh_CN']))
    def test_preview_image_is_a_1200_by_630_png(self):
        data=(self.dest/'social.png').read_bytes()
        self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n');self.assertEqual(data[12:16],b'IHDR')
        self.assertEqual(struct.unpack('>II',data[16:24]),(1200,630))
        self.assertLess(len(data),300_000)


if __name__=='__main__':unittest.main()
