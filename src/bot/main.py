import logging

from telegram.ext import Application, ApplicationBuilder

from src.bot.ai_client import AIClient
from src.bot.ai_summarizer import create_ai_summarizer
from src.bot.handlers import register_handlers
from src.bot.scheduler import start_scheduler_from_config
from src.config import load_config
from src.logging_config import configure_logging
from src.storage.google_sheets_client import GoogleSheetsClient


logger = logging.getLogger(__name__)


def build_application() -> Application:
    """Create and configure the Telegram application instance."""

    try:
        config = load_config()
    except ValueError as exc:
        logger.critical("Configuration error: %s", exc)
        raise
    configure_logging(config.log_level, config.timezone)

    application = ApplicationBuilder().token(config.telegram_bot_token).build()
    application.bot_data["allowed_user_ids"] = config.telegram_allowed_users
    register_handlers(application)

    if config.spreadsheet_id:
        try:
            storage_client = GoogleSheetsClient(
                config.spreadsheet_id,
                service_account_file=config.service_account_file,
                service_account_json=config.service_account_json,
            )
            storage_client.ensure_sheet_setup()
            application.bot_data["storage_client"] = storage_client
            logger.info("Storage client initialized", extra={"spreadsheet_id": config.spreadsheet_id})
        except Exception:  # noqa: BLE001
            logger.exception("Failed to initialize storage client")
    else:
        logger.warning("SPREADSHEET_ID not configured; storage features will be unavailable")

    if config.ai_api_key and config.ai_model:
        ai_client = AIClient(
            api_key=config.ai_api_key,
            model=config.ai_model,
            endpoint=config.ai_endpoint,
        )
        application.bot_data["ai_client"] = ai_client
        application.bot_data["ai_summarizer"] = create_ai_summarizer(ai_client)
        logger.info(
            "AI client initialized",
            extra={"ai_model": config.ai_model, "ai_endpoint": config.ai_endpoint},
        )
    elif any((config.ai_api_key, config.ai_model, config.ai_endpoint)):
        logger.warning(
            "AI provider configuration is incomplete; provide AI_API_KEY and AI_MODEL to enable it",
        )

    logger.info("Telegram application initialized")
    start_scheduler_from_config(application, config)
    return application


def main() -> None:
    """Entry point for running the bot via polling."""

    application = build_application()
    logger.info("Starting polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
