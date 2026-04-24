"""Scan-time analysis pipeline — rule-based only, zero tokens.

The LLM is no longer invoked during scanning. All voice drafting (the only
path that spends tokens) lives in inkwell.analyzers.voice.draft_voice
and is called on demand via the web UI's "Draft" button or the
`inkwell draft <signal_id>` CLI subcommand.

`analyze_signal` keeps its original signature so callers don't change.
"""

from __future__ import annotations

import logging

from inkwell.analyzers.base import Analysis
from inkwell.analyzers.rules import analyze_rules
from inkwell.scanners.base import RawSignal

logger = logging.getLogger(__name__)


def analyze_signal(
    signal: RawSignal,
    personality: dict | None = None,
    filters: dict | None = None,
) -> Analysis:
    """Rule-based signal analysis. Never makes a network call."""
    _ = personality  # accepted for API stability; not needed for rules
    return analyze_rules(signal, filters=filters)
