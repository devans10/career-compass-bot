import json
from unittest.mock import MagicMock

import pytest

from src.storage.google_sheets_client import (
    COMPETENCY_HEADERS,
    COMPETENCY_STATUSES,
    GOAL_HEADERS,
    GOAL_MAPPING_HEADERS,
    GOAL_STATUSES,
    HEADERS,
    GoogleSheetsClient,
)


def _build_service_mock(
    metadata=None, header_row=None, values=None, include_header=True, append_response=None
):
    """Helper to build a nested Google Sheets service mock."""

    service = MagicMock()
    spreadsheets_resource = MagicMock()
    values_resource = MagicMock()

    service.spreadsheets.return_value = spreadsheets_resource
    spreadsheets_resource.values.return_value = values_resource

    metadata_get_request = MagicMock()
    metadata_get_request.execute.return_value = metadata or {"sheets": []}
    spreadsheets_resource.get.return_value = metadata_get_request

    batch_update_request = MagicMock()
    batch_update_request.execute.return_value = {}
    spreadsheets_resource.batchUpdate.return_value = batch_update_request

    header_get_request = MagicMock()
    header_get_request.execute.return_value = {"values": header_row} if header_row is not None else {}

    header_update_request = MagicMock()
    header_update_request.execute.return_value = {}
    values_resource.update.return_value = header_update_request

    values_get_request = MagicMock()
    values_get_request.execute.return_value = {"values": values} if values is not None else {}
    append_payload = append_response or {"updates": {"updatedRows": 1}}
    values_resource.append.return_value = MagicMock(execute=MagicMock(return_value=append_payload))
    if values is not None:
        if include_header:
            values_resource.get.side_effect = [header_get_request, values_get_request]
        else:
            values_resource.get.return_value = values_get_request
    else:
        values_resource.get.return_value = header_get_request

    return service, spreadsheets_resource, values_resource


class FakeRequest:
    def __init__(self, func):
        self._func = func

    def execute(self):
        return self._func()


class FakeSheetsService:
    def __init__(self):
        self.sheet_titles: set[str] = set()
        self.sheet_data: dict[str, dict[str, list]] = {}
        self.spreadsheets_resource = FakeSpreadsheetsResource(self)

    def spreadsheets(self):
        return self.spreadsheets_resource

    def ensure_sheet(self, sheet_name: str) -> dict:
        if sheet_name not in self.sheet_titles:
            self.sheet_titles.add(sheet_name)
        if sheet_name not in self.sheet_data:
            self.sheet_data[sheet_name] = {"header": None, "values": []}
        return self.sheet_data[sheet_name]

    @property
    def header_row(self):
        return self.ensure_sheet("Accomplishments")["header"]

    @header_row.setter
    def header_row(self, value):
        self.ensure_sheet("Accomplishments")["header"] = value

    @property
    def values(self):
        return self.ensure_sheet("Accomplishments")["values"]


class FakeValuesResource:
    def __init__(self, service: FakeSheetsService):
        self.service = service

    def get(self, spreadsheetId, range):  # noqa: N802
        def _execute():
            sheet_name, cell_range = range.split("!")
            sheet = self.service.ensure_sheet(sheet_name)
            if cell_range.startswith("A1"):
                return {"values": [sheet["header"]]} if sheet["header"] is not None else {}
            values = list(sheet["values"])
            if sheet["header"] is not None:
                values = [sheet["header"]] + values
            return {"values": values}

        return FakeRequest(_execute)

    def update(self, spreadsheetId, range, valueInputOption, body):  # noqa: N802
        def _execute():
            sheet_name = range.split("!")[0]
            sheet = self.service.ensure_sheet(sheet_name)
            sheet["header"] = body.get("values", [None])[0]
            return {}

        return FakeRequest(_execute)

    def append(self, spreadsheetId, range, valueInputOption, insertDataOption, body):  # noqa: N802
        def _execute():
            sheet_name = range.split("!")[0]
            sheet = self.service.ensure_sheet(sheet_name)
            sheet["values"].extend(body.get("values", []))
            return {"updates": {"updatedRows": len(body.get("values", []))}}

        return FakeRequest(_execute)


