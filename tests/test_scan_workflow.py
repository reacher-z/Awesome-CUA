import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "scan.yml"


def block(lines, start):
    indent = len(lines[start]) - len(lines[start].lstrip())
    body = []
    for line in lines[start + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)).strip("\n") + "\n"


def step_script(name):
    lines = WORKFLOW.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {name}")
    return block(lines, next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "run: |"))


def section(*path):
    lines = WORKFLOW.read_text().splitlines()
    start, end = -1, len(lines)
    for depth, key in enumerate(path):
        prefix = "  " * depth + key + ":"
        start = next(i for i in range(start + 1, end) if lines[i] == prefix or lines[i].startswith(prefix + " "))
        end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) <= 2 * depth), len(lines))
    return lines[start].split(":", 1)[1].strip() or block(lines, start)


class ScanWorkflowTests(unittest.TestCase):
    def test_scan_runs_the_catalog_quality_gate_and_site_build_before_committing(self):
        check = step_script("Check generated data and review boundaries")
        for command in ["python scripts/catalog.py validate", "python scripts/catalog.py build --check",
                        "python scripts/run_tests.py", "node --test tests/web.test.mjs", "python scripts/build_site.py"]:
            self.assertIn(command, check)

    def test_only_the_dispatch_job_can_write_actions(self):
        self.assertEqual(section("permissions"), "{}")
        self.assertEqual(section("jobs", "scan", "permissions"), "contents: write\n")
        self.assertEqual(section("jobs", "scan", "outputs"), "pushed: ${{ steps.commit.outputs.pushed }}\nrepeated_partial: ${{ steps.scan.outputs.repeated_partial }}\n"
                         "status: ${{ steps.scan.outputs.status }}\nnotes: ${{ steps.scan.outputs.notes }}\n")
        self.assertEqual(section("jobs", "dispatch_quality", "needs"), "scan")
        self.assertEqual(section("jobs", "dispatch_quality", "if"), "needs.scan.outputs.pushed == 'true'")
        self.assertEqual(section("jobs", "dispatch_quality", "permissions"), "actions: write\n")
        steps = section("jobs", "dispatch_quality", "steps")
        self.assertNotIn("uses:", steps)
        self.assertEqual(steps.count("- name:"), 1)
        self.assertIn("GH_TOKEN: ${{ github.token }}", steps)
        self.assertIn('run: gh workflow run catalog.yml --ref main -R "$GITHUB_REPOSITORY"', steps)
        self.assertEqual(WORKFLOW.read_text().count("actions: write"), 1)


def run_commands(path, job, steps=None):
    """Shell commands of a job's run steps, in order; optionally only the named steps."""
    lines = path.read_text().splitlines()
    start = lines.index(f"  {job}:")
    end = next((i for i in range(start + 1, len(lines)) if re.fullmatch(r"  [\w-]+:", lines[i])), len(lines))
    commands, name = [], None
    for index in range(start + 1, end):
        line = lines[index]
        named = re.fullmatch(r"      - name: (.+)", line)
        if named:
            name = named.group(1)
        elif line.startswith("      - "):
            name = None
        if steps is not None and name not in steps:
            continue
        if line.strip() == "run: |":
            commands += [l.strip() for l in block(lines, index).splitlines() if l.strip() and not l.strip().startswith("#")]
        elif line.strip().startswith("run: ") or line.startswith("      - run: "):
            commands.append(line.split("run: ", 1)[1].strip())
    return commands


