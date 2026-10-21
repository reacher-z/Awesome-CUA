import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from topic_pages import reviewed_topics, topic_body, topic_counts, topic_index_body, topic_markdown, topic_path, write_topic_exports
from search_pages import resource_path
from test_paper_library import LibraryParser
from test_resource_payloads import paper


class TopicPagesTests(unittest.TestCase):
    def setUp(self):
        self.paper = paper('2401.00001')
        self.paper.update(topics=['grounding', 'planning'], name='A <script>title</script>',
                          environments=['web'], summary='An original annotation & source.')
        self.asset = copy.deepcopy(self.paper)
        self.asset.update(id='github:example/tool', kind='tool', name='A tool', url='https://github.com/example/tool',
                          published_at=None, updated_at=None, authors=[], identifiers={}, details={}, topics=['grounding'])
        self.metadata = paper('2401.00002', 'metadata_verified')
        self.metadata.update(topics=['grounding', 'only-pending'])
        self.untagged = paper('2401.00003')
        self.rows = [self.paper, self.asset, self.metadata, self.untagged]

    def test_membership_uses_only_reviewed_tags_and_does_not_sum_overlapping_topics(self):
        topics = reviewed_topics(self.rows)
        self.assertEqual(set(topics), {'grounding', 'planning'})
        self.assertEqual({r['id'] for r in topics['grounding']}, {self.paper['id'], self.asset['id']})
        self.assertEqual(topic_counts(topics['grounding']),
                         {'total': 2, 'papers': 1, 'benchmarks': 0, 'datasets': 0, 'models': 0, 'systems': 1, 'learning': 0})
        with tempfile.TemporaryDirectory() as temp:
            manifest, _ = write_topic_exports(temp, self.rows, b'original catalog bytes')
        self.assertEqual(manifest['reviewed_resources'], 3)
        self.assertEqual(manifest['resources_with_topics'], 2)
        self.assertEqual(manifest['reviewed_resources_without_topics'], 1)
        self.assertEqual(sum(item['counts']['total'] for item in manifest['topics']), 3)
        self.assertEqual(manifest['catalog_sha256'], hashlib.sha256(b'original catalog bytes').hexdigest())

    def test_exports_preserve_full_source_records_and_retained_citation_edition(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest, groups = write_topic_exports(temp, self.rows, b'snapshot')
            for entry in manifest['topics']:
                for export in entry['exports']:
                    body = (Path(temp) / export['url'].lstrip('/')).read_bytes()
                    self.assertEqual(len(body), export['bytes'])
                    self.assertEqual(hashlib.sha256(body).hexdigest(), export['sha256'])
                folder = Path(temp) / 'downloads/topics' / entry['id']
                records = [json.loads(line) for line in (folder / 'records.jsonl').read_text().splitlines()]
                self.assertEqual(records, groups[entry['id']])
                citations = json.loads((folder / 'citations.csl.json').read_text())
                self.assertEqual(len(citations), entry['counts']['papers'])
                self.assertEqual(citations[0]['URL'], self.paper['url'] + 'v2')
                self.assertEqual(citations[0]['author'], [{'literal': a} for a in self.paper['authors']])

    def test_bilingual_visible_records_match_structured_data_and_fragment_links(self):
        for lang in ('en', 'zh'):
            rows = reviewed_topics(self.rows)['grounding']
            markup, schema = topic_body('grounding', rows, resource_path, language=lang)
            parsed = LibraryParser(markup)
            self.assertEqual(set(parsed.records), {self.paper['id'], self.asset['id']})
            self.assertEqual(len(parsed.records), 2)
            self.assertEqual(schema['numberOfItems'], len(parsed.records))
            self.assertEqual([i['url'] for i in schema['itemListElement']],
                             ['https://awesomecua.github.io' + resource_path({'id': rid}) for rid in parsed.records])
            for link in parsed.links:
                if link.startswith('#') and link != '#content':
                    self.assertIn(link[1:], parsed.ids)
            self.assertNotIn('<script>title</script>', markup)
            self.assertIn('&lt;script&gt;title&lt;/script&gt;', markup)
            self.assertIn('2024-01-02', markup)
            self.assertIn(self.paper['url'] + 'v2', parsed.links)
            markdown = topic_markdown('grounding', rows, resource_path, language=lang)
            self.assertTrue(markdown.endswith('\n'))
            self.assertFalse(markdown.endswith('\n\n'))

    def test_unsafe_topic_identifiers_cannot_create_paths(self):
        for topic in ['../outside', 'a/b', 'a?b', '<script>', 'two words', '.']:
            with self.subTest(topic=topic), self.assertRaises(ValueError):
                reviewed_topics([{**self.paper, 'topics': [topic]}])
        self.assertEqual(topic_path('human-in-the-loop', 'zh'), '/zh/topics/human-in-the-loop/')

    def test_empty_and_removed_topics_do_not_retain_previous_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            write_topic_exports(temp, self.rows, b'first')
            folder = Path(temp) / 'downloads/topics/grounding'
            keep = folder / 'README.txt'
            keep.write_text('unmanaged note')
            manifest, groups = write_topic_exports(temp, [self.untagged, self.metadata], b'second')
            self.assertEqual(groups, {})
            self.assertEqual(manifest['topics'], [])
            self.assertEqual(manifest['resources_with_topics'], 0)
            self.assertTrue(keep.exists())
            self.assertFalse((folder / 'records.jsonl').exists())
            self.assertFalse((folder / 'citations.bib').exists())
            self.assertFalse((folder / 'citations.csl.json').exists())
            markup, schema = topic_index_body(manifest)
            self.assertEqual(schema['numberOfItems'], 0)
            self.assertNotIn('data-topic=', markup)


if __name__ == '__main__':
    unittest.main()
