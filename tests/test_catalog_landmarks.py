"""The home catalog's landmarks and ARIA attributes follow ARIA in HTML: no nested complementary landmark, no aria-label on a role-less div."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANDMARKS = {"aside", "main", "nav", "header", "footer"}
# Elements whose implicit role permits aria-label; a plain div or span needs an explicit role first.
NAMEABLE = {"a", "button", "input", "select", "textarea", "nav", "main", "section", "aside", "dialog", "form", "img", "svg", "table", "code", "header", "footer", "article"}


class Tree(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.nested_asides, self.unnamed_roles, self.elements = [], [], [], {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "aside" and any(t == "section" or t in LANDMARKS for t, _ in self.stack):
            self.nested_asides.append(attrs)
        if "aria-label" in attrs and tag not in NAMEABLE and not attrs.get("role"):
            self.unnamed_roles.append((tag, attrs.get("id") or attrs.get("class")))
        if attrs.get("id"):
            self.elements[attrs["id"]] = (tag, attrs)
        if tag not in {"img", "input", "meta", "link", "br", "source", "path", "rect", "circle"}:
            self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


class CatalogLandmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = Tree()
        cls.tree.feed((ROOT / "web/index.html").read_text(encoding="utf-8"))

    def test_no_complementary_landmark_is_nested_in_a_region(self):
        self.assertEqual(self.tree.nested_asides, [])

    def test_aria_labels_sit_on_elements_whose_role_allows_a_name(self):
        self.assertEqual(self.tree.unnamed_roles, [])

    def test_results_are_a_named_region_and_categories_a_named_group(self):
        tag, attrs = self.tree.elements["results"]
        self.assertEqual((attrs.get("role"), attrs.get("aria-label"), attrs.get("data-i18n-label")), ("region", "Catalog results", "resultsLabel"))
        html = (ROOT / "web/index.html").read_text(encoding="utf-8")
        self.assertIn('<div class="sidebar" role="group" aria-label="Resource categories" data-i18n-label="categories">', html)
        self.assertIn('<div class="ecosystem-map" role="group" aria-label="Explore web, desktop, and mobile agents"', html)


if __name__ == "__main__":
    unittest.main()
