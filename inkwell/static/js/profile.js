// Profile page — load personality.yml, render as form, save on submit.

(function () {
  const form = document.getElementById('profile-form');
  const examplesEl = document.getElementById('examples');
  const addExampleBtn = document.getElementById('add-example');
  const previewToggle = document.getElementById('toggle-preview');
  const previewEl = document.getElementById('prompt-preview');
  const saveStatus = document.getElementById('save-status');

  const chipGroups = Array.from(document.querySelectorAll('[data-chips]'));

  // ─── chip inputs ─────────────────────────────────────────────────────────
  function renderChips(group, items) {
    const key = group.dataset.chips;
    const input = group.querySelector('input');
    // Remove previous chips
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

  chipGroups.forEach((group) => {
    const input = group.querySelector('input');
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const val = input.value.trim();
        if (!val) return;
        const existing = readChips(group);
        if (existing.includes(val)) {
          input.value = '';
          return;
        }
        renderChips(group, [...existing, val]);
        input.value = '';
      } else if (e.key === 'Backspace' && !input.value) {
        const chips = group.querySelectorAll('.chip');
        if (chips.length) chips[chips.length - 1].remove();
      }
    });
  });

  // ─── example comments ────────────────────────────────────────────────────
  function addExample(text = '') {
    const wrap = document.createElement('div');
    wrap.className = 'form-row';
    const ta = document.createElement('textarea');
    ta.rows = 4;
    ta.placeholder = 'A comment you\'d actually write…';
    ta.value = text;
    wrap.appendChild(ta);
    const rm = document.createElement('button');
    rm.type = 'button';
    rm.className = 'btn btn-outline small';
    rm.textContent = 'Remove';
    rm.style.alignSelf = 'flex-start';
    rm.addEventListener('click', () => wrap.remove());
    wrap.appendChild(rm);
    examplesEl.appendChild(wrap);
  }

  addExampleBtn.addEventListener('click', () => addExample());

  function readExamples() {
    return Array.from(examplesEl.querySelectorAll('textarea'))
      .map((t) => t.value.trim())
      .filter(Boolean);
  }

  // ─── load ────────────────────────────────────────────────────────────────
  async function load() {
    const data = await Ink.api('/api/profile');
    const p = data.profile || {};
    document.getElementById('name').value = p.name || '';
    document.getElementById('bio').value = p.bio || '';
    document.getElementById('tone-style').value = (p.tone && p.tone.style) || '';
    document.getElementById('tone-humor').value = (p.tone && p.tone.humor) || '';
    document.getElementById('tone-formality').value = (p.tone && p.tone.formality) || '';

    renderChips(document.querySelector('[data-chips="interests"]'), p.interests);
    renderChips(document.querySelector('[data-chips="expertise"]'), p.expertise);
    renderChips(document.querySelector('[data-chips="dos"]'), p.dos);
    renderChips(document.querySelector('[data-chips="donts"]'), p.donts);

    examplesEl.innerHTML = '';
    (p.example_comments || []).forEach(addExample);
    if ((p.example_comments || []).length === 0) {
      addExample(''); addExample('');
    }

    previewEl.textContent = data.prompt_preview || '';
  }

  // ─── save ────────────────────────────────────────────────────────────────
  function buildPayload() {
    return {
      name: document.getElementById('name').value.trim(),
      bio: document.getElementById('bio').value.trim(),
      interests: readChips(document.querySelector('[data-chips="interests"]')),
      expertise: readChips(document.querySelector('[data-chips="expertise"]')),
      tone: {
        style: document.getElementById('tone-style').value.trim(),
        humor: document.getElementById('tone-humor').value.trim(),
        formality: document.getElementById('tone-formality').value.trim(),
      },
      dos: readChips(document.querySelector('[data-chips="dos"]')),
      donts: readChips(document.querySelector('[data-chips="donts"]')),
      example_comments: readExamples(),
    };
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = buildPayload();
    saveStatus.textContent = 'Saving…';
    try {
      const res = await Ink.api('/api/profile', { method: 'POST', body: payload });
      previewEl.textContent = res.prompt_preview || '';
      saveStatus.textContent = 'Saved ' + new Date().toLocaleTimeString();
      Ink.toast('Profile saved');
    } catch (err) {
      saveStatus.textContent = '';
      Ink.toast('Save failed: ' + err.message, true);
    }
  });

  previewToggle.addEventListener('click', () => {
    previewEl.classList.toggle('hidden');
  });

  load().catch((e) => Ink.toast('Load failed: ' + e.message, true));
})();
