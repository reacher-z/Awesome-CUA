"""Builders, publication settings and authored links share one canonical website origin."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from site_config import FORMER_SITES, HOST, SITE

# Scan-written data keeps historical receipts and observations. The reviewed survey bundle and the
# citation file move to the canonical origin with their own rebuild.
EXEMPT = ('data/', 'web/survey/', 'research/survey/', 'CITATION.cff', 'scripts/site_config.py')


class SiteConfigTests(unittest.TestCase):
    def test_origins_are_bare_https_origins(self):
        for origin in (SITE, *FORMER_SITES):
            parts = urlsplit(origin)
            self.assertEqual((parts.scheme, parts.path, parts.query, parts.fragment, parts.username), ('https', '', '', '', None), origin)
        self.assertEqual(HOST, urlsplit(SITE).hostname)
        self.assertNotIn(SITE, FORMER_SITES)

    def test_publication_settings_use_the_same_origins(self):
        config = json.loads((ROOT / 'data/site-discovery.json').read_text(encoding='utf-8'))
        self.assertEqual(config['site_url'], SITE + '/')
        self.assertEqual(config['former_site_urls'], [origin + '/' for origin in FORMER_SITES])

    def test_authored_files_link_to_the_canonical_origin(self):
        tracked = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout.decode('utf-8').split('\0')
        stale = []
        for name in tracked:
            if not name or name.startswith(EXEMPT):
                continue
            try:
                text = (ROOT / name).read_text(encoding='utf-8').lower()
            except (UnicodeDecodeError, OSError):
                continue
            stale += [name for origin in FORMER_SITES if origin in text]
        self.assertEqual(stale, [], 'Link to ' + SITE + ' (or build the URL from site_config.SITE) instead of a former origin')


if __name__ == '__main__':
    unittest.main()
