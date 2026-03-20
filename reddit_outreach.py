"""
Reddit Outreach Sweep – Daily Scheduler

Scans 21 subreddits for posts from the last 24 hours, uses OpenAI to
generate summaries / suggested comments / engagement recommendations,
and writes everything to a Google Sheet (new tab per day).

Usage:
  1. Copy .env.example to .env and fill in your keys
  2. source ../venv/bin/activate   (or your virtualenv)
  3. python reddit_outreach.py
"""

import os
import sys
import json
import time
import datetime

import yaml
import requests as http_requests
from openai import OpenAI
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ── Load .env ────────────────────────────────────────────────────────────────
load_dotenv()

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    sys.exit("ERROR: Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
if not OPENAI_API_KEY:
    sys.exit("ERROR: Set OPENAI_API_KEY in .env")
if not SPREADSHEET_ID:
    sys.exit("ERROR: Set SPREADSHEET_ID in .env")

# ── Constants ────────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(SCRIPT_DIR, "..", "youtube-creators", "token.json")
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "progress.json")

OAUTH_CLIENT_CONFIG = {
    "installed": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

def load_subreddits(path="subreddits.yml"):
    with open(os.path.join(SCRIPT_DIR, path)) as f:
        subs = yaml.safe_load(f)
    if not subs or not isinstance(subs, list):
        raise ValueError(f"No subreddits found in {path}")
    return subs


def load_personality(path="personality.yml"):
    filepath = os.path.join(SCRIPT_DIR, path)
    if not os.path.exists(filepath):
        print(f"WARNING: {path} not found, using default personality")
        return {}
    with open(filepath) as f:
        return yaml.safe_load(f) or {}


def load_filters(path="filters.yml"):
    filepath = os.path.join(SCRIPT_DIR, path)
    if not os.path.exists(filepath):
        print(f"WARNING: {path} not found, no filters applied")
        return {}
    with open(filepath) as f:
        return yaml.safe_load(f) or {}


SUBREDDITS = load_subreddits()
PERSONALITY = load_personality()
FILTERS = load_filters()

COLUMNS = [
    "Subreddit", "Post title", "Summary", "Age (hrs)", "Created UTC",
    "Engage?", "Why", "Status", "Coolest comment",
    "Suggested reply to cool comment", "Suggested post comment",
    "Post link", "Source URL(s)",
]

REDDIT_HEADERS = {
    "User-Agent": "RedditOutreachBot/1.0 (educational research project)"
}
MAX_POST_AGE_HOURS = FILTERS.get("thresholds", {}).get("max_age_hours", 24)
REDDIT_SLEEP = 2  # seconds between Reddit requests
OPENAI_MODEL = "gpt-4o-mini"


# ── Pre-AI filtering ────────────────────────────────────────────────────────
def apply_pre_filters(posts, filters):
    """Apply rule-based filters to posts BEFORE sending to OpenAI."""
    if not filters:
        return posts

    kw = filters.get("keywords", {})
    include_kw = [w.lower() for w in (kw.get("include") or [])]
    exclude_kw = [w.lower() for w in (kw.get("exclude") or [])]

    thresholds = filters.get("thresholds", {})
    min_score = thresholds.get("min_score", 0)
    min_comments = thresholds.get("min_comments", 0)
    max_comments = thresholds.get("max_comments", float("inf"))

    post_type_allow = filters.get("post_type", {}).get("allow", "all")

    flair_cfg = filters.get("flairs", {})
    flair_include = [f.lower() for f in (flair_cfg.get("include") or [])]
    flair_exclude = [f.lower() for f in (flair_cfg.get("exclude") or [])]

    allowed_statuses = filters.get("allowed_statuses", ["active"])

    filtered = []
    for post in posts:
        if post["status"] not in allowed_statuses:
            continue
        if post["score"] < min_score:
            continue
        if post["num_comments"] < min_comments:
            continue
        if post["num_comments"] > max_comments:
            continue

        # Post type
        if post_type_allow == "self_only" and not post.get("is_self"):
            continue
        if post_type_allow == "link_only" and post.get("is_self"):
            continue

        # Keywords
        searchable = (post["title"] + " " + post["selftext"]).lower()
        if include_kw and not any(kw in searchable for kw in include_kw):
            continue
        if any(kw in searchable for kw in exclude_kw):
            continue

        # Flairs
        flair = post.get("flair", "").lower()
        if flair_include and flair not in flair_include:
            continue
        if flair in flair_exclude:
            continue

        filtered.append(post)

    return filtered


# ── Reddit fetching ──────────────────────────────────────────────────────────
def fetch_json(url, retries=3):
    """Fetch JSON from a URL with retries and rate-limit handling."""
    for attempt in range(retries):
        try:
            resp = http_requests.get(url, headers=REDDIT_HEADERS, timeout=30)
            if resp.status_code == 429:
                wait = (attempt + 1) * 5
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            if resp.status_code == 403:
                print(f"  403 Forbidden for {url}")
                return None
            resp.raise_for_status()
            return resp.json()
        except http_requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                print(f"  Request error ({e}), retrying...")
                time.sleep(3)
            else:
                print(f"  Failed after {retries} attempts: {e}")
                return None
    return None


def fetch_subreddit_posts(subreddit):
    """Fetch posts from the last 24 hours in a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=100"
    data = fetch_json(url)
    time.sleep(REDDIT_SLEEP)

    if not data or "data" not in data:
        return []

    now = time.time()
    cutoff = now - (MAX_POST_AGE_HOURS * 3600)
    posts = []

    for child in data["data"].get("children", []):
        post = child.get("data", {})
        created = post.get("created_utc", 0)
        if created < cutoff:
            continue

        # Determine status
        if post.get("removed_by_category"):
            status = "blocked"
        elif post.get("archived"):
            status = "archived"
        elif post.get("locked"):
            status = "inactive"
        else:
            status = "active"

        posts.append({
            "id": post.get("id", ""),
            "title": post.get("title", ""),
            "selftext": post.get("selftext", "")[:2000],
            "url": f"https://www.reddit.com{post.get('permalink', '')}",
            "permalink": post.get("permalink", ""),
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", 0),
            "created_utc": created,
            "status": status,
            "flair": post.get("link_flair_text", "") or "",
            "is_self": post.get("is_self", False),
        })

    return posts


def fetch_post_comments(permalink):
    """Fetch top-level comments for a post."""
    url = f"https://www.reddit.com{permalink}.json?limit=25"
    data = fetch_json(url)
    time.sleep(REDDIT_SLEEP)

    if not data or not isinstance(data, list) or len(data) < 2:
        return []

    comments = []
    for child in data[1].get("data", {}).get("children", []):
        if child.get("kind") != "t1":
            continue
        c = child.get("data", {})
        body = c.get("body", "")
        if body in ("[deleted]", "[removed]", ""):
            continue
        comments.append({
            "author": c.get("author", "[deleted]"),
            "body": body[:500],
            "score": c.get("score", 0),
        })

    # Sort by score descending, take top 10
    comments.sort(key=lambda x: x["score"], reverse=True)
    return comments[:10]


# ── OpenAI analysis ──────────────────────────────────────────────────────────
def _build_personality_block(personality):
    """Build the personality section of the OpenAI prompt."""
    if not personality:
        return ("Write comments that are conversational, fun, non-marketing-y, "
                "slightly humorous, and genuinely helpful.")

    name = personality.get("name", "the user")
    bio = personality.get("bio", "").strip()
    interests = ", ".join(personality.get("interests", []))
    expertise = ", ".join(personality.get("expertise", []))
    tone = personality.get("tone", {})
    dos = personality.get("dos", [])
    donts = personality.get("donts", [])
    examples = personality.get("example_comments", [])

    block = f"You are writing comments as {name}."
    if bio:
        block += f"\nBio: {bio}"
    if interests:
        block += f"\nInterests: {interests}"
    if expertise:
        block += f"\nExpertise: {expertise}"
    if tone:
        block += f"\nTone: {tone.get('style', 'conversational')}"
        block += f"\nHumor style: {tone.get('humor', 'light')}"
        block += f"\nFormality: {tone.get('formality', 'casual')}"
    if dos:
        block += "\n\nDO:\n" + "\n".join(f"- {d}" for d in dos)
    if donts:
        block += "\n\nDON'T:\n" + "\n".join(f"- {d}" for d in donts)
    if examples:
        block += "\n\nExample comments that reflect this voice:"
        for i, ex in enumerate(examples, 1):
            block += f'\n{i}. "{ex.strip()}"'

    return block


def _build_ai_prefs_block(filters):
    """Build the AI engagement preferences section of the OpenAI prompt."""
    if not filters:
        return ""
    ai_prefs = filters.get("ai_preferences", {})
    if not ai_prefs:
        return ""

    block = "\nEngagement criteria:"
    prefer = ai_prefs.get("prefer_topics", [])
    avoid = ai_prefs.get("avoid_topics", [])
    notes = ai_prefs.get("engagement_notes", "")

    if prefer:
        block += "\nPREFER posts that are:"
        for p in prefer:
            block += f"\n- {p}"
    if avoid:
        block += "\nAVOID posts that are:"
        for a in avoid:
            block += f"\n- {a}"
    if notes:
        block += f"\nAdditional guidance: {notes.strip()}"

    return block


def analyze_post(client, subreddit, post, comments, personality=None, filters=None):
    """Use OpenAI to generate summary, cool comment, suggested replies, and engagement recommendation."""
    comments_text = ""
    if comments:
        for i, c in enumerate(comments[:10], 1):
            comments_text += f"\n{i}. [score: {c['score']}] u/{c['author']}: {c['body']}"
    else:
        comments_text = "\n(No comments yet)"

    personality_block = _build_personality_block(personality)
    ai_prefs_block = _build_ai_prefs_block(filters)

    prompt = f"""You are analyzing a Reddit post for outreach potential.

{personality_block}

Subreddit: r/{subreddit}
Post title: {post['title']}
Post body: {post['selftext'] or '(no body text)'}
Score: {post['score']} | Comments: {post['num_comments']}

Top comments:{comments_text}
{ai_prefs_block}

Return a JSON object (no markdown fencing) with these exact keys:
- "summary": 1-2 sentence summary of what the post is about
- "coolest_comment": Copy the most interesting/insightful/funny comment verbatim. If no comments are interesting, write "no cool comments"
- "suggested_reply": A suggested reply to that cool comment, written in the voice described above. If no cool comment, write "—"
- "suggested_post_comment": A useful comment you'd leave on this post, written in the voice described above. Be genuinely helpful and specific to this post.
- "engage": "Yes", "No", or "Maybe". Be strict with "Yes" — only use it for exceptional posts that are a perfect engagement opportunity based on the criteria above. Most posts should be "Maybe" or "No".
- "why": 1 sentence explaining the engagement recommendation"""

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0.7,
            )
            text = response.choices[0].message.content.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            return json.loads(text)
        except (json.JSONDecodeError, Exception) as e:
            if attempt < 2:
                print(f"  OpenAI parse error ({e}), retrying...")
                time.sleep(2)
            else:
                print(f"  OpenAI analysis failed: {e}")
                return {
                    "summary": "ERROR: could not analyze",
                    "coolest_comment": "no cool comments",
                    "suggested_reply": "—",
                    "suggested_post_comment": "—",
                    "engage": "No",
                    "why": "Analysis failed",
                }


# ── Google Sheets ────────────────────────────────────────────────────────────
def get_sheets_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(OAUTH_CLIENT_CONFIG, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("sheets", "v4", credentials=creds)


def get_or_create_daily_tab(sheets_service, date_str):
    """Get or create a tab named with today's date."""
    meta = sheets_service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID
    ).execute()

    for sheet in meta["sheets"]:
        if sheet["properties"]["title"] == date_str:
            print(f"Tab '{date_str}' already exists, resuming...")
            return date_str

    # Create new tab
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={
            "requests": [{
                "addSheet": {
                    "properties": {"title": date_str}
                }
            }]
        },
    ).execute()
    print(f"Created new tab '{date_str}'")

    # Write header row
    sheets_service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{date_str}'!A1:{chr(64 + len(COLUMNS))}1",
        valueInputOption="RAW",
        body={"values": [COLUMNS]},
    ).execute()

    # Write info rows
    info_rows = [
        ["Reddit Outreach Sweep – last 24h snapshot"],
        ["Best-effort live capture from subreddit /new feeds. "
         "Rows marked 'no recent post found' mean the newest accessible "
         "post appeared older than 24h."],
        [],  # blank separator
    ]
    sheets_service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{date_str}'!A2:A4",
        valueInputOption="RAW",
        body={"values": info_rows},
    ).execute()

    return date_str


