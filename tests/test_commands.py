import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from src.bot import commands


def _make_context(storage_client=None):
    application = SimpleNamespace(bot_data={})
    if storage_client:
        application.bot_data["storage_client"] = storage_client
    return SimpleNamespace(application=application)


def _make_bot_data_only_context(storage_client=None):
    bot_data = {}
    if storage_client:
        bot_data["storage_client"] = storage_client
    return SimpleNamespace(bot_data=bot_data)


def _make_update(text: str):
    message = SimpleNamespace(text=text, reply_text=AsyncMock())
    return SimpleNamespace(message=message)


def test_log_requires_text():
    update = _make_update("/log")
    context = _make_context()

    asyncio.run(commands.log_accomplishment(update, context))

    update.message.reply_text.assert_called_once_with(
        "Please include some text after the command to log it."
    )


def test_log_rejects_long_text():
    update = _make_update("/log " + "x" * (commands.MAX_ENTRY_LENGTH + 1))
    context = _make_context()

    asyncio.run(commands.log_accomplishment(update, context))

    update.message.reply_text.assert_called_once_with(
        "That message is a bit long. Please keep it under 1000 characters."
    )


def test_log_saves_entry_and_confirms():
    storage_client = MagicMock()
    storage_client.append_entry_async = AsyncMock()
    update = _make_update("/task Finish docs #writing")
    context = _make_context(storage_client)

    asyncio.run(commands.log_task(update, context))

    storage_client.append_entry_async.assert_called_once()
    update.message.reply_text.assert_called_with("Logged task: Finish docs #writing\nTags: #writing")


def test_log_handles_storage_errors():
    storage_client = MagicMock()
    storage_client.append_entry_async = AsyncMock(side_effect=Exception("boom"))
    update = _make_update("/log Finish docs")
    context = _make_context(storage_client)

    asyncio.run(commands.log_accomplishment(update, context))

    update.message.reply_text.assert_called_with(
        "Sorry, I couldn't save that right now. Please try again in a moment."
    )


def test_summary_without_storage():
    update = _make_update("/week")
    context = _make_context()

    asyncio.run(commands.get_week_summary(update, context))

    update.message.reply_text.assert_called_once_with(
        "Storage is not configured yet, so I can't fetch entries. Please try again later."
    )


def test_log_uses_bot_data_when_application_missing():
    storage_client = MagicMock()
    storage_client.append_entry_async = AsyncMock()
    update = _make_update("/log Finish docs")
    context = _make_bot_data_only_context(storage_client)

    asyncio.run(commands.log_accomplishment(update, context))

    storage_client.append_entry_async.assert_called_once()


def test_summary_formats_entries():
    storage_client = MagicMock()
    storage_client.get_entries_by_date_range_async = AsyncMock(return_value=[
        {
            "date": "2024-05-01",
            "type": "accomplishment",
            "text": "Shipped release",
            "tags": "#release #infra",
        },
        {
            "date": "2024-05-02",
            "type": "task",
            "text": "Schedule retro",
            "tags": "",
        },
    ])
    update = _make_update("/month")
    context = _make_context(storage_client)

    asyncio.run(commands.get_month_summary(update, context))

    summary_text = "\n".join(line.strip() for line in update.message.reply_text.call_args.args[0].split("\n"))
    assert summary_text.startswith("Entries from")
    assert "• [Accomplishment] 2024-05-01: Shipped release (#release #infra)" in summary_text
    assert "• [Task] 2024-05-02: Schedule retro" in summary_text


def test_summary_handles_storage_failure():
    storage_client = MagicMock()
    storage_client.get_entries_by_date_range_async = AsyncMock(side_effect=Exception("oops"))
    update = _make_update("/week")
    context = _make_context(storage_client)

    asyncio.run(commands.get_week_summary(update, context))

    update.message.reply_text.assert_called_with(
        "Sorry, I couldn't retrieve entries right now. Please try again later."
    )


def test_format_summary_handles_empty_entries():
    start_date = commands._start_date_for_range(7)
    end_date = start_date + commands.timedelta(days=6)

    summary = commands._format_summary([], start_date, end_date)

    assert summary == "No entries found for the last 7 days."


