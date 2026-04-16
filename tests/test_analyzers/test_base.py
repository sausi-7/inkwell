"""Tests for outreachpilot.analyzers.base."""

from outreachpilot.analyzers.base import Analysis


def test_error_fallback_sets_engage_no():
    """A failed LLM call must not produce an engagement 'Yes' — that would
    leak placeholder rows into the user's sheet as actionable signals."""
    fallback = Analysis.error_fallback()
    assert fallback.engage == "No"


def test_error_fallback_uses_dash_placeholders_for_suggestions():
    fallback = Analysis.error_fallback()
    assert fallback.suggested_reply == "\u2014"
    assert fallback.suggested_post_comment == "\u2014"


def test_error_fallback_marks_summary_as_error():
    assert "ERROR" in Analysis.error_fallback().summary


def test_analysis_round_trips_required_fields():
    a = Analysis(
        summary="A post asking for pricing feedback.",
        coolest_comment="Try value-based pricing.",
        suggested_reply="Agreed — anchoring matters.",
        suggested_post_comment="Have you tried X?",
        engage="Yes",
        why="Direct ask with specific context.",
    )
    assert a.engage == "Yes"
    assert a.model_used == ""
    assert a.tokens_used == 0
