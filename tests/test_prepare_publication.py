"""prepare_publication.py on the fixture catalog: its preconditions, .gitignore merging, copied files and generated READMEs.

Stale-page removal and old-manifest path containment are covered in test_clean_build.py and test_resource_payloads.py.
"""
import collections
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import prepare_publication
import test_resource_payloads as payloads
from agent_pages import CLONE_COMMAND
from search_pages import KINDS, SITE, resource_path

PUBLIC_SCHEMAS = ['publication-observation.schema.json', 'resource.schema.json', 'scope-decision.schema.json']


class PreparePublicationTests(unittest.TestCase):
    # Reuse the small fixture catalog without collecting its tests a second time.
    setUp = payloads.ResourcePayloadTests.setUp
    write_json = payloads.ResourcePayloadTests.write_json
    write_inputs = payloads.ResourcePayloadTests.write_inputs
    build_site = payloads.ResourcePayloadTests.build_site

    def prepare(self, *flags):
        argv = ['prepare_publication.py', '--site-dir', str(self.site), *flags]
        with mock.patch.object(prepare_publication, 'ROOT', self.root), mock.patch.object(sys, 'argv', argv), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            prepare_publication.main()
        return stdout.getvalue()

    def files(self, directory):
        return {path.relative_to(directory).as_posix(): path.read_bytes() for path in directory.rglob('*') if path.is_file()}

    def test_missing_build_stops_with_an_actionable_message_before_changing_the_checkout(self):
        (self.site / '.gitignore').write_text('node_modules/\n')
        before = self.files(self.site)
        with self.assertRaises(SystemExit) as stopped:
            self.prepare('--skip-profile')
        self.assertEqual(stopped.exception.code, f'No website build in {self.build}; run python3 scripts/build_site.py first.')
        self.assertEqual(self.files(self.site), before)

    def test_missing_checkouts_are_refused_before_any_change(self):
        self.build_site()
        shutil.rmtree(self.site / '.git')
        # The website checkout is always required; the profile checkout unless --skip-profile is given.
        for flags, site_entries in [(('--skip-profile',), []), (('--profile-dir', str(self.root / 'missing-profile')), ['.git'])]:
            if site_entries:
                (self.site / '.git').mkdir()
            with self.subTest(flags=flags), self.assertRaises(SystemExit) as stopped:
                self.prepare(*flags)
            self.assertIn('Clone AwesomeCUA/awesomecua.github.io and AwesomeCUA/.github', stopped.exception.code)
            self.assertEqual([path.name for path in self.site.iterdir()], site_entries)
        self.assertFalse((self.root / 'missing-profile').exists())

    def test_gitignore_keeps_existing_lines_and_adds_each_pattern_once(self):
        self.build_site()
        (self.site / '.gitignore').write_text('node_modules/\n.cache/')
        self.prepare('--skip-profile')
        merged = (self.site / '.gitignore').read_text()
        self.assertEqual(merged, 'node_modules/\n.cache/\n.pipeline/\n__pycache__/\n.DS_Store\n')
        self.prepare('--skip-profile')
        self.assertEqual((self.site / '.gitignore').read_text(), merged)

    def test_new_gitignore_starts_without_a_blank_line(self):
        self.build_site()
        self.prepare('--skip-profile')
        self.assertEqual((self.site / '.gitignore').read_text(), '.pipeline/\n.cache/\n__pycache__/\n.DS_Store\n')

    def test_issue_form_and_public_schemas_are_copied_and_the_workflow_only_on_request(self):
        (self.root / 'automation').mkdir()
        shutil.copy2(ROOT / 'automation/publish.yml', self.root / 'automation/publish.yml')
        self.build_site()
        self.prepare('--skip-profile')
        self.assertFalse((self.site / '.github/workflows').exists())
        self.assertEqual((self.site / '.github/ISSUE_TEMPLATE/resource.yml').read_bytes(), (ROOT / '.github/ISSUE_TEMPLATE/resource.yml').read_bytes())
        for name in PUBLIC_SCHEMAS:
            self.assertEqual((self.site / 'schemas' / name).read_bytes(), (ROOT / 'schemas' / name).read_bytes(), name)
        self.prepare('--skip-profile', '--install-workflow')
        self.assertEqual((self.site / '.github/workflows/publish.yml').read_bytes(), (ROOT / 'automation/publish.yml').read_bytes())

    def readme_counts(self, rows):
        readme = (self.site / 'README.md').read_text()
        curated = sum(r['review_status'] == 'curated' for r in rows)
        papers = sum(r['review_status'] == 'curated' and r['kind'] in {'paper', 'survey'} for r in rows)
        self.assertIn(f'**{curated} curated resources** · **{papers} reviewed papers and surveys** · **0 discovery documents**', readme)
        self.assertNotIn('resource records**', readme)
        kinds = collections.Counter(r['kind'] for r in rows if r['review_status'] == 'curated')
        table = [line for line in readme.splitlines() if '[Open directory]' in line]
        self.assertEqual(table, [f'| {name} | {kinds[kind]} | [Open directory]({SITE}/categories/{kind}/) |' for kind, name in KINDS.items()])
        return readme

    def test_public_readme_reports_coverage_counts_and_only_reviewed_papers(self):
        self.build_site()
        output = self.prepare('--skip-profile')
        readme = self.readme_counts(self.rows)
        self.assertIn('Evidence snapshot: 2026-10-16T02:00:00Z.', readme)
        self.assertIn(CLONE_COMMAND, readme)
        schedule=json.loads((self.root / 'data/scan-config.json').read_text())
        self.assertIn('Discovery is scheduled every two hours at '+', '.join(schedule['scan_times_local'])+' '+schedule['timezone'], readme)
        self.assertIn('This website checks for a new source commit at '+' and '.join(f':{m:02d}' for m in schedule['publish_check_minutes'])+' past each hour '+schedule['timezone'], readme)
        reading = readme.split('## Research reading list\n', 1)[1].split('\n## ', 1)[0]
        self.assertEqual([line for line in reading.splitlines() if line.startswith('- ')],
                         [f'- [{self.reviewed["name"]}]({SITE}{resource_path(self.reviewed)}) — {self.reviewed["summary"]} [Original paper]({self.reviewed["url"]}).'])
        self.assertIn('public README; profile left to its own checkout', output)
        # The README is regenerated from the current counts, not appended to.
        self.write_inputs([row for row in self.rows if row is not self.tool])
        self.build_site()
        self.prepare('--skip-profile')
        self.assertEqual(self.readme_counts([row for row in self.rows if row is not self.tool]).count('## Research reading list'), 1)

    def test_profile_readme_shows_the_live_badge_and_clone_command(self):
        self.build_site()
        profile = self.site.parent / 'profile'
        (profile / '.git').mkdir(parents=True)
        output = self.prepare('--profile-dir', str(profile))
        text = (profile / 'profile/README.md').read_text()
        self.assertIn(f'![Live catalog counts]({SITE}/badges/catalog.svg)', text)
        self.assertNotIn('resource records**', text)
        self.assertIn(f'```sh\n{CLONE_COMMAND}\n```', text)
        self.assertTrue(text.endswith(f'[Scan status · every 2 hours]({SITE}/updates/) · [Source and contribution workflow](https://github.com/reacher-z/Awesome-CUA)\n'))
        self.assertIn('updated public README/profile', output)
        self.prepare('--profile-dir', str(profile))
        self.assertEqual((profile / 'profile/README.md').read_text(), text)


if __name__ == '__main__':
    unittest.main()
