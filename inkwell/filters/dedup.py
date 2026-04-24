"""Cross-day deduplication using local signal files."""

import logging

from inkwell.scanners.base import RawSignal
from inkwell.storage.signals import load_recent_signal_ids

logger = logging.getLogger(__name__)


def deduplicate_signals(signals: list[RawSignal], lookback_days: int = 3) -> list[RawSignal]:
    """Remove signals that were already discovered in recent days."""
    seen_ids = load_recent_signal_ids(lookback_days)
    if not seen_ids:
        return signals

    deduped = [s for s in signals if f"{s.platform}_{s.platform_id}" not in seen_ids]
    removed = len(signals) - len(deduped)
    if removed:
        logger.info("Dedup: removed %d already-seen signals", removed)
    return deduped
