import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_site import build_site
from search_pages import clean_text, eligible, resource_path, reviewed_times
from test_search_pages import copy_survey_source_inputs

ROOT=Path(__file__).resolve().parents[1]


def whitespace_errors(root):
    # git's default core.whitespace rules, which `git diff --cached --check` enforces before publication.
    errors=[]
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        data=path.read_bytes();name=path.relative_to(root)
        if b'\0' in data[:8000]:continue
        lines=data.split(b'\n')
        for number,line in enumerate(lines,1):
            indent=line[:len(line)-len(line.lstrip(b' \t'))]
            if line!=line.rstrip(b' \t\r'):errors.append(f'{name}:{number}: trailing whitespace')
            elif b' \t' in indent:errors.append(f'{name}:{number}: space before tab in indent')
        if len(lines)>1 and data.endswith(b'\n') and not lines[-2].strip(b' \t\r'):errors.append(f'{name}: new blank line at EOF')
    return errors


class GeneratedWhitespaceTests(unittest.TestCase):
    def test_clean_text_strips_line_ends_and_blank_lines_at_eof(self):
        self.assertEqual(clean_text('a  \n\tb\t\r\n \n\n'),'a\n\tb\n')
        self.assertEqual(clean_text('<p>x</p>'),'<p>x</p>')
        self.assertEqual(clean_text('x\n'),'x\n')
        self.assertEqual(clean_text(' \n'),'')
    def test_checker_reports_what_git_diff_check_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,data in [('eol.md',b'ok\nx  \n'),('cr.txt',b'x\r\n'),('eof.md',b'x\n\n'),('indent.txt',b' \tx\n'),('clean.html',b'<p>x</p>'),('tab.txt',b'\tx\n'),('binary.sqlite',b'\0x  \n\n')]:
                (root/name).write_bytes(data)
            self.assertEqual(whitespace_errors(root),['cr.txt:1: trailing whitespace','eof.md: new blank line at EOF','eol.md:2: trailing whitespace','indent.txt:1: space before tab in indent'])
    def test_untrusted_text_with_trailing_whitespace_builds_cleanly(self):
        reason='Out of scope:  \nstudies circuit design.\t\n\n'
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source';source.mkdir()
            shutil.copytree(ROOT/'web',source/'web');shutil.copytree(ROOT/'data',source/'data');shutil.copytree(ROOT/'schemas',source/'schemas')
            shutil.copy2(ROOT/'LICENSE',source/'LICENSE');shutil.copy2(ROOT/'AGENTS.md',source/'AGENTS.md')
            copy_survey_source_inputs(source)
            status_path=source/'data/exclusion-status.json';status=json.loads(status_path.read_text())
            decision=next(d for d in status['decisions'] if d['status']=='excluded');decision.update(name=decision['name']+'  ',reason=reason)
            status_path.write_text(json.dumps(status))
            guides_path=source/'data/site-guides.json';guides=json.loads(guides_path.read_text())
            guides[0]['body']+='  \n<p>Trailing guide markup.</p> \t\n\n'
            guides_path.write_text(json.dumps(guides))
            catalog_path=source/'data/catalog.jsonl';rows=[json.loads(line) for line in catalog_path.read_text().splitlines()]
            # The feed lists the newest editorial approvals, name order breaking ties; inject into its first entry.
            reviewed=reviewed_times(ROOT)
            paper=max(sorted((r for r in rows if eligible(r) and r['id'] in reviewed),key=lambda r:r['name'].casefold()),key=lambda r:reviewed[r['id']])
            paper.update(summary=paper['summary']+'  \nSecond line. \n',notes='Limitation.  \n\n')
            catalog_path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows))
            with mock.patch('build_site.ROOT',source):destination=build_site(Path(directory)/'site')
            self.assertEqual(whitespace_errors(destination),[])
            markdown=(destination/resource_path(decision).lstrip('/')/'index.md').read_text()
            self.assertIn('Out of scope:\nstudies circuit design.\n',markdown)
            self.assertIn('Trailing guide markup.',(destination/'guides'/guides[0]['slug']/'index.html').read_text())
            self.assertIn('Second line.',(destination/'feed.xml').read_text())
            manifest={item['path']:item['sha256'] for item in json.loads((destination/'data/search-manifest.json').read_text())['pages']}
            self.assertEqual(manifest[resource_path(paper)],hashlib.sha256((destination/resource_path(paper).lstrip('/')/'index.html').read_bytes()).hexdigest())
    def test_built_site_passes_publication_whitespace_check(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(whitespace_errors(build_site(directory)),[])


if __name__=='__main__':unittest.main()
