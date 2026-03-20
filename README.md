# Reddit Outreach Sweep: Daily Engagement Scanner

Automatically scans subreddits for recent posts, uses AI to generate summaries and suggested comments, and writes everything to a Google Sheet — one new tab per day, hands-free.

---

## What It Does

This script scans your configured subreddits for posts from the **last 24 hours**, analyzes each post and its comments with OpenAI (GPT-4o-mini), and writes engagement-ready insights to a Google Sheet with the following columns:

| Column | Description |
|---|---|
| Subreddit | e.g. `r/edtech` |
| Post title | Title of the Reddit post |
| Summary | AI-generated 1-2 sentence summary |
| Age (hrs) | Hours since the post was created |
| Created UTC | Post creation timestamp |
| Engage? | `Yes`, `No`, or `Maybe` |
| Why | 1-sentence reasoning for the engagement recommendation |
| Status | `active`, `archived`, `inactive`, or `blocked` |
| Coolest comment | The most interesting/insightful comment on the post |
| Suggested reply to cool comment | A conversational, non-marketing reply to that comment |
| Suggested post comment | A useful comment for the post itself |
| Post link | Direct URL to the post |
| Source URL(s) | Reddit API endpoints used |

Suggestions (coolest comment, replies, post comment, why) are only populated for posts marked **"Yes"** — `Maybe` and `No` posts show dashes to reduce noise.

All suggested comments are written in your configured voice (see `personality.yml`) and designed to be **genuine, helpful, and non-promotional**.

---

## What You Need Before Starting

### Accounts & Access
1. A **Google account** with access to Google Cloud Console
2. **OAuth 2.0 credentials** for Google Sheets (Desktop app type)
3. An **OpenAI API key** with access to GPT-4o-mini
4. A **Google Sheet** where results will be written

### Software
- Python 3.8 or newer
- pip (Python package manager)

---

## Step-by-Step Setup

### Step 1 — Set Up Google Sheets OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Go to **APIs & Services → Library**
4. Search for **"Google Sheets API"** and click **Enable**
5. Go to **APIs & Services → OAuth consent screen**
   - Choose **External**, click Create
   - Fill in App name (anything), your email, and save
   - On the **Scopes** step, add `https://www.googleapis.com/auth/spreadsheets`
   - On the **Test users** step, add your own Google email
6. Go to **APIs & Services → Credentials**
7. Click **Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Name it anything
8. Copy the **Client ID** and **Client Secret**

---

### Step 2 — Get an OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com/)
2. Navigate to **API Keys** and create a new key
3. Copy the key — this is your `OPENAI_API_KEY`

---

### Step 3 — Get Your Spreadsheet ID

1. Open the Google Sheet where you want results saved
2. The URL looks like:
   `https://docs.google.com/spreadsheets/d/`**`1HJy1bAfynXs...`**`/edit`
3. Copy the long ID after `/d/` — that's your **Spreadsheet ID**

The script creates a new tab for each day automatically (named `YYYY-MM-DD`).

---

### Step 4 — Configure Your Environment

1. Copy the example env file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in your values:
   ```
   GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_client_secret
   OPENAI_API_KEY=sk-your_openai_key
   SPREADSHEET_ID=your_spreadsheet_id
   ```

---

### Step 5 — Configure Subreddits

Edit `subreddits.yml` to add or remove subreddits. It's a simple list:

```yaml
- edtech
- Entrepreneur
- SaaS
- learnprogramming
```

No code changes needed — just edit the YAML file and re-run.

---

### Step 6 — Configure Your Personality

Edit `personality.yml` to define the voice and tone of AI-generated comments. This file controls:

- **Who you are** — name, bio, interests, expertise
- **How you sound** — tone style, humor, formality
- **What to do / avoid** — guidelines for comment generation
- **Example comments** — 2-4 real examples of how you'd actually comment on Reddit

