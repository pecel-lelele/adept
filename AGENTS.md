# AGENTS.md

> **Primary Operating Manual for AI Agents**  
> This file is the single authoritative entry point and standard operating procedure for all AI agents, autonomous coding assistants, and IDE extensions (e.g., Cursor, Windsurf, Copilot, Qoder, Roo Code, Aider, Devins, Antigravity) working in the **Adept** repository.  
> *Note for Claude Code and Gemini CLI users:* See [CLAUDE.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/CLAUDE.md) and [GEMINI.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/GEMINI.md), which maintain feature parity with this document.

---

## 1. Project Context & Mission

- **Repository**: `adept`
- **Competition**: SDC XMUM Hackathon, Domain 1: *The Aiversecity Future-Ready Workforce*
- **Main SDG**: **SDG 4** (Quality Education) | **Key Targets**: 4.4, 4.3, 8.2, 8.5
- **Secondary SDGs**: SDG 5 (Gender Equality), SDG 8 (Decent Work), SDG 9 (Industry & Innovation), SDG 10 (Reduced Inequalities)
- **Problem Statement**: Build an AI-driven platform that continuously monitors AI advancement to forecast emerging/declining jobs and skills, matches workforce talent to future roles with explainable skills-gap analysis, and creates personalised reskilling pathways linked to the 17 UN Sustainable Development Goals.
- **Product Architecture**: A unified backend engine serving two primary front-end modes:
  1. **Individual Mode (`/app`)**: Tailored for working adults facing displacement, fresh graduates, and career switchers.
  2. **Organisation Mode (`/org`)**: Tailored for corporate HR/L&D managers and TVET / university career advisors.
  - *Full context & product details:* [docs/PROJECT_CONTEXT.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/docs/PROJECT_CONTEXT.md)
  - *Detailed system architecture:* [docs/architecture.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/docs/architecture.md)

---

## 2. Agent Initialization Protocol (Session Start)

Every AI agent starting a session in this repository **must** follow this 3-step initialization routine:

### Step 1: Identify Team Member & Feature Scope
If the user prompt does not explicitly declare their role and feature, ask immediately:
1. Which team member are you? (**M1**, **M2**, **M3**, or **M4**)
2. Which feature are you working on? (**F1** to **F8**, or **Core**)

### Step 2: Ingest Assigned Feature Context
Before planning or writing code, read the relevant specification files:
1. Feature task breakdown in [docs/TASKS.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/docs/TASKS.md)
2. Feature-specific documentation in `src/api/app/features/<feature>/FEATURE.md` (e.g., [src/api/app/features/trends/FEATURE.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/src/api/app/features/trends/FEATURE.md))
3. Prior decisions and methodology in [docs/decisions.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/docs/decisions.md) under the member's section (`## M1`, `## M2`, `## M3`, or `## M4`).
4. Core team rules in [docs/TEAM_RULES.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/docs/TEAM_RULES.md).

### Step 3: Verify Git Branch
Ensure work is being performed on a designated feature branch (`<type>/<feature>-<short-desc>`), **never directly on `main`**.

---

## 3. Non-Negotiable Guardrails (Hard Constraints)

These constraints derive directly from the Hackathon Handbook and competition ethics guidelines. **No agent may bypass them under any circumstances.**

