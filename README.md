# Career Compass Bot

Career Compass Bot is a personal Telegram bot designed to help you track your weekly accomplishments, tasks, ideas, and professional development activities. It provides a simple, low-friction way to build a record of your work throughout the year — making self-evaluations, goal updates, and career reflections dramatically easier.

Phase 1 focuses on logging and retrieval. Future phases will add goal mapping, competency tracking, and AI-driven career coaching.



## ✨ Features (Phase 1)

- **Log accomplishments, tasks, and ideas** directly from Telegram  
  (`/log`, `/task`, `/idea`)
- **Automatic weekly reminders** to capture your progress
- **Google Sheets storage** for structured, portable record-keeping
- **Quick summaries** of recent logs
  (`/week`, `/month`), with optional **AI-powered** condensing when enabled
- **Tag extraction** (e.g., `#apim #portal`) for future analytics
- **Extensible architecture** for future AI integration



## 🧭 Project Vision

Career Compass Bot is not just a journal — it's the first phase of a personal career development assistant.

Planned future capabilities:

- Goal and competency mapping  
- AI-guided self-evaluation drafting  
- Quarterly summaries and insights  
- Coaching suggestions  
- Growth pattern visualization  
- AI assistance for goal refinement

See [`docs/FUTURE_ENHANCEMENTS.md`](docs/FUTURE_ENHANCEMENTS.md) for more ideas.



## 📁 Repository Structure

```text
career-compass-bot/
├─ src/
│  ├─ bot/
│  │  ├─ main.py               # Entry point for the bot
│  │  ├─ handlers.py           # Telegram event handlers
│  │  ├─ commands.py           # Implementations of bot commands
│  │  ├─ scheduler.py          # Weekly reminder scheduling
│  │  └─ parsing.py            # Message/tag parsing helpers
│  │
│  ├─ storage/
│  │  └─ google_sheets_client.py  # Google Sheets read/write helper
│  │
│  ├─ config.py                # Environment variable + project settings
│  └─ logging_config.py        # Standard logging setup
│
├─ tests/
│  ├─ test_parsing.py
│  ├─ test_commands.py
│  └─ __init__.py
│
├─ docs/
│  ├─ ARCHITECTURE.md
│  ├─ AGENTS.md
│  └─ FUTURE_ENHANCEMENTS.md
│
├─ .env.example
├─ Dockerfile
├─ README.md
├─ CHANGELOG.md
└─ CONTRIBUTING.md
```

## 🛠️ Technology Stack

- Python 3.x
- Telegram Bot API
(via python-telegram-bot or aiogram)
- Google Sheets API for persistent storage
(service account)
- APScheduler or cron for reminders
- Docker (optional) for containerized deployment


## 🚀 Getting Started
### 1. Clone the repository
```bash
git clone https://github.com/<yourusername>/career-compass-bot.git
cd career-compass-bot
```
---
### 2. Set up a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

Dependencies are defined in `pyproject.toml`.

```bash
pip install --upgrade pip
pip install -e .            # Runtime dependencies
pip install -e '.[dev]'     # Optional: add linting/tests
```
---
### 4. Create your Telegram bot

