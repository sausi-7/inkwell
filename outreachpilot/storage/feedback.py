"""User feedback storage for signal quality ratings."""

import json
import logging

from outreachpilot.config import DATA_DIR

logger = logging.getLogger(__name__)

FEEDBACK_FILE = DATA_DIR / "feedback" / "ratings.json"


def _ensure_dir():
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_all() -> list[dict]:
    _ensure_dir()
    if not FEEDBACK_FILE.exists():
        return []
    with open(FEEDBACK_FILE) as f:
        return json.load(f)


def _save_all(feedback: list[dict]) -> None:
    _ensure_dir()
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(feedback, f, indent=2)


def add_feedback(signal_id: str, rating: int, outcome: str | None = None,
                 notes: str | None = None) -> None:
    """Add feedback for a signal. Rating is 1-5."""
    import datetime
    feedback = _load_all()
    feedback.append({
        "signal_id": signal_id,
        "rating": max(1, min(5, rating)),
        "outcome": outcome,
        "notes": notes,
        "timestamp": datetime.datetime.now().isoformat(),
    })
    _save_all(feedback)


def get_feedback_for_signal(signal_id: str) -> list[dict]:
    """Get all feedback entries for a signal."""
    return [f for f in _load_all() if f.get("signal_id") == signal_id]
