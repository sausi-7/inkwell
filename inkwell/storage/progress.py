"""Checkpoint/resume system using local JSON files."""

import datetime
import json
import logging

from inkwell.config import DATA_DIR

logger = logging.getLogger(__name__)

PROGRESS_FILE = DATA_DIR / "progress.json"


def load_progress() -> dict:
    """Load progress from checkpoint file, resetting if it's a new day."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
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


def save_progress(progress: dict) -> None:
    """Save progress to checkpoint file."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "date": progress["date"],
            "completed_subreddits": list(progress["completed_subs"]),
            "processed_post_ids": list(progress["processed_ids"]),
            "total_written": progress["total_written"],
        }, f)
