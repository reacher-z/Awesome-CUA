import {normalize,profileVisible} from './catalog-core.js';

const query = document.querySelector('#compare-query');
const environment = document.querySelector('#compare-environment');
const output = document.querySelector('#compare-results');
// The Chinese comparison pages mark their status line; it reports the count in Chinese.
const zh = output.dataset?.lang === 'zh';
const rows = [...document.querySelectorAll('[data-profile-row]')].map(element => ({element, text:normalize(element.dataset.search), environments:element.dataset.environments.split(' ')}));
const initial = new URLSearchParams(location.search);
query.value = initial.get('q') || '';
const initialEnvironment = initial.get('environment') || '';
if ([...environment.options].some(option => option.value === initialEnvironment)) environment.value = initialEnvironment;
function apply() {
  const terms = normalize(query.value).split(' ').filter(Boolean);
  let count = 0;
  for (const row of rows) {
    const visible = profileVisible(row.text, row.environments, terms, environment.value);
    row.element.hidden = !visible;
    count += Number(visible);
  }
  output.textContent = zh ? `显示 ${count} / ${rows.length} 个规格档案。` : `Showing ${count} of ${rows.length} profiles.`;
  const url = new URL(location.href);
  for (const [key,value] of [['q',query.value.trim()],['environment',environment.value]]) {
    if(value) url.searchParams.set(key,value); else url.searchParams.delete(key);
  }
  history.replaceState(null,'',url);
}
query.addEventListener('input',apply);
environment.addEventListener('change',apply);
apply();
