# Technical README — Reddit Outreach Sweep

This document covers the architecture, design decisions, and a full build-from-scratch guide for the `reddit_outreach.py` script.

---

## Architecture Overview

```
.env
 └── OAuth credentials + OpenAI key + Spreadsheet ID

subreddits.yml          personality.yml          filters.yml
 └── Subreddit list      └── Voice/tone config    └── Pre-filters + AI prefs
       │                        │                        │
       ▼                        ▼                        ▼
Reddit JSON API         ┌──────────────────────────────────┐
 (/new feed)            │       OpenAI Analysis            │
       │                │  (personality + prefs injected    │
       ▼                │   into prompt)                   │
 Fetch posts (last 24h) │                                  │
       │                └──────────────────────────────────┘
       ▼                        │
 Apply pre-filters              │
 (keywords, score,              │
  flairs, status)               │
       │                        │
       ▼                        │
 Fetch comments (top 10)        │
       │                        │
       ▼                        ▼
 OpenAI Analysis (gpt-4o-mini)
 (summary, cool comment, replies, engage?)
       │
       ▼
 Build row dicts (13 columns)
       │
       ▼
 Append to Google Sheet (batch per subreddit)
       │
       ▼
 Checkpoint (progress.json)
```

---

## Key Components

### 1. Configuration Loading

Three YAML files are loaded at startup:

| File | Loader | Purpose |
|---|---|---|
| `subreddits.yml` | `load_subreddits()` | Simple list of subreddit names (no `r/` prefix) |
| `personality.yml` | `load_personality()` | Voice/tone profile for AI-generated comments |
| `filters.yml` | `load_filters()` | Pre-filtering rules and AI engagement preferences |

All paths are resolved relative to the script directory (`SCRIPT_DIR`), so the script works regardless of working directory. `personality.yml` and `filters.yml` are optional — the script warns and continues with defaults if missing.

---

### 2. Pre-Filtering — `apply_pre_filters()`

Rule-based filtering applied **before** sending posts to OpenAI. This saves API costs by skipping irrelevant posts early.

Filters applied in order:
1. **Status** — only `active` by default (configurable via `allowed_statuses`)
2. **Score** — minimum upvote threshold (`min_score`, default: 2)
3. **Comment count** — `min_comments` / `max_comments` (skip mega-threads)
4. **Post type** — `all`, `self_only`, or `link_only`
5. **Keywords** — title + body searched case-insensitively; `include` (must match one) and `exclude` (must match none)
6. **Flairs** — inclusion/exclusion lists

Posts that survive all filters are sent to OpenAI for analysis.

---

### 3. Reddit Fetching — `fetch_json()`, `fetch_subreddit_posts()`, `fetch_post_comments()`

The script uses Reddit's **public JSON API** (no authentication needed). Each endpoint is accessed by appending `.json` to the standard Reddit URL.

**Rate limiting:**
- 2-second sleep (`REDDIT_SLEEP`) between all Reddit requests
- Exponential backoff on HTTP 429 (rate limited): waits 5s, 10s, 15s
- 403 Forbidden returns `None` (subreddit may be private/quarantined)
- Network errors retry up to 3 times with 3s delay

**Post fetching** (`fetch_subreddit_posts`):
```
GET https://www.reddit.com/r/{subreddit}/new.json?limit=100
```
- Filters posts older than `MAX_POST_AGE_HOURS` (configurable in `filters.yml`, default 24h)
- Determines post status: `active`, `blocked` (removed), `archived`, `inactive` (locked)
- Truncates post body to 2000 characters

**Comment fetching** (`fetch_post_comments`):
```
GET https://www.reddit.com/r/{subreddit}/comments/{id}/.json?limit=25
```
- Extracts top-level comments only (`kind == "t1"`)
- Skips `[deleted]` and `[removed]` comments
- Sorts by score descending, returns top 10
- Truncates comment body to 500 characters

---

### 4. Personality & AI Preferences — `_build_personality_block()`, `_build_ai_prefs_block()`

Two helper functions inject user configuration into the OpenAI prompt:

**`_build_personality_block()`** reads `personality.yml` and constructs a persona block:
- Name, bio, interests, expertise
- Tone (style, humor, formality)
- DO/DON'T guidelines
- Example comments for voice matching

If no personality file exists, falls back to a generic "conversational, fun, non-marketing-y" instruction.

**`_build_ai_prefs_block()`** reads `filters.yml`'s `ai_preferences` section:
- `prefer_topics` — types of posts to favor for engagement
- `avoid_topics` — types of posts to deprioritize
- `engagement_notes` — freeform guidance for the AI

These preferences influence the `engage` (Yes/Maybe/No) decision but don't filter posts.

