"""A scheduled website check publishes only a source commit that is not yet published; pushes and dispatches always publish."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / "automation" / "publish.yml"
STEP = "Compare the source catalog head with the published revision"
HEAD = "a" * 40
# The website repository; its name is also its GitHub Pages host.
REPOSITORY = "AwesomeCUA/awesomecua.github.io"
OTHER = "b" * 40


def step_script():
    lines = PUBLISH.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {STEP}")
    run = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body = []
    for line in lines[run + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= 8:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body)).strip("\n") + "\n"


class PublicationGateWorkflowTests(unittest.TestCase):
    def test_gate_reads_revisions_without_a_token_and_every_publishing_job_depends_on_it(self):
        text = PUBLISH.read_text()
        gate = text.split("\n  gate:\n", 1)[1].split("\n  build:\n", 1)[0]
        self.assertIn("publish: ${{ steps.decision.outputs.publish }}", gate)
        self.assertIn("source_commit: ${{ steps.decision.outputs.source_commit }}", gate)
        self.assertIn("sparse-checkout: data/build-info.json\n", gate)
        self.assertNotIn("github.token", gate)
        self.assertNotIn("permissions:", gate)
        build = text.split("\n  build:\n", 1)[1].split("\n  deploy:\n", 1)[0]
        self.assertTrue(build.startswith("    needs: gate\n    if: needs.gate.outputs.publish == 'true'\n"))
        # The build publishes exactly the revision the gate compared.
        self.assertIn("          repository: reacher-z/Awesome-CUA\n", build)
        self.assertIn("          ref: ${{ needs.gate.outputs.source_commit }}\n", build)
        self.assertIn("\n  deploy:\n    needs: build\n", text)
        self.assertIn("    needs: [build, deploy]\n", text)

    def test_push_and_dispatch_triggers_remain(self):
        triggers = PUBLISH.read_text().split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertIn("  push:\n    branches: [main]\n", triggers)
        self.assertIn("  workflow_dispatch:\n", triggers)
        self.assertIn("  schedule:\n", triggers)


@unittest.skipUnless(shutil.which("jq") and shutil.which("bash"), "the website runner provides bash and jq")
class PublicationGateStepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.tmp / "bin").mkdir()
        git = self.tmp / "bin" / "git"
        git.write_text('#!/bin/sh\nif [ "$1" = log ] && [ "$2" = -1 ] && [ "$3" = --format=%ct ]; then echo "$COMMIT_TIME"; exit 0; fi\n'
                       '[ "$1" = ls-remote ] && [ "$2" = https://github.com/reacher-z/Awesome-CUA.git ] && [ "$3" = refs/heads/main ] || exit 2\n'
                       'printf \'%s\\trefs/heads/main\\n\' "$SOURCE_HEAD"\n')
        git.chmod(0o755)
        # The live site answers with LIVE_BODY, or fails like an unreachable host when it is unset.
        curl = self.tmp / "bin" / "curl"
        curl.write_text('#!/bin/sh\nfor last; do :; done\nprintf \'%s\\n\' "$last" >> "$CURL_LOG"\n'
                        '[ -n "${LIVE_BODY+set}" ] || exit 6\nprintf \'%s\' "$LIVE_BODY"\n')
        curl.chmod(0o755)
        self.site = self.tmp / "site"
        (self.site / "data").mkdir(parents=True)

    def decide(self, event, published=None, head=HEAD, live=None, live_body=None, committed_minutes_ago=60):
        if published is not None:
            (self.site / "data" / "build-info.json").write_text(json.dumps(published))
        env = {**os.environ, "PATH": f"{self.tmp / 'bin'}{os.pathsep}{os.environ['PATH']}", "SOURCE_HEAD": head,
               "GITHUB_EVENT_NAME": event, "GITHUB_OUTPUT": str(self.tmp / "output"), "GITHUB_STEP_SUMMARY": str(self.tmp / "summary"),
               "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_RUN_ID": "7", "CURL_LOG": str(self.tmp / "curl.log"),
               "COMMIT_TIME": str(int(time.time()) - 60 * committed_minutes_ago)}
        env.pop("LIVE_BODY", None)
        if live is not None or live_body is not None:
            env["LIVE_BODY"] = json.dumps({"source_commit": live}) if live is not None else live_body
        for name in ("output", "summary"):
            (self.tmp / name).write_text("")
        completed = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step_script()],
                                   cwd=self.site, env=env, capture_output=True, text=True)
        outputs = dict(line.split("=", 1) for line in (self.tmp / "output").read_text().splitlines())
        return completed, outputs

    def test_scheduled_check_skips_a_source_commit_that_is_already_live(self):
        completed, outputs = self.decide("schedule", {"source_commit": HEAD, "publication_run": "https://example.org/run"}, live=HEAD)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(outputs, {"publish": "false", "source_commit": HEAD})
        self.assertIn(f"::notice title=Nothing new to publish::Source commit {HEAD} is already live", completed.stdout)
        # The live record is read from the Pages host that this repository's name designates.
        self.assertEqual((self.tmp / "curl.log").read_text(), "https://" + REPOSITORY.split("/", 1)[1] + "/data/build-info.json\n")

    def test_scheduled_check_publishes_a_new_source_commit(self):
        completed, outputs = self.decide("schedule", {"source_commit": OTHER}, live=OTHER)
        self.assertEqual((completed.returncode, outputs), (0, {"publish": "true", "source_commit": HEAD}))

    def test_a_committed_snapshot_whose_deployment_failed_is_published_again(self):
        completed, outputs = self.decide("schedule", {"source_commit": HEAD}, live=OTHER, committed_minutes_ago=25)
        self.assertEqual((completed.returncode, outputs), (0, {"publish": "true", "source_commit": HEAD}))

    def test_a_fresh_snapshot_waits_for_the_cdn_instead_of_publishing_twice(self):
        completed, outputs = self.decide("schedule", {"source_commit": HEAD}, live=OTHER, committed_minutes_ago=5)
        self.assertEqual((completed.returncode, outputs["publish"]), (0, "false"))
        self.assertIn(f"::notice title=Deployment propagating::Source commit {HEAD} was committed 5 minutes ago", completed.stdout)
        # A new source commit is published at once, whatever the age of the previous snapshot.
        self.assertEqual(self.decide("schedule", {"source_commit": OTHER}, live=OTHER, committed_minutes_ago=5)[1]["publish"], "true")

    def test_an_unreadable_live_site_falls_back_to_the_committed_snapshot(self):
        completed, outputs = self.decide("schedule", {"source_commit": HEAD})
        self.assertEqual((completed.returncode, outputs["publish"]), (0, "false"))
        self.assertIn("::warning title=Live site unreadable::", completed.stdout)
        for body in ("<html>Not Found</html>", "{}"):
            with self.subTest(body=body):
                self.assertEqual(self.decide("schedule", {"source_commit": HEAD}, live_body=body)[1]["publish"], "false")
                self.assertEqual(self.decide("schedule", {"source_commit": OTHER}, live_body=body)[1]["publish"], "true")
        # The committed record does not prove a deployment: an unverifiable one is retried once per scan interval.
        self.assertEqual(self.decide("schedule", {"source_commit": HEAD}, committed_minutes_ago=121)[1]["publish"], "true")

    def test_missing_or_unreadable_publication_records_publish(self):
        self.assertEqual(self.decide("schedule")[1]["publish"], "true")
        (self.site / "data" / "build-info.json").write_text("not json")
        self.assertEqual(self.decide("schedule")[1]["publish"], "true")
        # A live site already serving the source needs no rebuild even without a committed record.
        self.assertEqual(self.decide("schedule", live=HEAD)[1]["publish"], "false")

    def test_push_and_manual_dispatch_publish_even_an_unchanged_source(self):
        for event in ("push", "workflow_dispatch"):
            with self.subTest(event=event):
                completed, outputs = self.decide(event, {"source_commit": HEAD}, live=HEAD)
                self.assertEqual((completed.returncode, outputs), (0, {"publish": "true", "source_commit": HEAD}))

    def test_an_unreadable_source_head_fails_instead_of_publishing_or_skipping(self):
        completed, outputs = self.decide("schedule", {"source_commit": HEAD}, head="not-a-sha", live=HEAD)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(outputs, {})
        self.assertIn("::error::Could not read the source catalog main revision", completed.stdout)

if __name__ == "__main__":
    unittest.main()
