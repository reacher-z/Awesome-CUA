import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build
import catalog

# Official leaderboards linked from each benchmark's reviewed primary README or card (#98).
LEADERBOARDS = {
    "github:xlang-ai/osworld": "https://os-world.github.io/",
    "github:web-arena-x/webarena": "https://docs.google.com/spreadsheets/d/1M801lEpBbKSNwP-vDBkC_pF7LdyGU1f_ufZb_NWNBZQ/edit?usp=sharing",
    "github:google-research/android_world": "https://docs.google.com/spreadsheets/d/1cchzP9dlTZ3WXQTfYNhh3avxoLipqHN75v1Tb86uhHo/edit?gid=0#gid=0",
    "github:likaixin2000/screenspot-pro-gui-grounding": "https://gui-agent.github.io/grounding-leaderboard",
    "github:ethz-spylab/agentdojo": "https://agentdojo.spylab.ai/results/",
    "github:imeanai/webcanvas": "https://github.com/iMeanAI/WebCanvas/blob/main/Mind2web-live_Leaderboard.md",
    "github:jetastra/macagentbench": "https://jetastra.github.io/MacAgentBench/",
    "github:mcgill-nlp/agent-reward-bench": "https://huggingface.co/spaces/McGill-NLP/agent-reward-bench-leaderboard",
    "github:mcgill-nlp/safearena": "https://huggingface.co/spaces/McGill-NLP/safearena-leaderboard",
    "github:osu-nlp-group/mind2web-2": "https://osu-nlp-group.github.io/Mind2Web-2/#leaderboard",
    "github:osu-nlp-group/online-mind2web": "https://huggingface.co/spaces/osunlp/Online_Mind2Web_Leaderboard",
    "github:servicenow/workarena": "https://huggingface.co/spaces/ServiceNow/browsergym-leaderboard",
    "github:stonybrooknlp/appworld": "https://appworld.dev/appworld/leaderboard",
    "github:theagentcompany/theagentcompany": "https://the-agent-company.com/#/leaderboard",
    "github:thudm/agentbench": "https://docs.google.com/spreadsheets/d/e/2PACX-1vRR3Wl7wsCgHpwUw1_eUXW_fptAPLL3FkhnW_rua0O1Ji_GIVrpTjY5LaKAhwO-WeARjnY_KNw0SYNJ/pubhtml",
    "github:thudm/android-lab": "https://docs.google.com/spreadsheets/d/1Zv6mBfd4Ibt8mke24K6zAFrXe4AvEFaBLW3hpJqSgjw/edit?gid=0#gid=0",
    "github:tongyi-mai/mobileworld": "https://tongyi-mai.github.io/MobileWorld/#leaderboard",
    "github:unipat-ai/saas-bench": "https://unipat.ai/benchmarks/SaaS-Bench",
    "url:d9d8e68f19ef0956d189": "https://recreation-bench.cc/#leaderboard",
}


class LeaderboardUrlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl")}
        cls.receipts = {r["id"]: r for r in catalog.read_jsonl(catalog.DATA / "primary-evidence.jsonl")}
        cls.editorial = {e.get("id") or catalog.editorial_identity(e)[0]: e for e in catalog.read_json(catalog.DATA / "editorial.json")}

    def test_benchmarks_record_the_leaderboard_their_reviewed_source_links(self):
        self.assertEqual({rid: r["details"]["leaderboard_url"] for rid, r in self.records.items() if "leaderboard_url" in r["details"]}, LEADERBOARDS)
        for rid in LEADERBOARDS:
            with self.subTest(rid):
                record, receipt = self.records[rid], self.receipts[rid]
                self.assertEqual((record["kind"], record["review_status"]), ("benchmark", "curated"))
                primary = next(ev for ev in record["evidence"] if ev["method"] == "editorial_primary_review")
                self.assertEqual((primary["url"], primary["sha256"]), (receipt["url"], receipt["sha256"]))
                self.assertEqual(self.editorial[rid]["reviewed_sha256"], receipt["sha256"])
                self.assertTrue({"details", "details.leaderboard_url"} & set(primary["supports"]))

    def test_benchmark_table_links_the_leaderboard_after_the_name(self):
        page = (catalog.ROOT / "docs/benchmarks.md").read_text(encoding="utf-8")
        self.assertIn("| [OSWorld](https://github.com/xlang-ai/OSWorld) · [leaderboard](https://os-world.github.io/) |", page)
        for rid, url in LEADERBOARDS.items():
            with self.subTest(rid):
                self.assertIn(f"[{build.md(self.records[rid]['name'])}]({self.records[rid]['url']}) · [leaderboard]({url}) |", page)
        self.assertIn("A *leaderboard* link after the name is the official leaderboard", page)
        self.assertNotIn("leaderboard", (catalog.ROOT / "docs/datasets.md").read_text(encoding="utf-8").split("\n## ", 1)[0])

    def test_table_row_adds_the_link_only_when_recorded(self):
        row = copy.deepcopy(self.records["github:xlang-ai/osworld"])
        columns = ("Resource", "Description")
        self.assertTrue(build.table_row(row, columns, {}).startswith("| [OSWorld](https://github.com/xlang-ai/OSWorld) · [leaderboard](https://os-world.github.io/) | "))
        del row["details"]["leaderboard_url"]
        self.assertTrue(build.table_row(row, columns, {}).startswith("| [OSWorld](https://github.com/xlang-ai/OSWorld) | "))


class LeaderboardValidationTests(unittest.TestCase):
    def setUp(self):
        self.base = copy.deepcopy(next(r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl") if r["id"] == "github:xlang-ai/osworld"))
        # Without its protocol and paper relation, only the leaderboard rule can fail on this lone record.
        del self.base["details"]["benchmark_protocol"]
        self.base["relations"] = []

    def schema_errors(self, row):
        import jsonschema
        return list(jsonschema.Draft202012Validator(catalog.read_json(catalog.ROOT / "schemas/resource.schema.json"), format_checker=jsonschema.FormatChecker()).iter_errors(row))

    def test_both_validators_reject_a_misplaced_or_non_https_leaderboard(self):
        self.assertEqual(build.validate_records([self.base]), [])
        self.assertEqual(self.schema_errors(self.base), [])
        cases = {"http url": {"details": {"leaderboard_url": "http://os-world.github.io/"}}, "number": {"details": {"leaderboard_url": 1}},
            "dataset": {"kind": "dataset"}, "metadata-only benchmark": {"review_status": "metadata_verified"}}
        for name, change in cases.items():
            with self.subTest(name):
                row = copy.deepcopy(self.base)
                for key, value in change.items():
                    row[key] = {**row[key], **value} if isinstance(value, dict) else value
                self.assertIn("github:xlang-ai/osworld: leaderboard_url must be an https URL on a curated benchmark", build.validate_records([row]))
                self.assertTrue(self.schema_errors(row))


if __name__ == "__main__":
    unittest.main()
