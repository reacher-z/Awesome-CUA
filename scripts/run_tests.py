#!/usr/bin/env python3
"""Run the unit suite in parallel worker processes.

Discovers the same tests as ``python -m unittest discover -s tests`` and runs
them in separate ``python -m unittest`` processes, one test class (or one
slice of a large site-building class) per process, several at a time. Each
unit keeps its class and module fixtures. The run fails when any unit fails,
when discovery reports an import error, or when the tests run differ from the
tests discovered.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / 'tests'
# Modules that build the whole website take minutes; they start first.
SLOW_MARKERS = ('build_site', 'build_static_site')
# A slow class with more methods than this is split, so one class does not set the wall time.
SLICE_METHODS = 4
GROUPS = os.environ.get('GITHUB_ACTIONS') == 'true'
RAN = re.compile(r'^Ran (\d+) tests? in ', re.M)


def iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def discover(start=TESTS, pattern='test*.py'):
    """Discovered test IDs in suite order, and the IDs of modules that failed to load."""
    loader = unittest.TestLoader()
    suite = loader.discover(str(start), pattern=pattern, top_level_dir=str(start))
    ids, broken = [], []
    for test in iter_tests(suite):
        if type(test).__module__ == 'unittest.loader' or isinstance(test, unittest.loader._FailedTest):
            broken.append(test.id())
        else:
            ids.append(test.id())
    broken += [str(error) for error in loader.errors]
    return ids, broken


def slow_modules(start, modules):
    slow = set()
    for module in modules:
        path = Path(start) / (module.replace('.', '/') + '.py')
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue
        if any(marker in text for marker in SLOW_MARKERS):
            slow.add(module)
    return slow


def plan(ids, slow):
    """Units of test IDs, slowest first; each unit is one class or an interleaved slice of one."""
    classes = {}
    for test_id in ids:
        module, cls, _ = test_id.rsplit('.', 2)
        classes.setdefault((module, cls), []).append(test_id)
    units = []
    for (module, _), tests in classes.items():
        parts = -(-len(tests) // SLICE_METHODS) if module in slow else 1
        units += [(module in slow, tests[index::parts]) for index in range(parts)]
    # Stable: slow units first, larger first, then discovery order.
    order = sorted(range(len(units)), key=lambda i: (not units[i][0], -len(units[i][1]), i))
    return [units[i][1] for i in order]


def run_unit(tests, start):
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(filter(None, [str(start), os.environ.get('PYTHONPATH')]))}
    began = time.monotonic()
    result = subprocess.run([sys.executable, '-m', 'unittest', '-v', *tests], cwd=ROOT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
    return result.returncode, result.stdout, time.monotonic() - began


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('-j', '--jobs', type=int, default=os.cpu_count() or 1, help='worker processes (default: CPU count)')
    parser.add_argument('-s', '--start', default=str(TESTS), help='test directory (default: tests)')
    parser.add_argument('-p', '--pattern', default='test*.py', help='test file pattern (default: test*.py)')
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error('--jobs must be at least 1')
    start = Path(args.start).resolve()
    sys.path.insert(0, str(start))
    began = time.monotonic()
    ids, broken = discover(start, args.pattern)
    if broken:
        print('Test discovery failed:', *broken, sep='\n', file=sys.stderr)
        return 1
    if not ids:
        print('No tests discovered in ' + str(start), file=sys.stderr)
        return 1
    units = plan(ids, slow_modules(start, {test_id.rsplit('.', 2)[0] for test_id in ids}))
    print(f'Running {len(ids)} tests in {len(units)} units with {args.jobs} workers', flush=True)
    failed, ran, timings = [], 0, []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_unit, tests, start): tests for tests in units}
        for future in as_completed(futures):
            tests = futures[future]
            code, output, seconds = future.result()
            counted = RAN.search(output)
            ran += int(counted.group(1)) if counted else 0
            label = tests[0].rsplit('.', 1)[0] + (f' ({len(tests)} tests)' if len(tests) > 1 else '')
            timings.append((seconds, label))
            status = 'ok' if code == 0 and counted else 'FAILED'
            if GROUPS:
                print(f'::group::{label}: {status} in {seconds:.1f}s', flush=True)
            else:
                print(f'== {label}: {status} in {seconds:.1f}s')
            print(output.rstrip('\n'))
            if GROUPS:
                print('::endgroup::')
            sys.stdout.flush()
            if code != 0 or not counted:
                failed.append(label)
    print('\nSlowest units:')
    for seconds, label in sorted(timings, reverse=True)[:10]:
        print(f'  {seconds:7.1f}s  {label}')
    print('-' * 70)
    print(f'Ran {ran} tests in {time.monotonic() - began:.3f}s with {args.jobs} workers')
    if ran != len(ids):
        print(f'Expected {len(ids)} tests from discovery; {ran} ran.', file=sys.stderr)
        failed.append('test count')
    if failed:
        print('FAILED: ' + '; '.join(failed))
        return 1
    print('OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
