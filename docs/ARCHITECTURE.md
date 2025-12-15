# Career Compass Bot – Architecture

## Overview

Career Compass Bot is a personal Telegram bot that logs weekly work
accomplishments, tasks, and ideas into Google Sheets and layers in goal and
competency tracking. The bot keeps a running history of work and goal progress so
self-evaluations, status updates, and future coaching become low-effort.

The current release supports:
- Fast, low-friction logging via Telegram.
- Structured storage in Google Sheets across accomplishments, goals, mappings,
  milestones, reviews/evaluations, and reminder preferences.
- Weekly reminders to capture accomplishments.
- Retrieval of recent entries (week/month) enriched with goal/competency
  metadata when available.
- Goal lifecycle management (add, edit, status change, archive, supersede),
  milestone tracking, and evaluation/review recording.

Upcoming phases will add AI-powered summarization, richer analytics, and
coaching suggestions.

---

## High-Level Architecture

```text
Telegram Client (User)
    ↓
Telegram Bot API
    ↓
Bot Application (Python)
    - Command parsing (/log, /task, /goal_add, /goal_milestone_add, /week, /month, /reminder_settings, ...)
    - Message handling
    - Scheduling weekly reminders
    - Storage operations and goal/competency enrichment
    ↓
Google Sheets (Spreadsheet)
    - "Accomplishments" sheet
    - "Goals", "GoalMappings", "GoalMilestones", "GoalReviews", "GoalEvaluations", "Competencies", "CompetencyEvaluations", "ReminderSettings"
```

---

### Components
### 1. Bot Application (src/bot/)

**main.py**
- Entry point for the bot.
- Configures the Telegram bot client with allowed users and timezone handling.
- Registers command handlers and starts the polling loop.

**handlers.py**
- Telegram update handlers and error handling.
- Routes incoming messages and commands to `commands.py`.

**commands.py**
- Implements command behaviors:
  - Logging: `/start`, `/help`, `/log`, `/task`, `/idea`.
  - Retrieval: `/week`, `/month` with goal/competency enrichment and summaries.
  - Goals: `/goal_add`, `/goal_edit`, `/goal_status`, `/goal_archive`,
    `/goal_supersede`, `/goal_list`, `/goals_summary`.
  - Milestones: `/goal_milestone_add`, `/goal_milestone_done`, `/goal_milestones`.
  - Linking and context: `/goal_link`, automatic link creation from tags,
    enrichment of summaries with goal/competency titles/statuses.
  - Reviews/Evaluations: `/review_midyear`, `/eval_goal`, `/eval_competency`.
  - Reminders: `/reminder_settings` to view or set milestone/review reminder
    preferences.
- Uses `storage.google_sheets_client` for persistence and lookups.

**scheduler.py**
- In-process scheduling for weekly reminders (or disabled when using external
  cron).
- Emits reminder messages using the Telegram Interaction Agent and respects
  configuration flags.

**parsing.py**
- Utility helpers for:
  - Parsing command arguments and free text.
  - Extracting tags (e.g., `#portal`) and structured references
    (`#goal:<id>`, `#comp:<id>`).
  - Normalizing entry metadata and building goal/competency mappings.
  - Parsing goal lifecycle edits, milestone payloads, reviews, and reminder
    settings with validation.

---

### 2. Storage Layer (src/storage/)

**google_sheets_client.py**
- Thin abstraction over the Google Sheets API with schema enforcement.
- Responsibilities:
  - Append/query accomplishments with enforced headers and retry logic.
  - Manage multi-tab storage for Goals, GoalMappings, GoalMilestones,
    GoalReviews, GoalEvaluations, Competencies, CompetencyEvaluations, and
    ReminderSettings.
  - Validate required headers, accepted status vocabularies, and lifecycle
    states before writes.
  - Create sheets on-demand when allowed and guard against header mismatches.
- Key schemas (non-exhaustive):
  - **Accomplishments**: Timestamp, Date, Type, Text, Tags, Source.
  - **Goals**: GoalID, Title, Description, WeightPercentage, Status,
    CompletionPercentage, StartDate/EndDate/TargetDate, Owner, Notes,
    LifecycleStatus, SupersededBy, LastModified, Archived, History.
  - **GoalMappings**: EntryTimestamp, EntryDate, GoalID, CompetencyID, Notes.
  - **GoalMilestones**: GoalID, Title, TargetDate, CompletionDate, Status,
    Notes.
  - **GoalReviews/GoalEvaluations/CompetencyEvaluations**: ID, Notes, Rating,
    Reviewed/Evaluated dates.
  - **ReminderSettings**: Category, TargetID, Frequency, Enabled, Channel,
    Notes.

