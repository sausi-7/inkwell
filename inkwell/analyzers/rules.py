"""Rule-based analysis — no network, no LLM tokens.

Before the analyzer split, a single LLM call produced all six output fields
(summary, coolest_comment, suggested_reply, suggested_post_comment, engage, why).
That meant every scanned post burned tokens, even ones the user would never look at.

This module replaces the four non-voice fields with deterministic heuristics so
scanning is free. Voice drafts live in inkwell.analyzers.voice and are
generated on demand only when the user asks for one (UI button / CLI subcommand).
"""

from __future__ import annotations

import logging
import re
import time

from inkwell.analyzers.base import Analysis
from inkwell.scanners.base import RawSignal

logger = logging.getLogger(__name__)

VOICE_PLACEHOLDER = "—"  # em dash — drafts filled in later

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_QUESTION_STARTERS = (
    "how ", "what ", "why ", "where ", "when ", "which ", "who ",
    "can ", "could ", "should ", "is ", "are ", "does ", "do ", "any ",
    "anyone", "anybody", "has anyone", "help ",
)


def summary(signal: RawSignal, max_chars: int = 280) -> str:
    """First 1–2 sentences of the body; falls back to the title if body is empty."""
    text = (signal.body or "").strip()
    if not text:
        return signal.title.strip()
    sentences = _SENTENCE_SPLIT.split(text)
    out = " ".join(sentences[:2]).strip()
    if len(out) > max_chars:
        out = out[: max_chars].rsplit(" ", 1)[0] + "…"
    return out or signal.title.strip()


def coolest_comment(signal: RawSignal, max_chars: int = 500) -> str:
    """Pick the highest-scored comment. Returns a sentinel if no usable comment exists."""
    if not signal.replies:
        return "no cool comments"
    top = max(signal.replies, key=lambda r: r.score)
    body = (top.body or "").strip()
    if not body or top.score < 1:
        return "no cool comments"
    if len(body) > max_chars:
        body = body[: max_chars].rsplit(" ", 1)[0] + "…"
    return f"[u/{top.author}, {top.score}↑] {body}"


def _looks_like_question(title: str) -> bool:
    t = title.lower().strip()
    if t.endswith("?"):
        return True
    return any(t.startswith(w) for w in _QUESTION_STARTERS)


def _topic_hit(topic: str, searchable: str) -> bool:
    """A topic 'hits' if any of its significant words (>3 chars) appears in the text."""
    words = [w.strip(",.!?:;\"'()") for w in topic.lower().split() if len(w) > 3]
    return any(w in searchable for w in words)


# How hard learned preferences can pull the score, in points. The raw learned
# weight is in [-1, +1] (see storage.feedback.compute_preference_weights); we
# scale by this so it nudges rather than overrides the base heuristic.
LEARNED_BONUS_SCALE = 2.0


def _learned_bonus(signal: RawSignal, weights: dict | None) -> float:
    """Score nudge derived from the user's past ratings (free — no LLM).

    `weights` is the output of storage.feedback.compute_preference_weights().
    Combines the subreddit weight with the mean of matched keyword weights,
    scaled and clamped to ±LEARNED_BONUS_SCALE. Empty/None weights → 0.0, so
    this is a no-op until enough ratings exist (cold start).
    """
    if not weights:
        return 0.0
    sub = (signal.metadata or {}).get("subreddit", "").lower()
    raw = (weights.get("subreddits", {}) or {}).get(sub, 0.0)

    kw_weights = weights.get("keywords", {}) or {}
    if kw_weights:
        # Match on whole-word tokens (>3 chars), the same tokenization the
        # weights were built from in storage.feedback — so "art" can't match
        # inside "start".
        tokens = set(re.findall(r"[a-z0-9]+", (signal.title + " " + (signal.body or "")).lower()))
        hits = [w for kw, w in kw_weights.items() if kw in tokens]
        if hits:
            raw += sum(hits) / len(hits)

    scaled = raw * LEARNED_BONUS_SCALE
    return round(max(-LEARNED_BONUS_SCALE, min(LEARNED_BONUS_SCALE, scaled)), 2)