The AI uses this profile to write comments that sound like you, not a generic bot. If the file is missing, a default conversational tone is used.

---

### Step 7 — Configure Filters (Optional)

Edit `filters.yml` to control which posts get analyzed. Filters are applied **before** sending posts to OpenAI, saving API costs:

| Filter | What it does |
|---|---|
| `keywords.include` | Post must contain at least one keyword (empty = no filter) |
| `keywords.exclude` | Post is skipped if it contains any of these |
| `thresholds.min_score` | Minimum upvote score (default: 2) |
| `thresholds.max_comments` | Skip mega-threads (default: 500) |
| `thresholds.max_age_hours` | How old a post can be (default: 24) |
| `post_type.allow` | `all`, `self_only`, or `link_only` |
| `flairs.include / exclude` | Filter by post flair |
| `allowed_statuses` | Which statuses to keep (default: `active` only) |
| `ai_preferences` | Guides OpenAI's Yes/Maybe/No decision (doesn't filter posts) |

---

### Step 8 — Install Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

---

### Step 9 — Run the Script

```bash
python reddit_outreach.py
```

**First run only:** A browser window will open asking you to sign in with Google and grant access to your spreadsheet. Click Allow. This only happens once — the token is saved for future runs.

---

## How It Runs

```
Reddit Outreach Sweep – 2026-03-20
Scanning 101 subreddits for posts from the last 24h

Authenticating with Google Sheets...
Created new tab '2026-03-20'
Progress: 0/101 subreddits done, 0 rows written

[1/101] r/content_marketing
  Found 12 posts
  Appended 12 rows to Google Sheet
[2/101] r/coursecreators
  No posts in last 24h
  Appended 1 rows to Google Sheet
  ...
```

The script:
- Fetches up to 100 posts per subreddit from the `/new` feed
- Filters out posts older than 24 hours
- Applies rule-based pre-filters (keywords, score, flairs, etc.)
- For each post, fetches the top 10 comments by score
- Analyzes each post + comments with OpenAI using your personality profile
- Writes results per subreddit in batches
- Saves a progress checkpoint after each subreddit

---

## Stopping and Resuming

You can stop the script at any time with `Ctrl+C`. Progress is saved automatically.

When you run it again on the same day, it will:
- Skip all subreddits already completed
- Skip all posts already analyzed
- Continue exactly where it left off

Progress resets automatically each new day.

---

## Project Files

| File | Purpose |
|---|---|
| `reddit_outreach.py` | Main script — fetches, analyzes, writes to sheet |
| `subreddits.yml` | List of subreddits to scan (edit freely) |
| `personality.yml` | Your voice/tone profile for AI-generated comments |
| `filters.yml` | Rule-based filtering and AI engagement preferences |
| `.env` | Your API keys and credentials (keep this private) |
| `.env.example` | Template for `.env` |
| `requirements.txt` | Python dependencies |
| `progress.json` | Checkpoint: completed subreddits, processed post IDs, row count (auto-generated) |
| `fallback_rows.json` | Only created if a sheet write fails — contains unsaved rows for manual recovery |

> Never commit `.env` or `token.json` to version control.

---

## Common Issues

| Problem | Fix |
|---|---|
| `ERROR: Set OPENAI_API_KEY in .env` | Your `.env` file is missing or the key name is wrong |
| `ERROR: Set GOOGLE_CLIENT_ID...` | Google OAuth credentials not set in `.env` |
| `No subreddits found in subreddits.yml` | The YAML file is empty or malformed |
| Browser doesn't open for OAuth | Run on a machine with a browser, or check firewall settings |
| No rows appearing in sheet | Check that `SPREADSHEET_ID` is correct in `.env` |
| `token.json` auth error | Delete `token.json` and re-run to re-authenticate |
| Rate limited (429) | The script handles this automatically with backoff — just wait |
| All posts filtered out | Check `filters.yml` — your keyword/score/flair filters may be too strict |
