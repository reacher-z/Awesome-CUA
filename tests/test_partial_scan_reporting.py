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


def step_outputs(text):
    """Parse a GITHUB_OUTPUT file: name=value lines and name<<DELIMITER blocks."""
    result, lines = {}, iter(text.splitlines())
    for line in lines:
        if '<<' in line and ('=' not in line or line.index('<<') < line.index('=')):
            name, delimiter = line.split('<<', 1)
            value = []
            for item in lines:
                if item == delimiter:
                    break
                value.append(item)
            else:
                raise AssertionError('unterminated multiline output ' + name)
            result[name] = '\n'.join(value)
        else:
            name, value = line.split('=', 1)
            result[name] = value
    return result


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
        self.assertEqual((code, self.status), (0, 'partial'))
        outputs = step_outputs(output)
        self.assertEqual(sorted(outputs), ['notes', 'status'])
        self.assertEqual(outputs['status'], 'partial')
        self.assertIn('HTTP Error 429: Unknown Error', outputs['notes'].splitlines())
        warnings = [line for line in stdout.splitlines() if line.startswith('::warning title=Scan partial::')]
        self.assertEqual(len(outputs['notes'].splitlines()), len(warnings))
        self.assertIn('::warning title=Scan partial::HTTP Error 429: Unknown Error', warnings)
        self.assertIn('- HTTP Error 429: Unknown Error', stdout.splitlines())
        self.assertIn('- HTTP Error 429: Unknown Error', summary)
        self.assertEqual(len(warnings), sum(line.startswith('- ') for line in summary.splitlines()))
        self.assertNotIn('::error', stdout)

    def test_a_multiline_problem_is_one_escaped_annotation(self):
        recent = {'name': 'recent_arxiv', 'ok': True, 'complete': True, 'warnings': []}
        _, stdout, output, _ = self.scan(recent=recent, errors={'discovery': 'Traceback\nHTTP Error 429: 100% used'})
        self.assertIn('::warning title=Scan partial::discovery: Traceback%0AHTTP Error 429: 100%25 used', stdout.splitlines())
        # A multiline problem cannot end the multiline step output early.
        self.assertIn('discovery: Traceback HTTP Error 429: 100% used', step_outputs(output)['notes'].splitlines())

    def test_a_failed_scan_reports_errors(self):
        code, stdout, output, _ = self.scan(errors={'discovery': 'down'})
        self.assertEqual((code, self.status), (1, 'failed'))
        self.assertEqual(step_outputs(output)['status'], 'failed')
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
        self.assertEqual((code, self.status, step_outputs(output)['repeated_partial']), (0, 'partial', 'true'))
        self.assertTrue(step_outputs(output)['notes'].endswith('The last 4 scans were all partial; the recorded gaps are not clearing on their own.'))
        self.assertIn('::error title=Repeated partial scans::The last 4 scans were all partial; the recorded gaps are not clearing on their own.', stdout.splitlines())
        self.assertIn('- The last 4 scans were all partial', summary)

    def test_a_success_or_failure_resets_the_partial_streak(self):
        for history in (['partial', 'partial', 'success', 'partial'], ['partial', 'partial', 'failed', 'partial'], ['partial'] * 2):
            with self.subTest(history=history):
                code, stdout, output, _ = self.scan(history=history, max_consecutive_partial=4)
                self.assertEqual(code, 0)
                self.assertNotIn('repeated_partial', step_outputs(output))
                self.assertNotIn('Repeated partial scans', stdout)
        self.assertNotIn('repeated_partial', step_outputs(self.scan(history=['partial'] * 9)[2]), 'no limit configured')

    def test_the_configured_limit_is_set(self):
        self.assertEqual(scan.read_json(ROOT / 'data' / 'scan-config.json')['max_consecutive_partial'], 4)


class ThrottlePauseTests(unittest.TestCase):
    def row(self, status='partial', state='rate_limited', progress=3, failed=2, warnings=None):
        return {'status': status, 'candidate_observations': {'state': state, 'successful_responses': progress, 'new_unique_repositories': 0},
                'source_fetches': {'successful': 100 - failed + 2, 'total': 102}, 'warnings': warnings if warnings is not None else [
                    'GitHub candidate observations paused for provider rate limiting; verified progress and cursor are retained.',
                    'Discovery sources failed: a, b']}

    def test_a_rate_limit_pause_that_moved_the_cursor_is_not_a_partial_scan_gap(self):
        self.assertTrue(scan.throttle_pause(self.row()))
        self.assertEqual(scan.partial_streak([self.row()] * 9), 0)
        self.assertEqual(scan.partial_streak([{'status': 'partial'}, self.row(), self.row(), {'status': 'partial'}]), 2)

    def test_a_pause_without_progress_still_counts(self):
        stalled = self.row(progress=0)
        self.assertFalse(scan.throttle_pause(stalled))
        self.assertEqual(scan.partial_streak([stalled] * 4), 4)

    def test_other_failures_still_count(self):
        for case in (self.row(failed=20), self.row(warnings=['build: failed']), self.row(state='bounded_progress'), self.row(status='failed')):
            with self.subTest(case=case):
                self.assertFalse(scan.throttle_pause(case))
        self.assertEqual(scan.partial_streak([self.row(failed=20)] * 4), 4)

    def test_a_success_still_ends_the_streak(self):
        self.assertEqual(scan.partial_streak([{'status': 'partial'}] * 3 + [{'status': 'success'}, self.row()]), 0)


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
