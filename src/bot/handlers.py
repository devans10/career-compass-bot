import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from src.bot import commands


logger = logging.getLogger(__name__)


def register_handlers(application: Application) -> None:
    """Register command and message handlers with the Telegram application."""

    application.add_handler(CommandHandler("start", commands.start))
    application.add_handler(CommandHandler("help", commands.help_command))
    application.add_handler(CommandHandler("log", commands.log_accomplishment))
    application.add_handler(CommandHandler("task", commands.log_task))
    application.add_handler(CommandHandler("idea", commands.log_idea))
    application.add_handler(CommandHandler("week", commands.get_week_summary))
    application.add_handler(CommandHandler("month", commands.get_month_summary))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, commands.handle_message))
    application.add_handler(MessageHandler(filters.COMMAND, commands.handle_unknown))

    application.add_error_handler(handle_error)

    logger.info("Handlers registered")


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unexpected errors and provide a user-friendly response."""

    logger.exception("Unhandled exception while processing update", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Sorry, something went wrong. Please try again, or /help for options."
        )
