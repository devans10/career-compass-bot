# User Acceptance Testing Checklist

- [ ] Validate `/start` and `/help` respond with guidance for new users.
- [ ] Submit `/log`, `/task`, and `/idea` commands and verify entries reach Google Sheets with tags and correct schema.
- [ ] Run `/week` and `/month` after seeding data to confirm summaries format and date filtering are correct.
- [ ] Confirm invalid or empty payloads return friendly error messages without crashing.
- [ ] Trigger a scheduled reminder (or use `send_reminder_now`) to verify delivery to the configured chat ID at the expected time.
- [ ] Start the bot with missing or malformed configuration values to ensure validation errors surface clearly.
- [ ] Review logs during command execution and reminders to confirm consistent formatting and helpful context.
- [ ] Execute test suite (`pytest`) to confirm automated checks pass in CI/local environments.
