"""Profile (persona) CRUD — reads/writes config/personality.yml."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from inkwell.config import load_personality, write_yaml
from inkwell.personas.prompt_builder import build_personality_block

logger = logging.getLogger(__name__)

router = APIRouter()


class Tone(BaseModel):
    style: str = ""
    humor: str = ""
    formality: str = ""


class Profile(BaseModel):
    name: str = ""
    bio: str = ""
    interests: list[str] = Field(default_factory=list)
    expertise: list[str] = Field(default_factory=list)
    tone: Tone = Field(default_factory=Tone)
    dos: list[str] = Field(default_factory=list)
    donts: list[str] = Field(default_factory=list)
    example_comments: list[str] = Field(default_factory=list)


def _is_meaningfully_configured(p: dict) -> bool:
    """Did the user actually edit this, or is it the default scaffold?"""
    if not p:
        return False
    # Require at least bio + one example to count as "set up".
    return bool(p.get("bio", "").strip()) and bool(p.get("example_comments"))


@router.get("/profile")
async def get_profile():
    p = load_personality()
    tone = p.get("tone", {}) or {}
    prof = Profile(
        name=p.get("name", ""),
        bio=(p.get("bio") or "").strip(),
        interests=p.get("interests") or [],
        expertise=p.get("expertise") or [],
        tone=Tone(
            style=tone.get("style", ""),
            humor=tone.get("humor", ""),
            formality=tone.get("formality", ""),
        ),
        dos=p.get("dos") or [],
        donts=p.get("donts") or [],
        example_comments=[(c or "").strip() for c in (p.get("example_comments") or [])],
    )
    return {
        "profile": prof.model_dump(),
        "configured": _is_meaningfully_configured(p),
        "prompt_preview": build_personality_block(prof.model_dump()),
    }


@router.post("/profile")
async def save_profile(profile: Profile):
    data = profile.model_dump()
    # Drop the empty tone sub-object if all three fields are blank — keeps YAML tidy.
    if not any(data["tone"].values()):
        data["tone"] = {}
    try:
        path = write_yaml("personality.yml", data)
    except Exception as e:
        logger.exception("Failed to write personality.yml")
        raise HTTPException(status_code=500, detail=f"Write failed: {e}")
    return {
        "ok": True,
        "path": str(path),
        "prompt_preview": build_personality_block(data),
    }
