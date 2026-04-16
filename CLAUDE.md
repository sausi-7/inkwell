# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

OutreachPilot — a Python CLI (and incubating FastAPI web UI) that scans Reddit (and eventually HN / Product Hunt) for posts where people are asking for help, then uses an LLM to summarize, score engagement potential, pick the best comment, and draft replies in the user's voice. Results are written to Google Sheets / CSV.

Requires Python 3.11+. Installed as an editable package (`pip install -e .`) exposing the `outreachpilot` console script.

## Commands

```bash
# Activate venv first: source .venv/bin/activate

# Install in dev mode
pip install -e ".[dev]"

# Run a Reddit scan → Google Sheets (default)
python -m outreachpilot scan

# Pick a different subreddit list (file resolved against config/)
python -m outreachpilot scan --subreddits subreddits_1.yml

# Export to CSV, skip Sheets (useful when iterating without Google OAuth)
python -m outreachpilot scan --csv --no-sheets

# Verbose logging
python -m outreachpilot scan -v

# FastAPI web UI (placeholder — Phase 1 in progress)
python -m outreachpilot serve --port 8000 --reload

# Tests / lint (dev extra installs pytest + ruff)
pytest
pytest -k reddit          # match keyword
pytest tests/test_filters/test_rule_filter.py   # single file
ruff check outreachpilot/
ruff format outreachpilot/
```

Ruff config: line length 100, target `py311` (see [pyproject.toml](pyproject.toml)).

## Architecture

The package is a pipeline of protocol-based components wired together by [outreachpilot/__main__.py](outreachpilot/__main__.py):

```
config/*.yml + .env  →  config.py  →  scanners → filters → analyzers → exporters
                                         ↓           ↓         ↓          ↓
                                         └───── personas ──────┘      storage/ (JSON on disk)
```

Key points future instances must know:

- **`config.py` is the single source of truth for settings.** It loads `.env` (secrets, `LLM_MODEL`, etc.), exposes path constants (`ROOT_DIR`, `CONFIG_DIR`, `DATA_DIR`), and provides `load_subreddits / load_personality / load_filters`. Each loader has a **backward-compat fallback**: if a YAML file is missing from `config/`, it looks in `ROOT_DIR`. Preserve this when changing loaders.
- **Scanners, exporters, and filters are Protocol-based** (structural typing, not inheritance). A scanner is anything with `name: str` and `scan(targets, max_age_hours) → list[RawSignal]`. An exporter has `name` + `export(rows, config)`. Add new platforms/outputs by creating a class that matches the protocol — no base class required.
- **Scanners self-register via a lazy registry.** New scanners must (1) call `registry.register(MyScanner())` at module level, and (2) be imported inside [registry.py](outreachpilot/scanners/registry.py)'s `_ensure_loaded()` so they load on first `get_scanner()` call.
- **Filtering happens before AI.** [filters/rule_filter.py](outreachpilot/filters/rule_filter.py) applies keywords/score/flair/post-type rules first to avoid spending LLM tokens on junk. `ai_preferences` in `filters.yml` is a soft hint passed into the prompt, not a hard filter — don't treat it as one.
- **The LLM contract is JSON-shaped.** [analyzers/pipeline.py](outreachpilot/analyzers/pipeline.py) builds a prompt from persona + signal + AI prefs, calls [llm_client.py](outreachpilot/analyzers/llm_client.py) (LiteLLM — same code works with OpenAI, Claude, Ollama, etc.; the provider is selected by `LLM_MODEL`'s prefix), and parses the response into an `Analysis` dataclass. If you add output columns, also update the prompt's required JSON keys — the row builder in `__main__.py` reads those keys by name. Native JSON mode is only enabled for OpenAI models (see `_supports_native_json_mode`); other providers rely on the prompt instruction + fence stripping.
- **Only `engage == "Yes"` rows get populated suggestions** in exports; `Maybe`/`No` rows display an em-dash (`\u2014`). This is intentional noise reduction — don't "fix" it.
- **Storage is JSON files on disk, not a database.** Everything under `data/` (`signals/`, `campaigns/`, `feedback/`, `scan_history/`, `progress.json`) is human-readable JSON. `ensure_data_dirs()` creates the subdirectories — call it before any storage I/O.
- **Resume-by-default is core to the scan loop.** [storage/progress.py](outreachpilot/storage/progress.py) tracks `completed_subs` and `processed_ids`; re-running the same day skips what's already done, and progress resets automatically on a new UTC date. Signals are also deduped by `id` on save. Any change to the scan loop must preserve both levels of dedup and the `KeyboardInterrupt` → flush-then-save-progress path in `__main__.py`.
- **Google Sheets export has a fallback.** On write failure, [exporters/google_sheets.py](outreachpilot/exporters/google_sheets.py) writes to `fallback_rows.json`. It also creates one tab per day (`YYYY-MM-DD`) and appends via `INSERT_ROWS`. `token.json` stores OAuth credentials — deleting it forces re-auth.
- **Reddit scanner uses the public JSON API** (no PRAW, no auth). Rate-limit handling is hand-rolled: 2s sleep between calls (`REDDIT_SLEEP`), exponential backoff on 429 (5/10/15s), skip on 403, 3 retries on network errors. Post `status` (`active`/`archived`/`inactive`/`blocked`) is derived from Reddit flags and flows through to filters and exports.

## Adding things

- **New scanner** → create `scanners/<platform>.py` implementing the Scanner protocol, register at module bottom, add import to `registry._ensure_loaded()`. Use `fetch_json()` from [scanners/base.py](outreachpilot/scanners/base.py) for retries.
- **New exporter** → create `exporters/<name>.py` with `name` + `export(rows, config)`, wire a CLI flag in `__main__.py`.
- **New output column** → append to `COLUMNS` in [config.py](outreachpilot/config.py), populate the row dict in `__main__.py`'s scan loop, and (if it's AI-derived) add the key to the LLM prompt + `Analysis` dataclass.

Deeper architectural detail, data-flow diagrams, and error-handling tables live in [README_TECHNICAL.md](README_TECHNICAL.md) — check there before making non-trivial structural changes.
