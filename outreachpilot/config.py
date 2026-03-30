"""Configuration loader for OutreachPilot.

Loads settings from .env and YAML config files.
"""

import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Root directory of the project (where pyproject.toml lives)
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"

load_dotenv(ROOT_DIR / ".env")


def _require_env(key: str) -> str:
    val = os.environ.get(key, "")
    if not val:
        sys.exit(f"ERROR: Set {key} in .env")
    return val


# API keys and credentials
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "")

# LLM settings
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "1024"))

# Google Sheets OAuth
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TOKEN_FILE = ROOT_DIR / "token.json"

OAUTH_CLIENT_CONFIG = {
    "installed": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

# Reddit settings
REDDIT_HEADERS = {
    "User-Agent": "OutreachPilot/0.1 (open source outreach tool)"
}
REDDIT_SLEEP = 2  # seconds between Reddit requests

# Output columns for Google Sheets
COLUMNS = [
    "Subreddit", "Post title", "Summary", "Age (hrs)", "Created UTC",
    "Engage?", "Why", "Status", "Coolest comment",
    "Suggested reply to cool comment", "Suggested post comment",
    "Post link", "Source URL(s)",
]


def load_yaml(filename: str, directory: Path | None = None) -> dict | list:
    """Load a YAML file from config directory or a custom path."""
    if directory is None:
        directory = CONFIG_DIR
    filepath = directory / filename
    if not filepath.exists():
        return {}
    with open(filepath) as f:
        return yaml.safe_load(f) or {}


def load_subreddits(filename: str = "subreddits.yml") -> list[str]:
    subs = load_yaml(filename)
    if not subs or not isinstance(subs, list):
        # Fallback: try root directory (backward compat)
        root_path = ROOT_DIR / filename
        if root_path.exists():
            with open(root_path) as f:
                subs = yaml.safe_load(f)
        if not subs or not isinstance(subs, list):
            raise ValueError(f"No subreddits found in {filename}")
    return subs


def load_personality(filename: str = "personality.yml") -> dict:
    personality = load_yaml(filename)
    if not personality:
        # Fallback: try root directory (backward compat)
        root_path = ROOT_DIR / filename
        if root_path.exists():
            with open(root_path) as f:
                personality = yaml.safe_load(f) or {}
    return personality


def load_filters(filename: str = "filters.yml") -> dict:
    filters = load_yaml(filename)
    if not filters:
        # Fallback: try root directory (backward compat)
        root_path = ROOT_DIR / filename
        if root_path.exists():
            with open(root_path) as f:
                filters = yaml.safe_load(f) or {}
    return filters


def get_max_post_age_hours(filters: dict) -> int:
    return filters.get("thresholds", {}).get("max_age_hours", 24)


def ensure_data_dirs():
    """Create data directories if they don't exist."""
    for subdir in ["signals", "analyses", "campaigns", "feedback", "scan_history"]:
        (DATA_DIR / subdir).mkdir(parents=True, exist_ok=True)
