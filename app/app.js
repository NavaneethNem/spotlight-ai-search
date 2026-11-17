const input = document.querySelector('#query');
const list = document.querySelector('#suggestions');
const status = document.querySelector('#status');
const form = document.querySelector('form');
let results = [], selected = -1, draft = '', timer, request;
let version = 0;
const cache = new Map();
let navigating = false;
const panel = document.querySelector('main');
function publishLayout() {
  if (navigating) return;
  const height = Math.max(104, Math.min(380, Math.ceil(panel.getBoundingClientRect().height)));
  document.title = `Quick AI Search [${height}]`;
}
new ResizeObserver(publishLayout).observe(panel);
publishLayout();

function render() {
  list.replaceChildren();
  results.forEach((text, i) => {
    const item = document.createElement('li');
    item.id = `suggestion-${i}`;
    item.role = 'option';
    item.setAttribute('aria-selected', String(i === selected));
    item.textContent = text;
    item.addEventListener('pointerdown', event => event.preventDefault());
    item.addEventListener('click', () => {
      input.value = text;
      draft = text;
      close();
      input.focus();
    });
    list.append(item);
  });
  list.hidden = results.length === 0;
  input.setAttribute('aria-expanded', String(results.length > 0));
  if (selected >= 0) input.setAttribute('aria-activedescendant', `suggestion-${selected}`);
  else input.removeAttribute('aria-activedescendant');
}

function close() {
  clearTimeout(timer);
  request?.abort();
  version++;
  results = [];
  selected = -1;
  render();
}

input.addEventListener('input', () => {
  draft = input.value;
  clearTimeout(timer);
  request?.abort();
  const current = ++version;
  const query = draft.trim();
  selected = -1;
  status.textContent = '';
  results = cache.get(query) ?? [];
  render();
  if (!query || input.isComposing) return;
  timer = setTimeout(async () => {
    request = new AbortController();
    try {
      const response = await fetch(`/api/suggest?q=${encodeURIComponent(query)}`, { signal: request.signal });
      if (!response.ok) return;
      const data = await response.json();
      if (current !== version) return;
      results = data.slice(0, 5);
      if (cache.size > 128) cache.clear();
      cache.set(query, results);
      render();
    } catch (error) {
      if (error.name !== 'AbortError' && current === version)
        status.textContent = 'Suggestions unavailable. Press Enter to search.';
    }
  }, 110);
});

input.addEventListener('keydown', event => {
  if (event.isComposing) return;
  if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && results.length) {
    event.preventDefault();
    selected += event.key === 'ArrowDown' ? 1 : -1;
    if (selected >= results.length) selected = -1;
    if (selected < -1) selected = results.length - 1;
    input.value = selected >= 0 ? results[selected] : draft;
    render();
  } else if (event.key === 'Tab' && !event.shiftKey && results.length) {
    event.preventDefault();
    input.value = results[Math.max(selected, 0)];
    draft = input.value;
    close();
  } else if (event.key === 'Escape') {
    close();
  }
});

form.addEventListener('submit', event => {
  input.value = input.value.trim();
  if (!input.value) {
    event.preventDefault();
    return;
  }
  close();
  navigating = true;
  document.title = 'AI Mode · Opening';
  status.textContent = 'Opening Google AI Mode…';
});
