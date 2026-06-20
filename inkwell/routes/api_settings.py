"""Settings routes — filters, subreddits, output prefs, and connection probes.

LLM key is NEVER stored here. Key lives in browser localStorage and arrives
on the X-LLM-Key header when the client asks us to probe a provider.
"""

from __future__ import annotations

import logging
from pathlib import Path

import litellm
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from inkwell.config import (
    ROOT_DIR,
    SPREADSHEET_ID,
    TOKEN_FILE,
    load_app_prefs,
    load_filters,
    load_subreddits,
    load_yaml,
    write_yaml,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── schemas ────────────────────────────────────────────────────────────────

class AppPrefs(BaseModel):
    output_target: str = "both"  # "sheets" | "csv" | "both" | "sheets_only"


class SettingsPayload(BaseModel):
    filters: dict = Field(default_factory=dict)
    subreddits: list[str] = Field(default_factory=list)
    app_prefs: AppPrefs = Field(default_factory=AppPrefs)


class LLMTestPayload(BaseModel):
    model: str


# ─── GET / POST settings ────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings():
    try:
        subs = load_subreddits()
    except Exception:
        subs = []
    return {
        "filters": load_filters() or {},
        "subreddits": subs,
        "app_prefs": load_app_prefs() or {"output_target": "both"},
        "sheets": {
            "spreadsheet_id": SPREADSHEET_ID,
            "token_present": Path(TOKEN_FILE).exists(),
        },
    }


@router.post("/settings")
async def save_settings(payload: SettingsPayload):
    try:
        write_yaml("filters.yml", payload.filters or {})
        write_yaml("subreddits.yml", payload.subreddits or [])
        write_yaml("app.yml", payload.app_prefs.model_dump())
    except Exception as e:
        logger.exception("Failed to save settings")
        raise HTTPException(status_code=500, detail=f"Write failed: {e}")
    return {"ok": True}


# ─── learned preferences (read-only) ────────────────────────────────────────

@router.get("/settings/learned")
async def get_learned():
    """Surface what the tool has learned from the user's ratings.

    Read-only — returns the strongest boosted/penalized subreddits and keywords
    so the learned-preference loop is visible, not invisible magic. Empty until
    enough ratings exist (cold start).
    """
    from inkwell.storage.feedback import MIN_RATINGS_TO_LEARN, compute_preference_weights

    weights = compute_preference_weights()

    def _top(d: dict, n: int = 8) -> list[dict]:
        items = sorted(d.items(), key=lambda kv: abs(kv[1]), reverse=True)
        return [{"name": k, "weight": v} for k, v in items[:n] if v]

    return {
        "active": bool(weights["subreddits"] or weights["keywords"]),
        "n_ratings": weights["n_ratings"],
        "min_ratings": MIN_RATINGS_TO_LEARN,
        "subreddits": _top(weights["subreddits"]),
        "keywords": _top(weights["keywords"]),
    }


# ─── connection probes ─────────────────────────────────────────────────────

@router.post("/settings/test-sheets")
async def test_sheets():
    """Verify Google Sheets auth by loading the saved token and reading metadata."""
    if not SPREADSHEET_ID:
        return {"ok": False, "detail": "SPREADSHEET_ID not set in .env"}
    if not Path(TOKEN_FILE).exists():
        return {"ok": False, "detail": "Not authenticated — run `inkwell scan` once to auth"}
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        from inkwell.config import SCOPES
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        return {
            "ok": True,
            "title": meta.get("properties", {}).get("title", "(untitled)"),
            "sheet_count": len(meta.get("sheets", [])),
        }
    except Exception as e:
        return {"ok": False, "detail": str(e)}


@router.post("/settings/test-llm")
async def test_llm(payload: LLMTestPayload, x_llm_key: str | None = Header(default=None)):
    """Send a 1-token probe with the user's key + model. Does not log the key."""
    model = payload.model.strip()
    if not model:
        return {"ok": False, "detail": "Model is required"}

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
    }
    if x_llm_key:
        kwargs["api_key"] = x_llm_key
    try:
        litellm.completion(**kwargs)
        return {"ok": True, "detail": f"{model} responded"}
    except Exception as e:
        # Scrub any accidental key echoes — never log or return the key.
        msg = str(e)
        if x_llm_key and x_llm_key in msg:
            msg = msg.replace(x_llm_key, "[redacted]")
        return {"ok": False, "detail": msg[:400]}


# ─── default scaffolds (for first-run "reset" behavior, not wired yet) ──────

def _default_filters() -> dict:
    return load_yaml("filters.yml") or {}


def _default_subreddits() -> list[str]:
    try:
        return load_subreddits()
    except Exception:
        return []


_ = ROOT_DIR  # silence unused import warnings; we reference it for side effects via config
