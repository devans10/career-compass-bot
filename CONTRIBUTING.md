# Contributing Guidelines

Thank you for contributing to this project!  
To maintain high quality, architectural consistency, and predictable development workflows, all contributors—human or Codex—must follow the guidelines below.

---

## 1. Development Workflow

### Use Codex with a Defined Plan
- When working with Codex, **always begin by generating a Plan** before writing or modifying code.
- The Plan must detail:
  - Specific steps to complete the task
  - Files to be created or modified
  - Test additions/updates
  - Required documentation updates  
- The Plan must be approved before any implementation begins.
- Treat the Plan as a contract; if implementation deviates, revise the Plan first.

### Test-Driven Development (TDD)
- Write or update tests **before implementing** new features or refactors.
- Ensure tests cover:
  - Expected behavior
  - Error conditions
  - Edge cases
  - Regression scenarios
- All tests must pass before opening a Pull Request.

---

## 2. Documentation Requirements

### Keep `ARCHITECTURE.md` Accurate
- Review `ARCHITECTURE.md` prior to making changes.
- If the change affects:
  - Component boundaries  
  - Data flows  
  - Integrations  
  - Dependencies  
  - Deployment patterns  
  - Service interactions  
—then the architecture document **must** be updated.
- Architecture documentation is part of the deliverable, not optional.

### Update `CHANGELOG.md`
For every contribution, update `CHANGELOG.md` with an entry describing:

- **Added** — new features, endpoints, modules, or tooling  
- **Changed** — modifications to existing behavior  
- **Fixed** — bug fixes or regressions  
- **Removed** — deprecated or removed functionality  

Entries must be clear and scoped.

### Use `FUTURE_ENHANCEMENTS.md` for Roadmap Items
- New ideas, possible improvements, or larger future initiatives should be added here.  
- Do not include roadmap content in other files.
- Keep entries focused, short, and organized by category or priority.

---

## 3. Coding Standards

### Code Quality
- Follow the project’s established patterns, style conventions, and directory structure.
- Avoid introducing new dependencies unless justified in the Plan.
- Keep changes well scoped; avoid incidental refactoring unless explicitly part of the task.

### Testing Standards
- Prefer small, isolated tests.
- Maintain existing testing frameworks and patterns.
- Include fixtures, mocks, or test data as needed.

### Local Quality Checks
- Run unit tests: `pytest`
- Lint code: `ruff check`
- Type-check: `mypy`
- Address all reported issues before opening a PR.

---

## 4. Pull Requests

### PR Requirements
Every Pull Request must include:

1. A summary of the change  
2. A link to or pasted version of the Codex Plan (if Codex was involved)  
3. Confirmation that:
   - Tests were updated/written  
   - All tests pass  
   - `ARCHITECTURE.md` was reviewed/updated if needed  
   - `CHANGELOG.md` was updated  
4. A description of any follow-up work added to `FUTURE_ENHANCEMENTS.md`  

### PR Review Guidelines
- Small, focused PRs are easier to review and merge.
- Architectural modifications require more thorough discussion.
- PRs that do not meet documentation or testing requirements will not be merged.

---

## 5. Branching & Commit Practices

### Branching Strategy
- Create feature branches using a clear naming convention:  
  `feature/<name>`  
  `fix/<name>`  
  `refactor/<name>`  

### Commit Messages
- Use descriptive, concise commit messages.
- Follow the “one logical change per commit” principle.

---

## 6. Roadmap & Long-Term Planning

- Larger ideas, research topics, or enhancements that are not part of the immediate development cycle should be added to `FUTURE_ENHANCEMENTS.md`.
- If a feature is too big for one PR, break it down into well-defined tasks and ensure the Plan treats them as separate steps.

---

## 7. Contributor Expectations

All contributors are expected to:

- Follow TDD  
- Maintain architectural integrity  
- Keep documentation current  
- Use Codex responsibly with Plans  
- Write clean, maintainable code  
- Participate respectfully in reviews  

---

If you have any questions, propose improvements to the guidelines by opening an issue or PR.  
Thank you for helping make this project better!