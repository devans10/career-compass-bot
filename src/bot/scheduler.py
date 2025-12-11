"""Scheduling helpers for proactive reminders."""

from __future__ import annotations

import asyncio
import logging
from datetime import time
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from telegram.ext import Application

try:
    from asyncio import AbstractEventLoop
except ImportError:  # pragma: no cover - Python <3.10 fallback
    AbstractEventLoop = asyncio.AbstractEventLoop

logger = logging.getLogger(__name__)

DEFAULT_REMINDER_MESSAGE = "Weekly check-in: what were your top 3 accomplishments this week?"


def parse_reminder_time(reminder_time: str) -> time:
    """Parse a HH:MM string into a :class:`datetime.time` object."""

    try:
        hour_str, minute_str = reminder_time.split(":", maxsplit=1)
        hour = int(hour_str)
        minute = int(minute_str)
    except ValueError as exc:  # noqa: BLE001
        raise ValueError("REMINDER_TIME must be in HH:MM format, e.g., 15:30") from exc

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("REMINDER_TIME values must be a valid 24h time (00:00-23:59)")

    return time(hour=hour, minute=minute)


class ReminderScheduler:
    """Schedule weekly reminders for the bot."""

    def __init__(
        self,
        application: Application,
        chat_id: int,
        reminder_message: str = DEFAULT_REMINDER_MESSAGE,
        tz: Optional[str] = None,
        scheduler: Optional[BackgroundScheduler] = None,
    ) -> None:
        self.application = application
        self.chat_id = chat_id
        self.reminder_message = reminder_message
        try:
            self.loop: AbstractEventLoop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        self.scheduler = scheduler or BackgroundScheduler(timezone=tz)

    def start_weekly(self, day_of_week: str = "fri", run_time: time = time(hour=15)) -> None:
        """Start a weekly job that triggers the provided callback."""

        self.scheduler.add_job(
            self._enqueue_reminder,
            "cron",
            day_of_week=day_of_week,
            hour=run_time.hour,
            minute=run_time.minute,
            id="weekly_reminder",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(
            "Weekly reminder scheduled",
            extra={"day_of_week": day_of_week, "hour": run_time.hour, "minute": run_time.minute},
        )

    def _enqueue_reminder(self) -> None:
        """Push the reminder coroutine into the Telegram application's event loop."""

        asyncio.run_coroutine_threadsafe(self._send_reminder(), self.loop)

    async def _send_reminder(self) -> None:
        """Send the reminder message to the configured chat."""

        await self.application.bot.send_message(chat_id=self.chat_id, text=self.reminder_message)

    def send_once(self) -> asyncio.Task[None]:
        """Trigger a reminder immediately (useful for cron or manual runs)."""

        return self.application.create_task(self._send_reminder())

    def shutdown(self) -> None:
        """Shut down the scheduler if running."""

        if self.scheduler.running:
            self.scheduler.shutdown()


def start_scheduler_from_config(application: Application, config) -> Optional[ReminderScheduler]:
    """Start the weekly reminder scheduler if configuration permits."""

    if not getattr(config, "reminders_enabled", True):
        logger.info("Reminders are disabled via configuration")
        return None

    chat_id = getattr(config, "reminder_chat_id", None)
    if chat_id is None:
        logger.warning("REMINDER_CHAT_ID not set; skipping scheduler startup")
        return None

    reminder_time = time(
        hour=getattr(config, "reminder_hour", 15), minute=getattr(config, "reminder_minute", 0)
    )
    scheduler = ReminderScheduler(
        application=application,
        chat_id=chat_id,
        reminder_message=getattr(config, "reminder_message", DEFAULT_REMINDER_MESSAGE),
        tz=getattr(config, "timezone", None),
    )
    scheduler.start_weekly(
        day_of_week=getattr(config, "reminder_day_of_week", "fri"), run_time=reminder_time
    )
    application.bot_data["reminder_scheduler"] = scheduler
    return scheduler


async def send_reminder_now(application: Application, chat_id: int, message: str = DEFAULT_REMINDER_MESSAGE) -> None:
    """Send a reminder immediately without starting the persistent scheduler."""

    await application.bot.send_message(chat_id=chat_id, text=message)
