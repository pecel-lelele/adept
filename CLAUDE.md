# CLAUDE.md

Instructions for Claude Code in this repository. Read the imported files before doing any work.

@docs/PROJECT_CONTEXT.md
@docs/TEAM_RULES.md
@docs/TASKS.md

## Start of every session

1. If the user hasn't said, ask which member they are (M1–M4) and which feature they're working on (F1–F8 or Core).
2. Read that feature's section in `docs/TASKS.md`, its `FEATURE.md` if one exists, and the member's section in `docs/decisions.md`.

## Non-negotiable (from the hackathon handbook)

- Use only public, open or synthetic data. Never real personal data or real CVs.
- Never let the system invent jobs, courses, SDG targets or statistics. Recommendations come from data in the database or a cited source; LLM output must be validated against known IDs before it reaches the user.
- Every recommendation, score or trend shown to the user carries its source and date, its scenario where relevant, and is labelled as an estimate when it's a prediction.
- The product supports human decisions; it never makes hiring decisions.
- If an LLM is used, its name must be disclosed on the About page and in the README.
- Never commit secrets; keep `.env.example` up to date.

## Working agreements (from TEAM_RULES.md)

- Work mainly inside the current feature's folders.
- **Before** changing another feature's code or a shared thing (contracts/shared types, migrations, dependencies and lockfiles, root config, navigation/shared UI, the AI context files), tell the user what and why, and wait for their OK.
- New database changes go in a new migration file; never edit an existing one.
- After every meaningful change, add an entry to `docs/decisions.md` in the current member's section, at the bottom, using the template in that file.
- Primary stack is Python, Next.js (TypeScript) and PostgreSQL. Other libraries, models and methods are the feature owner's choice: if you introduce one, explain the choice briefly and record it in `docs/decisions.md`.

## Code quality

- Follow the conventions already used in the feature and the skeleton; don't restructure other code unprompted.
- Type everything (Python type hints, strict TypeScript).
- Keep scoring, parsing and validation logic in small, testable functions, and add tests for them.
- For data/ML work, structure it as a pipeline and document it in the decisions entry: data source → preprocessing/cleaning → feature engineering → model/method → evaluation → serving.

## Git

- Work on a branch named `<type>/<feature>-<short-desc>`; never commit directly to `main`, never force-push `main`.
- Before finishing: run the project's check command (`make check` if present), show `git status` and a short summary of the diff, and suggest a commit message `<type>(<feature>): <what changed>`.
