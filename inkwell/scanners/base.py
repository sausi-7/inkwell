"""Base scanner protocol and data models."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import requests

logger = logging.getLogger(__name__)


@dataclass
class Reply:
    """A comment/reply on a signal."""
    author: str
    body: str
    score: int
    platform_id: str = ""


@dataclass
class RawSignal:
    """Platform-agnostic representation of a discovered signal."""
    platform: str
    platform_id: str
    url: str
    title: str
    body: str
    author: str
    score: int
    reply_count: int
    created_utc: float
    metadata: dict = field(default_factory=dict)
    replies: list[Reply] = field(default_factory=list)
    status: str = "active"


@runtime_checkable
class Scanner(Protocol):
    """Protocol that all platform scanners must implement."""
    name: str

    def scan(self, targets: list[str], max_age_hours: int = 24) -> list[RawSignal]:
        """Scan targets (subreddits, topics, etc.) and return signals."""
        ...


def fetch_json(
    url: str,
    headers: dict,
    retries: int = 3,
    sleep_between: float = 2.0,
    emit=None,
) -> dict | None:
    """Fetch JSON from a URL with retries and rate-limit handling.

    `emit`, if provided, is called with a JSON-serializable dict for visible
    events (rate_limit, forbidden, retry_error) so the SSE scan stream can
    surface them to the UI instead of the fetch going silent during backoff.
    """
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 429:
                wait = (attempt + 1) * 5
                logger.warning("Rate limited, waiting %ds...", wait)
                if emit:
                    emit({
                        "kind": "rate_limit",
                        "url": url,
                        "wait_s": wait,
                        "attempt": attempt + 1,
                        "max_attempts": retries,
                    })
                time.sleep(wait)
                continue
            if resp.status_code == 403:
                logger.warning("403 Forbidden for %s", url)
                if emit:
                    emit({"kind": "forbidden", "url": url})
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                logger.warning("Request error (%s), retrying...", e)
                if emit:
                    emit({
                        "kind": "retry_error",
                        "url": url,
                        "error": str(e),
                        "attempt": attempt + 1,
                        "max_attempts": retries,
                    })
                time.sleep(3)
            else:
                logger.error("Failed after %d attempts: %s", retries, e)
                if emit:
                    emit({"kind": "fetch_failed", "url": url, "error": str(e)})
                return None
    return None