---

### 5. OpenAI Analysis — `analyze_post()`

Each post is analyzed by GPT-4o-mini with a single prompt that includes:
- The personality block
- Subreddit name, post title, post body
- Post score and comment count
- Top 10 comments with scores and authors
- AI engagement preferences

The model returns a JSON object with 6 keys:

| Key | Description |
|---|---|
| `summary` | 1-2 sentence summary of the post |
| `coolest_comment` | Most interesting comment (verbatim) |
| `suggested_reply` | Reply to the cool comment (in user's voice) |
| `suggested_post_comment` | Standalone comment for the post (in user's voice) |
| `engage` | `Yes`, `No`, or `Maybe` |
| `why` | 1-sentence reasoning |

**Selective output:** Only posts with `engage: "Yes"` get their suggestions, cool comment, and reasoning populated in the sheet. `Maybe` and `No` posts show dashes to reduce noise.

**Retry logic:**
- 3 attempts with 2s delay between retries
- Strips markdown code fences (`` ```json ... ``` ``) before parsing
- On final failure, returns a safe fallback dict with `engage: "No"`

**Model config:** `temperature=0.7`, `max_tokens=1024`

---

### 6. Google Sheets OAuth — `get_sheets_service()`

```python
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
```

Flow:
1. If `token.json` exists → load credentials
2. If expired but has refresh token → auto-refresh via `Request()`
3. Otherwise → open browser for `InstalledAppFlow.run_local_server(port=0)`
4. Save new token to `token.json`

Credentials are constructed from `OAUTH_CLIENT_CONFIG` (a dict built from `.env` values) rather than a file, so no `credentials.json` file is needed on disk.

**Token location:** The OAuth token is stored at `../youtube-creators/token.json` (shared with the youtube-creators project).

---

### 7. Daily Tab Management — `get_or_create_daily_tab()`

Each day gets its own tab named `YYYY-MM-DD`. On startup:

1. Fetches spreadsheet metadata via `spreadsheets().get()`
2. If tab exists → resume (no header rewrite)
3. If tab doesn't exist → create via `batchUpdate`, then write:
   - Row 1: Header row (13 column names)
   - Rows 2-4: Info banner describing the sweep + blank separator

This means multiple runs on the same day append to the same tab.

---

### 8. Row Appending — `append_rows_to_sheet()`

Rows are written in batches (one batch per completed subreddit):

```python
sheets.spreadsheets().values().append(
    spreadsheetId=SPREADSHEET_ID,
    range="'{tab}'!A:M",
    valueInputOption="RAW",
    insertDataOption="INSERT_ROWS",
    body={"values": [[row[col] for col in COLUMNS]]}
)
```

If a sheet write fails during the `finally` block, rows are saved to `fallback_rows.json` for manual recovery.

---

### 9. Checkpoint / Resume System

After each subreddit completes, `save_progress()` writes `progress.json`:

```json
{
  "date": "2026-03-20",
  "completed_subreddits": ["edtech", "SaaS", ...],
  "processed_post_ids": ["abc123", "def456", ...],
  "total_written": 420
}
```

On startup, `load_progress()` restores this state **only if the date matches today**. Otherwise it starts fresh.

Two levels of dedup:
1. **Subreddit level** — completed subreddits are skipped entirely
2. **Post level** — individual post IDs are tracked, so partially-completed subreddits resume correctly

---

## Building This From Scratch

### Dependencies

```
google-api-python-client   # Google Sheets API client
google-auth-oauthlib        # OAuth 2.0 flow for Sheets
google-auth-httplib2        # HTTP transport for google-auth
python-dotenv               # .env file loading
httplib2                    # HTTP client (used by googleapiclient)
openai                      # OpenAI API client
requests                    # HTTP requests for Reddit API
pyyaml                      # YAML parsing for config files
```

Install:
```bash
pip install -r requirements.txt
```

---

### Google Cloud Setup

**Google Sheets API + OAuth**
- Enable: APIs & Services → Library → "Google Sheets API"
- OAuth consent screen: External, add scope `https://www.googleapis.com/auth/spreadsheets`
- Credentials: OAuth client ID → Desktop app
- You need only the **Client ID** and **Client Secret** (not the downloaded JSON file)

---

### Project Structure

```
reddit-outreach/
├── reddit_outreach.py       # main script (single file)
├── subreddits.yml           # subreddit list (edit freely)
├── personality.yml          # voice/tone profile for AI comments
├── filters.yml              # pre-filters and AI engagement prefs
├── requirements.txt         # Python dependencies
├── .env                     # secrets (never commit)
├── .env.example             # template for .env
├── progress.json            # checkpoint (auto-generated)
├── fallback_rows.json       # backup rows on write failure (auto-generated)
├── README.md                # user guide
└── README_TECHNICAL.md      # this file
```

---

### Configuration Constants

Environment variables loaded from `.env`:
```
GOOGLE_CLIENT_ID       # OAuth client ID
GOOGLE_CLIENT_SECRET   # OAuth client secret
OPENAI_API_KEY         # OpenAI API key
SPREADSHEET_ID         # Target Google Sheet ID
```

Script-level constants:
```python
REDDIT_SLEEP       = 2              # seconds between Reddit API calls
OPENAI_MODEL       = "gpt-4o-mini"  # model for analysis
```

Configurable via `filters.yml`:
```yaml
thresholds:
  max_age_hours: 24   # MAX_POST_AGE_HOURS — how far back to scan
  min_score: 2        # minimum upvote score
  max_comments: 500   # skip mega-threads
```

---

### Reddit API — Request Patterns

**Fetch new posts:**
```
GET https://www.reddit.com/r/{subreddit}/new.json?limit=100
```
Returns: `data.children[].data` — each child has `id`, `title`, `selftext`, `permalink`, `score`, `num_comments`, `created_utc`, `archived`, `locked`, `removed_by_category`

**Fetch post comments:**
```
GET https://www.reddit.com/r/{subreddit}/comments/{post_id}/.json?limit=25
```
Returns: Array of 2 listings — `[0]` is the post, `[1].data.children[]` are comments with `kind`, `data.author`, `data.body`, `data.score`

---

### Sheets API — Key Patterns

**Get spreadsheet metadata:**
```python
sheets.spreadsheets().get(spreadsheetId=ID).execute()
```

**Create a new tab:**
```python
sheets.spreadsheets().batchUpdate(
    spreadsheetId=ID,
    body={"requests": [{"addSheet": {"properties": {"title": "2026-03-20"}}}]}
)
```

**Write to a range (headers):**
```python
sheets.spreadsheets().values().update(
    spreadsheetId=ID,
    range="'2026-03-20'!A1:M1",
    valueInputOption="RAW",
    body={"values": [COLUMNS]}
)
```

**Append rows:**
```python
sheets.spreadsheets().values().append(
    spreadsheetId=ID,
    range="'2026-03-20'!A:M",
    valueInputOption="RAW",
    insertDataOption="INSERT_ROWS",
    body={"values": [[col1, col2, ...]]}
)
```

---

### Extending the Script

**Change the post age window:**
Edit `filters.yml`:
```yaml
thresholds:
  max_age_hours: 48  # scan last 48 hours instead of 24
```

**Change the OpenAI model:**
```python
OPENAI_MODEL = "gpt-4o"  # use a more capable model
```

**Add/remove subreddits:**
Edit `subreddits.yml` — no code changes needed.

**Customize comment voice:**
Edit `personality.yml` — change bio, tone, guidelines, and example comments.

**Adjust filtering:**
Edit `filters.yml` — add keywords, change score thresholds, filter by flair.

**Add a new output column:**
1. Add the column name to `COLUMNS`
2. Populate it in the row dict (in the main loop or `analyze_post`)
3. The sheet range auto-adjusts via `chr(64 + len(COLUMNS))`

**Change the analysis prompt:**
Edit the `prompt` string in `analyze_post()`. The expected JSON keys should match what the main loop reads via `analysis.get(...)`.

---

## Error Handling Summary

| Error | Handling |
|---|---|
| Reddit 429 (rate limited) | Exponential backoff: 5s, 10s, 15s |
| Reddit 403 (forbidden) | Skip subreddit, return `None` |
| Network timeout / error | Retry up to 3 times with 3s delay |
| OpenAI parse error | Retry up to 3 times; fallback dict on final failure |
| Sheet write failure | Save rows to `fallback_rows.json` |
| `KeyboardInterrupt` | Flush pending rows, save progress, exit gracefully |
| Missing `personality.yml` | Warning printed, uses default tone |
| Missing `filters.yml` | Warning printed, no filters applied |

---

## Data Flow Per Subreddit

```
1. Skip if already in completed_subs (checkpoint)
2. Fetch /new.json → filter by max_age_hours
3. Apply pre-filters (keywords, score, flairs, status, post type)
4. If no posts survive → write "no recent post found" marker row
5. For each post (skip if post ID already processed):
   a. Fetch comments → top 10 by score
   b. Send to OpenAI (with personality + AI prefs) → get analysis JSON
   c. Build row dict with all 13 columns
   d. Only populate suggestions/reasoning for engage="Yes"
   e. Add post ID to processed_ids
6. Append all rows for this subreddit to sheet
7. Mark subreddit as completed
8. Save checkpoint
```
