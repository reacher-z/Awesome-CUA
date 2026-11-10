import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from search_pages import resource_schema, schema_type
from site_data import eligible

ROOT=Path(__file__).resolve().parents[1]
ROWS=[json.loads(line) for line in (ROOT/'data/catalog.jsonl').read_text().splitlines() if line.strip()]


class ResourceTypeTests(unittest.TestCase):
    def test_kinds_map_to_specific_schema_types(self):
        by_id={row['id']:row for row in ROWS}
        self.assertEqual(schema_type(by_id['github:xlang-ai/osworld']),'Dataset')
        for row in ROWS:
            with self.subTest(row['id']):
                kind,found=row['kind'],schema_type(row)
                if kind in {'paper','survey'}:self.assertEqual(found,'ScholarlyArticle')
                elif kind in {'dataset','benchmark'}:self.assertEqual(found,'Dataset')
                elif kind in {'tool','framework','agent','infrastructure','product'}:self.assertIn(found,{'SoftwareSourceCode','SoftwareApplication'})
                elif kind=='company':self.assertEqual(found,'Organization')

    def test_entities_carry_the_fields_their_type_needs(self):
        for row in ROWS:
            if not eligible(row):continue
            for zh in (False,True):
                entity=resource_schema(row,zh=zh)
                with self.subTest(row['id'],zh=zh):
                    self.assertTrue(entity['name']);self.assertTrue(entity['url'].startswith('https://'))
                    if entity['@type']=='Dataset':self.assertGreaterEqual(len(entity['description']),50)
                    if entity['@type']=='SoftwareSourceCode':self.assertEqual(entity['codeRepository'],row['url'])
                    if entity['@type']=='SoftwareApplication':self.assertEqual(entity['applicationCategory'],'DeveloperApplication')
                    if entity['@type']=='Organization':self.assertNotIn('author',entity)
                    self.assertEqual(entity.get('inLanguage'),'zh-CN' if zh else None)


if __name__=='__main__':unittest.main()
