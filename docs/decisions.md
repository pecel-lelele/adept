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
- **Change**: Adopted the locked core stack and the Individual | Organisation two-mode design in `docs/PROJECT_CONTEXT.md` §11.
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
- **Project context path**: `PROJECT_CONTEXT.md` stays at `docs/PROJECT_CONTEXT.md` (no `docs/ai/` folder); the imports in `CLAUDE.md`/`GEMINI.md` and the references in `TEAM_RULES.md` and TEAM-001 were updated to match (path-only fix, agreed with the team lead).
- **Unfinished / for owners**: no real ingestion, matching, pathway logic or LLM calls (all mocks); `AUTH_MODE=supabase` raises 501; repositories read mocks, not the database yet; courses are example.org placeholders (F5 must verify a real catalogue); SDG reasons are mock text pending review (F6); only 5 SDG targets seeded (F6 loads all 17 goals); ms/zh translations are first drafts to be reviewed by native speakers; web has no unit tests yet (only tsc + eslint); `.env.example` documents all variables.
- **Affects**: everyone
- **Replaces**: none
- **PR / branch**: `chore/skeleton`

### TEAM-003: Universal AGENTS.md operating standard
- **Date**: 2026-10-20
- **Feature**: Core / all
- **Type**: other
- **Change**: Added root `AGENTS.md` as the unified master operating standard and instruction manual for all AI coding agents and IDE tools (Cursor, Copilot, Windsurf, Qoder, Roo Code, Aider, Devin).
- **Why**: Non-Claude/Gemini agents do not expand `@docs/...` file include macros and require a self-contained, authoritative specification of guardrails, architecture, contracts, and team conventions.
- **Affects**: everyone
- **Replaces**: none
- **PR / branch**: `main`

---

## M1: Trends & Scenarios (F2, F3)

<!-- M1 adds entries below this line -->

### M1-001: Trend signal layer, disruption scenarios, and snapshot contract
- **Date**: 2026-10-20
- **Feature**: F2 (AI-trend signal layer), F3 (Scenarios & uncertainty)
- **Type**: contract, formula, pipeline, data source, schema
- **Change**: Implemented the patched TrendSnapshotResponse contract in `src/api/app/contracts/trends.py`, canonical taxonomy (110 skills across 3 categories), BLS 2023-2033 labor decay baseline with explicit citations, sentence-chunked arXiv semantic matching with `all-MiniLM-L6-v2` (threshold >= 0.55), deterministic composite scoring formula with scenario fast-amplification transform and clamping [-2.0, 2.0], mock fixture `mock_trends.json`, database migration for pgvector embeddings and signal tables, and GET `/api/v1/trends/snapshot`.
- **Why**: F2 continuously tracks emerging vs declining skill velocity without ML fine-tuning or live GPU dependency. F3 provides deterministic scenario modeling (moderate vs fast) using curated editorial automation exposure coefficients documented in `docs/skill-exposure-methodology.md`. All outputs trace to measured frequencies, BLS data, or disclosed coefficients with zero invented entities.
- **Pipeline** (data/ML only): arXiv cs.AI RSS + BLS 2023-2033 projections → clean HTML, normalize, sentence-chunk → 384-d MiniLM embeddings (CPU zero-shot) → max sentence cosine similarity (>= 0.55), log-ratio research velocity, composite velocity V = 0.6*RV + 0.4*LD, fast scenario transform with exposure amplification and [-2.0, 2.0] clamping → PostgreSQL `trend_snapshots` + cached JSON serving at GET `/api/v1/trends/snapshot`.
- **Affects**: M2 (taxonomy skill IDs and snapshot format), M4 (scenario toggle & radar frontend consumption)
- **Replaces**: none
- **PR / branch**: `feat/m1-trends-contract`

### M1-002: Scenario-invariance fix, live dual-snapshot pipeline, and M2 dependency contract
- **Date**: 2026-10-20
- **Feature**: F2 (AI-trend signal layer), F3 (Disruption scenarios)
- **Type**: formula | method | data source | contract
- **Change**: 
  1. Fixed scenario-invariance bug in `mocks.py` and `repository.py`: `velocity_moderate` and `velocity_fast` are fixed properties per skill and are now strictly invariant across scenario queries.
  2. Verified M2 taxonomy status: Current seed taxonomy in `src/data/seed/taxonomy/skills.csv` has 12 skills (all 12 are exact matches with M1 canonical skills); M2's expanded target taxonomy (ESCO/O*NET/hybrid) is not yet implemented in the codebase. Canonical 110-skill taxonomy is preserved with compatible IDs.
  3. Live pipeline operational with PostgreSQL pgvector: 110 skill embeddings populated in `skill_embeddings` via `all-MiniLM-L6-v2`; 789 real papers fetched and cached from arXiv cs.AI RSS. Generated two distinct dated snapshots in `trend_snapshots`: `2026-10-13` (baseline window 2026-W42) and `2026-10-20` (growth window 2026-W43). 38 skills exhibit velocity shifts and 27 skills show direction flips (e.g., `ai-agents` flips from `stable` to `rising`).
  4. M2 matching dependency contract: Verified `src/api/app/features/matching/` does not yet consume trends. M2 needs to call `app.features.trends.service.get_snapshot(snapshot_date, scenario)` (or `GET /api/v1/trends/snapshot?snapshot_date=<date>&scenario=<scenario>`) and incorporate skill velocities into `trend_outlook` score components.