def score_breakdown(
    signal: RawSignal, filters: dict | None = None, weights: dict | None = None
) -> dict:
    """Transparent per-component score. Exposed so the UI can show 'why' graphically.

    `weights` (optional) folds in learned preferences from past ratings; pass
    the cached output of storage.feedback.compute_preference_weights().
    """
    filters = filters or {}
    thresholds = filters.get("thresholds", {}) or {}
    max_age_h = thresholds.get("max_age_hours", 24)
    ai_prefs = filters.get("ai_preferences", {}) or {}
    prefer_topics = ai_prefs.get("prefer_topics", []) or []
    avoid_topics = ai_prefs.get("avoid_topics", []) or []

    searchable = (signal.title + " " + (signal.body or "")).lower()
    prefer_hits = sum(1 for t in prefer_topics if _topic_hit(t, searchable))
    avoid_hits = sum(1 for t in avoid_topics if _topic_hit(t, searchable))

    if signal.created_utc:
        age_hours = max(0.0, (time.time() - signal.created_utc) / 3600.0)
    else:
        age_hours = float(max_age_h)
    age_bonus = max(0.0, (max_age_h - age_hours) / max(max_age_h, 1)) * 2.0

    author_deleted = signal.author in ("", "[deleted]", "[removed]")

    breakdown = {
        "post_score": round(min(max(signal.score, 0) / 10.0, 5.0), 2),
        "velocity": round(min(signal.reply_count / 5.0, 3.0), 2),
        "prefer_hits": float(prefer_hits),
        "avoid_penalty": -2.0 * avoid_hits,
        "age_bonus": round(age_bonus, 2),
        "question_bonus": 1.0 if _looks_like_question(signal.title) else 0.0,
        "author_penalty": -5.0 if author_deleted else 0.0,
        "learned_bonus": _learned_bonus(signal, weights),
    }
    breakdown["total"] = round(sum(breakdown.values()), 2)
    return breakdown


def engage(
    signal: RawSignal, filters: dict | None = None, weights: dict | None = None
) -> tuple[str, dict]:
    """Return (decision, score_breakdown). Decision ∈ {Yes, Maybe, No}."""
    bd = score_breakdown(signal, filters, weights)

    # Hard disqualifiers: deleted author or any avoid-topic hit.
    if bd["author_penalty"] < 0 or bd["avoid_penalty"] < 0:
        return "No", bd

    total = bd["total"]
    if total >= 6.0:
        return "Yes", bd
    if total >= 3.0:
        return "Maybe", bd
    return "No", bd


def why(signal: RawSignal, decision: str, breakdown: dict) -> str:
    """One-line rationale. Keeps the UI row honest about the score."""
    parts = [f"score {signal.score}", f"{signal.reply_count} replies"]
    if breakdown["prefer_hits"]:
        parts.append(f"{int(breakdown['prefer_hits'])} preferred-topic hit(s)")
    if breakdown["avoid_penalty"] < 0:
        parts.append("avoid-topic hit")
    if breakdown["question_bonus"]:
        parts.append("looks like a question")
    if breakdown.get("learned_bonus", 0) > 0:
        parts.append("matches what you've liked before")
    elif breakdown.get("learned_bonus", 0) < 0:
        parts.append("similar to what you've passed on")
    if breakdown["author_penalty"] < 0:
        parts.append("author deleted/removed")
    parts.append(f"total {breakdown['total']}")
    return "; ".join(parts)


def analyze_rules(
    signal: RawSignal, filters: dict | None = None, weights: dict | None = None
) -> Analysis:
    """Full rule-based analysis. Voice fields are left as placeholders.

    `weights` (optional) folds learned rating preferences into the score; pass
    the cached output of storage.feedback.compute_preference_weights().
    """
    decision, bd = engage(signal, filters, weights)
    return Analysis(
        summary=summary(signal),
        coolest_comment=coolest_comment(signal),
        suggested_reply=VOICE_PLACEHOLDER,
        suggested_post_comment=VOICE_PLACEHOLDER,
        engage=decision,
        why=why(signal, decision, bd),
    )
