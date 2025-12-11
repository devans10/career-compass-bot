# Phase 1 Implementation Plan

## Objectives
- Enable fast, low-friction logging of accomplishments, tasks, and ideas via Telegram commands.
- Persist structured entries to Google Sheets for easy retrieval.
- Provide weekly reminders to prompt logging.
- Support simple retrieval of recent entries (week/month).

## Assumptions
- Telegram bot will run for a single user; access control is handled through the bot token and chat ID filtering.
- Google Sheets credentials are supplied via environment variables and mounted secrets; no credentials live in the repo.
- Hosting target is a single-process Docker container running on a DigitalOcean droplet, with optional external cron for scheduling.

## Deliverables
- Functional Telegram bot with `/start`, `/help`, `/log`, `/task`, `/idea`, `/week`, `/month` commands.
- Google Sheets integration with append/query capabilities and documented schema.
- Scheduler for weekly reminders (in-process or cron-friendly entry point).
- Configuration and logging setup with .env.example for local runs.
- Automated tests for parsing and command behavior.
- Minimal deployment docs for running the bot.

## Workstreams and Tasks

### 1) Telegram Interaction Agent
- Set up bot bootstrap in `src/bot/main.py` with polling and handler registration.
- Implement user-facing handlers in `src/bot/handlers.py`, including error handling and friendly messages for unknown commands.
- Add `/start` and `/help` responses with usage examples.

### 2) Command & Journal Agent
- Implement parsing helpers in `src/bot/parsing.py` (command argument extraction, tag parsing, entry normalization).
- Implement core command functions in `src/bot/commands.py`:
  - `/log`, `/task`, `/idea` → normalize entry types, extract tags, build record, call storage, return confirmation.
  - `/week`, `/month` → compute date ranges, fetch from storage, format summaries.
- Add lightweight input validation (empty messages, oversized payloads) and consistent error replies.

### 3) Storage Agent
- Implement Google Sheets client in `src/storage/google_sheets_client.py` with:
  - `append_entry(record)` for single-row writes.
  - `get_entries_by_date_range(start_date, end_date)` for retrieval.
- Enforce sheet schema: Timestamp, Date, Type, Text, Tags, Source.
- Add retry/backoff around API calls and structured logging for failures.
- Provide a small utility to bootstrap the sheet (headers, tab name) or document manual setup steps.

### 4) Scheduler / Reminder Agent
- Implement weekly reminder job in `src/bot/scheduler.py` (configurable weekday/time, timezone-aware).
- Ensure scheduler can be started from main process or invoked by external cron (expose callable entry point).
- Draft reminder message templates (e.g., prompt for top accomplishments).

### 5) Configuration & Secrets
- Centralize configuration in `src/config.py` with environment-driven settings (tokens, spreadsheet ID, credential path/JSON, timezone, reminder schedule).
- Provide `.env.example` covering required variables.
- Guard against missing config with clear startup validation errors.

### 6) Logging & Observability
- Standardize logging via `src/logging_config.py` (levels, formats).
- Add contextual logs for command handling and storage operations.

### 7) Testing & QA
- Expand unit tests in `tests/` for parsing utilities and command behavior (mock Telegram/storage layers).
- Add integration-style test for storage client using a stub/mocked Google Sheets service if feasible.
- Lint/type checks as defined in the repository tooling (e.g., `pytest`, `ruff`, `mypy` if configured).

### 8) Deployment & Operations
- Provide runbook in README or docs covering local run (`python -m src.bot.main`), dependency installation, and environment setup.
- Outline deployment steps for containerized environment (build image, configure secrets, run scheduler).
- Document monitoring basics (log inspection, handling API quota errors).

## Milestones
- **M1: Bot Skeleton** – Bot starts, `/start` and `/help` respond, logging infrastructure in place.
- **M2: Command Execution** – `/log`, `/task`, `/idea` write to Google Sheets; basic validation and confirmations.
- **M3: Retrieval** – `/week` and `/month` return formatted summaries from stored entries.
- **M4: Scheduling** – Weekly reminder job running and configurable.
- **M5: Quality & Docs** – Tests passing; `.env.example` updated; deployment/runbook documented.

## Risks and Mitigations
- **Google Sheets quota or auth errors**: implement retries, clear error messages, and document credential setup.
- **Scheduler reliability**: allow external cron fallback and make reminder job idempotent.
- **Timezone mismatches**: centralize timezone config and use aware datetimes when writing/querying.
- **Large/structured messages**: add input limits and graceful handling for unexpected payloads.
