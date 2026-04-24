"""Tests for inkwell.analyzers.rules — deterministic, no network.

These heuristics replaced the LLM's scan-time work when we split the analyzer
into rules (free) + voice (BYOK). Regressions here would silently change which
posts surface as "Yes", so every scoring component has its own test."""

from __future__ import annotations

from inkwell.analyzers.rules import (
    VOICE_PLACEHOLDER,
    analyze_rules,
    coolest_comment,
    engage,
    score_breakdown,
    summary,
    why,
)
from inkwell.scanners.base import Reply


# ─── summary ────────────────────────────────────────────────────────────────

def test_summary_returns_first_two_sentences(signal_factory):
    s = signal_factory(body="First sentence. Second sentence. Third sentence. Fourth.")
    assert summary(s) == "First sentence. Second sentence."


def test_summary_falls_back_to_title_when_body_empty(signal_factory):
    s = signal_factory(title="A bare-link post", body="")
    assert summary(s) == "A bare-link post"


def test_summary_truncates_long_single_sentences(signal_factory):
    long_text = "word " * 200  # ~1000 chars, no sentence break
    s = signal_factory(body=long_text.strip() + ".")
    out = summary(s, max_chars=280)
    assert len(out) <= 281  # 280 + ellipsis
    assert out.endswith("…")


# ─── coolest_comment ────────────────────────────────────────────────────────

def test_coolest_comment_picks_highest_score(signal_factory):
    replies = [
        Reply(author="alice", body="meh", score=1),
        Reply(author="bob", body="this is the insight", score=42),
        Reply(author="carol", body="also meh", score=3),
    ]
    s = signal_factory(replies=replies)
    out = coolest_comment(s)
    assert "bob" in out
    assert "42" in out
    assert "this is the insight" in out


def test_coolest_comment_sentinel_when_no_replies(signal_factory):
    assert coolest_comment(signal_factory(replies=[])) == "no cool comments"


def test_coolest_comment_sentinel_when_top_is_zero_score(signal_factory):
    s = signal_factory(replies=[Reply(author="x", body="hi", score=0)])
    assert coolest_comment(s) == "no cool comments"


# ─── score_breakdown / engage ───────────────────────────────────────────────

def test_engage_yes_for_high_quality_recent_question(signal_factory):
    s = signal_factory(
        title="How do you handle rate limiting with LLMs?",
        body="I'm building an app that hits the OpenAI API and keep getting 429s.",
        score=45,        # caps at 5.0
        reply_count=8,   # > cap, contributes 3.0
        age_hours=0.5,
    )
    # prefer_topics whose significant words (>3 chars) lexically overlap the post.
    filters = {
        "thresholds": {"max_age_hours": 24},
        "ai_preferences": {
            "prefer_topics": ["rate limiting questions", "building an app"],
        },
    }
    decision, bd = engage(s, filters)
    assert decision == "Yes", bd
    assert bd["question_bonus"] == 1.0
    assert bd["prefer_hits"] >= 1, bd


def test_prefer_topic_matches_on_significant_word_overlap(signal_factory):
    """Heuristic is intentionally simple/lexical — documents that behavior."""
    s = signal_factory(title="Rate limiting strategies", body="Curious what works.")
    bd = score_breakdown(
        s, {"ai_preferences": {"prefer_topics": ["rate limiting design"]}}
    )
    assert bd["prefer_hits"] == 1.0


def test_prefer_topic_does_not_match_on_short_stopwords(signal_factory):
    """Words <=3 chars (e.g. 'for', 'the') must not cause false-positive hits."""
    s = signal_factory(title="I need a hand with the config", body="")
    bd = score_breakdown(
        s, {"ai_preferences": {"prefer_topics": ["for the win"]}}
    )
    assert bd["prefer_hits"] == 0.0


def test_engage_no_when_author_deleted(signal_factory):
    s = signal_factory(score=100, reply_count=50, age_hours=0.1)
    s.author = "[deleted]"
    decision, bd = engage(s)
    assert decision == "No"
    assert bd["author_penalty"] < 0


def test_engage_no_when_avoid_topic_hits(signal_factory):
    s = signal_factory(
        title="Check out my new crypto airdrop",
        body="Free tokens for early backers!",
        score=50, reply_count=10, age_hours=0.5,
    )
    filters = {
        "ai_preferences": {"avoid_topics": ["self-promotion spam", "crypto airdrop stuff"]},
    }
    decision, _ = engage(s, filters)
    assert decision == "No"


def test_engage_maybe_for_middling_signals(signal_factory):
    s = signal_factory(
        title="Just shipped v0.1",
        body="Took me a month.",
        score=3,
        reply_count=1,
        age_hours=12.0,
    )
    decision, bd = engage(s, {"thresholds": {"max_age_hours": 24}})
    assert decision in ("Maybe", "No"), bd


def test_score_breakdown_age_bonus_decays(signal_factory):
    fresh = signal_factory(age_hours=0.1)
    stale = signal_factory(age_hours=23.9)
    filters = {"thresholds": {"max_age_hours": 24}}
    assert score_breakdown(fresh, filters)["age_bonus"] > score_breakdown(stale, filters)["age_bonus"]


def test_score_breakdown_post_score_caps_at_five(signal_factory):
    capped = signal_factory(score=10_000)
    assert score_breakdown(capped)["post_score"] == 5.0


# ─── why ────────────────────────────────────────────────────────────────────

def test_why_includes_score_and_reply_count(signal_factory):
    s = signal_factory(score=7, reply_count=4)
    decision, bd = engage(s)
    out = why(s, decision, bd)
    assert "score 7" in out
    assert "4 replies" in out
    assert "total" in out


def test_why_flags_question(signal_factory):
    s = signal_factory(title="How do you validate your SaaS idea?", score=5)
    decision, bd = engage(s)
    out = why(s, decision, bd)
    assert "question" in out.lower()


# ─── analyze_rules ──────────────────────────────────────────────────────────

def test_analyze_rules_leaves_voice_fields_as_placeholder(signal_factory):
    """Critical: scanning must not fill voice fields — that's BYOK-only now."""
    result = analyze_rules(signal_factory())
    assert result.suggested_reply == VOICE_PLACEHOLDER
    assert result.suggested_post_comment == VOICE_PLACEHOLDER


def test_analyze_rules_populates_non_voice_fields(signal_factory):
    s = signal_factory(
        title="Looking for feedback on my tool",
        body="I built this small CLI for indie devs. Anyone tried something similar?",
        replies=[Reply(author="alice", body="Nice!", score=10)],
    )
    result = analyze_rules(s)
    assert result.summary
    assert result.summary != VOICE_PLACEHOLDER
    assert "alice" in result.coolest_comment
    assert result.engage in ("Yes", "Maybe", "No")
    assert result.why
