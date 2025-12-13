from datetime import datetime

from src.bot import parsing
from src.storage.google_sheets_client import GOAL_STATUSES


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


def test_extract_goal_and_competency_tags():
    text = "#goal:G-123 #comp:communication #goal:Roadmap"

    goal_ids = parsing.extract_goal_ids(text)
    comp_ids = parsing.extract_competency_tags(text)

    assert goal_ids == ["G-123", "Roadmap"]
    assert comp_ids == ["communication"]


def test_parse_goal_add_supports_key_value_segments():
    command_text = "G-1 Launch new onboarding | status=In Progress | target=2024-12-31 | owner=Alex | notes=First milestone"

    parsed = parsing.parse_goal_add(command_text, GOAL_STATUSES)

    assert parsed == {
        "goalid": "G-1",
        "title": "Launch new onboarding",
        "status": "In Progress",
        "targetdate": "2024-12-31",
        "owner": "Alex",
        "notes": "First milestone",
    }


def test_parse_goal_add_preserves_goal_prefix():
    command_text = "GOAL-12 Launch new onboarding | status=In Progress"

    parsed = parsing.parse_goal_add(command_text, GOAL_STATUSES)

    assert parsed["goalid"] == "GOAL-12"


def test_parse_goal_status_change_extracts_notes():
    command_text = "#goal:G-7 Completed Released to customers"

    parsed = parsing.parse_goal_status_change(command_text, GOAL_STATUSES)

    assert parsed == {
        "goalid": "G-7",
        "status": "Completed",
        "notes": "Released to customers",
    }


def test_parse_goal_link_supports_prefixes_and_notes():
    command_text = "#goal:G-22 #comp:leadership Added links to monthly review"

    parsed = parsing.parse_goal_link(command_text)

    assert parsed == {
        "goalid": "G-22",
        "competencyid": "leadership",
        "notes": "Added links to monthly review",
    }
