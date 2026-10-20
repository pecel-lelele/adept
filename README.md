# adept

**Adept** is our entry for the SDC XMUM Hackathon, Domain 1: *The Aiversecity Future-Ready Workforce*.
It takes a user from "who I am today" to "where I can be in the AI era": a skills profile, a
Future Skills Radar built from updatable AI/job-market trend signals, explainable future-role
matches with a skills gap, and a personalised reskilling pathway where every role and skill is
linked to the UN Sustainable Development Goals. Two modes share one engine: **Individual**
(working adults, graduates, career switchers) and **Organisation** (HR/L&D and career centres).

Every recommendation shows its source and date, its scenario (moderate vs fast AI disruption),
and is labelled as an estimate. The product supports human decisions; it never makes hiring
decisions. Demo data is synthetic only.

> **Status: in progress.** Pathway (F5), SDG mapping (F6), guardrails (F8) and the organisation
> heatmap / group plan run on real, dated data: a course catalogue from the Microsoft Learn
> Catalog API plus a verified HRD Corp-claimable provider page, and all 17 SDGs / 169 targets from
> the UN SDG API. Trends and matching still serve mock data (`source: MOCK DATA`), and the UI
> says so wherever it is used.

## AI disclosure

**No language model is used in the current version** (`LLM_PROVIDER=none`). Pathways, scores
and SDG links come from deterministic, explainable rules over the catalogue and seed data.

If a model is enabled later, it goes through the F8 gateway (`src/api/app/core/llm/`), which:

- lets the model only *select* IDs from a catalogue we supply and rejects any unknown ID;
- redacts personal data (email, MyKad NRIC, passport, phone) and filters prompt-injection text
  before any prompt is sent;
- falls back to the deterministic logic when the model is unavailable or invents an ID;
- logs every call with provider, model and outcome.

The provider and model are then read from configuration and shown live on `/about`
(`GET /api/v1/guardrails/disclosure`), so this disclosure cannot drift from what runs. Update
this section with the provider, model name and purpose in the same PR that enables one.

## Prerequisites

- Python 3.11 and [uv](https://docs.astral.sh/uv/) (uv can download Python 3.11 for you)
- Node.js 20+ (pnpm is used via `npx` if not installed)
- Docker Desktop (for PostgreSQL 16 + pgvector; optional, the API runs on mocks without it)
- GNU Make (optional; on Windows without make use `uv run --no-project python src/scripts/dev.py <target>`)

## Quick start

```bash
make setup    # .env, .venv + requirements.txt, pnpm install, db up, migrate, seed
make dev      # API http://localhost:8000/docs  ·  web http://localhost:3000
make check    # run before every PR
```

Then open http://localhost:3000 and click **Try the demo as Aisyah** or **Try the demo company**.

## Make commands

| Command | What it does |
|---|---|
| `make setup` | Create `.env` and `.venv`, install `requirements.txt` and `src/web` deps, start db, migrate, seed |
| `make dev` | Run the API (FastAPI, :8000) and web (Next.js, :3000) with reload |
| `make check` | Quality gate: ruff, eslint, translation-key parity, pytest, `tsc --noEmit`, contract drift |
| `make lint` / `make format` | Lint (ruff + eslint) / auto-format Python |
| `make test` | pytest over `tests/` |
| `make typecheck` | TypeScript check of `src/web` |
| `make contracts` | Regenerate `src/api/openapi.json` and `src/web/src/lib/api/types.ts` from the Pydantic contracts |
| `make db-up` / `make db-down` | Start / stop PostgreSQL + pgvector (host port 5433) |
| `make db-migrate` | Apply pending SQL migrations in `src/db/migrations/` |
| `make seed` | Load synthetic CSVs from `src/data/seed/` |

## Repository layout

The root layout is set by the hackathon committee.

```
docs/                     project context, team rules, tasks, decisions log, architecture
src/
  api/                    FastAPI + Pydantic v2
    app/main.py           auto-discovers app/features/*/router.py
    app/core/             config, db, auth (demo + Supabase JWT), logging, errors, seed reader,
                          llm/ (F8 gateway), security/ (rate limit, PII, sanitiser), fairness
    app/contracts/        shared Pydantic contracts, one file per feature
    app/features/<f>/     router, service, repository, schemas, mocks, FEATURE.md
    openapi.json          generated contract (make contracts)
  web/                    Next.js App Router, TypeScript strict, Tailwind, shadcn/ui, next-intl
    messages/<locale>/    en, ms, zh; one JSON per feature namespace
    src/app/              routes only (thin pages)
    src/features/<f>/     feature UI: components/, hooks/, api.ts, index.ts
    src/components/       shared UI (ScenarioToggle, SourceBadge, EstimateLabel, ...)
    src/lib/api/          typed API client + generated types.ts
  pipelines/<f>/          offline data / ML jobs (trends, matching, sdg, pathway)
  db/                     migrations/ (timestamped SQL), migrate.py, seed.py
  data/seed/<f>/          tiny synthetic samples; data/raw/ is gitignored
  scripts/dev.py          cross-platform task runner behind the Makefile
tests/
  api/<feature>/          API tests, one folder per feature
  pipelines/<feature>/    pipeline tests
submission/               proposal, pitch deck, demo video link
requirements.txt          Python dependencies
pyproject.toml            ruff + pytest settings only
```

See [docs/architecture.md](docs/architecture.md) for the system flow and
[docs/SOLUTION_DESIGN.md](docs/SOLUTION_DESIGN.md) for the problem, the solution and how each of
the four target users moves through the app.

## Features and owners

| Feature | Owner | Code |
|---|---|---|
| F1 Skills profile intake | M2 | `profile` |
| F2 AI-trend signal layer | M1 | `trends`, `src/pipelines/trends` |
| F3 Scenarios & uncertainty | M1 | `scenarios` |
| F4 Future-role matching | M2 | `matching`, `src/pipelines/matching` |
| F5 Reskilling pathway | M3 | `pathway`, `src/pipelines/pathway` |
| F6 SDG mapping | M3 | `sdg`, `src/pipelines/sdg` |
| F7 Organisation mode | M4 | `org` |
| F8 Guardrails & transparency | M3 | `guardrails`, `src/api/app/core/{llm,security,fairness.py}` |
| Core | M4 | shells, shared UI, auth, `src/web/src/features/core` |

## Team docs

- [docs/TEAM_RULES.md](docs/TEAM_RULES.md): how we work without merge conflicts
- [docs/TASKS.md](docs/TASKS.md): tasks per feature
- [docs/decisions.md](docs/decisions.md): decisions and change log (an entry for every change)

## Licence

Apache License 2.0, see [LICENSE](LICENSE).
