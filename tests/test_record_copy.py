"""Guard visitor-facing per-record copy in authored editorial data."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from catalog import editorial_identity

ENGLISH = re.compile(r'does not imply|does not mean|not an endorsement', re.I)
CHINESE = re.compile(r'不代表|不意味着')
# build.py copies these into catalog records; search_pages.py:259-300,321-360,
# specifications.py:130-167, and topic_pages.py:233,267 render them.
TOP_LEVEL = {'summary', 'notes', 'review_note'}
DETAIL_NONCOPY = {'evidence_url', 'reference_url', 'evidence_urls', 'url',
                  'versioned_url', 'download_url', 'repository_url',
                  'release_notes_url', 'documentation_url', 'license_url',
                  'sha256', 'id', 'version'}


def visible(path):
    if path in TOP_LEVEL:
        return True
    if path.startswith('details.'):
        return path.rsplit('.', 1)[-1] not in DETAIL_NONCOPY
    if path.startswith('reviewed_licenses.'):
        return path.endswith(('.reason', '.value.basis', '.value.declared'))
    return False


def strings(value, path=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from strings(child, f'{path}.{key}' if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from strings(child, f'{path}[{index}]')
    elif isinstance(value, str):
        yield path, value


class RecordCopyTest(unittest.TestCase):
    def test_visible_editorial_and_chinese_summaries(self):
        editorial = json.loads((ROOT / 'data/editorial.json').read_text(encoding='utf-8'))
        translations = json.loads((ROOT / 'data/translations.zh-CN.json').read_text(encoding='utf-8'))
        failures = []
        for row in editorial:
            record_id = row.get('id') or editorial_identity(row)[0]
            for path, value in strings(row):
                if visible(path) and ENGLISH.search(value):
                    failures.append(f'{record_id} {path}: {value}')
        for record_id, entry in translations.items():
            if CHINESE.search(entry['summary']):
                failures.append(f'{record_id} summary (zh-CN): {entry["summary"]}')
        self.assertFalse(failures, '\n'.join(failures))


if __name__ == '__main__':
    unittest.main()
