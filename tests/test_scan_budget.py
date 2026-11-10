from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import catalog
import scan

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "scan.yml"
# Steps without their own timeout: job start, checkout, Python/Node setup and the hashed
# install (12-20 s on the runner), the snapshot, both evidence uploads and the notices.
UNTIMED_STEPS = 60
# scan.py work outside its stage timeouts: interpreter start, receipts, counts, history and
# the candidate integrity gate. 111 receipts from 16 Oct to 9 Nov 2026 record at most 96 s
# between phases, and the step adds about 20 s around the receipt.
SCAN_BOOKKEEPING = 120
# Minutes left under the job timeout when every step uses its whole budget.
MARGIN = 2 * 60
CONFIG = {'recent_lookback_days': 14, 'recent_max_results': 500, 'harvest_limit': 500, 'history_limit': 5,
          'timezone': 'UTC', 'scan_times_local': ['08:17', '20:17'], 'policy': 'Fixture'}


def scan_job():
    return re.search(r"^  scan:\n(.*?)(?=^  \S)", WORKFLOW.read_text(), re.M | re.S)[1]


def job_timeout():
    return int(re.search(r"^    timeout-minutes: (\d+)$", scan_job(), re.M)[1]) * 60


def step_timeouts():
    """Seconds allowed to each scan-job step that sets its own timeout, by step id."""
    return {step: int(minutes) * 60 for step, minutes in
            re.findall(r"^        id: (\w+)\n        timeout-minutes: (\d+)$", scan_job(), re.M)}


class ScanBudgetTests(unittest.TestCase):
    def test_stage_budgets_and_the_recent_search_fit_inside_the_job_timeout(self):
        config = catalog.read_json(ROOT / "data" / "scan-config.json")
        scan_seconds = config['network_max_seconds'] + sum(value for key,value in scan.STAGE_TIMEOUTS.items() if key not in scan.NETWORK_STAGES)
        steps = step_timeouts()
        self.assertEqual(set(steps), {"scan", "quality", "commit"})
        self.assertLessEqual(scan_seconds + SCAN_BOOKKEEPING, steps["scan"])
        self.assertLessEqual(UNTIMED_STEPS + sum(steps.values()) + MARGIN, job_timeout())
        self.assertLessEqual(job_timeout(), 30 * 60)

    def test_every_subprocess_stage_runs_under_its_own_budget(self):
        timeouts = []
        def run(command, **kwargs):
            timeouts.append((command[2] if command[1].endswith("catalog.py") else command[1], kwargs["timeout"]))
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(scan, "DATA", Path(directory)), \
                mock.patch.object(scan.subprocess, "run", side_effect=run), \
                mock.patch.object(scan, "recent_phase", return_value={"name": "recent_arxiv", "ok": True, "warnings": []}), \
                mock.patch.dict(scan.os.environ, {"GITHUB_STEP_SUMMARY": ""}):
            scan.write_json(Path(directory) / "scan-config.json", CONFIG)
            self.assertEqual(scan.run_scan(), 1)
            phases = {p["name"]: p for p in scan.read_json(Path(directory) / "scan-status.json")["phases"]}
        self.assertEqual([name for name, _ in timeouts], ["discover", "scripts/discover_papers.py", "harvest", "build", "validate"])
        self.assertTrue(all(359 < timeout <= 360 for _, timeout in timeouts[:3]), timeouts)
        self.assertEqual([timeout for _, timeout in timeouts[3:]], [90, 90])
        self.assertEqual(set(phases), set(scan.STAGE_TIMEOUTS))
        self.assertEqual(phases["harvest"]["error"], f"Stage exceeded {timeouts[2][1]:g} seconds; last verified records retained.")
        self.assertTrue(all(phases[name]['deferred'] for name in ('discovery','huggingface','harvest')))

    def test_an_interrupted_scan_leaves_its_own_running_receipt(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(scan, "DATA", Path(directory)), \
                mock.patch.dict(scan.os.environ, {"GITHUB_REPOSITORY": "o/r", "GITHUB_RUN_ID": "42", "GITHUB_STEP_SUMMARY": ""}):
            path = Path(directory)
            scan.write_json(path / "scan-config.json", CONFIG)
            scan.write_json(path / "scan-status.json", {"status": "success", "started_at": "2026-10-16T00:00:00Z",
                                                        "finished_at": "2026-10-16T00:01:00Z", "run_url": "https://github.com/o/r/actions/runs/1"})
            with mock.patch.object(scan, "stage", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
                scan.run_scan()
            receipt = scan.read_json(path / "scan-status.json")
        self.assertEqual((receipt["status"], receipt["finished_at"], receipt["run_url"]), ("running", None, "https://github.com/o/r/actions/runs/42"))
        self.assertEqual(receipt["id"], "scan:" + receipt["started_at"])
        self.assertNotEqual(receipt["started_at"], "2026-10-16T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
