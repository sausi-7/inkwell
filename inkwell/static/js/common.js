// Shared helpers — kept tiny on purpose. No build step, no modules.

window.Ink = window.Ink || {};

Ink.api = async function (path, opts = {}) {
  const init = Object.assign(
    { headers: { 'Content-Type': 'application/json' } },
    opts,
  );
  if (init.body && typeof init.body !== 'string') {
    init.body = JSON.stringify(init.body);
  }
  const res = await fetch(path, init);
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : null; } catch (_) { data = text; }
  if (!res.ok) {
    const msg = (data && data.detail) || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
};

Ink.toast = function (message, isError = false) {
  let el = document.querySelector('.toast');
  if (!el) {
    el = document.createElement('div');
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.classList.toggle('err', !!isError);
  el.classList.add('show');
  clearTimeout(Ink._toastTimer);
  Ink._toastTimer = setTimeout(() => el.classList.remove('show'), 2400);
};

Ink.copyToClipboard = async function (text) {
  try {
    await navigator.clipboard.writeText(text);
    Ink.toast('Copied to clipboard');
  } catch (e) {
    Ink.toast('Copy failed', true);
  }
};

// BYOK key lives in browser only.
Ink.llm = {
  get() {
    return {
      provider: localStorage.getItem('ink_llm_provider') || 'openai',
      model: localStorage.getItem('ink_llm_model') || 'gpt-4o-mini',
      key: localStorage.getItem('ink_llm_key') || '',
    };
  },
  set({ provider, model, key }) {
    if (provider !== undefined) localStorage.setItem('ink_llm_provider', provider);
    if (model !== undefined) localStorage.setItem('ink_llm_model', model);
    if (key !== undefined) localStorage.setItem('ink_llm_key', key);
  },
  clear() {
    localStorage.removeItem('ink_llm_provider');
    localStorage.removeItem('ink_llm_model');
    localStorage.removeItem('ink_llm_key');
  },
  hasKey() {
    return !!localStorage.getItem('ink_llm_key') ||
           (localStorage.getItem('ink_llm_provider') === 'ollama');
  },
};
