// Settings page — load/save filters, subreddits, output prefs; manage LLM key
// in browser localStorage (never sent to server except on test-llm / draft).

(function () {
  // ─── chip helpers (shared shape with profile.js) ─────────────────────────
  function renderChips(group, items) {
    const input = group.querySelector('input');
    group.querySelectorAll('.chip').forEach((c) => c.remove());
    (items || []).forEach((item) => {
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.dataset.value = item;
      chip.textContent = item;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = '×';
      btn.addEventListener('click', () => chip.remove());
      chip.appendChild(btn);
      group.insertBefore(chip, input);
    });
  }
  function readChips(group) {
    return Array.from(group.querySelectorAll('.chip')).map((c) => c.dataset.value);
  }
  document.querySelectorAll('[data-chips]').forEach((group) => {
    const input = group.querySelector('input');
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const val = input.value.trim();
        if (!val) return;
        const existing = readChips(group);
        if (!existing.includes(val)) renderChips(group, [...existing, val]);
        input.value = '';
      } else if (e.key === 'Backspace' && !input.value) {
        const chips = group.querySelectorAll('.chip');
        if (chips.length) chips[chips.length - 1].remove();
      }
    });
  });

  // ─── LLM key handling (browser-only) ─────────────────────────────────────
  const providerEl = document.getElementById('llm-provider');
  const modelEl = document.getElementById('llm-model');
  const keyEl = document.getElementById('llm-key');
  const keyRow = document.getElementById('llm-key-row');
  const llmStatus = document.getElementById('llm-status');

  function syncKeyVisibility() {
    keyRow.style.display = providerEl.value === 'ollama' ? 'none' : 'flex';
  }

  const DEFAULT_MODELS = {
    openai: 'gpt-4o-mini',
    claude: 'claude-sonnet-4-6',
    ollama: 'ollama/llama3',
    custom: '',
  };

  function loadLlmFromStorage() {
    const s = Ink.llm.get();
    providerEl.value = s.provider || 'openai';
    modelEl.value = s.model || DEFAULT_MODELS[providerEl.value] || '';
    keyEl.value = s.key || '';
    syncKeyVisibility();
  }

  function saveLlmToStorage() {
    Ink.llm.set({
      provider: providerEl.value,
      model: modelEl.value.trim(),
      key: keyEl.value.trim(),
    });
  }

  providerEl.addEventListener('change', () => {
    if (!modelEl.value || Object.values(DEFAULT_MODELS).includes(modelEl.value)) {
      modelEl.value = DEFAULT_MODELS[providerEl.value] || '';
    }
    syncKeyVisibility();
    saveLlmToStorage();
  });
  modelEl.addEventListener('input', saveLlmToStorage);
  keyEl.addEventListener('input', saveLlmToStorage);

  document.getElementById('clear-llm').addEventListener('click', () => {
    Ink.llm.clear();
    loadLlmFromStorage();
    llmStatus.innerHTML = '<span class="pill pill-muted">cleared</span>';
  });

  document.getElementById('test-llm').addEventListener('click', async () => {
    const model = modelEl.value.trim();
    if (!model) { llmStatus.innerHTML = '<span class="pill pill-err">model required</span>'; return; }
    llmStatus.innerHTML = '<span class="pill pill-muted">testing…</span>';
    try {
      const res = await fetch('/api/settings/test-llm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(keyEl.value ? { 'X-LLM-Key': keyEl.value } : {}),
        },
        body: JSON.stringify({ model }),
      });
      const data = await res.json();
      if (data.ok) {
        llmStatus.innerHTML = '<span class="pill pill-ok">✓ ' + (data.detail || 'ok') + '</span>';
      } else {
        llmStatus.innerHTML = '<span class="pill pill-err">' + escapeHtml(data.detail || 'failed') + '</span>';
      }
    } catch (e) {
      llmStatus.innerHTML = '<span class="pill pill-err">' + escapeHtml(e.message) + '</span>';
    }
  });

  // ─── Sheets test ─────────────────────────────────────────────────────────
  document.getElementById('test-sheets').addEventListener('click', async () => {
    const el = document.getElementById('sheets-status');
    el.innerHTML = '<span class="pill pill-muted">testing…</span>';
    try {
      const res = await Ink.api('/api/settings/test-sheets', { method: 'POST', body: {} });
      if (res.ok) {
        el.innerHTML = '<span class="pill pill-ok">✓ ' + escapeHtml(res.title || 'connected') + '</span>';
      } else {
        el.innerHTML = '<span class="pill pill-err">' + escapeHtml(res.detail || 'failed') + '</span>';
      }
    } catch (e) {
      el.innerHTML = '<span class="pill pill-err">' + escapeHtml(e.message) + '</span>';
    }
  });

  // ─── load + save main settings ───────────────────────────────────────────
  async function load() {
    const data = await Ink.api('/api/settings');
    const filters = data.filters || {};
    const thresholds = filters.thresholds || {};
    const prefs = data.app_prefs || {};
    const sheets = data.sheets || {};

    // Output
    const out = prefs.output_target || 'both';
    document.querySelectorAll('input[name="output"]').forEach((r) => {
      r.checked = (r.value === out);
    });
    document.getElementById('spreadsheet-id').value = sheets.spreadsheet_id || '';

    // Filters
    const kw = filters.keywords || {};
    renderChips(document.querySelector('[data-chips="include"]'), kw.include || []);
    renderChips(document.querySelector('[data-chips="exclude"]'), kw.exclude || []);
    document.getElementById('min-score').value = thresholds.min_score ?? 2;
    document.getElementById('min-comments').value = thresholds.min_comments ?? 0;
    document.getElementById('max-comments').value = thresholds.max_comments ?? 500;
    document.getElementById('max-age').value = thresholds.max_age_hours ?? 24;

    const prefs_ai = filters.ai_preferences || {};
    renderChips(document.querySelector('[data-chips="prefer_topics"]'), prefs_ai.prefer_topics || []);
    renderChips(document.querySelector('[data-chips="avoid_topics"]'), prefs_ai.avoid_topics || []);

    renderChips(document.querySelector('[data-chips="subreddits"]'), data.subreddits || []);

    loadLlmFromStorage();
  }

  function buildPayload() {
    const include = readChips(document.querySelector('[data-chips="include"]'));
    const exclude = readChips(document.querySelector('[data-chips="exclude"]'));
    const prefer = readChips(document.querySelector('[data-chips="prefer_topics"]'));
    const avoid = readChips(document.querySelector('[data-chips="avoid_topics"]'));
    const subs = readChips(document.querySelector('[data-chips="subreddits"]'));

    const filters = {
      keywords: { include, exclude },
      thresholds: {
        min_score: +document.getElementById('min-score').value,
        min_comments: +document.getElementById('min-comments').value,
        max_comments: +document.getElementById('max-comments').value,
        max_age_hours: +document.getElementById('max-age').value,
      },
      ai_preferences: {
        prefer_topics: prefer,
        avoid_topics: avoid,
      },
    };

    const outRadio = document.querySelector('input[name="output"]:checked');
    return {
      filters,
      subreddits: subs,
      app_prefs: { output_target: outRadio ? outRadio.value : 'both' },
    };
  }

  document.getElementById('save-settings').addEventListener('click', async () => {
    const status = document.getElementById('save-status');
    status.textContent = 'Saving…';
    try {
      await Ink.api('/api/settings', { method: 'POST', body: buildPayload() });
      status.textContent = 'Saved ' + new Date().toLocaleTimeString();
      Ink.toast('Settings saved');
    } catch (e) {
      status.textContent = '';
      Ink.toast('Save failed: ' + e.message, true);
    }
  });

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  load().catch((e) => Ink.toast('Load failed: ' + e.message, true));
})();
