import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.ext import ApplicationHandlerStop

from src.bot import handlers


def test_register_handlers_adds_expected_handlers():
    application = MagicMock()

    handlers.register_handlers(application)

    assert application.add_handler.call_count == 25
    application.add_error_handler.assert_called_once_with(handlers.handle_error)


def test_authorize_user_denies_unlisted_user():
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=1),
        effective_message=AsyncMock(),
    )
    context = SimpleNamespace(bot_data={"allowed_user_ids": {2}})

    with pytest.raises(ApplicationHandlerStop):
        asyncio.run(handlers.authorize_user(update, context))

    update.effective_message.reply_text.assert_awaited_once_with("Access denied")


def test_authorize_user_allows_configured_user():
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=99),
        effective_message=AsyncMock(),
    )
    context = SimpleNamespace(bot_data={"allowed_user_ids": {99}})

    asyncio.run(handlers.authorize_user(update, context))

    update.effective_message.reply_text.assert_not_called()


def test_handle_error_logs_and_informs_user(monkeypatch):
    message = AsyncMock()

    class FakeUpdate:
        def __init__(self, msg):
            self.effective_message = msg

    monkeypatch.setattr(handlers, "Update", FakeUpdate)

    update = FakeUpdate(message)
    context = SimpleNamespace(error=RuntimeError("boom"))

    asyncio.run(handlers.handle_error(update, context))

    message.reply_text.assert_awaited_once()
