import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import submit_indexnow as indexing


class IndexNowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.site = 'https://catalog.example'
        self.key = 'publictestkey123'
        self.manifest = {'site_url': self.site, 'indexable_pages': 2, 'pages': [
            {'path': '/', 'indexable': True, 'sha256': 'a' * 64},
            {'path': '/new/', 'indexable': True, 'sha256': 'b' * 64},
            {'path': '/pending/', 'indexable': False, 'sha256': 'c' * 64},
        ]}
        self.state = self.root / 'state.json'
        self.receipts = self.root / 'receipts.json'
        self.config = self.root / 'config.json'
        indexing.write_json(self.config, {'site_url': self.site, 'indexnow_key': self.key})
        indexing.write_json(self.root / 'data/search-manifest.json', self.manifest)
        self.previous = {'schema_version': 1, 'site': self.site, 'accepted_pages': {'/': 'd' * 64, '/gone/': 'e' * 64}}
        indexing.write_json(self.state, self.previous)
        self.root.joinpath('sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://catalog.example/</loc></url><url><loc>https://catalog.example/new/</loc></url></urlset>')

    def run_submission(self, submit=True):
        return indexing.submit_changes(site_dir=self.root, config_path=self.config, state_path=self.state, receipts_path=self.receipts, submit=submit)

    def preflight(self, url):
        return self.key.encode() if url.endswith('.txt') else json.dumps(self.manifest).encode()

    def test_changes_include_demotion_and_removal_but_not_unreviewed_discoveries(self):
        previous = {'/': 'd' * 64, '/gone/': 'e' * 64, '/pending/': 'f' * 64}
        result = indexing.changed_pages(indexing.fingerprints(self.manifest, self.site), previous)
        self.assertEqual(result, {'new': ['/new/'], 'changed': ['/'], 'removed': ['/gone/', '/pending/']})
        result = indexing.changed_pages(indexing.fingerprints(self.manifest, self.site), self.previous['accepted_pages'])
        self.assertNotIn('/pending/', [p for group in result.values() for p in group])

    def test_dry_run_never_writes_or_contacts_network(self):
        before = self.state.read_bytes()
        with mock.patch.object(indexing.urllib.request, 'urlopen', side_effect=AssertionError('network forbidden')):
            result = self.run_submission(submit=False)
        self.assertEqual(result['status'], 'dry_run')
        self.assertEqual(result['url_count'], 3)
        self.assertEqual(before, self.state.read_bytes())
        self.assertFalse(self.receipts.exists())

    def test_unchanged_pages_do_not_send_a_network_request(self):
        self.previous['accepted_pages'] = indexing.fingerprints(self.manifest, self.site)
        indexing.write_json(self.state, self.previous)
        before = self.state.read_bytes()
        with mock.patch.object(indexing.urllib.request, 'urlopen', side_effect=AssertionError('network forbidden')):
            result = self.run_submission()
        self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(before, self.state.read_bytes())
        self.assertEqual(indexing.read_json(self.receipts)[-1]['url_count'], 0)

    def test_stale_live_manifest_preserves_retry_state_without_posting(self):
        before = self.state.read_bytes()
        with mock.patch.object(indexing, 'fetch_public', side_effect=[self.key.encode(), b'{}']), mock.patch.object(indexing.urllib.request, 'urlopen', side_effect=AssertionError('POST forbidden')):
            result = self.run_submission()
        self.assertEqual(result['status'], 'not_sent')
        self.assertEqual(result['failure_phase'], 'preflight')
        self.assertEqual(before, self.state.read_bytes())

    def test_wrong_ownership_key_does_not_send_page_urls(self):
        with mock.patch.object(indexing, 'fetch_public', return_value=b'wrong'), mock.patch.object(indexing.urllib.request, 'urlopen', side_effect=AssertionError('POST forbidden')):
            result = self.run_submission()
        self.assertEqual(result['status'], 'not_sent')
        self.assertEqual(indexing.read_json(self.state), self.previous)

    def test_accepted_changes_advance_only_to_current_indexable_pages(self):
        response = io.BytesIO(b'')
        response.status = 200
        with mock.patch.object(indexing, 'fetch_public', side_effect=self.preflight), mock.patch.object(indexing.urllib.request, 'urlopen', return_value=response) as post:
            result = self.run_submission()
        request = post.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.method, 'POST')
        self.assertEqual(payload['urlList'], [self.site + '/', self.site + '/gone/', self.site + '/new/'])
        self.assertEqual(result['status'], 200)
        self.assertEqual(indexing.read_json(self.state)['accepted_pages'], indexing.fingerprints(self.manifest, self.site))
        self.assertEqual(self.run_submission(submit=False)['url_count'], 0)

    def test_pending_key_and_rate_limit_keep_all_changes_for_retry(self):
        for status in [202, 429]:
            with self.subTest(status=status):
                before = self.state.read_bytes()
                response = io.BytesIO(b'')
                response.status = status
                error = urllib.error.HTTPError(indexing.ENDPOINT, status, 'rate limited', {}, io.BytesIO(b'retry later'))
                with mock.patch.object(indexing, 'fetch_public', side_effect=self.preflight), mock.patch.object(indexing.urllib.request, 'urlopen', return_value=response, side_effect=error if status == 429 else None):
                    result = self.run_submission()
                self.assertEqual(result['status'], status)
                self.assertEqual(before, self.state.read_bytes())
                self.assertEqual(self.run_submission(submit=False)['url_count'], 3)
                error.close()

    def test_state_accepted_for_a_former_origin_restarts_for_the_new_host(self):
        indexing.write_json(self.config, {'site_url': self.site + '/', 'former_site_urls': ['https://old.example/'], 'indexnow_key': self.key})
        indexing.write_json(self.state, {**self.previous, 'site': 'https://old.example', 'accepted_pages': indexing.fingerprints(self.manifest, self.site)})
        response = io.BytesIO(b'')
        response.status = 200
        with mock.patch.object(indexing, 'fetch_public', side_effect=self.preflight) as fetch, mock.patch.object(indexing.urllib.request, 'urlopen', return_value=response) as post:
            result = self.run_submission()
        payload = json.loads(post.call_args.args[0].data)
        self.assertEqual((payload['host'], payload['keyLocation']), ('catalog.example', self.site + '/' + self.key + '.txt'))
        self.assertEqual(payload['urlList'], [self.site + '/', self.site + '/new/'])
        self.assertEqual({call.args[0] for call in fetch.call_args_list}, {self.site + '/' + self.key + '.txt', self.site + '/data/search-manifest.json'})
        self.assertEqual(result['replaces_accepted_state_for'], 'https://old.example')
        state = indexing.read_json(self.state)
        self.assertEqual((state['site'], state['accepted_pages']), (self.site, indexing.fingerprints(self.manifest, self.site)))
        self.assertEqual(self.run_submission(submit=False)['url_count'], 0)

    def test_state_for_an_undeclared_origin_is_rejected(self):
        for config in [{'site_url': self.site, 'indexnow_key': self.key},
                       {'site_url': self.site, 'former_site_urls': ['https://old.example/'], 'indexnow_key': self.key}]:
            with self.subTest(config=config):
                indexing.write_json(self.config, config)
                indexing.write_json(self.state, {**self.previous, 'site': 'https://other.example'})
                with self.assertRaisesRegex(ValueError, 'Accepted-state identity'):
                    self.run_submission(submit=False)
        indexing.write_json(self.config, {'site_url': self.site, 'former_site_urls': 'https://old.example/', 'indexnow_key': self.key})
        with self.assertRaisesRegex(ValueError, 'Former site origins'):
            self.run_submission(submit=False)

    def test_foreign_paths_or_sitemap_disagreement_are_rejected(self):
        self.previous['accepted_pages']['//outside.example/stolen'] = 'f' * 64
        indexing.write_json(self.state, self.previous)
        with self.assertRaisesRegex(ValueError, 'accepted-state'):
            self.run_submission(submit=False)
        self.root.joinpath('sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>')
        with self.assertRaisesRegex(ValueError, 'Sitemap'):
            self.run_submission(submit=False)


if __name__ == '__main__':
    unittest.main()
