#!/usr/bin/env python3
"""Retain verified public data before a scan's Git commit can conflict."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root)


def package_snapshot(root, output, *, quality_outcome, repository="", run_id=""):
    """Copy tracked JSON/JSONL bytes only; never include caches or local files."""
    root, output = Path(root).resolve(), Path(output)
    if quality_outcome != "success":
        raise ValueError("A successful workflow quality gate is required")
    if output.exists() or output.is_symlink():
        raise ValueError("Snapshot output must be a new directory")
    if (root / "data").is_symlink():
        raise ValueError("Public data directory must not be a symbolic link")
    run_url = None
    if repository or run_id:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not re.fullmatch(r"[0-9]+", run_id):
            raise ValueError("Invalid workflow identity")
        run_url = f"https://github.com/{repository}/actions/runs/{run_id}"
    status = json.loads((root / "data/scan-status.json").read_bytes())
    if status.get("status") not in {"success", "partial"} or not status.get("finished_at"):
        raise ValueError("A completed successful or partial scan receipt is required")
    if run_url and status.get("run_url") != run_url:
        raise ValueError("Scan receipt belongs to another workflow run")

    checkout_commit = git(root, "rev-parse", "HEAD").decode().strip()
    entries = git(root, "ls-tree", "-rz", "HEAD", "--", "data").split(b"\0")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".scan-snapshot-", dir=output.parent))
    try:
        files = []
        for entry in entries:
            if not entry:
                continue
            metadata, raw_path = entry.split(b"\t", 1)
            mode, object_type, blob = metadata.decode().split()
            relative = Path(raw_path.decode("utf-8"))
            if relative.suffix not in {".json", ".jsonl"}:
                continue
            if object_type != "blob" or mode not in {"100644", "100755"}:
                raise ValueError("Snapshot input is not a regular tracked file: " + str(relative))
            source = root / relative
            if any(parent.is_symlink() for parent in (source, *source.parents) if parent != root):
                raise ValueError("Snapshot input must not traverse symbolic links: " + str(relative))
            if not source.is_file():
                raise ValueError("Tracked public input is missing: " + str(relative))
            body = source.read_bytes()
            if relative.suffix == ".json":
                json.loads(body)
            else:
                for line in body.splitlines():
                    if line.strip():
                        json.loads(line)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            files.append({"path": relative.as_posix(), "bytes": len(body),
                          "sha256": hashlib.sha256(body).hexdigest(), "base_git_blob": blob})
        by_path = {item["path"]: item for item in files}
        if not {"data/catalog.jsonl", "data/scan-status.json"} <= by_path.keys():
            raise ValueError("Tracked catalog and scan receipt are required")
        manifest = {
            "schema_version": 1,
            "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "checkout_commit": checkout_commit,
            "workflow_run_url": run_url,
            "quality_gate": quality_outcome,
            "scan_status": status["status"],
            "catalog_sha256": by_path["data/catalog.jsonl"]["sha256"],
            "file_count": len(files),
            "files": files,
            "boundary": (
                "Tracked public JSON/JSONL captured after the workflow quality gate "
                "and before its commit attempt. The checkout commit identifies the "
                "baseline; data bytes contain the verified working result. This is "
                "not evidence of a successful push or editorial approval. Untracked "
                "files, raw HTTP caches, credentials and execution logs are omitted."
            ),
        }
        (staging / "snapshot-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        staging.rename(output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/scan-snapshot")
    args = parser.parse_args(argv)
    manifest = package_snapshot(
        ROOT, args.output, quality_outcome=os.getenv("SCAN_QUALITY_OUTCOME", ""),
        repository=os.getenv("GITHUB_REPOSITORY", ""), run_id=os.getenv("GITHUB_RUN_ID", ""),
    )
    print(f"Retained {manifest['file_count']} public data files at {args.output}")


if __name__ == "__main__":
    main()
