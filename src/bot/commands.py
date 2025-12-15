import asyncio
import inspect
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
    parse_goal_edit,
    parse_goal_evaluation,
    parse_goal_link,
    parse_goal_milestone,
    parse_goal_review,
    parse_goal_status_change,
    parse_reminder_setting,
)
from src.storage.google_sheets_client import (
    GOAL_LIFECYCLE_STATUSES,
    GOAL_MILESTONE_STATUSES,
    GOAL_STATUSES,
)


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
        "• /goal_milestone_add <id> | <milestone> — track milestones\n"
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
        "• /goal_milestone_add GOAL-12 | Launch beta | target=2024-09-01\n"
        "• /review_midyear GOAL-12 | rating=Strong | notes=Great trajectory\n"
        "• /eval_goal GOAL-12 | rating=Exceeds | notes=Impact summary\n"
        "• /reminder_settings category=milestone | frequency=weekly | enabled=true\n"
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
        milestone_rollup = _format_milestone_rollup(goal.get("goalid", ""), context)
        milestone_suffix = f" — milestones: {milestone_rollup}" if milestone_rollup else ""
        lifecycle = goal.get("lifecyclestatus") or "Active"
        lines.append(
            f"• {goal['goalid']}: {goal['title']} [{goal['status']} ({lifecycle}){target}{owner}{notes}]{milestone_suffix}"
        )

    await update.message.reply_text("\n".join(lines))


