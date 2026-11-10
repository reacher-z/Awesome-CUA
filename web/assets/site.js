/* Awesome CUA site script. Vanilla, no dependencies. Every feature degrades to links and forms without it.
   Modules: theme · header · search engine (lazy index) · command window (home) · palette (⌘K) · catalog facets ·
   copy/share · tabs · sheets · cursor glide. */
(() => {
  const d = document, root = d.documentElement, $ = (s, c = d) => c.querySelector(s), $$ = (s, c = d) => [...c.querySelectorAll(s)];
  const ZH = (root.lang || '').startsWith('zh');
  const INDEX_URL = ZH ? '/data/search-index.zh.json' : '/data/search-index.json', EXPLORE = '/explore/', CATALOG = '/catalog/';
  const store = {get(k) { try { return localStorage.getItem(k) } catch (e) { return null } },
    set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v) } catch (e) {} }};
  const sess = {get(k) { try { return sessionStorage.getItem(k) } catch (e) { return null } },
    set(k, v) { try { sessionStorage.setItem(k, v) } catch (e) {} }};
  const fmt = new Intl.NumberFormat('en-US').format; // one formatter; toLocaleString builds a new one per call
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const icon = (n, c = 'i') => `<svg class="${c}" aria-hidden="true"><use href="#i-${n}"/></svg>`;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');

  /* ---------- toast ---------- */
  const toastEl = $('#site-toast');
  let toastT;
  function toast(msg) {
    if (!toastEl) return;
    toastEl.innerHTML = icon('check') + esc(msg);
    toastEl.setAttribute('data-show', '');
    clearTimeout(toastT);
    toastT = setTimeout(() => toastEl.removeAttribute('data-show'), 1800);
  }
  async function copy(text, msg) {
    try { await navigator.clipboard.writeText(text) } catch (e) {
      const t = d.createElement('textarea'); t.value = text; t.style.position = 'fixed'; t.style.opacity = '0';
      d.body.append(t); t.select(); try { d.execCommand('copy') } catch (_) {} t.remove();
    }
    toast(msg || (ZH ? '已复制' : 'Copied'));
  }

  /* ---------- theme: auto -> light -> dark ---------- */
  const themeBtn = $('[data-theme-toggle]');
  const THEMES = ['auto', 'light', 'dark'];
  function applyTheme(t) {
    if (t === 'auto') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', t);
    if (!themeBtn) return;
    const label = ZH ? {auto: '跟随系统', light: '浅色', dark: '深色'}[t] : {auto: 'follows system', light: 'light', dark: 'dark'}[t];
    themeBtn.setAttribute('aria-label', (ZH ? '颜色主题：' : 'Color theme: ') + label);
    themeBtn.innerHTML = icon(t === 'auto' ? 'auto' : t === 'light' ? 'sun' : 'moon');
  }
  let theme = store.get('cua-theme') || 'auto';
  applyTheme(theme);
  themeBtn && themeBtn.addEventListener('click', () => {
    theme = THEMES[(THEMES.indexOf(theme) + 1) % 3];
    store.set('cua-theme', theme === 'auto' ? null : theme);
    applyTheme(theme);
    toast(ZH ? {auto: '主题：跟随系统', light: '主题：浅色', dark: '主题：深色'}[theme] : {auto: 'Theme follows your system', light: 'Light theme', dark: 'Dark theme'}[theme]);
  });

  /* ---------- header: compact after scroll; on home, reveal the search trigger once the window scrolls away ---------- */
  const header = $('.site-header');
  if (header && 'IntersectionObserver' in window) {
    const s = d.createElement('div'); s.style.cssText = 'position:absolute;top:0;height:8px;width:1px;pointer-events:none';
    d.body.prepend(s);
    new IntersectionObserver(([e]) => header.classList.toggle('is-scrolled', !e.isIntersecting)).observe(s);
    const fin = $('#finder .field');
    if (fin) new IntersectionObserver(([e]) => header.classList.toggle('show-search', !e.isIntersecting && e.boundingClientRect.top < 0)).observe(fin);
  }

  /* ---------- relative times ---------- */
  $$('time[data-ago]').forEach(t => {
    const mins = Math.max(1, Math.round((Date.now() - Date.parse(t.dateTime)) / 60000));
    const zh = t.dataset.lang === 'zh' || ZH;
    if (mins < 60 * 24 * 3) t.textContent = mins < 60 ? (zh ? mins + ' 分钟前' : mins + ' min ago') : (zh ? Math.round(mins / 60) + ' 小时前' : Math.round(mins / 60) + ' h ago');
  });

  /* ---------- build stamp: the star count and last scan, read once from a small same-origin file ---------- */
  const shortCount = n => {
    if (n < 1000) return String(n);
    const tenths = Math.floor(n / 100);
    return tenths >= 100 || tenths % 10 === 0 ? Math.floor(tenths / 10) + 'k' : (tenths / 10).toFixed(1) + 'k';
  };
  const starEls = $$('[data-star-count]').filter(e => !e.textContent), slots = $$('[data-last-scan-slot]');
  if (slots.length || starEls.length) {
    fetch('/data/site-stamp.json').then(r => r.ok ? r.json() : null).then(s => {
      if (!s) return;
      starEls.forEach(e => { const n = (s.stars || {})[e.dataset.starCount]; if (n) e.textContent = shortCount(n) });
      if (s.last_scan) slots.forEach(e => {
        const t = d.createElement('time'); t.dateTime = s.last_scan; t.textContent = ' ' + s.last_scan.slice(0, 16).replace('T', ' ') + ' UTC'; e.replaceWith(t);
      });
    }).catch(() => {}).finally(() => root.classList.add('stars-settled')); // an unfilled slot collapses
  }

  /* ---------- announcement bar: dismissal is remembered in this browser only ---------- */
  const sheetTheme = $('[data-sheet-theme]');
  if (sheetTheme && themeBtn) sheetTheme.addEventListener('click', () => themeBtn.click());
  const dismiss = $('[data-dismiss-announce]');
  if (dismiss) dismiss.addEventListener('click', () => {
    store.set('cua-announce', 'websitebench');
    root.classList.add('announce-off');
    const brand = $('.site-header .brand'); if (brand) brand.focus();
  });

  /* ---------- search engine ---------- */
  let IDX = null, idxP = null, txtP = null;
  const TEXT_URL = ZH ? '/data/search-text.zh.json' : '/data/search-text.json';
  const onText = []; // views that render again once the summaries arrive
  const ENV_BITS = {web: 1, desktop: 2, mobile: 4, cross: 8};
  const ENV_NAMES = ZH ? {1: '网页', 2: '桌面', 4: '手机', 8: '跨平台'} : {1: 'Web', 2: 'Desktop', 4: 'Mobile', 8: 'Cross-platform'};
  const ENV_IC = {1: 'web', 2: 'desktop', 4: 'mobile', 8: 'cross'};
  const KIND_LABEL = ZH ? {benchmark: '评测基准', dataset: '数据集', model: '模型', agent: '智能体', framework: '框架', tool: '工具', infrastructure: '基础设施', product: '产品', company: '发布方', paper: '论文', survey: '综述', learning: '学习资源'}
    : {benchmark: 'Benchmark', dataset: 'Dataset', model: 'Model', agent: 'Agent', framework: 'Framework', tool: 'Tool', infrastructure: 'Infrastructure', product: 'Product', company: 'Publisher', paper: 'Paper', survey: 'Survey', learning: 'Learning'};
  const KIND_PLURAL = ZH ? KIND_LABEL : {benchmark: 'Benchmarks', dataset: 'Datasets', model: 'Models', agent: 'Agents', framework: 'Frameworks', tool: 'Tools', infrastructure: 'Infrastructure', product: 'Products', company: 'Publishers', paper: 'Papers', survey: 'Surveys', learning: 'Learning'};
  const KIND_IC = {benchmark: 'gauge', dataset: 'database', model: 'cube', agent: 'pointer', framework: 'layers', tool: 'wrench', infrastructure: 'server', product: 'box', company: 'building', paper: 'file', survey: 'book', learning: 'cap'};
  // search-core:begin — pure ranking code; tests/search_quality.test.mjs runs this block against the built index.
  const SYN = {grounding: ['ground', 'screenspot'], trajectories: ['trajectory', 'episodes'], trajectory: ['trajectories'], phone: ['mobile', 'android'], browser: ['web'], gui: ['ui']};
  const KIND_WORDS = {benchmark: 'benchmark', benchmarks: 'benchmark', bench: 'benchmark', dataset: 'dataset', datasets: 'dataset', data: 'dataset', model: 'model', models: 'model', agent: 'agent', agents: 'agent', framework: 'framework', frameworks: 'framework', paper: 'paper', papers: 'paper', survey: 'survey', surveys: 'survey', tool: 'tool', tools: 'tool'};
  const ENV_WORDS = {web: 1, browser: 1, desktop: 2, windows: 2, linux: 2, macos: 2, mac: 2, mobile: 4, android: 4, ios: 4, phone: 4, harmonyos: 4, cross: 8};
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const norm = s => s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9一-鿿]+/g, ' ').trim();
  const nameOrder = new Intl.Collator().compare; // the order String.prototype.localeCompare gives, computed once per record
  // Index row -> record. Everything a keystroke compares is normalised here, once, so typing only reads it.
  function rowRecord(r, i, kinds, topics) {
    const ident = r[8] || 'arXiv ' + r[0].slice(6), id = r[0] || 'github:' + ident.toLowerCase();
    const name = r[1], n = norm(name), x = r[11] || {}, al = (x.a || []).map(norm);
    return {i, id, name, k: kinds[r[2]], env: r[3], y: r[4], f: r[5], d: '', m: r[6], t: r[7], ident, rv: r[9], lic: r[10],
      p: x.p, l: x.l, u: x.u, n, nc: n.replace(/ /g, ''), words: n.split(' '), al, aw: al.join(' ').split(' ').filter(Boolean),
      iw: ident ? norm(ident).split(' ') : [], tp: r[7].map(j => topics[j]), dn: '', dsp: ' '};
  }
  function rankNames(list) { list.slice().sort((a, b) => nameOrder(a.name, b.name)).forEach((rec, i) => { rec.nr = i }) }
  function setText(list, j) {
    if (j.n !== list.length) throw new Error('search text does not match the index');
    list.forEach((rec, i) => { const d = j.d[i] || '', e = j.e && j.e[i]; rec.d = d; rec.dn = norm(e ? d + ' ' + e : d); rec.dsp = ' ' + rec.dn });
  }
  // Damerau-Levenshtein (restricted), early exit beyond max. Three reused rows: no allocation per call.
  const R0 = new Int32Array(66), R1 = new Int32Array(66), R2 = new Int32Array(66);
  function lev(a, b, max) {
    const m = a.length, n = b.length;
    if (Math.abs(m - n) > max) return max + 1;
    if (n > 64) return levLong(a, b, max);
    let p2 = R2, p1 = R1, cur = R0;
    for (let j = 0; j <= n; j++) p1[j] = j;
    for (let i = 1; i <= m; i++) {
      const ca = a.charCodeAt(i - 1), pa = i > 1 ? a.charCodeAt(i - 2) : -1;
      cur[0] = i; let best = i;
      for (let j = 1; j <= n; j++) {
        const cb = b.charCodeAt(j - 1);
        let v = Math.min(p1[j] + 1, cur[j - 1] + 1, p1[j - 1] + (ca === cb ? 0 : 1));
        if (i > 1 && j > 1 && ca === b.charCodeAt(j - 2) && pa === cb) v = Math.min(v, p2[j - 2] + 1);
        cur[j] = v; if (v < best) best = v;
      }
      if (best > max) return max + 1;
      const t = p2; p2 = p1; p1 = cur; cur = t;
    }
    return p1[n];
  }
  function levLong(a, b, max) {
    const m = a.length, n = b.length; let prev2 = null, prev = Array.from({length: n + 1}, (_, j) => j);
    for (let i = 1; i <= m; i++) {
      const cur = [i]; let best = i;
      for (let j = 1; j <= n; j++) {
        let v = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
        if (prev2 && i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) v = Math.min(v, prev2[j - 2] + 1);
        cur[j] = v; if (v < best) best = v;
      }
      if (best > max) return max + 1;
      prev2 = prev; prev = cur;
    }
    return prev[n];
  }
  // Each distinct word points at the records that hold it, per field, so a keystroke compares a few thousand distinct
  // words instead of every word of every record. Summaries join the "d" field when they arrive.
  function addWords(V, list, from, to, fields) {
    const add = (m, w, i) => { let ids = m.get(w); if (!ids) m.set(w, ids = []); if (ids[ids.length - 1] !== i) ids.push(i) };
    for (let i = from; i < to; i++) {
      const rec = list[i];
      if (fields.includes('n')) { for (const w of rec.words) add(V.n, w, i); for (const w of rec.aw) add(V.a, w, i); for (const w of rec.iw) add(V.i, w, i); for (const w of rec.tp) add(V.t, w, i) }
      if (fields.includes('d') && rec.dn) for (const w of rec.dn.split(' ')) add(V.d, w, i);
    }
  }
  // Sorted words per field: the words that start with a token form one contiguous run, found by binary search.
  function sortWords(V) { V.keys = {}; for (const f of 'naitd') V.keys[f] = [...V[f].keys()].sort() }
  function vocab(list) { list.V = {n: new Map(), a: new Map(), i: new Map(), t: new Map(), d: new Map()}; addWords(list.V, list, 0, list.length, 'nd'); sortWords(list.V) }
  function firstAtLeast(keys, t) { let lo = 0, hi = keys.length; while (lo < hi) { const mid = (lo + hi) >> 1; if (keys[mid] < t) lo = mid + 1; else hi = mid } return lo }
  // One query token scored against every record: each record takes the first tier it meets, in this order — exact
  // name word 60 · name word prefix 45 · inside the name 34 · alias 40 · kind 26 · platform 24 · identity 22 ·
  // summary word 16 · topic 14 · one or two typos in a name word 30−6·distance. Kept per token, so each keystroke
  // scores only the token being typed.
  const rawCache = new Map(), tokCache = new Map();
  function rawScores(list, t) {
    let a = rawCache.get(t); if (a) return a;
    a = new Int16Array(list.length);
    const V = list.V, n = list.length;
    const max = t.length >= 8 ? 2 : t.length >= 4 ? 1 : 0, kw = own(KIND_WORDS, t) && KIND_WORDS[t], ew = own(ENV_WORDS, t) && ENV_WORDS[t];
    const mark = (ids, v) => { for (const i of ids) if (!a[i]) a[i] = v };
    const markWords = (f, v) => { const keys = V.keys[f], m = V[f]; for (let k = firstAtLeast(keys, t); k < keys.length && keys[k].startsWith(t); k++) mark(m.get(keys[k]), v) };
    if (V.n.has(t)) mark(V.n.get(t), 60);
    markWords('n', 45);
    if (t.length >= 3) for (let i = 0; i < n; i++) if (!a[i] && list[i].nc.includes(t)) a[i] = 34;
    markWords('a', 40);
    if (kw) for (let i = 0; i < n; i++) if (!a[i] && (kw === list[i].k || (kw === 'paper' && list[i].k === 'survey'))) a[i] = 26;
    if (ew) for (let i = 0; i < n; i++) if (!a[i] && (list[i].env & ew)) a[i] = 24;
    markWords('i', 22);
    markWords('d', 16);
    if (/[一-鿿]/.test(t)) for (let i = 0; i < n; i++) if (!a[i] && list[i].dn.includes(t)) a[i] = 16;
    markWords('t', 14);
    if (max) {
      // A record's first name word within reach sets its score, as in a left-to-right reading of the name.
      const dist = new Map(), near = new Set();
      for (const [w, ids] of V.n) {
        if (Math.abs(w.length - t.length) > max) continue;
        const e = lev(t, w, max);
        if (e <= max) { dist.set(w, e); for (const i of ids) if (!a[i]) near.add(i) }
      }
      for (const i of near) for (const w of list[i].words) { const e = dist.get(w); if (e !== undefined) { a[i] = 30 - 6 * e; break } }
    }
    rawCache.set(t, a);
    return a;
  }
  function tokScores(list, t) {
    let a = tokCache.get(t); if (a) return a;
    if (tokCache.size > 300) { tokCache.clear(); rawCache.clear() }
    const raw = rawScores(list, t), syn = own(SYN, t) ? SYN[t].map(s => rawScores(list, s)) : null;
    a = new Int16Array(list.length);
    const topical = new Uint8Array(list.length), keys = list.V.keys.t;
    for (let k = firstAtLeast(keys, t); k < keys.length && keys[k].startsWith(t); k++) for (const i of list.V.t.get(keys[k])) topical[i] = 1;
    for (let i = 0; i < list.length; i++) {
      let v = raw[i];
      if (v && v < 60 && topical[i]) v += 12; // a topic match lifts a weaker name match
      if (!v && syn) for (const s of syn) v = Math.max(v, s[i] - 6);
      a[i] = v;
    }
    tokCache.set(t, a);
    return a;
  }
  function clearScores() { rawCache.clear(); tokCache.clear() }
  // Results in order, with counts per kind, platform and leaderboard. With a limit, only that many lead results are
  // put in order (the same ones a full sort would put first) and total gives the full count.
  function rank(list, q, {kind = 'all', env = 0, lb = false, sort = 'relevance', limit = 0} = {}) {
    const qn = norm(q), toks = qn ? qn.split(' ') : [], scores = toks.map(t => tokScores(list, t));
    const S = new Int32Array(list.length), res = [], counts = {all: 0}, envCounts = {1: 0, 2: 0, 4: 0, 8: 0};
    let lbCount = 0;
    for (let i = 0; i < list.length; i++) {
      const rec = list[i]; let s = 0;
      if (toks.length) {
        for (const a of scores) { const v = a[i]; if (!v) { s = 0; break } s += v }
        if (!s) continue;
        if (rec.n === qn || rec.al.includes(qn)) s += 1000;
        else if (rec.n.startsWith(qn)) s += 800;
        s += Math.min(48, rec.m * 4) + (rec.f & 2 ? 6 : 0) + (rec.k === 'paper' || rec.k === 'survey' ? -10 : 0);
      } else s = rec.m;
      const envOk = !env || (rec.env & env), lbOk = !lb || (rec.f & 2);
      if (envOk && lbOk) { counts.all++; const kk = rec.k === 'survey' ? 'paper' : rec.k; counts[kk] = (counts[kk] || 0) + 1 }
      const kindOk = kind === 'all' || rec.k === kind || (kind === 'paper' && rec.k === 'survey');
      if (kindOk && lbOk && rec.env) { if (rec.env & 1) envCounts[1]++; if (rec.env & 2) envCounts[2]++; if (rec.env & 4) envCounts[4]++; if (rec.env & 8) envCounts[8]++ }
      if (kindOk && envOk && (rec.f & 2)) lbCount++;
      if (kindOk && envOk && lbOk) { S[i] = s; res.push(rec) }
    }
    const by = {
      relevance: (a, b) => S[b.i] - S[a.i] || b.m - a.m || a.nr - b.nr,
      mentions: (a, b) => b.m - a.m || S[b.i] - S[a.i] || a.nr - b.nr,
      reviewed: (a, b) => b.rv - a.rv || a.nr - b.nr,
      year: (a, b) => b.y - a.y || b.m - a.m || a.nr - b.nr,
      name: (a, b) => a.nr - b.nr,
    };
    const cmp = by[sort] || by.relevance;
    let top = res;
    if (limit && res.length > limit) {
      top = [];
      for (const rec of res) {
        if (top.length === limit && cmp(rec, top[limit - 1]) >= 0) continue;
        let j = top.length; while (j && cmp(rec, top[j - 1]) < 0) j--;
        top.splice(j, 0, rec); if (top.length > limit) top.pop();
      }
    } else top.sort(cmp);
    return {res: top, total: res.length, counts, envCounts, lbCount, toks};
  }
  // search-core:end

  // Normalising ~5,000 rows runs in slices, so loading the index or its summaries never blocks typing for long.
  const yieldTask = () => new Promise(r => setTimeout(r, 0));
  async function sliced(n, fn, size = 400) { for (let i = 0; i < n; i += size) { fn(i, Math.min(n, i + size)); await yieldTask() } }
  function loadIndex() {
    if (idxP) return idxP;
    performance.mark('idx-start');
    idxP = fetch(INDEX_URL).then(r => { if (!r.ok) throw new Error(r.status); return r.json() }).then(async j => {
      const list = new Array(j.rows.length);
      await sliced(list.length, (a, b) => { for (let i = a; i < b; i++) list[i] = rowRecord(j.rows[i], i, j.kinds, j.topics) });
      rankNames(list);
      list.V = {n: new Map(), a: new Map(), i: new Map(), t: new Map(), d: new Map()};
      await sliced(list.length, (a, b) => addWords(list.V, list, a, b, 'n'), 1000);
      sortWords(list.V);
      list.topics = j.topics; list.topicLabels = j.topic_labels; list.licences = j.licences; list.stamp = j.b;
      IDX = list;
      performance.mark('idx-ready'); performance.measure('index-load', 'idx-start', 'idx-ready');
      loadText();
      return IDX;
    });
    idxP.catch(() => { idxP = null });
    return idxP;
  }
  // Summaries arrive second: names, aliases, kinds and topics already answer a search; the summaries add their words
  // and fill the result rows, then every open view renders again.
  function loadText() {
    if (txtP) return txtP;
    txtP = fetch(TEXT_URL).then(r => { if (!r.ok) throw new Error(r.status); return r.json() }).then(async j => {
      if (j.n !== IDX.length || j.b !== IDX.stamp) throw new Error('search text does not match the index');
      await sliced(IDX.length, (a, b) => setText(IDX.slice(a, b), {n: b - a, d: j.d.slice(a, b), e: j.e && j.e.slice(a, b)}));
      const V = {...IDX.V, d: new Map()};
      await sliced(IDX.length, (a, b) => addWords(V, IDX, a, b, 'd'), 1000);
      sortWords(V);
      IDX.V = V;
      clearScores();
      IDX.hasText = true;
      onText.forEach(f => { try { f() } catch (e) {} });
    });
    txtP.catch(() => { txtP = null });
    return txtP;
  }
  // The index waits for the first sign of a search, so a visitor who only reads the page never downloads or parses it.
  const warmIndex = () => loadIndex().catch(() => {});
  $$('#finder').forEach(el => ['pointerover', 'touchstart', 'keydown'].forEach(type => el.addEventListener(type, warmIndex, {once: true, passive: true})));

  function search(q, opts) {
    if (!IDX.hasText) loadText().catch(() => {});
    performance.mark('q-start');
    const r = rank(IDX, q, opts);
    performance.mark('q-end'); performance.measure('query', 'q-start', 'q-end');
    return r;
  }
  // For debugging ranking in the console: CUA_SEARCH.loadIndex().then(() => CUA_SEARCH.search('osworld').res.slice(0, 3))
  window.CUA_SEARCH = {loadIndex, loadText, search};
  function hl(text, toks) {
    if (!toks || !toks.length) return esc(text);
    const words = toks.filter(t => t.length > 1).map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    if (!words.length) return esc(text);
    const re = new RegExp('(^|[^a-z0-9])(' + words.join('|') + ')', 'ig');
    let html = '', last = 0, m;
    while ((m = re.exec(text))) { const st = m.index + m[1].length; html += esc(text.slice(last, st)) + '<mark>' + esc(m[2]) + '</mark>'; last = st + m[2].length; if (re.lastIndex === m.index) re.lastIndex++ }
    return html + esc(text.slice(last));
  }
  const slug = id => id.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  function hrefFor(rec) { return (ZH ? '/zh/resources/' : '/resources/') + slug(rec.id) + '/' }
  // The explorer page searches every record, including those awaiting review; its filters are single-valued.
  const PLATFORM = {web: 'web', desktop: 'desktop', mobile: 'mobile', cross: 'cross-platform'};
  function exploreHref(q, kind, envBits) {
    const p = new URLSearchParams();
    if (q) p.set('q', q);
    if (kind && kind !== 'all') p.set('kind', kind);
    const envs = Object.keys(ENV_BITS).filter(k => envBits & ENV_BITS[k]);
    if (envs.length === 1) p.set('platform', PLATFORM[envs[0]]);
    if (ZH) p.set('lang', 'zh');
    const qs = p.toString();
    return EXPLORE + (qs ? '?' + qs : '') + '#catalog';
  }
  // The directory page lists categories, so a search addressed to it runs in the explorer.
  if (/^\/(zh\/)?catalog\/$/.test(location.pathname)) { const q = new URLSearchParams(location.search).get('q'); if (q) location.replace(exploreHref(q)) }
  function srcFor(rec) {
    if (rec.u) return rec.u;
    if (rec.id.startsWith('arxiv:')) return 'https://arxiv.org/abs/' + rec.id.slice(6);
    if (rec.id.startsWith('github:')) return 'https://github.com/' + rec.ident;
    return hrefFor(rec);
  }
  function envTag(bits) {
    const first = [1, 2, 4, 8].find(b => bits & b); if (!first) return '';
    const more = [1, 2, 4, 8].filter(b => bits & b).length - 1;
    return `<span class="env">${icon(ENV_IC[first])}${ENV_NAMES[first]}${more ? `<span aria-hidden="true">+${more}</span><span class="vh">and ${more} more</span>` : ''}</span>`;
  }
  function rowHTML(rec, toks, detail = true) {
    const k = rec.k, isPaper = rec.id.startsWith('arxiv:'), meta = [];
    if (detail) {
      if (!isPaper) meta.push(`<span>${icon('repo')}<code>${esc(rec.ident)}</code></span>`);
      else meta.push(`<a href="https://arxiv.org/abs/${rec.id.slice(6)}">${icon('file')}${esc(rec.ident)}</a>`);
      if (rec.p) meta.push(`<a href="https://arxiv.org/abs/${rec.p}">${icon('file')}arXiv ${rec.p}</a>`);
      if (rec.l) meta.push(`<a href="${esc(rec.l)}">${icon('trophy')}${ZH ? '排行榜' : 'Leaderboard'}</a>`);
      if (rec.m) meta.push(`<span>${rec.m} ${ZH ? '次提及' : rec.m === 1 ? 'mention' : 'mentions'}</span>`);
    }
    const desc = rec.d || [isPaper && detail ? '' : rec.ident, rec.y].filter(Boolean).join(' · ');
    const idTag = !detail && !isPaper ? `<span class="row-id">${esc(rec.ident)}</span>` : '';
    return `<li class="row" id="r-${slug(rec.id)}"><span class="kind">${icon(KIND_IC[k])}${KIND_LABEL[k]}</span>
<div class="row-main"><h3 class="row-name"><a href="${hrefFor(rec)}" data-src="${esc(srcFor(rec))}">${hl(rec.name, toks)}</a>${idTag}</h3>
<p class="row-desc">${hl(desc, toks)}</p>${meta.length ? `<p class="row-meta">${meta.join('')}</p>` : ''}</div>
<div class="row-side">${envTag(rec.env)}<span class="stamp stamp-ok">${icon('check')}${ZH ? '已审核' : 'Reviewed'}</span></div></li>`;
  }
  function nearNames(q, n = 3) {
    const qn = norm(q).replace(/ /g, ''); if (!qn || !IDX) return [];
    return IDX.filter(r => r.k !== 'paper').map(r => [lev(qn, r.nc.slice(0, qn.length + 2), 6), r]).sort((a, b) => a[0] - b[0] || b[1].m - a[1].m).slice(0, n).map(x => x[1]);
  }
  function emptyHTML(q) {
    const near = nearNames(q);
    return `<li class="empty"><h3>${ZH ? '没有找到' : 'Nothing matches'} “${esc(q)}”</h3><p>${ZH ? '试试更短的名字，或去掉筛选条件。' : 'Try a shorter name or remove a filter. Close names in the catalog:'}</p>
<div class="near">${near.map(r => `<a class="chip" href="${hrefFor(r)}">${esc(r.name)}</a>`).join('')}</div>
<p><a href="https://github.com/reacher-z/Awesome-CUA/issues/new/choose">${ZH ? '提交缺失的资源' : 'Suggest a missing resource'}</a></p></li>`;
  }

  /* recent searches: kept in this browser only; storage failures leave the list empty */
  const RECENT = 'cua-recent';
  function recents() { try { const v = JSON.parse(store.get(RECENT) || '[]'); return Array.isArray(v) ? v.filter(x => typeof x === 'string') : [] } catch (e) { return [] } }
  function addRecent(q) { if (!q) return; const r = [q, ...recents().filter(x => x !== q)].slice(0, 5); store.set(RECENT, JSON.stringify(r)) }
  const recentChips = list => list.map(r => `<button class="chip" type="button" data-recent="${esc(r)}">${icon('clock', 'i i-sm')}${esc(r)}</button>`).join('');

  /* roving focus inside result lists: ↑/↓ move, ⌘/Ctrl+Enter opens the source */
  function roving(list, input) {
    list.addEventListener('keydown', e => {
      const links = $$('.row-name a', list), i = links.indexOf(d.activeElement);
      if (i < 0) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); (links[i + 1] || links[i]).focus() }
      else if (e.key === 'ArrowUp') { e.preventDefault(); i ? links[i - 1].focus() : input && input.focus() }
      else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); open(links[i].dataset.src || links[i].href, '_blank', 'noopener') }
      else if (e.key === 'Escape' && input) { input.focus() }
    });
  }

  /* ---------- the command window (home + 404) ---------- */
  const fin = $('#finder');
  if (fin) {
    const input = $('#q', fin), list = $('#results', fin), count = $('#q-count', fin), field = $('.field', fin);
    const tabs = $$('[data-kind]', fin), chips = $$('[data-env]', fin), lbBtn = $('[data-lb]', fin), sortSel = $('[data-sort]', fin);
    const more = $('[data-more]', fin), moreLabel = $('[data-more-label]', fin), moreN = $('[data-more-n]', fin), panel = $('#filter-panel', fin);
    const TAIL = ['tool', 'infrastructure', 'product', 'company', 'learning'], moreDefault = moreLabel && moreLabel.textContent, moreNDefault = moreN && moreN.textContent;
    const addr = $('[data-address]', fin), seeAll = $('[data-see-all]', fin);
    const defaultRows = list.innerHTML, defCounts = Object.fromEntries($$('[data-count]', fin).map(e => [e.dataset.count, e.textContent]));
    const screenEl = $('[data-screen]');
    const st = {q: '', kind: 'all', env: 0, lb: false, sort: 'mentions'};
    const mid = matchMedia('(max-width: 1023px)');
    if (input.dataset.phShort) { input.dataset.phLong = input.placeholder; const f = () => input.placeholder = mid.matches ? input.dataset.phShort : input.dataset.phLong; f(); mid.addEventListener('change', f) }

    function url() {
      const p = new URLSearchParams();
      if (st.q) p.set('q', st.q); if (st.kind !== 'all') p.set('kind', st.kind);
      const envs = Object.keys(ENV_BITS).filter(k => st.env & ENV_BITS[k]); if (envs.length) p.set('env', envs.join(','));
      if (st.lb) p.set('leaderboard', '1'); if (st.sort !== (st.q ? 'relevance' : 'mentions')) p.set('sort', st.sort);
      return p.toString();
    }
    // The address line updates with every keystroke; the browser URL follows once typing pauses, because
    // history.replaceState costs more than the search itself.
    let urlT = 0, urlNext = null;
    function writeURL() { clearTimeout(urlT); if (urlNext) { urlNext(); urlNext = null } }
    function sync(push) {
      const qs = url();
      const path = (ZH ? '/zh/' : '/');
      if (addr) addr.innerHTML = `<b>awesomecua.com</b>${path}${qs ? `<span class="q">?${esc(decodeURIComponent(qs))}</span>` : ''}`;
      const target = location.pathname + (qs ? '?' + qs : '') + location.hash;
      urlNext = () => { if (target !== location.pathname + location.search + location.hash) history[push ? 'pushState' : 'replaceState'](null, '', target) };
      clearTimeout(urlT);
      if (push || !typingNow) writeURL(); else urlT = setTimeout(writeURL, 300);
      if (seeAll) seeAll.href = exploreHref(st.q, st.kind, st.env);
    }
    let typingNow = false;
    const pristine = () => !st.q && st.kind === 'all' && !st.env && !st.lb && st.sort === 'mentions';
    function render() {
      list.toggleAttribute('data-single', st.kind !== 'all' && st.kind !== 'paper');
      tabs.forEach(t => t.dataset.kind === st.kind ? t.setAttribute('aria-current', 'true') : t.removeAttribute('aria-current'));
      if (more) { const inTail = TAIL.includes(st.kind); more.classList.toggle('is-on', inTail); moreLabel.textContent = inTail ? KIND_PLURAL[st.kind] : moreDefault; }
      chips.forEach(c => c.setAttribute('aria-pressed', String(!!(st.env & ENV_BITS[c.dataset.env]))));
      lbBtn && lbBtn.setAttribute('aria-pressed', String(st.lb));
      field.classList.toggle('has-q', !!st.q);
      if (screenEl && st.q) screenEl.classList.add('is-typing');
      const fn = $('[data-filter-n]', fin); if (fn) fn.textContent = (st.env ? [1, 2, 4, 8].filter(b => st.env & b).length : 0) + (st.lb ? 1 : 0) || '';
      if (pristine()) {
        const rec = d.activeElement === input ? recents() : [];
        list.innerHTML = (rec.length ? `<li class="p-recent"><h3>${ZH ? '最近搜索' : 'Recent searches'}</h3>${recentChips(rec)}</li>` : '') + defaultRows; count.textContent = '';
        Object.entries(defCounts).forEach(([k, v]) => $$(`[data-count="${k}"]`, fin).forEach(e => { e.textContent = v; e.parentElement.classList.remove('is-zero') }));
        if (moreN) moreN.textContent = moreNDefault;
        sync(); return;
      }
      if (!IDX) { list.setAttribute('aria-busy', 'true'); loadIndex().then(render).catch(() => { list.innerHTML = `<li class="empty"><h3>${ZH ? '搜索暂不可用' : 'Search is offline'}</h3><p>${ZH ? '索引未能加载。' : 'The search index did not load. Browse the catalog instead.'} <a href="${CATALOG}">${ZH ? '浏览目录' : 'Open the catalog'}</a></p></li>` }); return }
      list.removeAttribute('aria-busy');
      const r = search(st.q, {...st, limit: 8});
      const t0 = performance.now();
      list.innerHTML = r.res.length ? r.res.map(x => rowHTML(x, r.toks, false)).join('') : emptyHTML(st.q);
      const topRow = st.q && $('.row', list); if (topRow) topRow.classList.add('is-active');
      performance.measure('render', {start: t0, end: performance.now()});
      $$('[data-count]', fin).forEach(e => {
        const k = e.dataset.count, n = k.startsWith('env-') ? r.envCounts[ENV_BITS[k.slice(4)]] : (r.counts[k] || 0);
        e.textContent = fmt(n); e.parentElement.classList.toggle('is-zero', !n);
      });
      if (moreN) moreN.textContent = fmt(TAIL.reduce((a, k) => a + (r.counts[k] || 0), 0));
      if (lbBtn) $('.n', lbBtn).textContent = r.lbCount;
      count.textContent = st.q ? (ZH ? `${fmt(r.total)} 条结果` : `${fmt(r.total)} result${r.total === 1 ? '' : 's'}`) : '';
      if (seeAll) seeAll.innerHTML = (!r.total ? (ZH ? '打开目录' : 'Open the catalog') : ZH ? `查看全部 ${fmt(r.total)} 条` : `See all ${fmt(r.total)} ${st.kind === 'all' ? 'results' : KIND_PLURAL[st.kind].toLowerCase()}`) + icon('right', 'i i-sm');
      sync();
    }
    // The summaries re-render the rows; the row in focus keeps its focus.
    onText.push(() => {
      if (pristine()) return;
      const f = d.activeElement, href = list.contains(f) && f.getAttribute('href');
      render();
      const back = href && $$('.row-name a', list).find(a => a.getAttribute('href') === href);
      if (back) { $$('.row.is-active', list).forEach(r => r.classList.remove('is-active')); back.focus() }
    });
    let settle;
    // A query that stays on screen with results for 1.5 s, or that opens a result, joins the recent searches.
    const keep = () => { writeURL(); if (st.q && $('.row', list)) addRecent(st.q) };
    input.addEventListener('blur', writeURL);
    input.addEventListener('focus', () => { if (pristine() && recents().length) render() });
    list.addEventListener('click', e => {
      const c = e.target.closest('[data-recent]');
      if (c) { input.value = c.dataset.recent; input.dispatchEvent(new Event('input')); input.focus(); return }
      if (e.target.closest('.row-name a')) keep();
    });
    // The first character brings the whole window under the header: the hero and keyboard stop hiding results, and the title bar stays whole.
    let scrolledForQuery = false;
    input.addEventListener('input', () => {
      if (!input.value) scrolledForQuery = false;
      else if (!scrolledForQuery) {
        scrolledForQuery = true;
        const headerEl = $('.site-header'), box = input.closest('.window') || input, top = box.getBoundingClientRect().top - (headerEl ? headerEl.offsetHeight : 0) - 8;
        if (Math.abs(top) > 4) scrollBy({top, behavior: reduce.matches ? 'auto' : 'smooth'});
      }
      const had = !!st.q; st.q = input.value.trim();
      if (st.q && !had && st.sort === 'mentions') { st.sort = 'relevance'; sortSel.value = 'relevance' }
      if (!st.q && had && st.sort === 'relevance') { st.sort = 'mentions'; sortSel.value = 'mentions' }
      typingNow = true; render(); typingNow = false; // in the same task as the keystroke: results paint in the next frame
      clearTimeout(settle); settle = setTimeout(keep, 1500);
    });
    input.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown') { const a = $('.row-name a', list); if (a) { e.preventDefault(); a.focus() } }
      if (e.key === 'Escape') { if (input.value) { input.value = ''; input.dispatchEvent(new Event('input')) } else input.blur() }
    });
    $('[data-finder-form]', fin).addEventListener('submit', e => {
      if (!st.q) return;
      const a = $('.row-name a', list);
      e.preventDefault(); keep(); location.href = a ? a.href : exploreHref(st.q);
    });
    $('.clear', fin).addEventListener('click', () => { input.value = ''; input.dispatchEvent(new Event('input')); input.focus() });
    tabs.forEach(t => t.addEventListener('click', e => { if (e.metaKey || e.ctrlKey || e.shiftKey) return; e.preventDefault(); st.kind = t.dataset.kind; if (more) more.open = false; render(); strip(t) }));
    // kind tabs: fade + arrows only when the strip overflows; the tail of the list lives in "More" from 768 px up
    const stripEl = $('[data-tabstrip]', fin), nav = $('.tabs', stripEl), prev = $('.prev', stripEl), next = $('.next', stripEl);
    const fine = matchMedia('(pointer: fine)');
    function strip(active) {
      if (active && active.closest('.tabs') && active.offsetParent) active.scrollIntoView({block: 'nearest', inline: 'nearest'});
      const over = nav.scrollWidth - nav.clientWidth > 2, st_ = over && nav.scrollLeft > 2, en_ = over && nav.scrollLeft + nav.clientWidth < nav.scrollWidth - 2;
      stripEl.toggleAttribute('data-start', st_); stripEl.toggleAttribute('data-end', en_);
      prev.hidden = !(st_ && fine.matches); next.hidden = !(en_ && fine.matches);
    }
    nav.addEventListener('scroll', () => strip(), {passive: true});
    addEventListener('resize', () => strip());
    prev.addEventListener('click', () => nav.scrollBy({left: -220, behavior: reduce.matches ? 'auto' : 'smooth'}));
    next.addEventListener('click', () => nav.scrollBy({left: 220, behavior: reduce.matches ? 'auto' : 'smooth'}));
    if (d.fonts) { d.fonts.ready.then(() => strip()); d.fonts.addEventListener('loadingdone', () => strip()) } strip();
    if (more) {
      d.addEventListener('click', e => { if (more.open && !more.contains(e.target)) more.open = false });
      more.addEventListener('keydown', e => { if (e.key === 'Escape' && more.open) { e.stopPropagation(); more.open = false; $('summary', more).focus() } });
    }
    chips.forEach(c => c.addEventListener('click', () => { st.env ^= ENV_BITS[c.dataset.env]; render() }));
    lbBtn && lbBtn.addEventListener('click', () => { st.lb = !st.lb; render() });
    sortSel.addEventListener('change', () => { st.sort = sortSel.value; render() });
    roving(list, input);
    // URL -> state (and back/forward)
    function fromURL() {
      const p = new URLSearchParams(location.search);
      st.q = p.get('q') || ''; st.kind = p.get('kind') || 'all'; st.lb = p.get('leaderboard') === '1';
      st.env = (p.get('env') || '').split(',').reduce((a, k) => a | (ENV_BITS[k] || 0), 0);
      st.sort = p.get('sort') || (st.q ? 'relevance' : 'mentions');
      input.value = st.q; sortSel.value = st.sort;
      if (st.q || st.kind !== 'all' || st.env || st.lb || st.sort !== 'mentions') render();
    }
    addEventListener('popstate', () => { clearTimeout(urlT); urlNext = null; fromURL() });
    fromURL();
    // mobile: filters live in a bottom sheet
    const fb = $('[data-open-filters]', fin);
    fb && fb.addEventListener('click', () => {
      if (matchMedia('(max-width: 767px)').matches) return openSheet(filterSheet(), fb);
      panel.hidden = !panel.hidden; fb.setAttribute('aria-expanded', String(!panel.hidden));
      if (!panel.hidden) { const c = $('button', panel); c && c.focus() }
    });
    function filterSheet() {
      let s = $('#filter-sheet'); if (s) return s;
      s = d.createElement('div'); s.className = 'sheet'; s.id = 'filter-sheet'; s.hidden = true; s.setAttribute('role', 'dialog'); s.setAttribute('aria-modal', 'true'); s.setAttribute('aria-label', ZH ? '筛选' : 'Filters');
      s.innerHTML = `<div class="sheet-panel"><div class="sheet-grip"></div><div class="sheet-head"><h2>${ZH ? '筛选' : 'Filters'}</h2><button class="icon-btn" type="button" data-close-sheet aria-label="${ZH ? '关闭' : 'Close'}">${icon('x')}</button></div>
<div class="facet"><h3>${ZH ? '运行环境' : 'Environment'}</h3><div style="display:flex;flex-wrap:wrap;gap:8px"></div></div><div class="facet"><h3>${ZH ? '排行榜' : 'Leaderboard'}</h3><div style="display:flex;flex-wrap:wrap;gap:8px" data-lb-slot></div></div>
<button class="btn btn-primary" type="button" data-close-sheet style="width:100%;margin-top:12px">${ZH ? '显示结果' : 'Show results'}</button></div>`;
      d.body.append(s);
      const slot = $('.facet div', s);
      chips.forEach(c => { const cl = c.cloneNode(true); cl.addEventListener('click', () => { c.click(); cl.setAttribute('aria-pressed', c.getAttribute('aria-pressed')) }); slot.append(cl) });
      if (lbBtn) { const cl = lbBtn.cloneNode(true); cl.classList.remove('chips-inline'); cl.addEventListener('click', () => { lbBtn.click(); cl.setAttribute('aria-pressed', lbBtn.getAttribute('aria-pressed')) }); $('[data-lb-slot]', s).append(cl) }
      return s;
    }
    // signature: the cursor glides once per session from the headline into the field
    if (screenEl) glide(screenEl, input, field);
  }

  function glide(screenEl, input, field) {
    const h1 = $('h1', screenEl), trail = $('.trail', screenEl), path = trail && $('path', trail), cur = $('.cursor', screenEl);
    const box = $('.bbox-f', screenEl), st2 = $('.step-2', screenEl), st3 = $('.step-3', screenEl), stats = $('.hero-stats', screenEl);
    const coords = () => { if (!box) return; const r = box.getBoundingClientRect(); box.dataset.l = `click(${Math.round(r.left + r.width / 2)}, ${Math.round(r.top + scrollY + r.height / 2)})` };
    coords();
    if (!h1 || !path || !cur || !box || matchMedia('(max-width: 767px)').matches) return;
    function geometry() {
      coords();
      const sr = screenEl.getBoundingClientRect(), fr = field.getBoundingClientRect(), b = box.getBoundingClientRect();
      const x0 = b.right - sr.left, y0 = b.bottom - sr.top;
      const cs = getComputedStyle(input), cv = geometry.c || (geometry.c = d.createElement('canvas').getContext('2d'));
      cv.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
      const ir = input.getBoundingClientRect(), textEnd = ir.left - sr.left + cv.measureText(input.value || input.placeholder).width, fRight = fr.right - sr.left;
      let clear = x0, midY = y0 + 60;
      if (stats) { const rg = d.createRange(); rg.selectNodeContents(stats); const rs = [...rg.getClientRects()]; clear = Math.max(x0, ...rs.map(r => r.right - sr.left)); const sb = stats.getBoundingClientRect(); midY = sb.top - sr.top + sb.height / 2 }
      const x1 = Math.max(textEnd + 56, Math.min(Math.max(x0 + 200, clear + 70), fRight - 190)), y1 = fr.top - sr.top + fr.height * .52;
      const ok = x1 < fRight - 110, xm = Math.min(Math.max(x0 + 90, clear + 26), fRight - 14);
      [trail, cur, st2, st3].forEach(e => { if (e) e.style.visibility = ok ? '' : 'hidden' });
      const f = n => n.toFixed(1);
      const dd = `M${f(x0)} ${f(y0)}C${f(x0 + 14)} ${f(y0 + (midY - y0) * .6)} ${f(xm - 34)} ${f(midY - (midY - y0) * .3)} ${f(xm)} ${f(midY)}C${f(xm + 34)} ${f(midY + (y1 - midY) * .3)} ${f(x1 + 10)} ${f(y1 - (y1 - midY) * .6)} ${f(x1)} ${f(y1)}`;
      // the drawn line stops at the cursor tip and a dash, not a gap, ends there; the cursor itself still travels dd
      path.setAttribute('d', dd.replace(/ [\d.-]+$/, ' ' + f(y1 - 2)));
      path.style.strokeDashoffset = f((7 - path.getTotalLength() % 14 + 14) % 14);
      trail.setAttribute('viewBox', `0 0 ${sr.width} ${sr.height}`); trail.setAttribute('width', sr.width); trail.setAttribute('height', sr.height);
      cur.style.offsetPath = `path("${dd}")`;
      if (st2) { st2.style.transform = `translate(${f(xm)}px,${f(midY)}px)`; $('[data-l]', st2).textContent = `move(${Math.round(xm + sr.left)}, ${Math.round(midY + sr.top + scrollY)})` }
      if (st3) st3.style.transform = `translate(${f(x1)}px,${f(y1)}px)`;
    }
    geometry();
    let rt; addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(geometry, 120) });
    // The body and mono faces load without a preload, so one can arrive after this first measure; re-measure whenever a face finishes.
    if (d.fonts) { d.fonts.ready.then(geometry); d.fonts.addEventListener('loadingdone', geometry) }
    const first = !sess.get('cua-glide') && !reduce.matches && !input.value;
    if (first) {
      sess.set('cua-glide', '1');
      screenEl.classList.add('js-glide');
      setTimeout(() => {
        field.classList.add('glow');
        if (matchMedia('(pointer: fine)').matches && d.activeElement === d.body && scrollY < 40) input.focus({preventScroll: true});
      }, 1480);
    } else cur.style.offsetDistance = '100%';
    input.addEventListener('input', () => screenEl.classList.toggle('is-typing', !!input.value));
  }

  /* ---------- sheets (mobile menu, filters) ---------- */
  let lastFocus;
  function openSheet(s, from) {
    lastFocus = from || d.activeElement; s.hidden = false; requestAnimationFrame(() => s.setAttribute('data-open', ''));
    const f = $('button,a,input', $('.sheet-panel', s)); f && f.focus();
    if (!s.dataset.bound) { s.dataset.bound = '1'; s.addEventListener('click', e => { if (e.target === s || e.target.closest('[data-close-sheet]')) closeSheet(s) }) }
    s.onkeydown = e => { if (e.key === 'Escape') closeSheet(s); trap(e, $('.sheet-panel', s)) };
  }
  function closeSheet(s) { s.removeAttribute('data-open'); setTimeout(() => { s.hidden = true }, reduce.matches ? 0 : 200); lastFocus && lastFocus.focus() }
  function trap(e, box) {
    if (e.key !== 'Tab') return;
    const f = $$('a[href],button:not([disabled]),input,select,[tabindex="0"]', box).filter(x => x.offsetParent !== null);
    if (!f.length) return; const a = f[0], z = f[f.length - 1];
    if (e.shiftKey && d.activeElement === a) { e.preventDefault(); z.focus() } else if (!e.shiftKey && d.activeElement === z) { e.preventDefault(); a.focus() }
  }
  const mb = $('[data-open-menu]'); mb && mb.addEventListener('click', () => openSheet($('#menu-sheet'), mb));

  /* ---------- ⌘K palette ---------- */
  let pal, palInput, palBody, palSel = -1, palHits = [];
  function buildPalette() {
    pal = d.createElement('div'); pal.className = 'palette'; pal.hidden = true;
    pal.setAttribute('role', 'dialog'); pal.setAttribute('aria-modal', 'true'); pal.setAttribute('aria-label', ZH ? '搜索目录' : 'Search the catalog');
    pal.innerHTML = `<div class="window"><div class="titlebar"><span class="lights" aria-hidden="true"><i></i><i></i><i></i></span><div class="address">${icon('lock')}<output data-paddr><b>awesomecua.com</b>/search</output></div><button class="copy-url" type="button" data-close-palette>${icon('x')}<span>esc</span></button></div>
<div class="field">${icon('search')}<input type="search" role="combobox" aria-expanded="true" aria-controls="p-list" aria-autocomplete="list" aria-label="${ZH ? '搜索目录' : 'Search the catalog'}" placeholder="${ZH ? '搜索名称、类型或主题' : 'Search names, kinds or topics'}" autocomplete="off" spellcheck="false"><span class="count" aria-live="polite"></span></div>
<div class="p-body" id="p-list" role="listbox" aria-label="${ZH ? '结果' : 'Results'}"></div>
<div class="statusbar"><span class="keys" aria-hidden="true"><span><kbd>↑</kbd><kbd>↓</kbd>${ZH ? '移动' : 'move'}</span><span><kbd>↵</kbd>${ZH ? '打开' : 'open'}</span><span><kbd>⌘</kbd><kbd>↵</kbd>${ZH ? '打开来源' : 'source'}</span></span><a class="see-all" href="${exploreHref()}" data-pall>${ZH ? '打开目录' : 'Open the catalog'}${icon('right', 'i i-sm')}</a></div></div>`;
    d.body.append(pal);
    palInput = $('input', pal); palBody = $('.p-body', pal);
    pal.addEventListener('click', e => { if (e.target === pal || e.target.closest('[data-close-palette]')) closePalette() });
    palInput.addEventListener('input', palRender);
    pal.addEventListener('keydown', e => {
      if (e.key === 'Escape') { e.preventDefault(); closePalette(); return }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); palMove(e.key === 'ArrowDown' ? 1 : -1); return }
      if (e.key === 'Enter' && palHits[palSel]) { e.preventDefault(); const h = palHits[palSel]; addRecent(palInput.value.trim()); (e.metaKey || e.ctrlKey) ? open(h.dataset.src || h.dataset.href, '_blank', 'noopener') : (location.href = h.dataset.href); return }
      trap(e, $('.window', pal));
    });
    palBody.addEventListener('click', e => { const h = e.target.closest('.hit'); if (h && h.dataset.href) { addRecent(palInput.value.trim()); location.href = h.dataset.href } else { const c = e.target.closest('[data-recent]'); if (c) { palInput.value = c.dataset.recent; palRender() } } });
    palBody.addEventListener('mousemove', e => { const h = e.target.closest('.hit'); if (h) palSet(palHits.indexOf(h)) });
  }
  function palSet(i) {
    palHits.forEach((h, j) => h.setAttribute('aria-selected', String(j === i))); palSel = i;
    if (palHits[i]) { palInput.setAttribute('aria-activedescendant', palHits[i].id); palHits[i].scrollIntoView({block: 'nearest'}) } else palInput.removeAttribute('aria-activedescendant');
  }
  function palMove(dir) { if (!palHits.length) return; palSet((palSel + dir + palHits.length) % palHits.length) }
  function hitHTML(rec, toks, i) {
    const sub = rec.d || (rec.ident + (rec.y ? ' · ' + rec.y : ''));
    return `<div class="hit" role="option" id="hit-${i}" aria-selected="false" data-href="${hrefFor(rec)}" data-src="${esc(srcFor(rec))}">${icon(KIND_IC[rec.k])}<b>${hl(rec.name, toks)}</b><small>${hl(sub, toks)}</small><span class="side">${envTag(rec.env)}${icon('enter', 'i i-sm enter')}</span></div>`;
  }
  function palRender() {
    const q = palInput.value.trim(), cnt = $('.count', pal);
    $('[data-paddr]', pal).innerHTML = `<b>awesomecua.com</b>/search${q ? `<span class="q">?q=${esc(q)}</span>` : ''}`;
    $('[data-pall]', pal).href = exploreHref(q);
    if (!q) {
      const rec = recents();
      const jumps = [['benchmark', ZH ? '评测基准' : 'Benchmarks'], ['dataset', ZH ? '数据集' : 'Datasets'], ['model', ZH ? '模型' : 'Models'], ['paper', ZH ? '论文' : 'Papers']];
      palBody.innerHTML = (rec.length ? `<div class="p-recent"><h3>${ZH ? '最近搜索' : 'Recent searches'}</h3>${recentChips(rec)}</div>` : '') +
        `<div class="p-group" role="group" aria-label="${ZH ? '跳转' : 'Jump to'}"><div class="p-h" role="presentation"><span>${ZH ? '跳转' : 'Jump to'}</span></div>${jumps.map(([k, l], i) => `<div class="hit" role="option" id="hit-${i}" aria-selected="false" data-href="/categories/${k}/">${icon(KIND_IC[k])}<b>${l}</b><small>${ZH ? '浏览全部' : 'Browse all ' + l.toLowerCase()}</small><span class="side">${icon('enter', 'i i-sm enter')}</span></div>`).join('')}</div>`;
      cnt.textContent = ''; palHits = $$('.hit', palBody); palSet(-1); return;
    }
    if (!IDX) { palBody.innerHTML = `<div class="p-group"><span class="skel" style="margin:16px 18px;width:60%"></span><span class="skel" style="margin:12px 18px;width:40%"></span></div>`; loadIndex().then(palRender).catch(() => { palBody.innerHTML = `<div class="empty"><p>${ZH ? '索引未能加载。' : 'The search index did not load.'}</p></div>` }); return }
    const r = search(q);
    cnt.textContent = ZH ? `${fmt(r.res.length)} 条` : `${fmt(r.res.length)} result${r.res.length === 1 ? '' : 's'}`;
    if (!r.res.length) { palBody.innerHTML = emptyHTML(q).replace(/^<li/, '<div').replace(/li>$/, 'div>'); palHits = []; palSet(-1); return }
    const groups = {}; const order = [];
    for (const rec of r.res) { const k = rec.k === 'survey' ? 'paper' : rec.k; if (!groups[k]) { groups[k] = []; order.push(k) } groups[k].push(rec) }
    let i = 0, html = '';
    for (const k of order.slice(0, 5)) {
      const g = groups[k];
      html += `<div class="p-group" role="group" aria-label="${KIND_PLURAL[k]}"><div class="p-h" role="presentation"><span>${KIND_PLURAL[k]}</span><span class="num">${fmt(g.length)}</span></div>${g.slice(0, k === order[0] ? 5 : 3).map(rec => hitHTML(rec, r.toks, i++)).join('')}</div>`;
    }
    palBody.innerHTML = html; palHits = $$('.hit', palBody); palSet(0);
  }
  onText.push(() => {
    if (!pal || pal.hidden || !palInput.value.trim()) return;
    const was = palHits[palSel] && palHits[palSel].dataset.href;
    palRender();
    const i = palHits.findIndex(h => h.dataset.href === was);
    if (i > 0) palSet(i);
  });
  function openPalette(q) {
    if (!pal) buildPalette();
    lastFocus = d.activeElement; pal.hidden = false; requestAnimationFrame(() => pal.setAttribute('data-open', ''));
    d.body.style.overflow = 'hidden';
    if (typeof q === 'string') palInput.value = q;
    palRender(); palInput.focus(); loadIndex().then(() => palInput.value && palRender()).catch(() => {});
  }
  function closePalette() { pal.removeAttribute('data-open'); d.body.style.overflow = ''; setTimeout(() => { pal.hidden = true }, reduce.matches ? 0 : 140); lastFocus && lastFocus.focus && lastFocus.focus() }
  $$('[data-open-palette]').forEach(b => b.addEventListener('click', () => openPalette()));
  addEventListener('keydown', e => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(d.activeElement.tagName) || d.activeElement.isContentEditable;
    if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) { e.preventDefault(); pal && !pal.hidden ? closePalette() : openPalette(); return }
    if (e.key === '/' && !typing) {
      if ($('#search')) return; // the explorer page focuses its own search field
      e.preventDefault();
      const hero = $('#finder #q'), r = hero && hero.getBoundingClientRect();
      if (hero && r.bottom > 0 && r.top < innerHeight) hero.focus(); else openPalette();
    }
  });
  if (/[?&]palette=open/.test(location.search)) addEventListener('load', () => openPalette(new URLSearchParams(location.search).get('pq') || ''));

  /* ---------- copy buttons ---------- */
  d.addEventListener('click', e => {
    const b = e.target.closest('[data-copy-url],[data-copy],[data-copy-panel],[data-copy-from]');
    if (!b) return;
    if (b.hasAttribute('data-copy-url')) {
      const out = b.closest('.window') && $('[data-address]', b.closest('.window'));
      copy(out ? 'https://' + out.textContent.trim() : location.href, ZH ? '链接已复制' : 'Link copied');
    } else if (b.hasAttribute('data-copy-panel')) {
      const p = $$('[role=tabpanel]', b.closest('.window')).find(x => !x.hidden); p && copy(p.textContent, ZH ? '已复制' : 'Snippet copied');
      const after = $('[data-after-copy]', b.closest('.window')); if (after) after.hidden = false;
    } else if (b.hasAttribute('data-copy-from')) {
      const src = d.getElementById(b.dataset.copyFrom); src && copy(src.textContent.trim(), b.dataset.msg);
    } else copy(b.dataset.copy, b.dataset.msg);
  });

  /* ---------- ARIA tabs (code snippets) ---------- */
  $$('[role=tablist]').forEach(tl => {
    const ts = $$('[role=tab]', tl);
    const sel = t => { ts.forEach(x => { const on = x === t; x.setAttribute('aria-selected', String(on)); x.tabIndex = on ? 0 : -1; const p = d.getElementById(x.getAttribute('aria-controls')); if (p) p.hidden = !on }); t.focus() };
    ts.forEach((t, i) => { t.addEventListener('click', () => sel(t)); t.addEventListener('keydown', e => { if (e.key === 'ArrowRight') sel(ts[(i + 1) % ts.length]); if (e.key === 'ArrowLeft') sel(ts[(i - 1 + ts.length) % ts.length]) }) });
  });

  /* ---------- menus (split button, cite) ---------- */
  $$('[data-menu]').forEach(btn => {
    const pop = d.getElementById(btn.getAttribute('aria-controls'));
    const close = () => { pop.hidden = true; btn.setAttribute('aria-expanded', 'false') };
    btn.addEventListener('click', e => { e.stopPropagation(); const o = pop.hidden; $$('.menu-pop').forEach(p => p.hidden = true); pop.hidden = !o; btn.setAttribute('aria-expanded', String(o)); o && $('a,button', pop).focus() });
    pop.addEventListener('keydown', e => {
      const items = $$('a,button', pop), i = items.indexOf(d.activeElement);
      if (e.key === 'Escape') { close(); btn.focus() } if (e.key === 'ArrowDown') { e.preventDefault(); (items[i + 1] || items[0]).focus() } if (e.key === 'ArrowUp') { e.preventDefault(); (items[i - 1] || items[items.length - 1]).focus() }
    });
    d.addEventListener('click', e => { if (!pop.contains(e.target)) close() });
  });

  /* ---------- show all authors ---------- */
  $$('[data-more-authors]').forEach(b => b.addEventListener('click', () => { const t = d.getElementById(b.getAttribute('aria-controls')); t.hidden = false; b.setAttribute('aria-expanded', 'true'); b.remove() }));

  /* ---------- survey: table of contents follows reading position ---------- */
  const tocD = $('[data-toc]'); if (tocD && matchMedia('(min-width: 1024px)').matches) tocD.open = true;
  const toc = $('.toc');
  if (toc && 'IntersectionObserver' in window) {
    const links = $$('a[href^="#"]', toc), map = new Map(links.map(a => [a.getAttribute('href').slice(1), a]));
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { links.forEach(a => a.removeAttribute('aria-current')); const a = map.get(e.target.id); a && a.setAttribute('aria-current', 'true') } }), {rootMargin: '-20% 0px -70% 0px'});
    map.forEach((_, id) => { const el = d.getElementById(id); el && io.observe(el) });
  }

  /* ---------- catalog: facets, sort, pages ---------- */
  const br = $('[data-browse]');
  if (br) {
    const list = $('#b-results', br), tot = $('[data-total]', br), act = $('[data-active]', br), pager = $('[data-pager]', br), sortSel = $('[data-bsort]', br);
    const facetsEl = $('.facets', br), kindHead = $('[data-kind-head]');
    const PER = 25;
    const st = {q: '', kind: 'benchmark', env: [], topic: [], lic: [], lb: false, year: [], sort: 'mentions', page: 1};
    const p0 = new URLSearchParams(location.search);
    function readURL(p) {
      st.q = p.get('q') || ''; st.kind = p.get('kind') || 'benchmark'; st.lb = p.get('leaderboard') === '1';
      st.env = (p.get('env') || '').split(',').filter(Boolean); st.topic = (p.get('topic') || '').split(',').filter(Boolean);
      st.lic = (p.get('licence') || '').split(',').filter(Boolean); st.year = (p.get('year') || '').split(',').filter(Boolean);
      st.sort = p.get('sort') || (st.q ? 'relevance' : 'mentions'); st.page = Math.max(1, +p.get('page') || 1);
    }
    readURL(p0);
    const changed = [...p0.keys()].some(k => !['kind'].includes(k)) || (p0.get('kind') && p0.get('kind') !== 'benchmark');
    function writeURL(push) {
      const p = new URLSearchParams();
      if (st.q) p.set('q', st.q); if (st.kind !== 'benchmark') p.set('kind', st.kind);
      if (st.env.length) p.set('env', st.env.join(',')); if (st.topic.length) p.set('topic', st.topic.join(','));
      if (st.lic.length) p.set('licence', st.lic.join(',')); if (st.year.length) p.set('year', st.year.join(','));
      if (st.lb) p.set('leaderboard', '1'); if (st.sort !== (st.q ? 'relevance' : 'mentions')) p.set('sort', st.sort); if (st.page > 1) p.set('page', st.page);
      const s = p.toString(); history[push ? 'pushState' : 'replaceState'](null, '', location.pathname + (s ? '?' + s : ''));
    }
    const yearOk = (rec, ys) => !ys.length || ys.some(y => y === 'older' ? rec.y && rec.y < 2022 : rec.y === +y);
    function pass(rec, skip) {
      if (st.kind !== 'all' && !(rec.k === st.kind || (st.kind === 'paper' && rec.k === 'survey'))) return false;
      if (skip !== 'env' && st.env.length && !st.env.some(e => rec.env & ENV_BITS[e])) return false;
      if (skip !== 'topic' && st.topic.length && !st.topic.some(t => rec.t.includes(IDX.topics.indexOf(t)))) return false;
      if (skip !== 'lic' && st.lic.length && !st.lic.some(l => l === 'none' ? rec.lic < 0 : IDX.licences[rec.lic] === l)) return false;
      if (skip !== 'year' && !yearOk(rec, st.year)) return false;
      if (skip !== 'lb' && st.lb && !(rec.f & 2)) return false;
      return true;
    }
    function facetCounts(base) {
      const c = {env: {}, topic: {}, lic: {}, year: {}, lb: 0};
      for (const rec of base) {
        if (pass(rec, 'env')) for (const e in ENV_BITS) if (rec.env & ENV_BITS[e]) c.env[e] = (c.env[e] || 0) + 1;
        if (pass(rec, 'topic')) for (const t of rec.t) { const k = IDX.topics[t]; c.topic[k] = (c.topic[k] || 0) + 1 }
        if (pass(rec, 'lic')) { const k = rec.lic < 0 ? 'none' : IDX.licences[rec.lic]; c.lic[k] = (c.lic[k] || 0) + 1 }
        if (pass(rec, 'year')) { const k = !rec.y ? 'unknown' : rec.y < 2022 ? 'older' : String(rec.y); c.year[k] = (c.year[k] || 0) + 1 }
        if (pass(rec, 'lb') && (rec.f & 2)) c.lb++;
      }
      return c;
    }
    function opt(name, val, label, n, checked, type = 'checkbox') {
      return `<label class="opt${n ? '' : ' is-zero'}"><input type="${type}" name="${name}" value="${esc(val)}"${checked ? ' checked' : ''}><span class="lab">${esc(label)}</span><span class="n">${fmt(n || 0)}</span></label>`;
    }
    function renderFacets(c) {
      const kinds = ['all', 'benchmark', 'dataset', 'model', 'agent', 'framework', 'paper', 'tool', 'infrastructure', 'product', 'company', 'learning'];
      const kc = {}; for (const rec of IDX) { const k = rec.k === 'survey' ? 'paper' : rec.k; if (st.q ? qset.has(rec) : true) { kc[k] = (kc[k] || 0) + 1; kc.all = (kc.all || 0) + 1 } }
      const topTopics = Object.entries(c.topic).sort((a, b) => b[1] - a[1]);
      const showAllT = facetsEl.dataset.allTopics === '1';
      const lics = Object.entries(c.lic).sort((a, b) => (a[0] === 'none') - (b[0] === 'none') || b[1] - a[1]).slice(0, 8);
      const years = ['2026', '2025', '2024', '2023', '2022', 'older'];
      facetsEl.innerHTML = `<div class="facets-head"><h2>${ZH ? '筛选' : 'Filter'}</h2>${act.children.length ? `<button class="clear-all" type="button" data-clear>${ZH ? '清除' : 'Clear all'}</button>` : ''}</div>
<fieldset class="facet"><legend>${ZH ? '类型' : 'Kind'}</legend>${kinds.map(k => opt('kind', k, k === 'all' ? (ZH ? '全部类型' : 'All kinds') : KIND_PLURAL[k], kc[k], st.kind === k, 'radio')).join('')}</fieldset>
<fieldset class="facet"><legend>${ZH ? '运行环境' : 'Environment'}</legend>${Object.keys(ENV_BITS).map(e => opt('env', e, ENV_NAMES[ENV_BITS[e]], c.env[e], st.env.includes(e))).join('')}</fieldset>
<fieldset class="facet"><legend>${ZH ? '排行榜' : 'Leaderboard'}</legend>${opt('lb', '1', ZH ? '有官方排行榜' : 'Has an official leaderboard', c.lb, st.lb)}</fieldset>
<fieldset class="facet"><legend>${ZH ? '主题' : 'Topic'}</legend>${(showAllT ? topTopics : topTopics.slice(0, 6)).map(([k, n]) => opt('topic', k, IDX.topicLabels[IDX.topics.indexOf(k)], n, st.topic.includes(k))).join('')}${topTopics.length > 6 ? `<button class="more-opts" type="button" data-more-topics>${showAllT ? (ZH ? '收起' : 'Show fewer') : (ZH ? `全部 ${topTopics.length} 个主题` : `All ${topTopics.length} topics`)}</button>` : ''}</fieldset>
<fieldset class="facet"><legend>${ZH ? '许可' : 'Licence'}</legend>${lics.map(([k, n]) => opt('licence', k, k === 'none' ? (ZH ? '未声明' : 'Not declared') : k, n, st.lic.includes(k))).join('')}</fieldset>
<fieldset class="facet"><legend>${ZH ? '年份' : 'Year'}</legend>${years.map(y => opt('year', y, y === 'older' ? (ZH ? '2022 年以前' : 'Before 2022') : y, c.year[y], st.year.includes(y))).join('')}</fieldset>
<fieldset class="facet"><legend>${ZH ? '审核状态' : 'Review status'}</legend>${opt('status', 'curated', ZH ? '已审核' : 'Source-reviewed', kc.all || 0, true)}<p style="color:var(--text-meta);font-size:.75rem;margin-top:6px">${ZH ? '候选条目在“最新”区单独列出。' : 'Unreviewed candidates are listed apart, under Latest.'}</p></fieldset>`;
    }
    let qset = new Set(), rendered = false;
    onText.push(() => { if (rendered) render() });
    function render(push) {
      if (!IDX) { loadIndex().then(() => render(push)); return }
      rendered = true;
      const r = search(st.q, {kind: 'all', sort: st.sort});
      qset = new Set(r.res);
      const base = st.q ? r.res : IDX.slice().sort((a, b) => ({mentions: b.m - a.m, reviewed: b.rv - a.rv, year: b.y - a.y, name: 0}[st.sort] || 0) || a.nr - b.nr);
      const items = base.filter(rec => pass(rec));
      const pages = Math.max(1, Math.ceil(items.length / PER)); st.page = Math.min(st.page, pages);
      const slice = items.slice((st.page - 1) * PER, st.page * PER);
      list.innerHTML = slice.length ? slice.map(x => rowHTML(x, r.toks)).join('') : emptyHTML(st.q || (ZH ? '这些筛选条件' : 'these filters'));
      list.toggleAttribute('data-single', st.kind !== 'all');
      const label = st.kind === 'all' ? (ZH ? '条记录' : 'records') : (ZH ? '条' : KIND_PLURAL[st.kind].toLowerCase());
      tot.innerHTML = `${fmt(items.length)} <span>${label}</span>`;
      const chips = [];
      if (st.q) chips.push(['q', st.q, `“${st.q}”`]);
      st.env.forEach(e => chips.push(['env', e, ENV_NAMES[ENV_BITS[e]]])); st.topic.forEach(t => chips.push(['topic', t, IDX.topicLabels[IDX.topics.indexOf(t)]]));
      st.lic.forEach(l => chips.push(['lic', l, l === 'none' ? (ZH ? '未声明许可' : 'No licence declared') : l])); st.year.forEach(y => chips.push(['year', y, y === 'older' ? 'Before 2022' : y]));
      if (st.lb) chips.push(['lb', '1', ZH ? '有排行榜' : 'Leaderboard']);
      act.innerHTML = chips.map(([k, v, l]) => `<button class="chip" type="button" data-rm="${k}" data-v="${esc(v)}" aria-label="${ZH ? '移除筛选' : 'Remove filter'} ${esc(l)}">${esc(l)}${icon('x')}</button>`).join('') + (chips.length ? `<button class="clear-all" type="button" data-clear>${ZH ? '全部清除' : 'Clear all'}</button>` : '');
      renderFacets(facetCounts(base));
      const nums = []; for (let i = 1; i <= pages; i++) if (i === 1 || i === pages || Math.abs(i - st.page) <= 1) nums.push(i); else if (nums[nums.length - 1] !== '…') nums.push('…');
      const link = i => { const p = new URLSearchParams(location.search); i > 1 ? p.set('page', i) : p.delete('page'); return '?' + p.toString() };
      pager.innerHTML = `<span class="info">${items.length ? `${fmt((st.page - 1) * PER + 1)}–${fmt(Math.min(items.length, st.page * PER))} ${ZH ? '共' : 'of'} ${fmt(items.length)}` : ''}</span><nav aria-label="${ZH ? '分页' : 'Pages'}">${st.page > 1 ? `<a href="${link(st.page - 1)}" data-page="${st.page - 1}" aria-label="${ZH ? '上一页' : 'Previous page'}">‹</a>` : ''}${nums.map(i => i === '…' ? '<span aria-hidden="true">…</span>' : i === st.page ? `<span aria-current="page">${i}</span>` : `<a href="${link(i)}" data-page="${i}">${i}</a>`).join('')}${st.page < pages ? `<a href="${link(st.page + 1)}" data-page="${st.page + 1}" aria-label="${ZH ? '下一页' : 'Next page'}">›</a>` : ''}</nav>`;
      const isBench = st.kind === 'benchmark' && !st.q, tEl = $('[data-kind-title]'), lEl = $('[data-kind-lede]'), jump = $('[data-jump]');
      if (kindHead) kindHead.hidden = !isBench;
      if (jump) jump.hidden = !isBench;
      if (tEl && !tEl.dataset.def) { tEl.dataset.def = tEl.textContent; lEl.dataset.def = lEl.textContent }
      if (tEl) {
        tEl.textContent = st.q ? `${ZH ? '搜索' : 'Search'}: ${st.q}` : st.kind === 'all' ? (ZH ? '目录' : 'Catalog') : isBench ? tEl.dataset.def : KIND_PLURAL[st.kind];
        const defs = JSON.parse(($('#kind-defs') || {}).textContent || '{}');
        lEl.textContent = isBench ? lEl.dataset.def : st.q ? (ZH ? '目录中的匹配结果。' : 'Matching records in the catalog.') : st.kind === 'all' ? (ZH ? '全部已审核记录。' : 'Every reviewed record, with its primary source.') : (defs[st.kind] || '');
        const cur = $('.crumbs [aria-current]'); if (cur) cur.textContent = tEl.textContent;
      }
      list.setAttribute('aria-label', tEl ? tEl.textContent : 'Results');
      const showN = $('[data-show-n]'); if (showN) showN.textContent = ZH ? `显示 ${fmt(items.length)} 条结果` : `Show ${fmt(items.length)} result${items.length === 1 ? '' : 's'}`;
      sortSel.value = st.sort;
      writeURL(push);
    }
    d.addEventListener('change', e => {
      const t = e.target; if (!t.name || !(t.closest('.facets') || t.matches('[data-bsort]'))) return;
      if (t.name === 'kind') { st.kind = t.value; st.topic = [] }
      else if (t.name === 'env') st.env = $$('input[name=env]:checked', facetsEl).map(x => x.value);
      else if (t.name === 'topic') st.topic = $$('input[name=topic]:checked', facetsEl).map(x => x.value);
      else if (t.name === 'licence') st.lic = $$('input[name=licence]:checked', facetsEl).map(x => x.value);
      else if (t.name === 'year') st.year = $$('input[name=year]:checked', facetsEl).map(x => x.value);
      else if (t.name === 'lb' || t.name === 'leaderboard') st.lb = t.checked;
      else if (t.name === 'sort') st.sort = t.value;
      else return;
      st.page = 1; const nm = t.name, val = t.value; render(true);
      const again = $(`input[name="${nm}"][value="${CSS.escape(val)}"]`, facetsEl); again && again.focus();
    });
    d.addEventListener('click', e => {
      const rm = e.target.closest('[data-rm]'), cl = e.target.closest('[data-clear]'), pg = e.target.closest('[data-page]'), mt = e.target.closest('[data-more-topics]');
      if (rm) { const k = rm.dataset.rm, v = rm.dataset.v; if (k === 'q') st.q = ''; else if (k === 'lb') st.lb = false; else st[k] = st[k].filter(x => x !== v); st.page = 1; render(true) }
      if (cl) { Object.assign(st, {q: '', env: [], topic: [], lic: [], year: [], lb: false, page: 1}); render(true) }
      if (pg) { e.preventDefault(); st.page = +pg.dataset.page; render(true); $('#b-top').scrollIntoView({behavior: reduce.matches ? 'auto' : 'smooth'}) }
      if (mt) { facetsEl.dataset.allTopics = facetsEl.dataset.allTopics === '1' ? '0' : '1'; render() }
    });
    roving(list, null);
    addEventListener('popstate', () => { readURL(new URLSearchParams(location.search)); render() });
    const fb = $('[data-open-facets]'), browseEl = $('.browse', br), mqB = matchMedia('(max-width: 1023px)');
    fb && fb.addEventListener('click', () => {
      let s = $('#facet-sheet');
      if (!s) {
        s = d.createElement('div'); s.className = 'sheet'; s.id = 'facet-sheet'; s.hidden = true; s.setAttribute('role', 'dialog'); s.setAttribute('aria-modal', 'true'); s.setAttribute('aria-label', ZH ? '筛选' : 'Filters');
        s.innerHTML = `<div class="sheet-panel"><div class="sheet-grip"></div><div class="sheet-head"><h2>${ZH ? '筛选' : 'Filters'}</h2><button class="icon-btn" type="button" data-close-sheet aria-label="${ZH ? '关闭' : 'Close'}">${icon('x')}</button></div><div data-slot></div><button class="btn btn-primary" type="button" data-close-sheet data-show-n style="width:100%;margin-top:16px">${ZH ? '显示结果' : 'Show results'}</button></div>`;
        d.body.append(s);
      }
      $('[data-slot]', s).append(facetsEl);
      if (IDX) render(); else loadIndex().then(() => render());
      openSheet(s, fb);
    });
    mqB.addEventListener('change', () => { if (!mqB.matches && !browseEl.contains(facetsEl)) browseEl.prepend(facetsEl) });
    if (changed) render(); else loadIndex().then(() => { qset = new Set(IDX); renderFacets(facetCounts(IDX)) }).catch(() => {});
  }
})();
