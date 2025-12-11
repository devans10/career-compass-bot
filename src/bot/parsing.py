import re
from typing import List

TAG_PATTERN = re.compile(r"#(\w+)")


def extract_tags(text: str) -> List[str]:
    """Extract hashtags from a text string."""

    return [f"#{tag}" for tag in TAG_PATTERN.findall(text)]
