"""Shared fixtures for the test suite."""

from __future__ import annotations

import time

import pytest

from outreachpilot.scanners.base import RawSignal, Reply


def make_signal(
    *,
    platform_id: str = "abc123",
    title: str = "Looking for feedback on my SaaS idea",
    body: str = "I'm building a tool that helps indie hackers.",
    score: int = 10,
    reply_count: int = 3,
    status: str = "active",
    flair: str = "",
    is_self: bool = True,
    subreddit: str = "SaaS",
    age_hours: float = 1.0,
    replies: list[Reply] | None = None,
) -> RawSignal:
    """Build a RawSignal with sensible defaults — override just what the test cares about."""
    return RawSignal(
        platform="reddit",
        platform_id=platform_id,
        url=f"https://www.reddit.com/r/{subreddit}/comments/{platform_id}/",
        title=title,
        body=body,
        author="someuser",
        score=score,
        reply_count=reply_count,
        created_utc=time.time() - age_hours * 3600,
        status=status,
        metadata={"subreddit": subreddit, "flair": flair, "is_self": is_self},
        replies=replies or [],
    )


@pytest.fixture
def signal_factory():
    """Factory fixture so tests can build custom RawSignals without repeating boilerplate."""
    return make_signal
