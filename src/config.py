from dataclasses import dataclass
import os
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Centralized configuration loaded from environment variables."""

    telegram_bot_token: str
    spreadsheet_id: Optional[str] = None
    service_account_file: Optional[str] = None
    log_level: str = "INFO"
    timezone: Optional[str] = None
    reminders_enabled: bool = True
    reminder_chat_id: Optional[int] = None
    reminder_day_of_week: str = "fri"
    reminder_hour: int = 15
    reminder_minute: int = 0
    reminder_message: str = "Weekly check-in: what were your top 3 accomplishments this week?"


def load_config() -> Config:
    """Load configuration values from environment variables.

    The function also loads values from a local `.env` file when present to simplify
    development workflows.
    """

    load_dotenv()

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required to start the bot")

    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    service_account_file = os.getenv("SERVICE_ACCOUNT_FILE")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    timezone = os.getenv("TIMEZONE")

    reminders_enabled = os.getenv("REMINDERS_ENABLED", "true").lower() not in {"false", "0", "no"}
    reminder_chat_id = _parse_int(os.getenv("REMINDER_CHAT_ID"))
    reminder_day_of_week = os.getenv("REMINDER_DAY_OF_WEEK", "fri")
    reminder_time = os.getenv("REMINDER_TIME", "15:00")
    reminder_hour, reminder_minute = _parse_time(reminder_time)
    reminder_message = os.getenv(
        "REMINDER_MESSAGE", "Weekly check-in: what were your top 3 accomplishments this week?"
    )

    return Config(
        telegram_bot_token=telegram_bot_token,
        spreadsheet_id=spreadsheet_id,
        service_account_file=service_account_file,
        log_level=log_level,
        timezone=timezone,
        reminders_enabled=reminders_enabled,
        reminder_chat_id=reminder_chat_id,
        reminder_day_of_week=reminder_day_of_week,
        reminder_hour=reminder_hour,
        reminder_minute=reminder_minute,
        reminder_message=reminder_message,
    )


def _parse_int(value: Optional[str]) -> Optional[int]:
    """Safely convert a string to int when provided."""

    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:  # noqa: BLE001
        raise ValueError("REMINDER_CHAT_ID must be an integer") from exc


def _parse_time(value: str) -> tuple[int, int]:
    """Parse a HH:MM string into hour/minute components."""

    try:
        hour_str, minute_str = value.split(":", maxsplit=1)
        hour = int(hour_str)
        minute = int(minute_str)
    except ValueError as exc:  # noqa: BLE001
        raise ValueError("REMINDER_TIME must be provided in HH:MM format") from exc

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("REMINDER_TIME must be a valid 24h time between 00:00 and 23:59")

    return hour, minute
