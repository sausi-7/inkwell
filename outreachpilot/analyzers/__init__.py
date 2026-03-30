"""AI analysis engine for outreach signals."""

from outreachpilot.analyzers.base import Analysis
from outreachpilot.analyzers.pipeline import analyze_signal

__all__ = ["Analysis", "analyze_signal"]
