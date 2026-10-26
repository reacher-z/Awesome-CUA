import copy
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build
import catalog

# Each value was stored as repository_tree_sha, but GET repos/<owner>/<repo>/git/commits/<sha> resolves it as a commit
# (its tree is a different object). A git/trees/<branch> response reports the commit in its top-level sha.
COMMITS = {
    "github:sunblaze-ucb/agentsynth": "cd42a4bd158fe3f0a1b0f376b9428d6a5fcb81b2",
    "github:jia-lab-research/arpo": "7489ae309e90d8b3b9e823f495b63e5116434060",
    "github:gair-nlp/pc-agent-e": "9b1b00b907b99a4a8dbfc9c01ea49010878dfbd6",
    "github:gair-nlp/windowsagentarena-v2": "2927fe55005d1be75d5a9188c0045f73ba28d192",
    "github:mobilellm/agentprog": "ef5e2998ac2defa86e0dc4c13e7e00d595e1e7cf",
    "component:tencent/selfevolvingagent/webevolver": "a82450e1b5e15070bee79ee8b79f8d9a97cb85f7",
    "github:sqzhang-lazy/d-pot": "fc764f19802f4f59afa635bfeec5a50e4c3d5465",
    "github:caap-agent/caap-agent": "9d65c0f30e3c119db533dd832863b4f3f7b74b18",
    "github:facebookresearch/openapps": "6e6782794433c60468d65ac75bc3f03c56007f8c",
    "component:x-plug/mobileagent/pc-agent": "11cea575561fb7800b5fb6b6cafa56f7a91de11f",
    "component:x-plug/mobileagent/mobile-agent-e": "11cea575561fb7800b5fb6b6cafa56f7a91de11f",
}
TREE_OF = {"11cea575561fb7800b5fb6b6cafa56f7a91de11f": "c7e96e39a9cb8a0cb9f411ed58e0394aba92513c"}

# URL shapes that name a commit (not a tree or blob object), written out independently of build.commit_pins.
COMMIT_PINNED = re.compile(
    r"^https://(?:raw\.githubusercontent\.com/[^/]+/[^/]+/"
    r"|github\.com/[^/]+/[^/]+/(?:blob|tree|raw|commit)/"
    r"|api\.github\.com/repos/[^/]+/[^/]+/(?:git/)?commits/"
    r"|huggingface\.co/(?:[^?#]+/)?(?:resolve|blob|raw|tree|commit)/)([0-9a-f]{40})(?![0-9a-f])"
    r"|[?&]ref=([0-9a-f]{40})(?![0-9a-f])")


def pinned_commits(urls):
    return {sha for url in urls for match in COMMIT_PINNED.finditer(url) for sha in match.groups() if sha}


class RepositoryCommitRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl")}
        cls.receipts = {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "primary-evidence.jsonl")}
        cls.editorial = {e.get("id") or catalog.editorial_identity(e)[0]: e for e in catalog.read_json(catalog.DATA / "editorial.json")}

    def receipt_urls(self, rid, entry):
        receipt = self.receipts.get(rid, {})
        return [*entry.get("evidence_urls", []), *(ev["url"] for ev in entry.get("additional_evidence", [])),
                *(receipt[key] for key in ("url", "final_url", "source_url") if receipt.get(key))]

    def test_the_eleven_commits_are_recorded_as_repository_revision(self):
        for rid, sha in COMMITS.items():
            with self.subTest(rid):
                for details in (self.editorial[rid]["details"], self.records[rid]["details"]):
                    self.assertEqual(details.get("repository_revision"), sha)
                    self.assertNotIn("repository_tree_sha", details)
                listing = [ev for ev in self.editorial[rid]["additional_evidence"] if "/git/trees/" in ev["url"]]
                self.assertEqual(len(listing), 1)
                self.assertIn("details.repository_revision", listing[0]["supports"])
                self.assertIn("details.repository_revision", next(ev for ev in self.records[rid]["evidence"] if ev["url"] == listing[0]["url"])["supports"])

    def test_receipts_support_only_details_the_record_has(self):
        for rid, entry in self.editorial.items():
            for ev in entry.get("additional_evidence", []):
                for path in ev["supports"]:
                    if path.startswith("details.repository_"):
                        with self.subTest(rid, path=path):
                            self.assertIn(path.split(".", 1)[1], entry.get("details", {}))

    def test_no_tree_sha_is_a_commit_its_own_receipts_pin(self):
        self.assertEqual(pinned_commits(["https://raw.githubusercontent.com/o/r/" + "a" * 40 + "/README.md",
                                         "https://api.github.com/repos/o/r/contents/README.md?ref=" + "b" * 40,
                                         "https://api.github.com/repos/o/r/git/trees/" + "c" * 40]), {"a" * 40, "b" * 40})
        for rid, entry in self.editorial.items():
            tree = entry.get("details", {}).get("repository_tree_sha")
            if tree:
                with self.subTest(rid):
                    self.assertNotIn(tree, pinned_commits(self.receipt_urls(rid, entry)))
                    self.assertNotEqual(tree, entry["details"].get("repository_revision"))
        for rid, record in self.records.items():
            tree = record["details"].get("repository_tree_sha")
            if tree:
                with self.subTest(rid):
                    self.assertNotIn(tree, pinned_commits(ev["url"] for ev in record["evidence"]))


class TreeShaValidationTests(unittest.TestCase):
    def setUp(self):
        self.base = copy.deepcopy(next(r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl") if r["id"] == "component:x-plug/mobileagent/pc-agent"))
        # Without relations, only the tree-SHA rule can fail on this lone record.
        self.base["relations"] = []
        self.commit = self.base["details"]["repository_revision"]
        self.receipt = next(ev for ev in self.base["evidence"] if "/git/trees/" in ev["url"])

    def errors(self, row):
        return [e for e in build.validate_records([row]) if "repository_tree_sha" in e]

    def test_a_real_tree_object_passes(self):
        self.assertEqual(build.validate_records([self.base]), [])
        row = copy.deepcopy(self.base)
        row["details"]["repository_tree_sha"] = TREE_OF[self.commit]
        row["evidence"].append({**self.receipt, "url": "https://api.github.com/repos/X-PLUG/MobileAgent/git/trees/" + TREE_OF[self.commit]})
        self.assertEqual(self.errors(row), [])

    def test_a_commit_in_the_tree_key_is_rejected(self):
        same = copy.deepcopy(self.base)
        same["details"]["repository_tree_sha"] = self.commit
        pinned = copy.deepcopy(self.base)
        del pinned["details"]["repository_revision"]
        pinned["details"]["repository_tree_sha"] = self.commit
        pinned["evidence"].append({**self.receipt, "url": f"https://raw.githubusercontent.com/X-PLUG/MobileAgent/{self.commit}/README.md"})
        for row in (same, pinned):
            with self.subTest(url=row["evidence"][-1]["url"]):
                self.assertEqual(self.errors(row), [f"{row['id']}: repository_tree_sha holds a commit SHA; record it as repository_revision"])
        self.assertEqual(build.commit_pins(f"https://api.github.com/repos/o/r/git/trees/{self.commit}?recursive=1"), set())


if __name__ == "__main__":
    unittest.main()
