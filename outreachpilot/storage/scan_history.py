"""Scan history tracking."""

import datetime
import json
import logging
from pathlib import Path

from outreachpilot.config import DATA_DIR

logger = logging.getLogger(__name__)

HISTORY_DIR = DATA_DIR / "scan_history"


def _ensure_dir():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def record_scan(scanner_name: str, targets_count: int, signals_found: int,
                signals_after_filter: int, signals_analyzed: int,
                status: str = "completed", error: str | None = None) -> None:
    """Record a scan run."""
    _ensure_dir()
    date_str = datetime.date.today().isoformat()
    filepath = HISTORY_DIR / f"{date_str}.json"

    history = []
    if filepath.exists():
        with open(filepath) as f:
            history = json.load(f)

    history.append({
        "scanner": scanner_name,
        "timestamp": datetime.datetime.now().isoformat(),
        "targets_count": targets_count,
        "signals_found": signals_found,
        "signals_after_filter": signals_after_filter,
        "signals_analyzed": signals_analyzed,
        "status": status,
        "error": error,
    })

    with open(filepath, "w") as f:
        json.dump(history, f, indent=2)


def load_scan_history(date_str: str | None = None) -> list[dict]:
    """Load scan history for a given date."""
    _ensure_dir()
    if date_str is None:
        date_str = datetime.date.today().isoformat()
    filepath = HISTORY_DIR / f"{date_str}.json"
    if not filepath.exists():
        return []
    with open(filepath) as f:
        return json.load(f)
