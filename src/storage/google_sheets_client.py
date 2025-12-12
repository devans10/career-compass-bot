import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)

SCOPE = "https://www.googleapis.com/auth/spreadsheets"
HEADERS = ["Timestamp", "Date", "Type", "Text", "Tags", "Source"]


class GoogleSheetsClient:
    """Client for interacting with the Google Sheets storage backend."""

    def __init__(
        self,
        spreadsheet_id: str,
        service_account_file: Optional[str] = None,
        service_account_json: Optional[str] = None,
        sheet_name: str = "Accomplishments",
        max_retries: int = 3,
        service: Any | None = None,
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.service_account_file = service_account_file
        self.service_account_json = service_account_json
        self.sheet_name = sheet_name
        self.max_retries = max_retries
        self._service = service
        self._headers_initialized = False

    def append_entry(self, record: Dict[str, Any]) -> None:
        """Append a single entry to the sheet following the enforced schema."""

        self._ensure_sheet_initialized()

        values = [
            record.get("timestamp", ""),
            record.get("date", ""),
            record.get("type", ""),
            record.get("text", ""),
            record.get("tags", ""),
            record.get("source", ""),
        ]

        logger.info(
            "Appending entry to Google Sheet",
            extra={"sheet": self.sheet_name, "spreadsheet_id": self.spreadsheet_id},
        )

        def _execute_append():
            request = (
                self._get_service()
                .spreadsheets()
                .values()
                .append(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{self.sheet_name}!A:F",
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": [values]},
                )
            )
            return request.execute()

        response = self._execute_with_retries(_execute_append, action="append_entry")

        updates = response.get("updates") if isinstance(response, dict) else None
        updated_rows = updates.get("updatedRows") if isinstance(updates, dict) else None
        if not updated_rows:
            logger.error(
                "Google Sheets append returned no updates",
                extra={
                    "sheet": self.sheet_name,
                    "spreadsheet_id": self.spreadsheet_id,
                    "response_keys": sorted(response.keys()) if isinstance(response, dict) else None,
                },
            )
            raise RuntimeError("Google Sheets append did not write any rows")

        logger.info(
            "Append completed",
            extra={
                "sheet": self.sheet_name,
                "spreadsheet_id": self.spreadsheet_id,
                "updated_rows": updated_rows,
            },
        )

    async def append_entry_async(self, record: Dict[str, Any]) -> None:
        """Async wrapper to append a single entry without blocking the event loop."""

        await asyncio.to_thread(self.append_entry, record)

    def get_entries_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Retrieve entries between two dates (inclusive)."""

        self._ensure_sheet_initialized()

        logger.info(
            "Fetching entries from Google Sheet",
            extra={
                "sheet": self.sheet_name,
                "spreadsheet_id": self.spreadsheet_id,
                "start_date": start_date,
                "end_date": end_date,
            },
        )

        def _execute_get():
            request = (
                self._get_service()
                .spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=f"{self.sheet_name}!A:F")
            )
            return request.execute()

        response = self._execute_with_retries(_execute_get, action="get_entries")
        values: List[List[str]] = response.get("values", [])

        if not values:
            return []

        rows = values[1:] if values and values[0][: len(HEADERS)] == HEADERS else values
        entries: List[Dict[str, str]] = []

        for row in rows:
            normalized_row = row + [""] * (len(HEADERS) - len(row))
            entry = dict(zip([header.lower() for header in HEADERS], normalized_row))
            entry_date = entry.get("date", "")
            if start_date <= entry_date <= end_date:
                entries.append(entry)

        return entries

    async def get_entries_by_date_range_async(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Async wrapper to fetch entries without blocking the event loop."""

        return await asyncio.to_thread(self.get_entries_by_date_range, start_date, end_date)

    def ensure_sheet_setup(self) -> None:
        """Public helper to set up the sheet headers and tab if missing."""

        self._ensure_sheet_initialized()

    async def ensure_sheet_setup_async(self) -> None:
        """Async wrapper for sheet setup without blocking the event loop."""

        await asyncio.to_thread(self.ensure_sheet_setup)

    def _ensure_sheet_initialized(self) -> None:
        if self._headers_initialized:
            return

        self._ensure_sheet_exists()
        self._ensure_headers()
        self._headers_initialized = True

    def _ensure_sheet_exists(self) -> None:
        def _execute_get_metadata():
            request = self._get_service().spreadsheets().get(
                spreadsheetId=self.spreadsheet_id, fields="sheets.properties.title"
            )
            return request.execute()

        metadata = self._execute_with_retries(_execute_get_metadata, action="get_metadata")
        sheet_titles = {sheet["properties"]["title"] for sheet in metadata.get("sheets", [])}

        if self.sheet_name in sheet_titles:
            return

        logger.info(
            "Creating missing sheet tab",
            extra={"sheet": self.sheet_name, "spreadsheet_id": self.spreadsheet_id},
        )

        def _execute_create_sheet():
            request = self._get_service().spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": self.sheet_name}}}]},
            )
            return request.execute()

        self._execute_with_retries(_execute_create_sheet, action="create_sheet")

    def _ensure_headers(self) -> None:
        def _execute_get_headers():
            request = self._get_service().spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=f"{self.sheet_name}!A1:F1"
            )
            return request.execute()

        response = self._execute_with_retries(_execute_get_headers, action="get_headers")
        values = response.get("values", [])
        if values and values[0][: len(HEADERS)] == HEADERS:
            return

        logger.info(
            "Updating sheet headers",
            extra={"sheet": self.sheet_name, "spreadsheet_id": self.spreadsheet_id},
        )

        def _execute_update_headers():
            request = self._get_service().spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A1:F1",
                valueInputOption="RAW",
                body={"values": [HEADERS]},
            )
            return request.execute()

        self._execute_with_retries(_execute_update_headers, action="update_headers")

    def _execute_with_retries(self, func, action: str):
        delay = 1
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "Calling Google Sheets API",
                    extra={"action": action, "attempt": attempt, "spreadsheet_id": self.spreadsheet_id},
                )
                return func()
            except (HttpError, Exception) as exc:  # noqa: BLE001
                is_last_attempt = attempt == self.max_retries
                logger.warning(
                    "Google Sheets API call failed",
                    extra={"action": action, "attempt": attempt, "error": str(exc)},
                )
                if is_last_attempt:
                    logger.error(
                        "Google Sheets API call exhausted retries",
                        extra={"action": action, "attempt": attempt, "spreadsheet_id": self.spreadsheet_id},
                    )
                    raise
                time.sleep(delay)
                delay *= 2

    def _get_service(self):
        if self._service:
            return self._service

        credentials = self._load_credentials()
        self._service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        return self._service

    def _load_credentials(self):
        scopes = [SCOPE]
        if self.service_account_json:
            info = self._load_service_account_info(self.service_account_json)
            return service_account.Credentials.from_service_account_info(info, scopes=scopes)
        if self.service_account_file:
            with open(self.service_account_file, "r", encoding="utf-8") as fh:
                info = json.load(fh)
            self._validate_service_account_info(info)
            return service_account.Credentials.from_service_account_info(info, scopes=scopes)

        credentials, _ = google.auth.default(scopes=scopes)
        return credentials

    def _load_service_account_info(self, raw_json: str) -> Dict[str, Any]:
        try:
            info = json.loads(raw_json)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
            raise ValueError("Service account JSON is not valid JSON") from exc

        self._validate_service_account_info(info)
        return info

    @staticmethod
    def _validate_service_account_info(info: Dict[str, Any]) -> None:
        required_fields = ["client_email", "token_uri", "private_key", "project_id"]
        missing = [field for field in required_fields if not info.get(field)]
        if missing:
            raise ValueError(
                "Service account info missing required fields: " + ", ".join(sorted(missing))
            )