- **Why**: Ensures trend-replay (C1) and disruption scenarios work deterministically against real data while keeping clear cross-team boundaries.
- **Affects**: M2 (matching dynamic trend scoring), M4 (scenario toggle & trend replay UI)
- **Replaces**: none
### M1-003: Five defect fixes (BLS quoting, weekly aggregation, arXiv date windows, fallback 404s, mock fixture consistency)
- **Date**: 2026-10-20
- **Feature**: F2 (AI-trend signal layer), F3 (Disruption scenarios)
- **Type**: model | method | data source | formula | contract | schema
- **Change**: 
  1. Part 1 (CSV Quoting): Corrected unquoted embedded commas in BLS occupation titles within `src/data/seed/bls_projections_2023_2033.csv` using Python's `csv.writer(quoting=csv.QUOTE_MINIMAL)`. Regenerated `labor_decay.csv` from scratch: verified `bookkeeping` shifted from corrupted -1.83 to -0.0134 (-1.3%/yr) and `scheduling-admin` from 16.12 to -0.0071 (-0.7%/yr); all 110 skills verified within sanity bounds `[-0.5, 0.5]`. Added `tests/pipelines/trends/test_labor_baseline.py`.
  2. Part 2 (Weekly Signal Aggregation): Added database migration `20261021140000_m1_signal_aggregation_by_fetch_date.sql` adding `total_papers` column to `skill_signal_raw` with unique constraint `(skill_id, source, metric, period, retrieved_at)`. Redesigned `score.py` (`aggregate_period_runs`) to sum BOTH `value` (mention count) and `total_papers` across all fetch runs for each period bucket (preserving frequency e.g. 10/100 + 10/100 -> 20/200). Added unit test in `tests/pipelines/trends/test_score.py`.
  3. Part 3 (Historical Snapshots & Provenance): Replaced arbitrary single-feed splitting with genuine date-bounded historical window queries via the arXiv Query API (`http://export.arxiv.org/api/query`, query: `cat:cs.AI AND submittedDate:[YYYYMMDDHHMM TO YYYYMMDDHHMM]`). Pulled and cached two real non-overlapping submission windows (2024-10-06..2024-10-12 and 2024-10-13..2024-10-19, 350 papers each) under `src/data/seed/arxiv_raw/<start>_<end>.json` calibrated to 2026-W42 and 2026-W43. Added optional `data_provenance_note: str | None` field to `TrendSnapshotMeta`.
  4. Part 4 (Fallback Date-Awareness & 404s): Restructured fallback mode to serve distinct per-date fixtures (`mock_trends_2026-10-13.json` and `mock_trends_2026-10-20.json`). In both DB and fallback modes, requesting an unavailable `snapshot_date` returns HTTP 404 with `NotFoundError`. Updated `test_multiple_available_snapshots_and_dates_differ` and added `test_requesting_unavailable_date_returns_404`.
  5. Part 5 (Mock Fixture Consistency): Built `src/pipelines/trends/generate_mock_fixtures.py` to derive `velocity_fast`, `direction_moderate`, and `direction_fast` directly from `score.py` functions (`scenario_fast`, `direction`), completely eliminating hand-authored derived values. Fixed `trade-confirmation` direction ("declining", not "stable") and `audit-internal` fast velocity (0.10625, not 0.13). Added `tests/pipelines/trends/test_mock_fixture_consistency.py`.
- **Why**: Resolves Greptile automated review flags and CI failures, guarantees data integrity against official BLS sources, prevents artificial frequency drops on repeated ingestion, complies with SDG ethical constraints against invented statistics, and ensures robust fallback in database-free CI.
- **Pipeline** (data/ML only): BLS CSV (properly quoted) -> `labor_baseline.py` -> `labor_decay.csv` -> arXiv Query API (two dated windows) -> sentence-chunked MiniLM embedding -> mention aggregation -> `score.py` -> `generate_mock_fixtures.py` -> dated JSON fixtures + Postgres `trend_snapshots`.
- **Affects**: M2 (matching trend consumption), M4 (scenario toggle & trend replay frontend)
- **Replaces**: none
- **PR / branch**: `feat/m1-trends-contract`

### M1-004: False-negative TTL recovery, authoritative source resolution, and genuine DB fixture export
- **Date**: 2026-10-20
- **Feature**: F2 (AI-trend signal layer), F3 (Disruption scenarios)
- **Type**: method | contract | data source | schema
- **Change**: 
  1. Part 1 (Short-TTL Negative Cache): Replaced permanent `lru_cache` in `_db_available()` with a dual-policy cache: successful checks are cached indefinitely; failed checks are cached with a 5.0-second TTL using `time.monotonic()`. Allows transient container startup race conditions to recover automatically without process restarts, proven by `test_db_availability_recovers_after_short_ttl`.
  2. Part 2 (Authoritative Source Resolution): Implemented `resolve_source() -> Literal["db", "fixture"]` in `repository.py`, called once per request in `service.py`. Treats reachable-but-empty database (`trend_snapshots` count == 0) identically to unreachable DB, resolving to "fixture". Threaded `source` through `list_available_dates()` and `get_snapshot()` so they never disagree, eliminating 404s on advertised dates.
  3. Part 3 (Genuine DB Fixture Export): Implemented `src/pipelines/trends/export_fixtures_from_db.py` to export the 110 genuine scored rows from PostgreSQL `trend_snapshots` directly into `mock_trends_2026-10-13.json`, `mock_trends_2026-10-20.json`, and `mock_trends.json`. Retired `BASE_ITEMS` generation path in `generate_mock_fixtures.py` by repointing it to `export_fixtures_from_db.py`. Formulated accurate `data_provenance_note` disclosing that files are frozen offline exports of the real arXiv Query API pipeline runs.
  4. Consistency Tests: Updated `test_mock_fixture_consistency.py` to assert verbatim field-level matches against PostgreSQL `trend_snapshots` rows, alongside pure formula consistency. Added `tests/api/trends/test_source_resolution.py`.
