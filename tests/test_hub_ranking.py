"""Topic and platform hubs rank non-paper resources by in-catalog mentions in a compact table."""
import copy
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build

ROWS = {row["id"]: row for row in map(json.loads, (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines())}


def row(rid, name, environments, **extra):
    base = copy.deepcopy(ROWS["github:xlang-ai/osworld"])
    base.update({"id": rid, "name": name, "environments": environments, "relations": [], "details": {}, "licenses": dict.fromkeys(("code", "data", "weights", "document")), **extra})
    return base


def section(markdown, heading):
    return markdown.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


class MentionCountTests(unittest.TestCase):
    def test_counts_distinct_other_cataloged_sources(self):
        edges = [{"source_id": "a", "target_id": "x", "target_in_catalog": True}, {"source_id": "a", "target_id": "x", "target_in_catalog": True},
                 {"source_id": "b", "target_id": "x", "target_in_catalog": True}, {"source_id": "x", "target_id": "x", "target_in_catalog": True},
                 {"source_id": "c", "target_id": "y", "target_in_catalog": False}]
        self.assertEqual(build.mention_counts(edges), {"x": 2})


class HubTableTests(unittest.TestCase):
    columns = build.KIND_COLUMNS["benchmark"][0]

    def test_rows_are_ranked_by_mentions_then_name(self):
        members = [row("u:a", "Alpha", ["android"]), row("u:b", "Beta", ["android"]), row("u:c", "Gamma", ["android", "ios"])]
        lines = build.hub_table(members, self.columns, {}, {"u:c": 7, "u:b": 2}, hub_env="android")
        self.assertEqual(lines[0], "| Resource | Mentions | Other platforms | Scale | Description |")
        self.assertEqual(lines[1], "| --- | ---: | --- | --- | --- |")
        self.assertEqual([re.match(r"\| \[(\w+)\]", line).group(1) for line in lines[2:]], ["Gamma", "Beta", "Alpha"])
        self.assertEqual([line.split(" | ")[1:3] for line in lines[2:]], [["7", "iOS"], ["2", "—"], ["·", "—"]])

    def test_evidence_paper_and_license_sit_in_the_resource_cell(self):
        osworld = ROWS["github:xlang-ai/osworld"]
        cell = build.hub_table([osworld], self.columns, ROWS, {}, hub_env="linux")[2].split(" | ")[0]
        self.assertRegex(cell, r'\[✓\]\(https://[^ )]+ "Source checked \d{4}-\d\d-\d\d"\)<br>\[2404\.07972\]\(https://arxiv\.org/abs/2404\.07972\) \(2024\) · code Apache‑2\.0$')

    def test_a_platform_column_empty_on_every_row_is_dropped(self):
        lines = build.hub_table([row("u:a", "Alpha", ["web"])], self.columns, {}, {}, hub_env="web")
        self.assertEqual(lines[0], "| Resource | Mentions | Scale | Description |")
        topic = build.hub_table([row("u:a", "Alpha", ["web"]), row("u:b", "Beta", ["web"])], self.columns, {}, {})
        self.assertEqual(topic[0], "All entries in this section: Web.")


class GeneratedHubTests(unittest.TestCase):
    def test_android_hub_leads_with_its_most_mentioned_benchmark(self):
        page = (ROOT / "docs/environments/android.md").read_text(encoding="utf-8")
        benchmarks = section(page, "Benchmarks")
        self.assertIn("| Resource | Mentions |", benchmarks)
        self.assertNotIn("| Evidence |", benchmarks)
        first = next(line for line in benchmarks.splitlines() if line.startswith("| ["))
        self.assertTrue(first.startswith("| [AndroidWorld]("), first)

    def test_every_hub_asset_section_is_sorted_by_mentions(self):
        for path in [*(ROOT / "docs/topics").glob("*.md"), *(ROOT / "docs/environments").glob("*.md")]:
            page = path.read_text(encoding="utf-8")
            for heading in ("Benchmarks", "Datasets", "Models", "Agents", "Frameworks"):
                if f"## {heading}\n" not in page:
                    continue
                counts = [0 if cell == "·" else int(cell.replace(",", "")) for cell in re.findall(r"^\| \[.*? \| ([\d,]+|·) \|", section(page, heading), re.M)]
                self.assertTrue(counts, (path.name, heading))
                self.assertEqual(counts, sorted(counts, reverse=True), (path.name, heading))

    def test_papers_keep_newest_first_dates(self):
        papers = section((ROOT / "docs/topics/grounding.md").read_text(encoding="utf-8"), "Papers").strip().splitlines()
        self.assertTrue(papers[0].startswith("| Date | Resource |"), papers[0])
        dates = [line.split(" | ")[0].lstrip("| ").replace("\u2011", "-") for line in papers[2:]]
        self.assertEqual(dates, sorted(dates, reverse=True))


if __name__ == "__main__":
    unittest.main()