class QualityGateParityTests(unittest.TestCase):
    """Every Catalog quality check, including checks added later, runs in the scan job before its commit and in publication."""
    CI = ROOT / ".github" / "workflows" / "catalog.yml"
    PUBLISH = ROOT / "automation" / "publish.yml"
    SETUP = "python -m pip install --require-hashes -r requirements-dev.txt"
    # The scan's own build phase runs catalog.py build; the gates then confirm it with build --check.
    REBUILD = "python scripts/catalog.py build"

    def ci_checks(self):
        checks = [command for command in run_commands(self.CI, "validate") if command not in {self.SETUP, self.REBUILD}]
        self.assertIn("python scripts/run_tests.py", checks)
        return checks

    def test_scan_job_runs_every_catalog_quality_check_before_committing(self):
        self.assertIn("['scripts/catalog.py','build']", (ROOT / "scripts" / "scan.py").read_text())
        self.assertEqual(run_commands(WORKFLOW, "scan", {"Check generated data and review boundaries"}), self.ci_checks())
        order = [line.strip() for line in WORKFLOW.read_text().splitlines() if line.startswith("      - name: ")]
        self.assertLess(order.index("- name: Check generated data and review boundaries"), order.index("- name: Commit verified scan output"))
        # A failed check skips the commit: the commit step never runs on always() or failure().
        commit = WORKFLOW.read_text().split("- name: Commit verified scan output\n", 1)[1].split("\n      - name:", 1)[0]
        self.assertNotRegex(commit, r"always\(\)|failure\(\)|continue-on-error")

    def test_publication_runs_every_catalog_quality_check_in_order_before_deploying(self):
        published = run_commands(self.PUBLISH, "build", {"Validate source data and website behavior", "Build website from the verified catalog"})
        self.assertEqual([check for check in self.ci_checks() if check not in published], [], "publication skips Catalog quality checks")
        positions = [published.index(check) for check in self.ci_checks()]
        self.assertEqual(positions, sorted(positions))


class ScanCommitStepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@example.org", "GH_LOG": str(base / "gh.log"), "GITHUB_OUTPUT": str(base / "output")}
        (base / "bin").mkdir()
        gh = base / "bin" / "gh"
        gh.write_text('#!/bin/sh\necho "$@" >> "$GH_LOG"\n')
        gh.chmod(0o755)
        self.env["PATH"] = f"{base / 'bin'}{os.pathsep}{os.environ['PATH']}"
        self.origin, self.work = base / "origin.git", base / "work"
        self.git("init", "-q", "--bare", "-b", "main", str(self.origin), cwd=base)
        self.git("init", "-q", "-b", "main", str(self.work), cwd=base)
        for path, text in {".gitignore": "dist/\n", "data/catalog.jsonl": "{}\n", "docs/papers.md": "# Papers\n",
                           "README.md": "readme\n", "README.zh-CN.md": "readme\n", "scripts/build.py": "pass\n"}.items():
            (self.work / path).parent.mkdir(parents=True, exist_ok=True)
            (self.work / path).write_text(text)
        self.git("add", "-A")
        self.git("commit", "-qm", "Initial")
        self.git("remote", "add", "origin", str(self.origin))
        self.git("push", "-q", "origin", "HEAD:main")
        self.initial = self.origin_head()

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.work, env=self.env, check=True, capture_output=True, text=True).stdout

    def origin_head(self):
        return self.git("--git-dir", str(self.origin), "rev-parse", "main").strip()

    def run_step(self):
        result = subprocess.run(["bash", "-e", "-c", step_script("Commit verified scan output")], cwd=self.work,
                                env=self.env, capture_output=True, text=True)
        gh, output = Path(self.env["GH_LOG"]), Path(self.env["GITHUB_OUTPUT"])
        return result, (gh.read_text() if gh.exists() else "") + (output.read_text() if output.exists() else "")

    def test_commits_scan_paths_and_reports_the_push(self):
        (self.work / "data" / "catalog.jsonl").write_text('{"id":"x"}\n')
        (self.work / "dist" / "site").mkdir(parents=True)
        (self.work / "dist" / "site" / "index.html").write_text("ignored build output\n")
        result, effects = self.run_step()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(self.origin_head(), self.initial)
        self.assertEqual(effects, "pushed=true\n")

    def test_refuses_tracked_change_outside_committed_paths(self):
        (self.work / "data" / "catalog.jsonl").write_text('{"id":"x"}\n')
        (self.work / "scripts" / "build.py").write_text("raise SystemExit\n")
        result, effects = self.run_step()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scripts/build.py", result.stdout)
        self.assertEqual((self.origin_head(), effects), (self.initial, ""))

    def test_refuses_untracked_file_outside_committed_paths(self):
        (self.work / "data" / "catalog.jsonl").write_text('{"id":"x"}\n')
        (self.work / "schemas").mkdir()
        (self.work / "schemas" / "new.schema.json").write_text("{}\n")
        result, effects = self.run_step()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("schemas/new.schema.json", result.stdout)
        self.assertEqual((self.origin_head(), effects), (self.initial, ""))

    def test_unchanged_scan_neither_commits_nor_reports_a_push(self):
        result, effects = self.run_step()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.origin_head(), effects), (self.initial, ""))


if __name__ == "__main__":
    unittest.main()
