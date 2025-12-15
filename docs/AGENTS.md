# Agents and Responsibilities

This bot groups behaviors into a handful of conceptual “agents.” They run in a single
process today but define responsibility boundaries for future refactoring into
separate workers or services.

## 1. Telegram Interaction Agent

**Purpose:** Owns communication with the user via Telegram.

**Responsibilities:**
- Receive incoming messages and commands from the Telegram Bot API.
- Route updates to the appropriate command handlers.
- Format and send responses back to the user.
- Handle basic errors and user-friendly error messages.

**Implemented by:**
- `src/bot/main.py`
- `src/bot/handlers.py`

**Key behaviors:**
- `/start` → welcome message and quick reference.
- `/help` → examples for logging, goal management, and reminder commands.
- Delegates `/log`, `/task`, `/idea`, `/week`, `/month`, goal/competency
  commands, and reminder settings to the Command Agent.

---

## 2. Command & Journal Agent

**Purpose:** Implements the core behavior for logging, retrieving, and enriching
entries with goal/competency context.

**Responsibilities:**
- Interpret user intent from commands.
- Normalize data into a standard record format with tags and references.
- Call the Storage Agent to persist or retrieve data.
- Perform aggregation for weekly/monthly summaries and goal snapshots.

**Implemented by:**
- `src/bot/commands.py`
- `src/bot/parsing.py`

**Key behaviors:**
- `/log <text>` → log an accomplishment (Type=`accomplishment`).
- `/task <text>` → log a task/follow-up (Type=`task`).
- `/idea <text>` → log an idea (Type=`idea`).
- `/week` → fetch entries from the last 7 days and summarize, enriching with
  goal/competency titles and mappings when present.
- `/month` → fetch entries from the last 30 days and summarize, enriching with
  goal/competency context.
- Extract tags and structured references (e.g., `#portal`, `#goal:Q3-Launch`,
  `#comp:communication`).
- Goal management: `/goal_add`, `/goal_edit`, `/goal_status`, `/goal_archive`,
  `/goal_supersede`, `/goal_list`, `/goals_summary`.
- Milestone support: `/goal_milestone_add`, `/goal_milestone_done`,
  `/goal_milestones`.
- Reviews and evaluations: `/review_midyear`, `/eval_goal`, `/eval_competency`.
- Entry-to-goal linking: `/goal_link` and automatic link creation when tags are
  present during logging.
- Reminder configuration: `/reminder_settings` for milestone/review nudges.

---

## 3. Storage Agent

**Purpose:** Abstract storage operations so the rest of the bot doesn’t handle
Google Sheets details directly.

**Responsibilities:**
- Append and query accomplishments with enforced headers and validation.
- Manage multi-tab storage for **Goals**, **GoalMappings**, **GoalMilestones**,
  **GoalReviews/Evaluations**, **Competencies**, **ReminderSettings**, and
  related lookups.
- Enforce header schemas and valid vocabularies (statuses, lifecycle states)
  before writing.
- Hide authentication details and API specifics behind a clean interface.

**Implemented by:**
- `src/storage/google_sheets_client.py`

**Key behaviors:**
- `append_entry(record)` – write a single accomplishment/task/idea to the sheet.
- `append_goal(...)`/`get_goals()` – maintain goals with lifecycle metadata.
- `append_goal_mapping(...)` – link entry timestamps to goal/competency IDs.
- `append_goal_milestone(...)`/`get_goal_milestones()` – track milestone plans
  and completions.
- `append_goal_review(...)`, `append_goal_evaluation(...)`,
  `append_competency_evaluation(...)` – record qualitative assessments.
- `append_reminder_setting(...)`/`get_reminder_settings()` – persist reminder
  preferences.

---

## 4. Scheduler / Reminder Agent

**Purpose:** Proactively remind the user to log accomplishments and follow
through on milestones or reviews.

**Responsibilities:**
- Trigger weekly reminders (e.g., every Friday afternoon) when enabled.
- Send messages via the Telegram Interaction Agent.
- Optionally handle other periodic tasks (e.g., monthly summaries, milestone
  or review nudges based on saved reminder settings).

**Implemented by:**
- `src/bot/scheduler.py`
- External cron job or systemd timer (if used).

**Key behaviors:**
- Weekly reminder: “What were your top accomplishments this week?”
- Optional milestone/review reminders informed by `/reminder_settings`.
- Honors `REMINDERS_ENABLED` and timezone configuration.

**Future expansion:**
- Adaptive reminders based on streaks or inactivity.
- Reminder batching by goal or competency focus area.

---

## 5. Evaluation & Coaching Agent (Planned)

**Purpose:** Use the logged data to help draft self-evaluations and provide
growth suggestions.

**Status:** Goal/competency evaluations are captured today, but automated
coaching is not yet implemented.

**Responsibilities (planned):**
- Summarize quarterly or yearly accomplishments in a self-evaluation-friendly
  format.
- Map entries to goals and competencies for rubric-aligned narratives.
- Suggest actions to strengthen weaker competencies.
- Integrate with external LLMs to generate draft self-evaluation sections and
  coaching prompts.

**Potential implementation:**
- New module (e.g., `src/bot/evaluation_agent.py`).
- Additional commands (e.g., `/summary_q1`, `/draft_self_eval`).
- Integration with OpenAI or other LLM providers.
