# Career Compass Bot

Career Compass Bot is a personal Telegram bot designed to help you track your weekly accomplishments, tasks, ideas, and professional development activities. It provides a simple, low-friction way to build a record of your work throughout the year — making self-evaluations, goal updates, and career reflections dramatically easier.

Phase 1 focuses on logging and retrieval. Future phases will add goal mapping, competency tracking, and AI-driven career coaching.



## ✨ Features (Phase 1)

- **Log accomplishments, tasks, and ideas** directly from Telegram  
  (`/log`, `/task`, `/idea`)
- **Automatic weekly reminders** to capture your progress
- **Google Sheets storage** for structured, portable record-keeping
- **Quick summaries** of recent logs  
  (`/week`, `/month`)
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

Then fill in:
| Variable | Description |
|----------|-------------|
| TELEGRAM_BOT_TOKEN          | Token provided by BotFather |
| SPREADSHEET_ID              | ID of your Google Sheet |
| TELEGRAM_ALLOWED_USERS      | Optional comma-separated list of Telegram user IDs allowed to interact with the bot (e.g., `12345,67890`) |
| SERVICE_ACCOUNT_FILE        | Path to your service account JSON file (required if SERVICE_ACCOUNT_JSON is not set) |
| SERVICE_ACCOUNT_JSON        | Raw JSON string for service account credentials (required if SERVICE_ACCOUNT_FILE is not set) |
| LOG_LEVEL                   | Logging level (INFO by default) |
| TIMEZONE                    | IANA timezone for scheduling/logging (e.g., America/New_York or UTC) |
| REMINDERS_ENABLED           | Set to `false` to disable scheduled reminders |
| REMINDER_CHAT_ID            | Telegram chat ID to receive reminders (required if reminders are enabled) |
| REMINDER_DAY_OF_WEEK        | Day to send reminders (`mon`–`sun`) |
| REMINDER_TIME               | Time to send reminders in 24h `HH:MM` format |
| REMINDER_MESSAGE            | Custom reminder text |

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
### 7. Enable Google Sheets API
1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create a Service Account
4. Generate a JSON key file
5. Share your Google Sheet with:

```php-template
<service-account-name>@<project-id>.iam.gserviceaccount.com
```

Add the Phase 2 tabs (**Goals**, **Competencies**, **GoalMappings**) and headers described in
[`docs/GOOGLE_SHEETS_MIGRATION.md`](docs/GOOGLE_SHEETS_MIGRATION.md) before using goal/competency features.
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

## 📈 Operations & Monitoring

- **Logs:** All components log to standard output with timezone-aware timestamps. For containers,
  use `docker logs <container>`; for local runs, monitor the terminal session. Increase verbosity
  by setting `LOG_LEVEL=DEBUG` temporarily when debugging.
- **Google Sheets auth/quota issues:** Authentication failures typically surface as 401/403 errors.
  Ensure the service account email listed in your JSON credentials has edit access to the sheet
  and that `SERVICE_ACCOUNT_FILE`/`SERVICE_ACCOUNT_JSON` paths are correct. Quota exhaustion will
  return 429 errors—spread calls out, reduce reminder frequency, or request higher limits in the
  Google Cloud Console.
- **Reminder schedule/timezone changes:** Update `REMINDER_DAY_OF_WEEK`, `REMINDER_TIME`, and
  `TIMEZONE` in your environment (.env or container env vars) and restart the process so the
  scheduler picks up the new cadence. Setting `REMINDERS_ENABLED=false` skips scheduler startup
  entirely if you prefer external scheduling.


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