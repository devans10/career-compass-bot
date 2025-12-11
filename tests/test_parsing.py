from datetime import datetime

from src.bot import parsing


def test_extract_tags():
    text = "Wrapped up sprint items #backend #APIM and #infra"

    tags = parsing.extract_tags(text)

    assert tags == ["#backend", "#APIM", "#infra"]


def test_extract_tags_handles_duplicates_and_punctuation():
    text = "Recapped #Team updates, refined #team roadmap and #road_map!"

    tags = parsing.extract_tags(text)

    assert tags == ["#Team", "#team", "#road_map"]


def test_extract_command_argument_removes_command():
    message_text = "/log Implemented endpoint for #feature after refactor"

    assert parsing.extract_command_argument(message_text) == "Implemented endpoint for #feature after refactor"


def test_extract_command_argument_handles_empty_text():
    assert parsing.extract_command_argument("/log") == ""
    assert parsing.extract_command_argument("") == ""


def test_extract_command_argument_strips_surrounding_whitespace():
    message_text = "/task    Close out sprint  "

    assert parsing.extract_command_argument(message_text) == "Close out sprint"


def test_normalize_entry_builds_expected_record(monkeypatch):
    fixed_time = datetime(2024, 5, 1, 12, 0, 0)

    record = parsing.normalize_entry(
        "Implemented endpoint for #feature after refactor",
        entry_type="accomplishment",
        tags=["#feature"],
        timestamp=fixed_time,
    )

    assert record == {
        "timestamp": "2024-05-01T12:00:00",
        "date": "2024-05-01",
        "type": "accomplishment",
        "text": "Implemented endpoint for #feature after refactor",
        "tags": "#feature",
        "source": "telegram",
    }


def test_normalize_entry_trims_text_and_joins_tags():
    fixed_time = datetime(2024, 6, 1, 9, 30, 0)

    record = parsing.normalize_entry(
        "  Drafted launch email  ",
        entry_type="idea",
        tags=["#launch", "#email"],
        timestamp=fixed_time,
    )

    assert record == {
        "timestamp": "2024-06-01T09:30:00",
        "date": "2024-06-01",
        "type": "idea",
        "text": "Drafted launch email",
        "tags": "#launch #email",
        "source": "telegram",
    }
