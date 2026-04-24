# Inkwell

**Open source AI outreach intelligence tool for entrepreneurs.**

Find real people with real problems you can actually help — across every platform where they talk about it.

[![CI](https://github.com/sausi-7/inkwell/actions/workflows/ci.yml/badge.svg)](https://github.com/sausi-7/inkwell/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## What It Does

Inkwell scans communities (Reddit today; Hacker News / Product Hunt / more via community scanners) for posts where people are asking for help, sharing projects, or discussing problems you can solve. It splits the work into two clean stages:

**Scanning is free (no LLM tokens).** Rule-based heuristics pick the signal, score engagement potential (Yes / Maybe / No), summarize the post, and surface the most interesting comment. Deterministic, auditable, fast.

**Voice drafting is BYOK, on demand.** When you see a signal worth replying to, click **Draft** and Inkwell uses *your* LLM key to write a reply in *your* voice — trained on your dos, don'ts, and example comments. The key lives in your browser's localStorage and never hits the server except on that one draft request.

### Why Inkwell?

Most outreach tools start with a contact database and blast cold messages. Inkwell flips this: it starts with **real signals** — people publicly expressing problems — and helps you engage authentically where they already are.

Three things make it different:

- **$0 until you draft.** Every other "AI outreach" tool bills you to scan. We don't spend a token until you ask for a reply in your voice.
- **Your voice, not LLM-speak.** The persona is a first-class artifact (YAML). Fork someone else's. Publish your own. Replies stop sounding generic.
- **Self-hosted, no lock-in.** One `pip install`, runs on your laptop, your data never leaves your machine. LLM provider of your choice (OpenAI, Claude, Ollama, local).

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/sausi-7/inkwell.git
cd inkwell

# Create a virtualenv — keeps deps off your system Python
python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# Editable install (CLI + web UI + FastAPI / LiteLLM / Jinja2 / …)
pip install -e ".[dev]"
```

Every `inkwell`, `python`, and `pytest` command in this README assumes the venv is active. Re-run `source .venv/bin/activate` in a fresh terminal to come back.

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
OPENAI_API_KEY=sk-your_openai_key
SPREADSHEET_ID=your_spreadsheet_id
```

### 3. Run

**Recommended — Web UI:**

```bash
python -m inkwell serve
```

Then open [http://localhost:8000](http://localhost:8000). The landing page walks you through profile → output → BYOK key → subreddits → first scan. The key lives in your browser; the server never sees it except when you click *Draft*.

**CLI — headless / cron:**

```bash
# Scan Reddit and export to Google Sheets (needs Google OAuth — one-time)
python -m inkwell scan

# Scan and export to CSV only (no Google setup required)
python -m inkwell scan --csv --no-sheets

# Generate a voice draft for a stored signal (uses your LLM key)
python -m inkwell draft reddit_abc123 --model gpt-4o-mini
```

**First Google Sheets run:** A browser window opens for OAuth. Sign in and grant Sheets access. Happens once.

---

## Web UI

Four pages, plain HTML/CSS/JS, no framework. Binds to `127.0.0.1` only — single-user, self-hosted.

- **`/` Home** — onboarding checklist that turns green as each step is complete.
- **`/profile`** — edit your persona visually. See the exact prompt the LLM will use.
- **`/settings`** — pick output (CSV / Sheets / both), paste your LLM key (stored in browser localStorage, never on the server), test the Google Sheets connection and the LLM key with one click, edit filters and the subreddit list.
- **`/scan`** — start a scan, watch SSE-streamed progress, and see signals scored as they arrive. Click **Draft** on any signal to generate a reply and a top-level comment in your voice. Drafts are cached per-signal so refreshing doesn't re-bill you.

### BYOK security model

- No auth. The server binds to `127.0.0.1` — do not expose it on a shared network without adding your own reverse proxy + auth.
- The LLM key is stored in the browser's `localStorage` under `ink_llm_key`. It never lands in `.env` or any log.
- On a draft request, the browser sends the key as the `X-LLM-Key` header. The server passes it straight to LiteLLM and does not write it anywhere.

---

## How It Works

```
You configure subreddits, personality, and filters
                    |
                    v
    +---------------------------------+
    |  Scan communities for signals   |  Reddit, HN, Product Hunt...
    +---------------------------------+
                    |
                    v
    +---------------------------------+
    |  Rule-based filter + score      |  ZERO tokens — keywords, score,
    |  (analyzers/rules.py)           |  flairs, velocity, age, Yes/Maybe/No
    +---------------------------------+
                    |
                    v
    +---------------------------------+
    |  Export + persist signals       |  Google Sheets, CSV, data/signals
    +---------------------------------+
                    |
                    v  (user clicks "Draft" in the web UI, per signal)
                    |
    +---------------------------------+
    |  Voice drafting (BYOK)          |  LLM tokens spent ONLY here.
    |  (analyzers/voice.py)           |  Key is per-request from browser
    |  OpenAI / Claude / Ollama       |  localStorage — never persisted.
    +---------------------------------+
```

### Output Columns

| Column | Description |
|--------|-------------|
| Subreddit | e.g. `r/SaaS` |
| Post title | Title of the post |
| Summary | AI-generated 1-2 sentence summary |
| Age (hrs) | Hours since post creation |
| Created UTC | Post creation timestamp |
| Engage? | `Yes`, `No`, or `Maybe` |
| Why | 1-sentence reasoning for the recommendation |
| Status | `active`, `archived`, `inactive`, or `blocked` |
| Coolest comment | Most interesting/insightful comment in the thread |
| Suggested reply to cool comment | A reply written in your voice |
| Suggested post comment | A standalone comment for the post |
| Post link | Direct URL to the post |
| Source URL(s) | API endpoints used |

Only posts marked **"Yes"** have the coolest comment populated in the CSV/Sheets export. All three voice columns (`Coolest comment reply`, `Suggested post comment`) now show dashes by default — they're filled on demand when you click *Draft* in the web UI or run `inkwell draft <signal_id>`. This is the BYOK split: scans never burn tokens.

---

## Configuration

### Subreddits — `config/subreddits.yml`

Simple list of subreddit names to scan:

```yaml
- Entrepreneur
- SaaS
- SideProject
- learnprogramming
- indiegames
```

Two lists are included: `subreddits.yml` (21 curated) and `subreddits_1.yml` (101 broad). Switch between them:

```bash
python -m inkwell scan --subreddits subreddits_1.yml
```

### Personality — `config/personality.yml`

Define the voice and tone of AI-generated comments:

```yaml
name: Saurabh
bio: "Indie developer and creative coder. Building AI-powered tools..."
interests: [game development, AI/ML tools, creative coding, indie hacking]
expertise: [Python scripting, AI integration, app development]
tone:
  style: "conversational, slightly nerdy, genuinely curious"
  humor: "dry wit, occasional puns, self-deprecating"
  formality: "casual but knowledgeable"
dos:
  - Share specific experiences
  - Ask follow-up questions
  - Offer concrete advice
donts:
  - Never mention products unless asked
  - No excessive enthusiasm
  - Max 1 emoji per comment
example_comments:
  - "I ran into the same issue last month..."
```

The AI uses this profile so comments sound like **you**, not a generic bot. Without this file, a default conversational tone is used.

### Filters — `config/filters.yml`

Control which posts get analyzed. Filters run **before** AI, saving API costs:

| Filter | What It Does | Default |
|--------|-------------|---------|
| `keywords.include` | Post must contain at least one keyword | `[]` (no filter) |
| `keywords.exclude` | Skip if post contains any of these | `[hiring, nsfw, crypto airdrop]` |
| `thresholds.min_score` | Minimum upvote score | `2` |
| `thresholds.max_comments` | Skip mega-threads | `500` |
| `thresholds.max_age_hours` | How far back to scan | `24` |
| `post_type.allow` | `all`, `self_only`, or `link_only` | `all` |
| `flairs.include/exclude` | Filter by post flair | `exclude: [Meme, Shitpost, NSFW]` |
| `allowed_statuses` | Which post statuses to keep | `[active]` |
| `ai_preferences` | Guides AI engagement decisions (not a hard filter) | see file |

### LLM Provider — `.env`

Inkwell uses [LiteLLM](https://docs.litellm.ai/) so one setting switches providers. Pick any model and set the matching API key:

```
# OpenAI
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-4-6

# Ollama (local, no key needed — just have Ollama running)
LLM_MODEL=ollama/llama3
OLLAMA_API_BASE=http://localhost:11434
```

Any model LiteLLM supports works — Gemini, Groq, Together, Mistral, etc. See [LiteLLM providers](https://docs.litellm.ai/docs/providers).

---

## Stopping and Resuming

Press `Ctrl+C` at any time. Progress is saved automatically after each subreddit.

When you run again on the same day:
- Completed subreddits are skipped
- Already-analyzed posts are skipped
- Continues exactly where it left off

Progress resets automatically each new day.

---

## Project Structure

```
inkwell/
├── inkwell/              # Python package
│   ├── __main__.py             # CLI entry point
│   ├── app.py                  # FastAPI web app (Phase 1)
│   ├── config.py               # Settings loader
│   ├── scanners/               # Platform scanners
│   │   ├── base.py             # Scanner protocol + data models
│   │   ├── reddit.py           # Reddit scanner
│   │   └── registry.py         # Auto-discovery registry
│   ├── analyzers/              # AI analysis engine
│   │   ├── base.py             # Analysis data model
│   │   ├── pipeline.py         # Prompt building + LLM call
│   │   └── llm_client.py       # LLM wrapper (OpenAI, LiteLLM)
│   ├── filters/                # Signal filtering
│   │   ├── rule_filter.py      # Rule-based pre-filtering
│   │   └── dedup.py            # Cross-day deduplication
│   ├── personas/               # Voice/tone engine
│   │   ├── loader.py           # Load from YAML
│   │   └── prompt_builder.py   # Build persona prompt blocks
│   ├── exporters/              # Output adapters
│   │   ├── google_sheets.py    # Google Sheets export
│   │   └── csv_exporter.py     # CSV export
│   └── storage/                # Local file storage
│       ├── progress.py         # Checkpoint/resume
│       ├── signals.py          # Signal CRUD (JSON files)
│       ├── campaigns.py        # Campaign management
│       ├── feedback.py         # Quality ratings
│       └── scan_history.py     # Scan run tracking
├── config/                     # YAML configuration files
│   ├── personality.yml         # Your voice profile
│   ├── filters.yml             # Filtering rules
│   └── subreddits.yml          # Target subreddits
├── data/                       # Runtime data (auto-created)
│   ├── signals/                # Daily signal JSON files
│   ├── campaigns/              # Campaign state files
│   └── scan_history/           # Scan run logs
├── pyproject.toml              # Dependencies + packaging
├── .env.example                # Environment template
└── README.md                   # This file
```

---

## Prerequisites

### Accounts & Access
1. **Google Cloud** account with OAuth 2.0 credentials (Desktop app type)
2. **Google Sheets API** enabled in your Google Cloud project
3. **OpenAI API key** with access to GPT-4o-mini (or your chosen model)
4. **Google Sheet** where results will be written

### Detailed Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Navigate to **APIs & Services > Library** — search **Google Sheets API**, click **Enable**
4. Go to **APIs & Services > OAuth consent screen**
   - Choose **External**, click Create
   - Fill in app name and your email
   - On **Scopes**, add `https://www.googleapis.com/auth/spreadsheets`
   - On **Test users**, add your Google email
5. Go to **APIs & Services > Credentials**
6. Click **Create Credentials > OAuth client ID**
   - Application type: **Desktop app**
7. Copy the **Client ID** and **Client Secret** into your `.env`

### Getting Your Spreadsheet ID

Open your target Google Sheet. The URL looks like:
```
https://docs.google.com/spreadsheets/d/1HJy1bAfynXs.../edit
```
The long string after `/d/` is your Spreadsheet ID.

---

## CLI Reference

```bash
# Run Reddit scan (default: exports to Google Sheets)
python -m inkwell scan

# Use a different subreddit list
python -m inkwell scan --subreddits subreddits_1.yml

# Export to CSV instead of Sheets
python -m inkwell scan --csv --no-sheets

# Both CSV and Sheets
python -m inkwell scan --csv

# Verbose logging
python -m inkwell scan -v

# Start web dashboard
python -m inkwell serve

# Web dashboard on custom port with auto-reload
python -m inkwell serve --port 3000 --reload
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ERROR: Set OPENAI_API_KEY in .env` | Your `.env` file is missing or the key name is wrong |
| `ERROR: Set GOOGLE_CLIENT_ID...` | Google OAuth credentials not set in `.env` |
| `No subreddits found` | Check `config/subreddits.yml` exists and is valid YAML |
| Browser doesn't open for OAuth | Run on a machine with a browser, or check firewall |
| No rows in sheet | Check `SPREADSHEET_ID` in `.env` is correct |
| `token.json` auth error | Delete `token.json` and re-run to re-authenticate |
| Rate limited (429) | Handled automatically with backoff — just wait |
| All posts filtered out | Check `config/filters.yml` — filters may be too strict |

---

## Roadmap

- [x] **Phase 0** — Modular architecture (scanners, analyzers, filters, exporters, storage)
- [x] **Multi-provider LLM** — OpenAI, Claude, Ollama, anything LiteLLM supports
- [x] **BYOK analyzer split** — scans are free; voice drafting is on-demand, key-in-browser
- [x] **Web UI** — Profile builder, settings (output + BYOK + filters), scan runner with live SSE progress and draft modal
- [ ] **Persona marketplace** — fork/publish personas under `config/personas/`
- [ ] **More scanners** — Hacker News, Product Hunt, Dev.to (protocol-based, ~100 LOC each)
- [ ] **More exporters** — Notion, Airtable, Slack webhook
- [ ] **Scheduling** — APScheduler cron for daily sweeps; email/Slack digests
- [ ] **Feedback loop** — ratings feed back into the engagement score

See [README_TECHNICAL.md](README_TECHNICAL.md) for architecture details.

---

## Contributing

Inkwell is built as an open platform — scanners, exporters, and personas are all intentionally small surfaces so a contributor can ship a real feature in an afternoon.

**Three-minute path in:**

1. 👀 Browse **[open good-first-issues](https://github.com/sausi-7/inkwell/issues?q=is%3Aopen+label%3A%22good+first+issue%22)** — scanner / exporter / persona / docs. Each has clear acceptance criteria and files-to-touch.
2. 💬 Comment "I'd like this" — you'll get assigned.
3. 🛠️ Read [**CONTRIBUTING.md**](CONTRIBUTING.md) for dev setup, code style, and the step-by-step for new scanners & exporters. Read [**docs/ROADMAP.md**](docs/ROADMAP.md) for project direction.

Prefer a chat first? Open a **[discussion](https://github.com/sausi-7/inkwell/discussions)** — ideas, persona show-and-tell, or "help me set this up."

The repo's whole architecture is designed around **plain Python protocols** (structural typing, no inheritance), **one YAML per concept** (persona, filters, subreddits), and **plain HTML/CSS/JS** (no build step, no framework). Easy to read, easy to fork, easy to extend.

---

## License

[MIT](LICENSE) — do whatever you want with this, including commercial use and forks. Just keep the copyright line.

---

## Acknowledgments

Built by [Saurabh Singh](https://github.com/sausi-7). Originally started as a Reddit outreach script, now growing into a full outreach intelligence platform.

If Inkwell helps you find great conversations, consider starring the repo and sharing it with other entrepreneurs.
