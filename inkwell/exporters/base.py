"""Base exporter protocol."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Exporter(Protocol):
    """Protocol that all exporters must implement."""
    name: str

    def export(self, rows: list[dict], config: dict | None = None) -> None:
        """Export rows of data."""
        ...
