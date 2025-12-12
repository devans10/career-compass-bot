import pytest

from src.config import load_config


def test_load_config_parses_allowed_users(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("SPREADSHEET_ID", "spreadsheet")
    monkeypatch.setenv("SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "1001, 2002")
    monkeypatch.setenv("REMINDERS_ENABLED", "false")

    config = load_config()

    assert config.telegram_allowed_users == (1001, 2002)


def test_load_config_rejects_invalid_allowed_users(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("SPREADSHEET_ID", "spreadsheet")
    monkeypatch.setenv("SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", "1001, abc")
    monkeypatch.setenv("REMINDERS_ENABLED", "false")

    with pytest.raises(ValueError):
        load_config()