- **Why**: Eliminates permanent fallback lock-in on initial DB failure, guarantees consistent contract behavior on newly migrated empty databases, removes all synthetic base items from demo fixtures, and ensures full transparency under SDG 4 ethics.
- **Affects**: M2 (matching trend dependency), M4 (scenario toggle & radar frontend)
- **Replaces**: none
- **PR / branch**: `feat/m1-trends-contract`

### M1-005: Line-ending normalization (.gitattributes), OpenAPI parity, and single-connection request resolution
- **Date**: 2026-10-20
- **Feature**: F2 (AI-trend signal layer), F3 (Disruption scenarios)
- **Type**: contract | method | other
- **Change**:
  1. Part 0 (Contract Drift Root Cause & Fix): Root-caused CI contract drift to two sources: (a) FastAPI version divergence where CI resolved FastAPI 0.151.0 (via `fastapi>=0.115,<1` in `requirements.txt`) which formats UploadFile schemas using `"contentMediaType": "application/octet-stream"` instead of older `"format": "binary"`; and (b) missing `.gitattributes` allowing Windows CRLF conversion under `core.autocrlf=true`. Upgraded local virtualenv dependencies, created root `.gitattributes` enforcing deterministic LF line endings for text files and generated contracts (`src/api/openapi.json`, `src/web/src/lib/api/types.ts`), and renormalized the git tree. Confirmed 100% byte-for-byte identical output between Windows and Linux Docker container `python:3.11-slim`.
  2. Part 1 (Greptile P2 - Single Connection & Dates Query): Refactored `repository.py` and `service.py` to resolve authoritative source ("db" vs "fixture") and available dates simultaneously in a single database round-trip via `ResolvedContext`. Reuses the open connection and pre-resolved date list across `get_snapshot()` and `_load_snapshot_db()`, eliminating redundant `SELECT DISTINCT snapshot_date` queries. Added unit test `test_snapshot_request_opens_single_connection_and_single_dates_query` verifying exactly 1 database connection and 1 dates query per live request.
- **Why**: Eliminates recurring CI contract drift failures across operating systems and resolves Greptile P2 performance finding by removing redundant round-trips.
- **Affects**: none (M1 internal optimization and contract parity)
- **Replaces**: none
- **PR / branch**: `feat/m1-trends-contract`

---

## M2: Profile Intake & Matching (F1, F4)

<!-- M2 adds entries below this line -->

### M2-001: Explainable matching engine, snapshot replay, fairness guards, and offline evaluation benchmark
- **Date**: 2026-10-20
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: model | method | formula | contract | data source
- **Change**:
  1. Implemented explainable scoring in `src/api/app/features/matching/scoring.py` with pure functions (`skill_overlap`, `trend_scores`, `role_trend`, `interest_fit`, `skills_gap`, `rank_roles`) using default weights (0.5 skill, 0.3 trend, 0.2 interest) and percentile-rank normalization for velocities to resist outlier suppression.
  2. Implemented `replay.py` for evaluating role movement across dated snapshots (`RoleMovement` delta_rank and delta_score).
  3. Implemented `trend_port.py` thin adapter to extract velocities from M1's `TrendSnapshotResponse`.
  4. Added fairness whitelist (`MatchProfile` restricted to skills and interests; no protected demographic attributes) and counterfactual invariance tests (`test_counterfactual_fairness_demographic_swaps`) proving identical rankings under identity swaps (M2-12, M2-13).
  5. Implemented evaluation metrics in `evaluation.py` (Precision@k, Recall@k, Reciprocal Rank, nDCG@k) and benchmark harness `tests/api/matching/test_evaluation.py` against hand-labelled ground truth `src/data/seed/personas/expected_roles.csv` for synthetic personas (Aisyah, Wei Jie, Ravi), achieving 100% MRR and >= 0.90 nDCG@3.
- **Why**: F4 requires explainable, human-in-the-loop role matching with clear skill gap attribution, zero hallucinated jobs/skills, strict non-discrimination (SDG 10.2 & Federal Constitution Art. 8), and quantitative validation on synthetic personas.
- **Pipeline** (data/ML only): taxonomy roles/skills + user profile + trend snapshot velocities -> skill overlap + rank-based trend score + interest Jaccard fit -> composite score -> tie-broken rank ordering -> gap bucketing (have/partial/missing) -> evaluation harness (MRR=1.0, P@3>=0.85, nDCG@3>=0.90).
- **Affects**: M1 (trend snapshot consumption), M3 (pathway gap intake), M4 (match UI and HR heatmap)
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-002: F1 Profile intake pipeline (CV parsing, questionnaire intake, and skill confirmation normalisation)
- **Date**: 2026-10-20
- **Feature**: F1 (Skills Profile Intake)
- **Type**: model | method | formula | contract | data source
- **Change**:
  1. Implemented rule-based CV parsing pipeline in `src/api/app/features/profile/cv_parser.py` (M2-01) supporting PDF and raw text, text cleaning (URL/email stripping), regex alias index matching against official taxonomy `src/data/seed/taxonomy/skills.csv`, context-based proficiency level estimation (1–5 scale), and confidence scoring.
  2. Implemented questionnaire intake in `src/api/app/features/profile/schemas.py` and `router.py` (M2-02) at `POST /api/v1/profile/questionnaire` capturing segment, target roles, weekly commitment, learning preferences, and HRD eligibility.
  3. Implemented skill confirmation endpoint in `src/api/app/features/profile/service.py` and `router.py` (M2-03) at `PUT /api/v1/profile/skills/confirm`, validating taxonomy IDs, rejecting duplicates, persisting confirmed skills, and returning normalised proficiency values on `[0.0, 1.0]` using `(level - 1) / 4.0` for downstream F4 matching engine compatibility.
