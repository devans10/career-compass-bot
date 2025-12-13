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
from tests.fakes import FakeSheetsService, build_service_mock


def test_ensure_sheet_setup_creates_sheet_and_headers():
    metadata = {"sheets": [{"properties": {"title": "Other"}}]}
    service, spreadsheets_resource, values_resource = build_service_mock(metadata=metadata, header_row=[])

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
    service, _, values_resource = build_service_mock(header_row=[HEADERS])
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
    service, _, _ = build_service_mock(
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
    service, _, values_resource = build_service_mock(
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


def test_trimmed_rows_are_padded_for_goal_related_sheets():
    service = FakeSheetsService()
    goals_sheet = service.ensure_sheet("Goals")
    goals_sheet["header"] = GOAL_HEADERS
    goals_sheet["values"].append(
        ["G-1", "Ship", "In Progress", "2024-12-31"]  # Missing Owner, Notes
    )

    competencies_sheet = service.ensure_sheet("Competencies")
    competencies_sheet["header"] = COMPETENCY_HEADERS
    competencies_sheet["values"].append(
        ["C-1", "Communication", "Core", "Active"]  # Missing Description
    )

    mappings_sheet = service.ensure_sheet("GoalMappings")
    mappings_sheet["header"] = GOAL_MAPPING_HEADERS
    mappings_sheet["values"].append(
        ["2024-06-01T12:00:00Z", "2024-06-01", "G-1"]  # Missing CompetencyID, Notes
    )

    client = GoogleSheetsClient("spreadsheet-id", service=service)

    goals = client.get_goals()
    competencies = client.get_competencies()
    mappings = client.get_goal_mappings()

    assert goals == [
        {
            "goalid": "G-1",
            "title": "Ship",
            "status": "In Progress",
            "targetdate": "2024-12-31",
            "owner": "",
            "notes": "",
        }
    ]
    assert competencies == [
        {
            "competencyid": "C-1",
            "name": "Communication",
            "category": "Core",
            "status": "Active",
            "description": "",
        }
    ]
    assert mappings == [
        {
            "entrytimestamp": "2024-06-01T12:00:00Z",
            "entrydate": "2024-06-01",
            "goalid": "G-1",
            "competencyid": "",
            "notes": "",
        }
    ]


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
