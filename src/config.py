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

    return Config(
        telegram_bot_token=telegram_bot_token,
        spreadsheet_id=spreadsheet_id,
        service_account_file=service_account_file,
        log_level=log_level,
    )
