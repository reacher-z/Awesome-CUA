"""land_prs.py against temporary git repositories: merges, conflict resolution, skipped PRs, and no push."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import land_prs

# Stands in for scripts/catalog.py in the fixture: views generated from editorial.json, and a validation rule.
STUB_CATALOG = r'''
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def views():
    entries = json.loads((ROOT / "data/editorial.json").read_text(encoding="utf-8"))
    rows = sorted(entries, key=lambda e: e["url"])
    catalog = "".join(json.dumps({"name": e["name"], "summary": e.get("summary"), "url": e["url"]}, sort_keys=True) + "\n" for e in rows)
    stats = f"\n{len(rows)} resources: {', '.join(e['name'] for e in rows)}\n"
    readme = re.sub(r"(?<=<!-- STATS:START -->).*?(?=<!-- STATS:END -->)", lambda _: stats, (ROOT / "README.md").read_text(encoding="utf-8"), flags=re.S)
    return {"data/catalog.jsonl": catalog, "README.md": readme}
command = sys.argv[1:]
if command == ["validate"]:
    missing = [e["name"] for e in json.loads((ROOT / "data/editorial.json").read_text(encoding="utf-8")) if not e.get("summary")]
    if missing:
        sys.exit("ValueError: no summary: " + ", ".join(missing))
elif command == ["build"]:
    for path, text in views().items():
        (ROOT / path).write_bytes(text.encode("utf-8"))
elif command == ["build", "--check"]:
    stale = [path for path, text in views().items() if (ROOT / path).read_text(encoding="utf-8") != text]
    if stale:
        sys.exit("ValueError: Generated files are stale: " + ", ".join(stale))
else:
    sys.exit("unknown command")
'''
README = "# Fixture\n\nIntro line.\n<!-- STATS:START -->\n<!-- STATS:END -->\n\nAuthored closing text.\n"


def entry(slug, name, summary="A reviewed resource."):
    return {"name": name, "kind": "tool", "url": f"https://github.com/a/{slug}", "summary": summary}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class LandPullRequestsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "gitconfig").write_text("")
        environment = {"GIT_CONFIG_GLOBAL": str(self.tmp / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Tester", "GIT_AUTHOR_EMAIL": "tester@example.com", "GIT_COMMITTER_NAME": "Tester", "GIT_COMMITTER_EMAIL": "tester@example.com"}
        patcher = mock.patch.dict(os.environ, environment)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.upstream = self.tmp / "upstream"
        git(self.tmp, "init", "-q", "-b", "main", str(self.upstream))
        (self.upstream / "scripts").mkdir()
        (self.upstream / "data").mkdir()
        (self.upstream / "scripts/catalog.py").write_text(STUB_CATALOG)
        (self.upstream / "README.md").write_text(README)
        self.commit_editorial([entry("one", "One"), entry("two", "Two")], "Initial catalog")
        self.main = git(self.upstream, "rev-parse", "HEAD")
        self.work = self.tmp / "work"
        git(self.tmp, "clone", "-q", str(self.upstream), str(self.work))
        self.prs = {}

    def commit_editorial(self, entries, message, files=()):
        (self.upstream / "data/editorial.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n")
        for path, text in dict(files).items():
            (self.upstream / path).write_text(text)
        subprocess.run([sys.executable, "scripts/catalog.py", "build"], cwd=self.upstream, check=True)
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "-q", "-m", message)

    def open_pr(self, number, title, entries, files=(), labels=("candidate-review",)):
        """Commit a PR branch from main, with its regenerated views as contributors commit them, and publish pull/N/head."""
        git(self.upstream, "switch", "-q", "-c", f"pr-{number}", self.main)
        self.commit_editorial(entries, title, files)
        git(self.upstream, "update-ref", f"refs/pull/{number}/head", "HEAD")
        self.prs[number] = {"number": number, "title": title, "state": "OPEN", "isDraft": False, "baseRefName": "main",
            "createdAt": f"2026-10-{number:02d}T00:00:00Z", "labels": list(labels)}
        git(self.upstream, "switch", "-q", "main")
        return git(self.upstream, "rev-parse", f"pr-{number}")

    def fake_gh(self, repo, args):
        if args[:2] == ["pr", "view"]:
            return self.prs[int(args[2])]
        label = args[args.index("--label") + 1]
        return [pr for pr in reversed(list(self.prs.values())) if label in pr["labels"]]

    def land(self, *argv, branch="land/test"):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(land_prs, "gh_json", self.fake_gh), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = land_prs.main([*argv, "--repo-dir", str(self.work), "--python", sys.executable, "--branch", branch])
        return code, stdout.getvalue()

    def branch_file(self, path, branch="land/test"):
        return git(self.work, "show", f"{branch}:{path}")

    def branch_names(self, branch="land/test"):
        return [e["name"] for e in json.loads(self.branch_file("data/editorial.json", branch))]

    def assert_restored(self):
        self.assertEqual(git(self.work, "symbolic-ref", "--short", "HEAD"), "main")
        self.assertEqual(git(self.work, "status", "--porcelain", "--untracked-files=all"), "")

    def test_clean_merge_commits_the_pr_head_as_a_parent(self):
        head = self.open_pr(1, "Add Three", [entry("one", "One"), entry("two", "Two"), entry("x-three", "Three")])
        code, out = self.land("1")
        self.assertEqual(code, 0, out)
        commit, *parents = git(self.work, "rev-list", "--parents", "-n", "1", "land/test").split()
        self.assertEqual(parents, [self.main, head])
        self.assertEqual(git(self.work, "log", "-1", "--format=%s", "land/test"), "Merge #1: Add Three")
        self.assertIn(f"| #1 | merged | {commit[:7]}", out)
        self.assertIn("  git push origin land/test:main", out)
        self.assertEqual(self.branch_names(), ["One", "Two", "Three"])
        self.assert_restored()

    def test_conflicting_generated_file_is_taken_from_the_branch_and_rebuilt(self):
        # Separate entries change, so editorial.json merges, but the adjacent catalog.jsonl lines and the README block conflict.
        self.open_pr(1, "Rename One", [entry("one", "One renamed"), entry("two", "Two")])
        self.open_pr(2, "Rename Two", [entry("one", "One"), entry("two", "Two renamed")])
        code, out = self.land("1", "2")
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"\| #2 \| merged \| \w+ \(merged entries in data/editorial\.json\) \(rebuilt README\.md, data/catalog\.jsonl\) \|")
        self.assertEqual(self.branch_names(), ["One renamed", "Two renamed"])
        catalog = [json.loads(line)["name"] for line in self.branch_file("data/catalog.jsonl").splitlines()]
        self.assertEqual(catalog, ["One renamed", "Two renamed"])
        self.assertIn("2 resources: One renamed, Two renamed", self.branch_file("README.md"))
        self.assert_restored()

    def test_appended_editorial_entries_are_unioned_in_label_order(self):
        base = [entry("one", "One"), entry("two", "Two")]
        self.open_pr(1, "Add Three", base + [entry("x-three", "Three")])
        # Also edits authored README text next to the generated block, which must survive the block conflict.
        self.open_pr(2, "Add Four", base + [entry("x-four", "Four")], files={"README.md": README.replace("Intro line.", "Intro, revised.")})
        self.open_pr(3, "Unlabelled", base + [entry("x-five", "Five")], labels=())
        code, out = self.land("--label", "candidate-review")
        self.assertEqual(code, 0, out)
        self.assertNotIn("#3", out)
        self.assertLess(out.index("| #1 |"), out.index("| #2 |"))
        self.assertIn("merged entries in data/editorial.json", out)
        self.assertEqual(self.branch_names(), ["One", "Two", "Three", "Four"])
        self.assertEqual(len(self.branch_file("data/catalog.jsonl").splitlines()), 4)
        readme = self.branch_file("README.md")
        self.assertIn("Intro, revised.", readme)
        self.assertIn("4 resources: One, Two, Four, Three", readme)
        self.assertEqual(git(self.work, "log", "--first-parent", "--format=%s", "main..land/test").splitlines(), ["Merge #2: Add Four", "Merge #1: Add Three"])

    def test_same_key_changed_differently_skips_that_pr(self):
        self.open_pr(1, "Revise One", [entry("one", "One", "Revised by the first PR."), entry("two", "Two")])
        self.open_pr(2, "Revise One again", [entry("one", "One", "Revised by the second PR."), entry("two", "Two"), entry("x-three", "Three")])
        code, out = self.land("1", "2")
        self.assertEqual(code, 1)
        self.assertIn("| #1 | merged |", out)
        self.assertIn("| #2 | skipped | data/editorial.json: both sides changed github:a/one differently |", out)
        self.assertEqual(git(self.work, "log", "-1", "--format=%s", "land/test"), "Merge #1: Revise One")
        self.assertEqual(self.branch_names(), ["One", "Two"])
        self.assert_restored()

    def test_validation_failure_skips_that_pr_and_lands_the_next(self):
        self.open_pr(1, "Add unsummarized", [entry("one", "One"), entry("two", "Two"), entry("x-bad", "Bad", "")])
        self.open_pr(2, "Add Four", [entry("one", "One"), entry("two", "Two"), entry("x-four", "Four")])
        code, out = self.land("1", "2")
        self.assertEqual(code, 1)
        self.assertIn("| #1 | skipped | catalog.py validate failed: ValueError: no summary: Bad |", out)
        self.assertEqual(git(self.work, "log", "--first-parent", "--format=%s", "main..land/test"), "Merge #2: Add Four")
        self.assertEqual(self.branch_names(), ["One", "Two", "Four"])
        self.assert_restored()

    def test_never_pushes(self):
        self.open_pr(1, "Add Three", [entry("one", "One"), entry("two", "Two"), entry("x-three", "Three")])
        before = git(self.upstream, "for-each-ref")
        calls, run = [], subprocess.run

        def spy(command, *args, **kwargs):
            calls.append(list(command))
            return run(command, *args, **kwargs)

        with mock.patch.object(land_prs.subprocess, "run", spy):
            code, out = self.land("1")
        self.assertEqual(code, 0, out)
        self.assertEqual(git(self.upstream, "for-each-ref"), before)
        self.assertEqual([c for c in calls if c[0] == "git" and "push" in c], [])
        self.assertTrue(any(c[:2] == ["git", "merge"] for c in calls))
        self.assertIn("  git push origin land/test:main", out)

    def test_dry_run_keeps_no_branch(self):
        self.open_pr(1, "Add Three", [entry("one", "One"), entry("two", "Two"), entry("x-three", "Three")])
        code, out = self.land("1", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("Dry run: would merge 1 of 1", out)
        self.assertNotIn("git push", out)
        self.assertEqual(git(self.work, "branch", "--list", "land/test"), "")
        self.assert_restored()

    def test_pr_that_changes_code_needs_allow_code(self):
        self.open_pr(1, "Change build", [entry("one", "One"), entry("two", "Two")], files={"scripts/catalog.py": STUB_CATALOG + "# changed\n"})
        code, out = self.land("1")
        self.assertEqual(code, 1)
        self.assertIn("| #1 | skipped | changes scripts/catalog.py; review it and pass --allow-code", out)
        code, out = self.land("1", "--allow-code")
        self.assertEqual(code, 0, out)

    def test_refuses_a_checkout_with_local_changes(self):
        self.open_pr(1, "Add Three", [entry("one", "One"), entry("two", "Two"), entry("x-three", "Three")])
        (self.work / "notes.txt").write_text("draft")
        code, _ = self.land("1")
        self.assertEqual(code, 2)
        self.assertEqual(git(self.work, "branch", "--list", "land/test"), "")


class KeyedMergeTests(unittest.TestCase):
    def test_jsonl_rows_merge_by_id_keep_their_lines_and_stay_sorted(self):
        row = lambda rid, value: json.dumps({"id": rid, "value": value}, sort_keys=True)
        base = "\n".join([row("a", 1), row("b", 1), row("c", 1)]) + "\n"
        ours = "\n".join([row("a", 1), row("b", 2), row("c", 1), row("d", 1)]) + "\n"
        # Their unchanged row "a" is removed; their new row keeps its own (unsorted-key) formatting.
        theirs = "\n".join([row("b", 1), row("c", 3), '{"value": 1, "id": "bb"}']) + "\n"
        merged = land_prs.merge_keyed("data/primary-evidence.jsonl", base, ours, theirs)
        self.assertEqual(merged.splitlines(), [row("b", 2), '{"value": 1, "id": "bb"}', row("c", 3), row("d", 1)])

    def test_removed_entry_changed_on_the_other_side_is_a_conflict(self):
        base = json.dumps([{"id": "arxiv:2401.00001", "reason": "old"}])
        ours = json.dumps([{"id": "arxiv:2401.00001", "reason": "new"}])
        with self.assertRaisesRegex(land_prs.Conflict, "changed on the branch but removed by the pull request"):
            land_prs.merge_keyed("data/exclusions.json", base, ours, "[]")

    def test_candidate_reviews_key_on_id_or_url_prefix(self):
        prefix = {"url_prefix": "https://star-history.com", "decision": "not_a_resource", "reason": "Badge."}
        exact = {"id": "url:bc04677877723978aa55", "url": "https://127.0.0.1", "decision": "not_a_resource", "reason": "Loopback."}
        merged = land_prs.merge_keyed("data/candidate-reviews.json", "[]", json.dumps([prefix]), json.dumps([exact]))
        self.assertEqual(json.loads(merged), [prefix, exact])
        with self.assertRaisesRegex(land_prs.Conflict, "both sides changed https://star-history.com differently"):
            land_prs.merge_keyed("data/candidate-reviews.json", "[]", json.dumps([prefix]), json.dumps([{**prefix, "reason": "Other."}]))


class BuildOutputTests(unittest.TestCase):
    def test_every_file_build_writes_is_a_build_output(self):
        """Run the real build into an empty root: land_prs must regenerate, never key-merge or refuse, each file it writes."""
        import build
        blank = lambda text: re.sub(r"(<!-- (\w+):START -->).*?(<!-- \2:END -->)", r"\1\3", text, flags=re.S)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stripped = {}
            for name in land_prs.BUILD_BLOCKS:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                stripped[name] = blank((ROOT / name).read_text(encoding="utf-8"))
                (root / name).write_text(stripped[name], encoding="utf-8")
            written = {}
            capture = lambda path, data: written.__setitem__(Path(path).relative_to(root).as_posix(), data.decode("utf-8"))
            with mock.patch.object(build, "ROOT", root), mock.patch.object(build, "atomic_write", capture), \
                    mock.patch.object(build, "write_sqlite"), mock.patch.object(build, "write_json"), contextlib.redirect_stdout(io.StringIO()):
                build.build(argparse.Namespace(check=False))
        self.assertTrue({"data/catalog.jsonl", "docs/coverage.md", "docs/topics/grounding.md", "docs/environments/web.md"} <= written.keys())
        for path, text in written.items():
            self.assertIsNotNone(land_prs.build_role(path), path)
            self.assertNotIn(path, land_prs.KEYED_INPUTS)
            if land_prs.build_role(path) == "blocks":
                # Every block build fills is one land_prs empties before merging the authored rest.
                self.assertEqual(land_prs.strip_blocks(path, text), stripped[path], path)
        self.assertEqual(written.keys() & land_prs.BUILD_BLOCKS.keys(), land_prs.BUILD_BLOCKS.keys())
        # Only a kind without curated records lacks its page.
        kind_pages = {f"docs/{'companies' if kind == 'company' else kind + 's'}.md" for kind in land_prs.KINDS}
        self.assertLessEqual(land_prs.BUILD_OUTPUTS - written.keys(), kind_pages)


if __name__ == "__main__":
    unittest.main()
