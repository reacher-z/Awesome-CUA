"""Resource pages show reviewed relations in both directions as one labeled list with kind, year and evidence."""
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from search_pages import connections_html, incoming_relations, resource_body, resource_path

ROWS = [json.loads(line) for line in (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]
LOOKUP = {row["id"]: row for row in ROWS}
INCOMING = incoming_relations(ROWS)


class Items(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items, self._field, self.headings, self._h2 = [], None, [], False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        cls = attrs.get("class", "")
        if tag == "h2":
            self._h2 = True
            self.headings.append([attrs.get("id"), ""])
        if tag == "li" and cls == "relation-item":
            self.items.append({"type": "", "kind": "", "name": "", "href": "", "year": "", "evidence": ""})
        if self.items and tag in ("span", "a"):
            field = {"relation-type": "type", "relation-name": "name", "relation-year": "year", "relation-evidence": "evidence"}.get(cls) or ("kind" if "topic-kind" in cls else None)
            if field:
                self._field = field
                if field in ("name", "evidence"):
                    self.items[-1]["href" if field == "name" else "evidence"] = attrs["href"]

    def handle_endtag(self, tag):
        self._field = None
        if tag == "h2":
            self._h2 = False

    def handle_data(self, data):
        if self._h2:
            self.headings[-1][1] += data
        if self._field and self._field != "evidence":
            self.items[-1][self._field] += data


def parse(markup):
    parser = Items()
    parser.feed(markup)
    return parser


class ResourceConnectionTests(unittest.TestCase):
    def test_both_directions_share_one_section_with_the_paper_library_anchor(self):
        page = parse(resource_body(LOOKUP["github:x-plug/mobileagent"], LOOKUP, INCOMING))
        titles = [title for _, title in page.headings]
        self.assertIn(["connected-assets", "Connections"], page.headings)
        self.assertNotIn("Related resources", titles)
        self.assertNotIn("Connected assets", titles)
        self.assertEqual([item["type"] for item in page.items], ["Documented by"] * 4 + ["Has part"] * 2)

    def test_items_carry_singular_kind_year_link_and_evidence(self):
        page = parse(connections_html(LOOKUP["github:x-plug/mobileagent"], LOOKUP, INCOMING))
        paper = next(item for item in page.items if item["name"].startswith("Mobile-Agent-v3:"))
        self.assertEqual((paper["kind"], paper["year"]), ("Paper", "2025"))
        self.assertTrue(paper["href"].startswith("/resources/arxiv-"))
        self.assertTrue(paper["evidence"].startswith("https://"))
        part = next(item for item in page.items if item["type"] == "Has part")
        self.assertEqual((part["kind"], part["year"]), ("Agent", ""))

    def test_incoming_relations_read_from_the_linked_record(self):
        paper = parse(connections_html(LOOKUP["arxiv:2404.07972"], LOOKUP, INCOMING))
        self.assertIn({"type": "Documents", "kind": "Benchmark", "name": "OSWorld"}, [{k: item[k] for k in ("type", "kind", "name")} for item in paper.items])
        repo = parse(connections_html(LOOKUP["github:xlang-ai/osworld"], LOOKUP, INCOMING))
        self.assertEqual([item["type"] for item in repo.items][0], "Documented by")
        self.assertIn("Used by", [item["type"] for item in repo.items])

    def test_every_catalog_relation_is_shown_once_on_each_end(self):
        for row in ROWS:
            items = parse(connections_html(row, LOOKUP, INCOMING)).items
            expected = sum(rel["target_id"] in LOOKUP for rel in row["relations"]) + len(INCOMING.get(row["id"], []))
            self.assertEqual(len(items), expected, row["id"])
            self.assertTrue(all(item["kind"] and item["type"] and item["evidence"] for item in items), row["id"])

    def test_records_without_relations_have_no_section(self):
        lonely = next(row for row in ROWS if not row["relations"] and not INCOMING.get(row["id"]))
        self.assertEqual(connections_html(lonely, LOOKUP, INCOMING), "")


if __name__ == "__main__":
    unittest.main()
