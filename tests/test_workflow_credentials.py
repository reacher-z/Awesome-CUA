import base64
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / ".github" / "workflows" / "scan.yml"
PUBLISH = ROOT / "automation" / "publish.yml"
# Every workflow in this repository, plus the publication workflow installed in the website repository.
WORKFLOWS = [*sorted((ROOT / ".github" / "workflows").glob("*.yml")), PUBLISH]
TOKEN = "ghs_exampletoken"
HEADER = "AUTHORIZATION: basic " + base64.b64encode(f"x-access-token:{TOKEN}".encode()).decode()
# Push, dispatch, issue-tracking and read-only API steps; none of them checks out or runs repository code.
PUSH_STEPS = {("scan.yml", "scan", "Commit verified scan output"), ("scan.yml", "dispatch_quality", "Run Catalog quality on the scan commit"),
              ("scan.yml", "track_scan_health", "Update the scan health tracking issue"),
              ("publish.yml", "build", "Read repository star counts"), ("publish.yml", "build", "Commit the public website snapshot"), ("publish.yml", "notify_search", "Preserve accepted state and actual submission receipts"),
              ("freshness.yml", "dispatch_scan", "Dispatch a recovery scan"), ("release.yml", "release", "Publish the GitHub release")}


def steps(path):
    """Yield (job, step name or None, step lines) for every step in the workflow."""
    job, step = None, None
    for line in path.read_text().splitlines():
        indent = len(line) - len(line.lstrip())
        if step and (line.startswith("      - ") or line.strip() and indent < 8):
            yield step
            step = None
        header = re.fullmatch(r"  ([A-Za-z_][\w-]*):\s*", line)
        if header:
            job = header.group(1)
        elif job and line.startswith("      - "):
            name = re.fullmatch(r"      - name: (.+)", line)
            step = (job, name and name.group(1), [line])
        elif step:
            step[2].append(line)
    if step:
        yield step


def step_script(path, name):
    lines = next(lines for _, step, lines in steps(path) if step == name)
    run = next(i for i, line in enumerate(lines) if line.strip() == "run: |")
    return textwrap.dedent("\n".join(lines[run + 1:])).strip("\n") + "\n"


class WorkflowCredentialTests(unittest.TestCase):
    def test_no_checkout_leaves_the_token_in_git_config(self):
        checkouts = 0
        for path in WORKFLOWS:
            for job, name, lines in steps(path):
                if any("uses: actions/checkout@" in line for line in lines):
                    checkouts += 1
                    with self.subTest(workflow=path.name, job=job, step=name):
                        self.assertIn("          persist-credentials: false", lines)
        self.assertEqual(checkouts, 9)

    def test_only_push_and_dispatch_steps_receive_the_token(self):
        found = set()
        for path in WORKFLOWS:
            text, seen = path.read_text(), 0
            self.assertNotIn("secrets.", text)
            for job, name, lines in steps(path):
                if any("github.token" in line for line in lines):
                    found.add((path.name, job, name))
                    seen += sum("github.token" in line for line in lines)
                    self.assertIn("          GH_TOKEN: ${{ github.token }}", lines)
            self.assertEqual(text.count("github.token"), seen, f"{path.name} passes the token outside a step")
        self.assertEqual(found, PUSH_STEPS)


class PushStepCredentialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = self.base = Path(self.tmp.name)
        (base / "bin").mkdir()
        # Every git and python call logs which credentials it can see.
        for name, target in {"git": shutil.which("git"), "python": sys.executable}.items():
            (base / "bin" / name).write_text(f'#!/bin/sh\nprintf \'%s|%s|%s\\n\' "{name} $1" "${{GH_TOKEN:-}}" "${{GIT_CONFIG_VALUE_0:-}}" >> "$CALLS"\nexec "{target}" "$@"\n')
            (base / "bin" / name).chmod(0o755)
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@example.org", "GITHUB_OUTPUT": str(base / "output"), "GH_TOKEN": TOKEN,
                    "CALLS": str(base / "calls.log"), "PATH": f"{base / 'bin'}{os.pathsep}{os.environ['PATH']}"}
        self.origin, self.work, other = base / "origin.git", base / "work", base / "other"
        self.git("init", "-q", "--bare", "-b", "main", str(self.origin), cwd=base)
        self.git("init", "-q", "-b", "main", str(other), cwd=base)
        self.write(other, {".gitignore": "dist/\n", "data/a.txt": "a\n", "README.md": "readme\n", "README.zh-CN.md": "readme\n",
                           "docs/a.md": "a\n", "scripts/catalog.py": "", ".indexnow/state.json": "{}\n", "index.html": "old\n"})
        self.commit(other)
        self.git("remote", "add", "origin", str(self.origin), cwd=other)
        self.git("push", "-q", "origin", "HEAD:main", cwd=other)
        self.git("clone", "-q", str(self.origin), str(self.work), cwd=base)
        # main moves after checkout, so each step must pull and push again.
        self.write(other, {"docs/b.md": "b\n"})
        self.commit(other)
        self.git("push", "-q", "origin", "HEAD:main", cwd=other)
        self.moved = self.git("rev-parse", "HEAD", cwd=other).strip()
        (base / "calls.log").write_text("")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.run([shutil.which("git"), *args], cwd=cwd or self.work, env=self.env, check=True, capture_output=True, text=True).stdout

    def write(self, repo, files):
        for path, text in files.items():
            (repo / path).parent.mkdir(parents=True, exist_ok=True)
            (repo / path).write_text(text)

    def commit(self, repo):
        self.git("add", "-A", cwd=repo)
        self.git("commit", "-qm", "Change", cwd=repo)

    def run_step(self, workflow, name, files):
        self.write(self.work, files)
        result = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step_script(workflow, name)],
                                cwd=self.work, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git("--git-dir", str(self.origin), "rev-parse", "main~1").strip(), self.moved)
        return [line.split("|") for line in (self.base / "calls.log").read_text().splitlines()]

    def assert_only_push_and_pull_see_the_token(self, calls):
        authorized = [call for call, token, header in calls if header]
        self.assertEqual(authorized, ["git push", "git pull", "git push"])
        self.assertEqual({(token, header) for call, token, header in calls if call in authorized}, {("", HEADER)})
        self.assertEqual({(token, header) for call, token, header in calls if call not in authorized}, {("", "")})

    def test_scan_commit_passes_the_token_only_to_git_push_and_pull(self):
        calls = self.run_step(SCAN, "Commit verified scan output", {"data/a.txt": "scanned\n"})
        self.assertIn(["python scripts/catalog.py", "", ""], calls)
        self.assert_only_push_and_pull_see_the_token(calls)

    def test_website_snapshot_commit_passes_the_token_only_to_git_push_and_pull(self):
        self.assert_only_push_and_pull_see_the_token(self.run_step(PUBLISH, "Commit the public website snapshot", {"index.html": "new\n"}))

    def test_search_receipt_commit_passes_the_token_only_to_git_push_and_pull(self):
        calls = self.run_step(PUBLISH, "Preserve accepted state and actual submission receipts", {".indexnow/state.json": '{"sent": 1}\n'})
        self.assert_only_push_and_pull_see_the_token(calls)

if __name__ == "__main__":
    unittest.main()
