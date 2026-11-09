import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / ".github" / "workflows" / "scan.yml"
PUBLISH = ROOT / "automation" / "publish.yml"
# Stands in for catalog.py: build derives data/count.txt from the paper rows, validate checks it; both log their calls.
CATALOG_STUB = """import os, pathlib, sys
data = pathlib.Path('data')
expected = f"{len((data / 'papers.jsonl').read_text().splitlines())} papers\\n"
with open(os.environ['STUB_LOG'], 'a') as log: log.write(' '.join(sys.argv[1:]) + '\\n')
if sys.argv[1:] == ['build', '--list-outputs']: print('data/count.txt\\nREADME.md\\nREADME.zh-CN.md')
elif sys.argv[1:] == ['build']: (data / 'count.txt').write_text(expected)
elif sys.argv[1:] == ['validate']: sys.exit((data / 'count.txt').read_text() != expected)
"""

ROWS = '{"id": "a", "v": 1}\n{"id": "b", "v": 1}\n{"id": "c", "v": 1}\n{"id": "d", "v": 1}\n'


def step_script(workflow, name):
    lines = workflow.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {name}")
    run = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "run: |")
    indent, body = len(lines[run]) - len(lines[run].lstrip()), []
    for line in lines[run + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)).strip("\n") + "\n"


class PushRetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = self.base = Path(self.tmp.name)
        (base / "bin").mkdir()
        (base / "bin" / "python").write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
        (base / "bin" / "python").chmod(0o755)
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@example.org", "GITHUB_OUTPUT": str(base / "output"),
                    "STUB_LOG": str(base / "stub.log"), "PATH": f"{base / 'bin'}{os.pathsep}{os.environ['PATH']}"}
        self.origin = base / "origin.git"
        self.git("init", "-q", "--bare", "-b", "main", str(self.origin), cwd=base)
        seed = base / "seed"
        self.git("init", "-q", "-b", "main", str(seed), cwd=base)
        self.write(seed, {".gitignore": "dist/\n", "data/papers.jsonl": "a\nc\n", "data/count.txt": "2 papers\n",
                          "data/scan-status.json": "old\n", "docs/notes.md": "notes\n", "README.md": "readme\n",
                          "data/candidates.jsonl": ROWS, "data/editorial.json": "[]\n",
                          "README.zh-CN.md": "readme\n", "scripts/catalog.py": CATALOG_STUB,
                          "scripts/replay_scan_commit.py": (ROOT / "scripts" / "replay_scan_commit.py").read_text(),
                          ".indexnow/state.json": "{}\n", "index.html": "<p>old</p>\n"})
        self.commit(seed, "Initial")
        self.git("push", "-q", str(self.origin), "HEAD:main", cwd=seed)
        # actions/checkout makes a depth-1 clone.
        self.work = base / "work"
        self.git("clone", "-q", "--depth", "1", f"file://{self.origin}", str(self.work), cwd=base)
        self.git("clone", "-q", str(self.origin), str(base / "maintainer"), cwd=base)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.work, env=self.env, check=True, capture_output=True, text=True).stdout

    def write(self, repo, files):
        for path, text in files.items():
            (repo / path).parent.mkdir(parents=True, exist_ok=True)
            (repo / path).write_text(text)

    def commit(self, repo, message):
        self.git("add", "-A", cwd=repo)
        self.git("commit", "-qm", message, cwd=repo)

    def maintainer_pushes(self, files):
        repo = self.base / "maintainer"
        self.write(repo, files)
        self.commit(repo, "Maintainer change")
        self.git("push", "-q", "origin", "HEAD:main", cwd=repo)
        return self.head()

    def head(self, rev="main"):
        return self.git("--git-dir", str(self.origin), "rev-parse", rev).strip()

    def show(self, path):
        return self.git("--git-dir", str(self.origin), "show", f"main:{path}")

    def reject_every_push(self):
        hook = self.origin / "hooks" / "pre-receive"
        hook.write_text(f'#!/bin/sh\necho rejected >> "{self.base / "pushes.log"}"\nexit 1\n')
        hook.chmod(0o755)

    def reject_pushes(self, count):
        hook = self.origin / "hooks" / "pre-receive"
        log = self.base / "pushes.log"
        hook.write_text(f'#!/bin/sh\n[ "$(wc -l < "{log}" 2>/dev/null || echo 0)" -ge {count} ] && exit 0\necho rejected >> "{log}"\nexit 1\n')
        hook.chmod(0o755)

    def run_step(self, workflow, name):
        result = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step_script(workflow, name)],
                                cwd=self.work, env=self.env, capture_output=True, text=True)
        output, log = Path(self.env["GITHUB_OUTPUT"]), Path(self.env["STUB_LOG"])
        return result, output.read_text() if output.exists() else "", log.read_text() if log.exists() else ""

    def scan_writes(self):
        self.write(self.work, {"data/papers.jsonl": "a\nb\nc\n", "data/count.txt": "3 papers\n", "data/scan-status.json": "scan\n"})

    def test_scan_pushes_directly_when_main_has_not_moved(self):
        self.scan_writes()
        result, output, calls = self.run_step(SCAN, "Commit verified scan output")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((output, calls), ("pushed=true\n", ""))
        self.assertEqual(self.show("data/count.txt"), "3 papers\n")

    def test_scan_replays_onto_a_moved_main_and_rebuilds_generated_files(self):
        moved = self.maintainer_pushes({"data/papers.jsonl": "a\nc\nd\n", "data/count.txt": "3 papers\n", "docs/notes.md": "edited\n"})
        self.scan_writes()
        result, output, calls = self.run_step(SCAN, "Commit verified scan output")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((output, calls), ("pushed=true\n", "build --list-outputs\nbuild\nvalidate\n"))
        self.assertEqual(self.head("main~1"), moved)
        self.assertEqual((self.show("data/papers.jsonl"), self.show("data/count.txt")), ("a\nb\nc\nd\n", "4 papers\n"))
        self.assertEqual((self.show("docs/notes.md"), self.show("data/scan-status.json")), ("edited\n", "scan\n"))

    def test_scan_takes_main_build_outputs_and_rebuilds_them_on_a_conflict(self):
        moved = self.maintainer_pushes({"README.md": "maintainer\n", "data/count.txt": "9 papers\n"})
        self.scan_writes()
        self.write(self.work, {"README.md": "scan\n"})
        result, output, calls = self.run_step(SCAN, "Commit verified scan output")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((output, calls), ("pushed=true\n", "build --list-outputs\nbuild\nvalidate\n"))
        self.assertEqual(self.head("main~1"), moved)
        self.assertEqual((self.show("README.md"), self.show("data/count.txt")), ("maintainer\n", "3 papers\n"))
        self.assertEqual(self.show("data/papers.jsonl"), "a\nb\nc\n")

    def test_scan_keeps_its_own_receipts_on_a_conflict(self):
        self.maintainer_pushes({"data/scan-status.json": "maintainer\n"})
        self.scan_writes()
        result, output, _ = self.run_step(SCAN, "Commit verified scan output")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((output, self.show("data/scan-status.json")), ("pushed=true\n", "scan\n"))

    def test_scan_merges_conflicting_candidate_rows_by_id(self):
        self.maintainer_pushes({"data/candidates.jsonl": ROWS.replace('"a", "v": 1', '"a", "v": 2').replace('{"id": "d", "v": 1}\n', '') + '{"id": "e", "v": 1}\n'})
        self.scan_writes()
        self.write(self.work, {"data/candidates.jsonl": ROWS.replace('"a", "v": 1', '"a", "v": 3').replace('"b", "v": 1', '"b", "v": 3') + '{"id": "f", "v": 1}\n'})
        result, output, _ = self.run_step(SCAN, "Commit verified scan output")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(output, "pushed=true\n")
        rows = {row["id"]: row["v"] for row in map(json.loads, self.show("data/candidates.jsonl").splitlines())}
        self.assertEqual(rows, {"a": 2, "b": 3, "c": 1, "e": 1, "f": 1})

    def test_scan_retries_while_main_keeps_moving(self):
        self.reject_pushes(2)
        self.scan_writes()
        result, output, calls = self.run_step(SCAN, "Commit verified scan output")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((output, calls), ("pushed=true\n", "build --list-outputs\nbuild\nvalidate\n" * 2))
        self.assertEqual(self.show("data/scan-status.json"), "scan\n")

    def test_scan_reports_a_conflicting_main_and_pushes_nothing(self):
        moved = self.maintainer_pushes({"data/editorial.json": "[1]\n"})
        self.scan_writes()
        self.write(self.work, {"data/editorial.json": "[2]\n"})
        result, output, calls = self.run_step(SCAN, "Commit verified scan output")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("::error::main moved during the scan", result.stdout)
        self.assertIn("Not replayed: data/editorial.json", result.stdout)
        self.assertEqual((self.head(), output, calls), (moved, "", "build --list-outputs\n"))
        self.assertFalse((self.work / ".git" / "rebase-merge").exists())

    def test_scan_stops_after_five_push_attempts(self):
        self.reject_every_push()
        self.scan_writes()
        result, output, calls = self.run_step(SCAN, "Commit verified scan output")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("::error::The scan commit was not pushed to main after 5 attempts", result.stdout)
        self.assertEqual((self.base / "pushes.log").read_text(), "rejected\n" * 5)
        self.assertEqual((output, calls), ("", "build --list-outputs\nbuild\nvalidate\n" * 4))

    def test_publish_snapshot_replays_onto_a_moved_main(self):
        moved = self.maintainer_pushes({"docs/notes.md": "edited\n"})
        self.write(self.work, {"index.html": "<p>new</p>\n"})
        result, _, _ = self.run_step(PUBLISH, "Commit the public website snapshot")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.head("main~1"), moved)
        self.assertEqual((self.show("index.html"), self.show("docs/notes.md")), ("<p>new</p>\n", "edited\n"))

    def test_publish_snapshot_conflict_and_retry_limit_are_reported(self):
        moved = self.maintainer_pushes({"index.html": "<p>maintainer</p>\n"})
        self.write(self.work, {"index.html": "<p>new</p>\n"})
        result, _, _ = self.run_step(PUBLISH, "Commit the public website snapshot")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("::error::The website snapshot could not be rebased onto a newer main", result.stdout)
        self.assertEqual(self.head(), moved)
        self.reject_every_push()
        self.git("reset", "-q", "--hard", "FETCH_HEAD")
        self.write(self.work, {"index.html": "<p>newer</p>\n"})
        result, _, _ = self.run_step(PUBLISH, "Commit the public website snapshot")
        self.assertIn("::error::The website snapshot was not pushed to main after 3 attempts", result.stdout)
        self.assertEqual((self.base / "pushes.log").read_text(), "rejected\n" * 3)

    def test_search_receipts_replay_onto_a_moved_main(self):
        moved = self.maintainer_pushes({"index.html": "<p>republished</p>\n"})
        self.write(self.work, {".indexnow/state.json": '{"page": "sent"}\n'})
        result, _, _ = self.run_step(PUBLISH, "Preserve accepted state and actual submission receipts")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.head("main~1"), moved)
        self.assertEqual((self.show(".indexnow/state.json"), self.show("index.html")), ('{"page": "sent"}\n', "<p>republished</p>\n"))


if __name__ == "__main__":
    unittest.main()
