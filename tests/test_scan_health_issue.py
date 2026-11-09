"""The scan workflow keeps one tracking issue for unhealthy scans of main and closes it after a healthy run."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "scan.yml"
STEP = "Update the scan health tracking issue"
RUN_URL = "https://github.com/owner/repo/actions/runs/42"
# Answers the issue, label and jobs commands the step uses and records every call and uploaded body.
FAKE_GH = r"""#!/bin/sh
printf '%s\n' "$*" >> "$GH_LOG"
case "$1 $2" in
  "issue list") printf '%s\n' "$GH_OPEN" ;;
  "issue view") printf '%s\n' "$GH_BODY" ;;
  "api repos/owner/repo/actions/runs/42/jobs") printf '%s\n' "$GH_FAILING" ;;
esac
previous=
for argument in "$@"; do
  if [ "$previous" = --body-file ]; then cat "$argument" > "$GH_UPLOADED"; fi
  previous=$argument
done
"""


def job(name):
    return WORKFLOW.read_text().split(f"\n  {name}:\n", 1)[1].split("\n  report_", 1)[0]


def step_script():
    lines = WORKFLOW.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {STEP}")
    run = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body = []
    for line in lines[run + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= 8:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)).strip("\n") + "\n"


class ScanHealthJobTests(unittest.TestCase):
    def test_job_runs_after_every_scan_of_main_with_only_issue_and_run_read_access(self):
        text = job("track_scan_health")
        self.assertIn("    needs: scan\n", text)
        self.assertIn("    if: always() && github.ref == 'refs/heads/main' && !inputs.dry_run\n", text)
        self.assertIn("    permissions:\n      actions: read\n      issues: write\n    steps:\n", text)
        self.assertNotIn("uses:", text)
        self.assertNotIn("contents:", text)
        for line in ["SCAN_RESULT: ${{ needs.scan.result }}", "SCAN_STATUS: ${{ needs.scan.outputs.status }}",
                     "SCAN_NOTES: ${{ needs.scan.outputs.notes }}", "REPEATED_PARTIAL: ${{ needs.scan.outputs.repeated_partial }}"]:
            self.assertIn(line, text)
        # Untrusted text reaches the script only through the environment, never by expression substitution.
        self.assertNotIn("${{", step_script())

    def test_scan_job_exposes_its_receipt_status_and_gaps(self):
        outputs = WORKFLOW.read_text().split("\n    outputs:\n", 1)[1].split("\n    steps:", 1)[0]
        self.assertIn("status: ${{ steps.scan.outputs.status }}", outputs)
        self.assertIn("notes: ${{ steps.scan.outputs.notes }}", outputs)


@unittest.skipUnless(shutil.which("bash"), "bash is required to run the workflow step")
class ScanHealthStepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.tmp / "bin").mkdir()
        (self.tmp / "bin" / "gh").write_text(FAKE_GH)
        (self.tmp / "bin" / "gh").chmod(0o755)
        self.log, self.uploaded = self.tmp / "gh.log", self.tmp / "uploaded.md"

    def run_step(self, result, status="", notes="", repeated="", open_issues="", body="", failing=""):
        env = {**os.environ, "PATH": f"{self.tmp / 'bin'}{os.pathsep}{os.environ['PATH']}", "GH_LOG": str(self.log),
               "GH_UPLOADED": str(self.uploaded), "GH_OPEN": open_issues, "GH_BODY": body, "GH_FAILING": failing,
               "GH_TOKEN": "token", "GITHUB_REPOSITORY": "owner/repo", "GITHUB_RUN_ID": "42", "GITHUB_EVENT_NAME": "schedule",
               "RUNNER_TEMP": str(self.tmp), "RUN_URL": RUN_URL, "SCAN_RESULT": result, "SCAN_STATUS": status,
               "SCAN_NOTES": notes, "REPEATED_PARTIAL": repeated}
        completed = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step_script()],
                                   env=env, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return [call.split(" -R owner/repo")[0] for call in calls], self.uploaded.read_text() if self.uploaded.exists() else None

    def test_a_healthy_run_closes_the_open_tracking_issue(self):
        calls, body = self.run_step("success", status="partial", open_issues="7")
        self.assertEqual(calls[1:], ["issue close 7"])
        self.assertIsNone(body)
        self.assertIn(f"--comment Resolved by {RUN_URL}: the scan job succeeded with status `partial`.", self.log.read_text())

    def test_a_healthy_run_without_an_open_issue_changes_nothing(self):
        calls, body = self.run_step("success", status="success")
        self.assertEqual(calls, ["issue list"])
        self.assertIsNone(body)

    def test_the_first_unhealthy_run_opens_one_labelled_issue_with_the_failure(self):
        calls, body = self.run_step("failure", status="failed", notes="discovery: down\nharvest: deferred",
                                    failing="scan (Check generated data and review boundaries)")
        self.assertEqual([call.split()[:2] for call in calls], [["issue", "list"], ["api", "repos/owner/repo/actions/runs/42/jobs"],
                                                                ["label", "create"], ["issue", "create"]])
        self.assertIn("issue create -R owner/repo --title Scheduled discovery scan is unhealthy --label scan-health --body-file", self.log.read_text())
        self.assertTrue(body.startswith("<!-- scan-health unhealthy_runs=1 since="))
        self.assertIn(f"- Latest unhealthy run: {RUN_URL} (schedule, ", body)
        self.assertIn("- Scan job: `failure`; scan status: `failed`; repeated partial scans: `false`", body)
        self.assertIn("- Failing jobs and steps: scan (Check generated data and review boundaries)", body)
        self.assertIn("```text\ndiscovery: down\nharvest: deferred\n```", body)

    def test_later_unhealthy_runs_edit_the_oldest_issue_in_place_and_close_duplicates(self):
        previous = "<!-- scan-health unhealthy_runs=3 since=2026-11-05T00:39:00Z -->\nThe scheduled discovery scan..."
        calls, body = self.run_step("success", status="partial", repeated="true", open_issues="7 9", body=previous,
                                    notes="The last 5 scans were all partial; the recorded gaps are not clearing on their own.")
        self.assertEqual([call.split()[:2] for call in calls],
                         [["issue", "list"], ["api", "repos/owner/repo/actions/runs/42/jobs"], ["issue", "view"], ["issue", "edit"], ["issue", "close"]])
        self.assertEqual([call for call in calls if call.startswith("issue ") and call != "issue list"], ["issue view 7", "issue edit 7", "issue close 9"])
        self.assertNotIn("issue create", "\n".join(calls))
        self.assertTrue(body.startswith("<!-- scan-health unhealthy_runs=4 since=2026-11-05T00:39:00Z -->\n"))
        self.assertIn("repeated partial scans: `true`", body)
        self.assertIn("- Consecutive unhealthy runs: 4 since 2026-11-05T00:39:00Z", body)
        self.assertIn("--comment Duplicate of #7, which tracks scan health.", self.log.read_text())

    def test_recorded_gaps_cannot_break_out_of_their_code_block(self):
        _, body = self.run_step("failure", notes="fetch failed ```\n@someone [link](https://example.org) $(touch pwned)")
        fence = body.split("```text\n", 1)[1]
        self.assertEqual(fence.count("```"), 1)
        self.assertIn("@someone [link](https://example.org) $(touch pwned)\n```", fence)
        self.assertFalse((self.tmp / "pwned").exists())
        self.assertTrue(re.search(r"scan status: `not recorded`", body))


if __name__ == "__main__":
    unittest.main()
