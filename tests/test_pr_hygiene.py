"""The PR hygiene check enforces commit trailers, maintainer and bot identities, and the Codex review section."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pr_hygiene  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "pr-hygiene.yml"
MAINTAINER = {"name": "reacher-z", "email": "reacher-z@users.noreply.github.com"}
NUMBERED = {"name": "reacher-z", "email": "68239571+reacher-z@users.noreply.github.com"}
ACTIONS_BOT = {"name": "github-actions[bot]", "email": "41898282+github-actions[bot]@users.noreply.github.com"}
GITHUB = {"name": "GitHub", "email": "noreply@github.com"}
OTHER = {"name": "Someone Else", "email": "someone@example.org"}
REVIEWED = "## Summary\n\nChange.\n\n## Codex review\n\nNo P0/P1 findings.\n"


def commit(sha="a" * 40, author=MAINTAINER, committer=MAINTAINER, message="Change something"):
    return {"sha": sha, "commit": {"author": dict(author), "committer": dict(committer), "message": message}}


def pull(login="reacher-z", body=REVIEWED, user_type="User"):
    return {"user": {"login": login, "type": user_type}, "body": body}


class TrailerTests(unittest.TestCase):
    def test_claude_trailer_and_generated_footer_fail_for_every_author(self):
        for message in ["Fix\n\nCo-Authored-By: Claude <noreply@anthropic.com>", "Fix\n\nco-authored-by:claude opus",
                         "Fix\n\nGenerated with Claude", "Fix\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)",
                         "Fix\n\ngenerated  WITH claude"]:
            with self.subTest(message=message):
                problems = pr_hygiene.check(pull("contributor", body=""), [commit(author=OTHER, committer=OTHER, message=message)])
                self.assertEqual(len(problems), 1, problems)
                self.assertTrue(problems[0].startswith("commit aaaaaaaaaaaa: message "))

    def test_other_co_authors_and_mentions_pass(self):
        for message in ["Fix\n\nCo-Authored-By: reacher-z <reacher-z@users.noreply.github.com>",
                        "Document how Claude models are listed", "Fix: Co-Authored-By trailers mentioning Claudette are fine"]:
            with self.subTest(message=message):
                self.assertEqual(pr_hygiene.check(pull(), [commit(message=message)]), [])


class IdentityTests(unittest.TestCase):
    def test_maintainer_and_bot_identities_pass(self):
        commits = [commit(), commit(author=NUMBERED, committer=NUMBERED), commit(author=ACTIONS_BOT, committer=ACTIONS_BOT),
                   commit(author=MAINTAINER, committer=GITHUB), commit(author=ACTIONS_BOT, committer=GITHUB),
                   commit(author={"name": "reacher-z", "email": "Reacher-Z@users.noreply.github.com"})]
        self.assertEqual(pr_hygiene.check(pull(), commits), [])
        self.assertEqual(pr_hygiene.check(pull("dependabot[bot]", body="", user_type="Bot"), commits), [])

    def test_other_identities_fail_with_the_sha_and_field_but_never_the_name(self):
        cases = {
            "author": commit(sha="b" * 40, author=OTHER),
            "committer": commit(sha="c" * 40, committer=OTHER),
            "both": commit(sha="d" * 40, author=OTHER, committer=GITHUB),
            "maintainer name with another email": commit(sha="e" * 40, author={"name": "reacher-z", "email": "private@example.org"}),
            "bot name with a mismatched email": commit(sha="f" * 40, author={"name": "github-actions[bot]", "email": "1+other[bot]@users.noreply.github.com"}),
            "bot email without the bot suffix": commit(sha="1" * 40, author={"name": "github-actions", "email": "41898282+github-actions@users.noreply.github.com"}),
        }
        expected = {"author": ["author"], "committer": ["committer"], "both": ["author", "committer"],
                    "maintainer name with another email": ["author"], "bot name with a mismatched email": ["author"],
                    "bot email without the bot suffix": ["author"]}
        for case, item in cases.items():
            with self.subTest(case=case):
                problems = pr_hygiene.check(pull(), [item])
                self.assertEqual([p.split(": ", 1)[1].split()[0] for p in problems], expected[case])
                self.assertTrue(all(p.startswith(f"commit {item['sha'][:12]}: ") for p in problems))
                text = "\n".join(problems)
                for person in (item["commit"]["author"], item["commit"]["committer"]):
                    if person["name"] not in ("reacher-z", "GitHub"):
                        self.assertNotIn(person["name"], text)
                    self.assertNotIn(person["email"], text)

    def test_merge_commits_are_checked_like_any_other(self):
        merge = commit(sha="9" * 40, author=OTHER, committer=GITHUB, message="Merge branch 'main' into topic")
        merge["parents"] = [{"sha": "1" * 40}, {"sha": "2" * 40}]
        self.assertEqual(len(pr_hygiene.check(pull(), [merge])), 2)

    def test_identities_are_not_checked_for_other_contributors(self):
        self.assertEqual(pr_hygiene.check(pull("contributor", body=""), [commit(author=OTHER, committer=OTHER)]), [])


class CodexReviewTests(unittest.TestCase):
    def test_heading_at_any_level_with_text_passes(self):
        for body in [REVIEWED, "# codex REVIEW\nclean", "Intro\n\n### Codex review ###\n\n- P2: kept, reason given\n",
                     "## Codex review\n\n```text\nno findings\n```\n", "## Codex review\n### Round 1\nNo P0/P1.\n",
                     "Summary\n=======\nChange.\n\nCodex review\n------------\nNo P0/P1.\n\nChecks\n------\nall green\n"]:
            with self.subTest(body=body):
                self.assertEqual(pr_hygiene.check(pull(body=body), [commit()]), [])

    def test_missing_or_empty_section_fails_for_the_maintainer_only(self):
        for body, problem in [(None, 'description: no "Codex review" heading'),
                              ("## Summary\nCodex review: clean", 'description: no "Codex review" heading'),
                              ("```\n## Codex review\nclean\n```", 'description: no "Codex review" heading'),
                              ("## Codex review\n\n<!-- paste the summary -->\n\n## Checks\nall green",
                               'description: the "Codex review" heading has no text under it'),
                              ("## Codex review\n   \n", 'description: the "Codex review" heading has no text under it'),
                              ("## Codex review\n### Checks\n", 'description: the "Codex review" heading has no text under it'),
                              ("## Codex review\n```text\n```\n", 'description: the "Codex review" heading has no text under it'),
                              ("## Codex reviews\nclean", 'description: no "Codex review" heading'),
                              ("Codex review\n---\nChecks\n---\nall green", 'description: the "Codex review" heading has no text under it'),
                              ("```\nCodex review\n---\nclean\n```", 'description: no "Codex review" heading')]:
            with self.subTest(body=body):
                self.assertEqual(pr_hygiene.check(pull(body=body), [commit()]), [problem])
        self.assertEqual(pr_hygiene.check(pull("github-actions[bot]", body="", user_type="Bot"), [commit(author=ACTIONS_BOT, committer=ACTIONS_BOT)]), [])
        self.assertEqual(pr_hygiene.check(pull("contributor", body=""), [commit(author=OTHER, committer=OTHER)]), [])


class SubstituteReviewTests(unittest.TestCase):
    def test_independent_review_heading_or_substitute_line_passes(self):
        for body in ["## Independent review\nNo P0/P1 findings.\n",
                     "## Summary\nChange.\n\nReviewed by an independent reviewer agent (Codex usage limit until 2026-11-13): no findings.\n",
                     "## Codex review\n\nIndependent reviewer agent (Codex usage limit until 2026-11-13): no P0/P1.\n"]:
            with self.subTest(body=body):
                self.assertEqual(pr_hygiene.check(pull(body=body), [commit()]), [])

    def test_substitute_line_passes_even_under_an_empty_review_heading(self):
        body = "## Codex review\n<!-- paste -->\n## Checks\nIndependent reviewer agent (Codex usage limit until 2026-11-13): clean.\n"
        self.assertEqual(pr_hygiene.check(pull(body=body), [commit()]), [])

    def test_lists_quotes_and_tables_above_a_rule_stay_review_text(self):
        for body in ["## Codex review\n- No P0/P1 findings.\n---\n## Checks\nok", "## Codex review:\n> No findings.\n---\n",
                     "## Codex review\n| Round | Result |\n---\n"]:
            with self.subTest(body=body):
                self.assertEqual(pr_hygiene.check(pull(body=body), [commit()]), [])

    def test_a_rule_or_unclosed_comment_is_not_review_text(self):
        for body in ["## Codex review\n---\n## Checks\nok", "## Codex review\n***\n", "## Codex review\n<!-- placeholder\nhidden text"]:
            with self.subTest(body=body):
                self.assertEqual(pr_hygiene.check(pull(body=body), [commit()]),
                                 ['description: the "Codex review" heading has no text under it'])

    def test_comment_markers_in_code_or_mid_line_hide_nothing(self):
        for body in ["Parser now handles <!-- in titles.\n\n## Codex review\nNo findings.",
                     "Strips `<!--` markers.\n\n## Codex review\nNo findings.\n\n## Notes\n<!-- hint -->",
                     "## Codex review\n```\n<!-- x -->\n```", "## Codex review\nClean <!-- note --> round.\n"]:
            with self.subTest(body=body):
                self.assertEqual(pr_hygiene.check(pull(body=body), [commit()]), [])

    def test_fences_close_only_on_a_bare_marker(self):
        hidden = "```\n```text\n## Codex review\nLGTM\n```"
        self.assertEqual(pr_hygiene.check(pull(body=hidden), [commit()]), ['description: no "Codex review" heading'])
        inline = "```x``` is inline code\n\n## Codex review\nNo findings."
        self.assertEqual(pr_hygiene.check(pull(body=inline), [commit()]), [])

    def test_heading_markup_is_read_as_words_and_an_empty_heading_ends_the_section(self):
        for body in ["## **Codex review**\nNo findings.", "## `Codex review` ##\nNo findings.", "## [Codex review](#x)\nNo findings."]:
            with self.subTest(body=body):
                self.assertEqual(pr_hygiene.check(pull(body=body), [commit()]), [])
        self.assertEqual(pr_hygiene.check(pull(body="## Codex review\n##\nreal text"), [commit()]),
                         ['description: the "Codex review" heading has no text under it'])

    def test_markup_without_words_is_not_review_text(self):
        for body in ["## Codex review\n-\n", "## Codex review\n>\n", "## Codex review\n&nbsp;\n",
                     "## Codex review\n<br>\n", "## Codex review\n\\\n"]:
            with self.subTest(body=body):
                self.assertEqual(pr_hygiene.check(pull(body=body), [commit()]),
                                 ['description: the "Codex review" heading has no text under it'])

    def test_claude_anywhere_in_a_co_author_trailer_fails(self):
        for trailer in ["Co-Authored-By: Anthropic Claude <x@example.com>", 'Co-authored-by: "Claude" <x@example.com>',
                        "Co-authored-by: Assistant <noreply@anthropic.com>"]:
            with self.subTest(trailer=trailer):
                self.assertTrue(pr_hygiene.message_problems(commit(message="Fix\n\n" + trailer)))

    def test_substitute_line_inside_a_comment_or_an_empty_independent_heading_fails(self):
        self.assertEqual(pr_hygiene.check(pull(body="<!-- independent reviewer agent (Codex usage limit until 2026-11-13) -->"), [commit()]),
                         ['description: no "Codex review" heading'])
        self.assertEqual(pr_hygiene.check(pull(body="## Independent review\n\n## Checks\nok"), [commit()]),
                         ['description: the "Codex review" heading has no text under it'])


class CommandLineTests(unittest.TestCase):
    def run_main(self, pages, event):
        with tempfile.TemporaryDirectory() as directory:
            commits, payload = Path(directory) / "commits.json", Path(directory) / "event.json"
            commits.write_text("".join(json.dumps(page, indent=1) + "\n" for page in pages))
            payload.write_text(json.dumps({"pull_request": event}))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = pr_hygiene.main(["--commits", str(commits), "--event", str(payload)])
            return code, output.getvalue()

    def test_reads_every_paginated_page_and_reports_failures_as_annotations(self):
        code, output = self.run_main([[commit()], [commit(sha="b" * 40, author=OTHER)]], pull())
        self.assertEqual(code, 1)
        self.assertIn("::error::commit bbbbbbbbbbbb: author is not reacher-z or a GitHub bot", output)
        self.assertNotIn("Someone Else", output)

    def test_a_clean_pull_request_passes(self):
        code, output = self.run_main([[commit(), commit(sha="b" * 40)]], pull())
        self.assertEqual((code, output.strip()), (0, "Checked 2 commits and the description."))

    def test_fewer_commits_than_the_pull_request_has_fails(self):
        code, output = self.run_main([[commit()]], {**pull(), "commits": 251})
        self.assertEqual(code, 1)
        self.assertIn("Read 1 of the pull request's 251 commits", output)

    def test_no_commits_fails(self):
        self.assertEqual(self.run_main([[]], pull())[0], 1)


class WorkflowTests(unittest.TestCase):
    def test_runs_on_every_description_and_commit_change_and_reads_the_body_from_the_event_file(self):
        text = WORKFLOW.read_text()
        self.assertIn("  pull_request_target:\n    types: [opened, edited, synchronize, reopened]\n", text)
        self.assertNotIn("head.sha", text)
        self.assertNotIn("head.ref", text)
        self.assertIn("permissions: {}\n", text)
        self.assertIn("    permissions:\n      contents: read\n      pull-requests: read\n", text)
        self.assertNotIn("pull_request.body", text)
        self.assertNotIn("pull_request.title", text)
        self.assertIn('          python scripts/pr_hygiene.py --commits "$RUNNER_TEMP/commits.json"\n', text)
        self.assertIn("          ref: ${{ github.event.pull_request.base.sha }}\n", text)
        # The token is only in the API step, which runs before any repository code is checked out.
        self.assertLess(text.index("GH_TOKEN: ${{ github.token }}"), text.index("uses: actions/checkout@"))
        self.assertEqual(text.count("github.token"), 1)


if __name__ == "__main__":
    unittest.main()
