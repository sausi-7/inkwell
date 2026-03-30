# OutreachPilot

**Open source AI outreach intelligence tool for entrepreneurs.**

Find real people with real problems you can actually help — across every platform where they talk about it.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## What It Does

OutreachPilot scans communities (Reddit, Hacker News, Product Hunt, and more) for posts where people are asking for help, sharing projects, or discussing problems you can solve. It uses AI to:

- **Summarize** each post in 1-2 sentences
- **Score engagement potential** (Yes / Maybe / No)
- **Identify the best comment** in each thread
- **Generate suggested replies** written in your voice and tone
- **Export everything** to Google Sheets, CSV, or a web dashboard

All suggestions are written using your configured personality profile — conversational, genuine, and non-promotional.

### Why OutreachPilot?

Most outreach tools start with a contact database and blast cold messages. OutreachPilot flips this: it starts with **real signals** — people publicly expressing problems — and helps you engage authentically where they already are. This signal-first approach gets 2-3x higher response rates than cold outreach.

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/sausi-7/reddit-outreach.git
cd reddit-outreach

python3 -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

pip install -e .
```

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

```bash
# Scan Reddit and export to Google Sheets
python -m outreachpilot scan

# Scan Reddit, export to CSV, skip Sheets
python -m outreachpilot scan --csv --no-sheets

# Start the web dashboard (Phase 1)
python -m outreachpilot serve
```

**First run:** A browser window will open for Google OAuth. Sign in and grant Sheets access. This only happens once.

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
    |  Pre-filter (zero AI cost)      |  Keywords, score, flairs, status
    +---------------------------------+
                    |
                    v
    +---------------------------------+
    |  AI analysis per signal         |  Summary, engagement score,
    |  (OpenAI / Claude / Ollama)     |  suggested replies in YOUR voice
    +---------------------------------+
                    |
                    v
    +---------------------------------+
    |  Export                          |  Google Sheets, CSV, web dashboard
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

Only posts marked **"Yes"** get populated suggestions. `Maybe` and `No` posts show dashes to reduce noise.

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
python -m outreachpilot scan --subreddits subreddits_1.yml
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

### LLM Model — `.env`

Change the AI model by setting in `.env`:

```
LLM_MODEL=gpt-4o-mini          # Default (cheap, fast)
LLM_MODEL=gpt-4o               # More capable
LLM_MODEL=claude-sonnet-4-6    # Anthropic Claude (via LiteLLM, Phase 1)
```

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
outreachpilot/
├── outreachpilot/              # Python package
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
python -m outreachpilot scan

# Use a different subreddit list
python -m outreachpilot scan --subreddits subreddits_1.yml

# Export to CSV instead of Sheets
python -m outreachpilot scan --csv --no-sheets

# Both CSV and Sheets
python -m outreachpilot scan --csv

# Verbose logging
python -m outreachpilot scan -v

# Start web dashboard
python -m outreachpilot serve

# Web dashboard on custom port with auto-reload
python -m outreachpilot serve --port 3000 --reload
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
- [ ] **Phase 1** — Web dashboard with FastAPI + HTMX, LiteLLM multi-provider support, scheduled scans
- [ ] **Phase 2** — Hacker News + Product Hunt scanners, campaign management, feedback loop
- [ ] **Phase 3** — Twitter/X + IndieHackers scanners, ML-based scoring, plugin system
- [ ] **Phase 4** — Landing page, pip-installable package, community launch

See [README_TECHNICAL.md](README_TECHNICAL.md) for architecture details.

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Quick ways to contribute:**
- Add a new platform scanner (Hacker News, Product Hunt, Dev.to)
- Add a new exporter (Notion, Airtable, Slack webhook)
- Improve AI prompts for better suggestions
- Build the web dashboard UI
- Write tests
- Report bugs or suggest features

---

## License

[AGPL-3.0](LICENSE) — Free to use, modify, and self-host. If you build a SaaS on top, you must open-source your modifications.

---

## Acknowledgments

Built by [Saurabh Singh](https://github.com/sausi-7). Originally started as a Reddit outreach script, now growing into a full outreach intelligence platform.

If OutreachPilot helps you find great conversations, consider starring the repo and sharing it with other entrepreneurs.
