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
        self.assertIn('/',{item['path'] for item in pages});locales={};images={}
        for item in pages:
            target=self.dest/item['path'].lstrip('/')
            if item['path'].endswith('/'):target=target/'index.html'
            head=HeadParser(target.read_text());meta=head.meta;locales[item['path']]=meta.get('og:locale')
            with self.subTest(path=item['path']):
                origin=page_origin(self.dest,item['path'])
                self.assertEqual(len(meta['og:image']),1);self.assertTrue(meta['og:image'][0].startswith(origin+'/'))
                image=self.dest/meta['og:image'][0][len(origin)+1:]
                self.assertTrue(image.is_file(),meta['og:image'])
                if 'twitter:image' in meta:self.assertEqual(meta['twitter:image'],meta['og:image'])
                images[item['path']]=meta['og:image'][0][len(origin):]
                self.assertEqual(meta['twitter:card'],['summary_large_image'])
                self.assertEqual(meta['og:site_name'],['AwesomeCUA'])
                self.assertEqual(meta['og:locale'],['zh_CN' if head.lang=='zh-CN' else 'en_US'])
                self.assertEqual((meta['og:image:width'],meta['og:image:height']),(['1200'],['630']))
                self.assertTrue(meta['og:image:alt'][0])
        self.assertEqual((locales['/'],locales['/zh/']),(['en_US'],['zh_CN']))
        # Home and every collection page have their own card; a Chinese page shares its English twin's card.
        collections=['/','/catalog/','/papers/','/topics/','/data/']+[path for path in images if path.startswith('/categories/') and path.count('/')==3]+[path for path in images if path.startswith('/topics/') and path.count('/')==3]
        self.assertEqual(len({images[path] for path in collections}),len(collections))
        for path in collections:self.assertEqual(images['/zh'+path] if '/zh'+path in images else images[path],images[path])
        rows=[json.loads(line) for line in (Path(__file__).resolve().parents[1]/'data/catalog.jsonl').read_text().splitlines() if line.strip()]
        from search_pages import resource_path
        for row in rows:
            self.assertEqual(images[resource_path(row)],f'/og/resource-{row["kind"]}.png',row['id'])
    def test_cards_are_1200_by_630_pngs(self):
        cards=sorted((self.dest/'og').glob('*.png'))
        self.assertGreater(len(cards),20)
        for card in cards:
            data=card.read_bytes()
            self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n',card.name);self.assertEqual(struct.unpack('>II',data[16:24]),(1200,630),card.name)
            self.assertLess(len(data),300_000,card.name)
    def test_preview_image_is_a_1200_by_630_png(self):
        data=(self.dest/'social.png').read_bytes()
        self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n');self.assertEqual(data[12:16],b'IHDR')
        self.assertEqual(struct.unpack('>II',data[16:24]),(1200,630))
        self.assertLess(len(data),300_000)


if __name__=='__main__':unittest.main()
