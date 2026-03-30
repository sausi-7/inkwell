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


def fetch_json(url: str, headers: dict, retries: int = 3, sleep_between: float = 2.0) -> dict | None:
    """Fetch JSON from a URL with retries and rate-limit handling."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 429:
                wait = (attempt + 1) * 5
                logger.warning("Rate limited, waiting %ds...", wait)
                time.sleep(wait)
                continue
            if resp.status_code == 403:
                logger.warning("403 Forbidden for %s", url)
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                logger.warning("Request error (%s), retrying...", e)
                time.sleep(3)
            else:
                logger.error("Failed after %d attempts: %s", retries, e)
                return None
    return None
