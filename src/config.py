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
    telegram_allowed_users: tuple[int, ...] = ()
    service_account_file: Optional[str] = None
    service_account_json: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_model: Optional[str] = None
    ai_endpoint: Optional[str] = None
    log_level: str = "INFO"
    timezone: str = "UTC"
    reminders_enabled: bool = True
    reminder_chat_id: Optional[int] = None
    reminder_day_of_week: str = "fri"
    reminder_hour: int = 15
    reminder_minute: int = 0
    reminder_message: str = "Weekly check-in: what were your top 3 accomplishments this week?"
    focus_reminders_enabled: bool = True
    focus_reminder_day_of_week: str = "mon"
    focus_reminder_hour: int = 9
    focus_reminder_minute: int = 0
    focus_reminder_message: str = "Here are a few goals and milestones to focus on this week."
    focus_upcoming_window_days: int = 14
    focus_inactivity_days: int = 14


def load_config() -> Config:
    """Load configuration values from environment variables.

    The function also loads values from a local `.env` file when present to simplify
    development workflows.
    """

    load_dotenv()

    telegram_bot_token = _require("TELEGRAM_BOT_TOKEN")
    spreadsheet_id = _require("SPREADSHEET_ID")
    telegram_allowed_users = _parse_int_list(os.getenv("TELEGRAM_ALLOWED_USERS"))
    service_account_file = os.getenv("SERVICE_ACCOUNT_FILE")
    service_account_json = os.getenv("SERVICE_ACCOUNT_JSON")
    ai_api_key = os.getenv("AI_API_KEY")
    ai_model = os.getenv("AI_MODEL")
    ai_endpoint = os.getenv("AI_ENDPOINT")
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

    focus_reminders_enabled = os.getenv("FOCUS_REMINDERS_ENABLED", "true").lower() not in {
        "false",
        "0",
        "no",
    }
    focus_reminder_day_of_week = _validate_day_of_week(os.getenv("FOCUS_REMINDER_DAY_OF_WEEK", "mon"))
    focus_reminder_time = os.getenv("FOCUS_REMINDER_TIME", "09:00")
    focus_reminder_hour, focus_reminder_minute = _parse_time(focus_reminder_time)
    focus_reminder_message = os.getenv(
        "FOCUS_REMINDER_MESSAGE", "Here are a few goals and milestones to focus on this week."
    )
    focus_upcoming_window_days = _parse_positive_int(os.getenv("FOCUS_UPCOMING_WINDOW_DAYS", "14"))
    focus_inactivity_days = _parse_positive_int(os.getenv("FOCUS_INACTIVITY_DAYS", "14"))

    if reminders_enabled and reminder_chat_id is None:
        raise ValueError("REMINDER_CHAT_ID is required when REMINDERS_ENABLED is true")

    return Config(
        telegram_bot_token=telegram_bot_token,
        spreadsheet_id=spreadsheet_id,
        telegram_allowed_users=telegram_allowed_users,
        service_account_file=service_account_file,
        service_account_json=service_account_json,
        ai_api_key=ai_api_key,
        ai_model=ai_model,
        ai_endpoint=ai_endpoint,
        log_level=log_level,
        timezone=timezone,
        reminders_enabled=reminders_enabled,
        reminder_chat_id=reminder_chat_id,
        reminder_day_of_week=reminder_day_of_week,
        reminder_hour=reminder_hour,
        reminder_minute=reminder_minute,
        reminder_message=reminder_message,
        focus_reminders_enabled=focus_reminders_enabled,
        focus_reminder_day_of_week=focus_reminder_day_of_week,
        focus_reminder_hour=focus_reminder_hour,
        focus_reminder_minute=focus_reminder_minute,
        focus_reminder_message=focus_reminder_message,
        focus_upcoming_window_days=focus_upcoming_window_days,
        focus_inactivity_days=focus_inactivity_days,
    )


def _parse_int(value: Optional[str]) -> Optional[int]:
    """Safely convert a string to int when provided."""

    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:  # noqa: BLE001
        raise ValueError("REMINDER_CHAT_ID must be an integer") from exc


def _parse_int_list(value: Optional[str]) -> tuple[int, ...]:
    """Parse a comma-separated list of integers into a tuple."""

    if not value:
        return ()

    values = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(int(item))
        except ValueError as exc:  # noqa: BLE001
            raise ValueError("TELEGRAM_ALLOWED_USERS must contain only integers") from exc

    return tuple(values)


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


def _parse_positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:  # noqa: BLE001
        raise ValueError("Provide a valid integer value for reminder windows") from exc
    if parsed < 1:
        raise ValueError("Reminder windows must be positive integers")
    return parsed


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
