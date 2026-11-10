#!/usr/bin/env python3
"""Write the shields.io endpoint JSON for the README's last-successful-scan badge.

A successful scan is a run of .github/workflows/scan.yml on main that concluded
``success``: every scan check passed and the repeated-partial alert did not fire.
A healthy scan with nothing new commits nothing and still counts. The badge shows
when the latest such run finished, in UTC, and turns the warning colour once that
is more than MAX_AGE_HOURS old: one eight-hour scan interval plus an hour, the
threshold of the operators' stale-scan alert.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

LABEL = 'last successful scan'
# The README badge colour (indigo) and an amber warning colour.
NORMAL = '4352E8'
WARNING = 'B45309'
MAX_AGE_HOURS = 9


def parse_time(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)


def last_success(runs):
    finished = [parse_time(run['updated_at']) for run in runs
                if run.get('status') == 'completed' and run.get('conclusion') == 'success'
                and run.get('head_branch') == 'main' and run.get('updated_at')]
    return max(finished, default=None)


def badge(runs, now):
    last = last_success(runs)
    if last is None:
        return {'schemaVersion': 1, 'label': LABEL, 'message': 'none', 'color': WARNING}
    stale = now - last > timedelta(hours=MAX_AGE_HOURS)
    return {'schemaVersion': 1, 'label': LABEL, 'message': last.strftime('%Y-%m-%d %H:%M UTC'),
            'color': WARNING if stale else NORMAL}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Write the last-successful-scan badge endpoint JSON.')
    parser.add_argument('--runs', required=True, help='JSON from GET /repos/{repo}/actions/workflows/scan.yml/runs')
    parser.add_argument('--output', required=True, help='endpoint JSON to write')
    parser.add_argument('--now', help='current UTC time (ISO 8601); defaults to the clock')
    args = parser.parse_args(argv)
    runs = json.loads(Path(args.runs).read_text(encoding='utf-8')).get('workflow_runs')
    if not isinstance(runs, list):
        parser.error('--runs has no workflow_runs list')
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    endpoint = badge(runs, now)
    Path(args.output).write_text(json.dumps(endpoint, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f"{endpoint['label']}: {endpoint['message']} ({endpoint['color']})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
