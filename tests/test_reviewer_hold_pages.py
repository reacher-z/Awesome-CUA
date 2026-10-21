import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import search_pages


class ReviewerHoldPageTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "id": "arxiv:2601.00001", "name": "Interface evidence pending",
            "kind": "paper", "url": "https://arxiv.org/abs/2601.00001",
            "summary": None, "review_status": "metadata_verified",
            "scope": "relevance_pending", "environments": ["unspecified"],
            "topics": [], "authors": [], "aliases": [],
            "identifiers": {"arxiv": "2601.00001"}, "details": {},
            "published_at": None, "updated_at": None, "relations": [],
            "links": [], "evidence": [], "licenses": {
                "code": None, "data": None, "weights": None, "document": None,
            },
            "last_verified_at": "2026-10-01T00:00:00Z",
            "notes": "Bibliographic metadata is retained.",
        }
        self.hold = {
            "id": self.record["id"], "cause": "reviewer_hold",
            "reason": "Section 3 leaves <interface> unresolved & needs evidence.",
        }

    def render(self, record=None, decision=None):
        record = record or self.record
        return search_pages.resource_body(record, {record["id"]: record},
                                          pending_review=decision)

    def test_current_hold_is_visible_and_escaped_in_both_reading_formats(self):
        body = self.render(decision=self.hold)
        markdown = search_pages.resource_markdown(self.record, self.hold)
        for content in (body, markdown):
            self.assertIn("Recorded reviewer hold", content)
            self.assertIn("&lt;interface&gt; unresolved &amp; needs evidence", content)
            self.assertIn("/downloads/coverage.json", content)
            self.assertNotIn("<interface>", content)
        self.assertIn('<details class="review-hold" open>', body)

    def test_approval_hides_a_stale_hold_without_rewriting_the_record(self):
        approved = copy.deepcopy(self.record)
        approved.update(review_status="curated", scope="core",
                        summary="A reviewed interface method.")
        self.assertNotIn("Recorded reviewer hold", self.render(approved, self.hold))
        self.assertNotIn("Recorded reviewer hold",
                         search_pages.resource_markdown(approved, self.hold))

    def test_other_id_unreviewed_snapshot_or_empty_reason_is_not_a_hold(self):
        for decision in (
            None, {}, {**self.hold, "id": "arxiv:2601.00002"},
            {**self.hold, "cause": "unreviewed_snapshot"},
            {**self.hold, "reason": ""}, {**self.hold, "reason": None},
        ):
            with self.subTest(decision=decision):
                self.assertNotIn("Recorded reviewer hold", self.render(decision=decision))
                self.assertNotIn("Recorded reviewer hold",
                                 search_pages.resource_markdown(self.record, decision))

    def test_display_does_not_promote_index_or_mutate_source_data(self):
        record_before, hold_before = copy.deepcopy(self.record), copy.deepcopy(self.hold)
        body = self.render(decision=self.hold)
        html = search_pages.page(
            self.record["name"], "Pending source review",
            search_pages.resource_path(self.record), body,
            index=search_pages.eligible(self.record),
        )
        self.assertIn('content="noindex,follow"', html)
        self.assertFalse(search_pages.eligible(self.record))
        self.assertEqual(self.record, record_before)
        self.assertEqual(self.hold, hold_before)

    def test_markdown_reason_does_not_become_a_link_heading_or_list(self):
        decision = {**self.hold, "reason":
                    "See [result](https://example.com).\n## Plain heading\n- Plain item\nUse `schema` & <node>."}
        markdown = search_pages.resource_markdown(self.record, decision)
        self.assertIn(r"\[result\]\(https://example\.com\)\.", markdown)
        self.assertIn(r"\#\# Plain heading", markdown)
        self.assertIn(r"\- Plain item", markdown)
        self.assertIn(r"\`schema\` &amp; &lt;node&gt;\.", markdown)
        self.assertNotIn("[result](https://example.com)", markdown)
        self.assertNotIn("\n## Plain heading", markdown)


if __name__ == "__main__":
    unittest.main()
