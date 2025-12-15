import re
from datetime import datetime
from typing import Dict, List

GOAL_ID_PATTERN = re.compile(
    r"(?:#?goal[:\-]?)([A-Za-z0-9_-]+)|(goal-[A-Za-z0-9_-]+)", re.IGNORECASE
)
COMPETENCY_TAG_PATTERN = re.compile(r"(?:#?(?:comp|competency)[:\-]?)([A-Za-z0-9_-]+)", re.IGNORECASE)
STATUS_SPLIT_PATTERN = re.compile(r"\s+")

TAG_PATTERN = re.compile(r"#(\w+)")


def extract_tags(text: str) -> List[str]:
    """Extract hashtags from a text string."""

    return [f"#{tag}" for tag in TAG_PATTERN.findall(text)]


def extract_goal_ids(text: str) -> List[str]:
    """Return a list of goal identifiers referenced in the text."""

    goal_ids = []
    for match in GOAL_ID_PATTERN.finditer(text or ""):
        goal_ids.append(_normalize_goal_id(_goal_match_to_id(match)))

    return _dedupe_preserve_order(goal_ids)


def extract_competency_tags(text: str) -> List[str]:
    """Return a list of competency identifiers referenced in the text."""

    competency_ids = [match.group(1).lower() for match in COMPETENCY_TAG_PATTERN.finditer(text or "")]
    return _dedupe_preserve_order(competency_ids)


def extract_goal_and_competency_refs(text: str) -> Dict[str, List[str]]:
    """Return normalized goal and competency references found in free-form text."""

    return {
        "goal_ids": extract_goal_ids(text),
        "competency_ids": extract_competency_tags(text),
    }


def build_goal_competency_mappings(
    entry_timestamp: str, entry_date: str, goal_ids: List[str], competency_ids: List[str]
) -> List[Dict[str, str]]:
    """Return GoalMappings rows for the provided identifiers."""

    mappings: List[Dict[str, str]] = []

    if goal_ids:
        for goal_id in goal_ids:
            if competency_ids:
                for competency_id in competency_ids:
                    mappings.append(
                        {
                            "entrytimestamp": entry_timestamp,
                            "entrydate": entry_date,
                            "goalid": goal_id,
                            "competencyid": competency_id,
                            "notes": "",
                        }
                    )
            else:
                mappings.append(
                    {
                        "entrytimestamp": entry_timestamp,
                        "entrydate": entry_date,
                        "goalid": goal_id,
                        "competencyid": "",
                        "notes": "",
                    }
                )
    elif competency_ids:
        for competency_id in competency_ids:
            mappings.append(
                {
                    "entrytimestamp": entry_timestamp,
                    "entrydate": entry_date,
                    "goalid": "",
                    "competencyid": competency_id,
                    "notes": "",
                }
            )

    return mappings


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
        "description": key_values.pop("description", ""),
        "weightpercentage": key_values.pop(
            "weightpercentage", key_values.pop("weight", key_values.pop("weight_percent", ""))
        ),
        "status": status,
        "completionpercentage": key_values.pop(
            "completionpercentage",
            key_values.pop("completion", key_values.pop("complete", key_values.pop("completepercent", ""))),
        ),
        "startdate": key_values.pop("start", key_values.pop("startdate", "")),
        "enddate": key_values.pop("end", key_values.pop("enddate", "")),
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


def parse_goal_milestone(text: str, allowed_statuses: set[str]) -> Dict[str, str]:
    """Parse milestone payloads into structured fields."""

    cleaned = text.strip()
    if not cleaned:
        return {}

    segments = [segment.strip() for segment in cleaned.split("|") if segment.strip()]
    head_tokens = segments[0].split(maxsplit=1)
    goal_id = _parse_goal_token(head_tokens[0]) if head_tokens else ""
    milestone = head_tokens[1].strip() if len(head_tokens) > 1 else ""
    if not milestone and len(segments) > 1:
        milestone = segments[1]

    key_values = _parse_key_value_segments(segments[1:])
    milestone = key_values.pop("title", key_values.pop("milestone", milestone))
    status = _normalize_status(key_values.pop("status", "Not Started"), allowed_statuses)
    completion = key_values.pop("completion", key_values.pop("completiondate", ""))

    target_date = key_values.pop("target", key_values.pop("targetdate", ""))
    notes = key_values.pop("notes", "")

    return {
        "goalid": goal_id,
        "title": milestone,
        "targetdate": target_date,
        "completiondate": completion,
        "status": status,
        "notes": notes,
    }


