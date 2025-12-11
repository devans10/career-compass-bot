# Career Compass Bot – Architecture

## Overview

The Career Compass Bot is a personal Telegram bot that helps log weekly work accomplishments, tasks, and ideas into a structured datastore (Google Sheets). The goal is to make it easy to build a history of work that can be used later for self-evaluations (mid-year and end-of-year), goal tracking, and eventually career coaching.

Phase 1 focuses on:
- Fast, low-friction logging via Telegram.
- Structured storage in Google Sheets.
- Weekly reminders to capture accomplishments.
- Simple retrieval of recent entries (week/month).

Future phases will add:
- Goal and competency mapping.
- AI-powered summarization and drafting of self-evaluations.
- More advanced analytics and suggestions.

---

## High-Level Architecture

```text
Telegram Client (User)
    ↓
Telegram Bot API
    ↓
Bot Application (Python)
    - Command parsing (/log, /task, /week, /month)
    - Message handling
    - Scheduling weekly reminders
    - Storage operations
    ↓
Google Sheets (Spreadsheet)
    - "Accomplishments" sheet
```

---

### Components
### 1. Bot Application (src/bot/)

main.py

- Entry point for the bot.
- Configures the Telegram bot client.
- Registers command handlers and starts the polling/webhook loop.

handlers.py

- Contains the Telegram update handlers.
- Routes incoming messages and commands to the appropriate functions in commands.py.
- Handles errors and user-facing error messages.

commands.py

- Implements the core command behaviors:
    - /start – introduces the bot and basic usage.
    - /help – lists available commands and examples.
    - /log – logs an accomplishment.
    - /task – logs a task or follow-up item.
    - /idea – logs an idea or future improvement.
    - /week – retrieves entries from the last 7 days.
    - /month – retrieves entries from the last 30 days.
- Calls into storage.google_sheets_client to persist/retrieve data.

scheduler.py

- Implements periodic tasks such as weekly reminders.
- Uses an in-process scheduler (e.g., APScheduler) or exposes functions to be used by an external cron job.
- Example job: send a message every Friday asking the user to log their top accomplishments for the week.

parsing.py

- Utility functions for:
    - Parsing command arguments and free-text messages.
    - Extracting tags (e.g., #portal, #apim).
    - Normalizing entry type (accomplishment, task, idea, reflection).

---

### 2. Storage Layer (src/storage/)

google_sheets_client.py

- Provides a thin abstraction over the Google Sheets API.
- Responsibilities:
    - Append rows to the “Accomplishments” sheet.
    - Query rows by date range or type.
- Uses a Google Service Account for authentication.
- Sheet structure (Phase 1):

| Column    | Description |
|-----------|-------------|
| Timestamp | Full timestamp (ISO 8601) of when entry was logged |
| Date	    | Date only for easier filtering (YYYY-MM-DD)        |
| Type	    | accomplishment, task, idea, reflection             |           
| Text	    | The original user-entered text                     |
| Tags	    | Free-form tags (e.g. #portal #apim)                | 
| Source	| manual or weekly_prompt                            |

---

### 3. Configuration (src/config.py)

Centralized configuration:

- Telegram bot token.
- Google Sheets spreadsheet ID.
- Google Service Account credentials path or JSON.
- Timezone and scheduling settings.

Configuration is loaded from environment variables, with defaults where appropriate. A .env.example is provided for local development.

---

### 4. Logging (src/logging_config.py)

Standardizes logging:

- Log levels (INFO, DEBUG, ERROR).
- Format includes timestamp, level, and message.
- Used by all modules for easier debugging and production monitoring.

---

### 5. Tests (tests/)

- test_parsing.py – unit tests for parsing tags, dates, and entry types.
- test_commands.py – tests for core command logic, using mocks for the storage layer and Telegram API.

---

## Data Flow
### Logging an Accomplishment

1. User sends /log Improved APIM throughput dashboard for the customer portal. #portal #apim in Telegram.
2. Telegram sends the update to the Bot Application.
3. handlers.py routes the /log command to commands.log_command.
4. commands.log_command:
    - Parses the message into Type=accomplishment, Text, Tags.
    - Constructs a record with Timestamp, Date, Type, Text, Tags, Source=manual.
    - Calls google_sheets_client.append_entry(record).
5. Google Sheets stores the new row.
6. Bot sends a confirmation message back to the user.

### Weekly Reminder

1. scheduler.py triggers a job every week (e.g., Friday at 15:00).
2. The job sends a Telegram message:
    - “Weekly check-in: what were your top 3 accomplishments this week?”
3. User replies using /log commands or plain text (free-text can be treated as /log).
4. Flow continues as in “Logging an Accomplishment”.

### Retrieval (/week, /month)

1. User sends /week.
2. Bot routes to commands.week_command.
3. week_command calculates the date range (last 7 days).
4. Calls google_sheets_client.get_entries_by_date_range(start_date, end_date).
5. Formats the results into a summary message and sends it back to the user.

--- 

### Security and Privacy

- No confidential or sensitive information is expected to be stored.
- The bot is personal-use and interacts only with the owner’s Telegram account.
- Google Service Account credentials are stored securely outside of the repo (e.g., environment variables or mounted secrets).
- Google Sheets is used as simple structured storage; sharing is restricted to the bot’s service account and the owner’s Google account.

---

### Phases and Extensibility
#### Phase 1 (Current)

- Logging via Telegram.
- Google Sheets storage.
- Weekly reminders.
- Basic retrieval (week/month).

#### Phase 2 (Future)

- Goal and competency definitions stored in a dedicated sheet.
- Mappings from entries to goals/competencies.
- Additional commands for goal review and tagging.

#### Phase 3 (Future)

- AI-powered summarization and drafting of self-evaluation sections.
- Career coaching suggestions based on patterns in entries.
- Optional migration to a more robust datastore (e.g., database backend).