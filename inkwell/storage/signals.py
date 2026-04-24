"""Signal storage — save and load signals as daily JSON files."""

import datetime
import json
import logging
from pathlib import Path

from inkwell.config import DATA_DIR

logger = logging.getLogger(__name__)

SIGNALS_DIR = DATA_DIR / "signals"


def _ensure_dir():
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)


def save_signals(signals: list[dict], date_str: str | None = None) -> Path:
    """Save signals to a daily JSON file. Merges with existing data."""
    _ensure_dir()
    if date_str is None:
        date_str = datetime.date.today().isoformat()

    filepath = SIGNALS_DIR / f"{date_str}.json"

    existing = []
    if filepath.exists():
        with open(filepath) as f:
            existing = json.load(f)

    # Merge: add new signals, skip duplicates by id
    existing_ids = {s.get("id") for s in existing}
    for signal in signals:
        if signal.get("id") not in existing_ids:
            existing.append(signal)

    with open(filepath, "w") as f:
        json.dump(existing, f, indent=2, default=str)

    logger.info("Saved %d signals to %s", len(existing), filepath.name)
    return filepath


def load_signals(date_str: str | None = None) -> list[dict]:
    """Load signals from a daily JSON file."""
    if date_str is None:
        date_str = datetime.date.today().isoformat()

    filepath = SIGNALS_DIR / f"{date_str}.json"
    if not filepath.exists():
        return []

    with open(filepath) as f:
        return json.load(f)


def load_recent_signal_ids(lookback_days: int = 3) -> set[str]:
    """Load signal IDs from recent days for deduplication."""
    _ensure_dir()
    ids = set()
    today = datetime.date.today()

    for i in range(lookback_days):
        date_str = (today - datetime.timedelta(days=i)).isoformat()
        filepath = SIGNALS_DIR / f"{date_str}.json"
        if filepath.exists():
            with open(filepath) as f:
                signals = json.load(f)
            for s in signals:
                ids.add(s.get("id", ""))

    return ids


def list_signal_dates() -> list[str]:
    """List all dates that have signal files, most recent first."""
    _ensure_dir()
    files = sorted(SIGNALS_DIR.glob("*.json"), reverse=True)
    return [f.stem for f in files]
