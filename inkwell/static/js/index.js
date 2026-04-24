// Landing page — toggle each checklist item to "done" based on the
// current install state. The signals for each step are independent so
// this is just a bunch of tiny probes.

(async function () {
  const marks = {
    profile: false,
    output: false,
    llm: false,
    subreddits: false,
    scan: false,
  };

  try {
    const p = await Ink.api('/api/profile');
    marks.profile = !!p.configured;
  } catch (_) {}

  try {
    const s = await Ink.api('/api/settings');
    const prefs = s.app_prefs || {};
    marks.subreddits = Array.isArray(s.subreddits) && s.subreddits.length > 0;
    const out = prefs.output_target;
    if (out === 'csv') marks.output = true;
    else if (s.sheets && s.sheets.token_present) marks.output = true;
  } catch (_) {}

  marks.llm = Ink.llm.hasKey();

  try {
    const sig = await Ink.api('/api/signals');
    marks.scan = (sig.signals && sig.signals.length > 0) ||
                 (sig.available_dates && sig.available_dates.length > 0);
  } catch (_) {}

  document.querySelectorAll('#checklist li[data-step]').forEach((li) => {
    const step = li.getAttribute('data-step');
    const icon = li.querySelector('[data-icon]');
    if (marks[step]) {
      icon.classList.add('done');
    }
  });
})();
