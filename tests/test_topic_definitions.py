from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build
from catalog import TOPICS
from search_pages import resource_path
from test_resource_payloads import paper
from topic_pages import topic_body, topic_markdown


def row(rid, topics, status="curated"):
    return {"id": rid, "name": rid, "kind": "benchmark", "review_status": status, "url": "https://example.com/" + rid, "environments": ["web"],
        "topics": topics, "summary": rid + ".", "published_at": None, "relations": [], "details": {},
        "licenses": {"code": None, "data": None, "weights": None, "document": None},
        "evidence": [{"method": "editorial_primary_review", "url": "https://example.com/" + rid, "retrieved_at": "2026-10-16T00:00:00Z"}]}


class ReadmeTopicLineTests(unittest.TestCase):
    report = {"bibliographic_records": 0}

    def test_line_counts_curated_tags_once_and_breaks_ties_by_topic_key(self):
        rows = [row("github:a/one", ["planning", "grounding", "grounding"]), row("github:a/two", ["planning"]), row("github:a/three", ["memory"]),
            row("github:a/pending", ["memory", "memory", "safety-security"], status="metadata_verified")]
        for lang, label, everything in (("en", "By topic:", "all 3 →"), ("zh", "按主题：", "全部 3 项 →")):
            explore = build.explore(rows, self.report, lang)
            links = " · ".join(f"[{TOPICS[t][lang]}](docs/topics/{t}.md) **{n}**" for t, n in (("planning", 2), ("grounding", 1), ("memory", 1)))
            self.assertTrue(explore.endswith(f"\n\n**{label}** {links} · [{everything}](docs/topics.md)\n"), explore)
            self.assertLess(explore.index("**By platform:**" if lang == "en" else "**按平台：**"), explore.index(label))
            self.assertNotIn("safety-security", explore)

    def test_line_lists_only_the_twelve_largest_topics(self):
        vocabulary = sorted(TOPICS)[:13]
        rows = [row(f"github:a/{i}", vocabulary[:13 - i]) for i in range(13)]
        explore = build.explore(rows, self.report)
        self.assertEqual(re.findall(r"\(docs/topics/([a-z-]+)\.md\)", explore), vocabulary[:12])
        self.assertIn(f"[{TOPICS[vocabulary[0]]['en']}](docs/topics/{vocabulary[0]}.md) **13**", explore)
        self.assertIn("[all 13 →](docs/topics.md)", explore)

    def test_no_line_without_curated_topics(self):
        self.assertNotIn("By topic", build.explore([row("github:a/b", [])], self.report))

    def test_committed_readmes_carry_the_localized_line(self):
        for name, label in (("README.md", "**By topic:** "), ("README.zh-CN.md", "**按主题：** ")):
            block = re.search(r"<!-- EXPLORE:START -->.*?<!-- EXPLORE:END -->", (ROOT / name).read_text(encoding="utf-8"), re.S).group(0)
            line = next(line for line in block.splitlines() if line.startswith(label))
            self.assertEqual(len(re.findall(r"\]\(docs/topics/[a-z-]+\.md\)", line)), 12)


class TopicDefinitionTests(unittest.TestCase):
    def test_markdown_hubs_start_with_the_definition(self):
        rows = [row("github:a/bench", ["grounding", "sandbox"]), row("github:a/other", ["not-in-vocabulary"])]
        files = build.topic_pages(rows)
        for topic in ("grounding", "sandbox"):
            paragraphs = files[f"docs/topics/{topic}.md"].split("\n\n")
            self.assertEqual(paragraphs[2], TOPICS[topic]["definition"])
            self.assertTrue(paragraphs[3].startswith(f"1 source-reviewed resources tagged `{topic}`."))
        self.assertTrue(files["docs/topics/not-in-vocabulary.md"].split("\n\n")[2].startswith("1 source-reviewed resources"))

    def test_committed_markdown_hubs_start_with_the_definition(self):
        hubs = sorted((ROOT / "docs/topics").glob("*.md"))
        self.assertTrue(hubs)
        for hub in hubs:
            self.assertEqual(hub.read_text(encoding="utf-8").split("\n\n")[2], TOPICS[hub.stem]["definition"], hub.name)

    def test_website_topic_pages_start_with_the_definition(self):
        record = paper("2401.00001")
        record.update(topics=["observability"], environments=["web"])
        definition = TOPICS["observability"]["definition"]
        for lang in ("en", "zh"):
            markup, _ = topic_body("observability", [record], resource_path, language=lang)
            self.assertIn(f'</h1><p class="topic-intro"><span lang="en">{definition}</span> ', markup)
            self.assertEqual(topic_markdown("observability", [record], resource_path, language=lang).split("\n\n")[1], definition)
        markup, _ = topic_body("not-in-vocabulary", [record], resource_path)
        self.assertIn('</h1><p class="topic-intro">Source-reviewed research', markup)


if __name__ == "__main__":
    unittest.main()
