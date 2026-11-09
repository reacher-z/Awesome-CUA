import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from paper_library import PAGE_SIZE, connected_assets, library_pages, paper_library
from publication_metadata import record_date_text
from search_pages import incoming_relations, resource_body, resource_path
from site_config import SITE


def record(rid, kind, *, name=None, status='curated', scope='core'):
    return {
        'id': rid, 'kind': kind, 'name': name or rid, 'url': 'https://example.org/' + rid.replace(':', '/'),
        'review_status': status, 'scope': scope, 'summary': 'Source-backed fixture annotation.',
        'published_at': '2025-02-03' if kind in {'paper', 'survey'} else None,
        'updated_at': None, 'authors': ['Literal Author'] if kind in {'paper', 'survey'} else [],
        'aliases': [], 'identifiers': {}, 'environments': ['unspecified'], 'topics': ['grounding'],
        'details': {}, 'relations': [], 'evidence': [], 'links': [], 'notes': '',
        'licenses': dict.fromkeys(('code', 'data', 'weights', 'document')),
        'last_verified_at': '2026-10-17T00:00:00Z',
    }


def asset(name, kind, paper_id='arxiv:2501.00001', *, rid=None, relation='introduced_by'):
    row = record(rid or 'github:fixture/' + kind, kind, name=name)
    url = 'https://example.org/evidence/' + kind
    row['relations'] = [{'type': relation, 'target_id': paper_id, 'evidence_url': url}]
    row['evidence'] = [{'url': url, 'sha256': 'a' * 64, 'retrieved_at': '2026-10-17T00:00:00Z',
                        'method': 'editorial_primary_review', 'role': 'primary', 'supports': ['relations']}]
    return row


