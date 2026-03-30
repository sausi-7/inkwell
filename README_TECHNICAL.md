# Technical Documentation — OutreachPilot

Architecture, design decisions, data flows, and extension guide for OutreachPilot.

---

## Architecture Overview

```
.env                         config/
 └── API keys + secrets       ├── personality.yml    (voice profile)
                              ├── filters.yml        (pre-filter rules + AI prefs)
                              └── subreddits.yml     (scan targets)
                                     │
                    ┌────────────────┘
                    ▼
             ┌─────────────┐
             │  config.py   │   Loads .env + YAML, exposes settings
             └──────┬──────┘
                    │
        ┌───────────┼───────────┬───────────────┐
        ▼           ▼           ▼               ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
  │ scanners │ │ filters  │ │analyzers │ │  exporters   │
  │          │ │          │ │          │ │              │
  │ reddit   │ │ rule     │ │ pipeline │ │ google_sheets│
  │ (HN)     │ │ dedup    │ │ llm      │ │ csv          │
  │ (PH)     │ │          │ │          │ │ (webhook)    │
  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘
       │             │            │               │
       └─────────────┴────────────┴───────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              ┌──────────┐       ┌──────────┐
              │ storage  │       │ personas │
              │          │       │          │
              │ signals  │       │ loader   │
              │ progress │       │ prompt   │
              │ campaigns│       │ builder  │
              │ feedback │       └──────────┘
              │ history  │
              └──────────┘
                    │
                    ▼
              data/ (JSON files on disk)
```

---

## Module Reference

### `config.py` — Configuration Hub

Loads all settings from `.env` and YAML files. Every other module imports from here.

**Key exports:**
- `ROOT_DIR`, `CONFIG_DIR`, `DATA_DIR` — path constants
- `OPENAI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SPREADSHEET_ID` — secrets
- `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS` — AI settings
- `REDDIT_HEADERS`, `REDDIT_SLEEP` — Reddit API settings
- `COLUMNS` — Google Sheets column definitions
- `load_subreddits()`, `load_personality()`, `load_filters()` — YAML loaders
- `ensure_data_dirs()` — creates data/ subdirectories

**Backward compatibility:** If a YAML file isn't found in `config/`, the loader falls back to the project root directory. This means the old file layout still works.

---

### `scanners/` — Platform Scanners

#### Scanner Protocol

Every scanner implements this interface:

```python
class Scanner(Protocol):
    name: str
    def scan(self, targets: list[str], max_age_hours: int = 24) -> list[RawSignal]: ...
```

#### Data Models

```python
@dataclass
class RawSignal:
    platform: str           # "reddit", "hackernews", etc.
    platform_id: str        # Unique ID on the platform
    url: str                # Direct link to the post
    title: str
    body: str               # Truncated to 2000 chars
    author: str
    score: int
    reply_count: int
    created_utc: float      # Unix timestamp
    metadata: dict           # Platform-specific (subreddit, flair, etc.)
    replies: list[Reply]    # Top comments/replies
    status: str             # "active", "archived", "inactive", "blocked"

@dataclass
class Reply:
    author: str
    body: str               # Truncated to 500 chars
    score: int
    platform_id: str
```

#### `reddit.py` — Reddit Scanner

Uses Reddit's public JSON API (no authentication required).

**Endpoints:**
```
GET https://www.reddit.com/r/{subreddit}/new.json?limit=100    # Fetch posts
GET https://www.reddit.com/r/{subreddit}/comments/{id}/.json?limit=25  # Fetch comments
```

**Rate limiting:**
- 2-second sleep between requests (`REDDIT_SLEEP`)
- Exponential backoff on 429: waits 5s, 10s, 15s
- 403 Forbidden: returns `None` (private/quarantined subreddit)
- Network errors: retry up to 3 times with 3s delay

**Post status detection:**
- `removed_by_category` set → `blocked`
- `archived` → `archived`
- `locked` → `inactive`
- Otherwise → `active`

