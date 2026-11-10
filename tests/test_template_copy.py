"""Guard visitor-facing template copy and generated record fields against maker labels and leaked editorial instructions."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Template sources whose strings reach visitors on the site, the API docs, the README and the dataset card.
TEMPLATES = sorted([*ROOT.glob('scripts/*.py'), ROOT / 'web/app.js', ROOT / 'README.md', ROOT / 'README.zh-CN.md'])
BANNED = re.compile(r'AI-assisted (?:editorial|inspection)|AI 辅助的?(?:一手来源)?编辑|not a weights/data license|'
                    r'Preserve supplied precision|third-party assets retain their own terms|'
                    r'newly observed changes require separate review|GNU text does not say')
# Fields copied onto resource pages from these generated or reviewed sources.
LICENSE_BASIS = re.compile(r'not a weights/data license|retain their own terms|does not say')
DATE_BASIS = re.compile(r'Preserve supplied precision|do not substitute')


class TemplateCopyTest(unittest.TestCase):
    def test_templates_carry_no_maker_labels_or_editorial_instructions(self):
        failures = [f'{path.relative_to(ROOT)}:{number}: {match[0]}'
                    for path in TEMPLATES
                    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1)
                    for match in BANNED.finditer(line)
                    if path.name != 'test_template_copy.py']
        self.assertFalse(failures, '\n'.join(failures))

    def test_license_basis_states_the_source_only(self):
        failures = []
        for line in (ROOT / 'data/enrichment.jsonl').read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            for slot, license in (row.get('licenses') or {}).items():
                if license and LICENSE_BASIS.search(license.get('basis', '')):
                    failures.append(f'{row["id"]} {slot}: {license["basis"]}')
        self.assertFalse(failures, '\n'.join(failures))

    def test_publication_date_basis_records_the_source_only(self):
        failures = []
        for line in (ROOT / 'data/publications.jsonl').read_text(encoding='utf-8').splitlines():
            row = json.loads(line)
            basis = (row.get('publication') or {}).get('date_basis') or ''
            if DATE_BASIS.search(basis):
                failures.append(f'{row["id"]}: {basis}')
        self.assertFalse(failures, '\n'.join(failures))


if __name__ == '__main__':
    unittest.main()
