"""Keyboard users can move from the catalog search box straight to the results and clear the query."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Boots web/app.js against a minimal DOM stub (the pattern used in tests/web.test.mjs) and drives the search box's keydown handler.
SCRIPT = r"""
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const [app, coverageFile] = process.argv.slice(1);
const coverage = JSON.parse(readFileSync(coverageFile, 'utf8'));
const records = Array.from({length: 30}, (_, i) => ({id: `url:k-${i}`, name: i % 2 ? `Web tool ${i}` : `Phone tool ${i}`, kind: 'tool', url: 'https://example.org/', page_url: `/resources/k-${i}/`, aliases: [], environments: ['web'], topics: [], authors: [], summary: 'Fixture.', review_status: 'curated', published_at: null, scope: 'core', paper_version: null, paper_source_url: null, paper_date: null, related_count: 0, incoming_relations: []}));
const doc = {documentElement: {}, body: {classList: {toggle() {}}}, addEventListener() {}, querySelectorAll: () => []};
const elements = new Map(), element = selector => {
  if (!elements.has(selector)) elements.set(selector, {selector, dataset: {}, listeners: {}, value: '', classList: {toggle() {}}, addEventListener(type, fn) { (this.listeners[type] ??= []).push(fn); }, setAttribute() {}, scrollIntoView() { this.scrolled = true; }, focus() { doc.activeElement = this; }, showModal() {}, close() {}});
  return elements.get(selector);
};
doc.querySelector = element;
const globals = {document: doc, window: {addEventListener() {}}, location: {search: '?q=phone', pathname: '/', hash: ''}, history: {replaceState() {}}, localStorage: {getItem: () => null, setItem() {}}, fetch: async () => ({ok: true, json: async () => ({coverage, records})})};
for (const [key, value] of Object.entries(globals)) Object.defineProperty(globalThis, key, {value, configurable: true, writable: true});
await import(pathToFileURL(app).href);
await new Promise(resolve => setImmediate(resolve));
const search = element('#search'), keydown = search.listeners.keydown?.[0];
const press = (key, extra = {}) => { let prevented = false; doc.activeElement = search; keydown?.({key, isComposing: false, target: search, preventDefault() { prevented = true; }, ...extra}); return {focus: doc.activeElement?.selector, prevented}; };
const count = () => element('#results-count').innerHTML.match(/<strong>([\d,]+)<\/strong>/)[1];
const out = {handler: Boolean(keydown), before: count()};
out.enter = press('Enter');
out.down = press('ArrowDown');
out.composing = press('Enter', {isComposing: true});
out.letter = press('a');
search.value = 'phone';
out.escape = press('Escape');
out.after = count();
out.cleared = search.value;
console.log(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "Node is required to run the catalog application")
class SearchKeyboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(["node", "--input-type=module", "-e", SCRIPT, str(ROOT / "web/app.js"), str(ROOT / "data/coverage.json")],
                                capture_output=True, text=True, check=True)
        cls.state = json.loads(result.stdout)

    def test_enter_and_down_arrow_move_focus_to_the_first_result(self):
        self.assertTrue(self.state["handler"])
        for key in ("enter", "down"):
            self.assertEqual(self.state[key], {"focus": "#results [data-record]", "prevented": True}, key)

    def test_ime_composition_and_typing_stay_in_the_search_box(self):
        self.assertEqual(self.state["composing"], {"focus": "#search", "prevented": False})
        self.assertEqual(self.state["letter"], {"focus": "#search", "prevented": False})

    def test_escape_clears_the_query_and_restores_every_result(self):
        self.assertEqual(self.state["before"], "15")
        self.assertTrue(self.state["escape"]["prevented"])
        self.assertEqual((self.state["cleared"], self.state["after"]), ("", "30"))

    def test_shortcuts_are_exposed_to_assistive_technology(self):
        html = (ROOT / "web/index.html").read_text(encoding="utf-8")
        field = re.search(r'<input id="search"[^>]*>', html).group(0)
        self.assertIn('aria-keyshortcuts="/"', field)
        description = re.search(r'aria-describedby="([^"]+)"', field).group(1)
        self.assertRegex(html, rf'<span id="{description}" class="sr-only" data-i18n="searchKeys">[^<]*Enter[^<]*Escape[^<]*</span>')
        app = (ROOT / "web/app.js").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"searchKeys:'", app)), 2)


if __name__ == "__main__":
    unittest.main()