class LibraryParser(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.entries = {}
        self.tags = []
        self.paper = None
        self.anchor = None
        self.kind_label = False
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        classes = attrs.get('class', '').split()
        if tag == 'article' and 'paper-entry' in classes:
            self.paper = attrs['data-resource-id']
            self.entries[self.paper] = {'assets': [], 'more': [], 'links': []}
        if tag == 'a' and self.paper:
            self.anchor = {'attrs': attrs, 'text': '', 'label': ''}
        if tag == 'span' and 'paper-asset-kind' in classes:
            self.kind_label = True

    def handle_data(self, value):
        if self.anchor is not None:
            self.anchor['text'] += value
            if self.kind_label:
                self.anchor['label'] += value

    def handle_endtag(self, tag):
        if tag == 'span':
            self.kind_label = False
        if tag == 'a' and self.anchor is not None:
            if self.paper:
                entry = self.entries[self.paper]
                entry['links'].append(self.anchor['attrs'].get('href'))
                if 'data-asset-id' in self.anchor['attrs']:
                    entry['assets'].append(self.anchor)
                if 'paper-asset-more' in self.anchor['attrs'].get('class', '').split():
                    entry['more'].append(self.anchor)
            self.anchor = None
        if tag == 'article':
            self.paper = None


class PaperAssetTests(unittest.TestCase):
    def setUp(self):
        self.paper = record('arxiv:2501.00001', 'paper', name='Fixture GUI paper')
        self.survey = record('arxiv:2501.00002', 'survey', name='Fixture GUI survey', scope='adjacent')

    def render(self, rows, language='en', number=1):
        markup, schema = paper_library(rows, resource_path, language=language, number=number)
        return markup, schema, LibraryParser(markup)

    def test_only_introduction_and_documentation_count_as_asset_connections(self):
        introduced = asset('Agent', 'agent')
        documented = asset('Dataset', 'dataset', relation='documented_by')
        ignored = [asset(kind, 'tool', rid='github:fixture/' + kind, relation=kind)
                   for kind in ('mentions', 'uses', 'evaluates', 'trained_on', 'variant_of', 'published_by')]
        shared_topic = asset('Shared topic only', 'model')
        shared_topic['relations'] = []
        linked = connected_assets([self.paper, introduced, documented, shared_topic, *ignored])
        self.assertEqual([row['id'] for row in linked[self.paper['id']]],
                         [introduced['id'], documented['id']])

    def test_owner_review_status_scope_and_kind_are_required(self):
        for changes in ({'review_status': 'metadata_verified'}, {'scope': 'relevance_pending'},
                        {'kind': 'paper'}, {'kind': 'survey'}, {'kind': 'company'}):
            with self.subTest(changes=changes):
                row = asset('Not a reviewed asset', 'agent')
                row.update(changes)
                row['evidence'] = []  # Ineligible owners must not create an evidence assertion.
                self.assertEqual(connected_assets([self.paper, row]), {})
        row = asset('Adjacent tool', 'tool')
        row['scope'] = 'adjacent'
        self.assertEqual(connected_assets([self.paper, row]), {self.paper['id']: [row]})

    def test_target_must_be_a_reviewed_core_or_adjacent_paper_or_survey(self):
        row = asset('Agent', 'agent')
        for changes in ({'review_status': 'metadata_verified'}, {'scope': 'relevance_pending'}, {'kind': 'dataset'}):
            with self.subTest(changes=changes):
                paper = {**self.paper, **changes}
                self.assertEqual(connected_assets([paper, row]), {})
        self.assertEqual(connected_assets([row]), {})
        row['relations'][0]['target_id'] = self.survey['id']
        self.assertEqual(connected_assets([self.survey, row]), {self.survey['id']: [row]})

    def test_relationship_receipt_must_have_matching_url_primary_role_and_relations_scope(self):
        row = asset('Agent', 'agent')
        receipt = row['evidence'][0]
        invalid = [[], [{**receipt, 'supports': ['aliases'], 'method': 'github_repository_identity'}],
                   [{**receipt, 'role': 'secondary'}], [{**receipt, 'url': 'https://example.org/other'}],
                   [{**receipt, 'supports': ['aliases']}, {**receipt, 'role': 'secondary'}],
                   [{**receipt, 'supports': ['details.relations']}]]
        for relation_type in ('introduced_by', 'documented_by'):
            for evidence in invalid:
                with self.subTest(relation=relation_type, evidence=evidence):
                    changed = copy.deepcopy(row)
                    changed['relations'][0]['type'] = relation_type
                    changed['evidence'] = evidence
                    with self.assertRaisesRegex(ValueError, 'relationship-scoped evidence'):
                        connected_assets([self.paper, changed])
                    with self.assertRaises(ValueError):
                        self.render([self.paper, changed])

    def test_assets_deduplicate_by_resource_id_and_sort_by_group_name_then_id(self):
        rows = [asset('Zebra', 'agent'), asset('Alpha', 'framework'), asset('alpha', 'tool'),
                asset('Beta', 'infrastructure'), asset('Data', 'dataset'), asset('Model', 'model'),
                asset('Bench', 'benchmark'), asset('Product', 'product')]
        rows[1]['relations'].append({**rows[1]['relations'][0], 'type': 'documented_by'})
        rows[1]['relations'].append(copy.deepcopy(rows[1]['relations'][0]))
        before = copy.deepcopy(rows)
        expected = ['github:fixture/framework', 'github:fixture/tool', 'github:fixture/infrastructure',
                    'github:fixture/agent', 'github:fixture/dataset', 'github:fixture/model',
                    'github:fixture/benchmark', 'github:fixture/product']
        for order in (rows, list(reversed(rows))):
            self.assertEqual([r['id'] for r in connected_assets([self.paper, *order])[self.paper['id']]], expected)
        self.assertEqual(rows, before)
        first = asset('Same name', 'framework', rid='github:fixture/z')
        second = asset('same NAME', 'framework', rid='github:fixture/a')
        self.assertEqual([r['id'] for r in connected_assets([self.paper, first, second])[self.paper['id']]],
                         [second['id'], first['id']])

    def test_three_direct_links_and_overflow_use_the_existing_paper_anchor(self):
        assets = [asset('D', 'model'), asset('B', 'dataset'), asset('A', 'framework'),
                  asset('E', 'product'), asset('C', 'benchmark')]
        rows = [self.paper, *assets]
        for language, suffix in [('en', 'resources'), ('zh', '项资源')]:
            markup, schema, parsed = self.render(rows, language)
            entry = parsed.entries[self.paper['id']]
            self.assertEqual([x['attrs']['data-asset-id'] for x in entry['assets']],
                             ['github:fixture/framework', 'github:fixture/dataset', 'github:fixture/model'])
            self.assertEqual(len(entry['more']), 1)
            self.assertEqual(entry['more'][0]['attrs']['href'], resource_path(self.paper) + '#connected-assets')
            self.assertEqual(entry['more'][0]['text'], '+2 ' + suffix)
            self.assertEqual(schema['numberOfItems'], 1)
            self.assertEqual([item['url'] for item in schema['itemListElement']],
                             [SITE + resource_path(self.paper)])
        detail = resource_body(self.paper, {r['id']: r for r in rows}, incoming_relations(rows))
        self.assertIn('id="connected-assets"', detail)

    def test_up_to_three_assets_do_not_render_an_overflow_link(self):
        all_assets = [asset('Agent', 'agent'), asset('Data', 'dataset'), asset('Model', 'model')]
        for count in range(4):
            with self.subTest(count=count):
                _, _, parsed = self.render([self.paper, *all_assets[:count]])
                self.assertEqual(len(parsed.entries[self.paper['id']]['assets']), count)
                self.assertEqual(parsed.entries[self.paper['id']]['more'], [])

    def test_every_asset_kind_has_the_expected_bilingual_label_and_color_group(self):
        expected = {'agent': ('code', 'Agent', '智能体'), 'framework': ('code', 'Code', '代码'),
                    'tool': ('code', 'Tool', '工具'), 'infrastructure': ('code', 'Runtime', '运行环境'),
                    'dataset': ('data', 'Data', '数据'), 'model': ('model', 'Model', '模型'),
                    'benchmark': ('benchmark', 'Benchmark', '基准'), 'product': ('product', 'Product', '产品')}
        for kind, (group, en, zh) in expected.items():
            for language, label in [('en', en), ('zh', zh)]:
                with self.subTest(kind=kind, language=language):
                    row = asset('Asset title', kind)
                    _, _, parsed = self.render([self.paper, row], language)
                    anchor = parsed.entries[self.paper['id']]['assets'][0]
                    self.assertIn('paper-asset-' + group, anchor['attrs']['class'].split())
                    self.assertEqual(anchor['label'], label)
                    self.assertEqual(anchor['attrs']['href'], row['url'])
                    self.assertEqual(anchor['attrs']['title'], label + ': Asset title')

    def test_rendered_asset_groups_have_distinct_stylesheet_color_tokens(self):
        css = (ROOT / 'web/pages.css').read_text(encoding='utf-8')
        inks = set()
        for group in ('code', 'data', 'model', 'benchmark', 'product'):
            rule = re.search(r'\.paper-asset-' + group + r'\{([^}]+)\}', css)
            self.assertIsNotNone(rule, group)
            tokens = dict(re.findall(r'--asset-(ink|fill|border):([^;}]+)', rule[1]))
            self.assertEqual(set(tokens), {'ink', 'fill', 'border'}, group)
            inks.add(tokens['ink'])
        self.assertEqual(len(inks), 5)
        shared = re.search(r'\.reading-shell a\.paper-asset\{([^}]+)\}', css)[1]
        for token in ('ink', 'fill', 'border'):
            self.assertIn('var(--asset-' + token + ')', shared)

    def test_unsafe_asset_href_is_rejected_and_untrusted_names_are_escaped(self):
        for url in ('javascript:alert(1)', 'data:text/html,<script>alert(1)</script>',
                    '//evil.example/path', '/relative/path', None):
            with self.subTest(url=url):
                row = asset('Unsafe URL', 'tool')
                row['url'] = url
                with self.assertRaises(ValueError):
                    self.render([self.paper, row])
        row = asset('<img src=x onerror="alert(1)"> & "quoted"', 'dataset')
        row['url'] = 'https://example.org/data?x=1&label="quoted"'
        paper = copy.deepcopy(self.paper)
        paper.update(name='<script>paper()</script>', authors=['<img src=x>'], summary='<script>summary()</script>')
        markup, _, parsed = self.render([paper, row])
        self.assertNotIn('<script>paper()</script>', markup)
        self.assertNotIn('<script>summary()</script>', markup)
        self.assertFalse(any(tag in ('script', 'img') for tag, _ in parsed.tags))
        anchor = parsed.entries[paper['id']]['assets'][0]
        self.assertEqual(anchor['attrs']['href'], row['url'])
        self.assertEqual(anchor['attrs']['title'], 'Data: ' + row['name'])
        self.assertNotIn('onerror', anchor['attrs'])
        self.assertIn('&amp;', markup)
        self.assertIn('&quot;', markup)

    def test_itemlist_contains_only_visible_reviewed_papers_with_or_without_asset_links(self):
        metadata = record('arxiv:2501.00003', 'paper', status='metadata_verified', scope='relevance_pending')
        unreviewed_scope = record('arxiv:2501.00004', 'paper', scope='relevance_pending')
        linked = asset('Only a data link', 'dataset')
        ignored = asset('Metadata paper link', 'agent', metadata['id'])
        rows = [self.paper, self.survey, metadata, unreviewed_scope, linked, ignored]
        original = copy.deepcopy(rows)
        for language in ('en', 'zh'):
            _, schema, parsed = self.render(rows, language)
            expected = {self.paper['id'], self.survey['id']}
            self.assertEqual(set(parsed.entries), expected)
            self.assertEqual(schema['numberOfItems'], len(expected))
            self.assertEqual([item['position'] for item in schema['itemListElement']], [1, 2])
            self.assertEqual({item['url'] for item in schema['itemListElement']},
                             {SITE + resource_path(r) for r in (self.paper, self.survey)})
            self.assertEqual(len(parsed.entries[self.paper['id']]['assets']), 1)
            self.assertEqual(parsed.entries[self.survey['id']]['assets'], [])
        self.assertEqual(rows, original)

    def test_later_page_assets_use_the_full_catalog_with_global_counts_and_overflow(self):
        newer = [record('arxiv:2502.' + f'{index:05}', 'paper') for index in range(PAGE_SIZE)]
        older = {**self.paper, 'published_at': '2024-01-01'}
        older_assets = [asset(name, kind, older['id']) for name, kind in
                        [('Code', 'framework'), ('Data', 'dataset'), ('Model', 'model'), ('Bench', 'benchmark')]]
        newer_asset = asset('Newer agent', 'agent', newer[-1]['id'])
        rows = [*newer, older, newer_asset, *older_assets]
        for language in ('en', 'zh'):
            first_markup, first_schema, first = self.render(rows, language)
            last_markup, last_schema, last = self.render(rows, language, number=2)
            self.assertNotIn(older['id'], first.entries)
            self.assertEqual(len(first.entries), PAGE_SIZE)
            self.assertEqual(first_schema['numberOfItems'], PAGE_SIZE)
            self.assertEqual(list(last.entries), [older['id']])
            self.assertEqual(last_schema['numberOfItems'], 1)
            self.assertEqual(last_schema['itemListElement'][0]['position'], PAGE_SIZE + 1)
            self.assertEqual(len(first.entries[newer[-1]['id']]['assets']), 1)
            self.assertEqual([item['attrs']['data-asset-id'] for item in last.entries[older['id']]['assets']],
                             [row['id'] for row in older_assets[:3]])
            self.assertEqual(last.entries[older['id']]['more'][0]['attrs']['href'],
                             resource_path(older) + '#connected-assets')
            for markup in (first_markup, last_markup):
                self.assertIn('<strong>' + str(PAGE_SIZE + 1) + '</strong>', markup)
                self.assertIn('class="library-connected-count" href="/connections/">2 ', markup)
        # An off-page connection must still meet the same evidence contract.
        changed = copy.deepcopy(rows)
        changed[-1]['evidence'][0]['supports'] = ['aliases']
        with self.assertRaisesRegex(ValueError, 'relationship-scoped evidence'):
            self.render(changed, number=1)

    def test_current_catalog_membership_and_rendered_links_match_reviewed_source_edges(self):
        rows = [json.loads(line) for line in (ROOT / 'data/catalog.jsonl').read_text(encoding='utf-8').splitlines()]
        papers = {row['id'] for row in rows if row['kind'] in ('paper', 'survey')
                  and row['review_status'] == 'curated' and row['scope'] in ('core', 'adjacent')}
        asset_kinds = {'agent', 'framework', 'tool', 'infrastructure', 'dataset', 'model', 'benchmark', 'product'}
        expected = set()
        for owner in rows:
            if owner['kind'] not in asset_kinds or owner['review_status'] != 'curated' or owner['scope'] not in ('core', 'adjacent'):
                continue
            proven = {receipt['url'] for receipt in owner['evidence']
                      if receipt['role'] == 'primary' and 'relations' in receipt['supports']}
            for relation in owner['relations']:
                if relation['type'] in ('introduced_by', 'documented_by') and relation['target_id'] in papers:
                    self.assertIn(relation['evidence_url'], proven)
                    expected.add((relation['target_id'], owner['id']))
        linked = connected_assets(rows)
        actual = {(rid, asset['id']) for rid, values in linked.items() for asset in values}
        self.assertEqual(actual, expected)
        self.assertTrue(expected)
        expected_order = [row['id'] for row in sorted((row for row in rows if row['id'] in papers),
                          key=lambda row: (record_date_text(row), row['id']), reverse=True)]
        for language in ('en', 'zh'):
            seen = []
            for number in range(1, library_pages(rows) + 1):
                markup, schema, parsed = self.render(rows, language, number)
                visible = list(parsed.entries)
                article_ids = [attrs['data-resource-id'] for tag, attrs in parsed.tags
                               if tag == 'article' and 'data-resource-id' in attrs]
                self.assertEqual(article_ids, visible)  # No duplicates hidden by the parser's ID map.
                self.assertEqual(visible, expected_order[len(seen):len(seen) + PAGE_SIZE])
                self.assertLessEqual(len(visible), PAGE_SIZE)
                self.assertEqual(schema['numberOfItems'], len(visible))
                self.assertEqual(len(schema['itemListElement']), len(visible))
                self.assertEqual([item['position'] for item in schema['itemListElement']],
                                 list(range(len(seen) + 1, len(seen) + len(visible) + 1)))
                self.assertEqual([item['url'] for item in schema['itemListElement']],
                                 [SITE + resource_path({'id': rid}) for rid in visible])
                self.assertIn('<strong>' + f'{len(papers):,}' + '</strong>', markup)
                self.assertIn('class="library-connected-count" href="/connections/">' + str(len(linked)) + ' ', markup)
                for rid, entry in parsed.entries.items():
                    expected_assets = linked.get(rid, [])
                    self.assertEqual([item['attrs']['data-asset-id'] for item in entry['assets']],
                                     [row['id'] for row in expected_assets[:3]])
                    self.assertEqual(len(entry['more']), int(len(expected_assets) > 3))
                    if entry['more']:
                        self.assertEqual(entry['more'][0]['attrs']['href'], resource_path({'id': rid}) + '#connected-assets')
                seen.extend(visible)
            self.assertEqual(seen, expected_order)
            self.assertEqual(len(seen), len(set(seen)))
            self.assertEqual(set(seen), papers)


if __name__ == '__main__':
    unittest.main()
