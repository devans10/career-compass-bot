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
├─ requirements.txt
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
### 2. Install dependencies

```bash
pip install -r requirements.txt
```
---
### 3. Configure environment variables
Copy the example environment file:

```bash
cp .env.example .env
```

Then fill in:
| Variable | Description |
|----------|-------------|
| TELEGRAM_BOT_TOKEN          | Token provided by BotFather |
| SPREADSHEET_ID              | ID of your Google Sheet |
| SERVICE_ACCOUNT_FILE        | Path to your service account JSON file (required if SERVICE_ACCOUNT_JSON is not set) |
| SERVICE_ACCOUNT_JSON        | Raw JSON string for service account credentials (required if SERVICE_ACCOUNT_FILE is not set) |
| LOG_LEVEL                   | Logging level (INFO by default) |
| TIMEZONE                    | IANA timezone for scheduling/logging (e.g., America/New_York or UTC) |
| REMINDERS_ENABLED           | Set to `false` to disable scheduled reminders |
| REMINDER_CHAT_ID            | Telegram chat ID to receive reminders (required if reminders are enabled) |
| REMINDER_DAY_OF_WEEK        | Day to send reminders (`mon`–`sun`) |
| REMINDER_TIME               | Time to send reminders in 24h `HH:MM` format |
| REMINDER_MESSAGE            | Custom reminder text |

### Logging

Logs are written to standard output for both local CLI runs and containerized deployments.
Timestamps honor the configured `TIMEZONE` and follow the format
`YYYY-MM-DDTHH:MM:SS±ZZZZ | LEVEL | logger | message`. Adjust verbosity with `LOG_LEVEL`
(INFO by default).

---
### 4. Enable Google Sheets API
1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create a Service Account
4. Generate a JSON key file
5. Share your Google Sheet with:

```php-template
<service-account-name>@<project-id>.iam.gserviceaccount.com
```
---
### 5. Run the bot
```bash
python -m src.bot.main
```

The bot will begin polling for messages.


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