"""Rule-based pre-filtering — runs before AI analysis to save costs."""

import logging

from inkwell.scanners.base import RawSignal

logger = logging.getLogger(__name__)


def apply_pre_filters(signals: list[RawSignal], filters: dict) -> list[RawSignal]:
    """Apply rule-based filters to signals BEFORE sending to AI."""
    if not filters:
        return signals

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
    for signal in signals:
        if signal.status not in allowed_statuses:
            continue
        if signal.score < min_score:
            continue
        if signal.reply_count < min_comments:
            continue
        if signal.reply_count > max_comments:
            continue

        # Post type (Reddit-specific)
        is_self = signal.metadata.get("is_self", True)
        if post_type_allow == "self_only" and not is_self:
            continue
        if post_type_allow == "link_only" and is_self:
            continue

        # Keywords
        searchable = (signal.title + " " + signal.body).lower()
        if include_kw and not any(kw in searchable for kw in include_kw):
            continue
        if any(kw in searchable for kw in exclude_kw):
            continue

        # Flairs (Reddit-specific)
        flair = signal.metadata.get("flair", "").lower()
        if flair_include and flair not in flair_include:
            continue
        if flair in flair_exclude:
            continue

        filtered.append(signal)

    logger.info("Pre-filter: %d → %d signals", len(signals), len(filtered))
    return filtered
