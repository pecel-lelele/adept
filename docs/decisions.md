# Decisions & Change Log

**Rule: every time a member changes something (a choice of model, method, data source, formula, contract, dependency, schema, or any meaningful feature change), they add an entry here in the same PR.**

## How to avoid merge conflicts in this file

- Each member writes **only inside their own section** below (M1, M2, M3, M4).
- **Add new entries at the bottom of your own section** (just above the next section's `---`). Never edit or reorder another member's entries.
- Never edit an old entry. If a decision changes, add a new entry that says `Replaces: <old entry ID>`.
- Entry ID format: `<member>-<NNN>`, numbered within your own section (M1-001, M1-002, ...).
- Team-wide decisions (stack, contracts, shared files) go in the **Team** section, added only via a dedicated PR announced in chat.

## Entry template (copy this)

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

## Team

### TEAM-001: Core stack and two-mode product
- **Date**: 2026-10-19
- **Feature**: all
- **Type**: other
- **Change**: Adopted the locked core stack and the Individual | Organisation two-mode design in `docs/ai/PROJECT_CONTEXT.md` §11.
- **Why**: Four target users share two usage patterns; one shared engine keeps the build small.
- **Affects**: everyone
- **Replaces**: none
- **PR / branch**: initial commit

### TEAM-002: Initial skeleton
- **Date**: 2026-10-20
- **Feature**: all
- **Type**: other
- **Change**: Runnable skeleton in the committee root layout (`docs/`, `src/`, `submission/`, `tests/`, root `requirements.txt`, `pyproject.toml` for ruff + pytest settings only, `Makefile`, `docker-compose.yml`). `src/api`: FastAPI + Pydantic v2 contracts (`app/contracts/`, one file per feature, `RecommendationMeta` on every recommendation/score/trend), 7 feature packages (router → service → repository → mocks, plus `schemas.py`, `FEATURE.md`, `CLAUDE.md`, `GEMINI.md`), all endpoints from the spec returning synthetic mock data with source `MOCK DATA` / 2026-10-20, `AUTH_MODE=demo` via `X-Demo-User`, and an F8 LLM gateway stub (`app/core/llm`: provider protocol, `NullProvider`, structured output, `validate_ids`, logging). `src/web`: Next.js 16 App Router, strict TS, Tailwind 4, hand-added shadcn/ui primitives (Card, Badge, Button), next-intl (en/ms/zh, one JSON per feature namespace, cookie locale, keys type-checked against `en`), every route in PROJECT_CONTEXT §11.3 as a thin page rendering a feature component with a STUB banner, global `?scenario=` toggle in the `/app` and `/org` shells, landing switch with data-freshness badge, `/demo/learner` and `/demo/org` cookie sign-in, typed client with `openapi-fetch` over generated `types.ts`. `src/db`: one migration `20261019120000_core_init.sql` (pgvector + the 14 tables) and a small runner; generic CSV seed loader over `src/data/seed/<area>/<table>.csv`. `src/pipelines/{trends,matching,sdg}` placeholders. Tests in `tests/api/<feature>/` (one per endpoint, validated against the contract, plus core, auto-discovery and LLM validator tests) and `tests/pipelines/<feature>/`.
- **Why**: Lets four people build features in parallel against stable contracts and mock data from day one.
- **Anti-conflict mechanisms**: router auto-discovery (nobody edits `main.py`); per-feature folders for API, web, contracts, translations, seeds, pipelines and tests; thin page files; shared UI only in `src/web/src/components`, navigation in `src/web/src/config/navigation.ts`; generic seed loader (no code change to add seed data); new-file-only migrations; contract drift check and translation-key parity check in `make check`.
- **Tooling choices**: `make` targets delegate to stdlib-only `src/scripts/dev.py` so Windows users without make can run `uv run --no-project python src/scripts/dev.py <target>`. Python deps installed with `uv pip install -r requirements.txt` into a root `.venv` (no `uv.lock`). `src/web` is a standalone pnpm project (`packageManager: pnpm@10.29.3`, run through `npx` if pnpm is missing). Added deps: `openapi-typescript` + `openapi-fetch` (typed client), `class-variance-authority`/`clsx`/`tailwind-merge` (shadcn/ui), `psycopg` (db + runner), `python-multipart` (CV upload). next-intl pinned to 4.4.0 because 4.5+ pulls in `@swc/core`, whose native binary failed to load on Windows here.
- **Deviations from PROJECT_CONTEXT §11.6**: migrations use a ~60-line runner (`src/db/migrate.py`) instead of the dbmate binary, but the files use dbmate's `-- migrate:up` / `-- migrate:down` format and the same `schema_migrations` table, so switching to dbmate later needs no re-run. Docker maps Postgres to host port **5433** (5432 was already in use on the dev machine; override with `POSTGRES_PORT`).
- **Unfinished / for owners**: no real ingestion, matching, pathway logic or LLM calls (all mocks); `AUTH_MODE=supabase` raises 501; repositories read mocks, not the database yet; courses are example.org placeholders (F5 must verify a real catalogue); SDG reasons are mock text pending review (F6); only 5 SDG targets seeded (F6 loads all 17 goals); ms/zh translations are first drafts to be reviewed by native speakers; web has no unit tests yet (only tsc + eslint); `.env.example` documents all variables.
- **Affects**: everyone
- **Replaces**: none
- **PR / branch**: `chore/skeleton`

---

## M1: Trends & Scenarios (F2, F3)

<!-- M1 adds entries below this line -->

---

## M2: Profile Intake & Matching (F1, F4)

<!-- M2 adds entries below this line -->

---

## M3: Pathway, SDG & Guardrails (F5, F6, F8)

<!-- M3 adds entries below this line -->

---

## M4: Core & Organisation (Core, F7)

<!-- M4 adds entries below this line -->
