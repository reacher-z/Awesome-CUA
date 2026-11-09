import {normalize,profileVisible} from './catalog-core.js';

const query = document.querySelector('#compare-query');
const environment = document.querySelector('#compare-environment');
const output = document.querySelector('#compare-results');
const sort = document.querySelector('#compare-sort');
const rows = [...document.querySelectorAll('[data-profile-row]')].map((element, index) => ({element, index, text:normalize(element.dataset.search), environments:element.dataset.environments.split(' '), paper:element.dataset.paper || ''}));
const initial = new URLSearchParams(location.search);
query.value = initial.get('q') || '';
const initialEnvironment = initial.get('environment') || '';
if ([...environment.options].some(option => option.value === initialEnvironment)) environment.value = initialEnvironment;
if (sort && [...sort.options].some(option => option.value === initial.get('sort'))) sort.value = initial.get('sort');
// Rows are generated A–Z; "newest" orders by the linked arXiv identifier (submission month, then number), and rows without a paper keep A–Z order at the end.
const ORDERS = {newest:(a,b) => (b.paper > a.paper) - (b.paper < a.paper)};
function order() {
  const body = rows[0]?.element.parentElement;
  if (!sort || !body) return;
  const compare = ORDERS[sort.value];
  for (const row of [...rows].sort((a,b) => (compare ? compare(a,b) : 0) || a.index - b.index)) body.append(row.element);
}
function apply() {
  const terms = normalize(query.value).split(' ').filter(Boolean);
  let count = 0;
  for (const row of rows) {
    const visible = profileVisible(row.text, row.environments, terms, environment.value);
    row.element.hidden = !visible;
    count += Number(visible);
  }
  output.textContent = `Showing ${count} of ${rows.length} profiles.`;
  const url = new URL(location.href);
  for (const [key,value] of [['q',query.value.trim()],['environment',environment.value],['sort',sort?.value || '']]) {
    if(value) url.searchParams.set(key,value); else url.searchParams.delete(key);
  }
  history.replaceState(null,'',url);
}
query.addEventListener('input',apply);
environment.addEventListener('change',apply);
sort?.addEventListener('change',()=>{order();apply();});
order();
apply();
