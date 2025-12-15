import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.bot import commands
from src.storage.google_sheets_client import (
    COMPETENCY_HEADERS,
    GOAL_HEADERS,
    GOAL_MAPPING_HEADERS,
    GoogleSheetsClient,
)
from tests.fakes import FakeSheetsService


def _make_context(storage_client):
    application = SimpleNamespace(bot_data={"storage_client": storage_client})
    return SimpleNamespace(application=application)


def _make_update(text: str):
    message = SimpleNamespace(text=text, reply_text=AsyncMock())
    return SimpleNamespace(message=message)


def test_goal_add_and_list_flow_with_fake_sheets():
    service = FakeSheetsService()
    service.ensure_sheet("Goals")["header"] = GOAL_HEADERS
    client = GoogleSheetsClient("spreadsheet-id", service=service)
    context = _make_context(client)

    add_update = _make_update("/goal_add GOAL-55 Ship beta | status=In Progress | owner=Alex")
    asyncio.run(commands.add_goal(add_update, context))

    goals_sheet = service.ensure_sheet("Goals")
    assert goals_sheet["values"][0][0] == "GOAL-55"
    assert goals_sheet["values"][0][1] == "Ship beta"
    assert goals_sheet["values"][0][4] == "In Progress"

    list_update = _make_update("/goal_list")
    asyncio.run(commands.list_goals(list_update, context))

    reply_text = list_update.message.reply_text.call_args.args[0]
    assert "GOAL-55" in reply_text
    assert "In Progress" in reply_text
    assert "owner Alex" in reply_text


def test_entry_logging_and_goal_mapping_flow_with_fake_sheets():
    service = FakeSheetsService()
    service.ensure_sheet("GoalMappings")["header"] = GOAL_MAPPING_HEADERS
    goals_sheet = service.ensure_sheet("Goals")
    goals_sheet["header"] = GOAL_HEADERS
    comps_sheet = service.ensure_sheet("Competencies")
    comps_sheet["header"] = COMPETENCY_HEADERS
    client = GoogleSheetsClient("spreadsheet-id", service=service)

    client.append_goal({"goalid": "GOAL-1", "title": "Ship beta", "status": "In Progress"})
    client.append_competency(
        {"competencyid": "communication", "name": "Communication", "status": "Active"}
    )

    context = _make_context(client)
    log_update = _make_update("/log Completed rollout #goal:GOAL-1 #comp:communication")
    asyncio.run(commands.log_accomplishment(log_update, context))

    accomplishments = service.ensure_sheet("Accomplishments")["values"]
    assert any("Completed rollout" in row[3] for row in accomplishments)

    mappings = service.ensure_sheet("GoalMappings")["values"]
    assert mappings
    assert any(row[2] == "GOAL-1" and row[3] == "communication" for row in mappings)

    summary_update = _make_update("/week")
    asyncio.run(commands.get_week_summary(summary_update, context))

    summary = summary_update.message.reply_text.call_args.args[0]
    assert "GOAL-1" in summary
    assert "Communication" in summary
