import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from src.bot import commands
from src.bot.ai_client import AIClient
from src.bot.ai_summarizer import build_prompt, create_ai_summarizer


def test_build_prompt_is_deterministic_and_includes_metadata():
    ai_client = AIClient(api_key="key", model="model")
    calls = []

    async def _provider(prompt: str, _ai_client: AIClient) -> str:  # pragma: no cover - helper
        calls.append(prompt)
        return "ai summary"

    summarizer = create_ai_summarizer(ai_client, provider=_provider)
    entries = [
        {
            "date": "2024-06-02",
            "type": "task",
            "text": "Write docs",
            "tags": "#docs",
            "goals": [{"goalid": "G-2", "title": "Docs", "status": "In Progress"}],
        },
        {
            "timestamp": "2024-06-01T10:00:00Z",
            "type": "accomplishment",
            "text": "Shipped release",
            "tags": "#release",
            "competencies": [
                {"competencyid": "C-1", "name": "Leadership", "status": "Active"},
                {"competencyid": "C-2", "name": "Delivery", "status": "Active"},
            ],
        },
    ]

    asyncio.run(summarizer(entries, date(2024, 6, 1), date(2024, 6, 2)))

    assert len(calls) == 1
    prompt = calls[0]
    # Entries should be sorted by timestamp/date first, then type/text for determinism
    assert "2024-06-01T10:00:00Z" in prompt.splitlines()[4]
    assert "2024-06-02" in prompt.splitlines()[5]
    # Metadata should be preserved within the prompt
    assert "Goals: G-2 — Docs — In Progress" in prompt
    assert "Competencies: C-1 — Leadership — Active; C-2 — Delivery — Active" in prompt
    assert "Date range: 2024-06-01 to 2024-06-02." in prompt


def test_build_prompt_helper_output():
    entries = [
        {"date": "2024-01-01", "type": "idea", "text": "Try new framework", "tags": "#research"}
    ]

    prompt = build_prompt(entries, date(2024, 1, 1), date(2024, 1, 7))

    assert "Try new framework" in prompt
    assert prompt.startswith("Summarize the user's work log")
    assert prompt.endswith("#research)")


def test_summarizer_returns_fallback_when_disabled():
    ai_client = AIClient(api_key="key", model="model")
    fallback_called = MagicMock()
    fallback_called.side_effect = commands._format_summary

    summarizer = create_ai_summarizer(ai_client, provider=AsyncMock(), formatter=fallback_called, enabled=False)

    entries = [{"date": "2024-06-01", "type": "task", "text": "Draft plan", "tags": ""}]
    summary = asyncio.run(summarizer(entries, date(2024, 6, 1), date(2024, 6, 7)))

    fallback_called.assert_called_once()
    assert summary.startswith("Entries from")


def test_summarizer_returns_fallback_on_provider_error():
    ai_client = AIClient(api_key="key", model="model")

    async def _failing_provider(prompt: str, _ai_client: AIClient):  # pragma: no cover - exercised indirectly
        raise RuntimeError("boom")

    summarizer = create_ai_summarizer(ai_client, provider=_failing_provider)
    entries = [{"date": "2024-06-01", "type": "task", "text": "Draft plan", "tags": ""}]

    summary = asyncio.run(summarizer(entries, date(2024, 6, 1), date(2024, 6, 7)))

    assert summary.startswith("Entries from")