---

### 3. Configuration (src/config.py)

Centralized configuration loaded from environment variables:
- Telegram bot token and optional allowed users list.
- Google Sheets spreadsheet ID and service account credentials (file path or
  JSON string).
- Timezone, reminder enablement, reminder schedule, and chat IDs.
- Sheet/tab names and allowed vocabularies for goals, competencies, milestones,
  and reminder categories.
- Validations for goal/competency statuses and required tab headers to prevent
  schema drift.

---

### 4. Logging (src/logging_config.py)

Standard logging setup for the bot:
- Configures format, timestamps, and log levels.
- Shared by all modules to keep runtime diagnostics consistent.

---

### 5. Tests (tests/)

- `test_parsing.py` – tag extraction, command parsing, goal/competency ref
  parsing, reminder parsing.
- `test_commands.py` – command behavior and error handling for logging,
  summaries, goal management, milestones, and reminders using fakes.
- `test_handlers.py` – handler wiring and error propagation.
- `test_scheduler.py` – reminder scheduling behaviors.
- `test_google_sheets_client.py` – storage schema validation and read/write
  protections.
- `test_integration_flows.py` – end-to-end coverage for goal creation, linking,
  and summaries against fake Sheets.
- `test_config.py`, `test_logging_config.py`, `test_main.py` – configuration and
  bootstrap validation.

---

## Data Flow

### Logging an Accomplishment
1. User sends `/log Improved APIM throughput #goal:Q3-Launch #comp:communication`.
2. Telegram forwards the update to the Bot Application.
3. `handlers.py` routes the `/log` command to `commands.log_accomplishment`.
4. `commands.log_accomplishment`:
   - Parses the message into Type, Text, Tags, and extracts goal/competency
     references.
   - Builds one accomplishment row and optional GoalMappings rows.
   - Calls `google_sheets_client.append_entry` and `append_goal_mapping` to
     persist.
5. Google Sheets stores the rows.
6. The bot replies with a confirmation and echoes extracted tags/links.

### Weekly Reminder
1. `scheduler.py` triggers a job each week when `REMINDERS_ENABLED=true`.
2. The job sends a Telegram message such as “Weekly check-in: what were your top
   accomplishments?”
3. User replies using `/log` or other commands.
4. Flow continues as in “Logging an Accomplishment.”

### Retrieval (/week, /month)
1. User sends `/week`.
2. Bot routes to `commands.get_week_summary`.
3. The command calculates the date range and fetches accomplishments, goals,
   goal mappings, competencies, milestones, and reminder settings as needed.
4. Results are formatted into a summary with bullet points and goal/competency
   labels when present.
5. When `AI_SUMMARY_ENABLED=true` and both `AI_API_KEY` and `AI_MODEL` are
   configured, `ai_summarizer.py` builds a deterministic prompt and sends the
   entry text (including tags, goal titles, and competency labels) to the
   configured OpenAI-compatible endpoint for a condensed paragraph. Failures or
   opt-outs fall back to the built-in formatter.
6. Bot returns the summary to the user.

### Goal Lifecycle, Milestones, and Evaluations
1. User issues goal commands (`/goal_add`, `/goal_status`, `/goal_edit`,
   `/goal_archive`, `/goal_supersede`) or milestone commands
   (`/goal_milestone_add`, `/goal_milestone_done`, `/goal_milestones`).
2. `commands.py` parses structured fields (IDs, statuses, dates, notes) and
   validates against allowed vocabularies.
3. Storage Agent appends rows to **Goals** or **GoalMilestones** with audit
   metadata (LastModified, History, LifecycleStatus).
4. `/review_midyear`, `/eval_goal`, and `/eval_competency` append qualitative
   assessments to the corresponding evaluation/review sheets.

### Reminder Preferences
1. User runs `/reminder_settings` with optional key-value pairs
   (e.g., `category=milestone | frequency=weekly | enabled=true`).
2. Without arguments, the command lists existing settings; with arguments, it
   validates and persists the preference to **ReminderSettings**.
3. Scheduler or external automation can read these rows to drive targeted
   reminders.

---

### Phases and Extensibility
**Current:** Logging, retrieval, weekly reminders, goal/competency lifecycle,
linking, milestones, and evaluation/review capture backed by Google Sheets.

**Future:** AI-powered summaries and coaching prompts, richer analytics and
visualizations, automated action suggestions, and potential decomposition into
separate services/workers for scale or reliability.
