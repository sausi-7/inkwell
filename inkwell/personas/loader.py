"""Load persona profiles from YAML config."""

from inkwell.config import load_personality


def load_persona(filename: str = "personality.yml") -> dict:
    """Load a persona profile from config."""
    return load_personality(filename)
