import logging

from telegram.ext import Application, ApplicationBuilder

from src.bot.handlers import register_handlers
from src.config import load_config
from src.logging_config import configure_logging
from src.storage.google_sheets_client import GoogleSheetsClient


logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Create and configure the Telegram application instance."""

    config = load_config()
    configure_logging(config.log_level)

    application = ApplicationBuilder().token(config.telegram_bot_token).build()
    register_handlers(application)

    if config.spreadsheet_id:
        try:
            storage_client = GoogleSheetsClient(
                config.spreadsheet_id, service_account_file=config.service_account_file
            )
            storage_client.ensure_sheet_setup()
            application.bot_data["storage_client"] = storage_client
            logger.info("Storage client initialized", extra={"spreadsheet_id": config.spreadsheet_id})
        except Exception:  # noqa: BLE001
            logger.exception("Failed to initialize storage client")
    else:
        logger.warning("SPREADSHEET_ID not configured; storage features will be unavailable")

    logger.info("Telegram application initialized")
    return application


def main() -> None:
    """Entry point for running the bot via polling."""

    application = build_application()
    logger.info("Starting polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
