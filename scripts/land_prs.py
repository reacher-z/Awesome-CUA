#!/usr/bin/env python3
"""Land a reviewed set of data pull requests on one local branch, ready for a single push to main.

Each PR head is merged with --no-ff into a branch made from <remote>/<base>. Conflicts that independent data PRs
always produce are resolved mechanically: keyed authored inputs are merged entry by entry, and build outputs are
regenerated. Anything else, or a failing build or validation, skips that PR. Never pushes. Standard library, git and gh.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from catalog import KINDS, editorial_identity


def _field(name):
    return lambda row: row[name]


# Authored inputs (and the verify/enrich/harvest outputs that data PRs commit) whose entries the code identifies by a
# key: build.source_records and catalog.select_editorial (editorial), build.candidate_reviews (exact id or url_prefix),
# scope_review.resolve_exclusions, repository_identity.repository_aliases, publication_metadata.attach_publications,
# catalog.discover (sources), and catalog.verify_editorial/enrich/harvest, which rewrite their rows keyed by id.
KEYED_INPUTS = {
    "data/editorial.json": lambda row: row["id"] if "id" in row else editorial_identity(row)[0],
    "data/candidate-reviews.json": lambda row: ("id", row["id"]) if "id" in row else ("url_prefix", row["url_prefix"]),
    "data/exclusions.json": _field("id"),
    "data/repository-aliases.json": _field("alias_id"),
    "data/sources.json": _field("id"),
    "data/publications.jsonl": _field("id"),
    "data/primary-evidence.jsonl": _field("id"),
    "data/enrichment.jsonl": _field("id"),
    "data/papers.jsonl": _field("id"),
    "data/candidates.jsonl": _field("id"),
    "data/metadata-updates.jsonl": _field("id"),
}
# catalog.write_jsonl writes these sorted by id; a merge keeps them sorted while our side still is.
SORTED_BY_ID = {"data/primary-evidence.jsonl", "data/enrichment.jsonl", "data/papers.jsonl", "data/candidates.jsonl", "data/metadata-updates.jsonl"}
# Whole files that catalog.py build writes: build.build and build.documents. tests/test_land_prs.py checks this against a real build.
BUILD_OUTPUTS = {"data/catalog.jsonl", "data/coverage.json", "data/exclusion-status.json", "data/review-queue.jsonl", "data/references.jsonl",
    "docs/papers.md", "docs/coverage.md", "docs/topics.md", "docs/environments.md",
    *(f"docs/{'companies' if kind == 'company' else kind + 's'}.md" for kind in KINDS - {"paper"})}
BUILD_PAGE_DIRS = ("docs/topics/", "docs/environments/")  # One generated page per topic or environment.
# Files where build replaces only the text between <!-- NAME:START --> and <!-- NAME:END -->; the rest is authored.
# None means every marker pair in the file, so a block the build adds later (CHARTS, BY_TOPIC) needs no change here.
BUILD_BLOCKS = {"README.md": None, "README.zh-CN.md": None, "docs/data-dictionary.md": ("TOPICS",)}
# A PR that changes only these paths runs no code of its own when the catalog is rebuilt.
DATA_PREFIXES = ("data/", "docs/")
GATE = (("build",), ("validate",), ("build", "--check"))
PR_FIELDS = "number,title,state,isDraft,baseRefName,createdAt"


class Conflict(Exception):
    """A change that needs a human decision; that PR is skipped."""


class SetupError(Exception):
    """The run cannot start or continue."""


def build_role(path):
    """'whole' for a file catalog.py build writes, 'blocks' for one where it rewrites marked blocks, otherwise None."""
    if path in BUILD_BLOCKS:
        return "blocks"
    if path in BUILD_OUTPUTS or (path.startswith(BUILD_PAGE_DIRS) and path.endswith(".md") and path.count("/") == 2):
        return "whole"
    return None


def is_data_path(path):
    return path.startswith(DATA_PREFIXES) or ("/" not in path and path.endswith(".md"))


def show_key(key):
    return key[1] if isinstance(key, tuple) else str(key)


def keyed_entries(path, text):
    """Map each entry's key to (entry, original JSONL line), in file order."""
    if path.endswith(".jsonl"):
        try:
            rows = [(json.loads(line), line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError as error:
            raise Conflict(f"{path}: invalid JSONL ({error.msg})") from error
    else:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as error:
            raise Conflict(f"{path}: invalid JSON ({error.msg})") from error
        if not isinstance(value, list):
            raise Conflict(f"{path}: expected a JSON list")
        rows = [(item, None) for item in value]
    entries = {}
    for item, line in rows:
        try:
            key = KEYED_INPUTS[path](item)
        except (KeyError, TypeError, AttributeError):
            raise Conflict(f"{path}: an entry has no identity key: {json.dumps(item, ensure_ascii=False)[:120]}") from None
        if key in entries:
            raise Conflict(f"{path}: duplicate entry {show_key(key)}")
        entries[key] = (item, line)
    return entries


def merge_keyed(path, base, ours, theirs):
    """Three-way merge of a keyed list: our order, their new entries appended, and a Conflict where both sides changed one key differently."""
    b, o, t = (keyed_entries(path, text) if text is not None else {} for text in (base, ours, theirs))
    merged = {}
    for key, ours_entry in o.items():
        if key not in t:
            if key not in b:
                merged[key] = ours_entry
            elif b[key][0] != ours_entry[0]:
                raise Conflict(f"{path}: {show_key(key)} was changed on the branch but removed by the pull request")
            continue
        theirs_entry = t[key]
        if theirs_entry[0] == ours_entry[0] or (key in b and b[key][0] == theirs_entry[0]):
            merged[key] = ours_entry
        elif key in b and b[key][0] == ours_entry[0]:
            merged[key] = theirs_entry
        else:
            raise Conflict(f"{path}: both sides changed {show_key(key)} differently")
    for key, theirs_entry in t.items():
        if key in o:
            continue
        if key in b:
            if b[key][0] != theirs_entry[0]:
                raise Conflict(f"{path}: {show_key(key)} was changed by the pull request but removed on the branch")
            continue
        merged[key] = theirs_entry
    keys = list(merged)
    if path in SORTED_BY_ID and list(o) == sorted(o):
        keys.sort()
    if path.endswith(".jsonl"):
        return "".join((merged[k][1] if merged[k][1] is not None else json.dumps(merged[k][0], ensure_ascii=False, sort_keys=True)) + "\n" for k in keys)
    return json.dumps([merged[k][0] for k in keys], ensure_ascii=False, indent=2) + "\n"


def strip_blocks(path, text):
    """Empty the generated blocks of a partly generated file, keeping their markers for build to refill."""
    for name in BUILD_BLOCKS[path] or re.findall(r"<!-- ([A-Z0-9_]+):START -->", text):
        text = re.sub(rf"(?<=<!-- {name}:START -->).*?(?=<!-- {name}:END -->)", "", text, flags=re.S)
    return text


class Lander:
    def __init__(self, repo, python, remote, base):
        self.repo, self.python, self.remote, self.base = repo, python, remote, base

    def git(self, *args, check=True):
        result = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, encoding="utf-8")
        if check and result.returncode:
            raise SetupError(f"git {' '.join(args)} failed: {(result.stderr or result.stdout).strip()}")
        return result

    def out(self, *args):
        return self.git(*args).stdout.strip()

    def lines(self, *args):
        return [line for line in self.out(*args).splitlines() if line]

    def blob(self, commit, path):
        result = subprocess.run(["git", "cat-file", "blob", f"{commit}:{path}"], cwd=self.repo, capture_output=True)
        return result.stdout.decode("utf-8") if result.returncode == 0 else None

    def write(self, path, text):
        (self.repo / path).write_bytes(text.encode("utf-8"))
        self.git("add", "--", path)

    def reset(self, commit):
        """Drop a merge attempt: tracked changes, merge state and files build created."""
        self.git("reset", "-q", "--hard", commit)
        self.git("clean", "-fdq", "--", "data", "docs")

    def merge_text(self, path, base, ours, theirs):
        with tempfile.TemporaryDirectory() as folder:
            files = []
            for name, text in (("ours", ours), ("base", base), ("theirs", theirs)):
                files.append(Path(folder) / name)
                files[-1].write_bytes(text.encode("utf-8"))
            result = subprocess.run(["git", "merge-file", "-p", *map(str, files)], capture_output=True)
        if result.returncode:
            raise Conflict(f"{path}: authored text outside the generated blocks conflicts")
        return result.stdout.decode("utf-8")

    def resolve(self, base, ours, theirs):
        """Resolve the merge in progress, or raise Conflict. Returns notes on what was resolved."""
        conflicted = self.lines("diff", "--name-only", "--diff-filter=U")
        other = [path for path in conflicted if path not in KEYED_INPUTS and not build_role(path)]
        if other:
            raise Conflict("conflict in " + ", ".join(other[:5]) + (" and more" if len(other) > 5 else ""))
        changed = set(self.lines("diff", "--name-only", "--no-renames", base, ours)) & set(self.lines("diff", "--name-only", "--no-renames", base, theirs))
        notes = []
        # Entry-level merge even where git's line merge succeeded: it would accept two edits of one entry or a duplicated key.
        for path in sorted(KEYED_INPUTS.keys() & changed):
            versions = [self.blob(commit, path) for commit in (base, ours, theirs)]
            if versions[1] == versions[2]:
                continue
            if versions[1] is None or versions[2] is None:
                raise Conflict(f"{path} was deleted on one side")
            self.write(path, merge_keyed(path, *versions))
            notes.append("merged entries in " + path)
        rebuilt = []
        for path in conflicted:
            if build_role(path) == "whole":
                # The branch's version; build regenerates it from the combined inputs.
                if self.blob(ours, path) is None:
                    self.git("rm", "-q", "--cached", "--ignore-unmatch", "--", path)
                    (self.repo / path).unlink(missing_ok=True)
                else:
                    self.git("checkout", ours, "--", path)
                rebuilt.append(path)
            elif build_role(path) == "blocks":
                versions = [self.blob(commit, path) for commit in (base, ours, theirs)]
                if versions[1] is None or versions[2] is None:
                    raise Conflict(f"{path} was deleted on one side")
                self.write(path, self.merge_text(path, *(strip_blocks(path, text or "") for text in versions)))
                rebuilt.append(path)
        if rebuilt:
            notes.append("rebuilt " + (", ".join(rebuilt) if len(rebuilt) <= 3 else f"{len(rebuilt)} generated files"))
        if remaining := self.lines("diff", "--name-only", "--diff-filter=U"):
            raise Conflict("unresolved conflict in " + ", ".join(remaining[:5]))
        return notes

    def gate(self, steps=GATE):
        """Run the catalog checks; return None, or why they failed."""
        for step in steps:
            try:
                result = subprocess.run([self.python, "scripts/catalog.py", *step], cwd=self.repo, capture_output=True, text=True, encoding="utf-8", errors="replace")
            except OSError as error:
                return f"cannot run {self.python}: {error.strerror}"
            if result.returncode:
                output = (result.stderr.strip() or result.stdout.strip()).splitlines()
                print("\n".join(output[-20:]), file=sys.stderr)
                # The exception line of a traceback names the first error; otherwise use the last line printed.
                error = next((line for line in output if re.match(r"\w+(Error|Exception): ", line)), output[-1] if output else f"exit {result.returncode}")
                return f"catalog.py {' '.join(step)} failed: {error[:200]}"
        return None

    def land(self, pr, allow_code):
        """Merge one PR on the current branch and commit it. Returns (merged, detail)."""
        number = pr["number"]
        if pr.get("state") != "OPEN":
            return False, f"PR is {str(pr.get('state')).lower()}"
        if pr.get("isDraft"):
            return False, "draft PR"
        if pr.get("baseRefName") != self.base:
            return False, f"targets {pr.get('baseRefName')}, not {self.base}"
        fetched = self.git("fetch", "-q", "--no-tags", self.remote, f"refs/pull/{number}/head", check=False)
        if fetched.returncode:
            return False, "could not fetch pull/{}/head: {}".format(number, fetched.stderr.strip()[:150])
        head = self.out("rev-parse", "FETCH_HEAD")
        ours = self.out("rev-parse", "HEAD")
        if self.git("merge-base", "--is-ancestor", head, ours, check=False).returncode == 0:
            return False, "already on the branch"
        base = self.git("merge-base", ours, head, check=False).stdout.strip()
        if not base:
            return False, "no common history with the branch"
        code = [path for path in self.lines("diff", "--name-only", "--no-renames", base, head) if not is_data_path(path)]
        if code and not allow_code:
            return False, "changes " + ", ".join(code[:3]) + (" and more" if len(code) > 3 else "") + "; review it and pass --allow-code to run its code"
        self.git("merge", "--no-ff", "--no-commit", "-q", head, check=False)
        if self.git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode:
            self.reset(ours)
            return False, "git merge could not start"
        try:
            notes = self.resolve(base, ours, head)
            failure = self.gate()
            if not failure:
                self.git("add", "-A")
                self.git("commit", "-q", "-m", f"Merge #{number}: {pr.get('title', '')}")
        except (Conflict, SetupError) as problem:
            failure = str(problem)[:300]
        if failure:
            self.reset(ours)
            return False, failure
        return True, " ".join([self.out("rev-parse", "--short", "HEAD"), *(f"({note})" for note in notes)])


def gh_json(repo, args):
    try:
        result = subprocess.run(["gh", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        raise SetupError("gh is not installed; see https://cli.github.com/") from None
    if result.returncode:
        raise SetupError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def pull_requests(repo, numbers, label, slug):
    """The PRs to land: the given numbers in order, or open PRs with the label, oldest first."""
    extra = ["--repo", slug] if slug else []
    if label:
        rows = gh_json(repo, ["pr", "list", "--state", "open", "--label", label, "--limit", "1000", "--json", PR_FIELDS, *extra])
        return sorted(rows, key=lambda row: (row["createdAt"], row["number"]))
    return [gh_json(repo, ["pr", "view", str(number), "--json", PR_FIELDS, *extra]) for number in dict.fromkeys(numbers)]


def report(results, branch, remote, base, dry_run):
    merged = sum(ok for _, ok, _ in results)
    lines = ["| PR | Result | Detail |", "| --- | --- | --- |"]
    lines += [f"| #{pr['number']} | {'merged' if ok else 'skipped'} | {detail.replace('|', '/')} |" for pr, ok, detail in results]
    lines += ["", f"{'Dry run: would merge' if dry_run else 'Merged'} {merged} of {len(results)} pull requests onto {remote}/{base}."]
    if dry_run:
        lines.append(f"Branch {branch} was deleted; nothing was kept or pushed.")
    elif merged:
        lines += [f"Review the branch, then push it yourself (fails if {remote}/{base} has moved; rerun the script then):", "",
            f"  git log --oneline --first-parent {remote}/{base}..{branch}", f"  git push {remote} {branch}:{base}"]
    else:
        lines.append(f"Nothing merged; branch {branch} was deleted.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("numbers", nargs="*", type=int, metavar="PR", help="pull request numbers, landed in this order")
    parser.add_argument("--label", help="land every open PR with this label, oldest first")
    parser.add_argument("--branch", help="local branch to create (default: land/<UTC timestamp>)")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--base", default="main", help="branch the PRs target and the push updates")
    parser.add_argument("--repo", help="GitHub OWNER/NAME for gh (default: inferred from the checkout)")
    parser.add_argument("--repo-dir", type=Path, default=Path("."), help="checkout to land in (default: current directory)")
    parser.add_argument("--python", default=sys.executable, help="interpreter for catalog.py, with requirements-dev.txt installed")
    parser.add_argument("--allow-code", action="store_true", help="also land PRs that change files outside data/, docs/ and top-level Markdown")
    parser.add_argument("--dry-run", action="store_true", help="run the same merges and checks, then delete the branch")
    args = parser.parse_args(argv)
    if bool(args.numbers) == bool(args.label):
        parser.error("give PR numbers or --label, not both")
    try:
        return run(args)
    except SetupError as error:
        print(f"land_prs: {error}", file=sys.stderr)
        return 2


def run(args):
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=args.repo_dir, capture_output=True, text=True)
    if top.returncode:
        raise SetupError(f"{args.repo_dir} is not a git checkout")
    lander = Lander(Path(top.stdout.strip()), args.python, args.remote, args.base)
    if lander.out("status", "--porcelain", "--untracked-files=all"):
        raise SetupError("the checkout has local changes or untracked files; commit, stash or remove them first")
    prs = pull_requests(lander.repo, args.numbers, args.label, args.repo)
    if not prs:
        raise SetupError(f"no open pull requests with label {args.label}")
    branch = args.branch or "land/" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    if lander.git("rev-parse", "-q", "--verify", "refs/heads/" + branch, check=False).returncode == 0:
        raise SetupError(f"branch {branch} already exists")
    original = lander.git("symbolic-ref", "-q", "--short", "HEAD", check=False).stdout.strip()
    original_commit = lander.out("rev-parse", "HEAD")
    lander.git("fetch", "-q", "--no-tags", args.remote, f"+refs/heads/{args.base}:refs/remotes/{args.remote}/{args.base}")
    lander.git("switch", "-q", "--no-track", "-c", branch, f"refs/remotes/{args.remote}/{args.base}")
    results = []
    try:
        if failure := lander.gate((("validate",), ("build", "--check"))):
            raise SetupError(f"{args.remote}/{args.base} does not pass the catalog checks before any merge ({failure}); "
                "fix it first, or pass --python with requirements-dev.txt installed")
        for pr in prs:
            print(f"#{pr['number']} {pr.get('title', '')}", file=sys.stderr, flush=True)
            ok, detail = lander.land(pr, args.allow_code)
            print(f"  {'merged' if ok else 'skipped'}: {detail}", file=sys.stderr, flush=True)
            results.append((pr, ok, detail))
    finally:
        # Interrupted or not, leave no half-finished merge and return to the starting checkout.
        lander.reset("HEAD")
        if original:
            lander.git("switch", "-q", original)
        else:
            lander.git("switch", "-q", "--detach", original_commit)
        if args.dry_run or not any(ok for _, ok, _ in results):
            lander.git("branch", "-q", "-D", branch)
    print(report(results, branch, args.remote, args.base, args.dry_run))
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
