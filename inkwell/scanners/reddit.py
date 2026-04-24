"""Reddit scanner — fetches posts and comments from subreddits."""

import logging
import time

from inkwell.scanners.base import RawSignal, Reply, fetch_json
from inkwell.scanners import registry
from inkwell.config import REDDIT_HEADERS, REDDIT_SLEEP

logger = logging.getLogger(__name__)


class RedditScanner:
    name = "reddit"

    def scan(
        self,
        targets: list[str],
        max_age_hours: int = 24,
        emit=None,
        fetch_comments: bool = True,
    ) -> list[RawSignal]:
        """Scan subreddits for recent posts.

        When `fetch_comments=False`, returns signals with empty `replies` —
        useful when the caller wants to filter first and only hydrate
        comments for posts that survive the filter. This turns what used to
        be ~200s of serial comment fetches into ~20s by skipping the
        90%+ of posts that fail rule filters.

        `emit`, if provided, is threaded to fetch_json so the SSE stream
        surfaces rate-limit / forbidden / network events in real time.
        """
        signals = []
        for subreddit in targets:
            posts = self._fetch_posts(subreddit, max_age_hours, emit=emit)
            if emit:
                emit({
                    "kind": "posts_fetched",
                    "subreddit": subreddit,
                    "count": len(posts),
                })
            for post in posts:
                replies = (
                    self._fetch_comments(post["permalink"], emit=emit)
                    if fetch_comments else []
                )
                signal = RawSignal(
                    platform="reddit",
                    platform_id=post["id"],
                    url=post["url"],
                    title=post["title"],
                    body=post["selftext"],
                    author=post.get("author", ""),
                    score=post["score"],
                    reply_count=post["num_comments"],
                    created_utc=post["created_utc"],
                    status=post["status"],
                    metadata={
                        "subreddit": subreddit,
                        "flair": post["flair"],
                        "is_self": post["is_self"],
                        "permalink": post["permalink"],
                    },
                    replies=replies,
                )
                signals.append(signal)
        return signals

    def hydrate_comments(self, signal: RawSignal, emit=None) -> RawSignal:
        """Populate `signal.replies` in-place by fetching its comment thread.

        Intended for the two-phase scan flow (fetch posts → filter → hydrate
        survivors). Returns the same signal for chaining.
        """
        permalink = signal.metadata.get("permalink", "")
        if permalink:
            signal.replies = self._fetch_comments(permalink, emit=emit)
        return signal

    def _fetch_posts(self, subreddit: str, max_age_hours: int, emit=None) -> list[dict]:
        """Fetch posts from the last N hours in a subreddit."""
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=100"
        data = fetch_json(url, headers=REDDIT_HEADERS, emit=emit)
        time.sleep(REDDIT_SLEEP)

        if not data or "data" not in data:
            return []

        now = time.time()
        cutoff = now - (max_age_hours * 3600)
        posts = []

        for child in data["data"].get("children", []):
            post = child.get("data", {})
            created = post.get("created_utc", 0)
            if created < cutoff:
                continue

            if post.get("removed_by_category"):
                status = "blocked"
            elif post.get("archived"):
                status = "archived"
            elif post.get("locked"):
                status = "inactive"
            else:
                status = "active"

            posts.append({
                "id": post.get("id", ""),
                "title": post.get("title", ""),
                "selftext": post.get("selftext", "")[:2000],
                "url": f"https://www.reddit.com{post.get('permalink', '')}",
                "permalink": post.get("permalink", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "created_utc": created,
                "status": status,
                "flair": post.get("link_flair_text", "") or "",
                "is_self": post.get("is_self", False),
                "author": post.get("author", ""),
            })

        logger.info("r/%s: fetched %d posts (last %dh)", subreddit, len(posts), max_age_hours)
        return posts

    def _fetch_comments(self, permalink: str, emit=None) -> list[Reply]:
        """Fetch top-level comments for a post."""
        url = f"https://www.reddit.com{permalink}.json?limit=25"
        data = fetch_json(url, headers=REDDIT_HEADERS, emit=emit)
        time.sleep(REDDIT_SLEEP)

        if not data or not isinstance(data, list) or len(data) < 2:
            return []

        comments = []
        for child in data[1].get("data", {}).get("children", []):
            if child.get("kind") != "t1":
                continue
            c = child.get("data", {})
            body = c.get("body", "")
            if body in ("[deleted]", "[removed]", ""):
                continue
            comments.append(Reply(
                author=c.get("author", "[deleted]"),
                body=body[:500],
                score=c.get("score", 0),
                platform_id=c.get("id", ""),
            ))

        comments.sort(key=lambda x: x.score, reverse=True)
        return comments[:10]


# Auto-register
registry.register(RedditScanner())
