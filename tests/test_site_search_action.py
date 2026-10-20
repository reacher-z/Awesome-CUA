from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_site import build_site
from search_pages import SITE

OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"


class HeadLinks(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.links = []; self.graphs = []; self._ld = None
        self.feed(text.split("</head>", 1)[0] + "</head>")

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link": self.links.append(a)
        if tag == "script" and a.get("type") == "application/ld+json": self._ld = ""

    def handle_data(self, data):
        if self._ld is not None: self._ld += data

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            self.graphs.append(json.loads(self._ld)); self._ld = None


def query_parameter(template, placeholder):
    # The single query parameter whose value is the placeholder, e.g. q for ?q={searchTerms}.
    parts = urlsplit(template)
    names = [name for name, values in parse_qs(parts.query).items() if values == [placeholder]]
    return parts.scheme + "://" + parts.netloc + parts.path, names


class SiteSearchActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(); cls.dest = build_site(cls.temp.name)
        cls.home = HeadLinks((cls.dest / "index.html").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def website(self):
        nodes = [node for graph in self.home.graphs for node in graph.get("@graph", [graph]) if node.get("@type") == "WebSite"]
        self.assertEqual(len(nodes), 1)
        return nodes[0]

    def test_website_names_and_languages(self):
        site = self.website()
        self.assertEqual(site["@id"], SITE + "/#website")
        self.assertEqual(site["name"], "AwesomeCUA")
        self.assertEqual(site["alternateName"], ["Awesome-CUA", "Awesome Computer-Use Agents"])
        self.assertEqual(site["inLanguage"], ["en", "zh-CN"])

    def test_search_action_targets_the_catalog_query(self):
        action = self.website()["potentialAction"]
        self.assertEqual(action["@type"], "SearchAction")
        self.assertEqual(action["query-input"], "required name=search_term_string")
        self.assertEqual(action["target"]["@type"], "EntryPoint")
        base, names = query_parameter(action["target"]["urlTemplate"], "{search_term_string}")
        self.assertEqual((base, names), (SITE + "/", ["q"]))

    def test_opensearch_description_matches_search_action(self):
        root = ET.parse(self.dest / "opensearch.xml").getroot()
        self.assertEqual(root.tag, OPENSEARCH + "OpenSearchDescription")
        short = root.find(OPENSEARCH + "ShortName").text
        self.assertTrue(0 < len(short) <= 16)
        self.assertLessEqual(len(root.find(OPENSEARCH + "Description").text), 1024)
        urls = {url.get("type"): url for url in root.findall(OPENSEARCH + "Url")}
        self.assertEqual(urls["text/html"].get("method"), "get")
        self.assertEqual(query_parameter(urls["text/html"].get("template"), "{searchTerms}"), (SITE + "/", ["q"]))
        self.assertEqual(urls["application/opensearchdescription+xml"].get("template"), SITE + "/opensearch.xml")

    def test_catalog_app_reads_the_same_parameter(self):
        source = (ROOT / "web/catalog-core.js").read_text(encoding="utf-8")
        self.assertRegex(source, r"q:p\.get\('q'\)")

    def test_every_html_page_links_the_opensearch_description(self):
        pages = json.loads((self.dest / "data/search-manifest.json").read_text())["pages"]
        # The survey page is a frozen bundle copied byte-for-byte and checked against its SHA-256, so it carries no site chrome.
        paths = [item["path"] for item in pages if item["path"] != "/survey/"] + ["/404.html"]
        for path in paths:
            target = self.dest / path.lstrip("/")
            if path.endswith("/"): target = target / "index.html"
            links = [link for link in HeadLinks(target.read_text(encoding="utf-8")).links if link.get("rel") == "search"]
            with self.subTest(path=path):
                self.assertEqual([(l.get("type"), l.get("href")) for l in links], [("application/opensearchdescription+xml", "/opensearch.xml")])


if __name__ == "__main__":
    unittest.main()
