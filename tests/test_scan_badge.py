"""The scan badge shows the latest successful scan of main and turns amber after six hours."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import scan_badge  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "scan-badge.yml"
NOW = datetime(2026, 11, 9, 18, 0, tzinfo=timezone.utc)


def run(updated, conclusion="success", branch="main", status="completed"):
    return {"updated_at": updated, "conclusion": conclusion, "head_branch": branch, "status": status}


def step_script(name):
    lines = WORKFLOW.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {name}")
    index = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body = []
    for line in lines[index + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= 8:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)).strip("\n") + "\n"


class BadgeTests(unittest.TestCase):
    def test_latest_successful_run_of_main_sets_the_message(self):
        runs = [run("2026-11-09T16:47:39Z"), run("2026-11-09T17:30:00Z", conclusion="failure"),
                run("2026-11-09T17:40:00Z", branch="topic"), run("2026-11-09T17:50:00Z", status="in_progress"),
                run("2026-11-09T08:47:00Z")]
        self.assertEqual(scan_badge.badge(runs, NOW), {"schemaVersion": 1, "label": "last successful scan",
                                                       "message": "2026-11-09 16:47 UTC", "color": "4352E8"})

    def test_turns_amber_after_six_hours(self):
        self.assertEqual(scan_badge.badge([run("2026-11-09T12:00:00Z")], NOW)["color"], "4352E8")
        stale = scan_badge.badge([run("2026-11-09T11:59:00Z")], NOW)
        self.assertEqual((stale["message"], stale["color"]), ("2026-11-09 11:59 UTC", "B45309"))

    def test_no_successful_run_is_a_warning(self):
        self.assertEqual(scan_badge.badge([run("2026-11-09T17:00:00Z", conclusion="failure")], NOW),
                         {"schemaVersion": 1, "label": "last successful scan", "message": "none", "color": "B45309"})

    def test_command_line_writes_compact_endpoint_json(self):
        with tempfile.TemporaryDirectory() as directory:
            runs, output = Path(directory) / "runs.json", Path(directory) / "badge.json"
            runs.write_text(json.dumps({"total_count": 1, "workflow_runs": [run("2026-11-09T16:47:39Z")]}))
            self.assertEqual(scan_badge.main(["--runs", str(runs), "--output", str(output), "--now", "2026-11-09T23:00:00Z"]), 0)
            self.assertEqual(output.read_text(), '{"schemaVersion":1,"label":"last successful scan","message":"2026-11-09 16:47 UTC","color":"B45309"}\n')


class WorkflowTests(unittest.TestCase):
    def test_runs_hourly_after_each_scan_and_on_dispatch(self):
        text = WORKFLOW.read_text()
        self.assertIn("    - cron: '47 * * * *'\n", text)
        self.assertIn("  workflow_dispatch:\n", text)
        scan_name = (ROOT / ".github/workflows/scan.yml").read_text().splitlines()[0].removeprefix("name: ")
        self.assertIn(f"    workflows: [{scan_name}]\n    types: [completed]\n    branches: [main]\n", text)
        self.assertIn("permissions: {}\n", text)
        self.assertIn("    permissions:\n      actions: read\n      contents: write\n", text)
        self.assertIn("workflows/scan.yml/runs?branch=main&status=success", text)

    def test_readme_badge_reads_the_file_the_workflow_publishes(self):
        import build
        self.assertEqual(build.SCAN_BADGE_JSON, "https://raw.githubusercontent.com/reacher-z/Awesome-CUA/status/scan-badge.json")
        self.assertIn("HEAD:refs/heads/status", step_script("Publish the badge to the status branch"))
        self.assertIn("cp \"$RUNNER_TEMP/scan-badge.json\" scan-badge.json", step_script("Publish the badge to the status branch"))


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "bash and git run the publish step")
class PublishStepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.origin = self.tmp / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.origin)], check=True)
        config = self.tmp / "gitconfig"
        config.write_text(f'[url "{self.origin.as_uri()}"]\n\tinsteadOf = https://github.com/owner/repo.git\n')
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1", "GITHUB_REPOSITORY": "owner/repo",
                    "GH_TOKEN": "token", "RUNNER_TEMP": str(self.tmp / "runner")}
        (self.tmp / "runner").mkdir()

    def publish(self, message):
        (self.tmp / "runner" / "scan-badge.json").write_text(json.dumps({"schemaVersion": 1, "message": message}) + "\n")
        shutil.rmtree(self.tmp / "runner" / "status", ignore_errors=True)
        completed = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step_script("Publish the badge to the status branch")],
                                   env=self.env, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return completed.stdout

    def log(self):
        return subprocess.run(["git", "--git-dir", str(self.origin), "log", "--format=%an <%ae>|%cn|%P|%s", "status"],
                              capture_output=True, text=True, check=True).stdout.splitlines()

    def test_creates_an_orphan_branch_then_commits_only_changes(self):
        self.publish("2026-11-09 16:47 UTC")
        first = self.log()
        self.assertEqual(first, ["github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>|github-actions[bot]||Update the last successful scan badge"])
        self.assertIn("Badge unchanged", self.publish("2026-11-09 16:47 UTC"))
        self.assertEqual(self.log(), first)
        self.publish("2026-11-10 00:47 UTC")
        self.assertEqual(len(self.log()), 2)
        files = subprocess.run(["git", "--git-dir", str(self.origin), "ls-tree", "--name-only", "status"], capture_output=True, text=True, check=True).stdout
        self.assertEqual(files, "scan-badge.json\n")
        shown = subprocess.run(["git", "--git-dir", str(self.origin), "show", "status:scan-badge.json"], capture_output=True, text=True, check=True).stdout
        self.assertIn("2026-11-10 00:47 UTC", shown)


if __name__ == "__main__":
    unittest.main()
