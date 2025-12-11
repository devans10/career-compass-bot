import logging
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.parsing import extract_tags


logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message and basic instructions."""

    message = (
        "Welcome to Career Compass Bot!\n"
        "Use /log to capture accomplishments, /task for follow-ups, /idea for new ideas, "
        "and /week or /month to review your entries."
    )
    if update.message:
        await update.message.reply_text(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide a list of available commands."""

    help_text = (
        "Here are some things you can try:\n"
        "- /log Built a prototype for the new dashboard\n"
        "- /task Schedule a follow-up with the analytics team\n"
        "- /idea Explore automating weekly summaries\n"
        "- /week to see the last 7 days\n"
        "- /month to see the last 30 days"
    )
    if update.message:
        await update.message.reply_text(help_text)


async def log_accomplishment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for logging an accomplishment."""

    await _log_with_type(update, context, entry_type="accomplishment")


async def log_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for logging a task."""

    await _log_with_type(update, context, entry_type="task")


async def log_idea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for logging an idea."""

    await _log_with_type(update, context, entry_type="idea")


async def get_week_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrieve a placeholder summary for the last 7 days."""

    await _send_summary(update, days=7)


async def get_month_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrieve a placeholder summary for the last 30 days."""

    await _send_summary(update, days=30)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-form text messages that are not commands."""

    if not update.message:
        return

    await update.message.reply_text(
        "I can log your updates! Try /log, /task, or /idea followed by your text."
    )


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands gracefully."""

    if update.message:
        await update.message.reply_text("Sorry, I don't recognize that command. Try /help for options.")


async def _log_with_type(
    update: Update, context: ContextTypes.DEFAULT_TYPE, entry_type: str
) -> None:
    """Common helper for logging entries of different types."""

    if not update.message:
        return

    message_text = update.message.text or ""
    tags = extract_tags(message_text)

    logger.debug("Received %s entry: %s", entry_type, message_text)
    await update.message.reply_text(
        f"(Placeholder) Logged {entry_type}: {message_text}\nTags: {' '.join(tags)}"
    )


async def _send_summary(update: Update, days: int) -> None:
    """Placeholder summary response based on the requested range."""

    if not update.message:
        return

    start_date = (datetime.utcnow() - timedelta(days=days)).date()
    await update.message.reply_text(
        f"(Placeholder) Showing entries since {start_date.isoformat()} for the last {days} days."
    )
