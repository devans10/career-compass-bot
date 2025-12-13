import asyncio
from datetime import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.bot.scheduler import (
    DEFAULT_REMINDER_MESSAGE,
    ReminderScheduler,
    parse_reminder_time,
    send_reminder_now,
    start_scheduler_from_config,
)


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


def test_shutdown_stops_running_scheduler():
    application = SimpleNamespace(create_task=lambda *args, **kwargs: None, bot=None)
    dummy_scheduler = DummyScheduler()
    dummy_scheduler.running = True
    reminder_scheduler = ReminderScheduler(application=application, chat_id=1, scheduler=dummy_scheduler)

    reminder_scheduler.shutdown()

    assert dummy_scheduler.running is False


def test_enqueue_reminder_submits_coroutine(monkeypatch):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    bot = SimpleNamespace(send_message=AsyncMock())
    application = SimpleNamespace(bot=bot, create_task=loop.create_task)
    scheduler = ReminderScheduler(
        application=application, chat_id=321, scheduler=DummyScheduler(), reminder_message="Hello"
    )

    captured = {}

    def fake_run_coroutine_threadsafe(coro, target_loop):
        captured["coro"] = coro
        captured["loop"] = target_loop

    monkeypatch.setattr(asyncio, "run_coroutine_threadsafe", fake_run_coroutine_threadsafe)

    scheduler._enqueue_reminder()

    assert captured["loop"] is scheduler.loop
    loop.run_until_complete(captured["coro"])
    bot.send_message.assert_awaited_once_with(chat_id=321, text="Hello")

    loop.close()
    asyncio.set_event_loop(None)


def test_send_reminder_now_sends_message():
    bot = SimpleNamespace(send_message=AsyncMock())
    application = SimpleNamespace(bot=bot)

    asyncio.run(send_reminder_now(application, chat_id=42, message="Quick ping"))

    bot.send_message.assert_awaited_once_with(chat_id=42, text="Quick ping")


def test_start_scheduler_from_config_disabled():
    application = SimpleNamespace(bot=None, bot_data={}, create_task=lambda *args, **kwargs: None)
    config = SimpleNamespace(reminders_enabled=False)

    scheduler = start_scheduler_from_config(application, config)

    assert scheduler is None
    assert "reminder_scheduler" not in application.bot_data


def test_start_scheduler_from_config_configures_scheduler(monkeypatch):
    application = SimpleNamespace(bot=None, bot_data={}, create_task=lambda *args, **kwargs: None)
    fake_scheduler = SimpleNamespace(start_weekly=lambda day_of_week, run_time: None)

    def fake_reminder_scheduler(**kwargs):
        fake_scheduler.application = kwargs["application"]
        fake_scheduler.chat_id = kwargs["chat_id"]
        fake_scheduler.reminder_message = kwargs["reminder_message"]
        return fake_scheduler

    monkeypatch.setattr("src.bot.scheduler.ReminderScheduler", fake_reminder_scheduler)

    config = SimpleNamespace(
        reminders_enabled=True,
        reminder_chat_id=7,
        reminder_day_of_week="wed",
        reminder_hour=14,
        reminder_minute=5,
        reminder_message=DEFAULT_REMINDER_MESSAGE,
        timezone="UTC",
    )

    scheduler = start_scheduler_from_config(application, config)

    assert scheduler is fake_scheduler
    assert application.bot_data["reminder_scheduler"] is fake_scheduler
    assert fake_scheduler.chat_id == 7
    assert fake_scheduler.reminder_message == DEFAULT_REMINDER_MESSAGE
