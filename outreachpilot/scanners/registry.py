"""Scanner registry — auto-discovers and registers available scanners."""

from __future__ import annotations

from outreachpilot.scanners.base import Scanner

_registry: dict[str, Scanner] = {}


def register(scanner: Scanner) -> None:
    _registry[scanner.name] = scanner


def get_scanner(name: str) -> Scanner | None:
    _ensure_loaded()
    return _registry.get(name)


def list_scanners() -> list[str]:
    _ensure_loaded()
    return list(_registry.keys())


_loaded = False


def _ensure_loaded():
    global _loaded
    if _loaded:
        return
    _loaded = True
    # Import built-in scanners to trigger registration
    from outreachpilot.scanners import reddit  # noqa: F401
