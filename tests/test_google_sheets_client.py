import json
from unittest.mock import MagicMock

import pytest

from src.storage.google_sheets_client import HEADERS, GoogleSheetsClient


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


class FakeValuesResource:
    def __init__(self, service):
        self.service = service

    def get(self, spreadsheetId, range):  # noqa: N802
        def _execute():
            if range.endswith("A1:F1"):
                return {"values": [self.service.header_row]} if self.service.header_row is not None else {}
            values = list(self.service.values)
            if self.service.header_row:
                values = [self.service.header_row] + values
            return {"values": values}

        return FakeRequest(_execute)

    def update(self, spreadsheetId, range, valueInputOption, body):  # noqa: N802
        def _execute():
            self.service.header_row = body.get("values", [None])[0]
            return {}

        return FakeRequest(_execute)

    def append(self, spreadsheetId, range, valueInputOption, insertDataOption, body):  # noqa: N802
        def _execute():
            self.service.values.extend(body.get("values", []))
            return {"updates": {"updatedRows": len(body.get("values", []))}}

        return FakeRequest(_execute)


class FakeSpreadsheetsResource:
    def __init__(self, service):
        self.service = service
        self.values_resource = FakeValuesResource(service)

    def get(self, spreadsheetId, fields=None):  # noqa: N802
        def _execute():
            return {
                "sheets": [
                    {"properties": {"title": name}} for name in self.service.sheet_titles
                ]
            }

        return FakeRequest(_execute)

    def batchUpdate(self, spreadsheetId, body):  # noqa: N802
        def _execute():
            for request in body.get("requests", []):
                add_sheet = request.get("addSheet")
                if add_sheet:
                    self.service.sheet_titles.add(add_sheet["properties"]["title"])
            return {}

        return FakeRequest(_execute)

    def values(self):
        return self.values_resource


class FakeSheetsService:
    def __init__(self):
        self.sheet_titles = set()
        self.header_row = None
        self.values = []
        self.spreadsheets_resource = FakeSpreadsheetsResource(self)

    def spreadsheets(self):
        return self.spreadsheets_resource


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
    client._headers_initialized = True

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
    client._headers_initialized = True

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
    client._headers_initialized = True

    entries = client.get_entries_by_date_range("2024-05-15", "2024-06-15")

    assert len(entries) == 1
    assert entries[0]["text"] == "Two"
    values_resource.get.assert_called_once_with(
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
