import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build
import catalog
import paper_library
import topic_pages
import test_resource_payloads


def osworld():
    row = next(r for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl") if r["id"] == "arxiv:2404.07972")
    return {**copy.deepcopy(row), "relations": []}


class TopicVocabularyTests(unittest.TestCase):
    def test_every_entry_has_a_slug_labels_and_a_definition(self):
        self.assertEqual(list(catalog.TOPICS), sorted(catalog.TOPICS))
        for topic, entry in catalog.TOPICS.items():
            with self.subTest(topic=topic):
                self.assertRegex(topic, r"^[a-z]+(-[a-z]+)*$")
                self.assertEqual(set(entry), {"en", "zh", "definition"})
                self.assertTrue(all(isinstance(value, str) and value.strip() for value in entry.values()))

    def test_committed_catalog_and_editorial_topics_are_in_the_vocabulary(self):
        used = {t for r in catalog.read_jsonl(catalog.DATA / "catalog.jsonl") for t in r["topics"]}
        used |= {t for entry in catalog.read_json(catalog.DATA / "editorial.json", []) for t in entry.get("topics", [])}
        self.assertTrue(used)
        self.assertEqual(used - catalog.TOPICS.keys(), set())

    def test_unknown_record_topics_fail_validation(self):
        row = osworld()
        self.assertEqual(build.validate_records([row]), [])
        row["topics"] = ["grounding", "gui-grounding", "Grounding"]
        self.assertEqual(build.validate_records([row]), ["arxiv:2404.07972: unknown topics Grounding, gui-grounding"])

    def test_validate_rejects_unknown_editorial_topics(self):
        entry = {"url": "https://github.com/example/agent", "name": "Example", "kind": "agent", "environments": ["web"], "topics": ["evaluation", "rl"]}
        with tempfile.TemporaryDirectory() as directory:
            catalog.write_jsonl(Path(directory) / "catalog.jsonl", [osworld()])
            catalog.write_json(Path(directory) / "editorial.json", [entry])
            catalog.write_json(Path(directory) / "task-classes.json", catalog.read_json(catalog.DATA / "task-classes.json"))
            with mock.patch.object(build, "DATA", Path(directory)), self.assertRaises(ValueError) as raised:
                build.validate(types.SimpleNamespace())
        self.assertEqual(str(raised.exception), "Editorial https://github.com/example/agent: unknown topics rl")

    def test_every_consumer_uses_the_vocabulary_labels(self):
        self.assertEqual(build.topic_label("grounding"), catalog.TOPICS["grounding"]["en"])
        self.assertEqual(build.TOPIC_LABELS, {topic: entry["en"] for topic, entry in catalog.TOPICS.items()})
        self.assertEqual(paper_library.TOPICS, {topic: (entry["en"], entry["zh"]) for topic, entry in catalog.TOPICS.items()})
        self.assertEqual(topic_pages.topic_name("ui-design", "zh"), catalog.TOPICS["ui-design"]["zh"])
        self.assertNotRegex((ROOT / "web/app.js").read_text(encoding="utf-8"), r"'(?:grounding|ui-design|world-models)':\[")

    def test_data_dictionary_lists_every_topic_with_its_meaning(self):
        text = (ROOT / "docs/data-dictionary.md").read_text(encoding="utf-8")
        block = re.search(r"<!-- TOPICS:START -->(.*?)<!-- TOPICS:END -->", text, re.S)[1]
        self.assertEqual(block, build.topic_vocabulary())
        for topic, entry in catalog.TOPICS.items():
            self.assertIn(f"| `{topic}` | {entry['en']} | {entry['zh']} | {entry['definition']} |", block)

    def test_site_index_carries_the_labels_for_the_web_app(self):
        fixture = test_resource_payloads.ResourcePayloadTests("test_topic_subsets_and_bilingual_pages_remove_stale_members_after_review_changes")
        fixture.setUp()
        try:
            fixture.reviewed["topics"] = ["ui-design"]
            fixture.write_inputs(fixture.rows)
            fixture.build_site()
            index = json.loads((fixture.build / "data/index.json").read_text(encoding="utf-8"))
            page = (fixture.build / "topics/ui-design/index.html").read_text(encoding="utf-8")
        finally:
            fixture.doCleanups()
        self.assertEqual(index["topics"], {topic: [entry["en"], entry["zh"]] for topic, entry in catalog.TOPICS.items()})
        self.assertIn("<h1>" + catalog.TOPICS["ui-design"]["en"], page)


if __name__ == "__main__":
    unittest.main()
