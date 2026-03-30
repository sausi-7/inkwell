"""Campaign storage — manage campaign files."""

import json
import logging
from pathlib import Path

from outreachpilot.config import DATA_DIR

logger = logging.getLogger(__name__)

CAMPAIGNS_DIR = DATA_DIR / "campaigns"


def _ensure_dir():
    CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)


def save_campaign(name: str, data: dict) -> Path:
    """Save a campaign to a JSON file."""
    _ensure_dir()
    slug = name.lower().replace(" ", "-")
    filepath = CAMPAIGNS_DIR / f"{slug}.json"
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


def load_campaign(name: str) -> dict | None:
    """Load a campaign by name."""
    _ensure_dir()
    slug = name.lower().replace(" ", "-")
    filepath = CAMPAIGNS_DIR / f"{slug}.json"
    if not filepath.exists():
        return None
    with open(filepath) as f:
        return json.load(f)


def list_campaigns() -> list[dict]:
    """List all campaigns with basic info."""
    _ensure_dir()
    campaigns = []
    for filepath in sorted(CAMPAIGNS_DIR.glob("*.json")):
        with open(filepath) as f:
            data = json.load(f)
        data["_slug"] = filepath.stem
        campaigns.append(data)
    return campaigns


def delete_campaign(name: str) -> bool:
    """Delete a campaign file."""
    slug = name.lower().replace(" ", "-")
    filepath = CAMPAIGNS_DIR / f"{slug}.json"
    if filepath.exists():
        filepath.unlink()
        return True
    return False
