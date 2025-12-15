"""AI summarization helpers for log entries."""

from __future__ import annotations

import inspect
import logging
from datetime import date
from typing import Awaitable, Callable, Dict, Iterable, List, Optional

from src.bot.ai_client import AIClient

logger = logging.getLogger(__name__)

ProviderFunc = Callable[[str, AIClient], Awaitable[str] | str]


def _sorted_entries(entries: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    """Return entries sorted deterministically for prompt construction."""

    return sorted(
        entries,
        key=lambda entry: (
            entry.get("timestamp") or entry.get("date") or "",
            entry.get("type", ""),
            entry.get("text", ""),
        ),
    )


def _format_goal(goal: Dict[str, str]) -> str:
    """Create a compact goal representation for prompts."""

    goal_id = goal.get("goalid") or goal.get("id") or goal.get("key") or ""
    title = goal.get("title") or goal.get("name") or ""
    status = goal.get("status") or goal.get("state") or ""
    parts = [part for part in (goal_id, title, status) if part]
    return " — ".join(parts) if parts else "(goal metadata missing)"


def _format_competency(comp: Dict[str, str]) -> str:
    """Create a compact competency representation for prompts."""

    comp_id = comp.get("competencyid") or comp.get("id") or comp.get("key") or ""
    name = comp.get("name") or comp.get("title") or ""
    status = comp.get("status") or comp.get("state") or ""
    parts = [part for part in (comp_id, name, status) if part]
    return " — ".join(parts) if parts else "(competency metadata missing)"


def _format_entry_for_prompt(entry: Dict[str, str]) -> str:
    """Format a single entry line for the AI prompt."""

    entry_date = entry.get("timestamp") or entry.get("date") or "(unknown date)"
    entry_type = entry.get("type", "entry").capitalize()
    text = (entry.get("text") or "").strip()
    tags = entry.get("tags") or ""
    tag_suffix = f" ({tags})" if tags else ""

    metadata_chunks: List[str] = []
    if entry.get("goals"):
        goals_text = "; ".join(_format_goal(goal) for goal in sorted(entry["goals"], key=_format_goal))
        metadata_chunks.append(f"Goals: {goals_text}")
    if entry.get("competencies"):
        comps_text = "; ".join(
            _format_competency(comp) for comp in sorted(entry["competencies"], key=_format_competency)
        )
        metadata_chunks.append(f"Competencies: {comps_text}")

    metadata_suffix = f" — {'; '.join(metadata_chunks)}" if metadata_chunks else ""
    return f"- [{entry_type}] {entry_date}: {text}{tag_suffix}{metadata_suffix}"


def build_prompt(entries: List[Dict[str, str]], start_date: date, end_date: date) -> str:
    """Construct a deterministic prompt for AI summarization."""

    header = [
        "Summarize the user's work log into a concise paragraph (under 120 words).",
        f"Date range: {start_date.isoformat()} to {end_date.isoformat()}.",
        "Highlight accomplishments, tasks, ideas, goals, and competencies.",
        "Entries:",
    ]
    lines = header + [_format_entry_for_prompt(entry) for entry in _sorted_entries(entries)]
    return "\n".join(lines)


async def _call_ai_provider(prompt: str, ai_client: AIClient) -> str:
    """Call the configured AI provider asynchronously."""

    from openai import AsyncOpenAI  # type: ignore[import-not-found]

    client = AsyncOpenAI(api_key=ai_client.api_key, base_url=ai_client.endpoint)
    response = await client.chat.completions.create(
        model=ai_client.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return (response.choices[0].message.content or "").strip()


def create_ai_summarizer(
    ai_client: Optional[AIClient],
    provider: Optional[ProviderFunc] = None,
    formatter: Optional[Callable[[List[Dict[str, str]], date, date], str]] = None,
    enabled: bool = True,
) -> Callable[[List[Dict[str, str]], date, date], Awaitable[str]]:
    """Create a summarizer function that wraps provider calls with fallbacks."""

    async def _summarize(entries: List[Dict[str, str]], start_date: date, end_date: date) -> str:
        nonlocal provider
        from src.bot.commands import _format_summary

        fallback_formatter = formatter or _format_summary

        if not enabled or not ai_client:
            return fallback_formatter(entries, start_date, end_date)

        prompt = build_prompt(entries, start_date, end_date)
        caller = provider or _call_ai_provider

        try:
            result = caller(prompt, ai_client)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, str) and result.strip():
                return result.strip()
        except Exception:  # noqa: BLE001
            logger.exception("AI provider call failed; using fallback summary")

        return fallback_formatter(entries, start_date, end_date)

    return _summarize
