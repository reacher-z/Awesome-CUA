"""Comparison tables can be sorted by newest paper, show each profile's paper, and keep their header visible while scrolling."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from specifications import comparison_body, profile_paper

ROWS = [json.loads(line) for line in (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]
LOOKUP = {row["id"]: row for row in ROWS}
SCRIPT = r"""
import {pathToFileURL} from 'node:url';
const [compare, rowsJSON, search] = process.argv.slice(1);
const appended = [];
const body = {append: element => appended.push(element.name)};
const profiles = JSON.parse(rowsJSON).map(([name, paper]) => ({name, parentElement: body, hidden: false, dataset: {search: name, environments: 'web', paper}}));
const control = (value = '', options = []) => ({value, options: options.map(value => ({value})), listeners: {}, addEventListener(type, fn) { this.listeners[type] = fn; }});
const elements = {'#compare-query': control(), '#compare-environment': control('', ['']), '#compare-results': {textContent: ''}, '#compare-sort': control('', ['', 'newest'])};
const urls = [];
Object.assign(globalThis, {document: {querySelector: s => elements[s], querySelectorAll: s => s === '[data-profile-row]' ? profiles : []},
  location: {search, href: 'https://awesomecua.github.io/compare/benchmarks/' + search}, history: {replaceState: (a, b, url) => urls.push(String(url))}});
await import(pathToFileURL(compare).href);
const initial = appended.splice(0);
elements['#compare-sort'].value = '';
elements['#compare-sort'].listeners.change();
console.log(JSON.stringify({initial, reset: appended.splice(0), url: urls.at(-1)}));
"""


class CompareSortingTests(unittest.TestCase):
    def test_profile_paper_prefers_the_introducing_paper_and_orders_by_month(self):
        row = {"relations": [{"type": "documented_by", "target_id": "arxiv:2501.00002"}, {"type": "introduced_by", "target_id": "arxiv:1412.6980"}]}
        self.assertEqual(profile_paper(row), ("1412.6980", "1412.06980"))
        self.assertEqual(profile_paper({"relations": [{"type": "documented_by", "target_id": "url:abc"}]}), (None, ""))
        self.assertEqual(profile_paper(LOOKUP["github:xlang-ai/osworld"])[0], "2404.07972")

    def test_tables_offer_a_sort_and_show_each_paper(self):
        for kind in ("benchmark", "dataset"):
            body = comparison_body(ROWS, kind, lambda row: "/resources/x/")
            self.assertRegex(body, r'<select id="compare-sort"><option value="">Name A–Z</option><option value="newest">Newest paper first</option></select>')
            keys = re.findall(r'data-paper="([^"]*)"', body)
            self.assertEqual(len(keys), body.count("data-profile-row"))
            self.assertTrue(all(re.fullmatch(r"(\d{4}\.\d{5})?", key) for key in keys))
            self.assertEqual(body.count('class="compare-paper"'), sum(bool(key) for key in keys))
        self.assertIn('<a href="https://arxiv.org/abs/2404.07972">arXiv 2404.07972</a> · 2024', comparison_body(ROWS, "benchmark", lambda row: "/x/"))

    def test_header_sticks_below_the_site_header_on_desktop(self):
        css = (ROOT / "web/pages.css").read_text(encoding="utf-8")
        desktop = re.search(r"@media\(min-width:1045px\)\{(\.reading-shell \.compare-scroll\{overflow:visible\}.*?)\}\}", css).group(1)
        self.assertIn(".compare-table thead th{position:sticky;top:82px", desktop)

    @unittest.skipUnless(shutil.which("node"), "Node is required to run compare.js")
    def test_newest_order_comes_from_the_url_and_unpapered_rows_keep_name_order_last(self):
        rows = [["Alpha", "2401.00001"], ["Beta", ""], ["Gamma", "2509.00010"], ["Delta", "1412.06980"], ["Epsilon", ""]]
        result = subprocess.run(["node", "--input-type=module", "-e", SCRIPT, str(ROOT / "web/compare.js"), json.dumps(rows), "?sort=newest"],
                                capture_output=True, text=True, check=True)
        state = json.loads(result.stdout)
        self.assertEqual(state["initial"], ["Gamma", "Alpha", "Delta", "Beta", "Epsilon"])
        self.assertEqual(state["reset"], ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"])
        self.assertNotIn("sort=", state["url"])


if __name__ == "__main__":
    unittest.main()
