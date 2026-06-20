"""Hacker News scanner — searches HN for recent stories matching topic queries.

Uses the public Algolia HN Search API (no auth, no key):
  - search:        https://hn.algolia.com/api/v1/search_by_date?query=...&tags=story
  - item/comments: https://hn.algolia.com/api/v1/items/<id>

`targets` here are search queries/topics (e.g. "show hn", "feedback", a niche
keyword) rather than subreddits — the Scanner protocol is platform-agnostic
about what a "target" means. Each query is filtered to the last N hours via
Algolia's numericFilters on created_at_i.
"""

from __future__ import annotations

import logging
import time

from inkwell.scanners import registry
from inkwell.scanners.base import RawSignal, Reply, fetch_json

logger = logging.getLogger(__name__)

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_ITEM_URL = "https://hn.algolia.com/api/v1/items"
HN_HEADERS = {"User-Agent": "inkwell/0.1 (+https://github.com/)"}
HN_SLEEP = 1.0  # be polite to the public API between calls

# How many comments to hydrate per story and the per-story search page size.
MAX_COMMENTS = 10
SEARCH_HITS = 50


class HackerNewsScanner:
    name = "hackernews"

    def scan(
        self,
        targets: list[str],
        max_age_hours: int = 24,
        emit=None,
        fetch_comments: bool = True,
    ) -> list[RawSignal]:
        """Search HN for recent stories matching each query in `targets`.

        Mirrors RedditScanner's two-phase shape: when `fetch_comments=False`,
        returns signals with empty `replies` so the caller can filter first and
        only hydrate survivors via `hydrate_comments`. `emit` is threaded to
        fetch_json so the SSE scan stream surfaces rate-limit / network events.
        """
        cutoff = int(time.time()) - max_age_hours * 3600
        signals: list[RawSignal] = []
        seen_ids: set[str] = set()

        for query in targets:
            stories = self._search(query, cutoff, emit=emit)
            if emit:
                emit({"kind": "posts_fetched", "subreddit": query, "count": len(stories)})
            for story in stories:
                if story["id"] in seen_ids:  # same story can match several queries
                    continue
                seen_ids.add(story["id"])
                replies = (
                    self._fetch_comments(story["id"], emit=emit) if fetch_comments else []
                )
                signals.append(self._to_signal(story, query, replies))
        return signals

    def hydrate_comments(self, signal: RawSignal, emit=None) -> RawSignal:
        """Populate `signal.replies` in-place for the two-phase scan flow."""
        signal.replies = self._fetch_comments(signal.platform_id, emit=emit)
        return signal

    # ─── internals ──────────────────────────────────────────────────────────

    def _to_signal(self, story: dict, query: str, replies: list[Reply]) -> RawSignal:
        return RawSignal(
            platform="hackernews",
            platform_id=story["id"],
            url=story["url"],
            title=story["title"],
            body=story["body"],
            author=story["author"],
            score=story["points"],
            reply_count=story["num_comments"],
            created_utc=story["created_utc"],
            status="active",
            metadata={
                "subreddit": f"hn:{query}",  # keep the key heuristics/exports expect
                "query": query,
                "hn_url": f"https://news.ycombinator.com/item?id={story['id']}",
            },
            replies=replies,
        )

    def _search(self, query: str, cutoff: int, emit=None) -> list[dict]:
        """Search HN stories created after `cutoff` (unix seconds), newest first."""
        url = (
            f"{HN_SEARCH_URL}?query={requests_quote(query)}&tags=story"
            f"&numericFilters=created_at_i>{cutoff}&hitsPerPage={SEARCH_HITS}"
        )
        data = fetch_json(url, headers=HN_HEADERS, emit=emit)
        time.sleep(HN_SLEEP)
        if not data or "hits" not in data:
            return []

        stories = []
        for hit in data["hits"]:
            object_id = str(hit.get("objectID", ""))
            if not object_id:
                continue
            # A story's own URL (external link) if present, else the HN thread.
            external = hit.get("url")
            hn_thread = f"https://news.ycombinator.com/item?id={object_id}"
            stories.append({
                "id": object_id,
                "title": hit.get("title") or hit.get("story_title") or "",
                "body": (hit.get("story_text") or "")[:2000],
                "url": external or hn_thread,
                "author": hit.get("author", ""),
                "points": hit.get("points") or 0,
                "num_comments": hit.get("num_comments") or 0,
                "created_utc": float(hit.get("created_at_i", 0)),
            })

        logger.info("hn '%s': fetched %d stories", query, len(stories))
        return stories

    def _fetch_comments(self, story_id: str, emit=None) -> list[Reply]:
        """Fetch top comments for a story via the Algolia item endpoint."""
        data = fetch_json(f"{HN_ITEM_URL}/{story_id}", headers=HN_HEADERS, emit=emit)
        time.sleep(HN_SLEEP)
        if not data:
            return []

        replies: list[Reply] = []
        for child in data.get("children", []) or []:
            text = (child.get("text") or "").strip()
            author = child.get("author")
            if not text or not author:  # deleted/dead comments have null author/text
                continue
            replies.append(Reply(
                author=author,
                body=_strip_html(text)[:500],
                score=child.get("points") or 0,
                platform_id=str(child.get("id", "")),
            ))

        # Algolia points are often null on comments; keep insertion (≈ thread) order
        # but surface higher-scored ones first when scores exist.
        replies.sort(key=lambda r: r.score, reverse=True)
        return replies[:MAX_COMMENTS]


def requests_quote(s: str) -> str:
    from urllib.parse import quote_plus
    return quote_plus(s)


def _strip_html(text: str) -> str:
    """HN comment text is HTML-ish (<p>, <a>, entities). Make it plain-ish."""
    import html
    import re
    text = re.sub(r"<p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


# Auto-register
registry.register(HackerNewsScanner())
