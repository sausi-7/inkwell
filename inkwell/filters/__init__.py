"""Filtering engine for outreach signals."""

from inkwell.filters.rule_filter import apply_pre_filters
from inkwell.filters.dedup import deduplicate_signals

__all__ = ["apply_pre_filters", "deduplicate_signals"]
