import re
from datetime import datetime
from typing import Dict, List

GOAL_ID_PATTERN = re.compile(r"(?:#?goal[:\-]?)([A-Za-z0-9_-]+)", re.IGNORECASE)
COMPETENCY_TAG_PATTERN = re.compile(r"(?:#?(?:comp|competency)[:\-]?)([A-Za-z0-9_-]+)", re.IGNORECASE)
STATUS_SPLIT_PATTERN = re.compile(r"\s+")

TAG_PATTERN = re.compile(r"#(\w+)")


def extract_tags(text: str) -> List[str]:
    """Extract hashtags from a text string."""

    return [f"#{tag}" for tag in TAG_PATTERN.findall(text)]


def extract_goal_ids(text: str) -> List[str]:
    """Return a list of goal identifiers referenced in the text."""

    return [match.group(1) for match in GOAL_ID_PATTERN.finditer(text or "")]


def extract_competency_tags(text: str) -> List[str]:
    """Return a list of competency identifiers referenced in the text."""

    return [match.group(1) for match in COMPETENCY_TAG_PATTERN.finditer(text or "")]


def extract_command_argument(message_text: str) -> str:
    """Return the text following the command name.

    Telegram sends the full command (e.g., "/log something great"). This helper
    discards the command itself and returns the remainder for further parsing.
    """

    if not message_text:
        return ""

    parts = message_text.split(maxsplit=1)
    if len(parts) == 1:
        return ""

    return parts[1].strip()


def parse_goal_add(text: str, allowed_statuses: set[str]) -> Dict[str, str]:
    """Parse arguments for /goal_add into a structured dict."""

    cleaned = text.strip()
    if not cleaned:
        return {}

    segments = [segment.strip() for segment in cleaned.split("|") if segment.strip()]
    head = segments[0]
    head_tokens = head.split(maxsplit=1)
    goal_id = _parse_goal_token(head_tokens[0]) if head_tokens else ""
    title = head_tokens[1].strip() if len(head_tokens) > 1 else ""

    key_values = _parse_key_value_segments(segments[1:])
    if not title:
        title = key_values.pop("title", "")

    status_value = key_values.pop("status", "Not Started")
    status = _normalize_status(status_value, allowed_statuses)

    return {
        "goalid": goal_id,
        "title": title,
        "status": status,
        "targetdate": key_values.pop("target", key_values.pop("targetdate", "")),
        "owner": key_values.pop("owner", ""),
        "notes": key_values.pop("notes", ""),
    }


def parse_goal_status_change(text: str, allowed_statuses: set[str]) -> Dict[str, str]:
    """Parse /goal_status input into goal id, status, and optional notes."""

    cleaned = text.strip()
    if not cleaned:
        return {}

    goal_id = ""
    status = ""
    notes = ""

    match_ids = extract_goal_ids(cleaned)
    working = cleaned
    if match_ids:
        goal_id = match_ids[0]
        working = GOAL_ID_PATTERN.sub("", working, count=1).strip()
    else:
        tokens = working.split(maxsplit=1)
        if tokens:
            goal_id = _parse_goal_token(tokens[0])
            working = tokens[1].strip() if len(tokens) > 1 else ""

    if working:
        status, notes = _extract_status_and_notes(working, allowed_statuses)

    return {"goalid": goal_id, "status": status, "notes": notes}


def parse_goal_link(text: str) -> Dict[str, str]:
    """Parse /goal_link arguments into goal/competency identifiers and notes."""

    cleaned = text.strip()
    if not cleaned:
        return {}

    goal_ids = extract_goal_ids(cleaned)
    competency_ids = extract_competency_tags(cleaned)
    goal_id = goal_ids[0] if goal_ids else ""
    competency_id = competency_ids[0] if competency_ids else ""

    working = cleaned
    if goal_id:
        working = GOAL_ID_PATTERN.sub("", working, count=1)
    if competency_id:
        working = COMPETENCY_TAG_PATTERN.sub("", working, count=1)

    if not goal_id:
        tokens = STATUS_SPLIT_PATTERN.split(working.strip(), maxsplit=1)
        if tokens:
            goal_id = tokens[0]
            working = tokens[1] if len(tokens) > 1 else ""

    notes = working.strip()
    return {"goalid": goal_id, "competencyid": competency_id, "notes": notes}


def normalize_entry(
    text: str,
    entry_type: str,
    tags: List[str],
    source: str = "telegram",
    timestamp: datetime | None = None,
) -> Dict[str, str]:
    """Create a normalized record ready for storage or display."""

    timestamp = timestamp or datetime.utcnow()
    return {
        "timestamp": timestamp.isoformat(),
        "date": timestamp.date().isoformat(),
        "type": entry_type,
        "text": text.strip(),
        "tags": " ".join(tags),
        "source": source,
    }


def _parse_goal_token(token: str) -> str:
    match = GOAL_ID_PATTERN.search(token)
    return match.group(1) if match else token


def _parse_key_value_segments(segments: List[str]) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for segment in segments:
        if "=" in segment:
            key, value = segment.split("=", maxsplit=1)
            parsed[key.strip().lower()] = value.strip()
    return parsed


def _normalize_status(value: str, allowed_statuses: set[str]) -> str:
    for status in allowed_statuses:
        if value.strip().lower() == status.lower():
            return status
    raise ValueError(f"Status '{value}' is not one of {sorted(allowed_statuses)}")


def _extract_status_and_notes(text: str, allowed_statuses: set[str]) -> tuple[str, str]:
    working = text.strip()
    for status in sorted(allowed_statuses, key=len, reverse=True):
        if working.lower().startswith(status.lower()):
            remaining = working[len(status) :].strip()
            return status, remaining
    raise ValueError(f"Could not find a valid status in '{text}'. Allowed: {sorted(allowed_statuses)}")
