"""Filtering engine for outreach signals."""

from outreachpilot.filters.rule_filter import apply_pre_filters
from outreachpilot.filters.dedup import deduplicate_signals

__all__ = ["apply_pre_filters", "deduplicate_signals"]
