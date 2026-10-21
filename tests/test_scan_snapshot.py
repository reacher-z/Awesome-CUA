import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from package_scan_snapshot import package_snapshot
from test_scan_workflow import WORKFLOW, step_script


class ScanSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        self.git("init", "-q", "-b", "main")
        self.write(".gitignore", "dist/\n.cache/\n")
        self.write("data/catalog.jsonl", '{"id":"old"}\n')
        self.status = {"status": "partial", "finished_at": "2026-10-20T13:00:00Z",
                       "run_url": "https://github.com/example/catalog/actions/runs/123"}
        self.write("data/scan-status.json", json.dumps(self.status))
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.org",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "baseline")
        self.output = self.root / "dist/snapshot"

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, env=self.env)

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def capture(self, **kwargs):
        return package_snapshot(self.root, self.output, quality_outcome="success",
                                repository="example/catalog", run_id="123", **kwargs)

    def test_captures_working_result_and_baseline_without_untracked_or_raw_files(self):
        baseline = self.git("rev-parse", "HEAD").decode().strip()
        before = self.git("rev-parse", "HEAD:data/catalog.jsonl").decode().strip()
        current = '{"id":"old"}\n{"id":"new"}\n'
        self.write("data/catalog.jsonl", current)
        self.write("data/local.json", '{"private":"not a tracked public input"}')
        self.write(".cache/http/source.body", "raw source")
        manifest = self.capture()
        self.assertEqual(manifest["checkout_commit"], baseline)
        self.assertEqual(manifest["scan_status"], "partial")
        self.assertEqual(manifest["file_count"], 2)
        item = next(r for r in manifest["files"] if r["path"] == "data/catalog.jsonl")
        self.assertEqual(item["base_git_blob"], before)
        self.assertEqual(item["sha256"], hashlib.sha256(current.encode()).hexdigest())
        self.assertEqual((self.output / item["path"]).read_text(), current)
        self.assertFalse((self.output / "data/local.json").exists())
        self.assertFalse((self.output / ".cache").exists())
        # A failed/aborted rebase can restore another working tree without losing the captured result.
        self.git("checkout", "--", "data/catalog.jsonl")
        self.assertEqual((self.output / item["path"]).read_text(), current)

    def test_refuses_failed_quality_stale_receipt_or_running_scan(self):
        with self.assertRaisesRegex(ValueError, "quality gate"):
            package_snapshot(self.root, self.output, quality_outcome="failure")
        with self.assertRaisesRegex(ValueError, "another workflow"):
            package_snapshot(self.root, self.output, quality_outcome="success",
                             repository="example/catalog", run_id="124")
        self.status["status"] = "running"
        self.write("data/scan-status.json", json.dumps(self.status))
        with self.assertRaisesRegex(ValueError, "completed"):
            self.capture()
        self.assertFalse(self.output.exists())

    def test_refuses_tracked_symlink_and_preserves_existing_output(self):
        target = self.root / "outside.json"
        target.write_text('{"private":true}')
        self.root.joinpath("data/catalog.jsonl").unlink()
        self.root.joinpath("data/catalog.jsonl").symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symbolic"):
            self.capture()
        self.assertFalse(self.output.exists())
        self.output.mkdir(parents=True)
        (self.output / "keep.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError, "new directory"):
            self.capture()
        self.assertEqual((self.output / "keep.txt").read_text(), "keep")

    def test_workflow_captures_before_commit_and_retains_after_commit_failure(self):
        workflow = WORKFLOW.read_text()
        quality = workflow.index("- name: Check generated data and review boundaries")
        capture = workflow.index("- name: Snapshot verified public scan data")
        commit = workflow.index("- name: Commit verified scan output")
        retain = workflow.index("- name: Retain verified scan snapshot")
        self.assertLess(quality, capture)
        self.assertLess(capture, commit)
        self.assertLess(commit, retain)
        self.assertIn("if: always() && steps.snapshot.outcome == 'success'", workflow[retain:])
        self.assertIn("path: dist/scan-snapshot/", workflow[retain:])
        self.assertNotIn("include-hidden-files", workflow[retain:])

    def test_snapshot_survives_actual_concurrent_push_and_aborted_rebase(self):
        for name in ("README.md", "README.zh-CN.md", "docs/papers.md"):
            self.write(name, "baseline\n")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.org",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "public views")
        origin = Path(self.temp.name) / "origin.git"
        other = Path(self.temp.name) / "other"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)],
                       env=self.env, check=True, capture_output=True)
        self.git("remote", "add", "origin", str(origin))
        self.git("push", "-q", "origin", "HEAD:main")
        subprocess.run(["git", "clone", "-q", str(origin), str(other)],
                       env=self.env, check=True, capture_output=True)
        (other / "README.md").write_text("concurrent editorial update\n")
        for command in (["add", "README.md"],
                        ["-c", "user.name=Test", "-c", "user.email=test@example.org",
                         "-c", "commit.gpgsign=false", "commit", "-qm", "concurrent update"],
                        ["push", "-q", "origin", "HEAD:main"]):
            subprocess.run(["git", *command], cwd=other, env=self.env, check=True, capture_output=True)
        remote = self.git("--git-dir", str(origin), "rev-parse", "main")
        self.write("README.md", "scan generated update\n")
        scanned = '{"id":"old"}\n{"id":"new"}\n'
        self.write("data/catalog.jsonl", scanned)
        self.capture()
        output = Path(self.temp.name) / "step-output"
        result = subprocess.run(
            ["bash", "-e", "-c", step_script("Commit verified scan output")],
            cwd=self.root, env={**self.env, "GH_TOKEN": "local-test-value", "GITHUB_OUTPUT": str(output)},
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not be rebased", result.stdout + result.stderr)
        self.assertEqual(self.git("--git-dir", str(origin), "rev-parse", "main"), remote)
        self.assertFalse(output.exists())
        self.assertEqual((self.output / "data/catalog.jsonl").read_text(), scanned)
        self.assertTrue((self.output / "snapshot-manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