class FakeSpreadsheetsResource:
    def __init__(self, service: FakeSheetsService):
        self.service = service
        self.values_resource = FakeValuesResource(service)

    def get(self, spreadsheetId, fields=None):  # noqa: N802
        def _execute():
            return {
                "sheets": [
                    {"properties": {"title": name}} for name in sorted(self.service.sheet_titles)
                ]
            }

        return FakeRequest(_execute)

    def batchUpdate(self, spreadsheetId, body):  # noqa: N802
        def _execute():
            for request in body.get("requests", []):
                add_sheet = request.get("addSheet")
                if add_sheet:
                    self.service.ensure_sheet(add_sheet["properties"]["title"])
            return {}

        return FakeRequest(_execute)

    def values(self):
        return self.values_resource


def test_ensure_sheet_setup_creates_sheet_and_headers():
    metadata = {"sheets": [{"properties": {"title": "Other"}}]}
    service, spreadsheets_resource, values_resource = _build_service_mock(metadata=metadata, header_row=[])

    client = GoogleSheetsClient("spreadsheet-id", service_account_file=None, service=service)

    client.ensure_sheet_setup()

    spreadsheets_resource.batchUpdate.assert_called_once()
    values_resource.update.assert_called_once_with(
        spreadsheetId="spreadsheet-id",
        range="Accomplishments!A1:F1",
        valueInputOption="RAW",
        body={"values": [HEADERS]},
    )


def test_append_entry_writes_row_in_schema_order():
    service, _, values_resource = _build_service_mock(header_row=[HEADERS])
    append_request = MagicMock()
    append_request.execute.return_value = {"updates": {"updatedRows": 1}}
    values_resource.append.return_value = append_request

    client = GoogleSheetsClient("spreadsheet-id", service=service)
    client._initialized_sheets.add(client.sheet_name)

    client.append_entry(
        {
            "timestamp": "2024-05-01T12:00:00Z",
            "date": "2024-05-01",
            "type": "task",
            "text": "Follow up",
            "tags": "#tag",
            "source": "telegram",
        }
    )

    values_resource.append.assert_called_once_with(
        spreadsheetId="spreadsheet-id",
        range="Accomplishments!A:F",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={
            "values": [
                ["2024-05-01T12:00:00Z", "2024-05-01", "task", "Follow up", "#tag", "telegram"]
            ]
        },
    )
    append_request.execute.assert_called_once()


def test_append_entry_raises_when_no_rows_updated():
    service, _, _ = _build_service_mock(
        header_row=[HEADERS], append_response={"updates": {"updatedRows": 0}}
    )
    client = GoogleSheetsClient("spreadsheet-id", service=service)
    client._initialized_sheets.add(client.sheet_name)

    with pytest.raises(RuntimeError, match="did not write any rows"):
        client.append_entry(
            {
                "timestamp": "",
                "date": "",
                "type": "task",
                "text": "",
                "tags": "",
                "source": "telegram",
            }
        )


def test_get_entries_by_date_range_filters_results():
    rows = [
        HEADERS,
        ["2024-05-01T00:00:00Z", "2024-05-01", "task", "One", "", "telegram"],
        ["2024-06-01T00:00:00Z", "2024-06-01", "idea", "Two", "", "telegram"],
    ]
    service, _, values_resource = _build_service_mock(
        header_row=[HEADERS], values=rows, include_header=False
    )
    client = GoogleSheetsClient("spreadsheet-id", service=service)
    client._initialized_sheets.add(client.sheet_name)

    entries = client.get_entries_by_date_range("2024-05-15", "2024-06-15")

    assert len(entries) == 1
    assert entries[0]["text"] == "Two"
    values_resource.get.assert_called_with(
        spreadsheetId="spreadsheet-id", range="Accomplishments!A:F"
    )


def test_google_sheets_client_integration_with_fake_service():
    service = FakeSheetsService()
    client = GoogleSheetsClient("spreadsheet-id", service=service)

    client.ensure_sheet_setup()

    assert "Accomplishments" in service.sheet_titles
    assert service.header_row == HEADERS

    client.append_entry(
        {
            "timestamp": "2024-05-15T10:00:00Z",
            "date": "2024-05-15",
            "type": "task",
            "text": "Prep slides",
            "tags": "#planning",
            "source": "telegram",
        }
    )
    client.append_entry(
        {
            "timestamp": "2024-06-01T12:00:00Z",
            "date": "2024-06-01",
            "type": "idea",
            "text": "Pilot",  # Should be filtered in May-only range
            "tags": "",
            "source": "telegram",
        }
    )

    may_entries = client.get_entries_by_date_range("2024-05-01", "2024-05-31")

    assert len(may_entries) == 1
    assert may_entries[0]["text"] == "Prep slides"


