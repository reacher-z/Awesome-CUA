"""An empty catalog search names what matched nothing and offers each condition as a removal with its result count."""
import json
import re
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Boots web/app.js against a minimal DOM stub (the pattern used in tests/web.test.mjs) and reports the rendered state.
SCRIPT = r"""
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const [app, coverageFile, search] = process.argv.slice(1);
const coverage = JSON.parse(readFileSync(coverageFile, 'utf8'));
const base = {url: 'https://example.org/', aliases: [], topics: [], authors: [], summary: 'Fixture.', review_status: 'curated', published_at: null, scope: 'core', paper_version: null, paper_source_url: null, paper_date: null, related_count: 0, incoming_relations: []};
const records = [
  ...Array.from({length: 3}, (_, i) => ({...base, id: `url:ios-${i}`, name: `Phone tool ${i}`, kind: 'tool', page_url: `/resources/ios-${i}/`, environments: ['ios']})),
  ...Array.from({length: 2}, (_, i) => ({...base, id: `url:bench-${i}`, name: `Grounding bench ${i}`, kind: 'benchmark', page_url: `/resources/bench-${i}/`, environments: ['web']})),
  {...base, id: 'url:solo', name: 'Grounding helper', kind: 'tool', page_url: '/resources/solo/', environments: ['web']},
];
const elements = new Map(), element = selector => {
  if (!elements.has(selector)) elements.set(selector, {dataset: {}, listeners: {}, classList: {toggle() {}}, addEventListener(type, fn) { (this.listeners[type] ??= []).push(fn); }, setAttribute() {}, scrollIntoView() {}, focus() {}, showModal() {}, close() {}});
  return elements.get(selector);
};
const globals = {document: {documentElement: {}, body: {classList: {toggle() {}}}, addEventListener() {}, querySelector: element, querySelectorAll: () => []},
  window: {addEventListener() {}}, location: {search, pathname: '/', hash: ''}, history: {replaceState() {}}, localStorage: {getItem: () => null, setItem() {}},
  fetch: async () => ({ok: true, json: async () => ({coverage, records})})};
for (const [key, value] of Object.entries(globals)) Object.defineProperty(globalThis, key, {value, configurable: true, writable: true});
await import(pathToFileURL(app).href);
await new Promise(resolve => setImmediate(resolve));
const snapshot = () => ({empty: element('#empty').hidden, title: element('#empty-title').textContent ?? '', relax: element('#empty-relax').innerHTML ?? '', pager: element('#pagination').hidden, count: element('#results-count').innerHTML});
const before = snapshot();
const relax = element('#empty-relax').listeners.click?.[0];
if (relax) relax({target: {closest: () => ({disabled: false, dataset: {relax: 'platform'}})}});
console.log(JSON.stringify({before, after: snapshot()}));
"""


@unittest.skipUnless(shutil.which("node"), "Node is required to run the catalog application")
class EmptySearchStateTests(unittest.TestCase):
    def render(self, search):
        result = subprocess.run(["node", "--input-type=module", "-e", SCRIPT, str(ROOT / "web/app.js"), str(ROOT / "data/coverage.json"), search],
                                capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_each_active_condition_is_offered_with_the_count_its_removal_restores(self):
        state = self.render("?q=grounding&kind=benchmark&platform=ios")["before"]
        self.assertFalse(state["empty"])
        self.assertEqual(state["title"], "No resources match all of these filters.")
        buttons = dict((key, count) for key, count in re.findall(r'data-relax="(\w+)"[^>]*>.*?<span class="relax-count">([^<]*)</span>', state["relax"]))
        # Without the search: 0 iOS benchmarks; without "Benchmarks": 0 iOS records named grounding; without iOS: 2 grounding benchmarks.
        self.assertEqual(buttons, {"q": "still none", "kind": "still none", "platform": "2 results"})
        self.assertIn('data-relax="q" disabled', state["relax"])
        self.assertIn("Search “grounding”", state["relax"])
        self.assertIn("Platform: iOS", state["relax"])

    def test_removing_one_condition_keeps_the_others(self):
        after = self.render("?q=grounding&kind=benchmark&platform=ios")["after"]
        self.assertTrue(after["empty"])
        self.assertRegex(after["count"], r"^<strong>2</strong> resources")

    def test_query_only_empty_state_names_the_query_without_redundant_buttons(self):
        state = self.render("?q=zzqx")["before"]
        self.assertEqual(state["title"], "No resources match “zzqx”.")
        self.assertEqual(state["relax"], "")

    def test_single_page_of_results_hides_the_pager(self):
        self.assertTrue(self.render("?q=grounding")["before"]["pager"])
        self.assertTrue(self.render("?q=zzqx")["before"]["pager"])


if __name__ == "__main__":
    unittest.main()
