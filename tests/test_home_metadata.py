from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_site import build_site


class HeadParser(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.title = ""; self.meta = {}; self._in_title = False
        self.feed(text.split("</head>", 1)[0])

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title": self._in_title = True
        key = a.get("property") or a.get("name")
        if tag == "meta" and key: self.meta.setdefault(key, []).append(a.get("content"))

    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False

    def handle_data(self, data):
        if self._in_title: self.title += data


def page_title(language):
    # The app resets document.title from TEXT.<language>.pageTitle after it loads.
    source = (ROOT / "web/app.js").read_text(encoding="utf-8")
    return re.search(rf"Object\.assign\(TEXT\.{language},\{{pageTitle:'([^']*)'", source)[1]


class HomeMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.head = HeadParser((build_site(cls.temp.name) / "index.html").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_title_names_the_list_and_gui_agents(self):
        title = self.head.title
        self.assertLessEqual(len(title), 70)
        self.assertIn("Awesome Computer-Use Agents", title)
        self.assertIn("GUI", title)
        self.assertEqual(title.count("AwesomeCUA"), 1)

    def test_static_social_and_script_titles_agree(self):
        self.assertEqual(self.head.meta["og:title"], [self.head.title])
        self.assertEqual(page_title("en"), self.head.title)
        self.assertIn("Awesome Computer-Use Agents", page_title("zh"))
        self.assertRegex(page_title("zh"), r"[\u4e00-\u9fff]")

    def test_description_covers_resource_kinds_and_platforms(self):
        [description] = self.head.meta["description"]
        self.assertTrue(120 <= len(description) <= 160, len(description))
        for term in ("papers", "models", "datasets", "benchmarks", "GUI", "web", "browser", "mobile"):
            self.assertIn(term, description)
        self.assertEqual(self.head.meta["og:description"], [description])

    def test_locale_alternate_points_to_chinese(self):
        self.assertEqual(self.head.meta["og:locale"], ["en_US"])
        self.assertEqual(self.head.meta["og:locale:alternate"], ["zh_CN"])


if __name__ == "__main__":
    unittest.main()
