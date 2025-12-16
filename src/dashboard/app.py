"""Lightweight FastAPI dashboard for longer-form data entry."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config import Config, load_config
from src.storage.google_sheets_client import (
    GOAL_MILESTONE_STATUSES,
    GOAL_STATUSES,
    GoogleSheetsClient,
)

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

REVIEW_TYPES = ["Midyear", "Quarterly", "Monthly Check-in", "Retrospective"]
RATING_CHOICES = ["", "Exceptional", "Strong", "Solid", "Progressing", "Needs Support"]
ENTRY_TYPES = [
    ("accomplishment", "Accomplishment"),
    ("task", "Task"),
    ("idea", "Idea"),
    ("reflection", "Reflection"),
]


def create_app(
    config: Optional[Config] = None, sheets_client: Optional[GoogleSheetsClient] = None
) -> FastAPI:
    """Create and configure the FastAPI dashboard application."""

    cfg = config or load_config()
    client = sheets_client or GoogleSheetsClient(
        spreadsheet_id=cfg.spreadsheet_id,
        service_account_file=cfg.service_account_file,
        service_account_json=cfg.service_account_json,
    )

    app = FastAPI(
        title="Career Compass Dashboard",
        description="Minimal web dashboard for longer-form updates",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
    )

    def _render(template: str, request: Request, **context: Dict[str, object]) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(template, {"request": request, **context})

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request, success: str | None = None) -> HTMLResponse:
        return _render("home.html", request, success=_success_message(success))

    @app.get("/goals/new", response_class=HTMLResponse)
    async def new_goal_form(request: Request) -> HTMLResponse:
        return _render(
            "goal_form.html",
            request,
            statuses=_ordered_goal_statuses(),
            form_data={},
        )

    @app.post("/goals/new")
    async def submit_goal(
        request: Request,
        title: str = Form(...),
        description: str = Form(""),
        status_value: str = Form("In Progress"),
        goal_id: str = Form(""),
        target_date: str = Form(""),
        owner: str = Form(""),
        notes: str = Form(""),
        completion_percentage: str = Form(""),
    ) -> HTMLResponse:
        form_data = {
            "title": title,
            "description": description,
            "status_value": status_value,
            "goal_id": goal_id,
            "target_date": target_date,
            "owner": owner,
            "notes": notes,
            "completion_percentage": completion_percentage,
        }

        if status_value not in GOAL_STATUSES:
            return _render(
                "goal_form.html",
                request,
                statuses=_ordered_goal_statuses(),
                form_data=form_data,
                error="Choose a valid status",
            )

        goal_payload = {
            "goal_id": _clean_text(goal_id),
            "title": _clean_text(title),
            "description": _clean_text(description),
            "status": status_value,
            "target_date": _clean_text(target_date),
            "owner": _clean_text(owner),
            "notes": _clean_text(notes),
            "completion_percentage": _clean_text(completion_percentage),
            "lifecycle_status": "Active",
        }

        try:
            client.append_goal(goal_payload)
        except ValueError as exc:  # noqa: BLE001
            return _render(
                "goal_form.html",
                request,
                statuses=_ordered_goal_statuses(),
                form_data=form_data,
                error=str(exc),
            )

        return RedirectResponse("/?success=goal", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/goals/milestones/new", response_class=HTMLResponse)
    async def new_milestone_form(request: Request) -> HTMLResponse:
        return _render(
            "milestone_form.html",
            request,
            statuses=_ordered_milestone_statuses(),
            form_data={},
        )

    @app.post("/goals/milestones/new")
    async def submit_goal_milestone(
        request: Request,
        goal_id: str = Form(...),
        title: str = Form(...),
        target_date: str = Form(""),
        status_value: str = Form("Not Started"),
        completion_date: str = Form(""),
        notes: str = Form(""),
    ) -> HTMLResponse:
        form_data = {
            "goal_id": goal_id,
            "title": title,
            "target_date": target_date,
            "status_value": status_value,
            "completion_date": completion_date,
            "notes": notes,
        }

        if status_value not in GOAL_MILESTONE_STATUSES:
            return _render(
                "milestone_form.html",
                request,
                statuses=_ordered_milestone_statuses(),
                form_data=form_data,
                error="Choose a valid milestone status",
            )

        milestone_payload = {
            "goal_id": _clean_text(goal_id),
            "title": _clean_text(title),
            "target_date": _clean_text(target_date),
            "completion_date": _clean_text(completion_date),
            "status": status_value,
            "notes": _clean_text(notes),
        }

        try:
            client.append_goal_milestone(milestone_payload)
        except ValueError as exc:  # noqa: BLE001
            return _render(
                "milestone_form.html",
                request,
                statuses=_ordered_milestone_statuses(),
                form_data=form_data,
                error=str(exc),
            )

        return RedirectResponse("/?success=milestone", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/reviews/goal", response_class=HTMLResponse)
    async def new_goal_review(request: Request) -> HTMLResponse:
        return _render(
            "goal_review_form.html",
            request,
            review_types=REVIEW_TYPES,
            ratings=RATING_CHOICES,
            form_data={},
        )

    @app.post("/reviews/goal")
    async def submit_goal_review(
        request: Request,
        goal_id: str = Form(...),
        review_type: str = Form("Midyear"),
        rating: str = Form(""),
        notes: str = Form(""),
        reviewed_on: str = Form(""),
    ) -> HTMLResponse:
        form_data = {
            "goal_id": goal_id,
            "review_type": review_type,
            "rating": rating,
            "notes": notes,
            "reviewed_on": reviewed_on,
        }

        if review_type not in REVIEW_TYPES:
            return _render(
                "goal_review_form.html",
                request,
                review_types=REVIEW_TYPES,
                ratings=RATING_CHOICES,
                form_data=form_data,
                error="Choose a valid review type",
            )

        review_payload = {
            "goal_id": _clean_text(goal_id),
            "review_type": review_type,
            "rating": _clean_text(rating),
            "notes": _clean_text(notes),
            "reviewed_on": reviewed_on or date.today().isoformat(),
        }

        try:
            client.append_goal_review(review_payload)
        except ValueError as exc:  # noqa: BLE001
            return _render(
                "goal_review_form.html",
                request,
                review_types=REVIEW_TYPES,
                ratings=RATING_CHOICES,
                form_data=form_data,
                error=str(exc),
            )

        return RedirectResponse("/?success=goal_review", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/evaluations/competency", response_class=HTMLResponse)
    async def new_competency_evaluation(request: Request) -> HTMLResponse:
        return _render(
            "competency_evaluation_form.html",
            request,
            ratings=RATING_CHOICES,
            form_data={},
        )

    @app.post("/evaluations/competency")
    async def submit_competency_evaluation(
        request: Request,
        competency_id: str = Form(...),
        rating: str = Form(""),
        notes: str = Form(""),
        evaluated_on: str = Form(""),
    ) -> HTMLResponse:
        form_data = {
            "competency_id": competency_id,
            "rating": rating,
            "notes": notes,
            "evaluated_on": evaluated_on,
        }

        evaluation_payload = {
            "competency_id": _clean_text(competency_id),
            "rating": _clean_text(rating),
            "notes": _clean_text(notes),
            "evaluated_on": evaluated_on or date.today().isoformat(),
        }

        try:
            client.append_competency_evaluation(evaluation_payload)
        except ValueError as exc:  # noqa: BLE001
            return _render(
                "competency_evaluation_form.html",
                request,
                ratings=RATING_CHOICES,
                form_data=form_data,
                error=str(exc),
            )

        return RedirectResponse("/?success=competency", status_code=status.HTTP_303_SEE_OTHER)

    @app.get("/entries/new", response_class=HTMLResponse)
    async def new_entry_form(request: Request) -> HTMLResponse:
        return _render(
            "entry_form.html",
            request,
            entry_types=ENTRY_TYPES,
            form_data={"entry_type": "accomplishment"},
        )

    @app.post("/entries/new")
    async def submit_entry(
        request: Request,
        entry_type: str = Form("accomplishment"),
        text: str = Form(...),
        tags: str = Form(""),
        source: str = Form("Dashboard"),
    ) -> HTMLResponse:
        form_data = {"entry_type": entry_type, "text": text, "tags": tags, "source": source}

        if entry_type not in {choice for choice, _ in ENTRY_TYPES}:
            return _render(
                "entry_form.html",
                request,
                entry_types=ENTRY_TYPES,
                form_data=form_data,
                error="Choose a valid entry type",
            )

        now = datetime.utcnow()
        entry_payload = {
            "timestamp": now.isoformat(),
            "date": now.date().isoformat(),
            "type": entry_type,
            "text": _clean_text(text),
            "tags": _clean_text(tags),
            "source": _clean_text(source) or "Dashboard",
        }

        try:
            client.append_entry(entry_payload)
        except ValueError as exc:  # noqa: BLE001
            return _render(
                "entry_form.html",
                request,
                entry_types=ENTRY_TYPES,
                form_data=form_data,
                error=str(exc),
            )

        return RedirectResponse("/?success=entry", status_code=status.HTTP_303_SEE_OTHER)

    return app


def _clean_text(value: str | None) -> str:
    return value.strip() if value else ""


def _ordered_goal_statuses() -> list[str]:
    return sorted(GOAL_STATUSES)


def _ordered_milestone_statuses() -> list[str]:
    return sorted(GOAL_MILESTONE_STATUSES)


def _success_message(code: str | None) -> str | None:
    messages = {
        "goal": "Goal saved to Google Sheets.",
        "milestone": "Milestone saved to Google Sheets.",
        "goal_review": "Goal review submitted.",
        "competency": "Competency evaluation submitted.",
        "entry": "Entry logged successfully.",
    }
    return messages.get(code or "")

