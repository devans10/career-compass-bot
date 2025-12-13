from unittest.mock import MagicMock


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

    def spreadsheets(self):  # noqa: D401 - external API mimic
        """Return the fake spreadsheets resource."""

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

    def values(self):  # noqa: D401 - external API mimic
        """Return the fake values resource."""

        return self.values_resource


# Helper used in storage unit tests to mirror Google Sheets client structure

def build_service_mock(metadata=None, header_row=None, values=None, include_header=True, append_response=None):
    """Build a nested Google Sheets service mock that mimics discovery structure."""

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


__all__ = [
    "FakeRequest",
    "FakeSheetsService",
    "FakeSpreadsheetsResource",
    "FakeValuesResource",
    "build_service_mock",
]
