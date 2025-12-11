# Agents and Responsibilities

This project is conceptually organized around a small set of “agents” or roles within the bot. These are **not** separate processes today, but they represent clear responsibility boundaries in the code and a roadmap for future refactoring (e.g., into microservices or separate workers).

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
- `/start` → welcome message, explain usage.
- `/help` → list available commands and examples.
- Delegates `/log`, `/task`, `/idea`, `/week`, `/month` to the Command Agent.

---

## 2. Command & Journal Agent

**Purpose:** Implements the core behavior for logging and retrieving entries.

**Responsibilities:**
- Interpret user intent from commands.
- Normalize data into a standard record format.
- Call the Storage Agent to persist or retrieve data.
- Perform basic aggregation for weekly/monthly summaries.

**Implemented by:**
- `src/bot/commands.py`
- `src/bot/parsing.py`

**Key behaviors:**
- `/log <text>` → log an accomplishment (Type=`accomplishment`).
- `/task <text>` → log a task/follow-up (Type=`task`).
- `/idea <text>` → log an idea (Type=`idea`).
- `/week` → fetch entries from the last 7 days and summarize.
- `/month` → fetch entries from the last 30 days and summarize.
- Extract tags from messages (e.g., `#portal`, `#apim`).

**Future expansion:**
- Map entries to goals and competencies.
- Tag entries by theme or category automatically.

---

## 3. Storage Agent

**Purpose:** Abstract storage operations so the rest of the bot doesn’t care about Google Sheets details.

**Responsibilities:**
- Append records to the Google Sheets “Accomplishments” sheet.
- Query records by date range and/or type.
- Hide authentication details and API specifics behind a clean interface.

**Implemented by:**
- `src/storage/google_sheets_client.py`

**Key behaviors:**
- `append_entry(record)` – write a single record to the sheet.
- `get_entries_by_date_range(start_date, end_date)` – read a list of records for a given period.

**Future expansion:**
- Support additional sheets (e.g., Goals, Competencies).
- Migrate to or supplement with a database backend.

---

## 4. Scheduler / Reminder Agent

**Purpose:** Proactively remind the user to log accomplishments and tasks.

**Responsibilities:**
- Trigger weekly reminders (e.g., every Friday afternoon).
- Send messages via the Telegram Interaction Agent.
- Optionally perform other periodic tasks (e.g., monthly summary dump).

**Implemented by:**
- `src/bot/scheduler.py`
- External cron job or systemd timer (if used).

**Key behaviors:**
- Weekly reminder: “What were your top 3 accomplishments this week?”
- Optionally, monthly nudges (e.g., “Run `/month` to review this month’s entries.”).

**Future expansion:**
- Adaptive reminders based on usage (e.g., if no entries logged this week).
- Reminders tied to goals or competency focus areas.

---

## 5. (Future) Evaluation & Coaching Agent

**Purpose:** Use the logged data to help draft self-evaluations and provide growth suggestions.

**Status:** Not implemented in Phase 1. Placeholder for future work.

**Responsibilities (planned):**
- Summarize quarterly or yearly accomplishments in a self-evaluation-friendly format.
- Map entries to goals and competencies.
- Suggest additional actions to strengthen weak areas (e.g., inclusion, empowerment).
- Integrate with external LLMs to generate draft self-evaluation sections.

**Potential implementation:**
- New module (e.g., `src/bot/evaluation_agent.py`).
- Additional commands (e.g., `/summary_q1`, `/draft_self_eval`).
- Integration with OpenAI or other LLM providers.


