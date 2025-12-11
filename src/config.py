import json
import os
from dataclasses import dataclass
from typing import Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass
class Config:
    """Centralized configuration loaded from environment variables."""

    telegram_bot_token: str
    spreadsheet_id: str
    service_account_file: Optional[str] = None
    service_account_json: Optional[str] = None
    log_level: str = "INFO"
    timezone: str = "UTC"
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

    telegram_bot_token = _require("TELEGRAM_BOT_TOKEN")
    spreadsheet_id = _require("SPREADSHEET_ID")
    service_account_file = os.getenv("SERVICE_ACCOUNT_FILE")
    service_account_json = os.getenv("SERVICE_ACCOUNT_JSON")
    if not (service_account_file or service_account_json):
        raise ValueError(
            "Provide SERVICE_ACCOUNT_FILE or SERVICE_ACCOUNT_JSON for Google Sheets access",
        )

    _validate_json_payload(service_account_json)

    log_level = os.getenv("LOG_LEVEL", "INFO")
    timezone = os.getenv("TIMEZONE", "UTC")
    _validate_timezone(timezone)

    reminders_enabled = os.getenv("REMINDERS_ENABLED", "true").lower() not in {"false", "0", "no"}
    reminder_chat_id = _parse_int(os.getenv("REMINDER_CHAT_ID"))
    reminder_day_of_week = _validate_day_of_week(os.getenv("REMINDER_DAY_OF_WEEK", "fri"))
    reminder_time = os.getenv("REMINDER_TIME", "15:00")
    reminder_hour, reminder_minute = _parse_time(reminder_time)
    reminder_message = os.getenv(
        "REMINDER_MESSAGE", "Weekly check-in: what were your top 3 accomplishments this week?"
    )

    if reminders_enabled and reminder_chat_id is None:
        raise ValueError("REMINDER_CHAT_ID is required when REMINDERS_ENABLED is true")

    return Config(
        telegram_bot_token=telegram_bot_token,
        spreadsheet_id=spreadsheet_id,
        service_account_file=service_account_file,
        service_account_json=service_account_json,
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


def _validate_timezone(value: str) -> None:
    """Ensure provided timezone is valid for ZoneInfo."""

    try:
        ZoneInfo(value)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("TIMEZONE must be a valid IANA timezone, e.g., 'UTC' or 'America/New_York'") from exc


def _validate_day_of_week(value: str) -> str:
    """Normalize and validate day-of-week abbreviations."""

    normalized = value.lower()
    valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    if normalized not in valid_days:
        raise ValueError("REMINDER_DAY_OF_WEEK must be one of: mon, tue, wed, thu, fri, sat, sun")
    return normalized


def _validate_json_payload(value: Optional[str]) -> None:
    """Validate that provided JSON string is parseable."""

    if not value:
        return
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("SERVICE_ACCOUNT_JSON must be valid JSON if provided") from exc

    if not isinstance(parsed, dict):
        raise ValueError("SERVICE_ACCOUNT_JSON must represent a JSON object")


def _require(var_name: str) -> str:
    """Fetch and assert that an environment variable is present."""

    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"{var_name} is required to start the bot")
    return value