Use [BotFather](https://t.me/BotFather) to create and configure your bot:

1. Start a chat with **BotFather** in Telegram.
2. Run `/newbot` and follow the prompts to set a display name and unique username (must end with `bot`).
3. Copy the **HTTP API token** BotFather returns — you will paste it into `TELEGRAM_BOT_TOKEN`.
4. (Optional) Use `/setdescription`, `/setuserpic`, and `/setabouttext` in BotFather to personalize the bot profile.

If you plan to restrict access, capture the Telegram user IDs you want to allow and supply them via `TELEGRAM_ALLOWED_USERS` (comma-separated list).
---
### 5. Configure environment variables
Copy the example environment file:

```bash
cp .env.example .env
```

Fill in the values that apply to your setup. The bot requires `TELEGRAM_BOT_TOKEN`, `SPREADSHEET_ID`, and **one** of `SERVICE_ACCOUNT_FILE` or `SERVICE_ACCOUNT_JSON` to start. Reminders and AI summaries are optional and can be toggled independently.

| Variable | Required? | Description |
|----------|-----------|-------------|
| TELEGRAM_BOT_TOKEN          | Yes | Token provided by BotFather. |
| SPREADSHEET_ID              | Yes | ID of your Google Sheet. |
| TELEGRAM_ALLOWED_USERS      | No  | Comma-separated list of Telegram user IDs allowed to interact with the bot (e.g., `12345,67890`). Leave blank to allow anyone who knows the bot handle. |
| SERVICE_ACCOUNT_FILE        | Conditional | Path to your service account JSON file (provide this **or** `SERVICE_ACCOUNT_JSON`). |
| SERVICE_ACCOUNT_JSON        | Conditional | Raw JSON string for service account credentials (provide this **or** `SERVICE_ACCOUNT_FILE`). |
| LOG_LEVEL                   | No  | Logging level (`INFO` by default). |
| TIMEZONE                    | No  | IANA timezone for scheduling/logging (e.g., `America/New_York` or `UTC`). |
| REMINDERS_ENABLED           | No  | Set to `false` to disable scheduled reminders. |
| REMINDER_CHAT_ID            | Conditional | Telegram chat ID to receive reminders (required when reminders are enabled). |
| REMINDER_DAY_OF_WEEK        | No  | Day to send reminders (`mon`–`sun`, defaults to `fri`). |
| REMINDER_TIME               | No  | Time to send reminders in 24h `HH:MM` format (defaults to `15:00`). |
| REMINDER_MESSAGE            | No  | Custom reminder text. |
| FOCUS_REMINDERS_ENABLED     | No  | Toggle focus reminders that highlight goals/milestones (defaults to `true`). |
| FOCUS_REMINDER_DAY_OF_WEEK  | No  | Day to send focus suggestions (`mon`–`sun`, defaults to Monday). |
| FOCUS_REMINDER_TIME         | No  | Time to send focus reminders in 24h `HH:MM` format (defaults to `09:00`). |
| FOCUS_REMINDER_MESSAGE      | No  | Intro line for the focus reminder payload. |
| FOCUS_UPCOMING_WINDOW_DAYS  | No  | Days ahead to check for target dates (defaults to `14`). |
| FOCUS_INACTIVITY_DAYS       | No  | Flag goals as inactive if no activity within this many days (defaults to `14`). |
| AI_SUMMARY_ENABLED          | No  | Set to `true` to enable AI-powered `/week` and `/month` summaries (defaults to `false`). |
| AI_API_KEY                  | Conditional | API key for your LLM provider (required when AI summaries are enabled). |
| AI_MODEL                    | Conditional | Model name to use with the provider (e.g., `gpt-4o-mini`). |
| AI_ENDPOINT                 | No  | Optional custom base URL for the AI provider (useful for gateways or self-hosted endpoints). |

#### AI-powered summaries for `/week` and `/month`

AI summarization is **opt-in** and off by default. To enable concise AI-written responses for `/week` and `/month`:

1. Set `AI_SUMMARY_ENABLED=true`.
2. Provide `AI_API_KEY` and `AI_MODEL` for your provider (OpenAI-compatible SDK is assumed). Optionally point to a gateway with `AI_ENDPOINT`.
3. Restart the bot so the configuration is picked up.

Privacy and control:

- Enabling AI summaries sends the text of your recent entries — including tags, goal links, and competency labels — to the configured provider to generate the response.
- No prompts or responses are persisted by the bot; storage remains in your Google Sheet. Review your provider’s data retention policies.
- Set `AI_SUMMARY_ENABLED=false` (or omit the AI variables) to skip AI calls and fall back to the built-in summarizer at any time.

### 6. Run the bot locally

The bot loads `.env` automatically for local development.

```bash
python -m src.bot.main
```

The bot will begin polling for messages.

### Logging

Logs are written to standard output for both local CLI runs and containerized deployments.
Timestamps honor the configured `TIMEZONE` and follow the format
`YYYY-MM-DDTHH:MM:SS±ZZZZ | LEVEL | logger | message`. Adjust verbosity with `LOG_LEVEL`
(INFO by default).

---
### 7. Enable Google Sheets API and prepare the workbook
1. Create (or use) a Google Cloud project.
2. Enable the **Google Sheets API**.
3. Create a **Service Account** and generate a JSON key file (download it for `SERVICE_ACCOUNT_FILE` or copy the JSON into `SERVICE_ACCOUNT_JSON`).
4. Share your Google Sheet with the service account email:

```php-template
<service-account-name>@<project-id>.iam.gserviceaccount.com
```

5. Create the tabs and headers below so the bot can validate writes/reads. Each block is copy/paste-ready for **row 1** of each tab:

```csv
Accomplishments
Timestamp,Date,Type,Text,Tags,Source

Goals
GoalID,Title,Description,WeightPercentage,Status,CompletionPercentage,StartDate,EndDate,TargetDate,Owner,Notes,LifecycleStatus,SupersededBy,LastModified,Archived,History

GoalMilestones
GoalID,Title,TargetDate,CompletionDate,Status,Notes

GoalMappings
EntryTimestamp,EntryDate,GoalID,CompetencyID,Notes

GoalReviews
GoalID,ReviewType,Notes,Rating,ReviewedOn

GoalEvaluations
GoalID,EvaluationType,Notes,Rating,EvaluatedOn

Competencies
CompetencyID,Name,Category,Status,Description

CompetencyEvaluations
CompetencyID,Notes,Rating,EvaluatedOn

ReminderSettings
Category,TargetID,Frequency,Enabled,Channel,Notes
```

Paste each section into its own tab (add a new sheet → rename it to the section title → paste the header row into line 1). If you prefer importing, save each section as a separate `.csv` file and use File → Import → Upload → Replace data for that tab. The existing **Accomplishments** tab must keep the six base headers shown above.

Add the Phase 2 tabs (**Goals**, **Competencies**, **GoalMappings**, **GoalMilestones**, **GoalReviews**, **GoalEvaluations**, **CompetencyEvaluations**, **ReminderSettings**) and headers exactly as described here or in [`docs/GOOGLE_SHEETS_MIGRATION.md`](docs/GOOGLE_SHEETS_MIGRATION.md).
Use these guards to avoid schema validation failures:

- Goal statuses must be one of: Not Started, In Progress, Blocked, Completed, Deferred.
- Competency statuses must be Active or Inactive.
- GoalMappings rows link entries to either `GoalID` or `CompetencyID` values (not both) and require ISO dates (`YYYY-MM-DD`).
---
### 8. Container build & runtime

A lightweight Dockerfile is included for containerized deployments.

```bash
# Build
docker build -t career-compass-bot .

# Run with your local .env and service account file
docker run \
  --env-file .env \
  -v $(pwd)/service_account.json:/app/service_account.json:ro \
  career-compass-bot
```

The default container command runs `python -m src.bot.main`, which starts Telegram polling
and the in-process scheduler when `REMINDERS_ENABLED=true`. To use an external cron instead,
disable the scheduler via `REMINDERS_ENABLED=false` and invoke the image on your schedule with
the same command.

### 9. Lightweight web dashboard

An experimental FastAPI dashboard is included for longer-form updates (goals, milestones,
reviews, and richer entries) backed by the same Google Sheets storage. Launch it locally with:

```bash
uvicorn src.dashboard.app:create_app --factory --host 0.0.0.0 --port 8000
```

The dashboard uses your existing `.env` (including the service account settings) and writes to
the same sheets as the Telegram bot. Keep it bound to `localhost` unless you add authentication
in front of it.

## 📈 Operations & Monitoring

- **Logs:** All components log to standard output with timezone-aware timestamps. For containers,
  use `docker logs <container>`; for local runs, monitor the terminal session. Increase verbosity
  by setting `LOG_LEVEL=DEBUG` temporarily when debugging.
- **Google Sheets auth/quota issues:** Authentication failures typically surface as 401/403 errors.
  Ensure the service account email listed in your JSON credentials has edit access to the sheet
  and that `SERVICE_ACCOUNT_FILE`/`SERVICE_ACCOUNT_JSON` paths are correct. Quota exhaustion will
  return 429 errors—spread calls out, reduce reminder frequency, or request higher limits in the
  Google Cloud Console.
- **Reminder schedule/timezone changes:** Update `REMINDER_DAY_OF_WEEK`, `REMINDER_TIME`,
  `FOCUS_REMINDER_DAY_OF_WEEK`, and `FOCUS_REMINDER_TIME` (plus `TIMEZONE`) in your environment
  (.env or container env vars) and restart the process so the scheduler picks up the new cadence.
  Setting `REMINDERS_ENABLED=false` skips scheduler startup entirely if you prefer external
  scheduling.


## 🤖 Commands
### Logging

- /log <text>
  Log an accomplishment.
- /task <text>
  Log a task or follow-up.
- /idea <text>
  Capture an idea or improvement.

Examples:

```bash
/log Improved APIM dashboard performance #apim #portal
/task Schedule meeting for timeout review
/idea Build Logic Apps p95 latency dashboard
```

### Goals & Competencies

- /goal_add <id> | <title> [| status=<status> | target=<YYYY-MM-DD> | owner=<name> | notes=<text>]
  Create or update a goal row in the **Goals** sheet.
- /goal_list
  Display all saved goals with status, target date, owner, and notes.
- /goal_status <id> <status> [notes]
  Append a status change with optional notes (statuses: Not Started, In Progress, Blocked, Completed, Deferred).
- /goal_link <goal/competency refs> [notes]
  Link the latest entry timestamp to a goal and/or competency (e.g., `/goal_link #goal:GOAL-1 #comp:communication`).
- /goals_summary
  Summarize goals by status and upcoming target dates.

Add `#goal:<id>` and `#comp:<competency>` tags inside `/log`, `/task`, or `/idea` messages to auto-map entries to the
**GoalMappings** sheet. Summaries include those links when present.
---
### Retrieval

- /week
  Show entries from the last 7 days.
- /month
  Show entries from the last 30 days.

---
### Help

- /help
Display available commands.

## ⏰ Weekly Reminder

Career Compass Bot can ping you once a week:

    “Weekly check-in: what were your top 3 accomplishments this week?”

Reminders are triggered via:
- An in-process scheduler (enabled automatically when `REMINDER_CHAT_ID` is set), or
- An external cron job that calls `send_reminder_now` from `src/bot/scheduler.py`.

Tune the cadence and message with `REMINDER_DAY_OF_WEEK`, `REMINDER_TIME`, and `REMINDER_MESSAGE`.


## 🧪 Testing

Tests are stored in the tests/ directory.
Run the entire suite with:
```bash
pytest
```

Quality checks are also configured for linting and type safety:

```bash
ruff check
mypy
```

## 🤝 Contributing

See `CONTRIBUTING.md`

for:

- Code style guidelines
- Using Codex to assist development
- Branching strategy
- PR requirements


## 🧠 Working with Codex

Codex performs best when you:
1. Reference the agent responsibilities in docs/AGENTS.md
2. Review system details in docs/ARCHITECTURE.md
3. Provide the file you want to modify or extend
4. Give Codex a clear role (“modify Command Agent”, “extend Storage Agent”, etc.)

This structure allows Codex to behave as a collaborative coding partner rather than a generic assistant.


## 📜 License

This project is for personal use.
You may adapt or extend it as needed.


## 🌟 Future Enhancements

Planned capabilities include:
- Goal and competency mapping
- AI-assisted accomplishment rewriting
- Quarterly summaries
- Self-evaluation drafting
- Growth trend analytics
- Multi-year career history

See `docs/FUTURE_ENHANCEMENTS.md`for the complete list.


## 🧭 Career Compass Bot

Your personal guide for navigating your accomplishments, growth, and career trajectory — one week at a time.