"""CSV exporter — writes signals to a CSV file."""

import csv
import logging
from pathlib import Path

from inkwell.config import DATA_DIR, COLUMNS

logger = logging.getLogger(__name__)


class CSVExporter:
    name = "csv"

    def export(self, rows: list[dict], config: dict | None = None) -> Path:
        """Export rows to a CSV file. Returns the file path."""
        import datetime
        filename = (config or {}).get("filename", f"outreach_{datetime.date.today().isoformat()}.csv")
        filepath = DATA_DIR / filename

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        logger.info("Exported %d rows to %s", len(rows), filepath)
        return filepath
