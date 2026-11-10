// Filters and re-sorts a category's rows. Without JavaScript every row stays in the HTML in its default order.
export const terms = (value) => value.toLowerCase().split(/\s+/).filter(Boolean);
export const matches = (text, query) => terms(query).every((term) => text.includes(term));
export const byName = (a, b) => a.localeCompare(b, undefined, { sensitivity: 'base', numeric: true });
const nameOf = (row) => row.querySelector('.row-name a').textContent;
const textOf = (row) => [nameOf(row), row.querySelector('.row-id')?.textContent, row.querySelector('.env')?.textContent, row.dataset.env].join(' ').toLowerCase();

function start(root) {
  const list = root.querySelector('[data-list-rows]');
  const input = root.querySelector('[data-list-filter]');
  const sort = root.querySelector('[data-list-sort]');
  const status = root.querySelector('[data-list-status]');
  const empty = root.querySelector('[data-list-empty]');
  const featured = document.querySelector('[data-list-featured]');
  const ranked = [...list.children];
  const named = [...ranked].sort((a, b) => byName(nameOf(a), nameOf(b)));
  const text = new Map(ranked.map((row) => [row, textOf(row)]));
  const params = new URLSearchParams(location.search);
  input.value = params.get('q') || '';
  if (params.get('sort') === 'name') sort.value = 'name';

  const apply = () => {
    const query = input.value.trim();
    list.append(...(sort.value === 'name' ? named : ranked));
    let shown = 0;
    for (const row of ranked) {
      row.hidden = !matches(text.get(row), query);
      if (!row.hidden) shown += 1;
    }
    list.hidden = !shown;
    empty.hidden = Boolean(shown);
    if (featured) featured.hidden = Boolean(query);
    status.textContent = query ? status.dataset.template.replace('{n}', shown).replace('{total}', ranked.length) : '';
    const next = new URLSearchParams(location.search);
    if (query) next.set('q', query); else next.delete('q');
    if (sort.value === 'name') next.set('sort', 'name'); else next.delete('sort');
    const search = next.toString();
    history.replaceState(null, '', location.pathname + (search ? `?${search}` : '') + location.hash);
  };

  input.addEventListener('input', apply);
  sort.addEventListener('change', apply);
  if (input.value || sort.value === 'name') apply();
}

if (typeof document !== 'undefined') {
  const root = document.querySelector('[data-list]');
  if (root && root.querySelector('[data-list-filter]')) start(root);
}
