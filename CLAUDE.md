# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Inkwell — a Python CLI + FastAPI web UI that scans Reddit (and eventually HN / Product Hunt) for posts where people are asking for help, scores them with pure-heuristic rules (no LLM), and generates replies in the user's voice **only on demand** using a BYOK LLM key. Results are written to Google Sheets / CSV; the web UI adds visual config, profile building, live scan streaming (SSE), and per-signal draft generation.

Requires Python 3.11+. Installed as an editable package (`pip install -e .`) exposing the `inkwell` console script. Single-user localhost tool — binds to `127.0.0.1`.

## Commands

```bash
# Activate venv first: source .venv/bin/activate

# Install in dev mode
pip install -e ".[dev]"

# Run a Reddit scan → Google Sheets (default)
python -m inkwell scan

# Pick a different subreddit list (file resolved against config/)
python -m inkwell scan --subreddits subreddits_1.yml

# Export to CSV, skip Sheets (useful when iterating without Google OAuth)
python -m inkwell scan --csv --no-sheets

# Verbose logging
python -m inkwell scan -v

# Generate a voice draft for one stored signal (uses BYOK LLM key from env)
python -m inkwell draft reddit_abc123 --model gpt-4o-mini

# FastAPI web UI — four HTML pages at /, /profile, /settings, /scan (binds 127.0.0.1)
python -m inkwell serve --port 8000 --reload

# Tests / lint (dev extra installs pytest + ruff)
pytest
pytest -k reddit          # match keyword
pytest tests/test_analyzers/test_rules.py       # heuristic scoring tests
pytest tests/test_filters/test_rule_filter.py   # single file
ruff check inkwell/
ruff format inkwell/
```

Ruff config: line length 100, target `py311` (see [pyproject.toml](pyproject.toml)).

## Architecture

The package is a pipeline of protocol-based components wired together by [inkwell/__main__.py](inkwell/__main__.py):

```
config/*.yml + .env  →  config.py  →  scanners → filters → analyzers → exporters
                                         ↓           ↓         ↓          ↓
                                         └───── personas ──────┘      storage/ (JSON on disk)
```

Key points future instances must know:

