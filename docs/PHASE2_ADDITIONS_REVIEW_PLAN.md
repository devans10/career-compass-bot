# Phase 2 Additions Review Plan

This plan evaluates the additional recommendations for Goals and Competencies to ensure they match the HR process (goal reshaping, milestones with target dates, mid-year reviews, year-end self/manager evaluations, and reminders).

## Objectives
- Confirm each addition aligns with the HR workflow and approval path.
- Decide on scope (Phase 2 vs follow-on) and required schema/command impacts.
- Produce actionable tickets/updates for design, implementation, testing, and documentation.

## Inputs to review
- HR process summary (goal cascades, reshaping with managers, milestone target dates, mid-year and year-end evaluations, goal changes during the year).
- Recommended additions: milestones with target dates, goal lifecycle changes (edit/archive/supersede), mid-year review logging, year-end self/competency evaluations, and reminders.
- Existing Phase 2 plan and open GitHub issues derived from it.

## Review activities and owners
1. **Requirements confirmation (Product/HR partner)**
   - Validate milestone fields (name, target date, status, completion date) and lifecycle rules (edit/add/remove/supersede) against HR policy.
   - Clarify approval/notification expectations when goals change mid-cycle.
2. **Data model & storage review (Engineering/Storage)**
   - Check Google Sheets schema changes for milestones, lifecycle metadata, and review records.
   - Verify backward compatibility and migration steps for adding new tabs/columns.
3. **Command/UX review (Engineering/Bot UX)**
   - Evaluate proposed commands: `/goal_milestone_add`, `/goal_milestone_list`, `/goal_milestone_done`, goal edit/archive/supersede, `/review_midyear`, `/eval_goal`, `/eval_competency`, and reminder configuration.
   - Align help text/examples with HR terminology.
4. **Workflow integration (Product/Engineering)**
   - Map mid-year and year-end reviews to logging/summarization flows (e.g., `/goals_summary`, `/competencies_summary`).
   - Confirm how milestone status rolls up into goal status and summaries.
5. **Quality & compliance review (QA/Compliance)**
   - Define test cases for milestones, goal lifecycle transitions, and review entries.
   - Identify data retention/visibility requirements for historical goal changes and reviews.
6. **Decision & tracking (Product/PMO)**
   - Decide what ships in Phase 2 vs a follow-up milestone; update the roadmap and GitHub issues accordingly.
   - Document acceptance criteria per addition and any dependencies.

## Artifacts to produce
- Updated implementation plan and/or new GitHub issues reflecting accepted additions.
- Updated schemas (tabs/headers) and migration notes for Sheets.
- Help/usage notes for new commands and review flows.
- Test plan updates covering milestones, lifecycle edits, and review capture.

## Timeline
- **Week 1:** Requirements confirmation and data model review; propose schema/command changes.
- **Week 2:** UX/workflow review and QA test case definition; finalize acceptance criteria.
- **Week 3:** Decision checkpoint; update roadmap/issues and documentation.

## Acceptance criteria for the review
- Each recommended addition has a documented decision (accept/phase later/reject) with rationale.
- Required schema and command changes are captured as actionable tickets with owners and timelines.
- Review outputs are reflected in the Phase 2 plan and user-facing documentation.