def append_rows_to_sheet(sheets_service, tab_name, rows):
    if not rows:
        return
    values = [[row.get(col, "") for col in COLUMNS] for row in rows]
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{tab_name}'!A:{chr(64 + len(COLUMNS))}",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
    print(f"  Appended {len(rows)} rows to Google Sheet")


# ── Checkpoint / resume ──────────────────────────────────────────────────────
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
        if data.get("date") == datetime.date.today().isoformat():
            return {
                "date": data["date"],
                "completed_subs": set(data.get("completed_subreddits", [])),
                "processed_ids": set(data.get("processed_post_ids", [])),
                "total_written": data.get("total_written", 0),
            }
    # Fresh start
    return {
        "date": datetime.date.today().isoformat(),
        "completed_subs": set(),
        "processed_ids": set(),
        "total_written": 0,
    }


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "date": progress["date"],
            "completed_subreddits": list(progress["completed_subs"]),
            "processed_post_ids": list(progress["processed_ids"]),
            "total_written": progress["total_written"],
        }, f)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    today = datetime.date.today().isoformat()
    print(f"Reddit Outreach Sweep – {today}")
    print(f"Scanning {len(SUBREDDITS)} subreddits for posts from the last {MAX_POST_AGE_HOURS}h\n")

    # Initialize clients
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print("Authenticating with Google Sheets...")
    sheets_service = get_sheets_service()

    # Create/get today's tab
    tab_name = get_or_create_daily_tab(sheets_service, today)

    # Load checkpoint
    progress = load_progress()
    print(f"Progress: {len(progress['completed_subs'])}/{len(SUBREDDITS)} subreddits done, "
          f"{progress['total_written']} rows written\n")

    pending_rows = []

    try:
        for i, subreddit in enumerate(SUBREDDITS, 1):
            if subreddit in progress["completed_subs"]:
                continue

            print(f"[{i}/{len(SUBREDDITS)}] r/{subreddit}")

            # Fetch and filter posts
            posts = fetch_subreddit_posts(subreddit)
            raw_count = len(posts)
            posts = apply_pre_filters(posts, FILTERS)

            if not posts:
                print(f"  No posts in last {MAX_POST_AGE_HOURS}h"
                      f" (fetched {raw_count}, all filtered out)" if raw_count else
                      f"  No posts in last {MAX_POST_AGE_HOURS}h")
                pending_rows.append({
                    "Subreddit": f"r/{subreddit}",
                    "Post title": "[No last-24h post detected in accessible /new snapshot]",
                    "Post link": "",
                    "Status": "inactive",
                    "Summary": f"Newest accessible post in the /new feed appeared far older "
                               f"than {MAX_POST_AGE_HOURS} hours, so this subreddit looked "
                               f"quiet for today's sweep.",
                    "Coolest comment": "no cool comments",
                    "Suggested reply to cool comment": "—",
                    "Suggested post comment": "—",
                    "Engage?": "No",
                    "Why": "",
                    "Source URL(s)": f"https://www.reddit.com/r/{subreddit}/new/.json?limit=5",
                    "Created UTC": "",
                    "Age (hrs)": "",
                })
            else:
                print(f"  Found {len(posts)} posts")
                for post in posts:
                    if post["id"] in progress["processed_ids"]:
                        continue

                    # Fetch comments
                    comments = fetch_post_comments(post["permalink"])

                    # Analyze with OpenAI
                    analysis = analyze_post(openai_client, subreddit, post, comments,
                                            personality=PERSONALITY, filters=FILTERS)

                    # Calculate age
                    age_hrs = round((time.time() - post["created_utc"]) / 3600, 1)
                    created_str = (
                        datetime.datetime.utcfromtimestamp(post["created_utc"])
                        .strftime("%Y-%m-%d %H:%M")
                        if post["created_utc"] else ""
                    )

                    # Build row — blank suggestions for Maybe/No
                    source_urls = (
                        f"https://www.reddit.com/r/{subreddit}/new/.json?limit=5 ; "
                        f"https://www.reddit.com/r/{subreddit}/comments/{post['id']}/.json?limit=10"
                    )

                    engage = analysis.get("engage", "Maybe")
                    show_suggestions = engage == "Yes"

                    pending_rows.append({
                        "Subreddit": f"r/{subreddit}",
                        "Post title": post["title"],
                        "Post link": post["url"],
                        "Status": post["status"],
                        "Summary": analysis.get("summary", ""),
                        "Coolest comment": analysis.get("coolest_comment", "—") if show_suggestions else "—",
                        "Suggested reply to cool comment": analysis.get("suggested_reply", "—") if show_suggestions else "—",
                        "Suggested post comment": analysis.get("suggested_post_comment", "—") if show_suggestions else "—",
                        "Engage?": engage,
                        "Why": analysis.get("why", "") if show_suggestions else "",
                        "Source URL(s)": source_urls,
                        "Created UTC": created_str,
                        "Age (hrs)": str(age_hrs),
                    })

                    progress["processed_ids"].add(post["id"])

            # Write batch for this subreddit
            if pending_rows:
                append_rows_to_sheet(sheets_service, tab_name, pending_rows)
                progress["total_written"] += len(pending_rows)
                pending_rows = []

            progress["completed_subs"].add(subreddit)
            save_progress(progress)

    except KeyboardInterrupt:
        print("\n\nInterrupted! Saving progress...")
    finally:
        # Flush any remaining rows
        if pending_rows:
            try:
                append_rows_to_sheet(sheets_service, tab_name, pending_rows)
                progress["total_written"] += len(pending_rows)
            except Exception as e:
                # Save to fallback file
                fallback = os.path.join(SCRIPT_DIR, "fallback_rows.json")
                with open(fallback, "w") as f:
                    json.dump(pending_rows, f, indent=2)
                print(f"  Sheet write failed ({e}), saved {len(pending_rows)} rows to {fallback}")

        save_progress(progress)
        print(f"\nDone! {progress['total_written']} total rows written to tab '{tab_name}'")
        print(f"Sheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


if __name__ == "__main__":
    main()
