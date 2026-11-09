import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from specifications import validate_profiles, profile_export, count_text, comparison_body
from search_pages import resource_path, resource_markdown

ROOT=Path(__file__).resolve().parents[1]


def fixture():
    row=next(json.loads(line) for line in (ROOT/'data/catalog.jsonl').read_text().splitlines() if json.loads(line)['id']=='github:xlang-ai/osworld')
    return copy.deepcopy(row)


class SpecificationIntegrityTests(unittest.TestCase):
    def test_count_units_population_and_evidence_are_required(self):
        for missing in ['unit','population','evidence_url']:
            with self.subTest(missing=missing):
                row=fixture();row['details']['benchmark_protocol']['counts'][0].pop(missing)
                self.assertTrue(validate_profiles(row))

    def test_distinct_manifest_populations_are_not_combined(self):
        row=fixture();profile=row['details']['benchmark_protocol'];counts=profile['counts']
        self.assertEqual(validate_profiles(row),[])
        exported=profile_export([row],'benchmark')['records'][0]['profile']['counts']
        self.assertEqual(len(exported),len({c['population'] for c in counts}))
        self.assertIn('test_all.json',{c['population'] for c in exported})
        self.assertIn('test_nogdrive.json',{c['population'] for c in exported})
        row['details']['benchmark_protocol']['counts'].append(copy.deepcopy(counts[0]))
        self.assertTrue(any('duplicate count grain' in e for e in validate_profiles(row)))

    def test_profile_requires_curated_kind_and_all_source_receipts(self):
        for change in ['review','kind','evidence']:
            with self.subTest(change=change):
                row=fixture()
                if change=='review':row['review_status']='metadata_verified'
                elif change=='kind':row['kind']='model'
                else:row['evidence']=[]
                self.assertTrue(validate_profiles(row))

    def test_unknown_counts_are_empty_and_zero_is_not_a_missing_sentinel(self):
        row=fixture();p=row['details']['benchmark_protocol'];p['counts']=[]
        self.assertEqual(validate_profiles(row),[])
        self.assertNotIn('0 task',comparison_body([row],'benchmark',resource_path))
        count=fixture()['details']['benchmark_protocol']['counts'][0];count['value']=0;p['counts']=[count]
        self.assertEqual(validate_profiles(row),[])
        self.assertTrue(count_text(count).startswith('0 '))
        for value in [True,-1,float('inf')]:
            count['value']=value;self.assertTrue(validate_profiles(row))

    def test_markdown_and_comparison_preserve_scoped_counts(self):
        row=fixture();markdown=resource_markdown(row);html=comparison_body([row],'benchmark',resource_path)
        for count in row['details']['benchmark_protocol']['counts']:
            self.assertIn(count['population'],markdown)
            self.assertIn(count['population'],html)
            self.assertIn(count['evidence_url'],markdown)
        self.assertNotIn('combined total: ',html)
        row['details']['benchmark_protocol']['notes']='</td><script>alert(1)</script>'
        rendered=comparison_body([row],'benchmark',resource_path)
        self.assertNotIn('<script>alert(1)</script>',rendered)
        self.assertIn('&lt;script&gt;',rendered)
        row['details']['benchmark_protocol']['counts'][0]['reference_url']='javascript:alert(1)'
        self.assertTrue(validate_profiles(row))

    def test_all_current_profiles_retain_primary_evidence(self):
        rows=[json.loads(x) for x in (ROOT/'data/catalog.jsonl').read_text().splitlines()]
        for kind in ['benchmark','dataset']:
            export=profile_export(rows,kind)
            self.assertGreater(export['profile_count'],0)
            for row in export['records']:
                self.assertEqual(set(row['profile']['evidence_urls']),{e['url'] for e in row['evidence']})
                self.assertTrue(all(e['sha256'] and e['retrieved_at'] for e in row['evidence']))




class ComparisonMarkupTests(unittest.TestCase):
    def test_cell_labels_are_block_strongs_without_line_breaks(self):
        # Each row repeats across 100+ profiles, so the table keeps its element count low.
        html=comparison_body([fixture()],'benchmark',resource_path)
        table=html[html.index('<tbody>'):html.index('</tbody>')]
        self.assertIn('<strong>Observe</strong>',table)
        self.assertIn('class="compare-name"',table)
        self.assertNotIn('<br><strong>',table)
        self.assertNotIn('<li><a href=',table.split('<details>')[1])


if __name__=='__main__':unittest.main()
