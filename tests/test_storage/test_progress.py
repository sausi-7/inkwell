"""Tests for inkwell.storage.progress."""

import datetime
import json

import pytest

from inkwell.storage import progress as progress_module


@pytest.fixture
def isolated_progress_file(tmp_path, monkeypatch):
    """Redirect the progress file to a tmp path so tests don't touch real data/."""
    path = tmp_path / "progress.json"
    monkeypatch.setattr(progress_module, "PROGRESS_FILE", path)
    return path


def test_fresh_load_returns_today_with_empty_sets(isolated_progress_file):
    p = progress_module.load_progress()
    assert p["date"] == datetime.date.today().isoformat()
    assert p["completed_subs"] == set()
    assert p["processed_ids"] == set()
    assert p["total_written"] == 0


def test_save_then_load_round_trips_same_day(isolated_progress_file):
    progress_module.save_progress({
        "date": datetime.date.today().isoformat(),
        "completed_subs": {"SaaS", "Entrepreneur"},
        "processed_ids": {"abc", "def"},
        "total_written": 5,
    })
    loaded = progress_module.load_progress()
    assert loaded["completed_subs"] == {"SaaS", "Entrepreneur"}
    assert loaded["processed_ids"] == {"abc", "def"}
    assert loaded["total_written"] == 5


def test_save_serializes_sets_as_lists(isolated_progress_file):
    """JSON can't serialize sets — save_progress must convert them."""
    progress_module.save_progress({
        "date": "2026-01-01",
        "completed_subs": {"SaaS"},
        "processed_ids": {"abc"},
        "total_written": 1,
    })
    on_disk = json.loads(isolated_progress_file.read_text())
    assert isinstance(on_disk["completed_subreddits"], list)
    assert isinstance(on_disk["processed_post_ids"], list)


def test_stale_progress_resets_on_new_day(isolated_progress_file):
    """If saved progress is from a previous day, load_progress starts fresh."""
    isolated_progress_file.write_text(json.dumps({
        "date": "2020-01-01",
        "completed_subreddits": ["SaaS"],
        "processed_post_ids": ["abc"],
        "total_written": 42,
    }))
    loaded = progress_module.load_progress()
    assert loaded["date"] == datetime.date.today().isoformat()
    assert loaded["completed_subs"] == set()
    assert loaded["processed_ids"] == set()
    assert loaded["total_written"] == 0
