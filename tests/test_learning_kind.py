"""Learning records remain visible across routes, topic exports and publication."""
import contextlib
import copy
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build
import catalog
import prepare_publication
import test_resource_payloads as payloads
import topic_pages
from search_pages import KINDS, SITE, resource_path
from test_paper_library import LibraryParser


def learning(name="Browser course", slug="browser-course"):
    url = "https://example.org/learn/" + slug
    row = payloads.paper("2401.00001")
    row.update(id=catalog.canonical(url)[0], name=name, kind="learning", url=url,
               authors=[], identifiers={}, published_at=None, updated_at=None,
               links=[{"rel": "primary", "url": url}], relations=[],
               environments=["web"], topics=["web-navigation"],
               summary="A worked browser-agent lesson with explicit source and execution limits.",
               details={})
    row["evidence"] = [{
        "role": "primary", "method": "editorial_primary_review",
        "supports": ["name", "kind", "summary", "scope", "environments", "topics", "licenses.document"],
        "url": url, "sha256": "a" * 64, "retrieved_at": row["last_verified_at"],
    }]
    row["details"]["license_review"] = {
        "document": {"reason": "The inspected source does not establish document reuse rights.", "evidence_urls": [url]}
    }
    return row


class LearningPublicationTests(unittest.TestCase):
    write_json = payloads.ResourcePayloadTests.write_json
    write_inputs = payloads.ResourcePayloadTests.write_inputs
    build_site = payloads.ResourcePayloadTests.build_site

    def setUp(self):
        payloads.ResourcePayloadTests.setUp(self)
        self.lessons = [learning("Browser <course> & practice"), learning("Vision tutorial", "vision-tutorial")]
        self.rows += self.lessons
        self.write_inputs(self.rows)

    def test_learning_routes_records_counts_and_publication_are_complete(self):
        self.build_site()
        pages = {item["path"]: item for item in json.loads(
            (self.build / "data/search-manifest.json").read_text(encoding="utf-8"))["pages"]}
        category = "/categories/learning/"
        markup = (self.build / category.lstrip("/") / "index.html").read_text(encoding="utf-8")
        self.assertTrue(pages[category]["indexable"])
        self.assertIn(f'<link rel="canonical" href="{SITE}{category}">', markup)
        self.assertIn("Browse 2 reviewed learning resources", markup)
        self.assertIn("Browser &lt;course&gt; &amp; practice", markup)
        self.assertNotIn("Browser <course>", markup)
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', markup, re.S)[1])["@graph"]
        listing = next(row for row in graph if row["@type"] == "ItemList")
        self.assertEqual(listing["numberOfItems"], 2)
        self.assertEqual({row["url"] for row in listing["itemListElement"]},
                         {SITE + resource_path(row) for row in self.lessons})
        for lesson in self.lessons:
            folder = self.build / resource_path(lesson).lstrip("/")
            self.assertEqual(json.loads((folder / "record.json").read_text(encoding="utf-8")), lesson)
            body = (folder / "index.html").read_text(encoding="utf-8")
            self.assertIn("Learning resources", body)
            self.assertIn(lesson["details"]["license_review"]["document"]["reason"], body)
            self.assertFalse((folder / "citation.bib").exists())
        for path in ("index.html", "zh/index.html", "catalog/index.html", "404.html"):
            self.assertIn('href="/categories/learning/"', (self.build / path).read_text(encoding="utf-8"), path)
        self.assertIn(f'id="stat-kinds">{len({row["kind"] for row in self.rows})}</span>',
                      (self.build / "index.html").read_text(encoding="utf-8"))
        self.assertIn("学习资源", (self.build / "zh/index.html").read_text(encoding="utf-8"))
        rag = [json.loads(line) for line in (self.build / "downloads/rag-documents.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual({row["id"] for row in rag}, {row["id"] for row in self.rows if row["review_status"] == "curated"})
        citations = json.loads((self.build / "downloads/citations.csl.json").read_text(encoding="utf-8"))
        self.assertEqual({row["id"] for row in citations}, {self.reviewed["id"], self.survey["id"]})
        topics = json.loads((self.build / "downloads/topics.json").read_text(encoding="utf-8"))
        entry = next(row for row in topics["topics"] if row["id"] == "web-navigation")
        self.assertEqual(entry["counts"]["total"], entry["counts"]["learning"])
        self.assertEqual(entry["counts"]["learning"], 2)
        self.assertEqual(entry["counts"]["total"], sum(entry["counts"][slug] for slug, _, _ in topic_pages.GROUPS))
        for language, path in entry["pages"].items():
            content = (self.build / path.lstrip("/") / "index.html").read_text(encoding="utf-8")
            self.assertEqual(set(LibraryParser(content).records), {row["id"] for row in self.lessons})
            self.assertIn("学习资源" if language == "zh" else "Learning resources", content)
        self.assertEqual(set(KINDS), catalog.KINDS)
        profile = self.root / "profile-checkout"
        (profile / ".git").mkdir(parents=True)
        with mock.patch.object(prepare_publication, "ROOT", self.root), \
                mock.patch.object(sys, "argv", ["prepare_publication.py", "--site-dir", str(self.site),
                                                "--profile-dir", str(profile)]), \
                contextlib.redirect_stdout(io.StringIO()):
            prepare_publication.main()
        readme = (self.site / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"| Learning resources | 2 | [Open directory]({SITE}/categories/learning/) |", readme)
        profile_text = (profile / "profile/README.md").read_text(encoding="utf-8")
        self.assertIn(f"[Learning resources]({SITE}/categories/learning/)", profile_text)
        self.assertIn("![Live catalog counts]", profile_text)
        self.assertNotIn("**11 categories**", profile_text)
        self.assertEqual((self.site / category.lstrip("/") / "index.html").read_bytes(),
                         (self.build / category.lstrip("/") / "index.html").read_bytes())


class LearningGroupingTests(unittest.TestCase):
    def setUp(self):
        self.lessons = [learning(), learning("Vision tutorial", "vision-tutorial")]
        self.paper = payloads.paper("2401.00002")
        self.paper.update(environments=["web"], topics=["web-navigation"])
        self.tool = copy.deepcopy(self.lessons[0])
        self.tool.update(id="github:example/tool", kind="tool", url="https://github.com/example/tool", name="Tool")
        self.pending = payloads.paper("2401.00003", "metadata_verified")
        self.pending["topics"] = ["web-navigation"]
        self.rows = [self.paper, self.tool, *self.lessons, self.pending]

    def test_learning_group_survives_topic_pagination_and_bilingual_exports(self):
        members = topic_pages.reviewed_topics(self.rows)["web-navigation"]
        counts = topic_pages.topic_counts(members)
        self.assertEqual(counts["total"], 4)
        self.assertEqual(counts["learning"], 2)
        with mock.patch.object(topic_pages, "PAGE_SIZE", 2), tempfile.TemporaryDirectory() as tmp:
            manifest, _ = topic_pages.write_topic_exports(tmp, self.rows, b"fixture catalog")
            self.assertEqual(topic_pages.topic_page_count(counts), 2)
            exported = [json.loads(line) for line in
                        (Path(tmp) / "downloads/topics/web-navigation/records.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual({row["id"] for row in exported}, {row["id"] for row in members})
            cited = json.loads((Path(tmp) / "downloads/topics/web-navigation/citations.csl.json").read_text(encoding="utf-8"))
            self.assertEqual([row["id"] for row in cited], [self.paper["id"]])
            for language in ("en", "zh"):
                all_ids = []
                for number in (1, 2):
                    markup, schema = topic_pages.topic_body("web-navigation", members, resource_path,
                                                          language=language, number=number)
                    ids = LibraryParser(markup).records
                    self.assertEqual(schema["numberOfItems"], len(ids))
                    self.assertEqual([item["url"] for item in schema["itemListElement"]],
                                     [SITE + resource_path({"id": rid}) for rid in ids])
                    all_ids.extend(ids)
                self.assertEqual(len(all_ids), len(set(all_ids)))
                self.assertEqual(set(all_ids), {row["id"] for row in members})
                target = topic_pages.topic_path("web-navigation", language, 2) + "#learning"
                self.assertEqual(topic_pages.topic_sections("web-navigation", counts, language)["learning"], target)
                self.assertIn(target, LibraryParser(topic_pages.topic_index_body(manifest, language=language)[0]).links)
                markdown = topic_pages.topic_markdown("web-navigation", members, resource_path, language=language)
                self.assertIn("## 学习资源" if language == "zh" else "## Learning resources", markdown)
                self.assertNotIn(self.pending["name"], markdown)

    def test_markdown_category_topic_platform_and_readme_include_learning(self):
        rows = [*self.lessons, self.pending]
        report = {
            "as_of_utc": "2026-10-20T00:00:00Z", "total_records": 3, "curated_records": 2,
            "metadata_only_records": 1, "bibliographic_records": 1, "arxiv_archive_records": 1,
            "excluded_records": 0, "discovery_identifiers": 0, "unindexed_candidates": 0,
            "pending_editorial": [], "sources": [], "primary_search": {},
            "license_declarations_by_scope": {}, "exclusion_revalidation_pending": 0,
            "curated_by_kind_and_environment": {"learning": {"web": 2}},
        }
        files = build.documents(rows, report)
        self.assertTrue(files["docs/learning.md"].startswith("# Learning resources"))
        self.assertNotIn("docs/learnings.md", files)
        for path in ("docs/learning.md", "docs/topics/web-navigation.md", "docs/environments/web.md"):
            for lesson in self.lessons:
                self.assertEqual(files[path].count(f"[{lesson['name']}]("), 1, path)
            self.assertNotIn(self.pending["name"], files[path])
        for path in ("docs/topics/web-navigation.md", "docs/environments/web.md"):
            self.assertIn("[Learning resources (2)](#learning-resources)", files[path])
        self.assertIn("| 2 | · | · | · | · | 2 | · |", files["docs/topics.md"])
        self.assertIn("| 2 | · | · | · | · | 2 | · |", files["docs/environments.md"])
        self.assertIn("[learning](learning.md)", files["docs/coverage.md"])
        for language, label in (("en", "Learning resources"), ("zh", "学习资源")):
            self.assertIn(f"[{label}](docs/learning.md) · **2**", build.explore(rows, report, language))
            self.assertNotIn("docs/learning.md", build.explore([self.pending], report, language))
        reviewed_at = {lesson["id"]: "2026-10-20T00:00:00Z" for lesson in self.lessons}
        self.assertIn("| Learning resources |", build.recently_reviewed(self.lessons, reviewed_at))
        self.assertIn("| 学习资源 |", build.recently_reviewed(self.lessons, reviewed_at, lang="zh"))

    def test_existing_topic_count_manifests_remain_readable_without_the_new_group(self):
        counts = {"total": 1, "papers": 1, "benchmarks": 0, "datasets": 0, "models": 0, "systems": 0}
        manifest = {"resources_with_topics": 1, "topics": [
            {"id": "web-navigation", "name": {"en": "Web navigation", "zh": "网页导航"}, "counts": counts}]}
        self.assertEqual(topic_pages.topic_page_count(counts), 1)
        self.assertEqual(topic_pages.topic_sections("web-navigation", counts), {"papers": "/topics/web-navigation/#papers"})
        for language in ("en", "zh"):
            markup, schema = topic_pages.topic_index_body(manifest, language=language)
            self.assertEqual(schema["numberOfItems"], 1)
            self.assertNotIn("#learning", markup)
            self.assertIn("学习资源" if language == "zh" else "Learning resources", markup)


if __name__ == "__main__":
    unittest.main()