1. **Synthetic & Public Data Only**:
   - Never ingest, parse, store, or display real personal data, private identities, or real resumes.
   - Only synthetic personas ([Aisyah, Wei Jie, Ravi](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/docs/PROJECT_CONTEXT.md#L160-L167)) and synthetic organisation data are permitted.
2. **Zero Hallucination / Zero Invented Entities**:
   - The system **must never invent** jobs, courses, skills, statistics, or SDG target definitions.
   - All recommendations, titles, and IDs must resolve against records in the database or cited official taxonomy datasets.
3. **F8 Grounding & Validation Gate**:
   - If an LLM or generative model is invoked, its output must pass through the validation filter (`validate_ids` in [src/api/app/core/llm/](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/src/api/app/core/llm/)) to verify that generated entity IDs exist in the catalog before reaching the user.
4. **Mandatory Output Attribution (`RecommendationMeta`)**:
   - Every API endpoint and UI card presenting recommendations, match scores, or trend projections **must** provide full attribution metadata:
     ```json
     {
       "sources": [{"name": "Source Name", "url": "https://...", "retrieved_at": "YYYY-MM-DD"}],
       "snapshot_date": "YYYY-MM-DD",
       "scenario": "moderate | fast",
       "is_estimate": true
     }
     ```
   - All predicted trends or forecasts must be explicitly labelled as **estimates**.
5. **Human-in-the-Loop Decision Support**:
   - The platform provides insights to guide human judgment. It must **never** make autonomous hiring, firing, promotion, or admission decisions.
6. **Transparent AI Disclosure**:
   - If any LLM or foundation model is utilized, its provider, model name, and specific purpose must be declared on the `/about` page and in the [README.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/README.md).
7. **Zero Secrets in Repository**:
   - Never commit API keys, credentials, or `.env` files. Keep [.env.example](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/.env.example) updated when introducing environment variables.

---

## 4. Feature Ownership Matrix & Repository Layout

### Feature Ownership Matrix

| Feature ID | Feature Name | Owner | Primary Code Locations |
|---|---|---|---|
| **F1** | Skills Profile Intake | **M2** | `src/api/app/features/profile/`<br>`src/web/src/features/profile/`<br>`src/api/app/contracts/profile.py` |
| **F2** | AI-Trend Signal Layer & Radar | **M1** | `src/api/app/features/trends/`<br>`src/web/src/features/trends/`<br>`src/pipelines/trends/`<br>`src/api/app/contracts/trends.py` |
| **F3** | Scenarios & Uncertainty | **M1** | `src/api/app/features/scenarios/`<br>`src/web/src/features/scenarios/`<br>`src/api/app/contracts/scenarios.py` |
| **F4** | Future-Role Matching & Gap | **M2** | `src/api/app/features/matching/`<br>`src/web/src/features/matching/`<br>`src/pipelines/matching/`<br>`src/api/app/contracts/matching.py` |
| **F5** | Reskilling Pathway & Catalogue | **M3** | `src/api/app/features/pathway/`<br>`src/web/src/features/pathway/`<br>`src/api/app/contracts/pathway.py` |
| **F6** | SDG Mapping & Contribution | **M3** | `src/api/app/features/sdg/`<br>`src/web/src/features/sdg/`<br>`src/pipelines/sdg/`<br>`src/api/app/contracts/sdg.py` |
| **F7** | Organisation Mode & Heatmaps | **M4** | `src/api/app/features/org/`<br>`src/web/src/features/org/`<br>`src/api/app/contracts/org.py` |
| **F8** | Guardrails & Transparency | **M3** | `src/api/app/core/llm/`<br>`src/web/src/features/guardrails/`<br>`src/web/src/app/about/` |
| **Core** | App Shells, Auth, Design, Deploy | **M4** | `src/web/src/components/`<br>`src/web/src/features/core/`<br>`src/web/src/config/navigation.ts`<br>`Makefile`, `src/scripts/dev.py` |

### Where Code Lives

```
docs/                                 # Central documentation (specs, rules, decisions, architecture)
src/
  api/
    app/main.py                       # FastAPI entrypoint (auto-discovers features/*/router.py)
    app/core/                         # Config, db, auth, logging, llm gateway (F8)
    app/contracts/                    # Shared Pydantic contracts (one file per feature)
    app/features/<feature>/           # router.py, service.py, repository.py, schemas.py, mocks.py
    openapi.json                      # Generated OpenAPI contract
  web/
    messages/<locale>/<feature>.json  # Localisation: en, ms, zh (one per feature namespace)
    src/app/                          # Thin Next.js App Router route pages
    src/features/<feature>/           # Feature components, hooks, api.ts, index.ts
    src/components/                   # Shared UI primitives (ScenarioToggle, SourceBadge, etc.)
    src/lib/api/                      # Typed API client + types.ts generated from openapi.json
  pipelines/<feature>/                # Offline data preparation and ML pipelines
  db/                                 # SQL migrations and migration runner (src/db/migrate.py)
  data/seed/<feature>/                # Synthetic CSV seed data (raw data is gitignored)
  scripts/dev.py                      # Cross-platform Python task runner
tests/
  api/<feature>/                      # Feature-specific API and contract tests
  pipelines/<feature>/                # Data and ML pipeline tests
submission/                           # Proposal document, pitch deck, demo links
```

---

## 5. Working Agreements & Anti-Conflict Rules

To prevent merge conflicts and coordination bottlenecks across multiple engineers and agents:

1. **Feature Boundary Isolation**:
   - Focus edits strictly within the current feature's directories.
   - Do not refactor or restructure adjacent feature packages unprompted.
2. **Shared Things Protocol**:
   Before modifying any shared component, **explicit confirmation from the user/lead is mandatory**:
   - Shared API contracts (`src/api/app/contracts/`)
   - Database migrations (`src/db/migrations/`)
   - Root configuration (`Makefile`, `pyproject.toml`, `docker-compose.yml`, `.env.example`)
   - Dependency files (`requirements.txt`, `src/web/package.json`, `pnpm-lock.yaml`)
   - Navigation and shared shell components (`src/web/src/components/`, `src/web/src/config/navigation.ts`)
   - AI context documents (`docs/PROJECT_CONTEXT.md`, `CLAUDE.md`, `GEMINI.md`, `AGENTS.md`)
3. **Database Changes: Append-Only Migrations**:
   - **Never edit an existing migration file.**
   - Always create a new timestamped migration file in `src/db/migrations/` using format `YYYYMMDDHHMMSS_<description>.sql`.
   - Maintain both `-- migrate:up` and `-- migrate:down` sections.

---

## 6. Engineering Standards & Code Quality

### Tech Stack Standards
- **Backend**: Python 3.11 with FastAPI and strict Pydantic v2 validation.
- **Frontend**: Next.js 16 (App Router), TypeScript with `strict: true`, Tailwind CSS v4, shadcn/ui primitives.
- **Database**: PostgreSQL 16 with `pgvector` extension.
- **Client Generation**: `openapi-typescript` + `openapi-fetch` generating typed client bindings.
- **Internationalisation**: `next-intl` (en, ms, zh). Key parity with English is enforced during `make check`.

### Implementation Rules
- **Type Everything**: Comprehensive Python type hints (return types, argument types); zero `any` in TypeScript.
- **Thin Pages, Rich Features**: Page routes (`src/web/src/app/...`) must remain thin wrappers that import self-contained feature components (`src/web/src/features/<feature>/`).
- **Small, Pure Functions**: Validation, scoring algorithms, and parsing logic must be isolated in pure, testable functions with comprehensive unit tests.
- **Data/ML 6-Stage Pipeline Standard**:
  Any offline pipeline or model job must adhere to and document the 6 canonical stages:
  $$\text{Data Source} \longrightarrow \text{Preprocessing / Cleaning} \longrightarrow \text{Feature Engineering} \longrightarrow \text{Model / Method} \longrightarrow \text{Evaluation} \longrightarrow \text{Serving}$$

---

## 7. Mandatory Decisions Log Protocol (`docs/decisions.md`)

**Every change that introduces or modifies a model, method, formula, dataset, schema, dependency, or architectural decision MUST be recorded in [docs/decisions.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/docs/decisions.md).**

### Rules for Logging Decisions
1. Write **only** in your assigned member section (`## M1`, `## M2`, `## M3`, or `## M4`).
2. Add new entries at the **bottom** of your section (above the terminating `---`).
3. Never edit or overwrite previous entries. If superseding an old decision, add a new entry referencing `Replaces: <OLD-ID>`.
4. Use the entry ID format `<member>-<NNN>` (e.g., `M1-001`, `M2-003`).

### Entry Template
```markdown
### M?-NNN: <short title>
- **Date**: YYYY-MM-DD
- **Feature**: F? (<name>)
- **Type**: model | method | data source | formula | contract | dependency | schema | UI | other
- **Change**: what changed, in one or two sentences
- **Why**: reason, options considered
- **Pipeline** (data/ML only): source → preprocessing/cleaning → features → model/method → evaluation (metric + result) → serving
- **Affects**: teammates or features impacted (or "none")
- **Replaces**: <entry ID> (or "none")
- **PR / branch**: <link or branch name>
```

---

## 8. Git & Pull Request Protocol

1. **Branch Naming**:
   - Format: `<type>/<feature>-<short-desc>`
   - Allowed types: `feat`, `fix`, `docs`, `chore`, `refactor`
   - Example: `feat/trends-radar-chart`, `fix/matching-score-breakdown`
2. **Commit Convention**:
   - Format: `<type>(<feature>): <short description>`
   - Example: `feat(trends): add radar chart visualization`, `fix(matching): handle zero overlapping skills`
3. **No Direct Commits to `main`**:
   - `main` is protected and must always remain deployable and stable.
4. **Pre-PR Quality Gate (`make check`)**:
   Before proposing a commit or concluding a session, run the quality gate:
   ```bash
   make check
   # Cross-platform fallback on Windows without make:
   uv run --no-project python src/scripts/dev.py check
   ```
   `make check` runs:
   - Ruff lint & format validation (Python)
   - ESLint & TypeScript compilation checks (`tsc --noEmit`)
   - `next-intl` translation-key parity check across all locales
   - Pytest unit and contract test suite
   - Contract drift verification (validates `openapi.json` and generated TypeScript definitions)

---

## 9. Development Commands & Operational Guide

All targets use the cross-platform runner [src/scripts/dev.py](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/src/scripts/dev.py). Use standard `make <command>` or `uv run --no-project python src/scripts/dev.py <command>`.

| Command | Action |
|---|---|
| `make setup` | Initialize `.venv`, install Python & web deps, create `.env`, start Postgres, migrate, seed |
| `make dev` | Start FastAPI backend (:8000) and Next.js frontend (:3000) with hot reload |
| `make check` | Execute complete quality gate (lint, test, typecheck, contract sync, i18n check) |
| `make lint` / `make format` | Check linting (Ruff + ESLint) / auto-format Python |
| `make test` | Run pytest test suite across `tests/` |
| `make typecheck` | Run TypeScript validation (`tsc --noEmit`) in `src/web` |
| `make contracts` | Regenerate `src/api/openapi.json` and TypeScript types (`src/web/src/lib/api/types.ts`) |
| `make db-up` / `make db-down` | Start / stop PostgreSQL 16 container with `pgvector` (host port 5433) |
| `make db-migrate` | Apply pending database migrations |
| `make seed` | Load synthetic seed datasets from `src/data/seed/` |

---

## 10. Agent Verification Checklist

### Pre-Flight (Before Writing Code)
- [ ] Confirmed member role (M1–M4) and feature (F1–F8 / Core).
- [ ] Verified current working branch is `<type>/<feature>-<short-desc>`.
- [ ] Reviewed `docs/PROJECT_CONTEXT.md` and feature `FEATURE.md`.
- [ ] Confirmed no shared items or foreign feature code will be modified without user permission.

### Post-Flight (Before Completing Task)
- [ ] Verified synthetic data only; no real PII or invented entities.
- [ ] Verified all recommendations include `sources`, `snapshot_date`, `scenario`, and `is_estimate`.
- [ ] Added required entry to [docs/decisions.md](file:///c:/Users/Darren%20Suwandi/Documents/SDC/adept/docs/decisions.md) in the member's section.
- [ ] If contracts changed, ran `make contracts` and updated client types.
- [ ] Successfully passed `make check` (or cross-platform python equivalent).
- [ ] Provided a concise summary of changes and suggested standard commit message.
