"""Tests for inkwell.scanners.hackernews — mocked, no real network.

The HN scanner proves the Scanner protocol generalizes beyond Reddit: same
RawSignal shape, same two-phase (fetch → filter → hydrate) contract, same emit
threading. fetch_json is patched so these stay offline and deterministic."""

from __future__ import annotations

from unittest.mock import patch

from inkwell.scanners import hackernews as hn_module
from inkwell.scanners.base import RawSignal, Scanner
from inkwell.scanners.hackernews import HackerNewsScanner, _strip_html


def _search_response(*hits):
    return {"hits": list(hits)}


def _hit(object_id, title, **kw):
    base = {
        "objectID": object_id,
        "title": title,
        "author": "pg",
        "points": 10,
        "num_comments": 3,
        "created_at_i": 1_700_000_000,
        "url": f"https://example.com/{object_id}",
    }
    base.update(kw)
    return base


def _item_response(*comments):
    return {"children": list(comments)}


def _comment(cid, author, text, points=5):
    return {"id": cid, "author": author, "text": text, "points": points}


# ─── protocol conformance ────────────────────────────────────────────────────

def test_satisfies_scanner_protocol():
    assert isinstance(HackerNewsScanner(), Scanner)


def test_registered_in_registry():
    from inkwell.scanners import registry
    assert "hackernews" in registry.list_scanners()
    assert registry.get_scanner("hackernews") is not None


# ─── search → signal mapping ─────────────────────────────────────────────────

@patch.object(hn_module, "fetch_json")
def test_scan_maps_hits_to_signals(mock_fetch):
    mock_fetch.side_effect = [
        _search_response(_hit("1", "Show HN: my tool")),
        _item_response(_comment("c1", "alice", "nice work")),
    ]
    signals = HackerNewsScanner().scan(["show hn"], max_age_hours=24)
    assert len(signals) == 1
    s = signals[0]
    assert isinstance(s, RawSignal)
    assert s.platform == "hackernews"
    assert s.platform_id == "1"
    assert s.title == "Show HN: my tool"
    assert s.score == 10
    assert s.metadata["subreddit"] == "hn:show hn"  # key heuristics/exports expect
    assert s.replies[0].author == "alice"


@patch.object(hn_module, "fetch_json")
def test_external_url_preferred_else_hn_thread(mock_fetch):
    mock_fetch.side_effect = [
        _search_response(_hit("9", "Ask HN: thoughts?", url=None)),
        _item_response(),
    ]
    s = HackerNewsScanner().scan(["ask hn"], max_age_hours=24)[0]
    assert s.url == "https://news.ycombinator.com/item?id=9"


@patch.object(hn_module, "fetch_json")
def test_dedups_same_story_across_queries(mock_fetch):
    mock_fetch.side_effect = [
        _search_response(_hit("5", "dup story")),  # query 1 search
        _item_response(),                           # query 1 comments
        _search_response(_hit("5", "dup story")),  # query 2 search (same id)
    ]
    signals = HackerNewsScanner().scan(["a", "b"], max_age_hours=24)
    assert len(signals) == 1  # second occurrence skipped before comment fetch


@patch.object(hn_module, "fetch_json")
def test_fetch_comments_false_skips_hydration(mock_fetch):
    mock_fetch.side_effect = [_search_response(_hit("1", "t"))]
    signals = HackerNewsScanner().scan(["x"], max_age_hours=24, fetch_comments=False)
    assert signals[0].replies == []
    assert mock_fetch.call_count == 1  # no item endpoint call


@patch.object(hn_module, "fetch_json")
def test_empty_search_returns_no_signals(mock_fetch):
    mock_fetch.return_value = {"hits": []}
    assert HackerNewsScanner().scan(["nothing"], max_age_hours=24) == []


# ─── comment parsing ─────────────────────────────────────────────────────────

@patch.object(hn_module, "fetch_json")
def test_skips_deleted_comments_and_sorts_by_score(mock_fetch):
    mock_fetch.side_effect = [
        _search_response(_hit("1", "t")),
        _item_response(
            _comment("a", "low", "meh", points=1),
            {"id": "b", "author": None, "text": None},   # deleted
            _comment("c", "high", "great insight", points=40),
        ),
    ]
    s = HackerNewsScanner().scan(["x"], max_age_hours=24)[0]
    assert [r.author for r in s.replies] == ["high", "low"]


def test_strip_html_unescapes_and_removes_tags():
    raw = "<p>Hello &amp; <a href=\"x\">world</a></p>"
    assert _strip_html(raw) == "Hello & world"


# ─── hydrate_comments (two-phase) ────────────────────────────────────────────

@patch.object(hn_module, "fetch_json")
def test_hydrate_comments_fills_replies(mock_fetch):
    mock_fetch.return_value = _item_response(_comment("c1", "bob", "hi"))
    sig = RawSignal(
        platform="hackernews", platform_id="42", url="", title="t", body="",
        author="x", score=0, reply_count=0, created_utc=0,
    )
    out = HackerNewsScanner().hydrate_comments(sig)
    assert out is sig
    assert sig.replies[0].author == "bob"
