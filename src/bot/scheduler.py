"""Scheduling helpers for proactive reminders."""

from __future__ import annotations

import importlib.util
import asyncio
import logging
from datetime import date, datetime, time, timedelta
from typing import Callable, List, Optional
from zoneinfo import ZoneInfo

if importlib.util.find_spec("apscheduler"):
    from apscheduler.schedulers.background import BackgroundScheduler
else:  # pragma: no cover - fallback for environments without APScheduler installed
    class BackgroundScheduler:  # type: ignore[misc]
        def __init__(self, *_, **__):
            self.jobs = []
            self.running = False

        def add_job(
            self,
            func,
            trigger,
            day_of_week=None,
            hour=None,
            minute=None,
            id=None,
            replace_existing=None,
        ) -> None:
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

        def start(self) -> None:
            self.running = True

        def shutdown(self) -> None:
            self.running = False

if importlib.util.find_spec("telegram"):
    from telegram.ext import Application
else:  # pragma: no cover - fallback to allow tests without telegram installed
    class Application:  # type: ignore[misc]
        def __init__(self, *_, **__):
            self.bot = None

        def create_task(self, coro):  # noqa: ANN001
            return coro

try:
    from asyncio import AbstractEventLoop
except ImportError:  # pragma: no cover - Python <3.10 fallback
    AbstractEventLoop = asyncio.AbstractEventLoop

logger = logging.getLogger(__name__)

DEFAULT_REMINDER_MESSAGE = "Weekly check-in: what were your top 3 accomplishments this week?"
DEFAULT_FOCUS_MESSAGE = "Here are a few goals and milestones to focus on this week."


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
        message_builder: Optional[Callable[[], str]] = None,
        tz: Optional[str] = None,
        scheduler: Optional[BackgroundScheduler] = None,
    ) -> None:
        self.application = application
        self.chat_id = chat_id
        self.reminder_message = reminder_message
        self.message_builder = message_builder
        try:
            self.loop: AbstractEventLoop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        self.scheduler = scheduler or BackgroundScheduler(timezone=tz)

    def start_weekly(
        self,
        day_of_week: str = "fri",
        run_time: time = time(hour=15),
        job_id: str = "weekly_reminder",
    ) -> None:
        """Start a weekly job that triggers the provided callback."""

        self.scheduler.add_job(
            self._enqueue_reminder,
            "cron",
            day_of_week=day_of_week,
            hour=run_time.hour,
            minute=run_time.minute,
            id=job_id,
            replace_existing=True,
        )
        if not self.scheduler.running:
            self.scheduler.start()
        logger.info(
            "Weekly reminder scheduled",
            extra={"day_of_week": day_of_week, "hour": run_time.hour, "minute": run_time.minute},
        )

    def _enqueue_reminder(self) -> None:
        """Push the reminder coroutine into the Telegram application's event loop."""

        message = self.reminder_message
        if self.message_builder:
            try:
                message = self.message_builder()
            except Exception:  # noqa: BLE001
                logger.exception("Failed to build reminder message", extra={"chat_id": self.chat_id})
        logger.info(
            "Queueing reminder send",
            extra={"chat_id": self.chat_id, "reminder_message": (message or "")[:80]},
        )
        asyncio.run_coroutine_threadsafe(self._send_reminder(message), self.loop)

    async def _send_reminder(self, message: Optional[str] = None) -> None:
        """Send the reminder message to the configured chat."""

        try:
            await self.application.bot.send_message(chat_id=self.chat_id, text=message or self.reminder_message)
            logger.info("Reminder sent", extra={"chat_id": self.chat_id})
        except Exception:  # noqa: BLE001
            logger.exception("Failed to send reminder", extra={"chat_id": self.chat_id})

    def send_once(self) -> asyncio.Task[None]:
        """Trigger a reminder immediately (useful for cron or manual runs)."""

        message = self.reminder_message
        if self.message_builder:
            try:
                message = self.message_builder()
            except Exception:  # noqa: BLE001
                logger.exception("Failed to build reminder message", extra={"chat_id": self.chat_id})
        logger.info("Dispatching immediate reminder", extra={"chat_id": self.chat_id})
        return self.application.create_task(self._send_reminder(message))

    def shutdown(self) -> None:
        """Shut down the scheduler if running."""

        if self.scheduler.running:
            self.scheduler.shutdown()


def _parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _goal_is_active(goal: dict) -> bool:
    status = (goal.get("status") or "").strip()
    lifecycle = (goal.get("lifecyclestatus") or "").strip().lower()
    archived_flag = str(goal.get("archived", "")).strip().lower()
    if lifecycle == "archived" or archived_flag in {"true", "1", "yes"}:
        return False
    return status not in {"Completed"}


def _format_upcoming_line(prefix: str, title: str, target: date, status: str) -> str:
    days_until = (target - date.today()).days
    countdown = "due today" if days_until == 0 else f"due in {days_until} days"
    return f"• {prefix}{title} — {countdown} ({status})"


def _collect_last_activity_by_goal(mappings: List[dict]) -> dict:
    last_activity: dict[str, date] = {}
    for mapping in mappings:
        goal_id = mapping.get("goalid") or mapping.get("goal_id") or mapping.get("goal")
        if not goal_id:
            continue
        entry_date_str = mapping.get("entrydate") or mapping.get("entry_date")
        if not entry_date_str and mapping.get("entrytimestamp"):
            entry_date_str = mapping.get("entrytimestamp").split("T", maxsplit=1)[0]
        parsed_date = _parse_date(entry_date_str or "")
        if not parsed_date:
            continue
        if goal_id not in last_activity or parsed_date > last_activity[goal_id]:
            last_activity[goal_id] = parsed_date
    return last_activity


