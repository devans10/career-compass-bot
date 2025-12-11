import re
from datetime import datetime
from typing import Dict, List

TAG_PATTERN = re.compile(r"#(\w+)")


def extract_tags(text: str) -> List[str]:
    """Extract hashtags from a text string."""

    return [f"#{tag}" for tag in TAG_PATTERN.findall(text)]


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