**Comment processing:**
- Extracts top-level comments only (`kind == "t1"`)
- Skips `[deleted]` and `[removed]`
- Sorts by score descending, returns top 10
- Body truncated to 500 characters

#### `registry.py` — Scanner Registry

Auto-discovers scanners on first access. Scanners self-register on import:

```python
# In reddit.py
registry.register(RedditScanner())

# To use:
from outreachpilot.scanners import get_scanner
scanner = get_scanner("reddit")
signals = scanner.scan(["Entrepreneur", "SaaS"], max_age_hours=24)
```

#### Adding a New Scanner

1. Create `scanners/hackernews.py`
2. Implement the `Scanner` protocol
3. Call `registry.register(HackerNewsScanner())` at module level
4. Import in `registry.py`'s `_ensure_loaded()`

```python
# scanners/hackernews.py
class HackerNewsScanner:
    name = "hackernews"

    def scan(self, targets: list[str], max_age_hours: int = 24) -> list[RawSignal]:
        # Use Algolia HN API: hn.algolia.com/api/v1/search_by_date
        ...

registry.register(HackerNewsScanner())
```

---

### `analyzers/` — AI Analysis Engine

#### `pipeline.py` — Main Analysis Function

```python
def analyze_signal(signal: RawSignal, personality: dict, filters: dict) -> Analysis
```

Builds a prompt from:
1. **Personality block** — who you are and how you write (from `personas/prompt_builder.py`)
2. **Signal context** — subreddit, title, body, score, comment count
3. **Top comments** — up to 10, with scores and authors
4. **AI preferences** — engagement criteria from `filters.yml`

Calls the LLM and parses the JSON response into an `Analysis` dataclass.

#### `base.py` — Analysis Data Model

```python
@dataclass
class Analysis:
    summary: str                # 1-2 sentence post summary
    coolest_comment: str        # Best comment (verbatim)
    suggested_reply: str        # Reply to that comment
    suggested_post_comment: str # Standalone comment for the post
    engage: str                 # "Yes", "No", or "Maybe"
    why: str                    # 1-sentence reasoning
    model_used: str
    tokens_used: int
```

Only `engage: "Yes"` posts get their suggestions populated in exports. `Maybe` and `No` show dashes.

#### `llm_client.py` — LLM Wrapper

Currently uses the OpenAI SDK directly. Configurable via `.env`:

```
LLM_MODEL=gpt-4o-mini      # Model name
LLM_TEMPERATURE=0.7         # Creativity (0.0 = deterministic, 1.0 = creative)
LLM_MAX_TOKENS=1024         # Max response length
```

**Retry logic:** 3 attempts with 2s delay. Strips markdown code fences before JSON parsing. Returns `None` on final failure (caller uses `Analysis.error_fallback()`).

---

### `filters/` — Signal Filtering

#### `rule_filter.py` — Pre-AI Filtering

Runs **before** AI analysis to save API costs. Filters applied in order:

1. **Status** — only `active` by default
2. **Score** — minimum upvote threshold
3. **Comment count** — min/max bounds
4. **Post type** — all, self-only, or link-only
5. **Keywords** — include (must match one) and exclude (must match none), case-insensitive
6. **Flairs** — include/exclude lists

#### `dedup.py` — Cross-Day Deduplication

Loads signal IDs from the last N days' JSON files and removes duplicates. Prevents the same trending post from appearing in multiple daily sweeps.

```python
deduped = deduplicate_signals(signals, lookback_days=3)
```

---

### `personas/` — Voice/Tone Engine

#### `prompt_builder.py`

Two functions build prompt blocks injected into the AI prompt:

**`build_personality_block(personality)`** — Constructs persona instructions from `personality.yml`:
- Name, bio, interests, expertise
- Tone (style, humor, formality)
- DO/DON'T guidelines
- Example comments for voice matching

**`build_ai_prefs_block(filters)`** — Constructs engagement criteria from `filters.yml`'s `ai_preferences`:
- `prefer_topics` — post types to favor
- `avoid_topics` — post types to deprioritize
- `engagement_notes` — freeform guidance

---

