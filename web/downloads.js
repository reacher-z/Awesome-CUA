const status = document.querySelector('#data-copy-status');
const fallback = document.querySelector('.data-copy-fallback');
const field = document.querySelector('#data-copy-value');
const zh = document.documentElement.lang.startsWith('zh');
const labels = new WeakMap();
const timers = new WeakMap();
let lastTrigger;

document.addEventListener('click', async event => {
  const button = event.target.closest('button[data-copy-value]');
  if (!button) return;
  if (!labels.has(button)) labels.set(button, button.textContent);
  clearTimeout(timers.get(button));
  const value = button.dataset.copyValue;
  try {
    await navigator.clipboard.writeText(value);
    button.textContent = zh ? '已复制' : 'Copied';
    button.dataset.copyState = 'copied';
    status.textContent = zh ? '已复制，可直接粘贴使用。' : 'Copied and ready to paste.';
    fallback.hidden = true;
    timers.set(button, setTimeout(() => {
      button.textContent = labels.get(button);
      delete button.dataset.copyState;
    }, 2200));
  } catch {
    button.textContent = labels.get(button);
    delete button.dataset.copyState;
    lastTrigger = button;
    field.value = value;
    fallback.hidden = false;
    field.focus();
    field.select();
    status.textContent = zh ? '请复制已选中的内容。' : 'Copy the selected value below.';
  }
});

document.querySelector('[data-dismiss-copy]').addEventListener('click', () => {
  fallback.hidden = true;
  lastTrigger?.focus();
});

// A link to #downloads-rag opens that group, so the target is visible.
function openLinkedGroup() {
  const target = document.getElementById(location.hash.slice(1));
  if (target && target.tagName === 'DETAILS') target.open = true;
}
if (typeof location !== 'undefined' && document.getElementById) {
  addEventListener('hashchange', openLinkedGroup);
  openLinkedGroup();
}
