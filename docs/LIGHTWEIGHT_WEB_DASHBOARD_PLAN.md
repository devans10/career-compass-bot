# Lightweight Web Dashboard Plan

## Goals
- Provide a richer interface for longer-form updates (goals, reviews, self-reflections) than the Telegram bot offers.
- Keep Google Sheets as the system of record while layering a friendlier UI and API around it.
- Reduce friction by combining quick logging via Telegram with deeper management, browsing, and editing workflows in the web UI.

## Key Use Cases
- Create and edit goals with milestones, status, and target dates.
- Submit structured review updates (mid-year, goal evaluations, competency reflections) with multi-field inputs.
- Browse recent accomplishments/tasks/ideas with filters and quick links back to related goals/competencies.
- Trigger summaries (week/month) and download CSV/markdown for reporting.
- Manage reminder preferences and view upcoming milestones.

## Design Principles
- **Low operational overhead:** Prefer serverless/managed hosting for the UI/API; reuse existing Google Sheets backend.
- **Progressive disclosure:** Keep fast paths for quick updates while offering richer, multi-step forms for detailed input.
- **Link-first:** Generate shareable links from the Telegram bot to prefilled forms for the specific goal/review.
- **Auditability:** Preserve the current headers and validation rules before writing to Sheets; log all mutations.
- **Security posture matches deployment:** Short-term assumes local-only access (prioritizing convenience), but the design should keep auth/CSRF/session hooks ready so medium-term hardening (OAuth, tokens) can be slotted in without rewriting flows.

## High-Level Architecture
- **Frontend:** Lightweight SPA (React/Vite) or server-rendered pages (FastAPI + Jinja) served from the same container as the bot API or from a static host (e.g., Netlify/Vercel) hitting the backend API.
- **Backend API:** New FastAPI router that wraps the Google Sheets client with explicit DTOs for goals, milestones, reviews, entries, reminders.
- **Storage:** Continue using Google Sheets via `src/storage/google_sheets_client.py`; no schema changes initially.
- **Auth:** Option A: Google OAuth (only allow configured workspace users). Option B: password/token gate in front of the dashboard when OAuth is unavailable.
- **Hosting:** Reuse existing container image with an extra ASGI entry point, or split into two services (bot and dashboard API) behind the same Sheets project.

## Proposed UI Surface
- **Home:** Snapshot of recent entries, upcoming milestones, and quick actions ("Add goal", "Log review", "View week summary").
- **Goals:** List with status filters; detail page showing milestones, linked entries, and an edit form.
- **Reviews/Evaluations:** Guided forms for mid-year/goal/competency reviews with autosave and validation.
- **Entries:** Table view with search/filter by date, tag, goal, or competency; export to CSV/Markdown.
- **Reminders:** Form to adjust reminder cadence/timezone and preview scheduled nudges.

## Backend API Sketch
- **Goals:** `GET /api/goals`, `POST /api/goals`, `PATCH /api/goals/{id}`, `POST /api/goals/{id}/milestones`, `PATCH /api/goals/{id}/milestones/{mid}`.
- **Entries:** `GET /api/entries?start=&end=&tag=&goal=`, `POST /api/entries` (for richer multi-field submissions).
- **Reviews:** `POST /api/reviews/goal`, `POST /api/reviews/competency`, `POST /api/reviews/midyear`.
- **Summaries:** `GET /api/summary/week`, `GET /api/summary/month` with optional AI flag to mirror bot behavior.
- **Reminders:** `GET/POST /api/reminders` to fetch/update settings.
- **Health/Auth:** `GET /api/health`, `POST /api/auth/login` (if not using OAuth middleware).

## Data Flow to Google Sheets
- Use existing client functions (e.g., `append_goal`, `append_goal_milestone`, `append_goal_review`, `append_goal_evaluation`, `append_competency_evaluation`, `append_entry`).
- Add thin translation layer converting API payloads to the expected row schemas and validating enumerations (statuses, lifecycle states, goal IDs, competency IDs).
- Preserve timestamps/timezones in UTC and store human-readable dates like the bot does.
- For edits, consider a "rewrite row" helper or append immutable correction rows with references to the prior timestamp.

## Security and Access Control
- Short-term (local-only): Default to binding on `127.0.0.1` with no mandatory auth; offer an optional single-user token gate when running on a shared machine.
- Medium-term: Enforce Google OAuth (allowlisted emails) or a comparable SSO; keep tokens server-side (HTTP-only cookies) and enable CSRF protection on state-changing routes.
- Rate limiting on API endpoints to protect Sheets quota once the dashboard is reachable beyond localhost.
- Avoid exposing raw Sheet IDs/headers to the client; the backend mediates all reads/writes and should be the only component holding credentials.

## Telemetry and Observability
- Structured logs for all API mutations including sheet tab, headers, and user ID/email.
- Basic request metrics (latency, error counts) and Sheets quota error tracking.
- Feature flags for AI summaries and reminder settings to mirror bot toggles.

## Accessibility and UX
- Keyboard-friendly forms, clear validation messages, and saved-draft support for long reviews.
- Autosave drafts to local storage on the client; warn on navigation with unsaved changes.
- Mobile-friendly layout to allow quick edits from a phone.

## Phased Delivery
1. **APIs first (Bot-compatible):**
   - Add FastAPI router and DTOs for goals, milestones, entries, reviews, reminders.
   - Reuse Google Sheets client; add validation layer and optional auth middleware (off by default for localhost-only use).
   - Ship a minimal HTML form for smoke testing (no full SPA yet).
2. **MVP Dashboard:**
   - React/Vite or server-rendered templates for Goals list/detail and Review submission forms.
   - Entry table with date/tag filters; week/month summary view using the new API.
   - Token-based auth and basic session UI.
3. **Quality & UX polish:**
   - Prefill links from Telegram replies (e.g., open specific goal ID or review form).
   - Autosave drafts, reminders editor, CSV/Markdown export.
   - Add Google OAuth, rate limiting, and better error states.
4. **Operations:**
   - CI checks for API contract tests and frontend lint/build.
   - Container entry point for ASGI server (e.g., `uvicorn src.dashboard.api:app`).
   - Deployment notes for hosting (single container vs. split services) and environment variables.

## Risks and Mitigations
- **Authentication complexity:** Keep auth pluggable—start local with no auth (or optional token) and upgrade to OAuth/SSO once the UI is ready for remote access.
- **Sheets latency/quota:** Cache list endpoints and batch reads where possible; add retry/backoff already used by the client.
- **Schema drift:** Centralize schemas in one module consumed by both bot and dashboard APIs.
- **Scope creep:** Phase the rollout; keep MVP to goals + reviews + entry browsing before tackling exports and advanced reminders.