def build_weekly_focus_message(
    storage_client,
    timezone: str,
    upcoming_window_days: int = 14,
    inactivity_days: int = 14,
) -> str:
    """Build a Monday reminder that highlights upcoming and inactive goals."""

    today = datetime.now(ZoneInfo(timezone)).date()
    upcoming_cutoff = today + timedelta(days=upcoming_window_days)
    stale_cutoff = today - timedelta(days=inactivity_days)

    try:
        goals = storage_client.get_goals()
    except Exception:  # noqa: BLE001
        logger.exception("Unable to load goals for focus reminder")
        goals = []

    try:
        milestones = storage_client.get_goal_milestones()
    except Exception:  # noqa: BLE001
        logger.exception("Unable to load milestones for focus reminder")
        milestones = []

    try:
        mappings = storage_client.get_goal_mappings()
    except Exception:  # noqa: BLE001
        logger.exception("Unable to load goal mappings for focus reminder")
        mappings = []

    last_activity = _collect_last_activity_by_goal(mappings)

    upcoming_lines: List[str] = []
    for goal in goals:
        target_date = _parse_date(goal.get("targetdate") or goal.get("target_date") or "")
        if not target_date or target_date > upcoming_cutoff:
            continue
        if target_date < today - timedelta(days=1):
            continue
        if not _goal_is_active(goal):
            continue
        title = goal.get("title") or goal.get("goalid") or "Goal"
        upcoming_lines.append(
            _format_upcoming_line(f"Goal {goal.get('goalid', '')}: ", title, target_date, goal.get("status", ""))
        )

    for milestone in milestones:
        status = milestone.get("status", "")
        if status == "Completed":
            continue
        target_date = _parse_date(milestone.get("targetdate") or milestone.get("target_date") or "")
        if not target_date or target_date > upcoming_cutoff:
            continue
        if target_date < today - timedelta(days=1):
            continue
        goal_prefix = milestone.get("goalid", "")
        title = milestone.get("title") or milestone.get("milestone") or "Milestone"
        prefix = f"Milestone {goal_prefix}: " if goal_prefix else "Milestone: "
        upcoming_lines.append(_format_upcoming_line(prefix, title, target_date, status))

    stale_lines: List[str] = []
    for goal in goals:
        if not _goal_is_active(goal):
            continue
        goal_id = goal.get("goalid", "")
        last_date = last_activity.get(goal_id)
        if last_date and last_date >= stale_cutoff:
            continue
        if not goal_id:
            continue
        last_seen = last_date.isoformat() if last_date else "no activity yet"
        stale_lines.append(
            f"• {goal_id} — {goal.get('title', '').strip() or 'Goal'} (last update: {last_seen})"
        )

    lines: List[str] = [DEFAULT_FOCUS_MESSAGE]
    if upcoming_lines:
        lines.extend(["", "Upcoming target dates:"])
        lines.extend(sorted(upcoming_lines))
    if stale_lines:
        lines.extend(["", "Goals to re-engage:"])
        lines.extend(sorted(stale_lines))

    if len(lines) == 1:
        lines.append("")
        lines.append("No upcoming deadlines or inactive goals detected. Have a focused week!")

    return "\n".join(lines)


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
    shared_scheduler = BackgroundScheduler(timezone=getattr(config, "timezone", None))

    scheduler = ReminderScheduler(
        application=application,
        chat_id=chat_id,
        reminder_message=getattr(config, "reminder_message", DEFAULT_REMINDER_MESSAGE),
        tz=getattr(config, "timezone", None),
        scheduler=shared_scheduler,
    )
    scheduler.start_weekly(
        day_of_week=getattr(config, "reminder_day_of_week", "fri"),
        run_time=reminder_time,
        job_id="weekly_reflection_reminder",
    )
    application.bot_data["reminder_scheduler"] = scheduler

    if getattr(config, "focus_reminders_enabled", True):
        storage_client = application.bot_data.get("storage_client")
        if storage_client:
            focus_time = time(
                hour=getattr(config, "focus_reminder_hour", 9),
                minute=getattr(config, "focus_reminder_minute", 0),
            )
            focus_scheduler = ReminderScheduler(
                application=application,
                chat_id=chat_id,
                reminder_message=getattr(config, "focus_reminder_message", DEFAULT_FOCUS_MESSAGE),
                message_builder=lambda: build_weekly_focus_message(
                    storage_client,
                    timezone=getattr(config, "timezone", "UTC"),
                    upcoming_window_days=getattr(config, "focus_upcoming_window_days", 14),
                    inactivity_days=getattr(config, "focus_inactivity_days", 14),
                ),
                tz=getattr(config, "timezone", None),
                scheduler=shared_scheduler,
            )
            focus_scheduler.start_weekly(
                day_of_week=getattr(config, "focus_reminder_day_of_week", "mon"),
                run_time=focus_time,
                job_id="weekly_focus_reminder",
            )
            application.bot_data["focus_reminder_scheduler"] = focus_scheduler
        else:
            logger.info("Skipping focus reminder scheduler; storage is not configured")

    return scheduler


async def send_reminder_now(application: Application, chat_id: int, message: str = DEFAULT_REMINDER_MESSAGE) -> None:
    """Send a reminder immediately without starting the persistent scheduler."""

    await application.bot.send_message(chat_id=chat_id, text=message)