async def add_goal_milestone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Append a milestone to the GoalMilestones sheet."""

    if not update.message:
        return

    message_text = extract_command_argument(update.message.text or "")
    logger.info("Handling /goal_milestone_add", extra=_user_context(update))
    try:
        milestone = parse_goal_milestone(message_text, GOAL_MILESTONE_STATUSES)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    if not milestone.get("goalid") or not milestone.get("milestone"):
        await update.message.reply_text(
            "Please provide a goal id and milestone name. Example: /goal_milestone_add GOAL-1 | Kickoff | target=2024-05-01"
        )
        return

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't save milestones.")
        return

    try:
        await asyncio.to_thread(storage_client.append_goal_milestone, milestone)
    except Exception:
        logger.exception("Failed to append milestone", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't save that milestone. Please try again later.")
        return

    await update.message.reply_text(
        f"Milestone added for {milestone['goalid']}: {milestone['milestone']} ({milestone['status']})"
    )


async def list_goal_milestones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List milestones for a goal or all goals."""

    if not update.message:
        return

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't fetch milestones.")
        return

    goal_filter = extract_command_argument(update.message.text or "").strip()
    if goal_filter:
        goal_filter = goal_filter.split()[0]

    try:
        milestones = await asyncio.to_thread(storage_client.get_goal_milestones)
    except Exception:
        logger.exception("Failed to fetch milestones", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't load milestones right now.")
        return

    if goal_filter:
        milestones = [m for m in milestones if m.get("goalid") == goal_filter]

    if not milestones:
        await update.message.reply_text("No milestones found. Add one with /goal_milestone_add.")
        return

    lines = ["Goal milestones:"]
    for ms in milestones:
        target = f" target {ms['targetdate']}" if ms.get("targetdate") else ""
        completion = f", completed {ms['completiondate']}" if ms.get("completiondate") else ""
        notes = f" — {ms['notes']}" if ms.get("notes") else ""
        lines.append(
            f"• {ms['goalid']}: {ms['milestone']} [{ms['status']}{target}{completion}]{notes}"
        )

    await update.message.reply_text("\n".join(lines))


async def complete_goal_milestone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark a milestone as completed by appending a new row."""

    if not update.message:
        return

    message_text = extract_command_argument(update.message.text or "")
    try:
        parsed = parse_goal_milestone(message_text, GOAL_MILESTONE_STATUSES)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    if not parsed.get("goalid") or not parsed.get("milestone"):
        await update.message.reply_text(
            "Please provide a goal id and milestone name. Example: /goal_milestone_done GOAL-1 | Kickoff"
        )
        return

    completion_date = parsed.get("completiondate") or datetime.utcnow().date().isoformat()
    milestone = {
        **parsed,
        "status": "Completed",
        "completiondate": completion_date,
    }

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't update milestones.")
        return

    try:
        await asyncio.to_thread(storage_client.append_goal_milestone, milestone)
    except Exception:
        logger.exception("Failed to append milestone completion", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't record that completion.")
        return

    await update.message.reply_text(
        f"Marked milestone '{milestone['milestone']}' for {milestone['goalid']} as completed on {completion_date}."
    )


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


async def edit_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit goal lifecycle fields while preserving audit trail."""

    if not update.message:
        return

    message_text = extract_command_argument(update.message.text or "")
    logger.info("Handling /goal_edit command", extra=_user_context(update))
    try:
        parsed = parse_goal_edit(message_text, GOAL_STATUSES)
    except ValueError as exc:
        await update.message.reply_text(str(exc))
        return

    goal_id = parsed.get("goalid")
    if not goal_id:
        await update.message.reply_text("Please provide a goal id to edit. Example: /goal_edit GOAL-1 | title=New title")
        return

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't edit goals.")
        return

    try:
        goals = await asyncio.to_thread(storage_client.get_goals)
    except Exception:
        logger.exception("Failed to load goals for edit", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't load goals to edit right now.")
        return

    existing = next((goal for goal in goals if goal.get("goalid") == goal_id), None)
    if not existing:
        await update.message.reply_text("I couldn't find that goal. Use /goal_list to review IDs.")
        return

    updated_goal = {
        **existing,
        **{k: v for k, v in parsed.items() if v},
        "goalid": goal_id,
        "lastmodified": datetime.utcnow().isoformat(),
        "lifecyclestatus": parsed.get("lifecyclestatus") or "Updated",
    }
    updated_goal["history"] = "Edited via bot"

    try:
        await asyncio.to_thread(storage_client.append_goal, updated_goal)
    except Exception:
        logger.exception("Failed to append goal edit", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't record that edit.")
        return

    await update.message.reply_text(f"Updated goal {goal_id} with new details.")


async def archive_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Archive a goal by appending a lifecycle change."""

    if not update.message:
        return

    message_text = extract_command_argument(update.message.text or "")
    goal_id = message_text.split()[0] if message_text else ""
    reason = message_text[len(goal_id) :].strip() if goal_id else ""

    if not goal_id:
        await update.message.reply_text("Please include a goal id. Example: /goal_archive GOAL-1 Deprecated")
        return

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't archive goals.")
        return

    try:
        goals = await asyncio.to_thread(storage_client.get_goals)
    except Exception:
        logger.exception("Failed to load goals for archive", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't archive that goal right now.")
        return

    existing = next((goal for goal in goals if goal.get("goalid") == goal_id), None)
    if not existing:
        await update.message.reply_text("I couldn't find that goal. Use /goal_list to review IDs.")
        return

    archived_goal = {
        **existing,
        "lifecyclestatus": "Archived",
        "archived": "TRUE",
        "notes": reason or existing.get("notes", ""),
        "lastmodified": datetime.utcnow().isoformat(),
        "history": "Archived via bot",
    }

    try:
        await asyncio.to_thread(storage_client.append_goal, archived_goal)
    except Exception:
        logger.exception("Failed to append archive", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't record the archive right now.")
        return

    await update.message.reply_text(f"Archived goal {goal_id}. Reason: {reason or 'n/a'}")


async def supersede_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark a goal as superseded by another goal."""

    if not update.message:
        return

    message_text = extract_command_argument(update.message.text or "")
    tokens = message_text.split(maxsplit=2)
    if len(tokens) < 2:
        await update.message.reply_text(
            "Please provide the original and replacement goal IDs. Example: /goal_supersede GOAL-1 GOAL-2 migrated"
        )
        return

    original, replacement = tokens[0], tokens[1]
    reason = tokens[2] if len(tokens) > 2 else ""

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't supersede goals.")
        return

    try:
        goals = await asyncio.to_thread(storage_client.get_goals)
    except Exception:
        logger.exception("Failed to load goals for supersede", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't load goals right now.")
        return

    existing = next((goal for goal in goals if goal.get("goalid") == original), None)
    if not existing:
        await update.message.reply_text("I couldn't find that goal. Use /goal_list to review IDs.")
        return

    superseded_goal = {
        **existing,
        "lifecyclestatus": "Superseded",
        "supersededby": replacement,
        "lastmodified": datetime.utcnow().isoformat(),
        "history": reason or "Superseded",
    }

    try:
        await asyncio.to_thread(storage_client.append_goal, superseded_goal)
    except Exception:
        logger.exception("Failed to append supersede", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't record the supersede.")
        return

    await update.message.reply_text(
        f"Marked {original} as superseded by {replacement}. Notes: {reason or 'n/a'}"
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


async def log_midyear_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Capture a mid-year review entry for a goal."""

    if not update.message:
        return

    message_text = extract_command_argument(update.message.text or "")
    review = parse_goal_review(message_text)
    review.setdefault("reviewtype", "midyear")
    if not review.get("goalid"):
        await update.message.reply_text(
            "Please include a goal id. Example: /review_midyear GOAL-1 | rating=Strong | notes=Great progress"
        )
        return

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't log the review.")
        return

    try:
        await asyncio.to_thread(storage_client.append_goal_review, review)
    except Exception:
        logger.exception("Failed to append midyear review", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't save that review right now.")
        return

    await update.message.reply_text(
        f"Logged mid-year review for {review['goalid']} with rating {review.get('rating') or 'n/a'}."
    )


async def evaluate_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Record a year-end evaluation for a goal."""

    if not update.message:
        return

    message_text = extract_command_argument(update.message.text or "")
    evaluation = parse_goal_evaluation(message_text, default_type="yearend")
    if not evaluation.get("id"):
        await update.message.reply_text(
            "Please include a goal id. Example: /eval_goal GOAL-1 | rating=Exceeds | notes=Delivered impact"
        )
        return

    payload = {
        "goalid": evaluation["id"],
        "evaluationtype": evaluation.get("evaluationtype", "yearend"),
        "notes": evaluation.get("notes", ""),
        "rating": evaluation.get("rating", ""),
        "evaluatedon": evaluation.get("evaluatedon", ""),
    }

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't save evaluations.")
        return

    try:
        await asyncio.to_thread(storage_client.append_goal_evaluation, payload)
    except Exception:
        logger.exception("Failed to append goal evaluation", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't save that evaluation.")
        return

    await update.message.reply_text(
        f"Recorded evaluation for goal {payload['goalid']} with rating {payload.get('rating') or 'n/a'}."
    )


async def evaluate_competency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Record a competency evaluation entry."""

    if not update.message:
        return

    message_text = extract_command_argument(update.message.text or "")
    evaluation = parse_goal_evaluation(message_text, default_type="competency")
    if not evaluation.get("id"):
        await update.message.reply_text(
            "Please include a competency id. Example: /eval_competency communication | rating=Meets | notes=Presented monthly"
        )
        return

    payload = {
        "competencyid": evaluation["id"],
        "notes": evaluation.get("notes", ""),
        "rating": evaluation.get("rating", ""),
        "evaluatedon": evaluation.get("evaluatedon", ""),
    }

    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't save evaluations.")
        return

    try:
        await asyncio.to_thread(storage_client.append_competency_evaluation, payload)
    except Exception:
        logger.exception("Failed to append competency evaluation", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't save that competency evaluation.")
        return

    await update.message.reply_text(
        f"Recorded competency evaluation for {payload['competencyid']} with rating {payload.get('rating') or 'n/a'}."
    )


async def configure_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable or list reminder settings for milestones and reviews."""

    if not update.message:
        return

    message_text = extract_command_argument(update.message.text or "")
    storage_client = _get_storage_client(context)
    if not storage_client:
        await update.message.reply_text("Storage is not configured yet, so I can't manage reminders.")
        return

    if not message_text:
        try:
            settings = await asyncio.to_thread(storage_client.get_reminder_settings)
        except Exception:
            logger.exception("Failed to fetch reminder settings", extra=_user_context(update))
            await update.message.reply_text("Sorry, I couldn't load reminder settings.")
            return

        if not settings:
            await update.message.reply_text("No reminder settings saved yet. Use /reminder_settings category=milestone | frequency=weekly")
            return

        lines = ["Reminder settings:"]
        for setting in settings:
            notes = f" — {setting['notes']}" if setting.get("notes") else ""
            lines.append(
                f"• {setting['category']} {setting.get('targetid') or ''} freq={setting.get('frequency')} enabled={setting.get('enabled')} channel={setting.get('channel')}{notes}"
            )

        await update.message.reply_text("\n".join(lines))
        return

    parsed = parse_reminder_setting(message_text)
    if not parsed.get("category"):
        await update.message.reply_text(
            "Please include a category (milestone/review). Example: /reminder_settings category=milestone | frequency=weekly"
        )
        return

    try:
        await asyncio.to_thread(storage_client.append_reminder_setting, parsed)
    except Exception:
        logger.exception("Failed to save reminder setting", extra=_user_context(update))
        await update.message.reply_text("Sorry, I couldn't save that reminder setting.")
        return

    await update.message.reply_text(
        f"Saved reminder setting for {parsed.get('category')} (enabled={parsed.get('enabled')})."
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

    milestones_by_goal = _load_milestone_rollups(context)

    upcoming = [goal for goal in goals if goal.get("targetdate")]
    if upcoming:
        upcoming.sort(key=lambda g: g.get("targetdate"))
        lines.append("")
        lines.append("Target dates:")
        for goal in upcoming:
            owner_text = f" (owner: {goal['owner']})" if goal.get("owner") else ""
            milestone_progress = milestones_by_goal.get(goal.get("goalid", ""))
            milestone_suffix = f" — milestones: {milestone_progress}" if milestone_progress else ""
            lines.append(
                f"• {goal['targetdate']}: {goal['goalid']} — {goal['title']} [{goal['status']}]"
                f"{owner_text}{milestone_suffix}"
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
        goal_context = await _fetch_goal_metadata(storage_client, start_date, end_date)
        entries = _attach_goal_metadata(entries, goal_context)
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
        metadata_chunks: List[str] = []

        if entry.get("goals"):
            goals_text = "; ".join(_format_goal_metadata(goal) for goal in entry["goals"])
            metadata_chunks.append(f"Goals: {goals_text}")

        if entry.get("competencies"):
            comps_text = "; ".join(
                _format_competency_metadata(comp) for comp in entry["competencies"]
            )
            metadata_chunks.append(f"Competencies: {comps_text}")

        metadata_suffix = f" — {'; '.join(metadata_chunks)}" if metadata_chunks else ""
        lines.append(f"• [{entry_type}] {entry_date}: {text}{tag_suffix}{metadata_suffix}")

    return "\n".join(lines)


async def _fetch_goal_metadata(
    storage_client: object, start_date: date, end_date: date
) -> Dict[str, List[Dict[str, str]]]:
    """Load goals, competencies, and mappings, skipping failures gracefully."""

    async def _load_optional(method_name: str) -> List[Dict[str, str]]:
        getter = getattr(storage_client, method_name, None)
        if not callable(getter):
            return []

        try:
            if inspect.iscoroutinefunction(getter):
                return await getter()
            return await asyncio.to_thread(getter)
        except Exception:
            logger.exception("Failed to fetch %s", method_name)
            return []

    goals, competencies, mappings = await asyncio.gather(
        _load_optional("get_goals"),
        _load_optional("get_competencies"),
        _load_optional("get_goal_mappings"),
    )

    filtered_mappings = [
        mapping
        for mapping in mappings
        if start_date.isoformat()
        <= mapping.get("entrydate", "")
        <= end_date.isoformat()
    ]

    return {
        "goals": goals,
        "competencies": competencies,
        "mappings": filtered_mappings,
    }


def _attach_goal_metadata(
    entries: List[Dict[str, str]], goal_context: Dict[str, List[Dict[str, str]]]
) -> List[Dict[str, object]]:
    """Attach goal and competency details to entries based on stored mappings."""

    goals_by_id = {goal.get("goalid", ""): goal for goal in goal_context.get("goals", [])}
    competencies_by_id = {
        comp.get("competencyid", ""): comp for comp in goal_context.get("competencies", [])
    }
    mappings_by_timestamp: Dict[str, List[Dict[str, str]]] = {}

    for mapping in goal_context.get("mappings", []):
        ts = mapping.get("entrytimestamp", "")
        if not ts:
            continue
        mappings_by_timestamp.setdefault(ts, []).append(mapping)

    enriched_entries: List[Dict[str, object]] = []
    for entry in entries:
        entry_mappings = mappings_by_timestamp.get(entry.get("timestamp", ""), [])
        entry_goals = []
        entry_competencies = []

        for mapping in entry_mappings:
            goal_id = mapping.get("goalid", "")
            if goal_id:
                entry_goals.append(goals_by_id.get(goal_id, {"goalid": goal_id}))

            competency_id = mapping.get("competencyid", "")
            if competency_id:
                entry_competencies.append(
                    competencies_by_id.get(competency_id, {"competencyid": competency_id})
                )

        enriched_entries.append(
            {
                **entry,
                "goals": entry_goals,
                "competencies": entry_competencies,
            }
        )

    return enriched_entries


def _load_milestone_rollups(context: ContextTypes.DEFAULT_TYPE) -> Dict[str, str]:
    """Return completed/total rollups for milestones keyed by goal id."""

    storage_client = _get_storage_client(context)
    if not storage_client or not hasattr(storage_client, "get_goal_milestones"):
        return {}

    try:
        milestones = storage_client.get_goal_milestones()
    except Exception:
        return {}

    if not isinstance(milestones, list):
        return {}

    rollups: Dict[str, str] = {}
    for milestone in milestones:
        goal_id = milestone.get("goalid", "")
        if not goal_id:
            continue
        rollups.setdefault(goal_id, {"total": 0, "done": 0, "completed_dates": []})
        rollups[goal_id]["total"] += 1
        if milestone.get("status") == "Completed":
            rollups[goal_id]["done"] += 1
            if milestone.get("completiondate"):
                rollups[goal_id]["completed_dates"].append(milestone.get("completiondate"))

    formatted: Dict[str, str] = {}
    for goal_id, counts in rollups.items():
        completed = counts.get("done", 0)
        total = counts.get("total", 0)
        formatted[goal_id] = f"{completed}/{total} done"
        if counts.get("completed_dates"):
            formatted[goal_id] += f" (latest {sorted(counts['completed_dates'])[-1]})"

    return formatted


def _format_milestone_rollup(goal_id: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    rollups = _load_milestone_rollups(context)
    return rollups.get(goal_id, "")


def _format_goal_metadata(goal: Dict[str, str]) -> str:
    """Return a readable label for a goal reference."""

    goal_id = goal.get("goalid", "")
    title = goal.get("title") or ""
    status = goal.get("status") or ""
    details = f" — {title}" if title else ""
    status_suffix = f" ({status})" if status else ""
    return f"{goal_id}{details}{status_suffix}".strip()


def _format_competency_metadata(competency: Dict[str, str]) -> str:
    """Return a readable label for a competency reference."""

    comp_id = competency.get("competencyid", "")
    name = competency.get("name") or comp_id
    status = competency.get("status") or ""
    category = competency.get("category") or ""
    status_suffix = f" ({status})" if status else ""
    category_suffix = f" — {category}" if category else ""
    return f"{name}{category_suffix}{status_suffix}".strip()
