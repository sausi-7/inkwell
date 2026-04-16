"""Google Sheets exporter — writes signals to a daily tab."""

import json
import logging

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from outreachpilot.config import (
    SCOPES, TOKEN_FILE, OAUTH_CLIENT_CONFIG, SPREADSHEET_ID, COLUMNS, ROOT_DIR,
)

logger = logging.getLogger(__name__)


class GoogleSheetsExporter:
    name = "google_sheets"

    def __init__(self):
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(OAUTH_CLIENT_CONFIG, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())

        self._service = build("sheets", "v4", credentials=creds)
        return self._service

    def get_or_create_daily_tab(self, date_str: str) -> str:
        """Get or create a tab named with the date."""
        service = self._get_service()
        meta = service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID
        ).execute()

        for sheet in meta["sheets"]:
            if sheet["properties"]["title"] == date_str:
                logger.info("Tab '%s' already exists, resuming...", date_str)
                return date_str

        # Create new tab
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "requests": [{
                    "addSheet": {
                        "properties": {"title": date_str}
                    }
                }]
            },
        ).execute()
        logger.info("Created new tab '%s'", date_str)

        # Write header row
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{date_str}'!A1:{chr(64 + len(COLUMNS))}1",
            valueInputOption="RAW",
            body={"values": [COLUMNS]},
        ).execute()

        # Write info rows
        info_rows = [
            ["OutreachPilot Sweep \u2013 last 24h snapshot"],
            ["Best-effort live capture from subreddit /new feeds. "
             "Rows marked 'no recent post found' mean the newest accessible "
             "post appeared older than 24h."],
            [],
        ]
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{date_str}'!A2:A4",
            valueInputOption="RAW",
            body={"values": info_rows},
        ).execute()

        return date_str

    def append_rows(self, tab_name: str, rows: list[dict]) -> None:
        """Append rows to the sheet."""
        if not rows:
            return
        service = self._get_service()
        values = [[row.get(col, "") for col in COLUMNS] for row in rows]
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{tab_name}'!A:{chr(64 + len(COLUMNS))}",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()
        logger.info("Appended %d rows to Google Sheet", len(rows))

    def export(self, rows: list[dict], config: dict | None = None) -> None:
        """Export rows to Google Sheets (creates daily tab if needed)."""
        import datetime
        tab_name = (config or {}).get("tab_name", datetime.date.today().isoformat())
        self.get_or_create_daily_tab(tab_name)
        self.append_rows(tab_name, rows)

    def save_fallback(self, rows: list[dict]) -> None:
        """Save rows to fallback JSON file if sheet write fails."""
        fallback_path = ROOT_DIR / "fallback_rows.json"
        with open(fallback_path, "w") as f:
            json.dump(rows, f, indent=2)
        logger.warning("Saved %d rows to %s", len(rows), fallback_path)
