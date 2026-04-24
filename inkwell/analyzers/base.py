"""Base data models for AI analysis."""

from dataclasses import dataclass


@dataclass
class Analysis:
    """Result of AI analysis on a signal."""
    summary: str
    coolest_comment: str
    suggested_reply: str
    suggested_post_comment: str
    engage: str  # "Yes", "No", "Maybe"
    why: str
    model_used: str = ""
    tokens_used: int = 0

    @staticmethod
    def error_fallback() -> "Analysis":
        return Analysis(
            summary="ERROR: could not analyze",
            coolest_comment="no cool comments",
            suggested_reply="\u2014",
            suggested_post_comment="\u2014",
            engage="No",
            why="Analysis failed",
        )
