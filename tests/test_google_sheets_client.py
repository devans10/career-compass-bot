from unittest.mock import MagicMock

from src.storage.google_sheets_client import HEADERS, GoogleSheetsClient


def _build_service_mock(metadata=None, header_row=None, values=None, include_header=True):
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
    values_resource.append.return_value = MagicMock(execute=MagicMock(return_value={}))
    if values is not None:
        if include_header:
            values_resource.get.side_effect = [header_get_request, values_get_request]
        else:
            values_resource.get.return_value = values_get_request
    else:
        values_resource.get.return_value = header_get_request

    return service, spreadsheets_resource, values_resource


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
    append_request.execute.return_value = {}
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
