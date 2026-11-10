"""Keep authored schedules, freshness expectations and public cadence aligned."""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import site_config  # noqa: E402

# Scan start to the scanned data being live on the website (GOAL U3).
LIVE_WITHIN_MINUTES = 150


def cron_field(text, limit):
    """Values of one cron field: '*', 'a', 'a-b', any of them with '/step', and comma lists."""
    values = set()
    for part in text.split(','):
        base, _, step = part.partition('/')
        if base == '*':
            start, stop = 0, limit - 1
        else:
            first, _, last = base.partition('-')
            start, stop = int(first), int(last or first)
        step = int(step or 1)
        if not 0 <= start <= stop < limit or step < 1:
            raise ValueError('Invalid cron field ' + part)
        values.update(range(start, stop + 1, step))
    return sorted(values)


def daily_slots(expression):
    minute, hours, day, month, weekday = expression.split()
    if (day, month, weekday) != ('*', '*', '*'):
        raise ValueError('Expected every-day cadence')
    return sorted(hour * 60 + m for hour in cron_field(hours, 24) for m in cron_field(minute, 60))


def gaps(slots):
    return [b - a for a, b in zip(slots, slots[1:] + [slots[0] + 1440])]


def workflow_schedule(path):
    text = path.read_text()
    slots = re.findall(r"^    - cron: '([^']+)'\n      timezone: (\S+)\s*$", text, re.M)
    if len(slots) != 1:
        raise ValueError('Expected one explicitly zoned schedule entry')
    return slots[0]


def job_timeout(path, job):
    text = path.read_text()
    body = re.split(r'^  [\w-]+:\n', text.split(f'\n  {job}:\n', 1)[1], maxsplit=1, flags=re.M)[0]
    return int(re.search(r'^    timeout-minutes: (\d+)$', body, re.M).group(1))


class ScanScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / 'data/scan-config.json').read_text())

    def test_source_and_publication_match_configured_utc_slots(self):
        self.assertEqual(self.config['timezone'], 'UTC')
        for workflow, key in [('.github/workflows/scan.yml', 'scan_cron'), ('automation/publish.yml', 'publish_cron')]:
            with self.subTest(workflow=workflow):
                self.assertEqual(workflow_schedule(ROOT / workflow), (self.config[key], self.config['timezone']))
        times = [f'{slot // 60:02d}:{slot % 60:02d}' for slot in daily_slots(self.config['scan_cron'])]
        self.assertEqual(times, self.config['scan_times_local'])
        minute, hours = self.config['publish_cron'].split()[:2]
        self.assertEqual((cron_field(minute, 60), hours), (self.config['publish_check_minutes'], '*'))

    def test_scans_run_every_eight_hours_at_minute_seven(self):
        self.assertEqual(self.config['scan_cron'], '7 */8 * * *')
        slots = daily_slots(self.config['scan_cron'])
        self.assertEqual((len(slots), set(gaps(slots))), (3, {480}))
        self.assertEqual(site_config.scan_schedule(self.config), 'at 00:07, 08:07 and 16:07 UTC')
        self.assertEqual(site_config.scan_schedule({'scan_times_local': ['08:17', '20:17'], 'timezone': 'UTC'}), 'at 08:17, 20:17 UTC')

    def test_publication_checks_reach_the_site_within_the_bound_after_each_scan(self):
        scans = daily_slots(self.config['scan_cron'])
        checks = daily_slots(self.config['publish_cron'])
        self.assertEqual(set(gaps(checks)), {30})
        publication = ROOT / 'automation/publish.yml'
        scan_timeout = job_timeout(ROOT / '.github/workflows/scan.yml', 'scan')
        self.assertLessEqual(scan_timeout, 60)
        # A scan that ends within its timeout is picked up by the next check, then validated, built and deployed.
        worst = scan_timeout + max(gaps(checks)) + sum(job_timeout(publication, job) for job in ('gate', 'build', 'deploy'))
        self.assertLessEqual(worst, LIVE_WITHIN_MINUTES)
        for scan in scans:
            self.assertTrue(any(0 < (check - scan) % 1440 <= 60 for check in checks), scan)
        text = publication.read_text()
        gate = text.index('name: Validate source data and website behavior')
        deployment = text.index('name: Build website from the verified catalog')
        self.assertLess(gate, deployment)
        for check in ['python scripts/catalog.py validate', 'python scripts/catalog.py build --check',
                      'python scripts/run_tests.py', 'node --test tests/web.test.mjs']:
            self.assertIn(check, text[gate:deployment])

    def test_freshness_limit_tolerates_missed_slots_after_an_uncommitted_scan(self):
        interval = gaps(daily_slots(self.config['scan_cron']))[0] / 60
        # A healthy scan with nothing new commits nothing until its receipt reaches the heartbeat. After that, two
        # scheduled intervals plus an hour of GitHub delay; a longer gap is stale and dispatches a recovery scan.
        heartbeat = self.config['scan_commit_heartbeat_hours']
        self.assertEqual(heartbeat, interval)
        self.assertEqual(self.config['max_scan_age_hours'], heartbeat + 1)
        # Counted in scans, so these hold a partial-scan alert to about eight hours and the receipts to about 15 days.
        self.assertEqual(self.config['max_consecutive_partial'], 3)
        self.assertEqual(self.config['history_limit'], 45)
        self.assertEqual(self.config['recent_lookback_days'], 14)
        self.assertEqual(self.config['recent_max_results'], 500)
        self.assertEqual(self.config['harvest_limit'], 500)
        freshness = (ROOT / '.github/workflows/freshness.yml').read_text()
        self.assertIn("cron: '37 */8 * * *'", freshness)

    def test_public_copy_has_no_stale_schedule_claim(self):
        paths = ['README.md', 'README.zh-CN.md', 'AGENTS.md', 'CONTRIBUTING.md', 'docs/maintenance.md',
                 'docs/methodology.md', 'docs/website.md', 'scripts/search_pages.py', 'scripts/agent_pages.py',
                 'scripts/prepare_publication.py', 'scripts/home_page.py', 'web/app.js', '.github/workflows/scan.yml', '.github/workflows/freshness.yml']
        stale = re.compile(r'twice[ -]daily|twice a day|both daily|both scheduled|three times (a day|daily)|three[ -]daily|'
                           r'3 runs daily|eight hours apart|90 minutes after|每日两次|每日计划执行两次|每日执行三次|'
                           r'01:47|09:47|17:47|every two hours|two-hourly|每两小时', re.I)
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNone(stale.search((ROOT / path).read_text()))
        self.assertIn('at 00:07, 08:07 and 16:07 UTC', (ROOT / 'README.md').read_text())
        self.assertIn('每天 00:07、08:07 和 16:07（UTC）', (ROOT / 'README.zh-CN.md').read_text())
        checks = ' and '.join(f':{minute:02d}' for minute in self.config['publish_check_minutes'])
        self.assertIn(checks, (ROOT / 'docs/maintenance.md').read_text())
        self.assertIn(checks, (ROOT / 'docs/website.md').read_text())


if __name__ == '__main__':
    unittest.main()
