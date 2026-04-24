// Scan page — trigger a scan via SSE, render signals as they arrive,
// generate voice drafts on demand using the localStorage BYOK key.
//
// The scan endpoint now enforces a single active scan (409 on double-start)
// and supports POST /api/scan/stop + GET /api/scan/status. The UI reflects
// that state: Start disables while a scan runs, Stop appears, and fetch-level
// events (rate_limit, heartbeat, cancelled) surface directly in the log.

(function () {
  const logEl = document.getElementById('scan-log');
  const summaryEl = document.getElementById('scan-summary');
  const startBtn = document.getElementById('start-scan');
  const stopBtn = document.getElementById('stop-scan');
  const resetEl = document.getElementById('reset-progress');
  const quickEl = document.getElementById('quick-scan');
  const statusPill = document.getElementById('scan-status-pill');
  const tableEl = document.getElementById('signals-table');
  const tbodyEl = tableEl.querySelector('tbody');
  const emptyEl = document.getElementById('signals-empty');
  const datePicker = document.getElementById('date-picker');

  const modal = document.getElementById('draft-modal');
  const draftTitle = document.getElementById('draft-title');
  const draftReply = document.getElementById('draft-reply');
  const draftPost = document.getElementById('draft-post');
  const draftCost = document.getElementById('draft-cost');
  let currentSignalId = null;
  let scanning = false;

  // ─── summary + scan status on load ───────────────────────────────────────
  async function loadSummary() {
    try {
      const s = await Ink.api('/api/settings');
      const subCount = (s.subreddits || []).length;
      const maxAge = (s.filters && s.filters.thresholds && s.filters.thresholds.max_age_hours) || 24;
      summaryEl.textContent = `${subCount} subreddit${subCount !== 1 ? 's' : ''}, posts from the last ${maxAge} hours.`;
    } catch (_) {
      summaryEl.textContent = '';
    }
  }

  async function loadScanStatus() {
    // If a scan is already running (e.g. left over from a previous tab),
    // reflect that in the UI so the user can Stop it instead of getting 409.
    try {
      const st = await Ink.api('/api/scan/status');
      if (st.running) {
        setScanningUI(true);
        statusPill.textContent = st.current_subreddit ? `scanning r/${st.current_subreddit}` : 'scanning…';
        log('A scan is already running in the background. Click Stop to cancel it.');
      }
    } catch (_) {}
  }

  function setScanningUI(isScanning) {
    scanning = isScanning;
    startBtn.disabled = isScanning;
    stopBtn.classList.toggle('hidden', !isScanning);
    statusPill.classList.toggle('hidden', !isScanning);
    statusPill.classList.toggle('pill-warn', isScanning);
    statusPill.classList.toggle('pill-muted', !isScanning);
    if (isScanning) statusPill.textContent = 'scanning…';
  }

  // ─── log helpers ─────────────────────────────────────────────────────────
  function log(line) {
    if (logEl.querySelector('.scan-log-empty')) logEl.textContent = '';
    logEl.textContent += line + '\n';
    logEl.scrollTop = logEl.scrollHeight;
  }
  function clearLog() { logEl.textContent = ''; }

  // ─── signals table ───────────────────────────────────────────────────────
  function rowHtml(s) {
    const a = s.analysis || {};
    const engage = a.engage || 'No';
    const engageCls = engage === 'Yes' ? 'pill-ok' : engage === 'Maybe' ? 'pill-warn' : 'pill-muted';
    const ageVal = s.age_hours != null ? s.age_hours : '';
    const why = a.why || '';
    const title = s.title || '';
    return `
      <tr data-id="${escapeAttr(s.id || '')}">
        <td><span class="pill ${engageCls}">${escapeHtml(engage)}</span></td>
        <td>r/${escapeHtml(s.subreddit || '')}</td>
        <td><a href="${escapeAttr(s.url || '')}" target="_blank" rel="noopener">${escapeHtml(title)}</a></td>
        <td>${s.score ?? ''}</td>
        <td>${ageVal === '' ? '' : ageVal + 'h'}</td>
        <td class="muted small">${escapeHtml(why)}</td>
        <td><button class="btn btn-outline small" data-action="draft">Draft</button></td>
      </tr>
    `;
  }

  function renderSignals(signals) {
    if (!signals || !signals.length) {
      emptyEl.classList.remove('hidden');
      tableEl.classList.add('hidden');
      return;
    }
    emptyEl.classList.add('hidden');
    tableEl.classList.remove('hidden');
    const rank = { Yes: 0, Maybe: 1, No: 2 };
    const sorted = [...signals].sort((a, b) => {
      const ra = rank[(a.analysis || {}).engage] ?? 3;
      const rb = rank[(b.analysis || {}).engage] ?? 3;
      if (ra !== rb) return ra - rb;
      return (b.score || 0) - (a.score || 0);
    });
    tbodyEl.innerHTML = sorted.map(rowHtml).join('');
  }

  async function loadDate(date) {
    const data = await Ink.api('/api/signals' + (date ? `?date=${encodeURIComponent(date)}` : ''));
    if (!datePicker.options.length) {
      const dates = data.available_dates || [];
      if (!dates.includes(data.date)) dates.unshift(data.date);
      datePicker.innerHTML = dates.map((d) =>
        `<option value="${escapeAttr(d)}"${d === data.date ? ' selected' : ''}>${escapeHtml(d)}</option>`
      ).join('');
    }
    renderSignals(data.signals || []);
  }

  datePicker.addEventListener('change', () => loadDate(datePicker.value));

  // ─── row interactions (delegated) ────────────────────────────────────────
  tbodyEl.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    const tr = btn.closest('tr');
    const id = tr && tr.dataset.id;
    if (!id) return;
    if (btn.dataset.action === 'draft') {
      openDraft(id, false);
    }
  });

  // ─── start scan (SSE) ────────────────────────────────────────────────────
  startBtn.addEventListener('click', async () => {
    if (scanning) return; // defensive: UI guard matches server lock
    setScanningUI(true);
    clearLog();
    log('Starting scan…');

    const payload = { reset_progress: resetEl.checked };
    if (quickEl.checked) payload.limit_subreddits = 3;

    let res;
    try {
      res = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch (e) {
      log('Network error: ' + e.message);
      setScanningUI(false);
      return;
    }

    if (res.status === 409) {
      const body = await res.json().catch(() => ({}));
      log('  ' + (body.detail || 'A scan is already running.'));
      // Sync UI to real state.
      await loadScanStatus();
      return;
    }
    if (!res.ok || !res.body) {
      log('Failed to start scan (HTTP ' + res.status + ')');
      setScanningUI(false);
      return;
    }

    const newSignals = [];
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const frames = buf.split('\n\n');
      buf = frames.pop();
      for (const frame of frames) {
        const line = frame.replace(/^data: /, '').trim();
        if (!line) continue;
        let ev;
        try { ev = JSON.parse(line); } catch { continue; }
        handleEvent(ev, newSignals);
      }
    }

    setScanningUI(false);
    datePicker.innerHTML = '';
    await loadDate();
  });

  stopBtn.addEventListener('click', async () => {
    stopBtn.disabled = true;
    try {
      const res = await Ink.api('/api/scan/stop', { method: 'POST', body: {} });
      if (res.ok) {
        log('  requesting cancellation…');
      } else {
        log('  ' + (res.detail || 'Stop failed'));
      }
    } catch (e) {
      log('  stop request failed: ' + e.message);
    } finally {
      stopBtn.disabled = false;
    }
  });

  function handleEvent(ev, newSignals) {
    switch (ev.kind) {
      case 'start':
        log(`Scanning ${ev.subreddit_count} subreddit${ev.subreddit_count !== 1 ? 's' : ''}, last ${ev.max_age_hours}h (${ev.already_done} already done).`);
        break;
      case 'subreddit_start':
        log(`[${ev.index}/${ev.total}] r/${ev.subreddit}`);
        statusPill.textContent = `r/${ev.subreddit} (${ev.index}/${ev.total})`;
        break;
      case 'subreddit_skipped':
        log(`  skipped r/${ev.subreddit} (already done)`);
        break;
      case 'posts_fetched':
        log(`  fetched ${ev.count} post${ev.count !== 1 ? 's' : ''}`);
        break;
      case 'posts_filtered':
        log(`  filters: ${ev.kept} of ${ev.raw} post${ev.raw !== 1 ? 's' : ''} passed`);
        break;
      case 'posts_capped':
        log(`  capping to top ${ev.cap} by score`);
        break;
      case 'post_analyzing':
        log(`  · ${ev.index}/${ev.total} "${ev.title}"`);
        break;
      case 'subreddit_done':
        log(`  done — ${ev.kept} kept`);
        break;
      case 'subreddit_error':
        log(`  ERROR r/${ev.subreddit}: ${ev.error}`);
        break;
      case 'rate_limit':
        log(`  ⏳ Reddit rate-limited — waiting ${ev.wait_s}s (try ${ev.attempt}/${ev.max_attempts})`);
        break;
      case 'forbidden':
        log(`  403 ${truncateUrl(ev.url)} — skipping`);
        break;
      case 'retry_error':
        log(`  network hiccup (try ${ev.attempt}/${ev.max_attempts}): ${ev.error}`);
        break;
      case 'fetch_failed':
        log(`  fetch failed: ${truncateUrl(ev.url)} — ${ev.error}`);
        break;
      case 'heartbeat':
        // Low-noise liveness indicator while Reddit is silent.
        statusPill.textContent = ev.current_subreddit
          ? `r/${ev.current_subreddit} · ${ev.elapsed_s}s`
          : `running · ${ev.elapsed_s}s`;
        break;
      case 'signal':
        log(`  + ${ev.row.analysis.engage}  ${ev.row.title.slice(0, 80)}`);
        newSignals.push(ev.row);
        break;
      case 'cancelled':
        log('\n— scan cancelled —');
        break;
      case 'done':
        log(`\nDone. ${ev.new_signals} new signal${ev.new_signals !== 1 ? 's' : ''}.`);
        break;
      case 'error':
        log(`\nScan error: ${ev.message}`);
        break;
    }
  }

  function truncateUrl(u) {
    if (!u) return '';
    try {
      const url = new URL(u);
      return url.pathname;
    } catch { return String(u).slice(0, 60); }
  }

  // ─── draft modal ─────────────────────────────────────────────────────────
  async function openDraft(signalId, regenerate) {
    const llm = Ink.llm.get();
    if (!Ink.llm.hasKey()) {
      Ink.toast('Set your LLM key in Settings first', true);
      return;
    }
    currentSignalId = signalId;
    draftTitle.textContent = 'Draft — ' + signalId;
    draftReply.textContent = 'Generating…';
    draftPost.textContent = '';
    draftCost.textContent = '';
    modal.classList.remove('hidden');

    try {
      const res = await fetch('/api/signals/' + encodeURIComponent(signalId) + '/draft', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(llm.key ? { 'X-LLM-Key': llm.key } : {}),
        },
        body: JSON.stringify({ model: llm.model, regenerate: !!regenerate }),
      });
      const data = await res.json();
      if (!res.ok) {
        draftReply.textContent = '';
        draftPost.textContent = data.detail || ('HTTP ' + res.status);
        return;
      }
      draftReply.textContent = (data.drafts && data.drafts.reply_to_comment) || '—';
      draftPost.textContent = (data.drafts && data.drafts.post_comment) || '—';
      draftCost.textContent = data.cached ? 'cached (no tokens used)' : 'model: ' + data.model;
    } catch (e) {
      draftReply.textContent = '';
      draftPost.textContent = e.message;
    }
  }

  document.getElementById('draft-close').addEventListener('click', () => {
    modal.classList.add('hidden');
  });
  document.getElementById('draft-regenerate').addEventListener('click', () => {
    if (currentSignalId) openDraft(currentSignalId, true);
  });
  modal.querySelectorAll('[data-copy]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = document.getElementById(btn.dataset.copy);
      if (target) Ink.copyToClipboard(target.textContent);
    });
  });
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
  });

  // ─── escape helpers ──────────────────────────────────────────────────────
  function escapeHtml(s) {
    return String(s ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }
  function escapeAttr(s) { return escapeHtml(s); }

  loadSummary();
  loadScanStatus();
  loadDate().catch(() => renderSignals([]));
})();
