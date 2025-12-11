import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from src.bot import commands


def _make_context(storage_client=None):
    application = SimpleNamespace(bot_data={})
    if storage_client:
        application.bot_data["storage_client"] = storage_client
    return SimpleNamespace(application=application)


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
    update = _make_update("/task Finish docs #writing")
    context = _make_context(storage_client)

    asyncio.run(commands.log_task(update, context))

    storage_client.append_entry.assert_called_once()
    update.message.reply_text.assert_called_with("Logged task: Finish docs #writing\nTags: #writing")


def test_summary_without_storage():
    update = _make_update("/week")
    context = _make_context()

    asyncio.run(commands.get_week_summary(update, context))

    update.message.reply_text.assert_called_once_with(
        "Storage is not configured yet, so I can't fetch entries. Please try again later."
    )


def test_summary_formats_entries():
    storage_client = MagicMock()
    storage_client.get_entries_by_date_range.return_value = [
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
    ]
    update = _make_update("/month")
    context = _make_context(storage_client)

    asyncio.run(commands.get_month_summary(update, context))

    summary_text = "\n".join(line.strip() for line in update.message.reply_text.call_args.args[0].split("\n"))
    assert summary_text.startswith("Entries from")
    assert "• [Accomplishment] 2024-05-01: Shipped release (#release #infra)" in summary_text
    assert "• [Task] 2024-05-02: Schedule retro" in summary_text
