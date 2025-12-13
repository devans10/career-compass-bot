import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)

SCOPE = "https://www.googleapis.com/auth/spreadsheets"
HEADERS = ["Timestamp", "Date", "Type", "Text", "Tags", "Source"]
ACCOMPLISHMENTS_HEADERS = HEADERS

GOAL_HEADERS = ["GoalID", "Title", "Status", "TargetDate", "Owner", "Notes"]
GOAL_STATUSES = {"Not Started", "In Progress", "Blocked", "Completed", "Deferred"}

COMPETENCY_HEADERS = ["CompetencyID", "Name", "Category", "Status", "Description"]
COMPETENCY_STATUSES = {"Active", "Inactive"}

GOAL_MAPPING_HEADERS = ["EntryTimestamp", "EntryDate", "GoalID", "CompetencyID", "Notes"]
DATE_FORMAT = "%Y-%m-%d"


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
        self._initialized_sheets: set[str] = set()

    def append_entry(self, record: Dict[str, Any]) -> None:
        """Append a single entry to the sheet following the enforced schema."""

        self._append_row(
            sheet_name=self.sheet_name,
            headers=ACCOMPLISHMENTS_HEADERS,
            values=[
                record.get("timestamp", ""),
                record.get("date", ""),
                record.get("type", ""),
                record.get("text", ""),
                record.get("tags", ""),
                record.get("source", ""),
            ],
            action="append_entry",
        )

    async def append_entry_async(self, record: Dict[str, Any]) -> None:
        """Async wrapper to append a single entry without blocking the event loop."""

        await asyncio.to_thread(self.append_entry, record)

    def append_goal(self, goal: Dict[str, Any]) -> None:
        """Append a goal record after validating required fields and status."""

        self._validate_goal(goal)
        self._append_row(
            sheet_name="Goals",
            headers=GOAL_HEADERS,
            values=[
                goal.get("goalid") or goal.get("goal_id") or goal.get("id", ""),
                goal.get("title", ""),
                goal.get("status", ""),
                goal.get("targetdate") or goal.get("target_date", ""),
                goal.get("owner", ""),
                goal.get("notes", ""),
            ],
            action="append_goal",
            create_if_missing=False,
            allow_header_update=False,
        )

    def append_competency(self, competency: Dict[str, Any]) -> None:
        """Append a competency record with validation."""

        self._validate_competency(competency)
        self._append_row(
            sheet_name="Competencies",
            headers=COMPETENCY_HEADERS,
            values=[
                competency.get("competencyid")
                or competency.get("competency_id")
                or competency.get("id", ""),
                competency.get("name", ""),
                competency.get("category", ""),
                competency.get("status", ""),
                competency.get("description", ""),
            ],
            action="append_competency",
            create_if_missing=False,
            allow_header_update=False,
        )

    def append_goal_mapping(self, mapping: Dict[str, Any]) -> None:
        """Append a mapping that links an entry to a goal and/or competency."""

        self._validate_goal_mapping(mapping)
        self._append_row(
            sheet_name="GoalMappings",
            headers=GOAL_MAPPING_HEADERS,
            values=[
                mapping.get("entrytimestamp")
                or mapping.get("entry_timestamp")
                or mapping.get("timestamp", ""),
                mapping.get("entrydate")
                or mapping.get("entry_date")
                or mapping.get("date", ""),
                mapping.get("goalid") or mapping.get("goal_id") or mapping.get("goal", ""),
                mapping.get("competencyid")
                or mapping.get("competency_id")
                or mapping.get("competency", ""),
                mapping.get("notes", ""),
            ],
            action="append_goal_mapping",
            create_if_missing=False,
            allow_header_update=False,
        )

    def get_goals(self) -> List[Dict[str, str]]:
        """Return all goal records with validation applied to each row."""

        rows = self._get_sheet_rows(
            sheet_name="Goals",
            headers=GOAL_HEADERS,
            create_if_missing=False,
            allow_header_update=False,
        )
        return [self._normalize_goal_row(row, index) for index, row in enumerate(rows, start=2)]

    def get_competencies(self) -> List[Dict[str, str]]:
        """Return all competency records with validation."""

        rows = self._get_sheet_rows(
            sheet_name="Competencies",
            headers=COMPETENCY_HEADERS,
            create_if_missing=False,
            allow_header_update=False,
        )
        return [
            self._normalize_competency_row(row, index)
            for index, row in enumerate(rows, start=2)
        ]

    def get_goal_mappings(self) -> List[Dict[str, str]]:
        """Return all goal-to-entry mapping rows with validation."""

        rows = self._get_sheet_rows(
            sheet_name="GoalMappings",
            headers=GOAL_MAPPING_HEADERS,
            create_if_missing=False,
            allow_header_update=False,
        )
        return [
            self._normalize_goal_mapping_row(row, index)
            for index, row in enumerate(rows, start=2)
        ]

    def get_entries_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Retrieve entries between two dates (inclusive)."""

        self._ensure_sheet_initialized_for(
            sheet_name=self.sheet_name,
            headers=ACCOMPLISHMENTS_HEADERS,
            create_if_missing=True,
            allow_header_update=True,
        )

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

        self._ensure_sheet_initialized_for(
            sheet_name=self.sheet_name,
            headers=ACCOMPLISHMENTS_HEADERS,
            create_if_missing=True,
            allow_header_update=True,
        )

    async def ensure_sheet_setup_async(self) -> None:
        """Async wrapper for sheet setup without blocking the event loop."""

        await asyncio.to_thread(self.ensure_sheet_setup)

    def _append_row(
        self,
        sheet_name: str,
        headers: Sequence[str],
        values: Sequence[Any],
        action: str,
        *,
        create_if_missing: bool = True,
        allow_header_update: bool = True,
    ) -> None:
        self._ensure_sheet_initialized_for(
            sheet_name=sheet_name,
            headers=headers,
            create_if_missing=create_if_missing,
            allow_header_update=allow_header_update,
        )

        normalized_values = list(values)[: len(headers)]
        if len(normalized_values) < len(headers):
            normalized_values.extend([""] * (len(headers) - len(normalized_values)))

        logger.info(
            "Appending row to Google Sheet",
            extra={"sheet": sheet_name, "spreadsheet_id": self.spreadsheet_id},
        )

        range_ref = self._build_range(sheet_name, len(headers))

        def _execute_append():
            request = (
                self._get_service()
                .spreadsheets()
                .values()
                .append(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_ref,
                    valueInputOption="RAW",
                    insertDataOption="INSERT_ROWS",
                    body={"values": [normalized_values]},
                )
            )
            return request.execute()

        response = self._execute_with_retries(_execute_append, action=action)

        updates = response.get("updates") if isinstance(response, dict) else None
        updated_rows = updates.get("updatedRows") if isinstance(updates, dict) else None
        if not updated_rows:
            logger.error(
                "Google Sheets append returned no updates",
                extra={
                    "sheet": sheet_name,
                    "spreadsheet_id": self.spreadsheet_id,
                    "response_keys": sorted(response.keys()) if isinstance(response, dict) else None,
                },
            )
            raise RuntimeError("Google Sheets append did not write any rows")

        logger.info(
            "Append completed",
            extra={
                "sheet": sheet_name,
                "spreadsheet_id": self.spreadsheet_id,
                "updated_rows": updated_rows,
            },
        )

    def _get_sheet_rows(
        self,
        *,
        sheet_name: str,
        headers: Sequence[str],
        create_if_missing: bool,
        allow_header_update: bool,
    ) -> List[List[str]]:
        self._ensure_sheet_initialized_for(
            sheet_name=sheet_name,
            headers=headers,
            create_if_missing=create_if_missing,
            allow_header_update=allow_header_update,
        )

        range_ref = self._build_range(sheet_name, len(headers))

        def _execute_get():
            request = (
                self._get_service()
                .spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=range_ref)
            )
            return request.execute()

        response = self._execute_with_retries(_execute_get, action="get_rows")
        values = response.get("values", [])
        if not values:
            return []

        header_row = values[0][: len(headers)]
        if header_row != list(headers):
            raise ValueError(
                f"Sheet '{sheet_name}' header mismatch. Expected {list(headers)}, found {header_row or 'empty'}"
            )

        return values[1:]

    def _ensure_sheet_initialized_for(
        self,
        *,
        sheet_name: str,
        headers: Sequence[str],
        create_if_missing: bool,
        allow_header_update: bool,
    ) -> None:
        if sheet_name in self._initialized_sheets:
            return

        self._ensure_sheet_exists(sheet_name=sheet_name, create_if_missing=create_if_missing)
        self._ensure_headers(
            sheet_name=sheet_name,
            headers=headers,
            allow_header_update=allow_header_update,
            _create_if_missing=create_if_missing,
        )
        self._initialized_sheets.add(sheet_name)

    def _ensure_sheet_exists(self, *, sheet_name: str, create_if_missing: bool) -> None:
        def _execute_get_metadata():
            request = self._get_service().spreadsheets().get(
                spreadsheetId=self.spreadsheet_id, fields="sheets.properties.title"
            )
            return request.execute()

        metadata = self._execute_with_retries(_execute_get_metadata, action="get_metadata")
        sheet_titles = {sheet["properties"]["title"] for sheet in metadata.get("sheets", [])}

        if sheet_name in sheet_titles:
            return
        if not create_if_missing:
            raise ValueError(
                f"Sheet '{sheet_name}' is missing. Please create it with the expected headers."
            )

        logger.info(
            "Creating missing sheet tab",
            extra={"sheet": sheet_name, "spreadsheet_id": self.spreadsheet_id},
        )

        def _execute_create_sheet():
            request = self._get_service().spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
            )
            return request.execute()

        self._execute_with_retries(_execute_create_sheet, action="create_sheet")

    def _ensure_headers(
        self,
        *,
        sheet_name: str,
        headers: Sequence[str],
        allow_header_update: bool,
        _create_if_missing: bool,
    ) -> None:
        header_range = self._build_header_range(sheet_name, len(headers))

        def _execute_get_headers():
            request = self._get_service().spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=header_range
            )
            return request.execute()

        response = self._execute_with_retries(_execute_get_headers, action="get_headers")
        values = response.get("values", [])
        if values and values[0][: len(headers)] == list(headers):
            return

        if not allow_header_update:
            raise ValueError(
                f"Sheet '{sheet_name}' header mismatch. Expected {list(headers)}, found {values[0] if values else 'empty'}"
            )

        logger.info(
            "Updating sheet headers",
            extra={"sheet": sheet_name, "spreadsheet_id": self.spreadsheet_id},
        )

        def _execute_update_headers():
            request = self._get_service().spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=header_range,
                valueInputOption="RAW",
                body={"values": [list(headers)]},
            )
            return request.execute()

        self._execute_with_retries(_execute_update_headers, action="update_headers")

    def _normalize_goal_row(self, row: Sequence[str], row_number: int) -> Dict[str, str]:
        normalized = self._normalize_row_length(row, GOAL_HEADERS, "Goals", row_number)
        record = dict(zip([header.lower() for header in GOAL_HEADERS], normalized))
        self._validate_status(record["status"], GOAL_STATUSES, "Goals", row_number)
        self._validate_date_field(
            record.get("targetdate", ""),
            field_name="TargetDate",
            sheet_name="Goals",
            row_number=row_number,
            allow_empty=True,
        )
        self._validate_non_empty(record.get("goalid", ""), "GoalID", "Goals", row_number)
        self._validate_non_empty(record.get("title", ""), "Title", "Goals", row_number)
        return record

    def _normalize_competency_row(
        self, row: Sequence[str], row_number: int
    ) -> Dict[str, str]:
        normalized = self._normalize_row_length(
            row, COMPETENCY_HEADERS, "Competencies", row_number
        )
        record = dict(zip([header.lower() for header in COMPETENCY_HEADERS], normalized))
        self._validate_status(
            record["status"], COMPETENCY_STATUSES, "Competencies", row_number
        )
        self._validate_non_empty(
            record.get("competencyid", ""), "CompetencyID", "Competencies", row_number
        )
        self._validate_non_empty(record.get("name", ""), "Name", "Competencies", row_number)
        return record

    def _normalize_goal_mapping_row(
        self, row: Sequence[str], row_number: int
    ) -> Dict[str, str]:
        normalized = self._normalize_row_length(
            row, GOAL_MAPPING_HEADERS, "GoalMappings", row_number
        )
        record = dict(zip([header.lower() for header in GOAL_MAPPING_HEADERS], normalized))
        self._validate_non_empty(
            record.get("entrytimestamp", ""), "EntryTimestamp", "GoalMappings", row_number
        )
        self._validate_date_field(
            record.get("entrydate", ""),
            field_name="EntryDate",
            sheet_name="GoalMappings",
            row_number=row_number,
            allow_empty=False,
        )
        if not record.get("goalid") and not record.get("competencyid"):
            raise ValueError(
                "GoalMappings row requires at least a GoalID or CompetencyID "
                f"(sheet 'GoalMappings', row {row_number})"
            )
        return record

    @staticmethod
    def _normalize_row_length(
        row: Sequence[str], headers: Sequence[str], sheet_name: str, row_number: int
    ) -> List[str]:
        if len(row) < len(headers):
            row = list(row) + [""] * (len(headers) - len(row))
        return list(row[: len(headers)])

    def _validate_goal(self, goal: Dict[str, Any]) -> None:
        status = goal.get("status", "")
        self._validate_status(status, GOAL_STATUSES, "Goals", row_number=0)
        self._validate_date_field(
            goal.get("targetdate") or goal.get("target_date", ""),
            field_name="TargetDate",
            sheet_name="Goals",
            row_number=0,
            allow_empty=True,
        )
        self._validate_non_empty(
            goal.get("goalid") or goal.get("goal_id") or goal.get("id", ""),
            "GoalID",
            "Goals",
            row_number=0,
        )
        self._validate_non_empty(goal.get("title", ""), "Title", "Goals", row_number=0)

    def _validate_competency(self, competency: Dict[str, Any]) -> None:
        status = competency.get("status", "")
        self._validate_status(status, COMPETENCY_STATUSES, "Competencies", row_number=0)
        self._validate_non_empty(
            competency.get("competencyid")
            or competency.get("competency_id")
            or competency.get("id", ""),
            "CompetencyID",
            "Competencies",
            row_number=0,
        )
        self._validate_non_empty(competency.get("name", ""), "Name", "Competencies", 0)

    def _validate_goal_mapping(self, mapping: Dict[str, Any]) -> None:
        entry_date = mapping.get("entrydate") or mapping.get("entry_date") or mapping.get("date", "")
        entry_timestamp = (
            mapping.get("entrytimestamp")
            or mapping.get("entry_timestamp")
            or mapping.get("timestamp", "")
        )
        self._validate_non_empty(entry_timestamp, "EntryTimestamp", "GoalMappings", 0)
        self._validate_date_field(
            entry_date,
            field_name="EntryDate",
            sheet_name="GoalMappings",
            row_number=0,
            allow_empty=False,
        )
        goal_id = mapping.get("goalid") or mapping.get("goal_id") or mapping.get("goal", "")
        competency_id = (
            mapping.get("competencyid")
            or mapping.get("competency_id")
            or mapping.get("competency", "")
        )
        if not goal_id and not competency_id:
            raise ValueError(
                "GoalMappings append requires at least a GoalID or CompetencyID"
            )

    @staticmethod
    def _validate_status(value: str, allowed: set[str], sheet_name: str, row_number: int) -> None:
        if value not in allowed:
            raise ValueError(
                f"Invalid status '{value}' in sheet '{sheet_name}' at row {row_number}. "
                f"Allowed: {sorted(allowed)}"
            )

    @staticmethod
    def _validate_non_empty(value: str, field_name: str, sheet_name: str, row_number: int) -> None:
        if not value:
            raise ValueError(
                f"Field '{field_name}' is required in sheet '{sheet_name}' at row {row_number}"
            )

    @staticmethod
    def _validate_date_field(
        value: str, *, field_name: str, sheet_name: str, row_number: int, allow_empty: bool
    ) -> None:
        if not value and allow_empty:
            return
        try:
            datetime.strptime(value, DATE_FORMAT)
        except ValueError as exc:
            raise ValueError(
                f"Field '{field_name}' must match {DATE_FORMAT} in sheet '{sheet_name}' at row {row_number}"
            ) from exc

    def _build_range(self, sheet_name: str, column_count: int) -> str:
        return f"{sheet_name}!A:{self._column_letter(column_count)}"

    def _build_header_range(self, sheet_name: str, column_count: int) -> str:
        column_letter = self._column_letter(column_count)
        return f"{sheet_name}!A1:{column_letter}1"

    @staticmethod
    def _column_letter(column_count: int) -> str:
        # Supports up to column ZZ which exceeds our current schema needs
        dividend = column_count
        column_name = ""
        while dividend > 0:
            modulo = (dividend - 1) % 26
            column_name = chr(65 + modulo) + column_name
            dividend = (dividend - modulo) // 26
        return column_name

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
