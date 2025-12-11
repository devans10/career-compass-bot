import logging

from telegram.ext import Application, ApplicationBuilder

from src.bot.handlers import register_handlers
from src.config import load_config
from src.logging_config import configure_logging


logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Create and configure the Telegram application instance."""

    config = load_config()
    configure_logging(config.log_level)

    application = ApplicationBuilder().token(config.telegram_bot_token).build()
    register_handlers(application)

    logger.info("Telegram application initialized")
    return application


def main() -> None:
    """Entry point for running the bot via polling."""

    application = build_application()
    logger.info("Starting polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
