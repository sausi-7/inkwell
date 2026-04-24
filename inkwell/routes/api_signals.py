"""Signals API — list stored signals, generate voice drafts (BYOK), save ratings."""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from inkwell.analyzers.voice import draft_voice
from inkwell.config import DATA_DIR, load_personality
from inkwell.scanners.base import RawSignal
from inkwell.storage.signals import list_signal_dates, load_signals

logger = logging.getLogger(__name__)

router = APIRouter()

RATINGS_FILE = DATA_DIR / "feedback" / "ratings.json"


class DraftPayload(BaseModel):
    model: str
    regenerate: bool = False


class RatingPayload(BaseModel):
    rating: int = Field(ge=1, le=5)
    note: str = ""


def _find_signal(signal_id: str) -> tuple[Optional[dict], Optional[str]]:
    """Search recent signal files for the given id. Returns (signal, date_str)."""
    for date_str in list_signal_dates():
        for s in load_signals(date_str):
            if s.get("id") == signal_id or s.get("platform_id") == signal_id:
                return s, date_str
    return None, None


@router.get("/signals")
async def list_signals(date: str | None = None):
    """List signals for a given date (default today). Returns [] if none yet."""
    if date is None:
        date = datetime.date.today().isoformat()
    signals = load_signals(date)
    dates = list_signal_dates()
    return {"date": date, "count": len(signals), "signals": signals, "available_dates": dates}


@router.get("/signals/{signal_id}")
async def get_signal(signal_id: str):
    s, _ = _find_signal(signal_id)
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")
    return s


@router.post("/signals/{signal_id}/draft")
async def draft_signal(
    signal_id: str,
    payload: DraftPayload,
    x_llm_key: str | None = Header(default=None),
):
    """Generate a voice draft for one signal. Key comes from browser localStorage.

    Drafts are cached inline on the stored signal's `drafts` field so a refresh
    or second visit doesn't re-bill the user. Pass regenerate=true to override.
    """
    s, date_str = _find_signal(signal_id)
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")

    cached = s.get("drafts")
    if cached and not payload.regenerate:
        return {"drafts": cached, "cached": True, "model": s.get("draft_model")}

    model = payload.model.strip()
    if not model:
        raise HTTPException(status_code=400, detail="Model is required")
    if not x_llm_key and not model.startswith("ollama"):
        raise HTTPException(
            status_code=400,
            detail="No API key. Set one in Settings (stored in your browser only).",
        )

    signal = RawSignal(
        platform=s.get("platform", "reddit"),
        platform_id=s.get("platform_id", ""),
        url=s.get("url", ""),
        title=s.get("title", ""),
        body=s.get("body", ""),
        author=s.get("author", ""),
        score=s.get("score", 0),
        reply_count=s.get("reply_count", 0),
        created_utc=s.get("created_utc", 0),
        metadata={"subreddit": s.get("subreddit", "")},
    )
    coolest = s.get("analysis", {}).get("coolest_comment", "no cool comments")
    personality = load_personality()

    drafts = draft_voice(
        signal, personality, coolest,
        model=model, api_key=x_llm_key,
    )
    if not drafts:
        raise HTTPException(status_code=502, detail="LLM call failed — see server logs")

    # Persist drafts back into the stored signal file so the UI can show them
    # on reload without re-billing.
    _update_stored_signal(date_str, signal_id, {"drafts": drafts, "draft_model": model})

    return {"drafts": drafts, "cached": False, "model": model}


def _update_stored_signal(date_str: str, signal_id: str, patch: dict) -> None:
    filepath = DATA_DIR / "signals" / f"{date_str}.json"
    if not filepath.exists():
        return
    with open(filepath) as f:
        signals = json.load(f)
    for s in signals:
        if s.get("id") == signal_id or s.get("platform_id") == signal_id:
            s.update(patch)
            break
    with open(filepath, "w") as f:
        json.dump(signals, f, indent=2, default=str)


@router.post("/signals/{signal_id}/rate")
async def rate_signal(signal_id: str, payload: RatingPayload):
    RATINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ratings = []
    if RATINGS_FILE.exists():
        try:
            with open(RATINGS_FILE) as f:
                ratings = json.load(f)
        except json.JSONDecodeError:
            ratings = []
    ratings = [r for r in ratings if r.get("signal_id") != signal_id]
    ratings.append({
        "signal_id": signal_id,
        "rating": payload.rating,
        "note": payload.note,
        "ts": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    })
    with open(RATINGS_FILE, "w") as f:
        json.dump(ratings, f, indent=2)
    return {"ok": True}


@router.get("/signals/{signal_id}/rating")
async def get_rating(signal_id: str):
    if not RATINGS_FILE.exists():
        return {"rating": None}
    try:
        with open(RATINGS_FILE) as f:
            ratings = json.load(f)
    except json.JSONDecodeError:
        return {"rating": None}
    for r in ratings:
        if r.get("signal_id") == signal_id:
            return {"rating": r.get("rating"), "note": r.get("note", ""), "ts": r.get("ts")}
    return {"rating": None}


# suppress lint: Path import used only for DATA_DIR below
_ = Path
