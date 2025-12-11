# Phase 2 Implementation Plan

## Objectives
- Introduce goals and competencies as first-class entities alongside journal entries.
- Map logged entries to goals/competencies for richer progress tracking.
- Provide commands to create, review, and update goals, plus summarize progress by goal.
- Preserve low-friction logging and retrieval while adding the new context.

## Assumptions
- Google Sheets remains the source of truth; new tabs (Goals, Competencies, GoalMappings) can be added to the existing workbook.
- The bot continues to operate for a single user with existing auth/chat ID protections.
- Phase 1 commands and schemas stay backward compatible; existing tabs and headers remain unchanged.
- Deployment/runtime footprint stays as a single-process container or cron-friendly entry point.

## Deliverables *(Planned)*
- Extended Google Sheets schema with Goals, Competencies, and GoalMappings tabs. *(Planned)*
- Bot commands for managing goals/competencies and linking entries. *(Planned)*
- Updated parsing utilities to accept goal/competency references in logging flows. *(Planned)*
- Retrieval and summary responses that surface goal/competency context. *(Planned)*
- Tests and docs covering the new workflows and configuration. *(Planned)*

## Workstreams and Tasks

### 1) Objectives & Success Metrics *(Planned)*
- Define goal/competency data model (IDs, titles, statuses, target dates, competency names).
- Document success metrics (e.g., create/list goals, link entries, summarize by goal).
- Capture assumptions, dependencies, and scope boundaries for Phase 2.

### 2) Storage Updates *(Planned)*
- Extend `src/storage/google_sheets_client.py` to read/write new tabs: Goals, Competencies, GoalMappings.
- Define schemas and validation for each tab (required headers, date formats, statuses).
- Add setup/migration notes for creating tabs and headers in the sheet.
- Handle missing tabs or malformed rows with clear errors and logging.

### 3) Goal/Competency Commands *(Planned)*
- Implement `/goal_add`, `/goal_list`, `/goal_status`, `/goal_link`, `/goals_summary` in command and handler layers.
- Update parsing helpers to handle goal IDs, status updates, and optional competency tags.
- Add user-facing help text/examples that explain the new commands and arguments.

### 4) Entry Tagging & Retrieval *(Planned)*
- Update `/log`, `/task`, `/idea` flows to accept goal/competency references (e.g., `#goal:123`, `#comp:communication`).
- Normalize and persist mappings alongside existing entry records when logging.
- Include goal/competency context in `/week` and `/month` summaries and any goal summary responses.

### 5) Testing, QA, and Documentation *(Planned)*
- Add unit tests for parsing helpers, command behaviors, and storage interactions (with mocked Sheets API).
- Create integration-style tests for goal creation/listing and entry-to-goal mapping flows.
- Update README/ARCHITECTURE to reflect Phase 2 capabilities and configuration.
- Extend the user acceptance checklist for goal/competency scenarios.

## Milestones *(Planned)*
- **M1: Data Model & Storage** – Schemas and Sheets tabs created; storage client reads/writes goals and mappings. *(Planned)*
- **M2: Command Layer** – Goal/competency commands implemented with validation and help text. *(Planned)*
- **M3: Logging Integration** – Entry logging supports goal/competency references and persists mappings. *(Planned)*
- **M4: Retrieval & Summaries** – `/week`, `/month`, and goal summaries include goal/competency context. *(Planned)*
- **M5: Quality & Docs** – Tests updated; documentation and checklists refreshed. *(Planned)*

## User Acceptance Testing Checklist
The checklist remains in [User Acceptance Testing Checklist](./USER_ACCEPTANCE_TESTING_CHECKLIST.md) and should be expanded for goal/competency use cases.

## Risks and Mitigations
- **Schema drift or missing tabs**: provide setup instructions and runtime validation to detect missing/incorrect headers.
- **Complex command inputs**: offer clear help text and examples; validate goal IDs/statuses to prevent user errors.
- **Data consistency between entries and mappings**: enforce normalization and add logging around link operations.
- **Google Sheets performance/quotas**: batch operations where possible and surface actionable errors to users.
