import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_site import build_site
from search_pages import FEED_ENTRIES, SITE, eligible, resource_path, review_feed, reviewed_times

ATOM='{http://www.w3.org/2005/Atom}'
UTC=dt.timezone.utc


def record(identity,name,kind='model',authors=()):
    return {'id':identity,'name':name,'kind':kind,'authors':list(authors),'summary':f'Annotation for {name}.'}


def entries(feed):
    return feed.findall(ATOM+'entry')


class ReviewFeedUnitTests(unittest.TestCase):
    def parse(self,rows,times,snapshot='2026-10-18T08:00:00Z'):
        return ET.fromstring(review_feed(rows,times,snapshot))

    def test_orders_by_review_time_then_name_and_dates_entries_by_review(self):
        rows=[record('github:a/old','Old'),record('github:a/zeta','Zeta'),record('github:a/alpha','Alpha',kind='dataset'),record('github:a/unreviewed','Unreviewed')]
        times={'github:a/old':dt.datetime(2026,10,16,9,0,tzinfo=UTC),'github:a/zeta':dt.datetime(2026,10,18,4,0,tzinfo=UTC),'github:a/alpha':dt.datetime(2026,10,18,4,0,tzinfo=UTC)}
        feed=self.parse(rows,times)
        self.assertEqual([e.find(ATOM+'title').text for e in entries(feed)],['Alpha','Zeta','Old'])
        self.assertEqual(feed.find(ATOM+'updated').text,'2026-10-18T04:00:00Z')
        first=entries(feed)[0]
        self.assertEqual(first.find(ATOM+'published').text,'2026-10-18T04:00:00Z')
        self.assertEqual(first.find(ATOM+'updated').text,'2026-10-18T04:00:00Z')
        self.assertEqual(first.find(ATOM+'category').attrib,{'term':'dataset','label':'Datasets'})
        self.assertEqual(first.find(ATOM+'id').text,SITE+resource_path(rows[2]))

    def test_uses_recorded_authors_capped_and_falls_back_to_the_catalog(self):
        rows=[record('arxiv:2601.00001','Paper',kind='paper',authors=[f'Author {i}' for i in range(14)]),record('github:a/tool','Tool',kind='tool')]
        times={r['id']:dt.datetime(2026,10,17,tzinfo=UTC) for r in rows}
        paper,tool=sorted(entries(self.parse(rows,times)),key=lambda e:e.find(ATOM+'title').text)
        self.assertEqual([a.find(ATOM+'name').text for a in paper.findall(ATOM+'author')],[f'Author {i}' for i in range(10)])
        self.assertEqual([a.find(ATOM+'name').text for a in tool.findall(ATOM+'author')],['AwesomeCUA'])

    def test_keeps_the_newest_entries_and_the_feed_identity(self):
        rows=[record(f'github:a/r{i:03d}',f'R{i:03d}') for i in range(FEED_ENTRIES+10)]
        times={r['id']:dt.datetime(2026,10,1,tzinfo=UTC)+dt.timedelta(minutes=i) for i,r in enumerate(rows)}
        feed=self.parse(rows,times)
        self.assertEqual(len(entries(feed)),FEED_ENTRIES)
        self.assertEqual(entries(feed)[0].find(ATOM+'title').text,f'R{FEED_ENTRIES+9:03d}')
        self.assertEqual(feed.find(ATOM+'id').text,SITE+'/papers/')
        self.assertIn(SITE+'/feed.xml',[l.get('href') for l in feed.findall(ATOM+'link') if l.get('rel')=='self'])

    def test_an_empty_feed_is_dated_by_the_snapshot(self):
        self.assertEqual(self.parse([],{}).find(ATOM+'updated').text,'2026-10-18T08:00:00Z')

    def test_a_checkout_without_editorial_input_has_no_review_times(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(reviewed_times(Path(directory)),{})

    def test_review_times_are_normalized_to_utc(self):
        times=reviewed_times(ROOT)
        self.assertTrue(times)
        self.assertTrue(all(t.tzinfo is not None and t.utcoffset()==dt.timedelta(0) for t in times.values()))


class BuiltFeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.dest=build_site(cls.temp.name)
        cls.feed=ET.parse(cls.dest/'feed.xml').getroot()
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_built_feed_lists_newest_reviews_of_every_kind(self):
        self.assertEqual(self.feed.tag,ATOM+'feed')
        items=entries(self.feed)
        self.assertEqual(len(items),FEED_ENTRIES)
        stamps=[e.find(ATOM+'updated').text for e in items]
        for stamp in stamps+[self.feed.find(ATOM+'updated').text]:
            self.assertRegex(stamp,r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
        self.assertEqual(stamps,sorted(stamps,reverse=True))
        self.assertEqual(self.feed.find(ATOM+'updated').text,stamps[0])
        kinds={e.find(ATOM+'category').get('term') for e in items}
        self.assertTrue(kinds-{'paper','survey'},kinds)

    def test_entries_match_the_newest_editorial_approvals(self):
        rows=[json.loads(line) for line in (ROOT/'data/catalog.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        times=reviewed_times(ROOT)
        reviewed=[r for r in rows if eligible(r) and r['id'] in times]
        newest=sorted(reviewed,key=lambda r:times[r['id']],reverse=True)
        cutoff=times[newest[FEED_ENTRIES-1]['id']]
        by_url={SITE+resource_path(r):r for r in reviewed}
        for entry in entries(self.feed):
            r=by_url[entry.find(ATOM+'id').text]
            self.assertGreaterEqual(times[r['id']],cutoff)
            self.assertEqual(entry.find(ATOM+'updated').text,times[r['id']].strftime('%Y-%m-%dT%H:%M:%SZ'))
            self.assertEqual(entry.find(ATOM+'category').get('term'),r['kind'])

    def test_data_hubs_and_readmes_link_the_feed(self):
        for path in ('data/index.html','zh/data/index.html'):
            self.assertIn('<a href="/feed.xml"',(self.dest/path).read_text(encoding='utf-8'),path)
        for name in ('README.md','README.zh-CN.md'):
            self.assertIn('](https://awesomecua.github.io/feed.xml)',(ROOT/name).read_text(encoding='utf-8'),name)
        self.assertRegex((self.dest/'index.html').read_text(encoding='utf-8'),r'<link rel="alternate" type="application/atom\+xml" href="[^"]*/feed\.xml"')


if __name__=='__main__':
    unittest.main()
