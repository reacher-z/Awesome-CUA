import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scan

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "scan.yml"
CONFIG = {'recent_lookback_days': 14, 'recent_max_results': 500, 'harvest_limit': 500, 'history_limit': 10,
          'timezone': 'UTC', 'scan_times_local': ['08:17', '20:17'], 'policy': 'Fixture'}
RATE_LIMITED = {'name': 'recent_arxiv', 'ok': False, 'rate_limited': True, 'warnings': ['HTTP Error 429: Unknown Error']}


class PartialScanReportingTests(unittest.TestCase):
    def scan(self, recent=RATE_LIMITED, errors=None, history=(), actions=True, **config):
        """Run one scan with stubbed stages; return its exit code, stdout, step output and step summary."""
        errors = errors or {}
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(scan, 'DATA', Path(directory)):
            path = Path(directory)
            scan.write_json(path / 'scan-config.json', {**CONFIG, **config})
            scan.write_json(path / 'discovery-runs.json', [{'id': 'current', 'ok': True}])
            scan.write_jsonl(path / 'scan-history.jsonl', [{'id': f'scan:2026-09-{10 + i}T00:00:00Z', 'status': s} for i, s in enumerate(history)])
            def stage(name, command, timeout=600):
                return {'name': name, 'ok': name not in errors, 'error': errors.get(name), 'started_at': '2026-10-17T00:00:00Z'}
            env = {'GITHUB_STEP_SUMMARY': str(path / 'summary.md') if actions else '', 'GITHUB_OUTPUT': str(path / 'output') if actions else ''}
            out = io.StringIO()
            with mock.patch.object(scan, 'stage', side_effect=stage), mock.patch.object(scan, 'recent_phase', return_value=recent), \
                    mock.patch.dict(scan.os.environ, env), contextlib.redirect_stdout(out):
                code = scan.run_scan()
            read = lambda name: (path / name).read_text() if (path / name).exists() else ''
            self.status = scan.read_json(path / 'scan-status.json')['status']
            return code, out.getvalue(), read('output'), read('summary.md')

    def test_a_partial_scan_warns_once_per_problem_and_still_succeeds(self):
        code, stdout, output, summary = self.scan()
        self.assertEqual((code, self.status, output), (0, 'partial', ''))
        warnings = [line for line in stdout.splitlines() if line.startswith('::warning title=Scan partial::')]
        self.assertIn('::warning title=Scan partial::HTTP Error 429: Unknown Error', warnings)
        self.assertIn('- HTTP Error 429: Unknown Error', stdout.splitlines())
        self.assertIn('- HTTP Error 429: Unknown Error', summary)
        self.assertEqual(len(warnings), sum(line.startswith('- ') for line in summary.splitlines()))
        self.assertNotIn('::error', stdout)

    def test_a_multiline_problem_is_one_escaped_annotation(self):
        recent = {'name': 'recent_arxiv', 'ok': True, 'complete': True, 'warnings': []}
        _, stdout, _, _ = self.scan(recent=recent, errors={'discovery': 'Traceback\nHTTP Error 429: 100% used'})
        self.assertIn('::warning title=Scan partial::discovery: Traceback%0AHTTP Error 429: 100%25 used', stdout.splitlines())

    def test_a_failed_scan_reports_errors(self):
        code, stdout, _, _ = self.scan(errors={'discovery': 'down'})
        self.assertEqual((code, self.status), (1, 'failed'))
        self.assertIn('::error title=Scan failed::discovery: down', stdout.splitlines())
        self.assertNotIn('::warning', stdout)

    def test_outside_actions_problems_are_printed_without_workflow_commands(self):
        code, stdout, output, _ = self.scan(actions=False, history=['partial'] * 5, max_consecutive_partial=4)
        self.assertEqual((code, output), (0, ''))
        self.assertIn('- HTTP Error 429: Unknown Error', stdout.splitlines())
        self.assertIn('- The last 6 scans were all partial; the recorded gaps are not clearing on their own.', stdout.splitlines())
        self.assertNotIn('::', stdout)

    def test_consecutive_partial_scans_request_a_failed_run_after_committing(self):
        code, stdout, output, summary = self.scan(history=['success', 'partial', 'partial', 'partial'], max_consecutive_partial=4)
        self.assertEqual((code, self.status, output), (0, 'partial', 'repeated_partial=true\n'))
        self.assertIn('::error title=Repeated partial scans::The last 4 scans were all partial; the recorded gaps are not clearing on their own.', stdout.splitlines())
        self.assertIn('- The last 4 scans were all partial', summary)

    def test_a_success_or_failure_resets_the_partial_streak(self):
        for history in (['partial', 'partial', 'success', 'partial'], ['partial', 'partial', 'failed', 'partial'], ['partial'] * 2):
            with self.subTest(history=history):
                code, stdout, output, _ = self.scan(history=history, max_consecutive_partial=4)
                self.assertEqual((code, output), (0, ''))
                self.assertNotIn('Repeated partial scans', stdout)
        self.assertEqual(self.scan(history=['partial'] * 9)[2], '', 'no limit configured')

    def test_the_configured_limit_is_set(self):
        self.assertEqual(scan.read_json(ROOT / 'data' / 'scan-config.json')['max_consecutive_partial'], 4)


class RepeatedPartialWorkflowTests(unittest.TestCase):
    def test_a_separate_job_fails_the_run_only_after_the_scan_job_succeeds(self):
        text = WORKFLOW.read_text()
        self.assertIn('      - name: Discover and verify public metadata\n        id: scan\n        run: python scripts/scan.py\n', text)
        self.assertIn('      repeated_partial: ${{ steps.scan.outputs.repeated_partial }}\n', text.split('    steps:', 1)[0])
        job = text.split('\n  report_repeated_partial:\n', 1)[1]
        self.assertIn('    needs: scan\n', job)
        self.assertIn("    if: needs.scan.outputs.repeated_partial == 'true'\n", job)
        self.assertNotIn('permissions', job)
        self.assertNotIn('uses:', job)
        self.assertTrue(job.rstrip().endswith('exit 1'))


if __name__ == '__main__':
    unittest.main()
