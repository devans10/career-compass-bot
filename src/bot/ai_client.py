"""Lightweight container for AI provider settings."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AIClient:
    """Holds configuration for an AI provider.

    The object is stored on ``application.bot_data`` so downstream handlers can
    access provider details (API key, model, and an optional endpoint) when
    constructing summarization calls.
    """

    api_key: str
    model: str
    endpoint: Optional[str] = None
