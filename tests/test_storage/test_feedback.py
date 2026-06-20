"""Tests for inkwell.storage.feedback — ratings and learned preferences.

compute_preference_weights joins ratings back to stored signals and turns the
user's taste into a mean-centered, clamped nudge for the free heuristic. These
tests pin the cold-start no-op, the join, and the centering/clamping behavior."""

import json

import pytest

from inkwell.storage import feedback as feedback_module
from inkwell.storage import signals as signals_module


@pytest.fixture
def isolated_storage(tmp_path, monkeypatch):
    """Redirect both the feedback file and the signals dir to tmp paths."""
    feedback_file = tmp_path / "feedback" / "ratings.json"
    signals_dir = tmp_path / "signals"
    signals_dir.mkdir(parents=True)
    monkeypatch.setattr(feedback_module, "FEEDBACK_FILE", feedback_file)
    monkeypatch.setattr(signals_module, "SIGNALS_DIR", signals_dir)
    return tmp_path


def _write_signals(date_str: str, signals: list[dict]):
    signals_module.save_signals(signals, date_str=date_str)


def _rate(signal_id: str, rating: int):
    feedback_module.add_feedback(signal_id, rating)


def test_cold_start_returns_empty_weights(isolated_storage):
    """Below MIN_RATINGS_TO_LEARN, scoring must be unchanged (empty maps)."""
    _write_signals("2026-06-01", [{"id": "reddit_a", "subreddit": "SaaS", "title": "hi"}])
    _rate("reddit_a", 5)
    w = feedback_module.compute_preference_weights()
    assert w["subreddits"] == {}
    assert w["keywords"] == {}
    assert w["n_ratings"] == 1


def test_ignores_ratings_with_no_matching_signal(isolated_storage):
    _rate("ghost", 5)
    w = feedback_module.compute_preference_weights()
    assert w["n_ratings"] == 0


def test_liked_subreddit_outweighs_disliked(isolated_storage):
    """5★ posts in one sub and 1★ in another → positive vs negative weight."""
    _write_signals("2026-06-01", [
        {"id": f"good{i}", "subreddit": "SaaS", "title": "build tool"} for i in range(3)
    ] + [
        {"id": f"bad{i}", "subreddit": "crypto", "title": "airdrop token"} for i in range(3)
    ])
    for i in range(3):
        _rate(f"good{i}", 5)
        _rate(f"bad{i}", 1)

    w = feedback_module.compute_preference_weights()
    assert w["n_ratings"] == 6
    assert w["subreddits"]["saas"] > 0
    assert w["subreddits"]["crypto"] < 0


def test_weights_are_mean_centered(isolated_storage):
    """Two subs rated equally high should center to ~0, not both strongly positive."""
    _write_signals("2026-06-01", [
        {"id": f"a{i}", "subreddit": "SaaS", "title": "x"} for i in range(3)
    ] + [
        {"id": f"b{i}", "subreddit": "Entrepreneur", "title": "y"} for i in range(3)
    ])
    for i in range(3):
        _rate(f"a{i}", 5)
        _rate(f"b{i}", 5)

    w = feedback_module.compute_preference_weights()
    assert abs(w["subreddits"]["saas"]) < 0.01
    assert abs(w["subreddits"]["entrepreneur"]) < 0.01


def test_weights_clamped_to_max_abs(isolated_storage):
    _write_signals("2026-06-01", [
        {"id": f"a{i}", "subreddit": "SaaS", "title": "x"} for i in range(3)
    ] + [
        {"id": f"b{i}", "subreddit": "crypto", "title": "y"} for i in range(3)
    ])
    for i in range(3):
        _rate(f"a{i}", 5)
        _rate(f"b{i}", 1)

    w = feedback_module.compute_preference_weights(max_abs=0.5)
    assert all(abs(v) <= 0.5 for v in w["subreddits"].values())


def test_keyword_weights_extracted_from_title(isolated_storage):
    _write_signals("2026-06-01", [
        {"id": f"a{i}", "subreddit": "SaaS", "title": "deployment pipeline help"}
        for i in range(3)
    ] + [
        {"id": f"b{i}", "subreddit": "crypto", "title": "free airdrop tokens"}
        for i in range(3)
    ])
    for i in range(3):
        _rate(f"a{i}", 5)
        _rate(f"b{i}", 1)

    w = feedback_module.compute_preference_weights()
    assert w["keywords"]["deployment"] > w["keywords"]["airdrop"]


def test_add_feedback_clamps_rating_range():
    """Existing behavior guard: ratings are bounded 1..5."""
    assert feedback_module._rating_to_value(99) == 1.0
    assert feedback_module._rating_to_value(-5) == -1.0
    assert feedback_module._rating_to_value(3) == 0.0


def test_round_trips_on_disk(isolated_storage):
    _write_signals("2026-06-01", [{"id": "x", "subreddit": "SaaS", "title": "hi"}])
    _rate("x", 4)
    on_disk = json.loads((isolated_storage / "feedback" / "ratings.json").read_text())
    assert on_disk[0]["signal_id"] == "x"
    assert on_disk[0]["rating"] == 4