### `exporters/` — Output Adapters

#### Exporter Protocol

```python
class Exporter(Protocol):
    name: str
    def export(self, rows: list[dict], config: dict | None = None) -> None: ...
```

#### `google_sheets.py` — Google Sheets Exporter

**OAuth flow:**
1. Check `token.json` → load credentials
2. If expired but has refresh token → auto-refresh
3. Otherwise → open browser for OAuth consent
4. Save token for future runs

**Daily tab management:**
- Each day gets a tab named `YYYY-MM-DD`
- If tab exists → resume (no header rewrite)
- If new → create tab, write 13-column header row + info banner

**Row appending:**
- Writes in batches (one per completed subreddit)
- Uses `INSERT_ROWS` to append after existing data
- On failure → saves to `fallback_rows.json`

#### `csv_exporter.py` — CSV Export

Writes signals to `data/outreach_YYYY-MM-DD.csv` with the same 13 columns.

#### Adding a New Exporter

```python
# exporters/webhook.py
class WebhookExporter:
    name = "webhook"

    def export(self, rows: list[dict], config: dict | None = None) -> None:
        url = config.get("webhook_url")
        requests.post(url, json={"signals": rows})
```

---

### `storage/` — Local File Storage

All data stored as JSON files on disk. No database required.

#### Directory Layout

```
data/
├── signals/
│   ├── 2026-03-30.json     # All signals discovered today
│   └── 2026-03-29.json
├── campaigns/
│   ├── launch-week.json    # Campaign with signal refs
│   └── customer-disc.json
├── feedback/
│   └── ratings.json        # User quality ratings
├── scan_history/
│   └── 2026-03-30.json     # Today's scan runs
└── progress.json           # Checkpoint for resume
```

#### `signals.py` — Signal CRUD

```python
save_signals(signals, date_str)       # Merge new signals into daily file
load_signals(date_str)                 # Load signals for a date
load_recent_signal_ids(lookback_days)  # IDs from last N days (for dedup)
list_signal_dates()                    # All available dates
```

Signals are deduplicated by `id` on save — re-running a scan won't create duplicates.

#### `progress.py` — Checkpoint/Resume

```json
{
  "date": "2026-03-30",
  "completed_subreddits": ["Entrepreneur", "SaaS"],
  "processed_post_ids": ["abc123", "def456"],
  "total_written": 42
}
```

- Saved after each subreddit completes
- Resets automatically on a new day
- Two-level dedup: subreddit-level + post-level

#### `campaigns.py` — Campaign Management

Campaigns group signals and track engagement state:

```python
save_campaign("launch-week", {"name": "Launch Week", "signals": [...], "status": "active"})
load_campaign("launch-week")
list_campaigns()
delete_campaign("launch-week")
```

#### `feedback.py` — Quality Ratings

Track signal quality for future ML training:

```python
add_feedback(signal_id="reddit_abc123", rating=5, outcome="converted")
get_feedback_for_signal("reddit_abc123")
```

---

## Data Flow — Full Scan Cycle

```
1. CLI: python -m outreachpilot scan
2. Load config: subreddits.yml, personality.yml, filters.yml
3. Load progress checkpoint (skip completed subreddits)
4. For each subreddit:
   a. scanner.scan([subreddit]) → list[RawSignal]
      ├── Fetch /r/{sub}/new.json → parse posts
      └── For each post: fetch comments → top 10 by score
   b. apply_pre_filters(signals, filters) → filtered signals
   c. For each signal (skip if already processed):
      ├── analyze_signal(signal, personality, filters) → Analysis
      │   ├── build_personality_block() → persona prompt
      │   ├── build_ai_prefs_block() → engagement criteria
      │   └── chat_completion(prompt) → parse JSON → Analysis
      └── Build export row dict (13 columns)
   d. sheets_exporter.append_rows(tab, rows)
   e. save_signals(signal_dicts) → data/signals/today.json
   f. Mark subreddit complete, save progress
5. Done: log total rows written + sheet URL
```

---

## Error Handling