- **`config.py` is the single source of truth for settings.** It loads `.env` (secrets, `LLM_MODEL`, etc.), exposes path constants (`ROOT_DIR`, `CONFIG_DIR`, `DATA_DIR`), and provides `load_subreddits / load_personality / load_filters`. Each loader has a **backward-compat fallback**: if a YAML file is missing from `config/`, it looks in `ROOT_DIR`. Preserve this when changing loaders.
- **Scanners, exporters, and filters are Protocol-based** (structural typing, not inheritance). A scanner is anything with `name: str` and `scan(targets, max_age_hours) → list[RawSignal]`. An exporter has `name` + `export(rows, config)`. Add new platforms/outputs by creating a class that matches the protocol — no base class required.
- **Scanners self-register via a lazy registry.** New scanners must (1) call `registry.register(MyScanner())` at module level, and (2) be imported inside [registry.py](inkwell/scanners/registry.py)'s `_ensure_loaded()` so they load on first `get_scanner()` call.
- **Filtering happens before scoring.** [filters/rule_filter.py](inkwell/filters/rule_filter.py) applies keywords/score/flair/post-type rules first; [analyzers/rules.py](inkwell/analyzers/rules.py) then scores what survives. `ai_preferences.prefer_topics` is a soft boost to the engage score; `ai_preferences.avoid_topics` is a hard "No". Neither spends tokens.
- **The analyzer is split: rules (free) + voice (BYOK, on demand).** [analyzers/rules.py](inkwell/analyzers/rules.py) is pure heuristics and produces `summary`, `coolest_comment`, `engage` (Yes/Maybe/No), and `why`. [analyzers/pipeline.py](inkwell/analyzers/pipeline.py) is a thin wrapper calling `analyze_rules` — **the LLM is never invoked during scan**. [analyzers/voice.py](inkwell/analyzers/voice.py) is the only code path that spends tokens; it takes `model` and `api_key` as arguments (not env) so the web UI can BYOK from browser `localStorage` via the `X-LLM-Key` header, and the server never persists the key. Native JSON mode is still OpenAI-only (see `_supports_native_json_mode` in [llm_client.py](inkwell/analyzers/llm_client.py)). The old single-call pipeline (summary + engage + voice in one LLM request) was removed when scans became free.
- **Voice drafts are NOT produced at scan time.** CSV/Sheets exports show em-dashes for `Suggested reply to cool comment` and `Suggested post comment`. Users generate drafts on demand via the UI's *Draft* button (`POST /api/signals/{id}/draft`) or `inkwell draft <signal_id>` on the CLI. Drafts are cached back into the daily signal JSON (`drafts` field) so refresh/second-visit doesn't re-bill.
- **Web UI is plain HTML/CSS/JS — no framework.** Jinja2 templates in [inkwell/templates/](inkwell/templates/), shared CSS at [inkwell/static/app.css](inkwell/static/app.css), one JS module per page in [inkwell/static/js/](inkwell/static/js/). Routes: [routes/pages.py](inkwell/routes/pages.py) renders HTML; [routes/api_profile.py](inkwell/routes/api_profile.py), [routes/api_settings.py](inkwell/routes/api_settings.py), [routes/api_scan.py](inkwell/routes/api_scan.py), [routes/api_signals.py](inkwell/routes/api_signals.py) handle JSON. Server binds `127.0.0.1` — there is no auth, by design (single-user localhost tool).
- **Only `engage == "Yes"` rows populate the `Coolest comment` column** in CSV/Sheets exports; `Maybe`/`No` rows display em-dashes (`\u2014`). This is intentional noise reduction — don't "fix" it.
- **Storage is JSON files on disk, not a database.** Everything under `data/` (`signals/`, `campaigns/`, `feedback/`, `scan_history/`, `progress.json`) is human-readable JSON. `ensure_data_dirs()` creates the subdirectories — call it before any storage I/O.
- **Resume-by-default is core to the scan loop.** [storage/progress.py](inkwell/storage/progress.py) tracks `completed_subs` and `processed_ids`; re-running the same day skips what's already done, and progress resets automatically on a new UTC date. Signals are also deduped by `id` on save. Any change to the scan loop must preserve both levels of dedup and the `KeyboardInterrupt` → flush-then-save-progress path in `__main__.py`.
- **Google Sheets export has a fallback.** On write failure, [exporters/google_sheets.py](inkwell/exporters/google_sheets.py) writes to `fallback_rows.json`. It also creates one tab per day (`YYYY-MM-DD`) and appends via `INSERT_ROWS`. `token.json` stores OAuth credentials — deleting it forces re-auth.
- **Reddit scanner uses the public JSON API** (no PRAW, no auth). Rate-limit handling is hand-rolled: 2s sleep between calls (`REDDIT_SLEEP`), exponential backoff on 429 (5/10/15s), skip on 403, 3 retries on network errors. Post `status` (`active`/`archived`/`inactive`/`blocked`) is derived from Reddit flags and flows through to filters and exports.

## Adding things

- **New scanner** → create `scanners/<platform>.py` implementing the Scanner protocol, register at module bottom, add import to `registry._ensure_loaded()`. Use `fetch_json()` from [scanners/base.py](inkwell/scanners/base.py) for retries.
- **New exporter** → create `exporters/<name>.py` with `name` + `export(rows, config)`, wire a CLI flag in `__main__.py`.
- **New output column** → append to `COLUMNS` in [config.py](inkwell/config.py), populate the row dict in `__main__.py`'s scan loop, and (if it's AI-derived) add the key to the LLM prompt + `Analysis` dataclass.

Deeper architectural detail, data-flow diagrams, and error-handling tables live in [README_TECHNICAL.md](README_TECHNICAL.md) — check there before making non-trivial structural changes.
