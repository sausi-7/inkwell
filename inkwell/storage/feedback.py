"""User feedback storage for signal quality ratings."""

import json
import logging

from inkwell.config import DATA_DIR

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


# ─── learned preferences ─────────────────────────────────────────────────────
#
# Ratings are collected by the /rate endpoint but were historically never read
# back. compute_preference_weights() joins each rating to its stored signal and
# turns the user's taste into a small, mean-centered, clamped nudge that
# analyzers.rules folds into the free heuristic score (no LLM, no tokens).

# Below this many ratings the learned signal is too sparse to trust — return
# empty weights so scoring is unchanged (cold start = no-op).
MIN_RATINGS_TO_LEARN = 5

# A rating maps to a centered value in [-1, +1]: 5★ → +1, 3★ → 0, 1★ → -1.
def _rating_to_value(rating: int) -> float:
    return (max(1, min(5, rating)) - 3) / 2.0


# Significant words (>3 chars) so we ignore stopwords — mirrors rules._topic_hit.
def _keywords(text: str) -> set[str]:
    import re
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3}


def compute_preference_weights(max_abs: float = 1.0) -> dict:
    """Aggregate past ratings into per-subreddit and per-keyword weights.

    Returns ``{"subreddits": {name: weight}, "keywords": {word: weight},
    "n_ratings": int}``. Each weight is the mean centered rating value for that
    key, then mean-centered across keys and clamped to ±``max_abs`` so a handful
    of ratings can't dominate the heuristic. Below MIN_RATINGS_TO_LEARN total
    usable ratings, weight maps are empty (cold-start no-op).

    Signals are looked up lazily; this is meant to be cached by the caller, not
    called once per scored post.
    """
    from inkwell.storage.signals import list_signal_dates, load_signals

    ratings = _load_all()

    # Index stored signals by both id and platform_id for the rating join.
    index: dict[str, dict] = {}
    for date_str in list_signal_dates():
        for s in load_signals(date_str):
            if s.get("id"):
                index.setdefault(s["id"], s)
            if s.get("platform_id"):
                index.setdefault(s["platform_id"], s)

    sub_vals: dict[str, list[float]] = {}
    kw_vals: dict[str, list[float]] = {}
    used = 0
    for r in ratings:
        signal = index.get(r.get("signal_id"))
        if not signal:
            continue
        value = _rating_to_value(r.get("rating", 3))
        used += 1
        sub = signal.get("subreddit", "")
        if sub:
            sub_vals.setdefault(sub.lower(), []).append(value)
        for word in _keywords(signal.get("title", "") + " " + signal.get("body", "")):
            kw_vals.setdefault(word, []).append(value)

    if used < MIN_RATINGS_TO_LEARN:
        return {"subreddits": {}, "keywords": {}, "n_ratings": used}

    def _finalize(vals: dict[str, list[float]]) -> dict[str, float]:
        means = {k: sum(v) / len(v) for k, v in vals.items()}
        if not means:
            return {}
        center = sum(means.values()) / len(means)
        return {
            k: round(max(-max_abs, min(max_abs, m - center)), 3)
            for k, m in means.items()
        }

    return {
        "subreddits": _finalize(sub_vals),
        "keywords": _finalize(kw_vals),
        "n_ratings": used,
    }
