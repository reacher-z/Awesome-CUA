"""Topic pages list benchmarks, datasets, models and systems before papers, with each asset's paper year, scale and licenses."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import topic_pages
from topic_pages import GROUPS, asset_facts, asset_paper, reviewed_topics, topic_body, topic_counts, topic_index_body, topic_sections

ROWS = [json.loads(line) for line in (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]
TOPICS = reviewed_topics(ROWS)


def resource_path(row):
    return "/resources/" + re.sub(r"[^a-z0-9]+", "-", row["id"].lower()).strip("-") + "/"


class Headings(HTMLParser):
    def __init__(self):
        super().__init__()
        self.groups, self.items, self._facts = [], {}, None
        self._current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h2" and attrs.get("id"):
            self.groups.append(attrs["id"])
        if tag == "article" and "data-resource-id" in attrs:
            self._current = attrs["data-resource-id"]
            self.items[self._current] = {"year": "", "facts": ""}
        if tag == "span" and attrs.get("class") == "topic-paper-year":
            self._facts = "year"
        if tag == "p" and attrs.get("class") == "topic-resource-facts":
            self._facts = "facts"

    def handle_endtag(self, tag):
        if (tag == "span" and self._facts == "year") or (tag == "p" and self._facts == "facts"):
            self._facts = None

    def handle_data(self, data):
        if self._current and self._facts:
            self.items[self._current][self._facts] += data


class TopicAssetsFirstTests(unittest.TestCase):
    def test_groups_put_assets_before_papers(self):
        self.assertEqual([slug for slug, _, _ in GROUPS], ["benchmarks", "datasets", "models", "systems", "papers"])

    def test_grounding_benchmarks_are_on_the_first_page(self):
        members = TOPICS["grounding"]
        page = Headings()
        page.feed(topic_body("grounding", members, resource_path)[0])
        self.assertEqual(page.groups[0], "benchmarks")
        self.assertLess(page.groups.index("datasets"), page.groups.index("models"))
        self.assertIn("github:likaixin2000/screenspot-pro-gui-grounding", page.items)
        sections = topic_sections("grounding", topic_counts(members))
        self.assertEqual(sections["benchmarks"], "/topics/grounding/#benchmarks")
        self.assertTrue(sections["papers"].startswith("/topics/grounding/page/"))

    def test_asset_rows_show_paper_year_scale_and_licenses(self):
        osworld = next(row for row in ROWS if row["id"] == "github:xlang-ai/osworld")
        page = Headings()
        page.feed(topic_body("evaluation", TOPICS["evaluation"], resource_path)[0])
        item = page.items["github:xlang-ai/osworld"]
        self.assertEqual(item["year"], "2024")
        self.assertIn("arXiv 2404.07972", item["facts"])
        self.assertIn("369 task definitions", item["facts"])
        self.assertIn("Code Apache-2.0", item["facts"])
        zh = [text for _, text, _ in asset_facts(osworld, zh=True)]
        self.assertIn("代码 Apache-2.0", zh)

    def test_unrecorded_facts_are_left_out(self):
        bare = {"kind": "tool", "relations": [{"type": "documented_by", "target_id": "url:abc"}], "licenses": {"code": None}, "details": {}}
        self.assertIsNone(asset_paper(bare))
        self.assertEqual(asset_facts(bare), [])
        counted = {"kind": "dataset", "relations": [], "licenses": {}, "details": {"dataset_profile": {"counts": [
            {"unit": "episodes", "value": 715142, "qualifier": "exact"}, {"unit": "episodes", "value": 5, "qualifier": "exact"},
            {"unit": "screenshots", "value": 104000, "qualifier": "more-than"}]}}}
        self.assertEqual([text for _, text, _ in asset_facts(counted)], ["715,142 episodes", "> 104,000 screenshots"])

    def test_papers_keep_their_own_dates_without_asset_facts(self):
        page = Headings()
        markup = topic_body("grounding", TOPICS["grounding"], resource_path, number=5)[0]
        page.feed(markup)
        papers = [rid for rid in page.items if rid.startswith("arxiv:")]
        self.assertTrue(papers)
        self.assertTrue(all(not page.items[rid]["facts"] and not page.items[rid]["year"] for rid in papers))

    def test_directory_columns_follow_the_page_order(self):
        manifest = {"resources_with_topics": 1, "topics": [{"id": "grounding", "name": {"en": "GUI grounding", "zh": "GUI 定位"}, "counts": topic_counts(TOPICS["grounding"])}]}
        header = re.search(r"<thead>(.*?)</thead>", topic_index_body(manifest)[0]).group(1)
        self.assertEqual(re.findall(r'class="topic-col-(\w+)"', header), ["benchmarks", "datasets", "models", "systems", "papers"])


if __name__ == "__main__":
    unittest.main()
