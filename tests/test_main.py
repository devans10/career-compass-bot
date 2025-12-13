from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.bot import main
from src.config import Config


@pytest.fixture
def fake_application():
    application = SimpleNamespace(bot_data={}, create_task=lambda *args, **kwargs: None)
    application.run_polling = MagicMock()
    return application


def test_build_application_configures_app(monkeypatch, fake_application):
    config = Config(
        telegram_bot_token="token",
        spreadsheet_id="spreadsheet",
        telegram_allowed_users=(1, 2),
        service_account_json="{}",
    )

    fake_builder = MagicMock()
    fake_builder.token.return_value = fake_builder
    fake_builder.build.return_value = fake_application

    google_client = MagicMock()
    monkeypatch.setattr(main, "ApplicationBuilder", MagicMock(return_value=fake_builder))
    monkeypatch.setattr(main, "configure_logging", MagicMock())
    monkeypatch.setattr(main, "register_handlers", MagicMock())
    monkeypatch.setattr(main, "GoogleSheetsClient", MagicMock(return_value=google_client))
    monkeypatch.setattr(main, "start_scheduler_from_config", MagicMock())
    monkeypatch.setattr(main, "load_config", MagicMock(return_value=config))

    application = main.build_application()

    assert application is fake_application
    main.configure_logging.assert_called_once_with(config.log_level, config.timezone)
    main.register_handlers.assert_called_once_with(fake_application)
    google_client.ensure_sheet_setup.assert_called_once_with()
    assert fake_application.bot_data["allowed_user_ids"] == config.telegram_allowed_users
    assert fake_application.bot_data["storage_client"] is google_client
    main.start_scheduler_from_config.assert_called_once_with(fake_application, config)


def test_build_application_without_storage(monkeypatch, fake_application):
    config = Config(
        telegram_bot_token="token",
        spreadsheet_id="",
        telegram_allowed_users=(),
        service_account_json="{}",
        reminders_enabled=False,
    )

    fake_builder = MagicMock()
    fake_builder.token.return_value = fake_builder
    fake_builder.build.return_value = fake_application

    monkeypatch.setattr(main, "ApplicationBuilder", MagicMock(return_value=fake_builder))
    monkeypatch.setattr(main, "configure_logging", MagicMock())
    monkeypatch.setattr(main, "register_handlers", MagicMock())
    monkeypatch.setattr(main, "GoogleSheetsClient", MagicMock())
    monkeypatch.setattr(main, "start_scheduler_from_config", MagicMock())
    monkeypatch.setattr(main, "load_config", MagicMock(return_value=config))

    application = main.build_application()

    assert application is fake_application
    assert "storage_client" not in fake_application.bot_data
