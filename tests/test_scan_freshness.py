import contextlib
import datetime as dt
import io
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scan

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "freshness.yml"
NOW = dt.datetime(2026, 10, 17, 12, 0, tzinfo=dt.timezone.utc)


def ago(hours, current=NOW):
    return (current - dt.timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


class ScanFreshnessTests(unittest.TestCase):
    def check(self, status=None, history=(), actions=True, current=NOW, run=None):
        """Return the exit code, stdout and step output of one freshness check over the given receipts."""
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(scan, "DATA", Path(directory)):
            path = Path(directory)
            scan.write_json(path / "scan-config.json", {"max_scan_age_hours": 14})
            if status is not None:
                scan.write_json(path / "scan-status.json", status)
            scan.write_jsonl(path / "scan-history.jsonl", [{"id": f"scan:{row['finished_at']}", **row} for row in history])
            env = {"GITHUB_STEP_SUMMARY": str(path / "summary.md") if actions else "", "GITHUB_OUTPUT": str(path / "output") if actions else ""}
            stdout = io.StringIO()
            with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(stdout):
                code = run() if run else scan.check_freshness(current)
            output = path / "output"
            files = sorted(p.name for p in path.iterdir())
            return code, stdout.getvalue(), output.read_text() if output.exists() else "", files

    def test_recent_completed_scan_passes_quietly(self):
        code, stdout, output, _ = self.check({"status": "partial", "finished_at": ago(13.9)})
        self.assertEqual((code, output), (0, ""))
        self.assertEqual(stdout, f"The last completed scan finished at {ago(13.9)}, 13.9 h ago, within the 14 h limit.\n")

    def test_late_or_dropped_scan_fails_with_an_annotation_and_step_output(self):
        code, stdout, output, files = self.check({"status": "success", "finished_at": ago(16.5)})
        self.assertEqual((code, output), (1, "stale=true\n"))
        self.assertEqual(stdout, f"::error title=Stale scan::The last completed scan finished at {ago(16.5)}, 16.5 h ago; "
                                 "scans are expected at least every 14 h, so a scheduled scan was delayed or dropped.\n")
        self.assertEqual(files, ["output", "scan-config.json", "scan-history.jsonl", "scan-status.json"])

    def test_outside_actions_the_message_is_plain(self):
        code, stdout, output, _ = self.check({"status": "success", "finished_at": ago(20)}, actions=False)
        self.assertEqual((code, output), (1, ""))
        self.assertTrue(stdout.startswith("The last completed scan finished at"))

    def test_running_receipt_falls_back_to_the_last_completed_scan_in_history(self):
        running = {"status": "running", "started_at": ago(0.2), "finished_at": None}
        self.assertEqual(self.check(running, [{"status": "success", "finished_at": ago(30)}, {"status": "partial", "finished_at": ago(3)}])[0], 0)
        self.assertEqual(self.check(running, [{"status": "success", "finished_at": ago(30)}])[0], 1)

    def test_failed_scans_do_not_count_as_fresh(self):
        code, stdout, _, _ = self.check({"status": "failed", "finished_at": ago(1)}, [{"status": "success", "finished_at": ago(15)}])
        self.assertEqual(code, 1)
        self.assertIn(f"finished at {ago(15)}, 15.0 h ago", stdout)

    def test_missing_receipts_are_stale(self):
        code, stdout, output, _ = self.check()
        self.assertEqual((code, output), (1, "stale=true\n"))
        self.assertIn("No completed scan is recorded", stdout)

    def test_cli_flag_checks_freshness_without_scanning(self):
        current = dt.datetime.now(dt.timezone.utc)
        with mock.patch.object(scan, "run_scan", side_effect=AssertionError("scan started")) as run_scan:
            fresh = self.check({"status": "success", "finished_at": ago(1, current)}, run=lambda: scan.main(["--check-freshness"]))
            stale = self.check({"status": "success", "finished_at": ago(15, current)}, run=lambda: scan.main(["--check-freshness"]))
        run_scan.assert_not_called()
        self.assertEqual((fresh[0], stale[0], stale[2]), (0, 1, "stale=true\n"))

    def test_configured_limit_allows_one_scheduled_interval_plus_slack(self):
        config = scan.read_json(ROOT / "data" / "scan-config.json")
        self.assertEqual(config["scan_times_local"], [f"{hour:02d}:07" for hour in (0, 8, 16)])
        self.assertEqual(config["max_scan_age_hours"], 9)


class FreshnessWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text()
        parts = re.split(r"^  ([\w-]+):\n", self.text.split("\njobs:\n", 1)[1], flags=re.M)
        self.jobs = dict(zip(parts[1::2], parts[2::2]))

    def test_runs_on_a_schedule_and_on_demand(self):
        self.assertIn("  schedule:\n", self.text)
        self.assertRegex(self.text, r"    - cron: '\d+ \*/8 \* \* \*'\n")
        self.assertIn("  workflow_dispatch:\n", self.text)
        self.assertIn("\npermissions: {}\n", self.text)

    def test_check_job_only_reads_and_reports_staleness(self):
        check = self.jobs["check"]
        self.assertIn("permissions:\n      contents: read\n", check)
        self.assertIn("stale: ${{ steps.freshness.outputs.stale }}", check)
        self.assertIn("id: freshness\n        run: python scripts/scan.py --check-freshness\n", check)
        self.assertIn("persist-credentials: false", check)
        self.assertNotIn("github.token", check)

    def test_stale_check_dispatches_one_recovery_scan_from_a_job_without_checkout(self):
        dispatch = self.jobs["dispatch_scan"]
        self.assertIn("needs: check\n", dispatch)
        self.assertIn("if: always() && needs.check.outputs.stale == 'true'\n", dispatch)
        self.assertIn("permissions:\n      actions: write\n", dispatch)
        self.assertNotIn("uses:", dispatch)
        self.assertIn('gh workflow run scan.yml --ref main -R "$GITHUB_REPOSITORY"', dispatch)
        # A queued or running scan suppresses the recovery dispatch.
        self.assertIn('--workflow scan.yml --limit 20 --json status --jq \'[.[] | select(.status != "completed")] | length\'', dispatch)
        self.assertLess(dispatch.index('if [ "$active" -gt 0 ]'), dispatch.index("gh workflow run scan.yml"))
        self.assertEqual(self.text.count("actions: write"), 1)


if __name__ == "__main__":
    unittest.main()