- **Why**: Standardises profile intake across diverse entry points (CV upload and questionnaire), eliminates hallucinated skill entities by strictly grounding in taxonomy seed data, and aligns integer user skill levels (1-5) with the downstream matching engine's unit float scale [0.0, 1.0].
- **Pipeline** (data/ML only): PDF/text resume -> clean_text() -> alias/regex scanner against taxonomy skills -> context level estimation (1-5) -> human-in-the-loop review/confirmation -> (level - 1) / 4.0 normalisation -> persistent user profile.
- **Affects**: M2 (matching engine input), M4 (profile onboarding frontend)
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

---

## M3: Pathway, SDG & Guardrails (F5, F6, F8)

<!-- M3 adds entries below this line -->

### M3-001: Problem framing and solution design
- **Date**: 2026-10-20
- **Feature**: F5, F6, F8 (and the whole journey)
- **Type**: other
- **Change**: Added `docs/SOLUTION_DESIGN.md`: the "skills-signal gap" problem, the skills-signal engine, how each of the four target users moves through the routes, M3 feature design, KerjaCerdas reuse map, routing summary and M3 risks with fallbacks.
- **Why**: The proposal needs one problem → approach → outcome narrative a cold listener can repeat; the four users needed concrete journeys, not just a list.
- **Affects**: everyone (reference doc; no shared file edited)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-002: Fixes for the six skeleton review findings (cross-feature, requested by M3)
- **Date**: 2026-10-20
- **Feature**: Core, F1, F4, F7 (fixes requested in review; owners please re-review)
- **Type**: other
- **Change**: (1) `docker-compose.yml` publishes Postgres on `${POSTGRES_BIND:-127.0.0.1}` (new `POSTGRES_BIND` in `.env.example`). (2) `POST /profile/cv` reads in 64 KB chunks and returns 413 `payload_too_large` above `MAX_UPLOAD_BYTES` (5 MB). (3) Every match now has a pathway: F5 builds plans for any taxonomy role instead of two mock plans (test `test_every_suggested_match_has_a_pathway`). (4) `JourneyStepper` preserves `?role=` as well as `?scenario=`. (5) `/org/plan` takes `scenario` (and optional `role_id`) through page → client → endpoint → pathway. (6) `make dev` raises `TaskError` with the exit code of the first server that exits (`supervise()` in `src/scripts/dev.py`).
- **Why**: P1/P2 review findings on the skeleton PR.
- **Affects**: M4 (compose, dev.py, stepper, org plan), M2 (CV upload, matches link)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-003: API security layer reused from KerjaCerdas
- **Date**: 2026-10-20
- **Feature**: F8 (shared core)
- **Type**: method | dependency
- **Change**: `app/core/security/`: per (IP, route bucket) sliding-window rate limiter (LRU-capped, never evicts a throttled key, `X-Real-IP` trusted only with `PROXY_SHARED_SECRET`), Content-Length body limits (1 MB JSON, upload cap + slack), security headers (CSP `default-src 'none'` except `/docs`), prompt-injection sanitiser, filename sanitiser, regex PII redaction adapted to Malaysia (MyKad NRIC, passport, +60/0 phones; specific phone patterns so date ranges like 2019-2024 survive). Installed once from `create_app` before CORS. The web server forwards the client IP with the secret (`src/web/src/lib/api/server.ts`). `AUTH_MODE=supabase` now verifies Supabase HS256 JWTs (`aud=authenticated`, `exp`/`sub` required), fails closed (503) without `SUPABASE_JWT_SECRET`, and takes privilege only from `app_metadata`. New dependency: `pyjwt>=2.8,<3`. New env vars documented in `.env.example`.
- **Why**: The demo API needs no credentials, so abuse limits matter; KerjaCerdas already solved these with tests and a threat model. Simplified the limiter (no per-key locks: the critical section has no `await`).
- **Affects**: everyone (middleware on every route; `main.py`, `auth.py`, `config.py`, `requirements.txt` touched)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-004: LLM gateway hardening; no model enabled
- **Date**: 2026-10-20
- **Feature**: F8
- **Type**: model | method
- **Change**: Prompts are injection-filtered and PII-redacted before sending; circuit breaker (3 failures → 30 s open); bounded call log with provider, model, outcome and rejected IDs (`llm_calls` table for the DB move); `select_ids_or_fallback` returns deterministic results when the model is unavailable or invents an ID. Provider stays `none`; `disclosure()` reads provider/model from settings for `/about` and README.
- **Why**: Catalogue-only rule needs defence in depth; the deterministic engine already meets every must-have, so no model is required for the demo.
- **Affects**: any feature that adds LLM calls
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-005: Fairness guards
- **Date**: 2026-10-20
- **Feature**: F8 (used by F4, F5, F7)
- **Type**: method
- **Change**: `app/core/fairness.py` with protected-attribute detection (age, sex/gender, race/ethnicity, religion, nationality, marital status, disability, names, …; grounds from Federal Constitution Art. 8 and SDG 10.2) and `counterfactual_diffs`. CI tests fail if any API input or DB column carries a protected attribute; pathway tests give three personas identical inputs via the API and require identical plans. `/guardrails/fairness` runs the checks live.
- **Why**: Handbook good-to-have; also makes the "human-centred, non-discriminatory" claim checkable.
- **Affects**: M2 (matching should add its own counterfactual tests with the same helper)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-006: SDG data source and mapping method
- **Date**: 2026-10-20
- **Feature**: F6
- **Type**: data source | method | contract
- **Change**: All 17 goals and 169 targets from the UN Statistics Division SDG API via `src/pipelines/sdg`. Every taxonomy role (7) and skill (12) links to official targets with a one-line reason and a `strength` (direct / enabling); 32 links across goals 4, 5, 8, 9, 10 and 16. Contribution views for person, organisation and region (synthetic `org_regions`); plan-level links computed from plan facts (4.4 when skills are built, 4.3 when out-of-pocket cost is RM 0). `GET /sdg/roles/{id}/alignment?goals=` scores roles (direct 1.0, enabling 0.5, ÷ 2, cap 1) for F4's SDG-weighted ranking. Contract additions: `SdgLink.strength/via/reviewed`, `GoalSummary.direct_count/enabling_count/is_focus/contributors`, `SdgContribution.scope/scope_id/role_ids`, new `SdgGoal`, `SdgGoalListResponse`, `SdgAlignment`, `RegionListResponse`.
- **Why**: Official source avoids typing targets from memory; strength + reason + computed plan links keep the mapping meaningful rather than decorative. Considered 17.18 for data roles and rejected it (it is about national statistical capacity).
- **Pipeline**: UN SDG API → keep codes/titles, validate 1..17 → curated role/skill links + plan facts → union per scope, strength-weighted alignment → tests (all mapped, targets exist, reasons name their target) and CI SQL check → `/sdg/*`, `/app/sdg`, `/org/sdg`.
- **Open**: `reviewed_by`/`reviewed_at` are empty; the UI shows "draft, pending review" until a human reviewer signs the mappings off. M2 can call `alignment` for the SDG slider.
- **Affects**: M2 (alignment for ranking), M4 (org SDG page now has organisation/region tabs)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-007: Course catalogue sources
- **Date**: 2026-10-20
- **Feature**: F5
- **Type**: data source
- **Change**: `src/pipelines/pathway` builds `courses.csv` from the Microsoft Learn Catalog API (16 curated free modules/paths for ai-literacy, prompt-engineering, python, sql, data-visualisation, process-mapping, rpa, risk-compliance; title, URL and duration from the API) plus one HRD Corp-claimable course checked on the provider's page on 2026-10-20 (AITraining2U "AI Data Analytics", RM 3,500 HRDC-claimable fee before SST; 14 h assumes 7 h/day for the stated 2 days). Each row carries `level` (Adept's estimate of the level reached), `source_name/url`, `hrd_note`, `duration_note`, `verified_at`. Weekly workflow re-fetches and warns on drift or retired courses.
- **Why**: A public API keeps hours and URLs current; HRD Corp claimability is only claimed where the provider states it. Kaggle Learn was considered but its pages could not be verified (client-rendered). No catalogue course yet for Excel, customer service or logistics planning; those gaps show as unmet rather than invented.
- **Affects**: none
- **Replaces**: the example.org placeholder courses
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-008: Pathway engine (ordering, selection, time estimate)
- **Date**: 2026-10-20
- **Feature**: F5
- **Type**: method | formula | contract
- **Change**: Pure engine (`features/pathway/engine.py`): gap from role requirements vs profile levels; priority = importance × gap share × (1 + clip(growth, −0.5, 1) × w), w = 1 moderate / 2 fast; Kahn topological sort over `skill_prerequisites` where a prerequisite inherits the highest priority of what it unlocks; per skill, ascending-level catalogue courses, cheapest out-of-pocket (HRD Corp-claimable = RM 0 when eligible) then fewest hours, within remaining budget; a multi-skill course is booked once; weeks from cumulative hours ÷ profile hours/week (5 h assumed with a warning if 0). Unmet skills are reported (`no_catalogue_course`, `over_budget`, `catalogue_tops_out`). Contract additions on `Course`, `PathwayStep`, `Pathway` (all defaulted) plus `SkillGap`, `UnmetSkill`, `CatalogueResponse`.
- **Why**: Deterministic and explainable (each step states its priority formula); respects time, budget and HRD Corp funding; scenario and trend data change the order.
- **Pipeline**: catalogue + taxonomy + prerequisites + latest trend snapshot → gap → priority → order → select → schedule → 38 tests (catalogue-only, budget, HRD, prerequisites, every match has a pathway, counterfactual fairness) → `GET /pathway`.
- **Affects**: M4 (org plan uses `group_pathway`), M1 (reads `trends/*.csv` read-only)
- **Replaces**: mock pathway plans
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-009: Saved plans, automatic re-planning, progress and badges
- **Date**: 2026-10-20
- **Feature**: F5
- **Type**: method | schema | contract
- **Change**: `POST /pathway/plans` saves the learner's chosen role (human decision) with the trend snapshot version. `GET /pathway/plans/me` rebuilds the plan on the latest snapshot and, if it is newer and the plan changed, proposes it with a diff (added / removed / reordered / courses changed) and a dated message; `POST …/accept-replan` adopts it. `GET|POST /pathway/progress` records course status (only courses in the plan), raises skill levels to each completed course's level, and awards skill and milestone badges labelled *self-reported* (KerjaCerdas proof-level idea). In-memory store for the demo; migration `20261020120000_m3_pathway_sdg_guardrails.sql` adds `pathway_plans`, `course_progress`, `user_badges`, `skill_prerequisites`, `sdg_goals`, `org_regions`, `llm_calls` and additive columns (tested: up, down, up, seed).
- **Why**: Handbook "re-planning when trend data changes" without silently replacing a plan the learner chose.
- **Affects**: M1 (a new snapshot row in `trends/` triggers the re-plan notice), everyone (new migration)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-010: Organisation heatmap and group plan from real member skills (F7 wiring)
- **Date**: 2026-10-20
- **Feature**: F7 (M4's feature; requested by M3, please review)
- **Type**: method
- **Change**: `/org/gaps` cells = share of completed-intake members below the role's required level (F5 `team_gaps`); `/org/plan` = F5 `group_pathway` (each skill starts from the weakest member who needs it, hours = team median, company plans may use HRD Corp) with `member_ids` per step; `member_plans` feeds the organisation/region SDG views. Synthetic `TEAM_SKILLS` added in `org/mocks.py` for members without a persona profile. The fake "fast scenario widens gaps" factor is removed: required levels do not change by scenario, so the heatmap does not either.
- **Why**: Good-to-have "workforce-level skills-gap heatmap and reskilling plan" from the same engine, without duplicated logic.
- **Affects**: M4
- **Replaces**: mock heatmap values
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-011: Source-on-every-recommendation sweep and guardrail endpoints
- **Date**: 2026-10-20
- **Feature**: F8
- **Type**: method | contract
- **Change**: `tests/api/guardrails/test_sources_everywhere.py` finds every GET endpoint whose response schema has `meta` and fails if a live response lacks dated sources (19 endpoints × 2 personas). New `GET /guardrails/disclosure`, `/guardrails/sources` (register with kind: live API, verified page, curated, synthetic, mock) and `/guardrails/fairness`, rendered on `/about`; README AI-disclosure section rewritten.
- **Why**: Makes the handbook rules regression-proof for every feature, including new ones.
- **Affects**: everyone (a new recommendation endpoint without sources fails CI)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-012: CI workflow
- **Date**: 2026-10-20
- **Feature**: all (root config)
- **Type**: other
- **Change**: `.github/workflows/ci.yml` (on PRs and pushes to main): `make check` via `src/scripts/dev.py check` (ruff, eslint, i18n parity, pytest, tsc, contract drift); `next build`; PostgreSQL 16 + pgvector service applying migrations and seeds twice (idempotency) plus SQL checks (17 goals, 169 targets, every role/skill mapped, every course has an https URL and source). `.github/workflows/data-sources.yml` runs weekly against the live UN and Microsoft Learn APIs and warns on drift. Structure adapted from KerjaCerdas CI.
- **Why**: `main` must always run; the migration job is the only place migrations meet a real pgvector database.
- **Affects**: everyone
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-013: M3 web pages and translations
- **Date**: 2026-10-20
- **Feature**: F5, F6, F8
- **Type**: UI
- **Change**: `/app/pathway` (summary with hours, weeks, out-of-pocket vs budget, HRD note; steps with levels, priority reason, prerequisites, courses with source and verified date, alternatives, SDG badges; unmet gaps; save plan; re-plan banner), `/app/progress` (mark courses done via server actions, skill levels, badges), `/app/sdg` and `/org/sdg` (17-goal grid, direct/enabling links, draft label, organisation and region tabs), `/about` (live disclosure, rules, sources, fairness). Stub banners removed on these pages. en/ms/zh messages added; ms and zh are drafts for native-speaker review.
- **Why**: Must-haves 4 and 5 and the transparency rules visible to users.
- **Affects**: M4 (org plan shows member names; heatmap stub banner removed)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-014: Fixes for the eight automated review findings on PR #2
- **Date**: 2026-10-20
- **Feature**: F5, F8 (+ Core web helper and CI that this PR added)
- **Type**: other
- **Change**: (1) Seed reads are cached per file version (path, mtime, size), so a new trend snapshot reaches saved plans without a restart. (2) When every rate-limit counter is throttled, newcomers get 429 instead of an active block being evicted. (3) Body size is counted as bytes arrive (pure ASGI middleware), so chunked uploads without Content-Length are stopped before multipart parsing. (4) The web server forwards only the client address appended by `TRUSTED_PROXY_HOPS` trusted proxies (default 0 = never). (5) Pathway and progress pages show the saved plan when its role and scenario match; progress returns the plan it is tracked against; profile changes are proposed as a re-plan, not applied. (6) A new migration deletes the skeleton's mock courses, mock links and shortened targets so `make seed` reloads the real rows; CI builds a DB from the skeleton commit and upgrades it. (7) Server actions report API errors (422, 429) next to the button instead of silently refreshing. (8) GitHub Actions pinned to commit SHAs.
- **Why**: Review findings (greptile) on PR #2.
- **Affects**: everyone using `make dev`/web server (TRUSTED_PROXY_HOPS), existing local databases (run `make db-migrate seed`)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-015: PostgreSQL storage for M3 (M3_BACKEND)
- **Date**: 2026-10-20
- **Feature**: F5, F6, F8
- **Type**: schema | method | dependency
- **Change**: `M3_BACKEND=csv|postgres` (`app/core/refdata.py`). With `postgres`: saved plans (whole Pathway as jsonb), per-role course progress and badges live in `pathway_plans`, `course_progress`, `user_badges` (`PostgresStore`, users row created for new authenticated users); catalogue and SDG reads come from the DB with a 30 s cache and a seed-file fallback if the DB is down; writes fail with 503 rather than being lost. Migration `20261021090000_m3_live_data_and_shared_state.sql`: evidence columns on the SDG maps, `provider_ref`/`last_synced_at`/`retired_at` on courses, `data_syncs` log, per-role progress key, UNLOGGED `rate_limit_counters`, skeleton data upgrade. Tested against pgvector/pg16 locally (upgrade from a skeleton-seeded DB, down/up round trip) and in CI. `DATABASE_URL` defaults now use 127.0.0.1 (the port is bound to IPv4 loopback; `localhost` cost 5 s per connection on Windows).
- **Why**: State must survive restarts and be shared by every instance on Replit (whose own PostgreSQL can be used by setting `DATABASE_URL` and `M3_BACKEND=postgres`).
- **Affects**: deployment config (set `M3_BACKEND=postgres` once the Replit database exists)
- **Replaces**: in-memory-only state from M3-009
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-016: Rate limits shared across API instances
- **Date**: 2026-10-20
- **Feature**: F8
- **Type**: method | dependency
- **Change**: With `M3_BACKEND=postgres` the limiter keeps one counter per (client, bucket, window) in `rate_limit_counters`, updated in one atomic upsert and read as a sliding window (`previous * (1 - elapsed/window) + current`); the call runs off the event loop through a small `psycopg-pool` pool (new dependency `psycopg-pool>=3.2`); if the DB fails it falls back to the in-memory limiter. Sync endpoints get a 5-per-hour bucket. Tested with two counters standing in for two instances.
- **Why**: Per-process counters let N instances allow N times the limit.
- **Affects**: everyone (requirements.txt)
- **Replaces**: per-process-only limits from M3-003
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-017: Live data sync and a deeper catalogue
- **Date**: 2026-10-20
- **Feature**: F5, F6, F8
- **Type**: data source | method
- **Change**: `python -m app.features.pathway.sync` / `POST /api/v1/pathway/catalogue/sync` and `python -m app.features.sdg.sync` / `POST /api/v1/sdg/sync` (header `X-Sync-Token` = `SYNC_TOKEN`, needs postgres) refresh reference data from live sources in one transaction, log every run in `data_syncs`, roll back on failure, and flag courses a provider no longer lists as `retired_at` (never recommended, progress kept). Catalogue now 31 courses: 20 Microsoft Learn items (API), 5 free-to-enrol Coursera courses (hours = module sums on the page; existence checked live through Coursera's catalog API) and 6 HRD Corp-claimable provider courses quoted from their own pages or brochures (AITraining2U x2, UNIMAS Excel Intermediate RM1,100 and Advanced RM1,300, FMM Supply Chain & Logistics RM1,350, MAICSA AML/CFT STR RM490); past run dates are stated, not hidden. UN SDG goals/targets now come from the light `Goal/List` + `Target/List` endpoints (~100 KB; the 11 MB tree failed mid-download). Source logic moved into `app/features/{pathway/catalogue_sources,sdg/sources}.py`, shared by pipelines and sync. Weekly workflow re-fetches, checks Coursera and checks that all 42 course and evidence links resolve (`pipelines.guardrails.check_links`).
- **Why**: Thin, static data was the main gap; the app now has real live connections and can be refreshed on a schedule (e.g. a Replit scheduled job running the two CLIs).
- **Pipeline**: Microsoft Learn API + Coursera API + provider pages / UN SDG API → validate (UIDs listed, skill IDs, https, HRD quote) → upsert + retire → `data_syncs` → API reads DB → `/guardrails/sources` shows last sync.
- **Open**: still no catalogue course for customer service; risk & compliance stops at level 2; HRD Corp course hours assume 7 h/day where only days are stated.
- **Affects**: none outside M3
- **Replaces**: M3-007
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-018: Evidence-backed SDG mappings
- **Date**: 2026-10-20
- **Feature**: F6
- **Type**: method | data source | contract
- **Change**: Every role and skill link now cites a published source with a note on what it says: UN SDG indicator metadata (4.4.1 ICT skill types incl. spreadsheets, coding, charts, information verification and online courses; 4.3.1; 8.2.1; 8.10.2; 9.1.2; 9.5.1; 10.5.1; 16.4.1; 16.5.2), ILO Working Paper 140 (2025) on generative-AI exposure ("clerical occupations continue to have the highest exposure levels"; "transformation of jobs is the most likely impact"), the UNESCO Recommendation on the Ethics of AI (2021) and UNESCO/EQUALS (2019) via the UNESCO GCED Clearinghouse record (unesdoc's certificate had expired). Links the evidence does not support were dropped (data analyst → 9.5, Python → 9.5, data visualisation → 8.2) or downgraded to enabling (AI ops → 9.5, compliance → 16.5, data analyst → 8.2). Plan-level links carry 4.4.1/4.3.1 evidence. 29 links in total. Contract: `SdgLink.evidence {source, note}`. Tests require an authoritative evidence URL on every link.
- **Why**: "Meaningful, not decorative" needs a justification a judge can open, not just a reason we wrote.
- **Open**: `reviewed_by` is still empty; a human reviewer should sign the mappings off.
- **Affects**: M2 (alignment scores changed for data-analyst and ai-operations-specialist)
- **Replaces**: M3-006 (mapping content)
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-019: Progress page gives feedback and tracks the saved plan
- **Date**: 2026-10-20
- **Feature**: F5
- **Type**: UI | method
- **Change**: "Mark done" / "Undo" now show "Saving…" then a confirmation or the API error (server actions return a state through `useActionState`). The course list comes from the plan the API tracks, so every button maps to a valid course. Undoing a course revokes badges it no longer supports (the first-earned date is kept if it is earned again).
- **Why**: Clicking did nothing visible; buttons for courses outside the saved plan failed silently; badges outlived the progress behind them.
- **Affects**: none outside M3
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-020: Paid, Malaysian and bundled courses; live exchange rate
- **Date**: 2026-10-20
- **Feature**: F5
- **Type**: data source | schema | contract
- **Change**: Courses gain `format` (self-paced, live online, in person, hybrid, subscription), `audience` (individual, corporate, both), `price_basis`, `currency`, `list_price`, `provider_type`, `location` and `price_note` (migration `20261021120000_m3_catalogue_formats_and_fx`, new `fx_rates` table). Added two paid HRD Corp-claimable courses quoted from the provider pages: UKM Professional Certificate in Data Analytics (RM3,000, online, 3 months) and FMM Power BI (RM1,080 non-member incl. 8% SST). Added the Coursera Plus annual subscription (USD 239) as a bundle; it shows in the catalogue but is never booked as a pathway step. USD prices are converted with Bank Negara Malaysia's live USD selling rate (`api.bnm.gov.my`, 4.088 on 2026-10-19) on every sync, with the rate and date in the price note. 34 courses in total.
- **Why**: The user asked for paid courses, Malaysian providers and corporate bundles; one hard-coded exchange rate would go stale.
- **Pipeline**: Microsoft Learn API + Coursera API + provider pages + BNM OpenAPI → validate (incl. FX note on converted prices) → upsert → `fx_rates` + `data_syncs` → API.
- **Open**: Coursera for Teams price is not shown publicly; Udemy and UiPath pages could not be read, so they are not listed.
- **Affects**: none outside M3 (new optional fields on `Course`)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-021: Course browse page for learners and HR
- **Date**: 2026-10-20
- **Feature**: F5
- **Type**: UI | contract
- **Change**: `GET /api/v1/pathway/catalogue` takes filters (skill, format, audience, provider type, HRD Corp-claimable, max cost in RM), sorted by cost then hours. New routes `/app/courses` and `/org/courses` (thin pages importing `CatalogueView`); the pathway and group plan link to them.
- **Why**: Learners and HR wanted to see what exists beyond the recommended steps, e.g. corporate HRD Corp-claimable programmes.
- **Affects**: M4 (two new routes the navigation can link to)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-022: Verified course completions
- **Date**: 2026-10-20
- **Feature**: F5, F7 (read-only use of org membership)
- **Type**: method | schema | contract | UI
- **Change**: Each completion has evidence on a ladder `self_reported` < `certificate_link` < `org_confirmed`; `org_rejected` removes the completion from progress. The learner can attach an https certificate link on `/app/progress`; the API checks whether it is an official verification page (Coursera accomplishments/verify, Microsoft Learn `/users/`, Credly badges) and whether it opens (HEAD then GET, 5 s). HR or a career advisor (`org_admin`) reviews members of their own organisation only at `/org/verify`, confirming or rejecting with a note the learner sees; for HRD Corp-claimable courses the hint points to the provider's attendance record in the HRD Corp claim. Badges show the weakest evidence behind them. New table `course_evidence` (migration `20261021130000_m3_completion_evidence`), endpoints `POST /pathway/progress/evidence` (20/min), `GET|POST /pathway/verifications`. Also fixed: saved-plan progress uses the course facts stored with the plan, so a course retired later keeps its credit (review P1).
- **Why**: A tick is only a claim; HR and career centres need a way to check it without the app pretending to certify anything.
- **Affects**: M4 (new route `/org/verify` for the org navigation); contracts `Badge.evidence`, `Progress.evidence`
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-023: Review fixes for sync, shared limiter and pipeline docs
- **Date**: 2026-10-20
- **Feature**: F5, F8
- **Type**: method
- **Change**: When Coursera cannot be reached, the sync refreshes a course's facts but keeps its retirement state, so a failed check never brings a removed course back. The shared limiter now prunes rows older than two of its longest windows (was a fixed hour, which forgot the previous hour of the hourly sync buckets). The pathway and SDG pipeline READMEs now use `PYTHONPATH=src/api:src`.
- **Why**: Greptile review on PR #2.
- **Affects**: none outside M3
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-024: Segment guidance on the pathway and a UX flows proposal
- **Date**: 2026-10-20
- **Feature**: F5 (proposal touches Core, F7)
- **Type**: UI | contract | other
- **Change**: `Pathway.segment` (added after the plan is built, so it cannot change it) drives a "next step" card: working adults are sent to HR first with an HRD Corp-claimable filter, graduates to free courses and certificate links, switchers to comparing roles. The fairness test now also checks the segment is echoed while plans stay identical. New `docs/UX_FLOWS.md`: per-audience flows and routes, dashboard contents for HR and career centres, the verification flow, comparable platforms (MyMahir, MYFutureJobs, HRD Corp, MySPIKE, MyTVET.my, Handshake, Gloat, Eightfold) and business-model options.
- **Why**: The user asked for clear, audience-specific flows; the shells and org navigation belong to M4, so those parts are written as proposals.
- **Affects**: M4 (navigation proposals in `docs/UX_FLOWS.md` §3.3 and §4.3: add Verify and Courses to the org rail, "My plan" shortcut), M2 (proposed per-segment panels on matches), M1 (proposed per-segment radar highlight)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

### M3-025: Second review round on verification and FX
- **Date**: 2026-10-20
- **Feature**: F5
- **Type**: contract | method
- **Change**: `ReviewDecision.submitted_at` (required, nullable) names the submission the reviewer saw; the review is saved in one conditional write (`UPDATE … WHERE submitted_at = seen`, or insert-if-absent), and a changed proof returns 409 `evidence_changed`. When Bank Negara Malaysia's rate cannot be fetched, the sync prices USD courses with the last rate in `fx_rates` instead of the seed rate. The link checker is looked up per call, so tests never reach live pages. The switcher card's "Compare roles" link keeps the current scenario.
- **Why**: Greptile review on PR #2: HR could confirm a certificate they never opened; an FX outage moved prices backwards; one test made a live request.
- **Affects**: anyone calling `POST /pathway/verifications` (must send `submitted_at`)
- **Replaces**: none
- **PR / branch**: `feat/pathway-sdg-guardrails`

---

## M4: Core & Organisation (Core, F7)

<!-- M4 adds entries below this line -->
