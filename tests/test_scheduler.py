import asyncio
from datetime import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.bot.scheduler import ReminderScheduler, parse_reminder_time


class DummyScheduler:
    def __init__(self, *_, **__):
        self.jobs = []
        self.running = False

    def add_job(self, func, trigger, day_of_week=None, hour=None, minute=None, id=None, replace_existing=None):
        self.jobs.append(
            {
                "func": func,
                "trigger": trigger,
                "day_of_week": day_of_week,
                "hour": hour,
                "minute": minute,
                "id": id,
                "replace_existing": replace_existing,
            }
        )

    def start(self):
        self.running = True

    def shutdown(self):
        self.running = False


def test_parse_reminder_time_valid():
    parsed = parse_reminder_time("09:30")
    assert parsed == time(hour=9, minute=30)


@pytest.mark.parametrize("invalid", ["25:00", "bad", "12-00", "09:99"])
def test_parse_reminder_time_invalid(invalid):
    with pytest.raises(ValueError):
        parse_reminder_time(invalid)


def test_send_once_dispatches_message():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    bot = SimpleNamespace(send_message=AsyncMock())
    application = SimpleNamespace(bot=bot)
    application.create_task = loop.create_task

    scheduler = ReminderScheduler(
        application=application, chat_id=123, scheduler=DummyScheduler(), reminder_message="Ping"
    )

    task = scheduler.send_once()
    loop.run_until_complete(task)

    bot.send_message.assert_awaited_once_with(chat_id=123, text="Ping")

    loop.close()
    asyncio.set_event_loop(None)


def test_start_weekly_adds_job():
    application = SimpleNamespace(create_task=lambda *args, **kwargs: None, bot=None)
    dummy_scheduler = DummyScheduler()
    reminder_scheduler = ReminderScheduler(
        application=application, chat_id=1, scheduler=dummy_scheduler, reminder_message="Ping"
    )

    reminder_scheduler.start_weekly(day_of_week="mon", run_time=time(hour=10, minute=15))

    assert dummy_scheduler.running is True
    assert dummy_scheduler.jobs == [
        {
            "func": reminder_scheduler._enqueue_reminder,
            "trigger": "cron",
            "day_of_week": "mon",
            "hour": 10,
            "minute": 15,
            "id": "weekly_reminder",
            "replace_existing": True,
        }
    ]
