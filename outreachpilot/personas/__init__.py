"""Persona/voice engine for outreach tone matching."""

from outreachpilot.personas.loader import load_persona
from outreachpilot.personas.prompt_builder import build_personality_block

__all__ = ["load_persona", "build_personality_block"]