| Error | Handling |
|-------|---------|
| Reddit 429 (rate limited) | Exponential backoff: 5s, 10s, 15s |
| Reddit 403 (forbidden) | Skip subreddit, return `None` |
| Network timeout/error | Retry up to 3 times with 3s delay |
| LLM JSON parse error | Retry 3 times; `Analysis.error_fallback()` on final failure |
| Sheet write failure | Save to `fallback_rows.json` |
| `KeyboardInterrupt` | Flush pending rows, save progress, exit cleanly |
| Missing `personality.yml` | Warning logged, uses default conversational tone |
| Missing `filters.yml` | Warning logged, no filters applied |

---

## Configuration Reference

### Environment Variables (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | Yes (for Sheets) | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes (for Sheets) | — | Google OAuth client secret |
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `SPREADSHEET_ID` | Yes (for Sheets) | — | Target Google Sheet ID |
| `LLM_MODEL` | No | `gpt-4o-mini` | LLM model name |
| `LLM_TEMPERATURE` | No | `0.7` | LLM temperature |
| `LLM_MAX_TOKENS` | No | `1024` | LLM max response tokens |

### YAML Configuration Files

All in `config/` directory (falls back to project root for backward compatibility).

**`subreddits.yml`** — List of subreddit names (no `r/` prefix)
**`personality.yml`** — Voice profile with keys: `name`, `bio`, `interests`, `expertise`, `tone`, `dos`, `donts`, `example_comments`
**`filters.yml`** — Pre-filter rules with keys: `keywords`, `thresholds`, `post_type`, `flairs`, `allowed_statuses`, `ai_preferences`

---

## Extending OutreachPilot

### Add a New Platform Scanner

1. Create `outreachpilot/scanners/your_platform.py`
2. Create a class with `name` attribute and `scan()` method
3. Return `list[RawSignal]` with platform-specific metadata in `metadata` dict
4. Call `registry.register(YourScanner())` at module level
5. Add import in `registry.py`'s `_ensure_loaded()`

### Add a New Exporter

1. Create `outreachpilot/exporters/your_exporter.py`
2. Implement the `Exporter` protocol with `name` and `export()` method
3. Add CLI flag in `__main__.py` if needed

### Add a New Filter

1. Create `outreachpilot/filters/your_filter.py`
2. Accept `list[RawSignal]` and return filtered `list[RawSignal]`
3. Call from the scan loop in `__main__.py`

### Customize AI Prompts

Edit `outreachpilot/analyzers/pipeline.py` — the prompt template is in `analyze_signal()`. The expected JSON keys must match what the export row builder reads.

### Add a New Output Column

1. Add column name to `COLUMNS` in `config.py`
2. Populate it in the row dict in `__main__.py`'s scan loop
3. Sheet column range auto-adjusts via `chr(64 + len(COLUMNS))`

---

## Design Decisions

### Why JSON Files Instead of a Database

- Zero setup — no PostgreSQL, no migrations, no connection strings
- Human-readable — open `data/signals/2026-03-30.json` in any editor
- Portable — copy the `data/` folder to back up everything
- Sufficient — a single-user tool processing hundreds of signals/day doesn't need SQL
- Extensible — if scale is needed, a database storage backend can be added as a plugin

### Why FastAPI + Jinja2 + HTMX (Phase 1)

- No Node.js, no npm, no webpack — one language (Python) for everything
- HTMX provides dynamic updates without writing JavaScript
- Tailwind CSS (pre-built) for professional styling without a build step
- FastAPI auto-generates OpenAPI docs for the JSON API

### Why Protocol-Based Architecture

Scanners, exporters, and filters use Python protocols (structural typing). This means:
- No base class inheritance required
- Any class with the right methods works
- Easy to add plugins without modifying core code
- Clear contracts documented as type hints

### Why AGPL-3.0

- Maximizes freedom for individual users and self-hosters
- Requires companies building commercial SaaS to contribute back
- Proven model used by GitLab, Mattermost, and Grafana
- Creates a natural dual-licensing revenue path if needed
