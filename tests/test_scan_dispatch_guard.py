from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "scan.yml"
LITERALS = {"true": True, "false": False, "null": None}
TOKEN = re.compile(r"\s*(==|!=|&&|\|\||!|\(|\)|'[^']*'|[A-Za-z_][\w.-]*)")


def evaluate(expression, context):
    """Evaluate the GitHub expression subset the guards use: context paths, string literals, ==, !=, !, && and ||."""
    return bool(value(expression, context))


def value(expression, context):
    """The value of an expression; like GitHub, && and || return an operand rather than a boolean."""
    items, position = [], 0
    while expression[position:].strip():
        match = TOKEN.match(expression, position)
        if not match:
            raise ValueError(f"unsupported expression syntax: {expression[position:]}")
        items.append(match.group(1))
        position = match.end()

    def either():
        value = both()
        while items[:1] == ["||"]:
            items.pop(0)
            right = both()
            value = value or right
        return value

    def both():
        value = comparison()
        while items[:1] == ["&&"]:
            items.pop(0)
            right = comparison()
            value = value and right
        return value

    def comparison():
        left = unary()
        if items[:1] in (["=="], ["!="]):
            operator, right = items.pop(0), unary()
            # GitHub compares strings case-insensitively.
            return (str(left).casefold() == str(right).casefold()) == (operator == "==")
        return left

    def unary():
        if items[:1] == ["!"]:
            items.pop(0)
            return not unary()
        token = items.pop(0)
        if token == "(":
            value = either()
            if items.pop(0) != ")":
                raise ValueError(expression)
            return value
        if token.startswith("'"):
            return token[1:-1]
        return LITERALS[token] if token in LITERALS else context.get(token)

    result = either()
    if items:
        raise ValueError(expression)
    return result


def steps():
    lines = WORKFLOW.read_text().splitlines()
    found, current = {}, None
    for line in lines[lines.index("    steps:") + 1:]:
        if line.startswith("  ") and not line.startswith("    "):
            break
        name = re.fullmatch(r"      - name: (.+)", line)
        if name:
            current = found.setdefault(name.group(1), {})
        elif current is not None and re.fullmatch(r"      - .*", line):
            current = None
        elif current is not None:
            key = re.fullmatch(r"        ([a-z-]+): ?(.*)", line)
            if key:
                current[key.group(1)] = key.group(2)
    return found


class ScanDispatchGuardTests(unittest.TestCase):
    RUNS = [  # (event, ref, inputs, commit expected)
        ("schedule", "refs/heads/main", {}, True),
        ("workflow_dispatch", "refs/heads/main", {"dry_run": False}, True),
        ("workflow_dispatch", "refs/heads/main", {"dry_run": True}, False),
        ("workflow_dispatch", "refs/heads/feature", {"dry_run": False}, False),
        ("workflow_dispatch", "refs/heads/feature", {"dry_run": True}, False),
        ("workflow_dispatch", "refs/heads/main-next", {"dry_run": False}, False),
        ("workflow_dispatch", "refs/tags/v1", {"dry_run": False}, False),
    ]

    def test_dispatch_offers_a_dry_run_that_defaults_to_committing(self):
        text = WORKFLOW.read_text()
        self.assertTrue("  workflow_dispatch:\n    inputs:\n      dry_run:\n" in text, "workflow_dispatch has no dry_run input")
        dry_run = text.split("      dry_run:\n", 1)[1].split("\n\n", 1)[0]
        self.assertIn("type: boolean", dry_run)
        self.assertIn("default: false", dry_run)

    def guard_results(self, step):
        condition = steps()[step].get("if", "success()").replace("success()", "true")
        for event, ref, inputs, commits in self.RUNS:
            context = {"github.ref": ref, "github.event_name": event, **{f"inputs.{k}": v for k, v in inputs.items()}}
            yield (event, ref, inputs), evaluate(condition, context), commits

    def test_only_main_without_a_dry_run_commits(self):
        self.assertIn("git push origin HEAD:main", WORKFLOW.read_text())
        for run, runs_step, commits in self.guard_results("Commit verified scan output"):
            with self.subTest(run=run):
                self.assertEqual(runs_step, commits)

    def test_every_skipped_commit_is_reported(self):
        for run, runs_step, commits in self.guard_results("Report a skipped commit"):
            with self.subTest(run=run):
                self.assertEqual(runs_step, not commits)
        self.assertIn("::notice::", steps()["Report a skipped commit"]["run"])
        self.assertIn("$GITHUB_REF", steps()["Report a skipped commit"]["run"])

    def test_no_other_step_pushes_and_evidence_is_kept_either_way(self):
        found = steps()
        self.assertEqual(WORKFLOW.read_text().count("git push"), 1)
        self.assertEqual(found["Retain scan evidence"]["if"], "always()")

    def test_a_scan_of_main_checks_out_main_as_the_job_starts(self):
        # A run queued behind another scan must not rebuild from the commit its event recorded.
        checkout = WORKFLOW.read_text().split("\n    steps:\n", 1)[1].split("\n      - uses: actions/setup-python@", 1)[0]
        self.assertIn("uses: actions/checkout@", checkout)
        ref = re.search(r"^          ref: \$\{\{ (.+) \}\}$", checkout, re.M).group(1)
        for event, github_ref, inputs, _ in self.RUNS:
            context = {"github.ref": github_ref, "github.event_name": event, "github.sha": "0" * 40}
            with self.subTest(event=event, ref=github_ref):
                self.assertEqual(value(ref, context), "refs/heads/main" if github_ref == "refs/heads/main" else "0" * 40)

    def test_evaluator_follows_github_operator_rules(self):
        context = {"github.ref": "refs/heads/main", "inputs.flag": None}
        self.assertTrue(evaluate("!inputs.flag", context))
        self.assertFalse(evaluate("github.ref != 'REFS/heads/MAIN'", context))
        self.assertTrue(evaluate("inputs.flag || github.ref == 'refs/heads/main' && !inputs.flag", context))
        self.assertFalse(evaluate("(inputs.flag || github.ref == 'x') && true", context))
        self.assertTrue(evaluate("(inputs.flag || github.ref == 'refs/heads/main') && true", context))
        with self.assertRaises(ValueError):
            evaluate("contains(github.ref, 'main')", context)


if __name__ == "__main__":
    unittest.main()