def test_handle_message_prompts_for_command_usage():
    update = _make_update("Just saying hi")
    context = _make_context()

    asyncio.run(commands.handle_message(update, context))

    update.message.reply_text.assert_called_once()


def test_add_goal_requires_id_and_title():
    update = _make_update("/goal_add")
    context = _make_context()

    asyncio.run(commands.add_goal(update, context))

    update.message.reply_text.assert_called_once()


def test_add_goal_saves_to_storage():
    storage_client = MagicMock()
    update = _make_update("/goal_add G-1 Launch platform | status=In Progress")
    context = _make_context(storage_client)

    asyncio.run(commands.add_goal(update, context))

    storage_client.append_goal.assert_called_once()
    update.message.reply_text.assert_called_once()


def test_list_goals_formats_results():
    storage_client = MagicMock()
    storage_client.get_goals.return_value = [
        {
            "goalid": "G-2",
            "title": "Improve onboarding",
            "status": "In Progress",
            "targetdate": "2024-12-31",
            "owner": "Alex",
            "notes": "Pilot phase",
        }
    ]
    update = _make_update("/goal_list")
    context = _make_context(storage_client)

    asyncio.run(commands.list_goals(update, context))

    update.message.reply_text.assert_called_once()
    assert "Improve onboarding" in update.message.reply_text.call_args.args[0]


def test_list_goals_handles_missing_storage():
    update = _make_update("/goal_list")
    context = _make_context()

    asyncio.run(commands.list_goals(update, context))

    update.message.reply_text.assert_called_once()


def test_update_goal_status_handles_missing_goal():
    storage_client = MagicMock()
    storage_client.get_goals.return_value = []
    update = _make_update("/goal_status G-99 Completed")
    context = _make_context(storage_client)

    asyncio.run(commands.update_goal_status(update, context))

    update.message.reply_text.assert_called_once()


def test_update_goal_status_succeeds_and_appends():
    storage_client = MagicMock()
    storage_client.get_goals.return_value = [
        {
            "goalid": "G-1",
            "title": "Ship onboarding",
            "status": "Not Started",
            "targetdate": "",
            "owner": "",
            "notes": "",
        }
    ]
    storage_client.append_goal = MagicMock()
    update = _make_update("/goal_status G-1 Completed Wrapped up")
    context = _make_context(storage_client)

    asyncio.run(commands.update_goal_status(update, context))

    storage_client.append_goal.assert_called_once()
    update.message.reply_text.assert_called_once()


def test_link_goal_requires_reference():
    update = _make_update("/goal_link")
    context = _make_context()

    asyncio.run(commands.link_goal(update, context))

    update.message.reply_text.assert_called_once()


def test_link_goal_appends_mapping():
    storage_client = MagicMock()
    storage_client.append_goal_mapping = MagicMock()
    update = _make_update("/goal_link #goal:G-1 Connected")
    context = _make_context(storage_client)

    asyncio.run(commands.link_goal(update, context))

    storage_client.append_goal_mapping.assert_called_once()
    update.message.reply_text.assert_called_once()


def test_goals_summary_returns_status_counts():
    storage_client = MagicMock()
    storage_client.get_goals.return_value = [
        {
            "goalid": "G-1",
            "title": "Ship onboarding",
            "status": "In Progress",
            "targetdate": "2024-12-31",
            "owner": "Alex",
            "notes": "",
        },
        {
            "goalid": "G-2",
            "title": "Improve quality",
            "status": "Completed",
            "targetdate": "",
            "owner": "",
            "notes": "",
        },
    ]
    update = _make_update("/goals_summary")
    context = _make_context(storage_client)

    asyncio.run(commands.goals_summary(update, context))

    summary_text = update.message.reply_text.call_args.args[0]
    assert "In Progress: 1" in summary_text
    assert "Completed: 1" in summary_text


def test_goals_summary_handles_empty_list():
    storage_client = MagicMock()
    storage_client.get_goals.return_value = []
    update = _make_update("/goals_summary")
    context = _make_context(storage_client)

    asyncio.run(commands.goals_summary(update, context))

    update.message.reply_text.assert_called_once()
