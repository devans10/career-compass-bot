# Google Sheets Setup for Goals and Competencies

Phase 2 introduces three new tabs to the Google Sheets workbook used by the bot. These tabs must be created manually with the exact headers and value conventions below so validation in `GoogleSheetsClient` succeeds.

## Tabs and Required Headers

Create the tabs with the following names and headers in row 1:

- **Goals**
  - `GoalID`, `Title`, `Status`, `TargetDate`, `Owner`, `Notes`
- **Competencies**
  - `CompetencyID`, `Name`, `Category`, `Status`, `Description`
- **GoalMappings**
  - `EntryTimestamp`, `EntryDate`, `GoalID`, `CompetencyID`, `Notes`

Use the existing **Accomplishments** tab and headers (`Timestamp`, `Date`, `Type`, `Text`, `Tags`, `Source`) unchanged.

## Status and Date Rules

- **Goal statuses:** `Not Started`, `In Progress`, `Blocked`, `Completed`, `Deferred`
- **Competency statuses:** `Active`, `Inactive`
- **Date format:** All date fields (`TargetDate`, `EntryDate`) must use `YYYY-MM-DD`.

## Validation Behavior

- The bot raises a clear error if any of the new tabs are missing or their headers do not match exactly.
- Rows with missing required fields, invalid statuses, or incorrect date formats are rejected with descriptive messages.
- Goal mappings must include at least one of `GoalID` or `CompetencyID` and a non-empty `EntryTimestamp`/`EntryDate` pair.

## Migration Steps

1. Open the Google Sheets workbook used by the bot.
2. Add the three tabs above if they do not exist.
3. Paste the exact headers into row 1 of each tab.
4. Ensure any existing rows comply with the status and date rules; adjust values as needed.
5. Redeploy/restart the bot so the updated schema is loaded.
