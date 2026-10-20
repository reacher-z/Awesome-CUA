"""Counts of 1,000 or more use thousands separators on every generated directory and status page, as on the home page."""
import html
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_site import build_site
from topic_pages import topic_index_body

# A bare run of four or more digits that is not part of an identifier, date, dimension or revision.
BARE = re.compile(r"(?<![\w.,/:#×=+-])(\d{4,})(?![\w.,/:×-])")


def bare_numbers(markup):
    text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", markup, flags=re.S)))
    found = []
    for match in BARE.finditer(text):
        context = text[max(0, match.start() - 30):match.end() + 20]
        # Years and checkpoint dates such as "CogAgent 9B 20241220" are not counts.
        if not 1990 <= int(match.group(1)) <= 2035 and not re.search(r"\d{8}", context):
            found.append(context.strip())
    return found


class NumberFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.site = Path(build_site(cls.temp.name))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_directory_and_status_pages_have_no_bare_large_counts(self):
        pages = [self.site / "updates/index.html", self.site / "topics/index.html", self.site / "zh/topics/index.html",
                 *self.site.glob("categories/*/index.html"), *self.site.glob("topics/*/index.html"), *self.site.glob("zh/topics/*/index.html")]
        self.assertGreater(len(pages), 40)
        for page in pages:
            self.assertEqual(bare_numbers(page.read_text(encoding="utf-8")), [], page.relative_to(self.site))

    def test_research_category_and_scan_counts_are_separated(self):
        papers = (self.site / "categories/paper/index.html").read_text(encoding="utf-8")
        self.assertRegex(papers, r"Browse \d{1,3}(,\d{3})+ reviewed research papers")
        updates = (self.site / "updates/index.html").read_text(encoding="utf-8")
        self.assertRegex(updates, r"Reviewed papers at scan completion</dt><dd>\d{1,3}(,\d{3})+</dd>")
        badge = (self.site / "badges/catalog.svg").read_text(encoding="utf-8")
        self.assertRegex(badge, r'aria-label="\d{1,3}(,\d{3})+ resources, \d{1,3}(,\d{3})+ reviewed resources, \d{1,3}(,\d{3})+ reviewed papers"')

    def test_topic_counts_are_formatted_at_any_size(self):
        counts = {"total": 12345, "papers": 12000, "benchmarks": 1200, "datasets": 0, "models": 0, "systems": 1145}
        manifest = {"resources_with_topics": 12345, "topics": [{"id": "grounding", "name": {"en": "GUI grounding", "zh": "GUI 定位"}, "counts": counts}]}
        index = topic_index_body(manifest)[0]
        for text in ("12,000", "1,200", "1,145", "12,345"):
            self.assertIn(text, index)
        self.assertEqual(bare_numbers(index), [])


if __name__ == "__main__":
    unittest.main()
