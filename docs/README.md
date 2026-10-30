# Documentation

Use these maintained guides rather than historical PR reports.

| Guide | Purpose |
|---|---|
| [Project README](../README.md) | Product behaviour, setup, configuration and checks |
| [Project context](project-context.md) | Competition brief, users and scope |
| [Solution design](solution-design.md) | Product approach and user journeys |
| [Architecture](architecture.md) | Services, data flow and workspace boundaries |
| [Tasks](tasks.md) | Feature ownership and task scope |
| [Team rules](team-rules.md) | Collaboration and engineering agreements |
| [Decisions](decisions.md) | Append-only record of methods, data and implementation choices |
| [Skill exposure methodology](skill-exposure-methodology.md) | Trend coefficient interpretation and evidence |
| [Submission proposal](submission-proposal.md) | Working proposal; team review and private fields remain pending |
| [Technical declaration](submission-technical-declaration.md) | Working technology/AI declaration; unsigned |
| [Submission deliverables](submission-deliverables.md) | Final deliverable checklist |

Feature-local `FEATURE.md` files document their current API, implementation and method.
Run results belong in PR descriptions and CI; old one-off validation and handoff reports
are recoverable from Git history. Existing decisions are retained as written, so historical
entries may mention a document's former name.

Use lowercase kebab-case for descriptive Markdown filenames. Keep conventional entrypoints
`README.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` and `FEATURE.md` so repository and agent
navigation continues to work. Use repository-relative links; avoid developer-specific paths.