def test_goal_sheet_validation_requires_tab_and_correct_rows():
    client = GoogleSheetsClient("spreadsheet-id", service=FakeSheetsService())

    with pytest.raises(ValueError, match="Sheet 'Goals' is missing"):
        client.get_goals()

    service = FakeSheetsService()
    goals_sheet = service.ensure_sheet("Goals")
    goals_sheet["header"] = GOAL_HEADERS
    goals_sheet["values"].append(["1", "Ship", "Done", "2024-12-31", "Me", ""])
    client = GoogleSheetsClient("spreadsheet-id", service=service)

    with pytest.raises(ValueError, match="Invalid status 'Done'"):
        client.get_goals()


def test_append_goal_mapping_and_read_back():
    service = FakeSheetsService()
    service.ensure_sheet("GoalMappings")["header"] = GOAL_MAPPING_HEADERS
    client = GoogleSheetsClient("spreadsheet-id", service=service)

    client.append_goal_mapping(
        {
            "entrytimestamp": "2024-06-01T12:00:00Z",
            "entrydate": "2024-06-01",
            "goal_id": "G-123",
            "competency_id": "C-456",
            "notes": "Linked",
        }
    )

    mappings = client.get_goal_mappings()

    assert len(mappings) == 1
    assert mappings[0]["goalid"] == "G-123"
    assert service.ensure_sheet("GoalMappings")["values"][-1][0] == "2024-06-01T12:00:00Z"


def test_append_goal_and_competency_validation():
    service = FakeSheetsService()
    service.ensure_sheet("Goals")["header"] = GOAL_HEADERS
    service.ensure_sheet("Competencies")["header"] = COMPETENCY_HEADERS
    client = GoogleSheetsClient("spreadsheet-id", service=service)

    with pytest.raises(ValueError, match="Field 'Title' is required"):
        client.append_goal({"goal_id": "G-1", "status": next(iter(GOAL_STATUSES))})

    with pytest.raises(ValueError, match="Invalid status 'Retired'"):
        client.append_competency(
            {
                "competency_id": "C-1",
                "name": "Communication",
                "status": "Retired",
            }
        )


def test_goal_mapping_requires_goal_or_competency():
    service = FakeSheetsService()
    service.ensure_sheet("GoalMappings")["header"] = GOAL_MAPPING_HEADERS
    client = GoogleSheetsClient("spreadsheet-id", service=service)

    with pytest.raises(ValueError, match="requires at least a GoalID or CompetencyID"):
        client.append_goal_mapping(
            {"entrytimestamp": "2024-06-01T12:00:00Z", "entrydate": "2024-06-01"}
        )


def test_goal_mapping_header_and_date_validation():
    service = FakeSheetsService()
    sheet = service.ensure_sheet("GoalMappings")
    sheet["header"] = ["Wrong"]
    client = GoogleSheetsClient("spreadsheet-id", service=service)

    with pytest.raises(ValueError, match="header mismatch"):
        client.get_goal_mappings()

    sheet["header"] = GOAL_MAPPING_HEADERS
    sheet["values"].append(["2024-01-01T00:00:00Z", "01-01-2024", "G-1", "", ""])

    with pytest.raises(ValueError, match="must match %Y-%m-%d"):
        client.get_goal_mappings()


def test_load_credentials_validates_service_account_json(monkeypatch):
    monkeypatch.setattr(
        "src.storage.google_sheets_client.service_account.Credentials.from_service_account_info",
        MagicMock(),
    )

    client = GoogleSheetsClient(
        "spreadsheet-id", service_account_json=json.dumps({"client_email": "bot@example.com"})
    )

    with pytest.raises(ValueError, match="Service account info missing required fields"):
        client._load_credentials()


def test_load_credentials_validates_service_account_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.storage.google_sheets_client.service_account.Credentials.from_service_account_info",
        MagicMock(),
    )
    service_account_file = tmp_path / "service.json"
    service_account_file.write_text(json.dumps({"token_uri": "https://example.com"}), encoding="utf-8")

    client = GoogleSheetsClient("spreadsheet-id", service_account_file=str(service_account_file))

    with pytest.raises(ValueError, match="Service account info missing required fields"):
        client._load_credentials()
