import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.parsing import (
    build_goal_competency_mappings,
    extract_command_argument,
    extract_goal_and_competency_refs,
    extract_tags,
    normalize_entry,
    parse_goal_add,
    parse_goal_link,
    parse_goal_status_change,
)
from src.storage.google_sheets_client import GOAL_STATUSES


logger = logging.getLogger(__name__)
MAX_ENTRY_LENGTH = 1000
ENTRY_TYPES = {
    "accomplishment": "Logged accomplishment",
    "task": "Logged task",
    "idea": "Logged idea",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message and basic instructions."""

    if update.effective_user:
        logger.info(
            "Received /start command",
            extra={"user_id": update.effective_user.id, "username": update.effective_user.username},
        )
    message = (
        "Welcome to Career Compass Bot! 🎯\n\n"
        "I can help you keep a running log of accomplishments, tasks, and ideas, plus track goals. "
        "Use the commands below to get started, or send /help for more details.\n\n"
        "• /log <text> — capture an accomplishment\n"
        "• /task <text> — note a follow-up task\n"
        "• /idea <text> — jot down a new idea\n"
        "• /goal_add <id> | <title> — add a goal (e.g., status=In Progress)\n"
        "• /goal_list — review saved goals\n"
        "• /week — see the last 7 days\n"
        "• /month — see the last 30 days"
    )
    if update.message:
        await update.message.reply_text(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide a list of available commands."""

    if update.effective_user:
        logger.info(
            "Received /help command",
            extra={"user_id": update.effective_user.id, "username": update.effective_user.username},
        )
    help_text = (
        "Here are some examples to try:\n\n"
        "• /log Built a prototype for the new dashboard\n"
        "• /task Schedule a follow-up with the analytics team\n"
        "• /idea Explore automating weekly summaries\n"
        "• /goal_add GOAL-12 | Ship onboarding revamp | status=In Progress\n"
        "• /goal_status GOAL-12 Completed Shipped to production\n"
        "• /goal_link #goal:GOAL-12 #comp:communication Linked to sprint demo\n"
        "• /week — quick snapshot of the last 7 days\n"
        "• /month — review the last 30 days\n\n"
        "Pro tip: add tags like #infra, goal references like #goal:Q3-Launch, "
        "or competency tags like #comp:communication anywhere in your message."
    )
    if update.message:
        await update.message.reply_text(help_text)


async def log_accomplishment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for logging an accomplishment."""

    logger.info("Handling /log command", extra=_user_context(update))
    await _log_with_type(update, context, entry_type="accomplishment")


async def log_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for logging a task."""

    logger.info("Handling /task command", extra=_user_context(update))
    await _log_with_type(update, context, entry_type="task")


async def log_idea(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Placeholder for logging an idea."""

    logger.info("Handling /idea command", extra=_user_context(update))
    await _log_with_type(update, context, entry_type="idea")


async def get_week_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrieve a summary for the last 7 days."""

    logger.info("Handling /week command", extra=_user_context(update))
    await _send_summary(update, context, days=7)


async def get_month_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retrieve a summary for the last 30 days."""

    logger.info("Handling /month command", extra=_user_context(update))
    await _send_summary(update, context, days=30)


async def add_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a goal record to storage."""

    if not update.message:
        return

    logger.info("Handling /goal_add command", extra=_user_context(update))
    message_text = extract_command_argument(update.message.text or "")

    try:
        goal_fields = parse_goal_add(message_text, GOAL_STATUSES)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    if not goal_fields.get("goalid") or not goal_fields.get("title"):
        await update.message.reply_text(
            "Please provide a goal ID and title. Example: /goal_add GOAL-1 | Improve onboarding | status=Not Started"
        )
        return

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text(
            "Storage is not configured yet, so I couldn't save that goal. Please try again later."
        )
        return

    try:
        await asyncio.to_thread(storage_client.append_goal, goal_fields)
    except Exception:
        logger.exception("Failed to append goal", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't save that goal. Please try again in a moment.")
        return

    await update.message.reply_text(
        f"Saved goal {goal_fields['goalid']} with status {goal_fields['status']}: {goal_fields['title']}"
    )


async def list_goals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all saved goals."""

    if not update.message:
        return

    logger.info("Handling /goal_list command", extra=_user_context(update))
    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't fetch goals.")
        return

    try:
        goals = await asyncio.to_thread(storage_client.get_goals)
    except Exception:
        logger.exception("Failed to fetch goals", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't retrieve goals right now. Please try again later.")
        return

    if not goals:
        await update.message.reply_text("No goals found yet. Add one with /goal_add <id> | <title> | status=Not Started")
        return

    lines = ["Goals:"]
    for goal in goals:
        target = f" (target {goal['targetdate']})" if goal.get("targetdate") else ""
        owner = f" — owner: {goal['owner']}" if goal.get("owner") else ""
        notes = f" — notes: {goal['notes']}" if goal.get("notes") else ""
        lines.append(
            f"• {goal['goalid']}: {goal['title']} [{goal['status']}{target}{owner}{notes}]"
        )

    await update.message.reply_text("\n".join(lines))


async def update_goal_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update the status of an existing goal."""

    if not update.message:
        return

    logger.info("Handling /goal_status command", extra=_user_context(update))
    message_text = extract_command_argument(update.message.text or "")
    try:
        parsed = parse_goal_status_change(message_text, GOAL_STATUSES)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    goal_id = parsed.get("goalid")
    status = parsed.get("status")
    if not goal_id or not status:
        await update.message.reply_text(
            "Please provide a goal and valid status. Example: /goal_status GOAL-1 In Progress Drafting plan"
        )
        return

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't update goals.")
        return

    try:
        goals = await asyncio.to_thread(storage_client.get_goals)
    except Exception:
        logger.exception("Failed to fetch goals for status update", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't load goals to update. Please try again later.")
        return

    existing = next((goal for goal in goals if goal.get("goalid") == goal_id), None)
    if not existing:
        await update.message.reply_text("I couldn't find that goal. Use /goal_list to review IDs.")
        return

    updated = {
        "goalid": goal_id,
        "title": existing.get("title", ""),
        "status": status,
        "targetdate": existing.get("targetdate", ""),
        "owner": existing.get("owner", ""),
        "notes": parsed.get("notes") or existing.get("notes", ""),
    }

    try:
        await asyncio.to_thread(storage_client.append_goal, updated)
    except Exception:
        logger.exception("Failed to append goal status update", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't record that update. Please try again later.")
        return

    await update.message.reply_text(
        f"Updated {goal_id} to '{status}'. Notes: {parsed.get('notes') or 'n/a'}"
    )


async def link_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Link a goal (and optional competency) to the latest work entry timestamp."""

    if not update.message:
        return

    logger.info("Handling /goal_link command", extra=_user_context(update))
    message_text = extract_command_argument(update.message.text or "")
    parsed = parse_goal_link(message_text)

    if not parsed.get("goalid") and not parsed.get("competencyid"):
        await update.message.reply_text(
            "Please include a goal or competency reference. Example: /goal_link #goal:GOAL-1 #comp:communication Linked to sprint demo"
        )
        return

    now = datetime.utcnow()
    mapping = {
        "entrytimestamp": now.isoformat(),
        "entrydate": now.date().isoformat(),
        "goalid": parsed.get("goalid", ""),
        "competencyid": parsed.get("competencyid", ""),
        "notes": parsed.get("notes", ""),
    }

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't link that goal.")
        return

    try:
        await asyncio.to_thread(storage_client.append_goal_mapping, mapping)
    except Exception:
        logger.exception("Failed to append goal mapping", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't record that link. Please try again later.")
        return

    goal_text = parsed.get("goalid") or "(no goal id)"
    comp_text = f" and competency {parsed['competencyid']}" if parsed.get("competencyid") else ""
    await update.message.reply_text(
        f"Linked goal {goal_text}{comp_text}. Notes: {parsed.get('notes') or 'n/a'}"
    )


async def goals_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Summarize goals by status and target dates."""

    if not update.message:
        return

    logger.info("Handling /goals_summary command", extra=_user_context(update))
    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't summarize goals.")
        return

    try:
        goals = await asyncio.to_thread(storage_client.get_goals)
    except Exception:
        logger.exception("Failed to fetch goals for summary", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't retrieve goals right now. Please try again later.")
        return

    if not goals:
        await update.message.reply_text("No goals to summarize yet. Add one with /goal_add <id> | <title>.")
        return

    status_counts: Dict[str, int] = {status: 0 for status in GOAL_STATUSES}
    for goal in goals:
        status_counts[goal.get("status", "Not Started")] = status_counts.get(goal.get("status", ""), 0) + 1

    lines = ["Goals summary:", "", "By status:"]
    for status in sorted(status_counts):
        lines.append(f"• {status}: {status_counts.get(status, 0)}")

    upcoming = [goal for goal in goals if goal.get("targetdate")]
    if upcoming:
        upcoming.sort(key=lambda g: g.get("targetdate"))
        lines.append("")
        lines.append("Target dates:")
        for goal in upcoming:
            owner_text = f" (owner: {goal['owner']})" if goal.get("owner") else ""
            lines.append(
                f"• {goal['targetdate']}: {goal['goalid']} — {goal['title']} [{goal['status']}]"
                f"{owner_text}"
            )

    await update.message.reply_text("\n".join(lines))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-form text messages that are not commands."""

    if not update.message:
        return

    logger.info(
        "Received free-form message", extra={**_user_context(update), "text_length": len(update.message.text or "")}
    )
    await update.message.reply_text(
        "I can log your updates! Try /log, /task, or /idea followed by your text."
    )


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands gracefully."""

    logger.warning("Unknown command received", extra=_user_context(update))
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

    logger.info(
        "Processing structured entry",
        extra={
            **_user_context(update),
            "entry_type": entry_type,
            "text_length": len(entry_text or ""),
        },
    )

    if not entry_text:
        await update.message.reply_text("Please include some text after the command to log it.")
        return

    if len(entry_text) > MAX_ENTRY_LENGTH:
        await update.message.reply_text("That message is a bit long. Please keep it under 1000 characters.")
        return

    tags = extract_tags(entry_text)
    refs = extract_goal_and_competency_refs(entry_text)
    record = normalize_entry(entry_text, entry_type=entry_type, tags=tags)

    storage_client = _get_storage_client(context)
    if not storage_client:
        logger.error("Storage client missing", extra=_user_context(update))
        await update.message.reply_text(
            "Storage is not configured yet, so I couldn't save that entry. Please try again later."
        )
        return

    try:
        await storage_client.append_entry_async(record)
    except Exception:
        logger.exception("Failed to append entry to storage", extra=_user_context(update))
        await update.message.reply_text(
            "Sorry, I couldn't save that right now. Please try again in a moment."
        )
        return

    mappings = build_goal_competency_mappings(
        record["timestamp"], record["date"], refs["goal_ids"], refs["competency_ids"]
    )
    if mappings:
        try:
            await asyncio.gather(
                *[
                    asyncio.to_thread(storage_client.append_goal_mapping, mapping)
                    for mapping in mappings
                ]
            )
        except Exception:
            logger.exception("Failed to append goal/competency mappings", extra=_user_context(update))

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
        logger.info(
            "Fetching summary",
            extra={**_user_context(update), "start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        )
        entries = await storage_client.get_entries_by_date_range_async(
            start_date.isoformat(), end_date.isoformat()
        )
    except Exception:
        logger.exception("Failed to fetch summary from storage", extra=_user_context(update))
        await update.message.reply_text(
            "Sorry, I couldn't retrieve entries right now. Please try again later."
        )
        return

    summary = _format_summary(entries, start_date, end_date)
    await update.message.reply_text(summary)


def _user_context(update: Update) -> Dict[str, object]:
    """Extract a minimal context dict for logging purposes."""

    user = update.effective_user if isinstance(update, Update) else None
    return {
        "user_id": getattr(user, "id", "unknown"),
        "username": getattr(user, "username", None),
        "chat_id": getattr(getattr(update, "effective_chat", None), "id", None),
    }


def _get_storage_client(context: ContextTypes.DEFAULT_TYPE):
    """Retrieve the storage client from the application context."""

    if hasattr(context, "application") and getattr(context.application, "bot_data", None) is not None:
        storage_client = context.application.bot_data.get("storage_client")
        if storage_client:
            return storage_client

    if hasattr(context, "bot_data"):
        return context.bot_data.get("storage_client")

    return None


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
