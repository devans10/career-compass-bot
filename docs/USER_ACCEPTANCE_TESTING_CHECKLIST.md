# User Acceptance Testing Checklist

- [ ] Validate `/start` and `/help` respond with guidance for new users.
- [ ] Submit `/log`, `/task`, and `/idea` commands and verify entries reach Google Sheets with tags and correct schema.
- [ ] Create goals with `/goal_add`, list them with `/goal_list`, and confirm statuses/target dates render correctly.
- [ ] Update goal status via `/goal_status <id> <status>` and confirm invalid statuses produce helpful errors.
- [ ] Link entries to goals/competencies using `/goal_link` and by embedding `#goal:`/`#comp:` tags in `/log` commands;
      confirm GoalMappings rows are created.
- [ ] Run `/week` or `/month` after linking data to ensure summaries include goal titles/statuses and competency names.
- [ ] Verify the Google Sheet contains **Goals**, **Competencies**, and **GoalMappings** tabs with the expected headers
      before running goal/competency commands.
- [ ] Run `/week` and `/month` after seeding data to confirm summaries format and date filtering are correct.
- [ ] Confirm invalid or empty payloads return friendly error messages without crashing.
- [ ] Trigger a scheduled reminder (or use `send_reminder_now`) to verify delivery to the configured chat ID at the expected time.
- [ ] Start the bot with missing or malformed configuration values to ensure validation errors surface clearly.
- [ ] Review logs during command execution and reminders to confirm consistent formatting and helpful context.
- [ ] Execute test suite (`pytest`) to confirm automated checks pass in CI/local environments.
