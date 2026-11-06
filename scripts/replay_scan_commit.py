#!/usr/bin/env python3
"""Replay the scan commit onto a moved main, keeping both sides' data.

Build outputs take main's version; the scan workflow rebuilds them afterwards from both sides' inputs. Files only the scan
keeps current take the scan's version. Row-based inputs merge by record id. Any other conflict stops the replay.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

# Receipts and the bound candidate triplet: each is one complete snapshot written by the scan.
SCAN_OWNED = frozenset({
    'data/discovery-runs.json', 'data/github-candidate-progress.json', 'data/github-candidates-manifest.json',
    'data/github-candidates.jsonl', 'data/harvest-failures.jsonl', 'data/paper-discovery-status.json',
    'data/recent-paper-search.json', 'data/research-discovery.json', 'data/scan-history.jsonl', 'data/scan-status.json'})
ROW_MERGED = frozenset({'data/candidates.jsonl', 'data/metadata-updates.jsonl', 'data/papers.jsonl'})


def git(*args, check=True):
    return subprocess.run(['git', *args], check=check, capture_output=True, text=True)


def build_outputs():
    """Every path the catalog build writes. Other lines it prints never match a path that git reports as conflicted."""
    result = subprocess.run([sys.executable, 'scripts/catalog.py', 'build', '--list-outputs'], check=True, capture_output=True, text=True)
    return set(result.stdout.splitlines())


def take(path, revision):
    if git('cat-file', '-e', f'{revision}:{path}', check=False).returncode == 0:
        git('checkout', revision, '--', path)
    else:
        git('rm', '-qf', '--', path)


def stage_rows(stage, path):
    blob = git('show', f':{stage}:{path}', check=False)
    return {row['id']: row for row in map(json.loads, blob.stdout.splitlines())} if blob.returncode == 0 else {}


def merge_rows(base, main, scan):
    """Three-way merge by id. A row main changed stays as main has it: the next scan reads its sources again."""
    merged = {rid: scan.get(rid) if main.get(rid) == base.get(rid) else main.get(rid) for rid in {*base, *main, *scan}}
    return {rid: row for rid, row in merged.items() if row is not None}


def write_rows(path, rows):
    # The same bytes as catalog.write_jsonl.
    text = ''.join(json.dumps(rows[rid], ensure_ascii=False, sort_keys=True) + '\n' for rid in sorted(rows))
    Path(path).write_text(text, encoding='utf-8')
    git('add', '--', path)


def replay(upstream):
    outputs = build_outputs()
    upstream = git('rev-parse', upstream).stdout.strip()
    if git('rebase', upstream, check=False).returncode == 0:
        return []
    conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.splitlines()
    unresolved = [path for path in conflicts if path not in outputs | SCAN_OWNED | ROW_MERGED]
    if not conflicts or unresolved:
        git('rebase', '--abort', check=False)
        return unresolved or ['the rebase stopped without a conflicted file']
    for path in conflicts:
        if path in outputs:
            take(path, upstream)
        elif path in SCAN_OWNED:
            take(path, 'REBASE_HEAD')
        else:
            write_rows(path, merge_rows(*(stage_rows(stage, path) for stage in (1, 2, 3))))
    finished = git('-c', 'core.editor=true', 'rebase', '--continue', check=False)
    if finished.returncode:
        git('rebase', '--abort', check=False)
        return [finished.stderr.strip() or 'the rebase did not continue']
    return []


def main(argv):
    problems = replay(argv[0])
    for problem in problems:
        print('Not replayed: ' + problem)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
