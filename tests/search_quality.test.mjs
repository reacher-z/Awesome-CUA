// Search quality and size against the built site: node --test tests/search_quality.test.mjs (after scripts/build_site.py).
// The ranking code is the block between "search-core:begin" and "search-core:end" in web/assets/site.js, run as is.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';

const site = new URL('../dist/site/data/', import.meta.url);
const source = readFileSync(new URL('../web/assets/site.js', import.meta.url), 'utf8');
const begin = source.indexOf('// search-core:begin'), end = source.indexOf('// search-core:end');
const core = new Function(source.slice(begin, end) + '; return {rowRecord, rankNames, setText, vocab, rank, clearScores};')();
const {queries, top} = JSON.parse(readFileSync(new URL('./e2e/search_queries.json', import.meta.url), 'utf8'));
const INDEX_BUDGET = 200 * 1024;

const built = existsSync(new URL('search-index.json', site));
if (!built && process.env.CI) throw new Error('dist/site is missing: run python3 scripts/build_site.py first');

function load(suffix, withText = true) {
  core.clearScores();
  const index = JSON.parse(readFileSync(new URL(`search-index${suffix}.json`, site), 'utf8'));
  const list = index.rows.map((row, i) => core.rowRecord(row, i, index.kinds, index.topics));
  core.rankNames(list);
  list.topics = index.topics;
  if (withText) core.setText(list, JSON.parse(readFileSync(new URL(`search-text${suffix}.json`, site), 'utf8')));
  core.vocab(list);
  return list;
}

test('the query file lists at least ten real searches, typos included', () => {
  assert.ok(queries.length >= 10);
  assert.ok(queries.some(q => /typo/.test(q.note)));
  for (const q of queries) assert.ok(q.q && q.expect.length, JSON.stringify(q));
});

for (const [suffix, label] of [['', 'English'], ['.zh', 'Chinese']]) {
  test(`${label} index: every expected record ranks in the top ${top}`, {skip: !built && 'site not built'}, () => {
    const list = load(suffix), ids = new Set(list.map(r => r.id));
    const misses = [];
    for (const {q, expect} of queries) {
      for (const id of expect) assert.ok(ids.has(id), `${id} is not in the ${label} index`);
      const got = core.rank(list, q).res.slice(0, top).map(r => r.id);
      if (!got.some(id => expect.includes(id))) misses.push(`${q}: ${got.join(', ')}`);
    }
    assert.deepEqual(misses, []);
  });

  test(`${label} index: names find their record before the summaries load`, {skip: !built && 'site not built'}, () => {
    const list = load(suffix, false);
    for (const {q, expect, note} of queries.filter(q => !/topic/.test(q.note))) {
      const got = core.rank(list, q).res.slice(0, top).map(r => r.id);
      assert.ok(got.some(id => expect.includes(id)), `${q} (${note}): ${got.join(', ')}`);
    }
  });

  test(`${label} index stays within ${INDEX_BUDGET / 1024} KB gzip`, {skip: !built && 'site not built'}, () => {
    const bytes = gzipSync(readFileSync(new URL(`search-index${suffix}.json`, site))).length;
    assert.ok(bytes <= INDEX_BUDGET, `search-index${suffix}.json is ${bytes} bytes gzip`);
  });
}
