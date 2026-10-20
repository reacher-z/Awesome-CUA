"""A single resource is labeled with the singular kind (Benchmark, Model), never its plural category name, and list rows name the kind once."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from search_pages import incoming_relations, resource_body

ROWS = [json.loads(line) for line in (ROOT / "data/catalog.jsonl").read_text(encoding="utf-8").splitlines()]
LOOKUP = {row["id"]: row for row in ROWS}
# Boots web/app.js against a DOM stub (the tests/web.test.mjs pattern) and returns the rendered results for grid and list views.
SCRIPT = r"""
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const [app, coverageFile, search] = process.argv.slice(1);
const coverage = JSON.parse(readFileSync(coverageFile, 'utf8'));
const base = {url: 'https://example.org/', aliases: [], topics: [], authors: [], summary: 'Fixture.', review_status: 'curated', published_at: null, scope: 'core', paper_version: null, paper_source_url: null, paper_date: null, related_count: 0, incoming_relations: [], environments: ['web']};
const records = ['benchmark', 'model', 'dataset', 'company'].map(kind => ({...base, id: `url:${kind}`, name: `Fixture ${kind}`, kind, page_url: `/resources/${kind}/`}));
const elements = new Map(), element = selector => {
  if (!elements.has(selector)) elements.set(selector, {dataset: {}, listeners: {}, classList: {toggle() {}}, addEventListener(type, fn) { (this.listeners[type] ??= []).push(fn); }, setAttribute() {}, scrollIntoView() {}, focus() {}, showModal() {}, close() {}});
  return elements.get(selector);
};
Object.assign(globalThis, {document: {documentElement: {}, body: {classList: {toggle() {}}}, addEventListener() {}, querySelector: element, querySelectorAll: () => []},
  window: {addEventListener() {}}, location: {search, pathname: '/', hash: ''}, history: {replaceState() {}}, localStorage: {getItem: () => null, setItem() {}},
  fetch: async () => ({ok: true, json: async () => ({coverage, records})})});
await import(pathToFileURL(app).href);
await new Promise(resolve => setImmediate(resolve));
console.log(JSON.stringify({results: element('#results').innerHTML, categories: element('#categories').innerHTML}));
"""


@unittest.skipUnless(shutil.which("node"), "Node is required to run the catalog application")
class CatalogBadgeTests(unittest.TestCase):
    def render(self, search):
        result = subprocess.run(["node", "--input-type=module", "-e", SCRIPT, str(ROOT / "web/app.js"), str(ROOT / "data/coverage.json"), search],
                                capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_cards_use_singular_kind_chips(self):
        chips = re.findall(r'<span class="kind-chip">([^<]+)</span>', self.render("")["results"])
        self.assertEqual(sorted(chips), ["Benchmark", "Dataset", "Model", "Publisher"])
        self.assertEqual(sorted(re.findall(r'<span class="kind-chip">([^<]+)</span>', self.render("?lang=zh")["results"])), sorted(["评测基准", "模型", "数据集", "发布方"]))

    def test_list_rows_name_the_kind_once(self):
        state = self.render("?view=list")
        for row in re.findall(r'<article class="resource-row".*?</article>', state["results"]):
            kind = re.search(r'<div class="row-date"><span>([^<]+)</span>', row).group(1)
            self.assertIn(kind, {"Benchmark", "Dataset", "Model", "Publisher"})
            self.assertNotRegex(row, r'<div class="row-meta">.*\b(Benchmarks|Datasets|Models|Publishers)\b')
        # Category buttons keep their plural names.
        self.assertIn("<span>Benchmarks</span>", state["categories"])


class ResourcePageBadgeTests(unittest.TestCase):
    def test_resource_eyebrow_is_singular(self):
        incoming = incoming_relations(ROWS)
        for rid, label in (("github:xlang-ai/osworld", "Benchmark"), ("arxiv:2404.07972", "Paper"), ("github:bytedance/ui-tars", "Model")):
            body = resource_body(LOOKUP[rid], LOOKUP, incoming)
            self.assertTrue(body.startswith(f'<div class="eyebrow">{label}</div>'), rid)


if __name__ == "__main__":
    unittest.main()
