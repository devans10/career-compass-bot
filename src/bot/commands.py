import logging
from datetime import date, datetime, timedelta
from typing import Dict, List

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.parsing import extract_command_argument, extract_tags, normalize_entry


logger = logging.getLogger(__name__)
MAX_ENTRY_LENGTH = 1000
ENTRY_TYPES = {
    "accomplishment": "Logged accomplishment",
    "task": "Logged task",
    "idea": "Logged idea",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message and basic instructions."""

    message = (
        "Welcome to Career Compass Bot! 🎯\n\n"
        "I can help you keep a running log of accomplishments, tasks, and ideas. "
        "Use the commands below to get started, or send /help for more details.\n\n"
        "• /log <text> — capture an accomplishment\n"
        "• /task <text> — note a follow-up task\n"
        "• /idea <text> — jot down a new idea\n"
        "• /week — see the last 7 days\n"
        "• /month — see the last 30 days"
    )
    if update.message:
        await update.message.reply_text(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide a list of available commands."""

    help_text = (
        "Here are some examples to try:\n\n"
        "• /log Built a prototype for the new dashboard\n"
        "• /task Schedule a follow-up with the analytics team\n"
        "• /idea Explore automating weekly summaries\n"
        "• /week — quick snapshot of the last 7 days\n"
        "• /month — review the last 30 days\n\n"
        "Pro tip: add tags like #infra or #ux anywhere in your message to categorize entries."
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
    """Retrieve a summary for the last 7 days."""

    await _send_summary(update, context, days=7)


async def get_month_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrieve a summary for the last 30 days."""

    await _send_summary(update, context, days=30)


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
    entry_text = extract_command_argument(message_text)

    if not entry_text:
        await update.message.reply_text("Please include some text after the command to log it.")
        return

    if len(entry_text) > MAX_ENTRY_LENGTH:
        await update.message.reply_text("That message is a bit long. Please keep it under 1000 characters.")
        return

    tags = extract_tags(entry_text)
    record = normalize_entry(entry_text, entry_type=entry_type, tags=tags)

    logger.info("Logging %s entry", entry_type)

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text(
            "Storage is not configured yet, so I couldn't save that entry. Please try again later."
        )
        return

    try:
        storage_client.append_entry(record)
    except Exception:
        logger.exception("Failed to append entry to storage")
        await update.message.reply_text(
            "Sorry, I couldn't save that right now. Please try again in a moment."
        )
        return

    confirmation = ENTRY_TYPES.get(entry_type, "Logged entry")
    tag_text = f"\nTags: {' '.join(tags)}" if tags else ""
    await update.message.reply_text(f"{confirmation}: {entry_text}{tag_text}")


async def _send_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int) -> None:
    """Build and send a summary response based on the requested range."""

    if not update.message:
        return

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text(
            "Storage is not configured yet, so I can't fetch entries. Please try again later."
        )
        return

    start_date = _start_date_for_range(days)
    end_date = date.today()

    try:
        entries = storage_client.get_entries_by_date_range(
            start_date.isoformat(), end_date.isoformat()
        )
    except Exception:
        logger.exception("Failed to fetch summary from storage")
        await update.message.reply_text(
            "Sorry, I couldn't retrieve entries right now. Please try again later."
        )
        return

    summary = _format_summary(entries, start_date, end_date)
    await update.message.reply_text(summary)


def _get_storage_client(context: ContextTypes.DEFAULT_TYPE):
    """Retrieve the storage client from the application context."""

    if not hasattr(context, "application"):
        return None

    return context.application.bot_data.get("storage_client")


def _start_date_for_range(days: int) -> date:
    """Return the starting date for the given window inclusive of today."""

    offset = max(days - 1, 0)
    return date.today() - timedelta(days=offset)


def _format_summary(entries: List[Dict[str, str]], start_date: date, end_date: date) -> str:
    """Create a user-friendly summary from retrieved entries."""

    if not entries:
        days = (end_date - start_date).days + 1
        return f"No entries found for the last {days} days."

    lines: List[str] = [
        f"Entries from {start_date.isoformat()} to {end_date.isoformat()}:",
    ]

    for entry in entries:
        entry_date = entry.get("date") or entry.get("timestamp", "")
        entry_type = entry.get("type", "entry").capitalize()
        text = entry.get("text", "").strip()
        tags = entry.get("tags", "")
        tag_suffix = f" ({tags})" if tags else ""
        lines.append(f"• [{entry_type}] {entry_date}: {text}{tag_suffix}")

    return "\n".join(lines)