def parse_goal_edit(text: str, allowed_statuses: set[str]) -> Dict[str, str]:
    """Parse lifecycle edits for a goal."""

    cleaned = text.strip()
    if not cleaned:
        return {}

    segments = [segment.strip() for segment in cleaned.split("|") if segment.strip()]
    head_tokens = segments[0].split(maxsplit=1)
    goal_id = _parse_goal_token(head_tokens[0]) if head_tokens else ""
    title = head_tokens[1].strip() if len(head_tokens) > 1 else ""

    key_values = _parse_key_value_segments(segments[1:])
    if not title:
        title = key_values.pop("title", "")

    status = key_values.pop("status", "")
    lifecycle_status = key_values.pop("lifecycle", "") or key_values.pop("lifecyclestatus", "")
    superseded_by = key_values.pop("superseded", "") or key_values.pop("superseded_by", "")
    archived = key_values.pop("archived", "")

    normalized_status = _normalize_status(status, allowed_statuses) if status else ""

    return {
        "goalid": goal_id,
        "title": title,
        "status": normalized_status,
        "targetdate": key_values.pop("target", key_values.pop("targetdate", "")),
        "owner": key_values.pop("owner", ""),
        "notes": key_values.pop("notes", ""),
        "lifecyclestatus": lifecycle_status,
        "supersededby": superseded_by,
        "archived": archived,
    }


def parse_goal_review(text: str) -> Dict[str, str]:
    """Parse review payloads for mid-year or other review types."""

    cleaned = text.strip()
    if not cleaned:
        return {}

    segments = [segment.strip() for segment in cleaned.split("|") if segment.strip()]
    head_tokens = segments[0].split(maxsplit=1)
    goal_id = _parse_goal_token(head_tokens[0]) if head_tokens else ""
    notes = head_tokens[1].strip() if len(head_tokens) > 1 else ""

    key_values = _parse_key_value_segments(segments[1:])
    notes = key_values.pop("notes", notes)
    review_type = key_values.pop("type", key_values.pop("reviewtype", "midyear"))
    rating = key_values.pop("rating", "")
    reviewed_on = key_values.pop("date", key_values.pop("reviewedon", ""))

    return {
        "goalid": goal_id,
        "notes": notes,
        "reviewtype": review_type,
        "rating": rating,
        "reviewedon": reviewed_on,
    }


def parse_goal_evaluation(text: str, default_type: str) -> Dict[str, str]:
    """Parse year-end evaluation payloads for goals and competencies."""

    cleaned = text.strip()
    if not cleaned:
        return {}

    segments = [segment.strip() for segment in cleaned.split("|") if segment.strip()]
    head_tokens = segments[0].split(maxsplit=1)
    identifier = _parse_goal_token(head_tokens[0]) if head_tokens else ""
    notes = head_tokens[1].strip() if len(head_tokens) > 1 else ""

    key_values = _parse_key_value_segments(segments[1:])
    notes = key_values.pop("notes", notes)
    rating = key_values.pop("rating", "")
    evaluation_type = key_values.pop("type", key_values.pop("evaluationtype", default_type))
    evaluated_on = key_values.pop("date", key_values.pop("evaluatedon", ""))

    return {
        "id": identifier,
        "notes": notes,
        "rating": rating,
        "evaluationtype": evaluation_type,
        "evaluatedon": evaluated_on,
    }


def parse_reminder_setting(text: str) -> Dict[str, str]:
    """Parse reminder configuration payloads."""

    cleaned = text.strip()
    if not cleaned:
        return {}

    key_values = _parse_key_value_segments([segment.strip() for segment in cleaned.split("|") if segment.strip()])
    return {
        "category": key_values.get("category", ""),
        "targetid": key_values.get("goal") or key_values.get("target", ""),
        "frequency": key_values.get("frequency", ""),
        "enabled": key_values.get("enabled", "true"),
        "channel": key_values.get("channel", "telegram"),
        "notes": key_values.get("notes", ""),
    }


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
    return _goal_match_to_id(match) if match else token


def _normalize_goal_id(goal_id: str) -> str:
    if not goal_id:
        return ""
    if goal_id.lower().startswith("goal-"):
        return f"GOAL-{goal_id[5:]}"
    return goal_id


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen: set[str] = set()
    deduped: List[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _goal_match_to_id(match: re.Match) -> str:
    """Normalize a GOAL_ID_PATTERN match to a consistent identifier."""

    full_match = match.group(0)
    captured = match.group(1) or match.group(2)

    if match.group(2):
        return match.group(2)

    if full_match.lower().startswith("goal-"):
        return full_match

    return captured


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
