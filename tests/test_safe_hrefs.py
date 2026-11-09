import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build import validate_sources
from build_site import build_site
from search_pages import guide_path, resource_path
from specifications import comparison_body, safe_href
from test_search_pages import copy_survey_source_inputs

ROOT=Path(__file__).resolve().parents[1]
ATTACK='javascript:alert(document.domain)'


class SafeHrefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.source=Path(cls.temp.name)/'source';cls.source.mkdir()
        shutil.copytree(ROOT/'web',cls.source/'web');shutil.copytree(ROOT/'data',cls.source/'data');shutil.copytree(ROOT/'schemas',cls.source/'schemas')
        shutil.copy2(ROOT/'LICENSE',cls.source/'LICENSE');shutil.copy2(ROOT/'AGENTS.md',cls.source/'AGENTS.md')
        copy_survey_source_inputs(cls.source)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def assertBuildRejects(self,name,mutate,message):
        path=self.source/'data'/name;original=path.read_text()
        try:
            path.write_text(mutate(original))
            with mock.patch('build_site.ROOT',self.source),self.assertRaises(ValueError) as caught:build_site(Path(self.temp.name)/'site')
            self.assertIn(message,str(caught.exception))
        finally:path.write_text(original)
    def test_only_absolute_web_urls_become_links(self):
        self.assertEqual(safe_href('https://example.org/a?b=1&c="2"'),'https://example.org/a?b=1&amp;c=&quot;2&quot;')
        self.assertEqual(safe_href('http://example.org/'),'http://example.org/')
        for value in [ATTACK,' JavaScript:alert(1)','java\tscript:alert(1)','data:text/html,<script>alert(1)</script>','vbscript:msgbox(1)','//example.org/','/resources/x/','https:example.org','',None]:
            with self.assertRaises(ValueError,msg=repr(value)):safe_href(value)
    def test_script_license_url_fails_the_build(self):
        def mutate(text):
            rows=[json.loads(line) for line in text.splitlines()]
            row=next(r for r in rows if r['kind'] not in {'paper','survey'} and r['licenses']['code'])
            row['licenses']['code']['url']=ATTACK
            return ''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows)
        self.assertBuildRejects('catalog.jsonl',mutate,ATTACK)
    def test_script_dataset_license_url_cannot_reach_the_comparison_table(self):
        rows=[json.loads(line) for line in (ROOT/'data/catalog.jsonl').read_text().splitlines()]
        row=next(r for r in rows if r['kind']=='dataset' and r['details'].get('dataset_profile') and r['licenses']['data'])
        self.assertIn(row['licenses']['data']['url'],comparison_body(rows,'dataset',resource_path))
        row['licenses']['data']={**row['licenses']['data'],'url':ATTACK}
        with self.assertRaises(ValueError):comparison_body(rows,'dataset',resource_path)
    def test_script_source_homepage_and_scan_run_url_fail(self):
        sources=json.loads((ROOT/'data/sources.json').read_text())
        self.assertEqual(validate_sources(sources),[])
        self.assertEqual(validate_sources([{**sources[0],'homepage':ATTACK},{'id':'missing'}]),[sources[0]['id']+': discovery-source homepage must be an https URL','missing: discovery-source homepage must be an https URL'])
        def homepage(text):
            coverage=json.loads(text);coverage['sources'][0]['url']=ATTACK;return json.dumps(coverage)
        self.assertBuildRejects('coverage.json',homepage,ATTACK)
        if (self.source/'data/scan-status.json').exists():
            self.assertBuildRejects('scan-status.json',lambda text:json.dumps({**json.loads(text),'run_url':ATTACK}),ATTACK)
    def test_guide_slugs_cannot_escape_their_directory_or_attribute(self):
        self.assertEqual(guide_path({'slug':'gui-agent-benchmarks'}),'/guides/gui-agent-benchmarks/')
        for slug in ['../../index','a/b','a.b','x"><script>alert(1)</script>','Upper','',None]:
            with self.assertRaises(ValueError,msg=repr(slug)):guide_path({'slug':slug})
        def mutate(text):
            guides=json.loads(text);guides[0]['slug']='../../index';return json.dumps(guides)
        self.assertBuildRejects('site-guides.json',mutate,"Invalid guide slug: '../../index'")


if __name__=='__main__':unittest.main()
