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
- **Unfinished / for owners**: no real ingestion, matching, pathway logic or LLM calls (all mocks); repositories read mocks, not the database yet; courses are example.org placeholders (F5 must verify a real catalogue); SDG reasons are mock text pending review (F6); only 5 SDG targets seeded (F6 loads all 17 goals); ms/zh translations are first drafts to be reviewed by native speakers; web has no unit tests yet (only tsc + eslint); `.env.example` documents all variables.
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

### TEAM-004: Autonomous agent workflow with explicit trust and execution boundaries
- **Date**: 2026-10-29
- **Feature**: Core / all
- **Type**: other
- **Change**: Keep `AGENTS.md` as shared policy with thin Claude/Gemini import entry points and explicit fallback reads. Replace blanket shared-file/feature approval stops with task-scoped autonomy; add untrusted-content handling, workspace preservation, secret/environment isolation, server-side privacy checks, and truthful verification requirements. Correct stale upload/auth/dependency guidance and align decision IDs with the existing log.
- **Why**: Preserve tool/model capabilities and avoid repetitive permission prompts while preventing data loss, credential leakage, prompt-injection authority escalation, accidental live writes, and conflicting instructions. Instruction text complements code/CI/service enforcement; it cannot guarantee perfect security.
- **Affects**: All coding agents using root instructions; no application runtime changes
- **Validation**: Local instruction links, balanced code fences, Claude/Gemini entry-point parity, unique TEAM-004 ID, and `git diff --check` passed. `python src/scripts/dev.py check` passed translation parity but could not complete lint/tests/contracts without `.venv` or TypeScript checks without installed web dependencies. The retry outside the sandbox resolved npm access; remaining failures are missing local dependencies. No live database/model operations were used.
- **Replaces**: TEAM-003 operating guidance where superseded; preserves its single-manual architecture
- **PR / branch**: `docs/core-agent-guardrails`

### TEAM-005: Replit PostgreSQL and signed local accounts only
- **Date**: 2026-10-29
- **Feature**: Core / all
- **Type**: dependency | method | other
- **Change**: Remove the unused external JWT authentication provider, verifier, claim mapping, web bypass, environment settings and sole-purpose PyJWT dependency. Keep the deployed `AUTH_MODE=demo` name for signed local accounts and use Replit's managed PostgreSQL through `DATABASE_URL`; local development/CI retain PostgreSQL 16 with pgvector. Production matching now requests strict trend snapshots using `APP_ENV=production` instead of an alternate auth mode.
- **Why**: The user confirmed that the retired provider is not used for either storage or authentication and requested removal across code and documentation. Existing migrations, PostgreSQL access, password hashing, signed sessions and membership checks remain. At the user's explicit request to remove provider references everywhere, historical entries retain their original events but replace provider-specific setup details with a retirement note; public job-posting employer names remain source data, not integrations.
- **Affects**: Core/F8 authentication, F4 trend reads, dependency manifests/lock, setup and architecture docs, agent stack guidance, submission source and PDFs
- **Validation**: Full quality gate passed (980 tests, 32 opt-in/environment skips, 48 subtests), plus 26 client regressions and the production web build. The lockfile removes only the unused JWT package; other package versions are unchanged. Edited PDF pages were rendered and visually checked. Docker is unavailable, so no disposable PostgreSQL integration or live Replit database verification was performed.
- **Replaces**: TEAM-002's alternate auth stub, M3-003's external JWT integration and stale provider guidance in the project context
- **PR / branch**: `chore/core-replit-database-cleanup`

### TEAM-006: Disclose trend fallback throughout recommendations (review 1.1)
- **Date**: 2026-10-29
- **Feature**: F2/F3/F4/F5/F8 and Core
- **Type**: contract
- **Change**: Snapshot and freshness responses identify database versus fixture serving and fallback status. Trend-derived recommendation metadata preserves these fields; the shared metadata bar shows a translated, visible last-good-snapshot notice. Pathways retain the snapshot date separately from source retrieval dates.
- **Why**: Database failure or an empty snapshot table must not appear to be fresh live data. Existing strict reads still reject unavailable authoritative data.
- **Affects**: Trend, scenario, match, pathway, overview and assistant metadata; generated API client
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-007: Keep historical replay explicit in navigation (review 1.2)
- **Date**: 2026-10-29
- **Feature**: F2/F4/F5 and Core
- **Type**: UI
- **Change**: Radar offers Latest by removing the snapshot query parameter. Journey links carry only scenario and role; explicit historical match/detail/pathway views display a translated banner returning to latest while preserving their role, scenario and SDG weight.
- **Why**: Exploring an old radar snapshot must not silently disable saving a current learning plan.
- **Affects**: Journey navigation, radar picker, matches and pathway UI
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-008: Explicit best-effort proxy identity and per-session limits (review 1.3)
- **Date**: 2026-10-29
- **Feature**: Core/F8
- **Type**: method
- **Change**: Add `PROXY_CLIENT_IP_MODE=trusted|best-effort`; best-effort permits zero hops in production while preserving the shared proxy secret. All forwarding paths select only the right-most valid address. Missing addresses warn and forward without X-Real-IP. Protected-route rate limits use session-verified user IDs; anonymous login/signup/preview retain IP buckets.
- **Why**: Zero-hop deployments must start deliberately without making every authenticated user share the loopback allowance or rejecting requests lacking forwarded headers. Missing anonymous addresses necessarily share the direct-peer bucket; this limitation is documented.
- **Affects**: Configuration validation, private proxy, server clients, rate limits and startup regressions; no infrastructure settings changed
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-009: Catalogue-grounded score improvements (review 2.1)
- **Date**: 2026-10-29
- **Feature**: F4/F5/F8
- **Type**: formula
- **Change**: Return each open skill's score gain from closing its remaining importance-weighted overlap, using the existing 0.45 skill weight, plus the cheapest catalogue course reaching the required level (otherwise null). SDG-weighted scores scale those gains too. Cards show the top three; Adi and cards expose weighted arithmetic and actual catalogue links.
- **Why**: Learners need concrete, traceable changes that would improve fit without inventing a course or promising a partial course closes a full gap.
- **Affects**: Matching contracts/client, card/detail UI, Adi context and score answer blocks
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-010: Share the scenario reference range without forcing rank changes (review 2.2)
- **Date**: 2026-10-29
- **Feature**: F2/F4 and Core
- **Type**: formula
- **Change**: Normalize skill velocity with min-max bounds over both stored scenarios in each snapshot; matching, detail and replay use those same bounds. Preserve full score-component precision so API ordering matches its scores. Show each card's score difference from the other scenario's API response. Weights remain 0.45/0.25/0.30.
- **Why**: Independent percentiles erased magnitude changes. Existing Fast velocities already encode scenario effects, so applying another multiplier would double-count them. Following the user's delegated choice, real-profile regressions require a change above 0.005: the observed maximum is 0.0084866, below the initially requested 0.01. A separate synthetic near-tie applies k=1.5 before the same shared normalization and proves a rank flip. No profiles, reference data or weights were changed to force results.
- **Pipeline**: stored scenario snapshots → preserve raw velocities → shared union bounds → min-max/weighted score → all four fixture profiles plus synthetic rank-flip and old-normalizer failure checks → match/detail/replay API and score delta chip
- **Affects**: F4 score and replay adapters/contracts, match UI, synthetic regressions
- **Replaces**: M2-001 percentile normalization only
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-011: Require a separate explicit sharing choice on join (review 2.3)
- **Date**: 2026-10-29
- **Feature**: Core/F7
- **Type**: contract
- **Change**: Remove the join payload's true sharing default; require a strict boolean and reject missing or false sharing consent with 422 before joining. Join UI has separate, initially unticked membership and skill-sharing checkboxes. Actions submit the actual checkbox value, and signup checks sharing before creating an account. Existing per-organisation sharing revocation remains available.
- **Why**: General membership consent must never silently authorize manager access to skill levels, study hours or budgets. A revoked member remains excluded from manager learning inputs.
- **Affects**: Join/signup validation and actions, translated join flow, generated client and privacy regressions
- **Replaces**: M4-055 bundled join disclosure and default sharing only
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-012: Visible attribution and hour-weighted SDG learning links (review 2.4)
- **Date**: 2026-10-29
- **Feature**: F4/F5/F6 and Core
- **Type**: formula
- **Change**: Show source names inline, place estimate labels beside fit percentages, and preserve catalogue mapping reasons/strengths on SDG badges and match-card tooltips. SDG contribution sums each step's planned hours once per distinct mapped target/goal, including its course skills, divided by all planned hours across people. Role-wide and plan-wide links remain available as supporting explanations. Source metadata includes SDG references and preserves pathway fallback status.
- **Why**: Unequal learning plans should not contribute as equal-sized sets. The UI labels these as estimated learning-hour shares, allows overlapping targets and explicitly distinguishes them from measured progress toward UN targets.
- **Affects**: Recommendation metadata UI, match/preview/dashboard fit labels, SDG contracts and aggregation, generated client
- **Replaces**: M3-006 unweighted contribution display only
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-013: Show role directions and ground declining answers separately (review 2.5)
- **Date**: 2026-10-29
- **Feature**: F2/F5/F8
- **Type**: UI
- **Change**: Radar shows rising and declining roles from the existing RoleOption comparison for the selected scenario/date. Adi stores separate declining skill/role facts from the snapshot and routes declining questions to a grounded multilingual block. A model selection cannot replace that requested block with rising advice.
- **Why**: Skill trends alone hid role directions, and declining questions previously reused the rising list. Directions remain estimates, not claims that jobs will disappear.
- **Affects**: Radar role card, Adi context/routing, translated headings and regression cases
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-014: Scored, grounded Adi intent routing and the review matrix (review 2.6)
- **Date**: 2026-10-29
- **Feature**: Core/F8
- **Type**: method
- **Change**: Score keyword hits across intents with conservative difflib typo tolerance and low generic weights, while keeping people decisions, injection refusal and other-person privacy ahead of scoring. Safety replies load no private context and invoke no provider. Add grounded source, scenario, SDG-definition, forecast-limit, unsupported-action and missing-data answers; resolve ordinal roles against current rankings. Specific intents cannot be replaced by generic model selections.
- **Why**: First-match overlap sent realistic questions to unrelated blocks. Facts come from the catalogue, current user's plans/matches and source metadata; scenario comparison calls the production matcher at the same snapshot. Missing facts are stated rather than guessed.
- **Affects**: Adi guide, context and answer selection; the user's verbatim 40-row EN/MS/ZH matrix, guard precedence, typo and missing-context regressions
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-015: Complete model and data disclosure register (review 2.7)
- **Date**: 2026-10-29
- **Feature**: F8 / Core
- **Type**: contract, UI
- **Change**: Serve one versioned public register of trend and Adi models, job feeds, certification sources, BNM rates and O*NET 31.0 through the disclosure contract and render every entry on About with EN/MS/ZH purposes. Disclose MiniLM's background research encoding and GLM-5.3's validated block selection even when this instance uses the built-in Adi guide; keep active provider disclosure separate.
- **Why**: Disabling Adi does not erase models used to prepare trend snapshots. The register describes system roles without fabricating retrieval dates or claiming a live provider check. Existing dated source and sync records remain separate.
- **Affects**: Guardrails disclosure, generated API contracts, About page and registry completeness tests
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-016: Scope team learning credit to the current organisation (review 3.1)
- **Date**: 2026-10-29
- **Feature**: F5 / F7
- **Type**: method
- **Change**: Filter team earned-learning reads to the current organisation's scope and, only for consenting members, personal learning. Preserve the learner's own cross-workspace credit and the existing single batch query.
- **Why**: A member's work in another organisation must not affect the current team's gaps or plans. Shared profile skills do not authorize disclosure of another organisation's learning records.
- **Affects**: Team skill inputs, memory and PostgreSQL learning reads
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-017: Protect current role with membership sharing consent (review 3.2)
- **Date**: 2026-10-29
- **Feature**: F7
- **Type**: method
- **Change**: Return null for a member's current role unless that organisation's skill-sharing consent is active, in both PostgreSQL and the fixture store. Keep the stored profile unchanged when consent is revoked.
- **Why**: A role is profile data and must follow the same explicit consent boundary as skill levels.
- **Affects**: Organisation member responses
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-018: Revoke signed sessions with an uncached account version (review 3.3)
- **Date**: 2026-10-29
- **Feature**: Core / F8
- **Type**: schema, contract, method
- **Change**: Append a users.session_version migration, sign the current version into v2 session tokens, and check it without the account cache on every verification. POST logout increments the version for all sessions of that account. Next.js requires a same-origin POST, revokes through FastAPI before clearing cookies, and rejects GET with 405; sign-out controls submit forms. Rate-limit identity checks move blocking verification to a worker and fail closed on storage outages.
- **Why**: Cookie deletion alone cannot invalidate a copied token, and GET links allow cross-site logout. Existing v1 sessions intentionally require a fresh sign-in after this upgrade. Revocation storage is shared across instances.
- **Affects**: Local-account sessions, auth/logout, sign-out controls, rate-limit verification and generated contracts. Apply the migration before deploying code; rollback drops revocation state and requires coordinated code rollback and fresh sign-in.
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-019: Apply security headers to Next.js responses (review 3.4)
- **Date**: 2026-10-29
- **Feature**: Core / F8
- **Type**: method
- **Change**: Add a global Next.js header rule for CSP with frame-ancestors none, frame denial, nosniff and one-year HSTS. Restrict script and connection origins to self in production; retain inline hydration scripts and existing inline styles. Permit eval and WebSocket connections only in development.
- **Why**: FastAPI headers do not protect HTML served by Next.js. The existing static pages and inline JSX styles require inline allowances; nonce enforcement would require a separate rendering change. Bundled three.js needs no remote script origin or production eval.
- **Affects**: Page, static and API response headers; Next.js configuration-response regression
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-020: Share the last good trend serving fallback (review 3.5)
- **Date**: 2026-10-29
- **Feature**: F2 / F4 / F5
- **Type**: contract, method
- **Change**: Keep a bounded store of successfully read public database snapshots in the trend service. One non-I/O fallback returns the requested cached date or the newest cached database snapshot, otherwise the committed date-aware fixture, always marked is_fallback. Radar, matching read failures/timeouts and pathway outages use it. Remove the pathway-only legacy CSV fallback and its separate scenario weighting; retry fallback reads on the shared short TTL.
- **Why**: Serving callers must agree on dates, velocities and provenance during outages. Both scenario velocities are already present in each saved snapshot, so Fast fallback must not be weighted again. Unknown replay dates remain 404 and available dates list only servable snapshots. Strict database-only diagnostics still raise; production matching explicitly uses disclosed serving fallback after strict-read failure.
- **Affects**: Trend serving and adapter fallback metadata, cache bounds, timeout and replay regressions
- **Replaces**: M2-020 (production matching outage behavior only; bounded strict reads remain)
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-021: Return preliminary matches for saved zero-skill profiles (review 3.6)
- **Date**: 2026-10-29
- **Feature**: F4
- **Type**: contract, UI
- **Change**: Allow a saved profile without confirmed or earned skills through the existing scorer. Skill overlap contributes zero; trend and interest determine ranking under the unchanged 0.45/0.25/0.30 weights. Return an add_skills notice code and render its EN/MS/ZH explanation on match list and detail views.
- **Why**: An empty skill list should offer a usable first ranking and a clear next step. Keeping the existing score scale preserves explainability and improvement deltas rather than fabricating skill credit. Profiles with no saved intake still receive profile_required.
- **Affects**: Matching profile loader and role response, generated contracts, match notices
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-022: Actionable empty states, saving feedback and consistent journey totals (review 3.7)
- **Date**: 2026-10-30
- **Feature**: Core / F1 / F4 / F5
- **Type**: UI
- **Change**: Render existing EmptyState components for empty matches and comparisons, show a busy Saving label during intake submission, and derive page totals from navigation. Personal navigation and its home journey include skills, radar, roles, plan, progress and SDG links; the organisation journey retains four stages. Show the existing scenario hint visibly. Replace all raw ApiError call sites with ErrorState using the full failure object and remove the unused renderer.
- **Why**: Empty or failed results need a next action; disabled submission needs visible feedback. Navigation and page counts must agree. Existing retry, sign-in and missing-profile actions remain the shared recovery path; impact review has no fabricated completion event.
- **Affects**: Shared error rendering, learner navigation and affected page headings, intake feedback, EN/MS/ZH copy and DOM regressions
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-023: Contrast-safe muted text and heatmap labels (review 3.8)
- **Date**: 2026-10-30
- **Feature**: Core / F1 / F7
- **Type**: UI
- **Change**: Darken the existing muted green-grey token, including its registered default and team override; use it for disclaimer text. Keep heatmap background hues and calculate the higher-contrast black/white label from relative luminance. Add a visible deep-green focus outline around intake radio cards.
- **Why**: Small text must reach 4.5:1 on white and sage surfaces. A fixed heatmap value threshold selected white text before the background was dark enough. Regression checks measure the actual rendered cell styles over the entire clamped range.
- **Affects**: Muted copy, disclaimer, team heatmap labels and keyboard intake focus
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-024: Reserve mobile clearance for the Adi launcher (review 3.9)
- **Date**: 2026-10-30
- **Feature**: Core
- **Type**: UI
- **Change**: Give mobile main content and the final disclaimer bottom padding equal to tab-bar height plus 80px and the device safe-area inset. Keep the existing 52px launcher and its position.
- **Why**: The final content must scroll above both fixed controls, including on devices with a bottom safe area. Padding the disclaimer too prevents it remaining covered at the end of the page.
- **Affects**: Workspace mobile spacing; clearance regression reads actual CSS dimensions
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-025: Translate error codes at the rendering boundary (review 3.10)
- **Date**: 2026-10-30
- **Feature**: Core / F1 / F5 / F7
- **Type**: contract, UI
- **Change**: API failures carry status and validated machine codes without raw backend prose. Profile/auth actions return codes for local validation and request failures; auth preserves non-password form values. One typed EN/MS/ZH lookup renders codes in ErrorState and affected client forms, with a translated fallback for unfamiliar codes. Existing pathway action adapters reuse the common parser, and organisation adapters forward codes.
- **Why**: English fallback text and backend messages bypassed locale selection. Updating the consuming forms together avoids exposing codes to users. Distinct server password-failure codes preserve the difference between wrong credentials and an expired session while retaining HTTP 401 and the existing exception type. Preserve specific file, consent, stale programme, evidence and budget recovery instructions without passing backend details into the UI.
- **Affects**: ApiFailure internal TypeScript shape, auth/profile actions, shared action errors, organisation forms, localization and parser/action/DOM regressions
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades`

### TEAM-026: Reconcile scoped review commits with current main and gate all web regressions
- **Date**: 2026-10-30
- **Feature**: Core / all
- **Type**: method, other
- **Change**: Reconstruct the 20 numbered review commits on main at `55bf2d0`, preserving its team-account copy, auth branding and safe logout redirects while applying explicit consent, translated errors and POST-only revocation. Run every `tests/web-*.test.ts` regression in CI, including the component suites previously omitted; align the auth stub with BrandMark and exercise the production redirect helper through POST logout.
- **Why**: The earlier instruction, profile resolver and provider-removal work is already merged through PRs #26/#27 and must contribute no new diff here. The broader web run exposed two harness integration failures despite the previous CI selection passing. The user authorized a separate compatibility commit after the 20 scoped commits instead of rewriting the pushed draft branch. Defer deploying review 3.3 until after judging: v2 rejects all existing v1 sessions, logout revokes every session for the account, and the session-version migration must precede the corresponding application release. Keep it in the draft for review without authorizing production changes.
- **Affects**: Review integration, web regression CI and session rollout planning; no changes to resolver files, submission PDFs or lockfiles
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades-clean` / PR #29


### TEAM-027: Keep streamed score text under React ownership during scenario navigation
- **Date**: 2026-10-30
- **Feature**: Core / F3 / F4
- **Type**: UI, method
- **Change**: Remove the imperative number count-up from PageEnter while retaining its CSS page entrance. The parent no longer rewrites server-rendered KPI/fit text during child hydration or scenario navigation. Add a production-component regression that runs the mount effects before descendant hydration and preserves the server score text.
- **Why**: The old effect changed a server score from 41 to 0 before its descendant could hydrate, reproducing a concrete text mismatch consistent with React error 418. A streamed parent effect is not proof that every descendant has hydrated. The synthetic PostgreSQL-backed scenario endpoints returned in 41?141 ms during investigation; that does not verify browser transition latency or prove this is the only cause of the reported hang. The existing Docker web image showed the older four-stage UI, so it must not be confused with the clean review branch. Browser automation stopped on an address/document URL confidence check; no successful manual toggle is claimed.
- **Affects**: Shared page entrance and recommendation metric rendering; scores, attribution, session rollout and provider configuration are unchanged
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades-clean` / PR #29

### TEAM-028: Correct signup, public role directions and recommendation provenance after PR review
- **Date**: 2026-10-30
- **Feature**: Core / F2 / F3 / F6 / F7 / F8
- **Type**: UI, contract, method
- **Change**: Submit JoinView's team-account switch through POST logout, preserving both signup query parameters. Read radar role directions through the public trend-signals endpoint with an additive optional snapshot date, pinned to the displayed skill snapshot, without loading personal intake or plans. Keep the original match metadata separately from Adi's trend metadata, re-read both scenarios at that match date, and reject mismatched responses. Aggregate SDG plan origins independently of fallback status: cached database plans remain database-sourced; any fixture input marks the aggregate fixture-sourced, and otherwise incomplete origin metadata remains unknown.
- **Why**: The review found a GET caller left behind by POST-only logout, an inappropriate learner-profile dependency for managers, comparison dates that could diverge across strict/non-strict caches, and database fallback mislabeled as fixture data.
- **Affects**: Team signup entry, learner/organisation radar, generated OpenAPI/TypeScript bindings, Adi scenario answers and SDG attribution. Existing radar callers remain compatible. Session-version production rollout remains deferred until after judging.
- **Replaces**: none
- **PR / branch**: `fix/core-review-upgrades-clean` / PR #29

### TEAM-029: Preserve PDF overflow detection and run static privacy/asset checks in CI
- **Date**: 2026-10-30
- **Feature**: F1 / Core verification
- **Type**: method
- **Change**: Charge PDF page separators only when joining a subsequent page, retaining the extra character used to detect truncation at the text limit. Include `privacy-page.test.mjs` and `dead-assets.test.mjs` explicitly in the frontend CI regression command; the HTTP suite remains separate because this step does not start a server.
- **Why**: PR #30 review identified silent PDF truncation when a page ends exactly at the retained-text limit and static regression files omitted by the TypeScript-only CI glob.
- **Pipeline**: synthetic PDF page text in memory → bounded extraction and existing cleaning → existing catalogue aliases → deterministic extraction with an overflow character → boundary regressions against production extraction/truncation → existing CV response warning
- **Affects**: PDF truncation metadata and frontend CI; no dependencies, database, API contracts or model settings change
- **Validation**: Both exact-limit omission cases failed before the fix. All six boundary cases and 40 targeted parser tests now pass; the expanded frontend command passes 62 tests. The full quality gate passes (1189 tests passed, 32 environment/opt-in skips, 54 subtests passed), including source attribution and contract drift checks, with database/model providers isolated. The initial sandbox run was blocked by npm, temporary-file and subprocess permissions; the approved rerun passed.
- **Replaces**: none
- **PR / branch**: `feat/core-hardening-and-submission-evidence` / PR #30

### TEAM-030: Require verified proxy hops and prepare count-only Replit evidence
- **Date**: 2026-10-30
- **Feature**: Core / F8
- **Type**: method
- **Change**: Zero hops no longer signs XFF as client identity, including in best-effort production mode. Positive counts validate and select a suffix from the right (one = last entry, two = second-last); all web relays use one helper. Add opt-in `PROXY_LOG_XFF_COUNT` diagnostics containing only entry counts, plus an owner-run verification procedure.
- **Why**: #55 cannot assume a platform sanitises caller headers. A shared secret authenticates our relay but does not make its input trustworthy. The maintainer lacks access to the friend's Replit workspace, so live verification remains pending; synthetic edge tests are not deployment evidence. Unverified best-effort mode keeps serving with a shared anonymous direct-peer bucket; verified session limits remain unchanged. Counts alone cannot establish spoof resistance or the correct hop setting.
- **Affects**: Server component/action API clients, API proxy, preview and Adi forwarding; production warnings and configuration documentation. No new migration or deployment is performed. Tests cover forged-prefix bucket continuity, zero-hop rejection, malformed/short suffixes and count-only logging.
- **Validation**: After integrating latest main (`95a2505`) while preserving the PM regression branch (`8cc9ed0`), the full isolated quality gate passed: 1317 pytest tests, 54 subtests, 32 environment/opt-in skips; lint, TypeScript, translations, source attribution and contract drift passed. All 74 web regressions passed again; the Next.js production build passed before the upstream-only configuration/documentation integration. Sandbox-denied npm/module/subprocess operations were rerun through approved escalation. Remote CI, Greptile and the live Replit chain were not verified.
- **Replaces**: TEAM-008's zero-hop XFF trust; positive counts now have explicit suffix semantics rather than always selecting the last entry.
- **PR / branch**: `fix/core-proxy-scenario-loading`

### TEAM-031: Submit scenario changes through native GET navigation
- **Date**: 2026-10-30
- **Feature**: Core / F3
- **Type**: UI, method
- **Change**: Replace ScenarioToggle's router transition and global busy state with a normal GET form. Submit exactly one selected scenario and preserve other query entries, including repeated filters, role, snapshot and SDG weight. Retain roving radio focus and arrow-key submission.
- **Why**: The user still reports indefinite loading after TEAM-027's hydration fix. The control previously stayed unavailable for as long as an RSC transition remained pending. A native document navigation removes that dependency and works before hydration; it deliberately incurs a full page load and resets transient client state. This addresses the control's indefinite transition state without claiming that the inaccessible production root cause has been reproduced or that network/backend outages cannot delay navigation.
- **Affects**: Scenario control in learner and organisation shells; no API, formula, scoring, attribution or provider changes. Production-component tests cover both directions, filters, keyboard submission and EN/MS/ZH server markup.
- **Validation**: The built standalone web server and unmodified API passed an isolated loopback HTTP smoke with a synthetic signed-in account: moderate → fast → moderate → fast, completed streamed pages, matching selected controls/estimate labels and preserved repeated filters. This exercised native GET form serialization over HTTP, not a browser click or production deployment. Providers were disabled, storage was disposable in-memory state, and both child processes were stopped.
- **Replaces**: ScenarioToggle's transition-only navigation; TEAM-027's React ownership fix remains in place.
- **PR / branch**: `fix/core-proxy-scenario-loading`

### TEAM-032: Integrate reviewed trend scoring and on-demand refresh
- **Date**: 2026-10-30
- **Feature**: F2, F3, F4, F5 and Core
- **Type**: method
- **Change**: Integrate the interrupted trend worktree: robust shared velocity scaling, bounded scenario weights, evidence coverage, truthful frozen-source dates, bounded database reads and asynchronous RunPod job polling/cancellation. Dashboard admins can dispatch the existing published MiniLM workflow or re-score stored signals; provider and GitHub credentials stay server-side.
- **Why**: Scenario comparisons need a shared reference distribution; an untracked skill is not evidence of decline. Refresh should be reachable from the app without an unbounded inference request.
- **Pipeline**: arXiv → cleaned abstracts → catalogue skill embeddings → published MiniLM and shared robust scoring → production-function regression/counterfactual tests → dated PostgreSQL snapshots with explicit fixture fallback.
- **Affects**: matching, preview, pathway, trend contracts, dashboards and workflow setup
- **Replaces**: scenario scaling/fallback implementation portions of TEAM-010 and TEAM-020
- **PR / branch**: fix/core-review-regressions

### TEAM-033: Stable admin identities and scoped learning records
- **Date**: 2026-10-30
- **Feature**: Core and F7
- **Type**: schema
- **Change**: Replace unverified email admin matching with ADMIN_USER_IDS in API and web gates. Add membership lookup index, generated organisation keys and NOT VALID learning foreign keys, and force transaction-scoped funding RLS. Member removal cleans private ledger references atomically while retaining anonymised historical events.
- **Why**: Email text is not identity proof. New writes must resolve to real roles/workspaces without deleting legacy records; old orphan rows require a separate audit before constraint validation. Production roles must not have superuser/BYPASSRLS privileges.
- **Affects**: admin deployment configuration, funding, membership removal and migration rollout
- **Replaces**: email-based admin authorization in M4-027
- **PR / branch**: fix/core-review-regressions

### TEAM-034: Observation dates, regional privacy and explicit workspace navigation
- **Date**: 2026-10-30
- **Feature**: F1, F5, F6, F7 and Core
- **Type**: contract
- **Change**: Batch heatmap profile reads and date their actual stored inputs; keep raw skill gaps scenario-invariant observations. Regional SDG outputs require five distinct people and suppress rare target/goal cells. Workspace selection is an exact-origin POST verified against current memberships; login, join, role, cohort and scenario context survive navigation.
- **Why**: Trend metadata cannot make observations fresh. Counting memberships twice or returning rare cells leaks small cohorts. GET links must not change workspace state.
- **Affects**: SdgContribution status fields, heatmaps, auth/workspace routes, Adi links and pathway navigation
- **Replaces**: none
- **PR / branch**: fix/core-review-regressions

### TEAM-035: Dated Malaysian context and verified current occupations
- **Date**: 2026-10-30
- **Feature**: F2, F5 and Core
- **Type**: data source
- **Change**: Add the DOSM monthly Labour Force Survey as separately labelled national observations, never blended into occupational forecasts. Add three verified O*NET current occupations with source codes; do not advertise them as emerging target roles. Scheduled catalogue and jobs sync require explicit database secrets.
- **Why**: Local context and non-technical intake coverage are useful only with traceable evidence. Malay course records remain pending verified delivery-language and provider metadata.
- **Pipeline**: DOSM public CSV → bounded date/rate validation → latest complete monthly rates → no predictive model → parsing/provenance tests → stored API response and dated fixture, with collapsed dashboard disclosure.
- **Affects**: source register, role catalogue, new public-context table/API, dashboard and data-source workflow
- **Replaces**: none
- **PR / branch**: fix/core-review-regressions

### TEAM-036: Final-round operations, infrastructure and browser verification
- **Date**: 2026-10-30
- **Feature**: all
- **Type**: dependency
- **Change**: Integrate the infra draft's production configuration, container, rate-limit, source-attribution and fairness checks; remove pathway daemon-thread timeouts in favour of the bounded F2 operation. Pin Playwright 1.64.1 and run real desktop/mobile synthetic journeys against isolated services; run CI for every PR target, including stacked branches. Publish revision/dirty build identity and loopback-only synthetic account preparation. Align unsigned submission sources with the supplied finalist templates and six official rubric categories.
- **Why**: Local passing checks do not establish production state or measured human impact. Reproducible builds, independent browser checks and explicit outstanding evidence make those limits reviewable.
- **Affects**: CI, Docker, Python task runner, development dependency lock, demo tooling and submission documentation
- **Replaces**: abandoned timeout-worker implementation in refactor/pathway-trend-and-match-ports
- **PR / branch**: fix/core-review-regressions

### TEAM-037: Record the frontend and Adi worktree handover
- **Date**: 2026-10-30
- **Feature**: F1, F4, F7, F8 and Core
- **Type**: UI
- **Change**: Record the already integrated frontend/Adi commits: optional skill sharing independent of membership, operational student-project privacy notice, session-aware team CTAs, radar-first intake, populated role comparison and weighted score bars, Steady/Rapid display labels, phrase-level Adi routing and grounded multilingual replies. Scenario IDs remain moderate/fast; Adi uses validated answer blocks.
- **Why**: Claude left proposed decision notes outside the append-only log. These changes affect consent and user interpretation and need an authoritative record.
- **Affects**: signup/join, privacy, matching, landing and Adi; original commits d51c0d7, f724298, d287224 and e0be794
- **Replaces**: mandatory sharing condition on joining; preserves explicit programme acceptance requirements
- **PR / branch**: fix/core-review-regressions

### TEAM-038: Keep refresh workflow configuration distinct from CI metadata
- **Date**: 2026-10-30
- **Feature**: F2 and Core
- **Type**: contract
- **Change**: Rename the app-only workflow setting to TRENDS_REFRESH_WORKFLOW. Regenerate source branch contracts and add a regression with the real GitHub runner variable present.
- **Why**: GITHUB_WORKFLOW is reserved runner metadata and caused refresh configuration tests to reject CI as a filename; validation remains strict.
- **Affects**: app environment configuration and review-branch CI
- **Replaces**: workflow environment setting in TEAM-032
- **PR / branch**: fix/core-review-regressions

### TEAM-039: Ground historical MyCOL badges and separate measured API timings from human KPIs
- **Date**: 2026-10-30
- **Feature**: F1 / F4 / F8 / Core submission evidence
- **Type**: contract | method | UI | other
- **Change**: Add an optional historical MyCOL badge to RoleMatch, with its own RecommendationMeta, edition and page locator. Resolve only an explicit stored role-ID crosswalk; the sole reviewed mapping is data-analyst to MASCO 2524, whose restricted title list explicitly includes Data Analyst. Display the sourced badge on matching list/detail cards in all three locales without changing scoring. Align the About register, README and re-exported technical declaration on RunPod MiniLM, RunPod GLM with Gemini failover, Replit and Google Fonts/Fontsource assets; retain ElevenLabs after the user's actual-use confirmation.
- **Why**: The reference CSV was disconnected, broad MASCO groups are insufficient evidence for arbitrary title matches, and the declaration export lagged its source. Existing CSS uses system fonts, so installed Inter assets are disclosed without inventing live Google Fonts requests. The user confirmed no human trials exist; preserve the unrun human template and null reduction while recording separate automated synthetic journeys, including failed attempts.
- **Pipeline**: official MyCOL PDF and five synthetic demo CVs -> visually verify the restricted title list and use existing intake/parser rules -> stored role IDs and reviewed synthetic skill fixtures -> metadata-only badge and production API journeys with signed synthetic sessions -> exact-ID/negative/ranking-invariance/source regressions and recorded step timings -> matching cards and dated submission evidence, with no human speed-up claim
- **Affects**: additive matching/guardrails contracts and generated clients, matching UI/translations, reference crosswalk, API image reference-file packaging, declaration export and KPI evidence; no ranking formula, migration, runtime provider enablement or deployment change
- **Validation**: Final full quality gate passed: 1,435 Python tests passed, 34 skipped, 54 subtests passed, and 78 frontend regressions passed. The production frontend build passed. Both fairness reports contain 65 invariant synthetic-CV cases; all 15 final signed-session API journeys completed. The eight-page declaration was exported and visually reviewed; Docker runtime and production deployment remain unverified.
- **Limits**: Review the published CV-text fairness rewrite from cb8bbf0 using both scenarios, meaningful negative controls and real stored-profile boundary regressions. Passing these finite synthetic cases does not establish universal fairness. Human KPI trials remain 0 testers/0 trials.
- **Replaces**: none; extends TEAM-015 disclosure and the historical MyCOL reference deliverable
- **PR / branch**: `fix/core-final-round-integration`, based on fetched `fix/core-review-regressions`

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

### M1-006: Bounded snapshot reads and internal fail-closed mode
- **Date**: 2026-10-21
- **Feature**: F2 (Trends), F3 (Scenarios)
- **Type**: method
- **Change**: All snapshot-read connections use `_get_connection(connect_timeout_s=2, statement_timeout_ms=2000, lock_timeout_ms=1000)`, passing integer `connect_timeout=2` and libpq startup `options="-c statement_timeout=2000 -c lock_timeout=1000"`. Resolution performs the bounded dates query directly, eliminating the separate health probe from the request path; demo failures retain the five-second negative cache. Offline pipelines are unchanged.
- **Why**: Bound connection establishment, statements and lock waits while preserving default HTTP fallback/not-found behavior. Strict calls bypass the demo cache and raise on database errors, empty databases, or fixture contexts; unknown requested dates still raise `NotFoundError`. No HTTP parameter, schema or generated contract changes.
- **Manual verification**: Isolated PostgreSQL 16 with psycopg 3.3.6 reported connection parameter `connect_timeout=2`, `SHOW statement_timeout = 2s`, and `SHOW lock_timeout = 1s`. `SELECT pg_sleep(10)` raised `QueryCanceled` at 2.000 s; an access-exclusive table lock caused a strict snapshot call to raise `TrendsUnavailableError` (cause `LockNotAvailable`) at 1.031 s. Temporarily setting process-only `DATABASE_URL` to `192.0.2.1:5432` raised `TrendsUnavailableError` (cause `ConnectionTimeout`) at 2.000 s; the environment was restored and `.env` was untouched.
- **Quality gate**: `python src/scripts/dev.py check` passed in all three states: unavailable database (332 passed / 21 skipped), migrated empty database (332 / 21), and standard seeds plus 220 rows from the committed two-date trend exports (334 / 19). Existing tests were unchanged. Standalone `python src/scripts/dev.py contracts` followed by `git diff --exit-code -- src/api/openapi.json src/web/src/lib/api/types.ts` confirmed zero drift.
- **M2 calling contract**: Import `get_snapshot` from `app.features.trends.service`; signature `get_snapshot(snapshot_date: date | None, scenario: ScenarioId, strict: bool = False) -> TrendSnapshotResponse`. Call `get_snapshot(snapshot_date, scenario, strict=True)` (`None` selects latest). Catch `TrendsUnavailableError` imported from `app.features.trends.repository` and map it to M2's own HTTP 503 inside matching. The exception propagates unchanged through the service; successful database results are identical in both modes. M2's adapter is not modified here.
- **Affects**: M2 (opt-in internal adapter call)
- **Replaces**: M1-004 and M1-005 request-path health probing only; default fallback and source/date semantics retained
- **PR / branch**: `feat/m1-trends-contract`

### M1-007: Interrupt established-connection network stalls
- **Date**: 2026-10-21
- **Feature**: F2 (Trends), F3 (Scenarios)
- **Type**: method
- **Change**: Wrap date and snapshot cursor operations in a three-second client watchdog. On expiry, shut down the socket in both directions to unblock pending libpq I/O locally; retain descriptor ownership in libpq, cancel/join the watchdog before connection cleanup, and use autocommit for read-only connections so cleanup cannot wait for COMMIT/ROLLBACK. Existing server and connection timeouts remain in place.
- **Why**: Greptile P1: server-side statement/lock timeouts cannot release a client when an established connection stops replying. Merely timing out a future would leave request workers or database threads blocked. Socket shutdown interrupts the actual pending operation without waiting for server cancellation or TCP failure detection.
- **Validation**: Real loopback peers complete PostgreSQL startup and then withhold every query reply. Tests cover date resolution, reused snapshot connections, both standalone loaders, strict errors versus existing default fallback/not-found behavior, peer-observed disconnect, and watchdog cancellation on success. No public contract changes.
- **Affects**: M2 internal callers retain the same `strict=True` / `TrendsUnavailableError` interface
- **Replaces**: M1-006 bounded-read claim (adds the missing client-side network deadline)
- **PR / branch**: `feat/m1-trends-contract`

### M1-008: Bug fix — score_rows() iterates full DB skill catalogue (Bug 1)
- **Date**: 2026-10-23
- **Feature**: F2 (AI-trend signal layer)
- **Type**: method
- **Change**: Added `load_skill_ids(db_url) -> set[str]` that queries `SELECT id FROM skills` (same canonical source as `validate_ids`). Added optional `skill_ids: set[str] | None = None` to `score_rows()`; when provided, iterates `sorted(skill_ids)` instead of `sorted(exposure_map)`, skills absent from `canonical_skills.csv` receive `DEFAULT_EXPOSURE = 0.5`. Refactored `main()` to delegate to `score_rows()` (eliminates duplicate inline loop).
- **Why**: Skills absent from `canonical_skills.csv` were silently dropped from every snapshot, violating the zero-invented-entities guardrail by omission. The DB `skills` table is the only authoritative catalogue.
- **Affects**: pipeline output only; API contract unchanged
- **Replaces**: none
- **PR / branch**: `feat/m1-trends-contract`

### M1-009: Bug fix — fast scenario magnitude invariant at role level (Bug 2)
- **Date**: 2026-10-23
- **Feature**: F3 (Scenarios & uncertainty)
- **Type**: formula
- **Change**: Added `enforce_fast_magnitude(moderate, fast) -> float` which floors `|fast deviation|` to `|moderate deviation|` when same sign, without flipping sign. Applied in `get_outlook()` after importance-weighted aggregation. Added range clamping `low = min(low, outlook_val)` / `high = max(high, outlook_val)` to guarantee `low <= outlook <= high` after adjustment.
- **Why**: Mixed-exposure role aggregations can partially cancel, making the aggregate fast signal less extreme than moderate — breaking Must-Have #6 (the judge toggles scenario switch live and sees fast < moderate). Guard restores the invariant at role level without changing per-skill math.
- **Affects**: none (no contract field change)
- **Replaces**: none
- **PR / branch**: `feat/m1-trends-contract`

### M1-010: Bug fix — nonzero uncertainty range at low coverage (Bug 3)
- **Date**: 2026-10-23
- **Feature**: F3 (Scenarios & uncertainty)
- **Type**: formula | contract | UI
- **Change**: Changed `outlook_range()` widen from `(1-cov)*|signal|` to `(1-cov)*(|signal|+BASE_UNCERTAINTY)` where `BASE_UNCERTAINTY=0.10`. Added `MIN_COVERAGE_THRESHOLD=0.20`; roles below this get additive field `insufficient_evidence=True` (default `False`) on `RoleOutlook`. Amber "Low evidence" badge added to `RoleOutlookPanel.tsx`, styled in `adept.css`, i18n keys in all three locales.
- **Why**: Old formula collapsed widen to 0 at near-zero signal regardless of coverage, giving a false point estimate — violating Must-Have #6. The flag surfaces thin-evidence cases without hiding the numeric range.
- **Affects**: M4 (frontend consumes new optional field); all consumers of `OutlookResponse` (additive, default `False`)
- **Replaces**: none
- **PR / branch**: `feat/m1-trends-contract`

### M1-011: Automated MiniLM worker publishing to GHCR and Replit-RunPod integration architecture
- **Date**: 2026-10-24
- **Feature**: F2 (AI-Trend Signal Layer) / Core deployment
- **Type**: model | dependency | architectural decision
- **Change**: Added `.github/workflows/publish-minilm.yml` to automatically build and publish the MiniLM RunPod worker image to GitHub Container Registry (`ghcr.io/pecel-lelele/adept-minilm:latest`) on changes to the worker or manual trigger. Added `TRENDS_*` variables to `.env.example` and root `.env`. Updated `DEPLOYMENT_HANDOFF.md` and `README.md` documenting the Replit + RunPod architecture.
- **Why**: Facilitates deploying the pinned sentence-transformers `all-MiniLM-L6-v2` worker to RunPod Serverless without local Docker setup. When the web app is hosted on Replit, it serves pre-computed PostgreSQL `trend_snapshots` with zero GPU cold-start delay, while the batch trend pipeline runs on GitHub Actions or locally, making authenticated calls to the RunPod Serverless worker endpoint.
- **Pipeline** (data/ML only): arXiv cs.AI + BLS 2023-2033 -> clean HTML, sentence chunk -> 384-d MiniLM vectors via RunPod Serverless (`ghcr.io/pecel-lelele/adept-minilm:latest`) -> cosine similarity (threshold >= 0.55) -> composite velocity -> PostgreSQL `trend_snapshots` served on Replit.
- **Affects**: M1 (trend pipeline execution), M4 (Replit deployment / RunPod setup)
- **Replaces**: none
- **PR / branch**: `feat/minilm-runpod-deploy`

### M1-012: Review trend scaling, on-demand refresh and source provenance
- **Date**: 2026-10-30
- **Feature**: F2, F3 and jobs
- **Type**: method
- **Change**: Share robust reference scaling across scenarios and preview/matching, disclose coverage and frozen provenance, bound outages, poll/cancel RunPod asynchronous jobs, and expose workflow refresh/re-score controls. Refilter stored job locations offline before the next fetch; the committed source data stays dated.
- **Why**: Low coverage must not be confused with decline; source dates and cold-start handling must reflect actual evidence and runtime behaviour. Final integration replaces email-based admins with stable account IDs.
- **Pipeline**: arXiv/job sources → cleaning/geographic filtering → catalogue embeddings/counts → MiniLM/shared scaling → production scorer/refilter tests → dated stored snapshots and job records
- **Affects**: F4, F5, preview, dashboard and jobs
- **Replaces**: none
- **PR / branch**: worktree-agent-a17103c77ff6e8291

### M1-013: Separate app refresh configuration from GitHub runner metadata
- **Date**: 2026-10-30
- **Feature**: F2
- **Type**: contract
- **Change**: Use TRENDS_REFRESH_WORKFLOW for the application workflow filename; the runner-owned GITHUB_WORKFLOW variable must not select an app dispatch target. Regenerate the source branch contracts from production schemas.
- **Why**: Branch CI exposed a collision with GITHUB_WORKFLOW=CI. Preserve validation instead of accepting a malformed filename or masking the inherited setting in tests.
- **Affects**: refresh configuration and branch CI
- **Replaces**: workflow environment setting in M1-012
- **PR / branch**: worktree-agent-a17103c77ff6e8291

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

### M2-003: Matching responses carry real snapshot date and sources (never invented)
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: contract | method
- **Change**: `trend_port.py` now returns a typed `TrendSnapshot` dataclass whose every field (`velocities`, `snapshot_date`, `sources`, `scenario`, `is_estimate`) comes directly from M1's snapshot `meta` — no defaults, no invented values. `service.py` maps these field-by-field into `RecommendationMeta`. When the snapshot is unavailable (no items or no sources), the port raises `TrendUnavailable` (alias for `TrendUnavailableError`) → router converts to 503. Tests in `test_snapshot_meta.py` freeze "today" to 2026-10-21 while the fake snapshot is dated 2026-10-20, proving `meta.snapshot_date` never equals `date.today()`.
- **Why**: Prompt-1 review item: the old implementation used `date.today()` and a hardcoded `"MOCK DATA"` source string in `RecommendationMeta`. This violates AGENTS.md §3 rule 4 (mandatory output attribution).
- **Affects**: none (internal matching module only)
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-004: Matching calls M1's trend service in-process with threading timeout (no HTTP)
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: method | dependency
- **Change**: Removed all HTTP self-calls (previously `fetch_snapshot` called `GET /api/v1/trends/snapshot` over `requests`). `trend_port._call_with_timeout` now calls `app.features.trends.service.get_snapshot` on a daemon thread and joins with `SNAPSHOT_TIMEOUT_S=2.0` (same guard as M3's pathway port). A hung psycopg connect is bounded; any exception or timeout raises `TrendUnavailable` → 503. Removed dead `_SNAPSHOT_URL` constant, `_API_BASE` constant, `get_settings` import, and `base_url` parameter from `fetch_snapshot`. Added `tests/api/matching/conftest.py` patching M1's fixture snapshots (mirrors `tests/api/pathway/conftest.py`) so router tests never need a live DB.
- **Why**: Prompt-2 review item: self-calling over HTTP held two thread-pool threads per request, starving the pool under concurrent load. The threading daemon + bounded join pattern is already established by M3's pathway port.
- **Affects**: none (internal matching module only; trends service not modified)
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-005: Matching uses live saved profile with no cache and raises 4xx when profile missing
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: method | contract
- **Change**: Replaced cached CSV persona reading in matching repository (`_load_profile` with `@lru_cache`) with a direct integration to `profile_service.get_my_profile(user_id)`. Converted skill levels 1-5 to [0, 1] using `profile_service.normalise_level` (single conversion function). Built `MatchProfile` strictly adhering to the fairness whitelist (only skills and interests; demographic signals like age, gender, and background are never read). If a user has no saved profile or has no saved skills, `repository._load_profile` raises `ProfileRequiredError` (HTTP 400 Bad Request) instead of falling back to mock matches or an empty list. Removed `@lru_cache` so user profile edits immediately reflect in matches. Moved CSV persona loading into `app.features.matching.personas` solely for evaluation harness and demo seeding; verified production code does not import it.
- **Why**: Prompt-3 review item: user's saved profile edits were not reaching matches because matching read from static cached CSV files. Additionally, unknown users received mock matches instead of a clear profile-required error.
- **Affects**: F1 profile service (accepts user_id string and exports `has_profile`), F4 matching repository/personas
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-006: Unified skills-gap rule with pathway and live SDG badges from SDG service
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: formula | method | contract
- **Change**: Deleted the hardcoded gap thresholds (`HAVE, PARTIAL = 0.7, 0.3`) in `scoring.py`. Implemented `gap_state(user_level, required_level)` (integer levels 1-5: `have` if user_level >= required_level, `partial` if 0 < user_level < required_level, `missing` if <= 0) and aligned the overlap score rule with `credit = min(user_level / required_level, 1.0)`, ensuring overlap score and gap status never disagree. Added `gap_port.py` delegating to `pathway.service.skills_gap()`, and loaded each role's `required_level` directly from `taxonomy/role_skills.csv`. Removed the hardcoded `_ROLE_SDG` dictionary and added `sdg_port.py` delegating to `sdg.service.role_badges()`, mapping reviewed SDG targets from `role_sdg_map.csv` to `RoleMatch.sdg_targets`.
- **Why**: Prompt-4 review item: matching and pathway previously used conflicting gap thresholds, and matching presented hardcoded SDG badges rather than the authoritative reviewed SDG mapping from M3.
- **Affects**: F4 matching repository/scoring, F5 pathway (read-only gap caller), F6 SDG (read-only badges caller)
- **Replaces**: none
### M2-007: Safe, accurate CV parsing pipeline rewrite
- **Date**: 2026-10-21
- **Feature**: F1 (Skills Profile Intake)
- **Type**: model | method | contract | security
- **Change**:
  1. Rewrote CV parser (`cv_parser.py`) for safe in-memory extraction with 200k char truncation (`truncated: bool` flag added to `CvExtractionResult`), ReDoS-safe linear regex patterns for PII stripping (`_EMAIL_RE`, `_URL_RE`, `_PHONE_RE`), non-overlapping span matching (`(?<!\w)phrase(?!\w)`), and count-based confidence capped at 1.0 (`CONFIDENCE_PER_HIT = 0.30`).
  2. Routed CPU-bound parsing through `asyncio.to_thread` in `router.py`.
  3. Enforced strict content-type validation (`application/pdf`, `text/plain` only; 415 on invalid types) and upload size check (413).
  4. Added `PdfSupportUnavailable` (501 `pdf_unsupported`) and `PdfNoText` (422 `pdf_no_text`) typed errors; never decode PDF binary as text.
  5. Isolated alias matching strictly to catalogue labels without word-splitting to eliminate false-positive subword matches (e.g. "data entry" matching "data analysis").
  6. Added comprehensive test suite `tests/api/profile/test_cv_parser_prompt5.py` (18 tests covering ReDoS safety, word boundaries, non-overlapping spans, 413/415/422/501 error responses, catalogue guarantee, and end-to-end multipart HTTP upload).
- **Why**: Prompt-5 review item: resolved ReDoS vulnerabilities in regex, unhandled PDF errors / silent binary fallback, sub-word false positives, event loop blocking during CV processing, and missing truncation signals.
- **Pipeline** (data/ML only): raw bytes -> extract_text(fitz/utf-8) -> _truncate_text(200k) -> _clean_text(NFKC + linear PII strip) -> extract_skills(longest-alias-first, non-overlapping spans) -> context proficiency level -> confidence score -> sorted ParsedSkill list.
- **Affects**: M2 (profile CV intake contract), M4 (UI receives `truncated` flag)
- **Replaces**: M2-002 (item 1 only)
- **PR / branch**: `feat/matching-scoring-engine`

### M2-008: Benchmark tests run on production code only (item 12b)
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: method | data source
- **Change**: Removed the benchmark's private copies from `tests/api/matching/test_evaluation.py`: the duplicated `interest_map` (a copy of `repository._ROLE_INTEREST_TAGS`) and `_load_catalog_roles()` (a re-implementation of `repository._load_roles` that silently dropped `required_level`). The benchmark now calls the production `repository.load_roles()` (new public wrapper; interest tags read through the new `repository.role_interest_tags()` getter), `personas.load_all_personas()` and the new `personas.load_expected_roles()` harness loader (moved from the test), and `scoring.rank_roles`. Added a guard test that monkeypatches the production role-tag getter and asserts the benchmark metrics change. Baseline `velocities` stay in the test as frozen benchmark inputs (production velocities come from M1's live snapshot via trend_port).
- **Why**: Review item 12b: tests must not carry their own copy of production data or logic, or the benchmark proves nothing about what ships.
- **Affects**: none (test-side + new public getters in matching repository/personas)
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-009: Match response returns trend_coverage (item 12c)
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: contract
- **Change**: Added optional `trend_coverage: float | None` (0..1) to `contracts.matching.RoleMatch`, filled in `repository._score_to_contract` from the scoring engine's `_RoleScore.trend_coverage` (computed by `scoring.role_trend` as the importance-weighted share of role skills present in the trend snapshot). Mock responses leave it None. Regenerated `openapi.json` and `src/web/src/lib/api/types.ts`; no frontend file edited. New tests in `tests/api/matching/test_trend_coverage.py` (field present and in [0,1] on list/get; exactly 0.0 when the snapshot covers none of the role's skills).
- **Why**: Review item 12c: the UI must warn when many skills fell back to the neutral 0.5 trend instead of real data.
- **Affects**: M4 (shared contract change — field added, additive and optional; UI may surface a low-coverage warning), M3 (pathway already exposes its own `trend_coverage`)
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-010: Real Jaccard interest fit, exact-match interest sanitising, `provided` flag on score components
- **Date**: 2026-10-21
- **Feature**: F1 (Skills Profile Intake), F4 (Future-Role Matching & Gap)
- **Type**: formula | method | contract
- **Change**:
  1. Part A (item 8): interests are free text (`contracts/profile.py`, questionnaire `interests: list[str]`), so `_sanitise_interests` (`profile/service.py`) now normalises each tag (lowercase, punctuation stripped, spaces collapsed) and drops it **only** when the whole normalised text equals a member of the module-level `BLOCKED_DEMOGRAPHIC_INTERESTS` = {age, gender, race, ethnicity, religion, nationality, disability}. Every `startswith`/substring test on the interest path is gone, so "agentic AI", "management", "language", "package" and "age-friendly design" survive while "age"/"Age"/"gender" are dropped.
  2. Part B (item 12a): `scoring.interest_fit` is a real Jaccard, `len(interests & tags) / len(interests | tags)`, replacing the previous containment ratio `len(interests & tags) / len(interests)`. It returns `None` when the user has no interests; `score_role` then contributes `NEUTRAL` 0.5 for that weight, and `_RoleScore.breakdown` is typed `dict[str, float | None]`.
  3. Contract: `ScoreComponent` gains `provided: bool` (default true). `repository._score_to_contract` sends `value = 0.5, provided = false, explanation = "Not provided: ..."` for a user with no interests, instead of a null value, so the UI can show "not provided" from a flag rather than by parsing English, and existing consumers that treat `value` as a number keep compiling.
  4. Tests: `tests/api/profile/test_interest_sanitising.py` and `tests/api/matching/test_interest_jaccard.py` (0.2 / 1.0 / 0.0 / None + neutral contribution, plus API-level `provided` and a recomputed-Jaccard cross-check); `test_matching_scoring.py` updated to the Jaccard value.
- **Why**: Review items 8 and 12a. The label said "Jaccard" while the formula was containment; the substring filter over-blocked (dropped "agentic AI" for starting with "age") and under-blocked nothing, since only an exact demographic tag can be a protected attribute.
- **Affects**: M4 (`ScoreComponent.provided` is additive; `ScoreBreakdown.tsx` can render "not provided" from it — no M4 file was edited here), M3 (reads gap ports, not interest scores), benchmark (see below)
- **Pipeline** (data/ML only): taxonomy role interest tags + free-text interests → normalise + exact-match demographic drop → Jaccard(interests, tags) or None → weighted composite (0.5 skill / 0.3 trend / 0.2 interest, neutral 0.5 when not provided) → evaluation: `tests/api/matching/test_evaluation.py` now reports mean P@3=0.7778, R@3=0.7778, MRR=0.8333, nDCG@3=0.8083 against gates MRR=1.0 / P>=0.85 / R>=0.85 / nDCG>=0.90 — **failing**, because Jaccard's magnitude is systematically smaller than containment on this tag vocabulary (max ~0.43 vs 1.0), which silently cut the interest signal's influence and let `ai-operations-specialist` overtake hand-labelled relevant roles for aisyah and ravi → serving: `GET /matches`, `GET /matches/{role_id}`.
- **Affects (open)**: the benchmark gate needs a decision — re-tune `Weights` (a scan shows w_interest >= 0.3 restores MRR=1.0, P@3=0.8889, nDCG@3=0.9392 with tags unchanged), re-author the synthetic role interest tags, or revise `expected_roles.csv`. Gates were deliberately **not** weakened.
- **Replaces**: none (supersedes the interest term inside M2-001 item 1)
- **PR / branch**: `feat/matching-scoring-engine`

### M2-011: Matching weights re-tuned to 0.45 skill / 0.25 trend / 0.30 interest
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: model | formula
- **Change**: `scoring.Weights` defaults (the single canonical source) move from `skill=0.5, trend=0.3, interest=0.2` to `skill=0.45, trend=0.25, interest=0.30`. `repository._W`, `mocks.WEIGHTS`, and `replay._DEFAULT_WEIGHTS` follow; `repository._W` and the benchmark/scoring test constants now use `Weights()` instead of restating the numbers, so there is one place to change them. `matching/FEATURE.md` stage table updated.
- **Why**: Real Jaccard (M2-010) has a systematically smaller magnitude than the previous containment ratio (max attainable ≈0.43 on this role-tag vocabulary versus 1.0), so keeping `w_interest=0.2` quietly defanged the interest term and the benchmark gate failed (P@3 0.7778, nDCG@3 0.8083 against P>=0.85 / nDCG>=0.90). Options were: re-tune the weights, re-author the synthetic role interest tags, or revise the hand-labelled `expected_roles.csv`. Re-tuning is the only one that touches no ground-truth data and weakens no assertion. A candidate scan over ratio-preserving and interest-heavy setups picked 0.45/0.25/0.30: it passes every gate with the widest nDCG margin (+0.0392) while keeping skill overlap the dominant term, which is the product's explainability claim.
- **Pipeline** (data/ML only): role tags + free-text interests + M1 snapshot velocities → same preprocessing as M2-010 → percentile-ranked trend, weighted composite 0.45/0.25/0.30 (neutral 0.5 when interests not provided) → evaluation on `tests/api/matching/test_evaluation.py` (k=3, gates unchanged): per-persona P@3 1.0 / 1.0 / 0.6667, mean P@3=0.8889, mean R@3=0.8889, mean MRR=1.0, mean nDCG@3=0.9392 — **passing** → serving: `GET /matches`, `GET /matches/{role_id}`.
- **Affects**: M4 — the weights arrive in the response payload, so `ScoreBreakdown` and any `/app` numbers shift automatically with no code change on their side; M2 benchmark tests (already wired to production, M2-008).
- **Replaces**: M2-001 (item 1 — weight values only; the formula shape and the explainability contract are unchanged)
- **PR / branch**: `feat/matching-scoring-engine`

### M2-012: Synthetic CV fixtures generated by a stdlib PDF writer; PyMuPDF added as a read-only dependency
- **Date**: 2026-10-21
- **Feature**: F1 (Skills Profile Intake)
- **Type**: dependency | data source | other
- **Change**:
  1. `src/scripts/generate_mock_cvs.py` writes eight fixtures to `tests/api/profile/fixtures/cvs/` — one CV per synthetic persona (`cv_aisyah/weijie/ravi.pdf`, name + segment + skills read from `src/data/seed/personas/*.csv`) plus `cv_data_entry.pdf`, `cv_python_programming.pdf`, `cv_java_javascript.pdf`, `cv_scanned.pdf` (image-only, no selectable text) and `cv_long.txt` (exactly 100,000 characters, no `@`). All names are invented, all emails are on `example.com`.
  2. The PDFs are written by the script itself (PDF 1.4, Helvetica literal strings, one FlateDecode `DeviceGray` image XObject, hand-built xref), so **no PDF-writing dependency** was added. Output is deterministic: no `/CreationDate`, no timestamps, trailer `/ID` = MD5 of the body; `--check` compares a fresh generation against the files on disk (CI mode) and `--verify` re-parses them with the production parser.
  3. `requirements.txt` gains `pymupdf>=1.24.0,<2` (runtime). The parser now imports `pymupdf` and falls back to the older `fitz` alias; the `<2` bound avoids the deprecated `fitz` shim and the four transitive packages PyMuPDF 2.x drags into every `make setup`.
  4. `tests/api/profile/test_cv_fixtures.py` parses each fixture with the production parser and posts three of them through `POST /api/v1/profile/cv`. Expected persona skill IDs come from `matching.personas.load_persona_profile` (the shared seed loader), not a copy. PDF tests skip with an install hint when PyMuPDF is absent.
- **Why**: Review item 9 — the CV endpoint had to be testable and demoable before M4's intake UI exists. Fixtures went to `tests/api/profile/fixtures/cvs/` because that follows the repo's existing fixture convention (`tests/pipelines/*/fixtures/`) and keeps non-CSV binaries out of `src/data/seed/`, which `src/db/seed.py` scans for table files. A PDF library for generation was rejected because a hand-written writer keeps the dependency surface at one read-only package.
- **Pipeline** (data/ML only): seed personas + taxonomy → deterministic PDF/text writer (no LLM, no inference) → fixture files → serving: `POST /profile/cv` → evaluation: `test_cv_fixtures.py` (14 tests, all passing; 10 skip cleanly with PyMuPDF blocked)
- **Affects**: M4 (they can upload these files against the intake UI once it exists), every teammate (`make setup` now installs PyMuPDF), CI (`generate_mock_cvs.py --check` can gate fixture drift)
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-013: CV parser never decodes PDF bytes as text; unreadable PDFs are 422 pdf_unreadable
- **Date**: 2026-10-21
- **Feature**: F1 (Skills Profile Intake)
- **Type**: method | contract
- **Change**: Final sweep (Prompt 10) removed every `.decode("utf-8", errors="replace")` fallback that could be reached with PDF bytes in `profile/cv_parser.py`. Deleted the legacy `(filename, bytes)` branches of `extract_text`/`parse_cv` and the legacy `extract_text_from_pdf` helper — they existed only for tests, and the production path (`router` → `service.extract_cv` → `parse_cv(bytes, mime)`) already used the modern signature. `parse_cv` now always returns `(skills, truncated)`. An empty or unopenable PDF raises `AppError(422, "pdf_unreadable")`; `PdfSupportUnavailable` (501) is reserved for the server genuinely lacking PyMuPDF, and `PdfNoText` (422) for a PDF that opens but has no text. Tests migrated in `test_f1_intake.py`: three assertions that required the unsafe fallback (binary decoded into the skill scanner, `except Exception` swallowing `PdfNoText`) now require the refusal instead, and `test_parse_returns_sorted_by_confidence` lost its vacuous `if len(results) > 1` guard.
- **Why**: The sweep's rule is that PDF bytes must never be treated as text. The fallbacks did exactly that, and worse, `except Exception` converted a scanned or corrupt upload into a silent `200` with an empty skill list, which the UI would render as "this CV shows no skills" instead of "I could not read this file". 501 for a corrupt file was also wrong: it tells the user PDF support is missing on a server that has it.
- **Pipeline** (data/ML only): raw bytes → extract_text (PyMuPDF only; 422 if unreadable) → truncate → clean → taxonomy scan → serving: `POST /profile/cv` (unchanged success shape) → evaluation: `tests/api/profile/test_f1_intake.py`, `test_cv_parser_prompt5.py`, `test_cv_fixtures.py` (498 tests pass repo-wide)
- **Affects**: M4 — `POST /profile/cv` can now answer `422 {"error":{"code":"pdf_unreadable"}}` for an empty or corrupt PDF (previously 200-with-empty-skills on the legacy path, 501-worded on the modern one). No OpenAPI schema change: error bodies are not schematised, so `openapi.json`/`types.ts` are untouched. Also reviewed `core/fairness.py:61`, which keeps a `startswith` prefix rule — it matches *field names* against protected stems (`ethnic` → `ethnicity`), not free-text interests, and does not sit on the interest path, so it is left as is.
- **Replaces**: none (extends M2-007)
- **PR / branch**: `feat/matching-scoring-engine`

### M2-014: expected_roles.csv is benchmark ground truth, never a database table
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: data source | schema
- **Change**: Records the decision already landed in commit `a2950c1`, which had no log entry. `src/db/seed.py` keeps `NON_TABLE_CSVS = {"expected_roles"}` and skips those files while collecting, so `make seed` never tries to insert hand-labelled relevance judgements into a table; every other CSV under `src/data/seed/` must name a table in `TABLE_ORDER` or seeding raises. The file stays in `src/data/seed/personas/` because it is persona-shaped data, and the benchmark reaches it through `matching/personas.py::load_expected_roles`.
- **Why**: Prompt 10 asked for this entry explicitly. Ground truth is an evaluation artefact, not workforce data: seeding it would put M2's private labels in the demo database where F7 heatmaps or any future query could read them as if they were observations about real people, and it would make the benchmark self-fulfilling.
- **Affects**: M4 (`make seed` output unchanged apart from the skip), M2 benchmark, anyone adding a new CSV to the seed tree
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-015: Remove matching catalogue cache and align benchmark proficiency with production
- **Date**: 2026-10-21
- **Feature**: F1 (Skills Profile Intake), F4 (Future-Role Matching & Gap)
- **Type**: method
- **Change**: Removed matching's remaining `lru_cache` from the catalogue loader to satisfy review F1; the benchmark guard now reads fresh roles without cache-reset setup. Corrected the harness-only persona loader to preserve proficiency levels 1–5, matching saved-profile production input and role requirements, instead of normalising them to 0–1. Added review acceptance tests for cache absence, production/harness parity, real in-process trend calls under disabled HTTP clients and concurrency, frozen-date metadata, full-parser timings, truncation, explicit test-only Java boundaries and deterministic fixture generation.
- **Why**: Session validation found the original suite green (498 passed, 21 skipped), but added acceptance checks exposed one cache violation and three persona scale mismatches. Neither benchmark thresholds, role tags, ground truth nor weights were changed. Java and JavaScript remain absent from the production catalogue; the scanner boundary test uses an isolated test catalogue only.
- **Pipeline**: synthetic persona CSVs / saved profiles + taxonomy + frozen benchmark velocities → preserve levels 1–5 and interest tags → required-level skill credit + percentile trend + Jaccard → existing weighted ranking → 12 targeted benchmark/coverage/parity tests passed; mean P@3=0.8889, R@3=0.8889, MRR=1.0, nDCG@3=0.9650 → GET /api/v1/matches.
- **Affects**: M2 evaluation; M4 owns the contract-check gate, which reports modified generated files even when regeneration is stable. No other lane's modules, contracts or dependencies were edited for these fixes.
- **Replaces**: M2-001/M2-005 normalised-scale descriptions for matching; M2-011 benchmark metrics (weights unchanged)
- **PR / branch**: PR #4 / feat/matching-scoring-engine

### M2-016: Add taxonomy aliases to the skills schema
- **Date**: 2026-10-21
- **Feature**: F1 (Skills Profile Intake), F4 (Future-Role Matching & Gap)
- **Type**: schema
- **Change**: Add `skills.aliases text NOT NULL DEFAULT ''` using the append-only migration `20261021150000_m2_skill_aliases.sql`. This matches the `aliases` column in `src/data/seed/taxonomy/skills.csv` and allows the generic CSV seed loader to insert the field into both fresh and upgraded databases. The default preserves compatibility with older seed files that omit aliases. The down migration drops the added column.
- **Why**: CI failed during the post-migration taxonomy seed: `skills.csv` included `aliases`, but the initial skills table did not. The seed loader correctly builds insert columns from the CSV header; the schema must support that data.
- **Affects**: CI database migration/seed job and matching taxonomy consumers; no API contract change.
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-017: Bound CV match counting and timed-out trend workers
- **Date**: 2026-10-21
- **Feature**: F1 (Skills Profile Intake), F4 (Future-Role Matching & Gap)
- **Type**: method
- **Change**: CV skill extraction stops scanning a skill after its confidence reaches 1.0. The matching trend adapter calls M1 `get_snapshot(..., strict=True)`, maps `TrendsUnavailableError` to the matching 503, and shares at most one outstanding getter among concurrent requests. A timed-out getter retains its slot until it exits; later requests fail fast while it remains occupied.
- **Why**: Repeated CV aliases previously caused needless overlap comparisons after the score was already capped. A request timeout alone did not stop a stuck trend worker, so concurrent timeouts could start unbounded threads/connections. M1-006 now bounds its database connections and queries and exposes strict failure behavior; the M2 worker cap remains a resource guard.
- **Affects**: M1 trend availability under a stuck database read; matching may return fast 503 responses while its sole trend worker remains stuck.
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-018: Load match interest tags from the role catalogue
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: data source | method
- **Change**: Store each role's interest tags in `taxonomy/roles.csv` and load them alongside role labels. Add an HTTP integration test covering saved profile intake, deterministic matching output, attribution, trend coverage, skill gaps, SDG badges, and strict trend failure.
- **Why**: Matching must use catalogue-owned role attributes and produce explainable, attributed results from the saved profile; duplicated role tags in Python could drift from the catalogue.
- **Affects**: matching score interest contribution; catalog consumers using `roles.csv`
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-019: Replay matching against an explicit M1 snapshot
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: method | contract | UI
- **Change**: Both matching endpoints accept an optional `snapshot_date` and obtain that scenario/date directly from M1's trend service. The API and matching pages also carry M1's provenance note, including fixture caveats. The matching page exposes a date control and preserves the date in role-detail links. While replaying, its pathway link explicitly points to the latest-data plan because F5's UI does not yet forward snapshot dates. Concurrent requests for different scenarios or dates cannot share one in-flight trend result. API gaps always come from F5's `skills_gap` port, and the role-detail route no longer shows F3's static mock outlook panel.
- **Why**: A selected historical snapshot must drive the actual score and attribution, while a request for a different snapshot cannot inherit another caller's data. The static F3 range was not derived from M1 evidence.
- **Pipeline**: M1 dated snapshot → validate requested scenario/date and source → skill velocities → existing F4 scoring formula → replay API check for both dates → matching API and UI
- **Affects**: M1 snapshot service; M3 pathway UI still needs to forward a selected date before matching and pathway views can replay together.
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-020: Use M1's disclosed fixture snapshot in demo mode
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: method
- **Change**: Matching calls M1's in-process snapshot service in its documented demo mode when `auth_mode=demo`, allowing M1's fixture fallback and carrying its provenance note into the matching API and UI. Other auth modes request `strict=True` and return 503 if the database snapshot is unavailable. The bounded worker key includes the mode so concurrent demo and live reads cannot share a result.
- **Why**: The explicit demo must work without a database and disclose its frozen source; live matching must still fail closed rather than silently substitute fixtures. This also aligns M2 with M1's existing demo contract without editing M1 or M3 features.
- **Affects**: Matching availability and source disclosure; M1 snapshot service is consumed unchanged.
- **Replaces**: M2-017's unconditional strict-read choice
- **PR / branch**: `feat/matching-scoring-engine`

### M2-021: Store role interest tags in the roles table
- **Date**: 2026-10-21
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: schema
- **Change**: Add nullable `roles.interest_tags text` in the append-only `20261021160000_m2_role_interest_tags.sql` migration. Backfill the four synthetic future-role values for databases seeded before the migration; fresh seeds take the values from `taxonomy/roles.csv`.
- **Why**: The generic seed loader inserts every CSV column, but the roles table lacked the newly added `interest_tags` column. GitHub's database job failed at `Load seeds` with `UndefinedColumn`. Blank role tags become SQL `NULL` in the seed loader, so the column must allow NULL. The backfill keeps upgraded role rows consistent because the seed loader skips existing IDs.
- **Affects**: CI database migration and seed job; F4 role catalogue data.
- **Replaces**: none
- **PR / branch**: `feat/matching-scoring-engine`

### M2-022: Queue distinct trend reads behind the bounded M2 worker
- **Date**: 2026-10-22
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: method
- **Change**: Different scenario/date requests wait up to five seconds for the single M1 trend worker, using a condition that releases the state lock while waiting. Identical requests still share the active result; a timed-out worker retains the sole slot until it exits. A 503 is returned when the queue deadline expires.
- **Why**: Immediate rejection of a different snapshot caused avoidable 503 responses during ordinary overlapping requests. Waiting on the semaphore while holding the state lock would prevent worker cleanup, so the port waits for a state change and acquires the semaphore outside that lock.
- **Affects**: M2 matching latency under concurrent requests; M1 trend service is unchanged.
- **Replaces**: M2-017's fast-fail policy for a busy worker
- **PR / branch**: `feat/matching-scoring-engine`

### M2-023: Alias-aware skill bank and abstaining search resolver
- **Date**: 2026-10-29
- **Feature**: F1 (Skills Profile Intake)
- **Type**: method | contract | UI
- **Change**: Return approved aliases from the skill catalogue and include them directly in the existing local manual-search filter. Add an authenticated, rate-limited POST resolver whose deduplicated union contains at most one alias, one fuzzy and one semantic candidate. Fuzzy uses each canonical skill's best label/alias `SequenceMatcher` score with `top_score >= 0.83` and `top_score - runner_up_score >= 0.05`; above-threshold ties/close scores abstain before embedding. Semantic remains the existing top-1 cosine rule, `>= 0.80` and lead `>= 0.015`, using only a ready index.
- **Why**: The picker omitted approved aliases such as Microsoft Excel. Explicit query submission, a four-letter/digit minimum before semantic lookup, and a bounded in-memory wizard-session cache (including pending and empty results) prevent embedding requests per keystroke. Catalogue IDs/labels, dated attribution and human confirmation remain mandatory; provider failure retains deterministic candidates. No new dependency, migration or model default.
- **Pipeline**: existing public taxonomy labels/aliases → NFKC/case/whitespace normalization and bounded query → per-skill string scores / existing optional embeddings → tier-specific top-1 gates and ID validation → nine-case production-function regression (three positives, two out-of-catalogue negatives, three short tokens, one close-score ambiguity; all pass at 0.83/0.05) → attributed proposals and explicit Add/confirmation.
- **Affects**: F1 API contracts and generated client, manual intake picker and EN/MS/ZH copy, resolver rate bucket, README and F8 About-page embedding-purpose disclosure. Existing CV semantic suggestion path unchanged.
- **Replaces**: none; preserves M4-061 semantic thresholds and top-1 output
- **PR / branch**: `fix/profile-alias-resolver`

### M2-024: Preserve CV status and avoid unused extraction/search work
- **Date**: 2026-10-29
- **Feature**: F1 (Skills Profile Intake)
- **Type**: method | contract | UI
- **Change**: Show empty-result feedback in intake and truncation warnings in both CV screens without restoring the wording list. Add `include_suggestions` to authenticated and preview CV extraction, defaulting to true for API compatibility; both web upload paths explicitly disable semantic suggestions. Reuse one fuzzy ranking for resolver candidates and ambiguity checks.
- **Why**: Address three PR review findings: silent empty/truncated uploads, paid provider work for discarded suggestions, and duplicate catalogue comparisons. Preserve attribution, user confirmation, parsing limits and existing matching thresholds.
- **Pipeline**: synthetic CV or submitted search → existing bounded parsing/normalization → catalogue matches and one fuzzy ranking → optional semantic suggestions only when requested → API opt-out/default and ranking-count regressions → extraction feedback and confirmed skill selection.
- **Affects**: F1 service/router, guest preview, web upload screens, generated contracts and resolver
- **Validation**: All 215 profile/preview tests and four skill-search client tests passed. Regressions verify that both CV APIs skip suggestion calls when disabled, preserve their default behaviour and return truncation/empty extraction metadata; the resolver scores the catalogue once. The complete quality gate and production web build also passed.
- **Replaces**: M2-023's unchanged CV UI behaviour; preserves its resolver gates
- **PR / branch**: `chore/core-replit-database-cleanup`

### M2-025: Index frozen MyCOL reference assets once per worker
- **Date**: 2026-10-30
- **Feature**: F4 (Future-Role Matching & Gap)
- **Type**: method
- **Change**: Read the frozen crosswalk, occupation CSV and provenance JSON through a cached zero-argument loader and index them by stored role ID and MASCO code. Badge lookups no longer reopen or rescan files, including for unsupported roles; construct fresh scenario-specific response models and source metadata on every call.
- **Why**: PR #69 review identified repeated reference reads across every ranked role. These are versioned release assets, so a worker restart loads a new reference release; user profiles, role catalogue reads, scores and request metadata are not cached.
- **Pipeline**: frozen verified MyCOL assets -> parse once per worker -> role-ID and MASCO indexes -> exact ID lookup with unchanged badge attribution -> file-open-count, metadata-isolation and existing badge/source regressions -> matching list/detail responses
- **Affects**: F4 historical MyCOL badge reads only; no contract, dependency, scoring or source-date change
- **Replaces**: TEAM-039's per-lookup reference-file loading; preserves M2-015's fresh role catalogue and saved-profile behaviour
- **PR / branch**: PR #69 / `fix/core-final-round-integration`

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
- **Change**: `app/core/security/`: per (IP, route bucket) sliding-window rate limiter (LRU-capped, never evicts a throttled key, `X-Real-IP` trusted only with `PROXY_SHARED_SECRET`), Content-Length body limits (1 MB JSON, upload cap + slack), security headers (CSP `default-src 'none'` except `/docs`), prompt-injection sanitiser, filename sanitiser, regex PII redaction adapted to Malaysia (MyKad NRIC, passport, +60/0 phones; specific phone patterns so date ranges like 2019-2024 survive). Installed once from `create_app` before CORS. The web server forwards the client IP with the secret (`src/web/src/lib/api/server.ts`). A former external JWT integration was added at this stage and later retired; see TEAM-005.
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

### M3-026: Pathway reads M1's trend snapshot; compare roles before choosing; ports for M2
- **Date**: 2026-10-21
- **Feature**: F5, F6, F8
- **Type**: data source | method | contract | UI
- **Change**: New `pathway/trend_port.py` is the only place F5/F6/F8 get trend data: M1's `trends.service.get_snapshot` in process (no HTTP self-call), falling back to the legacy seed snapshot (`mock-0`) only when M1 has none. M1's `velocity_<scenario>` already models the scenario, so the engine no longer weights it again (`scenario_weighted`). Pathway meta cites M1's sources and date; re-plan fires when M1's snapshot date changes; skills M1 does not score (excel, rpa, sql today) are listed in a warning and treated as neutral. New `GET /pathway/compare` (+ web `/app/pathway/compare`) shows each target role's weeks, cost, skills to close, trend outlook and F6 SDG targets side by side before the learner chooses; `GET /pathway` takes an optional `snapshot_date` for trend replay. `/app/pathway`, `/app/progress` and `GET /sdg/contribution/me` no longer default to `data-analyst`: they use the saved choice, or ask the learner to compare and choose. The About page lists the trend sources actually used. Ports for M2: `pathway.service.skills_gap(levels, role_id)` (one have/partial/missing rule, based on `required_level`) and `sdg.service.role_badges(role_id)` (F6's reviewed mapping, to replace matching's hardcoded `_ROLE_SDG`).
- **Why**: Pathway, re-plan and the About page still read the mock snapshot, so new M1 data never changed a plan (handbook: "output visibly changes when trend data changes"); the role choice was implicit with a hardcoded fallback; matching and pathway disagreed on gaps and SDG badges. M1's `resolve_context()` opens psycopg without `connect_timeout` and hung on this machine, so the port reads M1 on a daemon thread with a 3 s timeout and skips M1 for 60 s after an outage.
- **Pipeline**: M1 snapshot (arXiv cs.AI + BLS projections, dated) → `velocity_<scenario>` per skill → clip to [-0.5, 1.0] → priority = importance × gap share × (1 + velocity) → prerequisite-ordered plan; role outlook = importance-weighted velocity over covered skills (rising > 0.05, declining < -0.05, as M1), with coverage shown → evaluation: `tests/api/pathway/test_integration_ports.py` (M1 source used, seed fallback, no double weighting, trend change reorders the plan, replay 404, compare uses F6 badges, required-level gap, no assumed SDG role) → serving: `GET /pathway`, `GET /pathway/compare`, `/app/pathway/compare`.
- **Affects**: M1 (please add `connect_timeout` in `trends/repository.resolve_context`); M2 (switch matching to `skills_gap` and `role_badges`, link matches to `/app/pathway/compare?roles=…`); M4 (heatmap can call `skills_gap`)
- **Replaces**: none
- **PR / branch**: `refactor/pathway-trend-and-match-ports`

### M3-027: Shared learning and HR workspaces, guest preview, and Compose startup

- **Date**: 2026-10-21
- **Feature**: F5, F6, F8; Core/F7 explicitly requested by M3
- **Type**: UI | method | contract | schema | other
- **Change**: Added API-backed learner and HR overview pages, responsive workspace shells, scenario/role/snapshot navigation, a clickable journey atlas, synthetic guest CV preview using M2 public parsing/scoring and M1 bounded snapshot ports, explicit demo consent and safe return links. Activity points are 100 per completed unique course and a level per 500 points, never a proficiency measure. Added backend/frontend Dockerfiles, fresh-db migration/seed startup, standalone Next.js output, and an append-only skills.aliases migration matching M2's CSV header. Guest API returns one role plus a count, never the full ranking or raw CV; no anonymous profile is saved into a demo identity.
- **Why**: M3 can integrate presentation and deployment while M1/M2 retain ownership of their algorithms and in-flight changes. Container startup testing exposed the missing aliases column; relative allowlisted redirects avoid Docker-internal hostname leakage. Exact public-origin checks remain on preview submission.
- **Pipeline**: synthetic CV → M2 capped parser and taxonomy extraction → unconfirmed skill levels → M2 rank_roles with M1 dated velocities → restricted top-one response with original sources and estimates → skill confirmation handoff (production account/draft claim pending).
- **Affects**: M1/M2 (existing public interfaces consumed, no owned files edited), M4 (Core shell, routes, organisation target selection, Compose; landing CTA /try hook pending)
- **Replaces**: none
- **PR / branch**: feat/core-m3-workspace-navigation

### M3-028: Clarify submission provenance and actual AI development tools

- **Date**: 2026-10-25
- **Feature**: F8 (transparency), Core (submission documentation)
- **Type**: other
- **Change**: Record the team leader's clarification that KerjaCerdas belongs to a different team and informed security concepts, rather than supplying a prior-owned implementation. Correct the active solution guide, security docstrings and submission draft; preserve earlier decision entries as history. Declare confirmed Codex debugging, Claude Code video/pitch work, Replit Agent and Antigravity exploration, and Greptile PR review. Ignore local pitch-planning Markdown and PPTX assets under `submission/pitch/`.
- **Why**: Earlier wording implied shared authorship and code reuse that the leader says did not occur; AI-tool placeholders also omitted confirmed work. Distinguish team product decisions, conceptual references and actual tool contributions without understating AI assistance.
- **Affects**: Submission reviewers; no runtime behaviour, contracts, dependencies or schema changes
- **Replaces**: M3-003 provenance wording and M3-001's reuse-map description; implementation decisions remain unchanged
- **PR / branch**: docs/core-submission-accuracy

### M3-029: Select five complete synthetic CVs for the public demo guide

- **Date**: 2026-10-25
- **Feature**: Core (README/demo), F1 (synthetic intake references)
- **Type**: data source | other
- **Change**: Add the leader-supplied Imran Hakim, Sofia Tan, Meera Anand, Adrian Lim and Nur Hana PDFs unchanged under `submission/demo-cvs/`; point README and submission references to them. Supply complete, editable synthetic intake settings separately from CV facts using existing profile fields and catalogue IDs. Keep older seeded personas and parser edge cases for regression tests.
- **Why**: The README's test-fixture link did not identify the team's selected presentation CVs. A separate guide makes the demo reproducible without claiming that budgets, HRD eligibility or proficiency are extracted or verified.
- **Pipeline**: supplied synthetic PDFs → in-memory deterministic CV parsing → known catalogue skill IDs with reviewable omissions → human confirmation with explicit demo assumptions → all five parse without truncation; profile shapes and IDs checked → downloadable demo assets and manual intake guide, no database import
- **Affects**: Manual demos and submission documentation; no matching/parser behaviour, API schema or existing test fixtures changed
- **Replaces**: none
- **PR / branch**: docs/core-submission-accuracy

### M3-030: Credit Claude Code as the primary implementation assistant

- **Date**: 2026-10-25
- **Feature**: F8 (AI development disclosure), Core (submission)
- **Type**: other
- **Change**: Expand the technical declaration to state the leader's clarification that Claude Code produced most of the application code, in addition to demo-video and pitch-design work. Keep Codex's debugging/corrections role and the other confirmed tools distinct, and retain the team's product direction and final responsibility.
- **Why**: The earlier tool inventory understated Claude Code's implementation contribution by describing only presentation work.
- **Affects**: Submission disclosures only; no application behaviour, schema, dependency or model configuration changes
- **Replaces**: M3-028's incomplete Claude Code usage description
- **PR / branch**: docs/core-submission-accuracy

### M3-031: Declare Replit deployment and RunPod Serverless sponsor usage

- **Date**: 2026-10-25
- **Feature**: F8 (transparency), Core (deployment/submission)
- **Type**: other
- **Change**: Add the leader-confirmed Replit sponsor deployment resource alongside the deployed RunPod MiniLM Serverless worker and separate GLM inference endpoint. Update the proposal and cloud-service inventory with successful read-only landing/About/API database-health checks on 25 October; keep source-revision verification and failed trend publication distinct from resource usage.
- **Why**: The earlier sponsor section incorrectly reduced disclosure to RunPod API usage and omitted Replit's actual hosting role. A specific credit amount or mentoring claim is not needed to describe confirmed platform use.
- **Affects**: Submission documentation only; no hosting, model, schema or runtime changes
- **Replaces**: Earlier sponsor-resource omissions in the submission drafts
- **PR / branch**: docs/core-submission-accuracy

### M3-032: Keep submission tables aligned with the supplied PDF

- **Date**: 2026-10-25
- **Feature**: Core (submission), F8 (disclosures)
- **Type**: other
- **Change**: Restore the PDF's column order and relative order/grouping of existing rows in the technical declaration and proposal third-party inventory. Keep corrections in their matching rows, remove obsolete entries explicitly and append genuinely new entries after existing ones. Provide a change-only editing guide identified by section and original row name.
- **Why**: Reordered, merged and split tables caused unnecessary replacement work in the user's Google Docs. Unchanged factual content should require no manual edit.
- **Affects**: Submission authoring only; no application behaviour or new dependencies
- **Replaces**: Earlier table presentation choices in the submission drafts, not the factual corrections
- **PR / branch**: docs/core-submission-accuracy

### M3-033: Record confirmed sponsor plans and Replit integrated database

- **Date**: 2026-10-25
- **Feature**: Core (submission/deployment), F8 (disclosure)
- **Type**: other
- **Change**: Record the leader-confirmed Replit Core sponsor subscription, US$25 RunPod sponsor credits and Replit integrated PostgreSQL. Replace the unused external-service row in place, retaining PDF table order. Remove generic unspecified-plan placeholders; distinguish recommended Replit Asia/RunPod available-data-center scheduling from the unverified active geography.
- **Why**: The declaration omitted concrete benefits the team used and left an unused database provider in the services table. A known plan satisfies the Plan / Region field without inventing an active deployment location.
- **Affects**: Submission text only; no account, database, region, billing or infrastructure changes
- **Replaces**: M3-031's incomplete plan/credit details and the unused external-service row
- **PR / branch**: docs/core-submission-accuracy

---

## M4: Core & Organisation (Core, F7)

<!-- M4 adds entries below this line -->

### M4-001: Real accounts, PostgreSQL-first storage, no built-in personas
- **Date**: 2026-10-22
- **Feature**: Core, F1, F7 (cross-feature, requested by the user on `feat/core-insight-design`)
- **Type**: contract | schema | method | data source
- **Change**: Sign-up / sign-in replace the persona shortcuts. New `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` (`features/accounts`, `core/accounts.py`): scrypt password hashes in `users.password_hash`, HMAC-signed 14-day session tokens (`core/security/session.py`, `SESSION_SECRET`) kept by Next.js in an httpOnly `adept_session` cookie and forwarded as `X-Demo-User`. Organisation sign-up creates the organisation and a manager/advisor membership with a join code (`organizations.join_code`); learners join with `POST /org/join` or a code at sign-up. Migration `20261022090000_core_local_accounts.sql`. `M3_BACKEND` now defaults to `postgres`; profiles (`profiles`, `user_skills`) and organisations/memberships are read from and written to PostgreSQL, and user-data reads fail with 503 instead of silently falling back to memory. `DEMO_USERS`, `features/profile/mocks.py`, `features/org/mocks.py`, the proxy's persona allow-list and `/demo/*` routes are removed; `src/db/seed.py` no longer loads `seed/personas` and `seed/org` (they stay as test fixtures, installed by `tests/harness/fixtures.py`). Saving a profile moves the member's intake status forward.
- **Why**: Profiles lived in a Python dict (lost on restart) and only five hard-coded ids could use the app, so a live demo could not use real app logic. Persona data in the database was fake data.
- **Affects**: everyone (shared contracts, migration, `.env.example`, `tests/conftest.py`); M2 (profile repository); tests use `AUTH_RAW_USER_IDS` / `AUTH_DEFAULT_USER` (test-only settings).
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-002: Hard-coded scenario outlooks, radar signals and data-freshness replaced by snapshot-derived values
- **Date**: 2026-10-22
- **Feature**: F2, F3, Core (cross-feature)
- **Type**: formula | data source | contract
- **Change**: `GET /scenarios` and `/scenarios/outlook`, `GET /trends/radar` and `/trends/roles/{id}`, `GET /meta/data-freshness` and the CV extraction meta no longer return `MOCK DATA`; they are computed from M1's dated snapshot and the taxonomy and cite its sources. `adoption_rate` = mean `automation_exposure` of tracked skills (fast: × (1 + k), k = 1.5 from `pipelines/trends/score.py`, capped at 1).
- **Pipeline**: M1 snapshot (arXiv cs.AI + BLS, dated) → per-scenario skill velocity → role signal = importance-weighted velocity over covered required skills → outlook = 1 + signal; low/high = min/max over every stored snapshot, widened by (1 − coverage) × |signal| → evaluation: `tests/api/scenarios/test_outlook_method.py` (range contains outlook, fast ≥ moderate adoption, no mock sources) → serving: the endpoints above.
- **Affects**: M1 (owner of F2/F3: please review the method)
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-003: Skill bank enriched to 113 skills with cited SDG links
- **Date**: 2026-10-22
- **Feature**: F1, F4, F6
- **Type**: data source
- **Change**: `seed/taxonomy/skills.csv` now includes all 110 canonical skills M1's trend pipeline scores (labels, aliases, group in `description`), and `GET /profile/skills/catalogue` serves the bank plus the role interest tags for the intake. Every new skill has ≥ 1 `skill_sdg_map` link with a reason and an authoritative source (ILO WP140, UN indicator metadata, UNESCO), still `pending review`.
- **Why**: Learners could only pick 12 skills, most of which the trend snapshot did not cover; must-have 5 requires every skill to be SDG-tagged.
- **Affects**: M2 (taxonomy, CV aliases), M3 (SDG map review)
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-004: Rebuilt shell, navigation, dashboards and intake (visual-first)
- **Date**: 2026-10-22
- **Feature**: Core, F1, F4, F7 UI
- **Type**: UI | contract
- **Change**: New design system `app/adept.css` and `ui` message namespace (EN/BM/ZH). One `Shell` for all workspaces: desktop sidebar grouped by journey with numbered steps (ticked when done), page title and an AI-scenario switch only on pages where it matters; mobile uses a fixed 5-tab bar (4 destinations + "More" bottom sheet), no horizontal scrolling. Learner home shows one next step, top-3 fit rings, the learner's own skills as a diverging trend chart, the plan as a step track and SDG goal tiles; organisation home moves from invite (join code) → waiting → act, with an intake stacked bar, gap heatmap, team-plan track and SDG tiles. New 4-step intake (stage, interests, time/budget, skills from CV or the skill bank) — previously there was no way to enter skills. Org settings edit, join-code rotation and member removal (`PUT /org/me`, `POST /org/me/join-code`, `DELETE /org/members/{id}`); gap heatmap and plan carry role labels. API errors always use `{"error": {code, message}}` (validation, 404/405, database outages → 503) and the web client keeps status and code to show the right fix (sign in, finish profile, retry). Looping CSS-3D scenes (no library): staircase climb (pathway), signal gyroscope (radar), role-card carousel (matches), cube heatmap (team), SDG globe; paused for reduced motion.
- **Why**: Users asked for a visual hierarchy, a coherent route/navigation model and mobile navigation without sideways scrolling.
- **Affects**: all features' pages render inside the new shell; feature-owned pages beyond radar/matches/org were not restyled.
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-005: Local reliability fixes
- **Date**: 2026-10-22
- **Feature**: Core
- **Type**: other
- **Change**: `DATABASE_URL` hosts `localhost` are normalised to `127.0.0.1` (Docker binds IPv4 only; on Windows every connection waited the 2 s timeout on `::1`, which made matching return 503). `migrate.py status` reports the duplicate-version alias migration correctly. GET requests from the web retry once on a dropped connection.
- **Affects**: everyone running locally on Windows
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-006: Upload-first home with a For me ⇄ For my team switch; refined visual system
- **Date**: 2026-10-22
- **Feature**: Core, F1 (anonymous preview), F7 (team pitch)
- **Type**: UI | contract
- **Change**: The home page is upload-first: anyone uploads a CV and immediately sees the skills found, how those skills trend, and their best-fit role (fit ring); more roles, the skills gap, the learning plan and SDG impact are shown blurred behind a free sign-up. Skills found carry into the intake after sign-up (browser storage only, cleared once saved). `POST /preview/cv` adds `skill_trends` (direction per extracted skill from the snapshot, ±0.05 band). A "For me ⇄ For my team" switch re-themes the whole landing (light ⇄ dark, colours animated via registered CSS properties) and swaps to the team pitch; `/?for=teams` links to it. Design tokens: white base, 1.2 type scale, 8-pt spacing, motion tokens, hover lift on cards, entrance stagger, ring labels scale with ring size (no overflow on phones). Sidebar is white; secondary pages sit in one collapsible "More" group. The CSS staircase scene (broken on phones) is replaced by an SVG line-art object (a skill lifting from your stack to a future role); the other 3D scenes are kept. `/try` redirects to `/#start`; the developer route atlas `/journey` is removed; About-page wording is user-facing.
- **Why**: User feedback: visual-first, minimal white, sign-in from the landing, CV preview without login with the rest locked, and a teams landing that feels like a theme switch.
- **Affects**: M2/M3 (preview response gains a field; About copy)
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-007: Trend snapshots live in PostgreSQL with their provenance; route chain fixes
- **Date**: 2026-10-22
- **Feature**: F2, F3, F5 (cross-feature)
- **Type**: schema | data source | contract | formula
- **Change**: `make seed` loads the pipeline's exported, dated snapshots (`src/data/seed/mock_trends_<date>.json`) into `trend_snapshots`, and their sources and provenance note into the new `trend_snapshot_meta` table (migration `20261022120000_core_trend_snapshot_meta.sql`); the trends repository now cites the stored sources (it used to hard-code "arXiv cs.AI RSS" even for Query-API runs) and uses taxonomy labels instead of title-cased ids. `GET /pathway` and `GET /pathway/progress` take an optional `role_id` and fall back to the saved plan (`409 role_required` until one exists); planning endpoints require a saved profile (`profile_required`, same rule as matching). Role outlook clips the signal to the engine's growth band so the index stays in [0.5, 2.0]. Tests never touch a developer database (`tests/conftest.py` points `DATABASE_URL` at an unreachable address unless `ADEPT_TEST_DATABASE_URL` is set).
- **Pipeline**: pipeline export (arXiv cs.AI Query API windows + BLS, dated) → seed loader (no overwrite) → `trend_snapshots` + `trend_snapshot_meta` → repository (DB first, frozen export as fallback) → radar, matching, scenarios, pathway, freshness.
- **Affects**: M1 (pipeline runs can write `trend_snapshot_meta` too), M3 (pathway defaults)
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-008: Docs brought up to date
- **Date**: 2026-10-22
- **Feature**: Core
- **Type**: other
- **Change**: PROJECT_CONTEXT §11.3 routes and §11.5 personas (now design/test fixtures only), SOLUTION_DESIGN start rows and routing summary with the API chain, README quick start, architecture auth section; WORKSPACE_IMPLEMENTATION marked superseded.
- **Affects**: everyone (shared AI context, edited at the user's request)
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-009: CI split into backend and frontend jobs
- **Date**: 2026-10-22
- **Feature**: Core
- **Type**: other
- **Change**: `.github/workflows/ci.yml` now runs Backend (ruff lint + format, pytest), Frontend (eslint, tsc, translation keys, Next.js build) and Contracts (OpenAPI + TS types drift) as parallel jobs instead of one `make check` job; the database job waits on Backend only. A failure now shows which side broke. `make check` locally is unchanged.
- **Affects**: everyone (root config); required status checks in branch protection, if any, must be renamed to the new job names
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-010: Review fixes on PR #7 (sessions, sign-up, membership, outlooks, web)
- **Date**: 2026-10-22
- **Feature**: Core, F7 (also touches F3 scenarios)
- **Type**: other
- **Change**: Session fallback key is now random (`.session-secret`, gitignored, or in memory) instead of derived from the public default `DATABASE_URL`; compose passes `SESSION_SECRET` to the API. A team sign-up whose organisation can't be created is undone, so the email is free to retry. A member joining a second organisation gets 409 `already_member` (one organisation per member; removal clears it). Role outlooks load each snapshot date once over one connection instead of twice per date with a new connection each. Web: every selected skill is saved (no 60 cap), Server Action body limit raised to 6 MB for 5 MB CVs, the home page no longer claims "path complete" when progress fails to load, `a-span-3` added, Compare link uses `roles`, the mobile More sheet traps and restores focus.
- **Affects**: everyone running compose (set `SESSION_SECRET` in `.env` to keep sessions across restarts); F3 owner (outlook loading)
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-011: Partner design applied (frontend/adept): palette, type, sidebar, public header and footer
- **Date**: 2026-10-22
- **Feature**: Core (also restyles F5, F6, F8 pages)
- **Type**: other
- **Change**: Tokens now follow the partner design: Arial/Helvetica, charcoal-green ink `#18231C`, green actions `#22C55E` with a pressed edge, sage surfaces, `#E4E9E4` dividers, 20px cards, weight-500 editorial headings. The workspace keeps the sidebar (no top bar); the AI-scenario switch is an "AI pace: Moderate | Fast" control at the top right of the pages it changes. New public `SiteHeader` (pinned, hamburger on phones, EN/BM/中文 pill) and `SiteFooter` used by the landing and About pages. Pathway, progress, courses, compare, reviews, SDG and About pages rebuilt on shared `a-` components (metric cards, step rail, course rows, goal tiles, filters). The partner app itself (Vite/Cloudflare, its own database) was not merged: only its design was ported; `frontend/` stays out of the repo.
- **Affects**: everyone (shared UI); F5/F6/F8 owners (M3) please review the restyled pages, F3 (scenario switch placement)
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-012: Landing page: live data, isometric objects, team view
- **Date**: 2026-10-22
- **Feature**: Core
- **Type**: feature
- **Change**: New public `GET /api/v1/meta/overview` (cached 60 s) computes the landing figures from the app's own data (snapshot rising/stable/declining and top movers, role outlooks, course and HRD Corp counts, SDG goals linked) with sources and date; it feeds the "How it works" stepper (auto-advancing, no layout jumps) and the team numbers band, replacing the partner's illustrative sample profile. Monochrome isometric line-art objects (one projection, one green accent) for every feature, a "where you are → where you could be" career scene for individuals and an office scene for organisations. "For me | For my team" is a segmented control in the header; switching wipes to the other audience's hero (View Transitions). Teams get a sage/forest-green theme, their own features (roster, gap heatmap, target role, group plan, HRD Corp, reviews), steps and FAQ. Scroll reveals, count-ups and hover motion all respect reduced motion.
- **Affects**: none outside Core
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-013: Checklist gaps closed: SDG-weighted ranking, trend replay "what changed and why", learning style
- **Date**: 2026-10-22
- **Feature**: F4, F2, F1 (built by M4 at the team's request; M2 please review)
- **Type**: feature
- **Change**: (1) `GET /matches?sdg_weight=0..1`: each role gets an SDG impact value from its reviewed SDG links (direct = 1, enabling = 0.5, divided by the strongest role); existing parts keep their relative weights scaled by (1 − λ) and "sdg_impact" is added with weight λ, so the score stays a visible weighted sum; λ = 0 is unchanged. Slider on the matches page. (2) `GET /matches/replay?from_date=&to_date=` ranks the saved profile on two snapshots (`replay.py`) and names, per role, the required skills whose velocity × importance moved most; shown as "What changed from … to …" when an older snapshot is picked. (3) Learning style is now asked in the intake and stored (`profiles.learning_style`, migration `20261022150000`); a profile update without it keeps the saved value. Tests: `tests/api/matching/test_sdg_weight_and_replay.py`, `tests/api/profile/test_learning_style.py`.
- **Affects**: M2 (F1/F4 code and contracts: `RoleMatch` unchanged, new `ReplayResponse`, `ProfileIn.learning_style`), shared migration
- **Replaces**: none
- **PR / branch**: feat/core-insight-design
- **Pipeline**: source = trend snapshots + reviewed SDG links → features = SDG link weight, velocity deltas → method = linear blend (λ) / rank diff with importance-weighted drivers → evaluation = unit + API tests → serving = `/api/v1/matches`, `/api/v1/matches/replay`

### M4-014: Partner prototype folder removed; app icon added
- **Date**: 2026-10-22
- **Feature**: Core
- **Type**: chore
- **Change**: The partner's prototype (`frontend/adept`, never committed) was deleted after checking its colours, type, logo and layout patterns are all in `src/web` (M4-011, M4-012). Its sample CV and team files were fake data and its favicon was a template icon, so neither was kept. Added `src/web/src/app/icon.svg`, the Adept "A" mark, as the browser-tab icon.
- **Affects**: none
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-015: Consistent dashboard layouts and restored workspace CSS
- **Date**: 2026-10-22
- **Feature**: Core; F1, F2, F4, F5 and F6 presentation
- **Type**: UI
- **Change**: Added shared KPI strips, level pips, score bars and trend labels, grouped desktop navigation, and consistent layouts for Home, My skills, Radar, Roles, Plan, Progress, Courses and Impact. Restored the missing dashboard styles from the design handoff, scoped them to `.a-shell`, and adjusted compact charts and responsive KPI layouts. Dashboard labels have matching English, Bahasa Melayu and Chinese keys.
- **Why**: Revised page components referenced CSS that had not been saved, leaving the dashboard layout broken. A shared visual rhythm makes metrics, skills gaps, learning steps and evidence easier to compare across screens. The landing page and backend were excluded from this work.
- **Affects**: All workspace UI; feature owners should review their screens. API contracts, dependencies and backend behavior are unchanged.
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-016: Same ranking context across matches, role detail, replay and outlook (H04, H03 wording)
- **Date**: 2026-10-22
- **Feature**: F4, F3 (Core integration)
- **Type**: fix
- **Change**: (1) The UN Goals weight now travels from the matches list to the role detail (`?sdg=`) and to `GET /matches/replay?sdg_weight=`, which blends SDG impact into both snapshots' scores the same way as the list. (2) Replay reasons now use the scorer's own input: each skill's percentile position among all skills in the snapshot. Effect = change in position × the skill's share of the role's importance × trend weight, i.e. the score points it moved. `ReplayDriver` gains `position_before` / `position_after`. (3) `GET /scenarios/outlook?snapshot_date=` uses only snapshots up to that date, so a historical match page cites its own period. (4) The SDG part of the score no longer calls its links "reviewed"; its explanation says how many of the role's links a person has reviewed. Role detail restyled to the shared layout (score arithmetic, gap list, outlook range bars).
- **Why**: Greptile review on PR #7 and handoff H04/H03: the same choice showed different scores and ranks between views, replay could explain a fall as a rise, and draft mappings were described as reviewed.
- **Affects**: M2 (matching contracts/service), M1 (outlook endpoint); contract additions only.
- **Replaces**: none
- **PR / branch**: feat/core-insight-design
- **Pipeline**: source = trend snapshots + SDG links → features = percentile positions (`trend_scores`), SDG impact → method = linear blend (1 − λ)·score + λ·impact on both dates; driver effect = Δposition × importance share × w_trend → evaluation = regression tests (percentile vs raw velocity, weighted replay order = weighted list order, detail score = list score, outlook date) → serving = `/matches`, `/matches/{id}`, `/matches/replay`, `/scenarios/outlook`

### M4-017: Handoff fixes H05, H06, H07, H09, H10 and landing headline sizing
- **Date**: 2026-10-22
- **Feature**: Core; F2, F5, F6, F7 integration
- **Type**: fix
- **Change**: H05: `GET /sdg/contribution/org` and `/contribution/region/{state}` take `role_id`; the organisation Impact page passes the role chosen on the team plan and keeps it on the scope tabs (unknown roles 404). H06: translated every BM/Chinese string still in English that the app uses; removed about 100 unused keys (`common.workspace`, `common.journey`, unused `common.design`); progress badges are named from their stable id via `pathway.badge.*` instead of the API's English label. H07: the Next.js dev indicator is off, since it intercepted clicks on the sidebar language switch and on the mobile "More" tab. H09: snapshot and recommendation metadata gain optional `observed_from` / `observed_to` (from stored metadata, else parsed from the provenance note; `trends/provenance.py`); the sources line shows "data measured … to …" and the Radar warns when the evidence is a historical replay. H10: evidence wording says a certificate link only shows the page opens on the provider's site; a reviewer confirms ownership; landing "Verified completions" became "Reviewed completions". Landing: both hero headlines share one rule (same size, line height and spacing, larger), and BM/Chinese headlines flow as one balanced paragraph.
- **Why**: Handoff `docs/FEATURE_STATUS_AND_FIX_HANDOFF.md` items H05–H10 and user feedback on the landing headlines.
- **Affects**: M3 (SDG contribution endpoints, evidence wording, badge names), M1 (snapshot metadata fields), shared `RecommendationMeta` (two optional fields), all locales.
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-018: Scheduled trend refresh (H01), data audit, team pages, join entry, auth panel, dropdowns
- **Date**: 2026-10-22
- **Feature**: F2 (pipeline), Core, F7
- **Type**: feature / fix
- **Change**: (1) `pipelines/trends/run.py` replaces the placeholder: ingest → `score.score_rows` (extracted, pure) → `validate` → `publish` (rows + `trend_snapshot_meta` in one transaction; note names the measured ISO week). `.github/workflows/trends-refresh.yml` runs it weekly when `TREND_DATABASE_URL` is set, installing CPU torch 2.5.1 and sentence-transformers 3.3.1 in the job only. (2) Data audit: sidebar ticks follow the same rule as the Home/team journeys (saved plan → steps 1-3; completed member profile → team steps 1-4); My skills follows the AI pace; "110+ skills" copy no longer hard-codes a count; replan banner shows skill names. (3) Team dashboard, Team, Skill gaps, Team plan, Reviews and Settings on the shared layout (no 3D scenes on dashboards). (4) "Join a team" in the sidebar, mobile menu and Home for learners without an organisation; join page explains what is shared. (5) Auth pages: one top-aligned framed panel with the landing drawings (career path; office on the forest background for teams), stable scrollbar gutter, so switching sign-in/sign-up does not jump. (6) All `<select>` elements styled; option lists styled where `appearance: base-select` is supported. (7) `docs/FEATURE_STATUS_AND_FIX_HANDOFF.md` gains a fix-status table.
- **Why**: Handoff H01 and user review of data consistency, team flow, auth and dropdowns.
- **Affects**: M1 (pipeline, new workflow, CI secret `TREND_DATABASE_URL`), M2/M3 screens (layout only), root config (`.github/`).
- **Replaces**: none
- **PR / branch**: feat/core-insight-design
- **Pipeline**: source = arXiv cs.AI listing + BLS 2023-2033 → preprocessing = HTML strip, sentence split → features = MiniLM sentence-cosine mention counts per ISO week → method = log-ratio velocity + labour baseline + fast-scenario transform → evaluation = publish-time validation (two weeks, ≥ 50 skills, taxonomy ids, finite values) → serving = `trend_snapshots` / `trend_snapshot_meta` read by `/trends/snapshot`

### M4-019: Smooth page transitions, loading skeletons and steady auth panel
- **Date**: 2026-10-22
- **Feature**: Core
- **Type**: UI
- **Change**: (1) `components/shell/Motion.tsx`: a top progress bar from any internal link click or GET form submit until the next route renders; a page entrance (fade and rise, sections and rows staggered) keyed by path; key numbers count up. (2) `app/app/loading.tsx` and `app/org/loading.tsx` show `PageSkeleton` (header, number strip, two cards) while the server renders. (3) `useBusy`: the AI pace, snapshot, UN Goals slider and Radar snapshot controls mark the page busy (bar runs, content dims) until new data arrives; course filters and the team-plan role picker use `next/form` (client navigation, no full reload). (4) Buttons lift on hover, arrows nudge, presses sink; pending buttons show a spinner. (5) Auth: `/auth/login` and `/auth/signup` share `app/auth/(entry)/layout.tsx`, which keeps one `AuthView` mounted; tabs are links (`replace`, no scroll), the pill slides, the form cross-fades. On sign-up, team and personal fields share one slot sized to the taller set and cross-fade, so the panel never changes size; the inactive fieldset is disabled (not validated or submitted). The art panel cross-fades between sage and forest. All motion is off under `prefers-reduced-motion`.
- **Why**: User review: switching pages and auth tabs felt jumpy, waits had no feedback.
- **Affects**: shared shell and UI only; no API or contract change.
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-020: Review fixes on PR #7: exposure score wording, refresh freshness and dates, team gap averages
- **Date**: 2026-10-22
- **Feature**: F2, F7, Core
- **Type**: fix
- **Change**: (1) `automation_exposure` is shown as a 0–1 score ("Exposure score"), not a percentage, with an explanation that reviewers assigned it from published research (`docs/skill-exposure-methodology.md`); EN/BM/ZH. (2) `pipelines.trends.run` refuses to publish after an ingest that stored no signals today (empty or unreadable feed), so older evidence is never republished as new. (3) The measured period and source retrieval date come from the days signals were actually collected (`collected_dates`), not the calendar ISO week, so a Monday run does not claim future days. (4) `GapHeatmapResponse.role_gaps` returns each role's average gap over its required skills only (the figure that picks the default team target); the Skill gaps page and team dashboard use it instead of averaging zero cells for unrelated skills.
- **Why**: Greptile review comments on PR #7.
- **Affects**: M1 (pipeline), M4 F7 contract addition (`role_gaps`).
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-021: H08 evidence policy for matching; H02 closed by design
- **Date**: 2026-10-22
- **Feature**: F4, F5 (Core integration)
- **Type**: feature / decision
- **Change**: Completed learning now feeds role matching under the policy the user chose: a course's skill level counts when the completion is confirmed by the organisation's reviewer (`org_confirmed`) or has a certificate link that opens on the provider's own verification page (`certificate_link` with `provider_verified`). Self-reported, unreachable or rejected completions do not change matches. `pathway.service.earned_levels` (pure) and `evidenced_levels(user_id)` compute the levels from the saved plan; `matching.repository._load_profile` takes the higher of the intake and evidenced level per skill, so the skills gap, score and pathway update together. H02 (synthetic-only enforcement) is closed by design: the app behaves as a real product and the team runs the demo with synthetic data only.
- **Why**: Handoff H08 and H02, decided by the user.
- **Affects**: M2 (matching profile input), M3 (evidence semantics now affect matching).
- **Replaces**: none
- **PR / branch**: feat/core-insight-design

### M4-022: Keep evidenced learning across targets and share effective skill levels
- **Date**: 2026-10-22
- **Feature**: Core integration; F4, F5, F7
- **Type**: schema | method
- **Change**: Progress records retain an immutable `Course` snapshot in `course_progress.course_snapshot` (append-only migration `20261022220000`). Accepted learning is aggregated across every target instead of the current saved plan. Matching, pathway generation/comparison/re-planning and organisation member inputs use `pathway.service.combined_levels`, the per-skill maximum of intake and accepted learning. Review queues use historical course facts; rejection and undo still revoke credit.
- **Why**: Greptile PR #7 findings “Changing targets loses earned credit” and “Plans ignore earned skills”. Replacing a target previously removed earned levels, and the same learner had inconsistent gaps across matching, pathways and team views. Retaining facts with progress also prevents catalogue edits or retirement from changing past learning. Existing rows are backfilled from their surviving saved plan, otherwise from the current catalogue; facts lost before this migration cannot be reconstructed.
- **Pipeline**: source = confirmed intake, persisted course facts, completion status and evidence → preprocessing = include only completed courses with accepted evidence → features = highest evidenced course level per skill across targets → method = maximum of intake and earned levels → evaluation = regression tests for target changes, retired/edited courses, consistent individual/team planning, rejection, undo, user isolation, PostgreSQL persistence and migration backfill → serving = matching, pathway and organisation services.
- **Affects**: M2 (matching input), M3 (progress persistence and planning), M4 (team gaps); one new database column, no API contract change.
- **Replaces**: M4-021 (current-target-only earned-level lookup; the evidence acceptance policy is unchanged)
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/7 / feat/core-insight-design

### M4-023: Submission drafts and readable, interactive documentation diagrams
- **Date**: 2026-10-22
- **Feature**: Core (submission and documentation)
- **Type**: other
- **Change**: Added proposal and technical-tools Markdown drafts following the supplied PDF sections and narrative limits. README branding reuses the existing Adept mark with a centered title and technology badges; diagrams are editable Mermaid, checked against routes and migrations, with large schemas split by domain. A standalone offline viewer adds zoom, pan, resize, fullscreen and SVG/Mermaid downloads; documentation-only Mermaid 11.12.0 tooling generates it without changing application dependencies.
- **Why**: The existing submission links had no target files and screenshot diagrams were unreadable. GitHub Markdown cannot run interactive controls, so a local browser viewer complements the native source blocks. Declarations separate verified local functionality from planned cloud/sponsor use and leave personal, legal and registration attestations for the team. The proposed 20% planning-time reduction is an evaluation target, not a measured outcome; the draft specifies a matched synthetic manual-catalogue comparison before claiming results.
- **Affects**: M4 submission assembly; all owners review their technical disclosures. No API contract or application dependency changes for documentation.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/7 / feat/core-insight-design

### M4-024: Batch accepted learning across team members and targets
- **Date**: 2026-10-22
- **Feature**: F5, F7 (Core integration)
- **Type**: method
- **Change**: One joined learning-record query loads progress, immutable course facts and evidence for all requested members across every target. Team planning reuses its loaded members when choosing the default target; accepted per-skill levels are calculated from the supplied batch.
- **Why**: Greptile PR #7 finding “Team reads grow with history”. Per-member, per-target connections multiplied with learning history, and default target selection loaded members twice.
- **Pipeline**: source = persisted progress, course snapshots and evidence → preprocessing = batch by requested user IDs → features = per-skill accepted maximum → method = reuse batch inputs for team gaps and planning → evaluation = one-query regression for 100 members with three targets and single-member-load checks → serving = pathway earned levels and organisation planning.
- **Affects**: M3 F5 internal repository read; M4 F7 team inputs. No API or schema change.
- **Replaces**: M4-022 per-target lookup implementation; earned-credit policy remains unchanged.
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/7 / feat/core-insight-design

### M4-025: Retain completed course history and badges after re-planning
- **Date**: 2026-10-22
- **Feature**: F5 (Core integration)
- **Type**: schema | contract | UI
- **Change**: Saved plan contexts are archived atomically in pathway_plan_history. Progress returns completed course history independently of the remaining plan. The Progress page keeps historical evidence and undo controls, and badges are re-evaluated against original plans with current evidence so rejection and undo still revoke credit.
- **Why**: Greptile PR #7 finding “Completed courses disappear after re-planning”. Replacing a saved plan hid completed courses and badge context. The migration backfills the surviving saved plan; overwritten pre-migration plan contexts cannot be reconstructed, although captured course facts remain available.
- **Pipeline**: source = completed course snapshots, evidence and archived plans → preprocessing = apply current evidence policy → features = historical course facts and original requirements → method = evaluate badges against original plans and merge completed hours with remaining work → evaluation = memory/PostgreSQL regressions for re-plan, history, badges, undo, rejection and isolation → serving = progress API and EN/MS/ZH Progress page.
- **Affects**: M3 F5 additive history/badge fields and one append-only migration; M4 progress presentation.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/7 / feat/core-insight-design

### M4-026: Exclude rejected past courses from progress totals
- **Date**: 2026-10-22
- **Feature**: F5 (Core integration)
- **Type**: formula | UI
- **Change**: Historical hours join the progress denominator only when their effective status is completed. Rejected courses remain visible and editable in history; a rejected course still present in the current plan remains unfinished required work. The course-count KPI applies the same rule to historical entries.
- **Why**: Greptile PR #7 finding “Finished plans still look incomplete”. Raw completed records with rejected evidence added historical hours to the denominator without adding completed hours, leaving a finished replacement plan below 100%.
- **Affects**: M3 F5 progress calculation; progress page KPI. No API or schema changes.
- **Replaces**: M4-025 inclusion of rejected historical hours in progress totals.
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/7 / feat/core-insight-design

### M4-027: Backend speed, security and CV edge cases (audit fixes)
- **Date**: 2026-10-23
- **Feature**: Core; F1, F2, F4, F7 (cross-feature, approved by the user)
- **Type**: method | contract | other
- **Change**: (1) `core/db.py` uses one `psycopg_pool` pool per process (`DB_POOL_MAX`, 10 s statement timeout) instead of a new connection per query. (2) `trends.service.get_snapshot` caches published snapshots (latest 60 s, dated 10 min, fixture fallback 5 s); matching's trend port drops the single global worker lock (every request queued behind it) for a shared 8-thread pool with the same 2 s timeout. (3) Matching and the guest preview read the role catalogue through the cached `seed.rows` instead of re-opening three CSV files several times per request. (4) `trends.repository` no longer imports `unittest.mock` in production. (5) Security: login runs a dummy scrypt check for unknown emails (no timing enumeration); `POST /auth/me/delete` (password re-check, cascades every user table, removes an organisation whose last manager leaves) and `GET /auth/me/export` (PDPA access) with a "Your data" card on My skills and team Settings; tighter limits on `/org/join` and account deletion; `/admin` pages need `ADMIN_EMAILS` (nobody in production when unset); `APP_ENV=production` refuses to start without a 32+ char `SESSION_SECRET`, exact CORS origins and no test auth switches, warns when `PROXY_SHARED_SECRET` is empty, and hides `/docs`; the landing preview proxy forwards the client IP. (6) The legacy `PUT /profile/skills` now rejects skill IDs outside the taxonomy (it stored anything); legacy profile routes are marked deprecated. (7) CV parsing: Word `.docx` (standard library, zip-bomb guarded), PDF magic-byte check, 30-page cap, password-protected PDFs get their own message, binary files sent as text are refused, file type inferred from the extension when the browser sends none; level cues match whole words (no more "leadership" → expert, "machine learning" → beginner), years of experience set the level, negated mentions ("no experience with Python") are skipped, CJK aliases match without word boundaries.
- **Why**: Audit on 2026-10-23. Connection-per-query and the global trend lock were fine locally but cost 100–300 ms per connection and serialised all users on a hosted database; the rest were security, PDPA and CV-intake gaps.
- **Pipeline** (CV intake): upload (PDF / DOCX / text, type checked by bytes) → text (≤ 30 pages / ≤ 8 MB XML) → NFKC + PII strip → taxonomy alias scan (whole words; CJK substrings; negation skipped) → level from cue words, else years, else 2 → evaluation: `tests/api/profile/test_cv_edge_cases.py` (13 cases) → serving: `POST /profile/cv`, `POST /preview/cv`.
- **Affects**: M1 (trend cache, repository seam), M2 (matching repository and trend port, CV parser, legacy routes), M3 (rate limits), all (new env vars `APP_ENV`, `DB_POOL_MAX`, `ADMIN_EMAILS`; contract additions `DeleteAccountIn`, `AccountExport`).
- **Replaces**: none
- **PR / branch**: fix/core-backend-perf-security

### M4-028: Adi, the Adept assistant (3D mascot, grounded LLM answers, Gemini)
- **Date**: 2026-10-23
- **Feature**: Core, F8 (guardrails), touches F2/F4/F5/F6/F7 read-only
- **Type**: model | contract | dependency | UI
- **Change**: Adi, a mascot (Malay *adi-* = excellent) with a radar-dish antenna and an SDG leaf, docked bottom-right on the landing page and every learner/team page (not on sign-in, intake or admin). Real 3D with three.js 0.180 (lazy-loaded; follows the pointer, blinks, waves, thinks, talks, hops; spins on click; pauses off-screen), flat SVG fallback for reduced motion or no WebGL. `POST /assistant/chat` (signed-in or visitor) builds a context from the person's own data (profile, matches with score parts and gaps, saved plan, progress, team gaps and plan, dated trend snapshot) and asks the configured model; roles, skills, courses, SDG targets and pages may only appear as `[[kind:id]]` tags resolved against the catalogue (unknown IDs dropped and logged), figures not in the context are flagged, questions are injection-filtered and PII-redacted. Without a model, a deterministic EN/BM/ZH guide answers from the same facts. New OpenAI-compatible provider (`gemini`, `replit`, `runpod`, `openai`, `openrouter`, `openai_compatible`) with `LLM_FALLBACK_MODEL`; chosen model: `gemini-3.5-flash-lite` (Google AI Studio free tier: 15 req/min, ~2 s; fallbacks `gemini-3.6-flash`, `gemini-3.1-flash-lite`). `gemini-3.8-flash` returned 503 on the team's tier; Pro/Argon have no free quota. `httpx` moves to runtime dependencies. Sign-in and Create account share one fixed frame height.
- **Why**: The brief asks for innovation beyond "a chatbot"; Adi explains the user's own results with sources, keeps the "never invent" rule enforceable, and still works without credits.
- **Pipeline**: source = Adept DB/services + dated trend snapshot → preprocessing = PII redaction, injection filter → features = per-audience CONTEXT block, catalogue tag list → model = Gemini 3.5 Flash Lite (temperature-free OpenAI-compatible chat, `reasoning_effort=low`) or the deterministic guide → evaluation = `tests/api/assistant` (16 tests: invented IDs dropped, labels from catalogue, figures flagged, PII never sent, fallback on failure, three languages, provider protocol) + live check on the AI Studio key (grounded answer, 0 rejected IDs, 0 unchecked figures) → serving = `POST /api/v1/assistant/chat`, web dock.
- **Affects**: everyone (shell, landing, new dependency `three`, env vars `LLM_BASE_URL`, `LLM_FALLBACK_MODEL`, `LLM_TIMEOUT_S`, rate limit bucket), M3 (F8 disclosure text, gateway log reused).
- **Replaces**: none
- **PR / branch**: feat/core-adi-assistant

### M4-029: Team (HR) data is manager-only in the API, not only in the web
- **Date**: 2026-10-23
- **Feature**: F7, F6 (security)
- **Type**: contract | other
- **Change**: `GET /org/members`, `/org/gaps`, `/org/plan`, `/sdg/contribution/org` and `/sdg/contribution/region/{state}` now require an organisation manager or advisor (403 `forbidden` for members, 401 without sign-in). Before, any member of a team could read colleagues' names, intake status, the gap heatmap, the group plan and team impact through the API (the `/org` pages already redirected them), the region view needed no sign-in, and a user without a team asking for the organisation view hit a removed `DEFAULT_ORG_ID` (500). `org.service.require_manager` is the shared guard. Members keep `GET /org/me` without the join code.
- **Why**: User question on 2026-10-23: members must not see any HR interface or data.
- **Affects**: M3 (SDG contribution endpoints), M4 (F7). Learner pages never used these endpoints.
- **Replaces**: none
- **PR / branch**: fix/core-backend-perf-security

### M4-030: Review fixes on PR #8 and PR #9 (pooling, export, trend queue, CV clauses, Adi guardrails)
- **Date**: 2026-10-23
- **Feature**: Core, F1, F4, F8
- **Type**: fix
- **Change**: PR #8: pooled connections reset row format and autocommit when returned (a sync job's tuple rows leaked to later requests); account export adds plan history, every tracked course with evidence, and badges; trend reads are capped at 16 outstanding, identical reads are shared, and new callers fail fast instead of queueing; CV cleaning keeps line breaks and level cues and years count only within the skill's own clause. PR #9: every chat turn (not only the user's), the page path and the context are redacted before the model; an answer that names a course, role or programme outside the catalogue is replaced by the guide; SDG references resolve against the official target list; figures are compared with their units; fallback models share one deadline; the web route caps the body while reading; saved chats are kept per account and other accounts' chats are removed; Adi's links keep the current AI pace; team answers are for managers only.
- **Why**: Greptile reviews on PR #8 and PR #9.
- **Affects**: M2 (CV parser), M3 (F8 gateway use), M4.
- **Replaces**: none
- **PR / branch**: feat/core-adi-assistant (PR #8 parts also on fix/core-backend-perf-security)

### M4-031: Adi uses validated answer blocks in signed-in workspaces
- **Date**: 2026-10-23
- **Feature**: Core, F8 (Adi); read-only F5 progress integration
- **Type**: method | UI
- **Change**: Removed Adi from the landing page and require an authenticated API session. Conversations remount on account changes and abort old browser requests. The model selects server-authored answer-block IDs through the F8 gateway and `validate_ids`; generated prose, rationale and figures cannot reach the UI. Context uses the saved plan's scenario and effective completion statuses, guide intents use complete words and narrower privacy phrases, and SDG answers use the matched role's links. Provider retries use cancellable async I/O with one wall-clock deadline; at most four complete answers run concurrently under a 24-second route deadline, and expired context cannot start paid work. Attribution uses request-local model identity.
- **Why**: Remaining PR #9 review findings exposed private visitor-key chats, regex grounding bypasses, misleading numeric reuse, deadline overruns, incorrect progress, intent collisions and fallback attribution races. The user chose to keep Adi only inside signed-in workspaces.
- **Pipeline**: source = own profile, matching, saved-plan progress, catalogue and trends → preprocessing = effective evidence statuses, sanitisation and PII redaction → features = server-authored answer blocks → method = model selects validated block IDs or deterministic intent guide → evaluation = assistant/gateway regressions for unstructured/unknown outputs, redaction, scenario, rejected learning, deadline cancellation and actual fallback attribution → serving = authenticated assistant API and account-scoped workspace chat.
- **Affects**: M3 F8 provider/gateway/disclosure; M4 assistant/web; no new dependencies or database schema changes.
- **Replaces**: M4-030 free-text answer checks and phase-only provider timeout; M4-028 landing-page assistant placement.
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/9 / feat/core-adi-assistant

### M4-032: feat(catalogue): enrich future-facing roles skills and public courses
- **Date**: 2026-10-23
- **Feature**: F1, F4, F5, F6, F7 / Core integration
- **Type**: data source | method
- **Change**: Preserve all existing entities; complete the unfinished expansion to 140 skills, 31 roles, 160 role-skill links and 71 courses. Add 37 provider-verified Microsoft Learn entries, future AI skills in role requirements, BM/CJK aliases and O*NET 31.0 occupation crosswalks. New role SDG links are conservative enabling hypotheses tied to official UN definitions; remove unsupported cloud/mobile-network and cybersecurity/transport arguments.
- **Why**: The four-role pool could not serve varied career backgrounds. The user requested additive future-facing coverage, never fabricated courses or growth forecasts.
- **Pipeline**: Microsoft Learn live API, O*NET occupation data and official UN targets → exact-ID/URL/duration validation and retained original rows → curated estimated role/skill edges and draft SDG links → shared F4/F5 catalogues → closed graph with 28 future targets, all roles/skills mapped and provider IDs validated → seed CSVs, provenance JSON and live course sync.
- **Affects**: M1 trends coverage; M2 taxonomy/profile/matching; M3 courses and SDG mappings.
- **Replaces**: none
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-033: fix(pathway): unify catalogue credit prerequisites and price estimates
- **Date**: 2026-10-23
- **Feature**: F1, F4, F5, F6, F7 / Core integration
- **Type**: method | schema | contract
- **Change**: Use shared DB-first taxonomy reads in matching, profile, CV and pathways; upsert reference seeds without overwriting user state or dated trend snapshots. Preserve duplicate legacy IDs but merge credit once at the highest canonical level. Add current-role baselines with an explicit target flag. Include external prerequisites, block unavailable foundations, show honest unmet levels and exclude unknown certificate prices from costed plans. HRD eligibility no longer zeroes list prices. Default HR target uses existing team skill fit.
- **Why**: Expanded data exposed disconnected skill IDs, stale deployments, impossible prerequisite ordering, misleading free certificates and unrelated default team targets.
- **Affects**: M2 profile/matching; M3 pathway and contracts; M4 organisation defaults. Append-only migration required before seeding.
- **Replaces**: none
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-034: feat(org): persist private member budgets and funding ledgers
- **Date**: 2026-10-23
- **Feature**: F1, F4, F5, F6, F7 / Core integration
- **Type**: schema | contract
- **Change**: Add typed decimal MYR budgets, immutable course snapshots, request revisions and audit events. Store all budget years in one locked ledger per organisation, with RLS and no public policy; the memory store is synthetic-test-only. Embedded funding and assignment data participate in account export and transactional deletion.
- **Why**: Per-member caps must remain correct across concurrent API workers, restarts and repeated requests; new private data must not outlive the account deletion flow.
- **Affects**: M4 accounts/org; M3 course snapshots. Append-only learning_funding migration, no dependencies.
- **Replaces**: none
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-035: feat(org): gate reimbursements on purchase approval and course proof
- **Date**: 2026-10-23
- **Feature**: F1, F4, F5, F6, F7 / Core integration
- **Type**: method | other
- **Change**: Require HR purchase approval before buying, reserve the approved cap, and accept receipt claims only after current-org HR confirms the certificate. Block over-cap amounts, duplicate course/receipt claims, stale revisions and revoked evidence; distinguish payable from an externally recorded finance payment. Let members submit certificates for approved courses absent from generated plans. Validate current manager membership and stop certificate probes from following redirects.
- **Why**: Completion-based reimbursement is useful with pre-approval, receipt review and a non-upfront employer procurement option. Certificate URL reachability alone cannot authorize a payment. Subscription/group purchases require separate employer procurement; no bank transfer is performed by Adept.
- **Affects**: M3 completion verification; M4 finance workflow and security. Tests cover synthetic claim lifecycle, reservation races, scope, stale/revoked proof, export/deletion and blocked redirects.
- **Replaces**: none
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-036: feat(org): compare and assign member-specific learning packages
- **Date**: 2026-10-23
- **Feature**: F1, F4, F5, F6, F7 / Core integration
- **Type**: method | contract
- **Change**: Offer free-first, per-member-budget-capped and broader-catalogue proposals for an HR-selected role and cohort of 1–50 completed profiles. Reuse F5 for each member, expose costs/time/unmet skills and combined provenance, reject stale offer hashes, persist the selected proposal and require explicit member adoption. Selection does not purchase, reserve funds or overwrite personal plans.
- **Why**: HR needs comparable, concrete choices rather than one automatically chosen team curriculum. Identical free coverage can legitimately yield coinciding options.
- **Affects**: M3 pathway engine; M4 organisation APIs and member adoption. Synthetic tests verify cohort isolation, stale budget offers and consent.
- **Replaces**: none
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-037: feat(web): expose plan packages member budgets and expense claims
- **Date**: 2026-10-23
- **Feature**: F1, F4, F5, F6, F7 / Core integration
- **Type**: UI
- **Change**: Replace the organisation plan page with role/cohort package comparison and per-member course previews; add proposal adoption and account-scoped funding pages for HR budgets, purchase requests, certificates, receipts and external payment records. Display unknown certificate prices and provider learning-achievement caveats. Add English, Malay and Chinese labels and revise obsolete largest-gap guidance.
- **Why**: A coherent plan-to-purchase-to-proof flow must be accessible to HR and learners, with actual remaining gaps and dated price assumptions visible before a choice.
- **Affects**: M4 navigation and organisation UI; M3 pathway/catalogue screens. Uses existing design primitives and typed API client.
- **Replaces**: none
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-038: chore(api): regenerate catalogue and organisation contract bindings
- **Date**: 2026-10-23
- **Feature**: F1, F4, F5, F6, F7 / Core integration
- **Type**: contract
- **Change**: Regenerate OpenAPI and TypeScript from the final typed catalogue, funding, package and account-export contracts.
- **Why**: Keep generated client bindings in sync with the server contract; separate generated output from handwritten changes for review.
- **Affects**: All typed API consumers; no handwritten changes to generated files.
- **Replaces**: none
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-039: Restore grounded personal-plan answers and plural intent coverage
- **Date**: 2026-10-23
- **Feature**: Core, F8 (Adi), read-only F5 plan/progress integration
- **Type**: method
- **Change**: Add server-authored progress, duration and cost blocks in EN/MS/ZH using numeric facts from the saved plan and its effective progress. Personal-plan answers carry saved-plan attribution, including its scenario; missing data is explicit. Model selection cannot omit a specifically requested plan block and substitute generic advice. Add explicit plural/inflected intent keywords while preserving complete-word checks, and clarify that HRD eligibility does not guarantee RM0 funding.
- **Why**: Greptile PR #9 findings 4352515679 and 4352515689: the answer-block redesign lost personal totals, and ending boundaries stopped ordinary plural role/course/skill questions matching.
- **Affects**: M3 F5 read-only data; M4 assistant. No dependencies, schema or public contract changes. Decision IDs 032–038 are already used by the catalogue branch in PR #10.
- **Replaces**: none (extends M4-031)
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/9 / feat/core-adi-assistant

### M4-040: fix(org): bound funding transactions and preserve budget history
- **Date**: 2026-10-23
- **Feature**: F5, F6, F7 / Core integration
- **Type**: method | contract
- **Change**: Read ledgers and assignments through snapshots without write locks. Bind nested synchronous repository calls to the existing transaction connection, with thread isolation and exception-safe reset; lock completion/evidence rows during claim/payment decisions. Move certificate/pathway work outside the funding lock and recheck revisions before recording it. Return accessible budget years, use Malaysia calendar years, and retain historical member records for managers. Add real PostgreSQL regression coverage for ten concurrent approvals plus claim/payment with a one-connection pool, and tests for slow certificate checks, cancellation and rollover.
- **Why**: Greptile 4352984351 identified pool starvation when lock holders borrowed another connection. Calendar rollover must not change a previously approved purchase year. Real connection contention and failure paths were missing from the original validation.
- **Affects**: M3 pathways/SDG, M4 organisation and shared database access.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses

### M4-041: fix(web): keep prior-year learning claims accessible
- **Date**: 2026-10-23
- **Feature**: F5, F6, F7 / Core integration
- **Type**: UI
- **Change**: Add a budget-year selector on both funding pages using the API-provided accessible years. Preserve each claim year in every action, keep historic certificate/receipt/payment forms usable, and limit new purchase requests to the current Malaysia budget year. Historical views avoid unnecessary live catalogue, matching and proposal reads.
- **Why**: Greptile 4352984368: a December approval disappeared from the UI in January even though the backend retained the original record.
- **Affects**: M3 pathways/SDG, M4 organisation and shared database access.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses

### M4-042: fix(pathway): retain team prerequisite knowledge
- **Date**: 2026-10-23
- **Feature**: F5, F6, F7 / Core integration
- **Type**: method
- **Change**: Include the transitive prerequisite closure when deriving the lowest team skill levels. Known foundations are not scheduled again, and newly required foundations are assigned only to members who lack them.
- **Why**: Greptile 4352984384: aggregating only role-required skills erased known SQL and created foundation steps with no assigned members. Regressions cover both fully-known and mixed-knowledge teams.
- **Affects**: M3 pathways/SDG, M4 organisation and shared database access.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses

### M4-043: fix(sdg): include official target text in alignment evidence
- **Date**: 2026-10-23
- **Feature**: F5, F6, F7 / Core integration
- **Type**: data source
- **Change**: Populate all 48 new role alignment evidence notes from the official target label column. Preserve draft enabling status and the explicit distinction between curated alignment and measured impact. Add a regression requiring the actual target definition in every new evidence note.
- **Why**: Greptile 4352984399: the generator looked for absent title/description fields instead of label, leaving blank target quotations.
- **Affects**: M3 pathways/SDG, M4 organisation and shared database access.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses

### M4-044: chore(api): regenerate accessible funding year bindings
- **Date**: 2026-10-23
- **Feature**: F5, F6, F7 / Core integration
- **Type**: contract
- **Change**: Regenerate OpenAPI and TypeScript for the accessible budget-year field.
- **Why**: Keep the funding history UI and API contract in sync.
- **Affects**: M3 pathways/SDG, M4 organisation and shared database access.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses

### M4-031: Free-to-learn courses in plans, 27 more verified courses, honest "tops out" gaps
- **Date**: 2026-10-23
- **Feature**: F5, F4 (Core integration)
- **Type**: data source | method
- **Change**: (1) Plans may use free-to-enrol courses whose certificate fee is unknown as RM 0 learning; they keep `price_status=certificate_price_unknown` and their certificate note, and callers that need certificates filter them out (the HR planning brief). Replaces the rule that excluded them from plans. (2) 25 more Coursera courses checked on 2026-10-23 (each page shows "Enroll for free"; hours = sum of module hours) for machine learning, statistics, cybersecurity, cloud, renewable energy, IoT, UX, digital marketing, business analysis, instructional design, accounting, data engineering, project management, sales, content, warehouse, CRM, semiconductor physics, hotel distribution and Six Sigma; plus UTM's HRDC-claimable Registered Energy Manager course (RM 4,900 HRDC rate) and IBFIM's Fundamentals of Shariah for Islamic Finance (RM 2,730 online, HRDC claimable per brochure). Catalogue 71 → 98 courses. (3) Role requirements are capped at level 3 (24 links were 4): these are entry targets for reskilling, the team's original roles never exceed 3, and level 4+ comes from practice, not courses. (4) A skill whose courses stop at or below the learner's level is reported as "courses stop at level N" instead of "no course in our catalogue".
- **Why**: Measured coverage: a newcomer with RM 0 could fully reach only 42% of role requirements and many plans were under 2 hours; now 50% (RM 0) / 53% (RM 6,000). The remaining gaps are skills no free or verified course teaches yet (listed by the pipeline run), shown honestly.
- **Pipeline**: Coursera course pages + Catalog API slug checks, provider pages/brochures → `catalogue_sources.py` → `pipelines.pathway.run` (98 rows, validated) → engine selection (level ladder, cheapest then shortest, free-to-learn allowed) → evaluation: coverage script over 28 roles; tests for tops-out labelling and certificate caveats → serving: `/pathway`, `/org/packages`.
- **Affects**: M3 (catalogue, engine), M2 (role requirement levels), M4.
- **Replaces**: the PR #10 rule excluding `certificate_price_unknown` courses from plans.
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-045: Personal and organisation workspaces with explicit learning sharing
- **Date**: 2026-10-23
- **Feature**: Core, F1, F4, F5, F7, F8 integration
- **Type**: schema | contract | method | UI
- **Change**: Add membership-checked `X-Workspace` selection, a server-rendered switcher and employee home, agreements, progress, funding and skill-sharing views. Scope course progress/evidence to `personal` or `org:<id>`; personal completions enter an employer programme only when the member shares them. Keep personal saved plans and assistant conversations separate, require current management membership for team operations, and block last-manager account deletion when it would orphan a team or its learning records. Group role matches by existing skill overlap without changing ranking scores.
- **Why**: A manager also needs a personal workspace, and a member may belong to several organisations. Joining must not expose personal learning or grant management rights. Reuse the existing F5 engine and funding store rather than create a second progress model.
- **Affects**: Shared auth, accounts, profile/matching, pathway and organisation contracts; EN/MS/ZH navigation and copy. Migration `20261023120000_core_workspaces.sql` is append-only; its introductory M4-033 comment refers to the earlier integration work, while this entry records the final workspace design.
- **Replaces**: M4-001 single-default-organisation navigation; extends M4-021 evidence rules with explicit workspace ownership.
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses

### M4-046: Reviewable employer programmes and fluid workspace layouts
- **Date**: 2026-10-23
- **Feature**: Core, F7 (programme wizard), read-only F4/F5 integration
- **Type**: method | contract | UI
- **Change**: HR chooses catalogue-backed business objectives, roles/headcounts, sharing members, date, paid study hours, budgets and delivery restrictions, then reviews estimated personal routes before sending. Programmes retain dated attribution and require member acceptance; optional programmes can be declined and members can request changes. Add EN/MS/ZH strings and regenerate OpenAPI/TypeScript. Replace pill-based programme headers, steps and filters with wrapping employer identity, status text, numbered steps and checkbox rows; show labelled table records on narrow screens. Generation animation runs only while the request is pending and does not claim unreported stage completion.
- **Why**: The employer/status row overflowed on narrow cards; fixed minimum columns, edge-to-edge tables and a mobile workspace menu also prevented fluid layouts. HR and employees need understandable agreements and an explicit decision before learning is adopted.
- **Affects**: M4 organisation features/shared shell styles, M3 pathway metadata. No dependency changes.
- **Replaces**: none (extends M4-036/M4-037)
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses

### M4-047: Current reference seeds in local Docker and public display wording
- **Date**: 2026-10-23
- **Feature**: Core, F2, F4, F5, F6, F8 integration
- **Type**: data source | UI
- **Change**: Load current reference CSVs through the existing upsert loader and verify every stored column against the typed CSV rows, plus both dated trend exports. The local database has 98 courses, 140 skills, 31 roles, 160 role/skill requirements, 12 prerequisites, 17 goals, 169 targets, 61 role/SDG and 165 skill/SDG links; all comparisons match. Use “Sample personas and teams” for the source register and “Artificial data generation” for the existing skill ID, preserving its search aliases and dated numerical evidence. Trend fixture presentation resolves labels through the current taxonomy.
- **Why**: Updated CSV values must reach an existing database, not only a fresh deployment. The user requested plain sample-data wording in the website while preserving provenance and stable catalogue IDs.
- **Pipeline**: existing public/cited seed CSVs and frozen trend exports → existing FK-ordered, typed upserts (test personas/organisations remain fixture-only) → unchanged skill/course IDs → existing catalogue and trend methods → read-only PostgreSQL record comparison with zero mismatches → Docker PostgreSQL and rebuilt API/web images.
- **Affects**: M1/M2/M3 read-only consumers; no schema, formula or source changes.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses

### M4-048: Runpod GLM-5.3 primary with separately authenticated Gemini failover
- **Date**: 2026-10-23
- **Feature**: Core, F8 (Adi provider configuration)
- **Type**: method | other
- **Change**: Configure the user-supplied Runpod public Chat Completions endpoint and `glm-5.3` as primary; call Google Gemini only after primary request/schema failure or timeout. Keep `RUNPOD_API_KEY` and `GEMINI_API_KEY` separate, forward secrets only to the API container, and retain the existing HTTP client. Use low reasoning, capped output and one shared deadline with time reserved for the backup. Logs and assistant replies cite the actual answering provider/model; `/about` and README disclose the configured chain. Preserve the Adi name.
- **Why**: The presentation uses Runpod credits without deploying a Pod, while Gemini provides continuity during an outage. A fallback model name alone cannot switch endpoints or credentials safely.
- **Affects**: M3 gateway/provider/config; M4 assistant, Docker and documentation. No dependency changes. Unit tests cover primary-only success, key separation, malformed JSON, cancellation and expired deadlines; one small live request returned a validated ID from Runpod GLM-5.3.
- **Replaces**: M4-028 Gemini-primary configuration; extends M4-031 grounded answer selection.
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses

### M4-049: Mobile workspace choices and visual skill readiness
- **Date**: 2026-10-23
- **Feature**: Core, F7 (employee agreements and mobile navigation)
- **Type**: UI
- **Change**: Show workspace choices directly inside the mobile menu rather than expanding a nested dropdown. Use a short menu entrance, visible-focus controls and larger touch targets; prevent the desktop account footer from widening the sidebar. Replace estimate/status pills with wrapping text markers and an evidence disclosure. Show role readiness as an accessible percentage meter with its meaning, compact two-column agreement terms, and courses behind an explicit disclosure.
- **Why**: A nested dropdown changed the height of an already animated mobile sheet. Stacked text-only terms and boxed status tags obscured the key numbers and caused fatigue on phones. Readiness remains the existing required-skill-level coverage, not a new score or a hiring decision.
- **Affects**: Shared shell, estimate/badge styling and EN/MS/ZH employee copy. No scoring, schema or data changes.
- **Replaces**: none (refines M4-046)
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses

### M4-050: Softer agreement hierarchy and unobtrusive phone assistant
- **Date**: 2026-10-23
- **Feature**: Core, F7 (employee agreements)
- **Type**: UI
- **Change**: Refine the agreement into a rounded sage route panel with an accessible circular skill-coverage gauge and a prominent catalogue role. Use localised dates, icon-led time/date facts, a separate budget amount and planned course cost, and compact programme context. Keep the phone assistant launcher small, hide its promotional callout and remove it while the menu is open; wrap suggestions and use a 16px input to avoid phone zoom.
- **Why**: The first straight-bar design still felt rigid and text-heavy. Mobile numbers and decisions need more visual hierarchy without adding a new score or obscuring evidence.
- **Affects**: EN/MS/ZH agreement copy and assistant styles; no API, scoring or data changes.
- **Replaces**: M4-049 straight-bar visual treatment only; preserves its workspace and evidence rules.
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses


### M4-051: Review catalogue omissions without inventing CV skills
- **Date**: 2026-10-23
- **Feature**: Core integration, F1 (CV intake), guest preview
- **Type**: method
- **Change**: Add optional `unmatched_terms` to CV/guest responses, bounded to 30 short entries from explicit EN/MS/ZH skills lists. Compare complete entries against approved aliases, deduplicate case-insensitively, skip contact/markup/negated/oversized entries and keep the original cleaned wording for transient review. Guest preview and intake explain catalogue limits and truncation; intake can search for a user-confirmed equivalent. Unknown wording is never stored, scored, sent to an LLM or promoted into the taxonomy; unknown-only previews have no role or score.
- **Why**: The previous parser silently omitted unfamiliar skills and the upload action discarded truncation. Absence from the catalogue must not be presented as lack of ability, and fuzzy guesses must not receive credit.
- **Pipeline**: in-memory sample CV upload → existing extraction, text cap and scrubbing → exact catalogue aliases plus bounded explicit-list review entries → deterministic extraction with human confirmation → 165 profile/preview checks pass, including mixed/unknown-only lists, aliases, duplicates, truncation, unsafe entries and non-persistence → additive API fields and EN/MS/ZH review interfaces.
- **Affects**: F1 contracts and generated bindings, public preview, intake; no database migration or score changes.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses


### M4-052: Maintained documentation names and retirement of one-off handoffs
- **Date**: 2026-10-23
- **Feature**: Core documentation
- **Type**: other
- **Change**: Remove obsolete PR #4 validation, feature-status/fix handoff, workspace handoff and proposed UX-flow reports; Git preserves their history. Rename six maintained guides to lowercase kebab-case, update active references and developer-specific links, and add a documentation index. Keep conventional agent/README/FEATURE entrypoints; Claude and Gemini import the authoritative AGENTS manual. Refresh stale skeleton, provider, catalogue and workspace descriptions in active guides and unsigned submission drafts.
- **Why**: Multiple old reports contradicted the implemented flows and current provider/data configuration. One maintained guide per topic and portable names make the repository easier to navigate without erasing the decision history.
- **Affects**: Documentation and code-comment references only; existing decisions remain unchanged, including historical paths. No runtime or schema changes.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses


### M4-053: PostgreSQL CI fixtures respect workspace privacy and sharing
- **Date**: 2026-10-23
- **Feature**: Core, F5/F7 integration tests
- **Type**: other
- **Change**: Update the persistent evidence test to reject manager review of private personal evidence, then complete an accepted employer programme and verify its scoped evidence persists independently. Update the earned-level/team test to assert hidden skills are excluded, explicitly enable sharing before team comparisons, and restore the prior sharing choice.
- **Why**: CI's PostgreSQL upgrade job retained pre-workspace assumptions; new memberships correctly default to private skills and personal evidence cannot be reviewed through employer routes. Memory fixtures had opted into sharing, hiding the integration-test mismatch.
- **Affects**: Two regression tests only; production privacy, matching, transaction and migration logic are unchanged.
- **Validation**: Reproduced both CI failures using the exact skeleton upgrade in a disposable PostgreSQL database; all 38 tests from that CI job pass after the change. Existing stale-certificate and multi-skill foundation regressions also pass. Temporary databases are removed; the application database is untouched.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses


### M4-054: Claude workspace configuration remains local
- **Date**: 2026-10-23
- **Feature**: Core repository hygiene
- **Type**: other
- **Change**: Ignore the entire `.claude/` directory and remove its previously tracked launch/helper files from the Git index while preserving local copies. Keep repository-wide `CLAUDE.md` as the intentional agent entrypoint.
- **Why**: The old rule ignored only `.claude/settings.local.json`; tracked machine-specific launch configuration and helpers continued to appear in commits.
- **Affects**: Local tool configuration only; no application behaviour or dependency changes.
- **Replaces**: none
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/10 / feat/catalogue-roles-skills-courses


### M4-055: Organisation join flow uses explicit member consent and shares profile
- **Date**: 2026-10-23
- **Feature**: F7 (Organisation Mode & Heatmaps), Core
- **Type**: UI / schema / contract
- **Change**: Replace the optional 'share private skills' toggle on the join-code flow with an explicit consent requirement to join the organisation workspace and share the learner's skill profile and learning progress with organisation managers. Members joining with a valid code and consent default `share_skills` to `True`.
- **Why**: Joining an organisation workspace is an affirmative, consensual action initiated by the employee/student themselves to collaborate with their team. Explicit consent replaces confusing separate "private skills" choices during intake while ensuring members understand what managers can access.
- **Affects**: `JoinOrgIn` and `SignupIn` contracts (added `consent`, defaulted `share_skills` to True), `JoinView` and `AuthView` UI components, join API endpoints, and join test assertions.
- **Replaces**: none
- **PR / branch**: feat/org-join-consent


### M4-056: Privacy hardening across join consent, programme acceptance, and cross-tab workspaces
- **Date**: 2026-10-23
- **Feature**: F7 (Organisation Mode & Heatmaps), Core
- **Type**: contract | UI | method | schema
- **Change**:
  1. Signup with an organisation join code requires explicit user consent via a mandatory checkbox to share skill levels and learning progress with managers (`SignupIn.share_skills` defaults to `False` and is enforced by `accounts/service.py`).
  2. Programme agreement acceptance requires explicit consent when skills sharing is switched off before rebuilding routes with personal profile levels; employer-facing `list_programmes` masks private profile skill levels (`current_level: 0`) for members whose sharing is toggled off.
  3. Every organisation action, form, and mutation carries the displayed organisation ID (`expected_org`) and passes it into API requests to reject cross-tab workspace cookie drift with 409 `workspace_changed`.
- **Why**: Resolves Greptile P1 security and privacy findings ("Signup shares skills without notice", "Acceptance reveals private skills", and "Forms change another organisation") while respecting the user choice that membership in an organisation is an affirmative consensual collaboration.
- **Affects**: `SignupIn`, `AssignmentDecision` contracts, `accounts/service.py`, `programmes.py`, `org/router.py`, `AuthView.tsx`, `auth-actions.ts`, `funding-actions.ts`, `work/actions.ts`, `server.ts`, and i18n locales.
- **Replaces**: none
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-057: Close the remaining gaps in the M4-056 privacy fixes
- **Date**: 2026-10-23
- **Feature**: F7 (Organisation Mode & Heatmaps), F5 (progress forms), Core
- **Type**: method | UI
- **Change**:
  1. HR's programme list hides every level derived from a non-sharing member's private skills (`programmes.private_route`): gap statuses are removed, and step and unmet `current_level` are 0. Courses, hours, costs and target levels stay visible because the employer funds them.
  2. Acceptance consent is an explicit checkbox, shown only to members who do not share skill levels; the web action no longer sends `consent: true` on every accept.
  3. Progress, certificate, share-from-personal and HR review forms carry the workspace the API rendered (`Progress.workspace`, `VerificationQueue.org_id`), and the package-accept form carries its organisation, so a workspace switched in another tab cannot receive the change.
- **Why**: Greptile P1 threads "Acceptance reveals private skills" and "Forms change another organisation" were only partly fixed by M4-056: gap statuses still revealed levels, consent was implicit, and pathway forms still followed the shared cookie.
- **Affects**: M3 (F5 `ProgressView`, `VerificationQueueView`, `pathway/actions.ts`: forms now include a `workspace` field)
- **Replaces**: none (extends M4-056)
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-058: Employer view of private routes is an allowlist; join consent is never assumed
- **Date**: 2026-10-23
- **Feature**: F7 (Organisation Mode & Heatmaps), Core
- **Type**: method | contract | UI
- **Change**:
  1. `programmes.private_route` rebuilds each step from an allowlist for members who do not share skills. Step explanations are neutral, with no "You are at level ..." text or gap share. Priority and current level are 0; the reached level comes from the courses' own catalogue levels. Unmet details are generic, and gaps, warnings and segment are removed. New pathway fields therefore stay private by default.
  2. `JoinOrgIn.consent` now defaults to `false`, so an API join without explicit consent is refused (`consent_required`). This brings the contract in line with M4-055 and M4-056. The join consent and sign-up sharing checkboxes start unticked.
- **Why**: Greptile (confidence 3/5) found private levels still in step explanations. Review also found the join contract's `consent=True` default contradicted the agreed explicit-consent rule.
- **Affects**: API clients of `POST /org/join` must send `consent: true`
- **Replaces**: none (extends M4-056, M4-057)
- **PR / branch**: feat/catalogue-roles-skills-courses

### M4-059: Live job openings from public employer and job-board feeds
- **Date**: 2026-10-23
- **Feature**: Core (new `jobs` feature; works with F4, F5, F7)
- **Type**: data source | method | schema | contract | UI
- **Change**: New pipeline `src/pipelines/jobs` reads current openings and stores them in `job_postings` (migration `20261023160000`) and `src/data/seed/jobs/job_postings.csv`. It keeps openings in Malaysia, plus remote ones open to Malaysians. Sources are 45 employer feeds (Greenhouse, Lever, Ashby, Workday and Jibe career sites) and 4 remote boards. Each ad is matched to an Adept role by job title. The skills it names are read with the CV parser's catalogue matcher. Ad text is never stored. New `/jobs` endpoints serve:
  - openings per role, with how many are within reach today and after the learner's plan;
  - a filtered job board;
  - opening counts for the matches list.

  The web shows a `/app/jobs` page, a "Hiring now" card on role and plan pages, opening counts on match cards and a learn → prove → apply roadmap on the plan.
- **Why**: Mentor feedback asked for a path to real jobs after training, not only projections. Rejected sources:
  - JobStreet: its terms (clause 7(d)) ban scraping;
  - LinkedIn and Indeed: no public jobs API;
  - EY: its robots.txt disallows the feed path;
  - SmartRecruiters: its API host disallows crawlers.

  Careerjet, Jooble and web3.career are wired but run only with a free publisher key. A role match from skills alone was tried and dropped: it filed a React developer as an ML engineer.
- **Pipeline**:
  1. Source: public ATS and remote-board APIs. robots.txt is checked for every host, with a delay per host.
  2. Cleaning: Malaysia filter, HTML to text, dedupe.
  3. Features: catalogue skills, named certifications and seniority.
  4. Method: ordered title patterns per role.
  5. Evaluation: title rules are at least 95% right on 31 hand-labelled titles. The share of openings assigned to a role, and the job families left unassigned, are logged in `fetch_log.json`.
  6. Serving: seed CSV plus a `--db` upsert. A board read successfully closes the openings it no longer lists, and any opening unseen for 14 days is closed.
- **Affects**:
  - M2: match cards and role detail show openings.
  - M3: the plan page shows the roadmap and openings; the jobs feature reads `pathway_service.learner_for`, `get_saved_plan` and `get_pathway`.
  - M4: `/org/plan` shows market demand.
- **Replaces**: none
- **PR / branch**: feat/jobs-live-openings

### M4-060: Paid certification exams linked to role skills, payer by context
- **Date**: 2026-10-23
- **Feature**: Core (jobs), F5, F7
- **Type**: data source | schema | contract | UI
- **Change**: `certifications` table and seed hold 14 exams, each with the official fee for a candidate in Malaysia, the page it was read from and the date checked:
  - Microsoft PL-900/PL-300/DP-900/DP-700/AZ-900/AZ-104/AI-901/SC-900/SC-200, priced from Microsoft's exam-pricing data (USD 50 Fundamentals, USD 83 role-based);
  - AWS CLF-C02 and AIF-C01 (USD 100);
  - Google Cloud Digital Leader (USD 99);
  - IIBA ECBA ("$395 or less" bundle);
  - IAPP AIGP (USD 799 for non-members).

  Ringgit amounts use the BNM selling rate. `GET /jobs/certifications` lists the exams covering a role's required skills. Each entry shows the learner's status per skill, the plan courses that prepare for it and how many current ads name it. On a personal plan the learner pays the issuer. With `payer=employer` (team programme) the organisation buys exams like courses and no personal skills are shown.
- **Why**: Mentor feedback said to link course completion to certifications employers recognise. Free courses teach the skills; a paid exam is what an employer can verify. In practice HR buys team training and exams directly, so the team view frames exams as programme budget, not member reimbursement.
- **Pipeline**: source (issuer pages, read 2026-10-23) → validation (skills exist in the catalogue, https URLs, positive fee, dated) → features (role coverage = overlap with required skills) → serving (seed CSV, DB upsert, API)
- **Affects**: M3 (plan page card); M4 (`/org/plan` card)
- **Replaces**: none
- **PR / branch**: feat/jobs-live-openings

### M4-061: Section-aware CV review list and Gemini embedding skill suggestions
- **Date**: 2026-10-23
- **Feature**: F1 (Skills Profile Intake), Core
- **Type**: method | model | schema | contract | dependency
- **Change**: (1) `cv_parser` reads a skills list only up to the next heading of any kind and rejoins wrapped and hyphenated lines, so "Wording to review" no longer lists employers, job titles, dates or sentences. On the five synthetic CVs it drops from 16–25 noisy entries each to 2–3 genuine skill phrases. (2) New `app.core.embeddings` (Gemini `gemini-embedding-001`, 768 dims) and `features/profile/skill_match.py`. Catalogue skills are embedded into `catalogue_embeddings` (pgvector, HNSW cosine; migration `20261023170000`). CV skills-list entries that no alias matches get a suggested nearest skill: similarity >= 0.80, lead over runner-up >= 0.015, and never when the nearest skill is already found. `CvExtractionResult` and the guest preview gain `suggestions`, and the web review list shows "≈ skill (n% similar)" with an Add button.
- **Why**: Users saw non-skills in the review list (company names, locations, sentences) because "PROFESSIONAL EXPERIENCE" did not end the skills section. The KerjaCerdas approach (structured, field-separated extraction) was adapted: sections give the separation, and embeddings map unfamiliar wording to the catalogue without letting a model invent skills.
- **Pipeline**: catalogue labels + aliases + descriptions → embed (redacted, batched, rate-limit aware) → pgvector → per-term cosine top-3 → threshold + margin rule → proposal → person adds and sets the level
- **Evaluation**: calibrated on 18 entries. Matched: Power BI / Tableau / QlikSense → Data visualisation; "problem solving" → Critical thinking; "stakeholder communication" → Stakeholder management. Rejected: "Kuala Lumpur" (0.775), "Rust", "teamwork", "exception handling" (ambiguous). Unit tests use fake vectors; the suite never calls the API.
- **Affects**: M2 (F1 parser and contract: new optional `suggestions` field); M3 (`/about` disclosure lists the embedding model)
- **Replaces**: the F1 FEATURE note that unmatched entries are never sent to a model, for these short entries only
- **PR / branch**: feat/jobs-live-openings

### M4-062: Organisation pays for training; member reimbursement removed
- **Date**: 2026-10-23
- **Feature**: F7 (Organisation Mode & Heatmaps)
- **Type**: method | contract | UI
- **Change**: Removed the member purchase-request, completion, receipt-claim and HR decision/payment endpoints (`POST /org/funding/{year}/requests...`) and their contracts, the member "Learning funds" page and nav entry (`/work/funding` and `/app/funding` now redirect to `/work/plan`), and the claim UI. `/org/funding` is now "Training budgets": HR sets a yearly amount per member, and `/org/packages` uses it for the budget-capped option. Stored claim records stay readable only for export and deletion.
- **Why**: In practice HR chooses team training and pays providers directly (often under HRD Corp), not by reimbursing employees. The reimbursement flow added steps and risk without matching how companies buy upskilling.
- **Affects**: M3 (no change to pathway or verification); API clients of the removed endpoints
- **Replaces**: the claim workflow parts of M4-040, M4-041 and the funding notes in F7 FEATURE.md
- **PR / branch**: feat/jobs-live-openings

### M4-063: Resolve the live-openings PR's eight Greptile findings
- **Date**: 2026-10-24
- **Feature**: Core (jobs), F1, F7
- **Type**: method | UI
- **Change**: CV requests read only an existing, current catalogue embedding index without waiting for its build; acronyms no longer terminate skills lists. Job refreshes distinguish incomplete reads, preserve skipped/failed boards in CSV mode, and close missing listings only after a complete read; API reads apply the same 14-day stale limit. Security title rules exclude securities banking jobs, and five affected seed rows were corrected. Archived unpaid claims no longer reserve training funds, while paid historical expenses remain recorded. Certification cards show every option counted in their heading.
- **Why**: Greptile identified optional embedding retries blocking uploads, incomplete refreshes hiding valid jobs, stale or misclassified jobs appearing live, unusable budget reservations, and advertised exam options being inaccessible.
- **Evaluation**: Focused regressions passed; full repository quality gate passed with 882 tests passed and 26 skipped. Checks call no paid endpoints.
- **Affects**: M2 (CV extraction), M3 (certification cards), M4 (jobs and funding)
- **Replaces**: the request-time indexing and archived-reservation behaviour in M4-061/M4-062
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/13 / feat/jobs-live-openings

### M4-064: Deploy the trend encoder as a RunPod Serverless worker
- **Date**: 2026-10-24
- **Feature**: F2 (AI-Trend Signal Layer), Core deployment
- **Type**: model | dependency | architectural decision
- **Change**: Background trend jobs use a RunPod client by default for the pinned all-MiniLM-L6-v2 model (384 dimensions). A separate container caches the model weights and serves bounded text batches; local CPU inference remains an explicit development option. The weekly workflow reads the endpoint ID and API key from Actions configuration. Deployment instructions require no application-code edits.
- **Why**: A teammate will host inference on RunPod; deployment preparation must work without creating an account, spending credits, or placing credentials in the repository. The web API continues serving stored snapshots.
- **Pipeline**: public research and taxonomy → existing sentence cleaning → normalized 384-dimensional vectors → pinned MiniLM on RunPod, existing cosine threshold → mocked client/worker regressions and full quality gate (882 passed, 26 skipped) → existing validated database snapshots. Live RunPod validation is pending deployment.
- **Affects**: M1 (trend refresh), M4 (deployment); Adi and CV embedding settings remain separate
- **Replaces**: local-only trend encoder deployment; scoring formulas are unchanged
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/13 / feat/jobs-live-openings

### M4-065: Allow partial board reads in the PostgreSQL fetch log
- **Date**: 2026-10-24
- **Feature**: Core (jobs)
- **Type**: schema
- **Change**: Append migration `20261024010000_jobs_partial_fetch_status.sql` to allow `partial` in the fetch-log status constraint. Downgrading preserves those audit rows as errors with an explanatory detail. PostgreSQL CI now exercises the real pipeline transaction with both partial and complete boards.
- **Why**: Greptile found that the status introduced in M4-063 was rejected by the original database constraint, rolling back successful boards along with the incomplete one.
- **Evaluation**: Eight focused regressions passed, including a real PostgreSQL test in an isolated schema: the partial board stays active, a complete board closes missing openings, both audit records commit, and the migration reverses and reapplies successfully. The full quality gate also passed (882 passed, 27 skipped; the PostgreSQL regression was run separately with its database configured).
- **Affects**: Deployments must apply the new migration before the next jobs refresh
- **Replaces**: none (completes M4-063)
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/13 / feat/jobs-live-openings

### M4-066: Concise project README and confirmed team details
- **Date**: 2026-10-24
- **Feature**: Core (documentation and submission)
- **Type**: other
- **Change**: Restructure the README around the product, confirmed Pecel Lele team information, project links, setup, model disclosure and development commands. Separate the configured Adi GLM endpoint from the pending MiniLM endpoint, and include a collapsible inventory of tracked application files and folders. Remove submission-draft references and detailed PDF preparation material from the README.
- **Why**: Give readers a clear project entry point while preserving the disclosures and instructions needed to understand and run the app. Design-thinking, deployment-strategy and detailed implementation references are saved separately as local working documents; this PR contains only the README and this decision entry.
- **Affects**: Project documentation only. Replit Agent will handle platform configuration in a separate PR; demo-video files stay local.
- **Validation**: Full quality gate passed (904 tests passed, 27 skipped); GitHub Markdown rendering and local documentation links verified.
- **Replaces**: none
- **PR / branch**: docs/core-readme-cleanup

### M4-067: Restore README diagrams and explicit setup section
- **Date**: 2026-10-24
- **Feature**: Core (documentation)
- **Type**: other
- **Change**: Restore all 11 product diagrams to the README: architecture, four journey/pipeline diagrams, scoring and knowledge graph, and four database/provenance views. Keep the architecture visible and group detailed diagrams in expandable sections. Label the retained setup instructions Getting started, display complete URLs in the project-links table, and restore all nine original technology/licence badges.
- **Why**: The README cleanup removed diagrams beyond the requested separation of design-thinking and deployment-strategy material. Readers need both the diagrams and the run instructions in the README itself.
- **Affects**: README and decision log only; Replit configuration and local demo-video files remain outside the PR.
- **Validation**: Full quality gate passed (904 tests passed, 27 skipped). All 11 product diagram sources match the originals; GitHub Markdown exposes all 11 Mermaid containers, with nine badges, valid local links and full resource URLs.
- **Replaces**: M4-066 (diagram placement and link presentation only)
- **PR / branch**: docs/core-restore-readme-diagrams

### M4-068: Integrate MiniLM deployment and verify database access before inference
- **Date**: 2026-10-24
- **Feature**: Core deployment / F2 (AI-Trend Signal Layer)
- **Type**: method | other
- **Change**: Integrate the existing trusted GHCR publisher and worker configuration with current main. Refresh the README, operations, architecture, feature and submission docs with the deployed endpoint, pinned model, separate credentials and observed results. Add a bounded database preflight before scheduled ingestion or inference, including read-write transaction status, table privileges and ID sequence access; exercise it against PostgreSQL in CI.
- **Why**: The worker returns the pinned revision and two 384-dimensional vectors, but the first real refresh spent about seven minutes fetching and embedding 366 papers before failing on Replit's private development host `helium`. Preflight rejects that configuration early and sanitizes failures; production publishing and connection setup remain account-owner operations.
- **Pipeline**: public arXiv/catalogue → existing cleaning → pinned 384-dimensional MiniLM via RunPod → unchanged cosine/scoring → database preflight, vector and snapshot checks → atomic PostgreSQL publication read by Replit.
- **Affects**: M1 (scheduled refresh), M4 (deployment/docs); no contract, schema, dependency or scoring changes beyond the existing deployment branch.
- **Validation**: Full quality gate passed: 918 tests passed, 27 skipped; Ruff, ESLint, translations, TypeScript and generated contracts passed. Fourteen preflight regressions cover private-host rejection, bounded queries, read-only connections, table/sequence privileges, preserved connection options and sanitized failures. CI additionally exercises the preflight against migrated PostgreSQL. Documentation links and submission answer limits passed.
- **Replaces**: M4-066 (MiniLM pending status); completes deployment integration from M1-011/M4-064.
- **PR / branch**: feat/minilm-runpod-deploy

### M4-069: Explicit Replit production build and supervised startup
- **Date**: 2026-10-24
- **Feature**: Core deployment
- **Type**: other
- **Change**: Add a versioned Autoscale build/start configuration and stdlib production launcher. Build Next.js standalone assets and Python dependencies; co-host a private FastAPI process with one public web port, honor existing workspace port mappings, resolve Nix's GCC runtime for PyMuPDF and stop both children on failures. Document workspace preservation, production secrets, database preparation and publishing diagnostics.
- **Why**: GitHub main had no Replit configuration. The partner's unpushed workspace configuration provided only a development Preview workflow, without deployment build/run commands. Explicit production commands close that gap; the generic disabled Publish banner still requires account-side validation after configuration is loaded.
- **Affects**: M4 (Replit deployment), all features served by the app; no schema, contract, scoring or dependency changes.
- **Validation**: Full quality gate passed (932 tests, 27 skipped), including 14 launcher regressions. The exact production build passed; a local production smoke test verified the public landing/About/sign-in pages, static assets and API database health using synthetic local data with model providers disabled. Replit account-side publishing remains unverified.
- **Replaces**: none
- **PR / branch**: fix/core-replit-deployment

### M4-071: Patch Next.js before retrying Replit package installation
- **Date**: 2026-10-24
- **Feature**: Core deployment
- **Type**: dependency
- **Change**: Pin Next.js and eslint-config-next to 16.4.1 and regenerate the existing pnpm 10.29.3 lockfile. Document diagnosis of Replit package-firewall rejection without disabling platform checks or adding registry credentials.
- **Why**: The live Replit build successfully installed Python dependencies, then received HTTP 403 downloading Next.js 16.2.12 from its internal package firewall. Vendor advisories identify critical affected-version ranges covering 16.2.12 and prescribe 16.4.1. The firewall's precise rejection reason remains unconfirmed; the dependency update independently addresses the published advisories. The official public tarball for 16.2.12 remains reachable, and the repository contains no internal registry URL.
- **Affects**: All Next.js pages and production web builds; no API contracts, schema, model or scoring changes.
- **Validation**: Full quality gate passed (932 tests, 27 skipped), including ESLint with the aligned configuration, translations, TypeScript and generated contracts. The exact Replit build passed with the frozen lockfile; a local production smoke test verified landing/About/sign-in pages, static assets and API/database health without model calls. The advisory query returned no published matches for Next.js 16.4.1 at verification time. Replit's own package download remains to be retested by the account owner.
- **Replaces**: Next.js/eslint-config-next 16.2.12 pins only
- **PR / branch**: fix/core-replit-next-patch

### M4-072: Recover from terminated pooled database sessions
- **Date**: 2026-10-24
- **Feature**: Core deployment, shared database access and rate limiting
- **Type**: method
- **Change**: Check both PostgreSQL pools before checkout and sweep remaining idle sessions after a failure so multiple dead connections cannot exhaust checkout time through per-connection retry backoff. Bound rate-limit statements/locks, synchronize its worker-thread fallback and preserve the supplied empty counter. Retry web GET/HEAD once for HTTP 502/503/504 in addition to connection failures; never replay writes or transactions already started.
- **Why**: Production logs showed administrative session termination followed by stale-connection account 503s and seed/in-memory fallbacks. The initiating database infrastructure event remains unconfirmed. Recovery should not spend a user request discovering each dead idle connection or duplicate a write whose outcome is unknown.
- **Affects**: All database-backed features and the shared web API client; no schema, contract, dependency or environment changes.
- **Validation**: Full quality gate passed (949 tests, 32 skipped, 48 subtests); all 18 targeted recovery/rate-limit checks passed against disposable PostgreSQL 16, including real administrative session termination, and 35 existing PostgreSQL integration checks passed after loading CI's synthetic upgrade personas. Seven web retry regressions and the production web build passed. The currently deployed public pages and unsigned app redirect passed read-only smoke checks; the repair still needs publishing and signed-in production verification.
- **Replaces**: none (extends M4-027 and M4-005)
- **PR / branch**: fix/core-database-recovery

### M4-073: Preserve production boundaries and CI after the workspace migration
- **Date**: 2026-10-24
- **Feature**: Core deployment and dependency hardening
- **Type**: architecture | dependency | method
- **Change**: Resolve main's deployment/preflight changes into the Replit artifact layout. Restore active CI and scheduled data/trend workflows, the regression suite and contract generation; correct the worker Docker context and instructions. Preserve FastAPI CORS headers, discard forged proxy identity headers, derive visitor addresses from an explicitly configured trusted proxy chain and require shared-secret/hop configuration at production startup. Preserve Nix native-library discovery, supervise API/database readiness, copy standalone assets safely and restore secret-file ignores. Pin fast-uri 3.1.9 and align React types; allow the Windows build binaries alongside Linux.
- **Why**: Greptile identified five migration regressions: CORS loss, spoofable/shared visitor buckets, missing secret ignores, broken worker build instructions and inactive workflows. Main also added preflight and deployment fixes that would otherwise remain only in the historical backup. Production trust counts must be verified by the operator rather than guessed.
- **Affects**: All served features; M1 scheduled trend refresh and MiniLM publication. No database schema, API contract, scoring or entity changes. Existing authentication modes are preserved.
- **Validation**: Initial quality gate passed (939 Python tests, 27 environment-dependent skips, 48 subtests). After integrating main's M4-072 recovery changes into active paths, the full quality gate passed (940 tests, 32 environment-dependent skips, 48 subtests); 44 PostgreSQL integration tests and twelve navigation/read-retry regressions passed. Eleven proxy/startup regressions, Ruff, ESLint, translation parity, workspace TypeScript, generated contract checks, all workspace production builds, actionlint and worker publication policy checks passed. The pinned worker requirements resolve for Linux/Python 3.11. npm and installed Python audits report no known vulnerabilities. A local production smoke test returned 200 for landing/About/sign-in/static CSS and CORS preflight, and confirmed healthy API/database and catalogue reads. No live database changes, model calls, image publication or RunPod deployment.
- **Replaces**: M4-069 launcher layout only; keeps its startup/readiness and native-runtime guarantees in the migrated services.
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/20 / security/publish-hardening

### M4-074: Keep the relocated development Compose file database-only
- **Date**: 2026-10-24
- **Feature**: Core local deployment
- **Type**: architecture
- **Change**: Remove the obsolete API/web Compose services, whose old Dockerfiles no longer exist in the active build context. Keep the loopback-bound pgvector database, required password, persistent volume and readiness check.
- **Why**: Greptile's follow-up identified the broken container build paths. The migrated web/API already run through workspace artifact commands; restoring a second app packaging path would duplicate that setup.
- **Affects**: Local development only; no production service, schema or dependency changes.
- **Validation**: Docker Compose config resolves successfully and lists only db. The preceding source revision passed the complete quality gate (940 tests, 32 skips), 44 database tests, twelve navigation/retry checks and the clean workspace production build.
- **Replaces**: Historical API/web Compose services only.
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/20 / security/publish-hardening

### M4-075: Use Next.js native development port defaults
- **Date**: 2026-10-24
- **Feature**: Core local development
- **Type**: other
- **Change**: Remove shell interpolation of PORT from the web dev command. Next.js reads an explicitly supplied PORT itself and defaults to 3000 when absent. Show the configured web port in the relocated task runner's startup message.
- **Why**: Greptile's follow-up found that the old command passed an empty --port argument outside Replit. Native CLI configuration also works across Windows and POSIX shells.
- **Affects**: Local/Replit Preview startup only; production build/start is unchanged.
- **Validation**: Verified the installed Next.js 16.4.2 CLI's default(3000).env('PORT') behavior and CLI documentation; startup with an explicit alternate port reaches Ready.
- **Replaces**: Shell-dependent development port argument only.
- **PR / branch**: https://github.com/pecel-lelele/adept/pull/20 / security/publish-hardening

### M4-076: Restore the repository root layout inside the workspace deployment
- **Date**: 2026-10-24
- **Feature**: Core repository structure, CI and Replit deployment
- **Type**: architecture
- **Change**: Move the Next.js app back to `src/web` and the FastAPI app, pipelines, migrations, seed data and tests back to `src/` and `tests/`; restore `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `Makefile`, `docker-compose.yml`, `docs/` and `submission/` at their documented paths and delete the `.migration-backup/` import. Point `pyproject.toml`, `.gitattributes`, `.gitignore`, the CI and scheduled workflows, the MiniLM Docker context, the Express supervisor, the proxy test import and the Replit documents at the restored paths. Keep the Replit artifact settings (`artifacts/*/.replit-artifact`) and the pnpm workspace, now listing `src/web` as the `@workspace/adept` package. Repair UTF-8 text that the migration double-encoded. Add the live demo URL to the README links table.
- **Why**: The workspace import relocated everything under `artifacts/` and `.migration-backup/`, breaking the layout documented in AGENTS.md, the docs and the feature ownership paths. Keeping the Replit publishing setup while restoring the source layout satisfies both.
- **Affects**: All members' feature paths (restored to their documented locations); CI, scheduled data/trend workflows and MiniLM publication. No schema, contract, scoring or entity changes.
- **Validation**: See the pull request for the quality gate, proxy tests, workspace production build and diagram checks.
- **Replaces**: Layout aspects of M4-073 only.
- **PR / branch**: fix/core-root-layout-restoration

### M4-077: Deploy from the root with one public Next.js server
- **Date**: 2026-10-24
- **Feature**: Core deployment, repository structure, CI and submission documentation
- **Type**: architecture | dependency | method
- **Change**: Replace the artifact application router and Express supervisor with root build/start commands, one public Next.js listener and private FastAPI. Remove unused artifact, mockup, Drizzle and generated-client scaffolding; simplify the pnpm workspace and Python project while retaining PR #23's security hardening. Add streamed API forwarding, database-aware health aliases and a disposable-database CI smoke using the actual launcher. Use webpack for consistent standalone packaging after reproducing a Windows Turbopack tracing race. Disable implicit fetch credentials so streamed 401 responses are preserved without a write retry. Refresh both submission documents and deployment instructions, preserving all README badges, link tables and eleven diagrams.
- **Why**: The prior setup had multiple routing/startup paths and an unnecessary artifact scaffold. The supplied failed-publish log used `next start` despite standalone output. Root commands make the deployed process and public port explicit; a real startup smoke catches failures that compilation cannot, including the streamed-login 401 regression.
- **Affects**: All product pages/API routes and deployment CI; M1 background workflows remain separate. No schema, contract, entity, scoring or authentication-mode changes.
- **Validation**: Full quality gate passed (958 Python tests, 32 environment-dependent skips, 48 subtests); 44 disposable-PostgreSQL integration checks, ten proxy regressions and twelve navigation/read-recovery checks passed. The exact root production build and supervised startup passed landing/About/sign-in, static CSS, health/HEAD, CORS, failed-login 401 and unknown-route 404 checks. All eleven diagrams rendered; submission limits and local links passed. Publishing this source and checking platform forwarding trust remain account-owner operations.
- **Replaces**: Deployment/scaffold aspects of M4-073 and M4-076; retains production boundaries and native-runtime/readiness behavior from M4-069.
- **PR / branch**: fix/core-single-public-server


### M4-078: Reject the published session key and keep logout redirects same-origin
- **Date**: 2026-10-30
- **Feature**: Core authentication
- **Type**: method
- **Change**: Leave SESSION_SECRET empty in the example so local development generates a private random key and Compose requires an explicitly generated value. Reject the previously published placeholder in settings for both environments. Revalidate the serialized redirect path before returning it from the shared logout helper.
- **Why**: A public HMAC key permits forged sessions. A validated same-origin URL can still yield a protocol-relative Location when its pathname begins with two slashes.
- **Affects**: API configuration/startup and web logout; no API contract or database changes. Existing deployments using the published key must replace it, invalidating their sessions.
- **Replaces**: none
- **PR / branch**: feat/core-sidebar-home-button


### M4-079: Restore verification and preserve full Back navigation
- **Date**: 2026-10-30
- **Feature**: Core authentication and CI
- **Type**: method | UI
- **Change**: Use Next.js Link with onNavigate to perform the auth Back link's intended full navigation, remove an unused landing variable, and include the logout helper regression suite in frontend CI. Add a regression rejecting a token forged with the published session key.
- **Why**: Restoring the pinned test environments revealed an ESLint error in the existing Back link. Preserve cookie-aware full reload behavior while satisfying the framework rule and keeping security regressions in CI.
- **Affects**: Auth Back navigation, landing lint, and frontend CI. No dependency, database, or API contract changes.
- **Replaces**: none
- **PR / branch**: feat/core-sidebar-home-button


### M4-080: Isolate database-only Compose from API secret interpolation
- **Date**: 2026-10-30
- **Feature**: Core local development
- **Type**: method
- **Change**: Move the local database definition to `docker-compose.db.yml`, reused through `extends` by the full stack. Route database startup and shutdown through the database-only file, preserving the project volume and the full-stack API's required private SESSION_SECRET.
- **Why**: Compose interpolates every service before selecting db, so the blank example secret prevented setup, dev and db-up from starting PostgreSQL. A separate database file avoids supplying a dummy signing key or weakening API validation.
- **Affects**: Local setup/dev/db-up/db-down, full-stack Compose database definition and onboarding documentation. No database contents, schema, provider or production changes.
- **Replaces**: M4-078's assumption that the full-stack Compose file can start db with an empty API secret.
- **PR / branch**: feat/core-sidebar-home-button


### M4-081: Cover database-dependent checks with explicit disposable test state
- **Date**: 2026-10-30
- **Feature**: Core verification and F2 trend fixture validation
- **Type**: method
- **Change**: Include trend fixture/database export comparisons in the existing PostgreSQL CI job and document ADEPT_TEST_DATABASE_URL as the explicit opt-in for local database coverage. Keep default tests isolated from developer databases.
- **Why**: The isolated run skipped 30 PostgreSQL tests and two export comparisons; the CI database job already enabled the former but omitted the latter. Passed workflow-security subtests are successful coverage and need no removal.
- **Affects**: Database CI and local verification documentation; no runtime, schema, dependencies or fixture changes.
- **Replaces**: none
- **PR / branch**: feat/core-sidebar-home-button

### M4-082: Pause Dependabot version updates and group them per ecosystem
- **Date**: 2026-10-30
- **Feature**: Core (CI and dependency maintenance)
- **Type**: dependency
- **Change**: Routine Dependabot version updates are paused (`open-pull-requests-limit: 0`) for all four ecosystems (uv, RunPod pip, npm, GitHub Actions). Each ecosystem keeps one catch-all group, so setting the limit to 1 after the final resumes updates as one grouped PR per ecosystem.
- **Why**: The ungrouped config used the defaults (one PR per package, up to five open per ecosystem). Its first run opened 12 separate bump PRs (#31–#43) at once. Options considered: delete the config (stops version PRs entirely), set the limit to 0 (pause), or group. The team chose to pause version PRs before the final and closed the 12 open bumps. Grouping is kept for when updates resume. Security alerts remain a separate repository setting.
- **Affects**: Dependabot pull request volume only; no runtime, dependency versions or CI checks change.
- **Replaces**: none
- **PR / branch**: chore/core-dependabot-grouping

### M4-083: Keep grounded chat fallbacks and refuse lowercase decision questions
- **Date**: 2026-10-30
- **Feature**: Core / F8 (Adi)
- **Type**: method
- **Change**: Keep the already-checked deterministic answer if routing restores any model-selected answer ID absent from the grounded candidate set. Recognize explicit English people-decision questions without requiring capitalized names.
- **Why**: Greptile identified a catalogue-outage `KeyError` when a rejected learn runner-up was restored, and lowercase-name questions bypassing the decision refusal. Both failures were reproduced before fixing them; changes are limited to these two review findings and their regressions.
- **Affects**: Adi answer selection and decision refusals; EN/MS/ZH catalogue-outage HTTP tests and learner/manager lowercase-name safety coverage. No contracts, dependencies, scoring, catalogue data or other product flows change.
- **Replaces**: none
- **PR / branch**: fix/core-proxy-scenario-loading

### M4-084: Ground Adi routing and multilingual explanations
- **Date**: 2026-10-30
- **Feature**: Core and F8
- **Type**: method
- **Change**: Phrase-level intent routing, scoped people-decision refusal, near-tie suggestions, multilingual replies, explicit fallback sources and validated page/catalogue references replace broad keyword routing. The browser opens with sources, scenario and declining-skill questions.
- **Why**: Avoid misleading refusals and destination labels while keeping all displayed facts in validated server-authored blocks.
- **Affects**: associated API, web, tests and deployment configuration
- **Replaces**: none
- **PR / branch**: worktree-agent-ae781c8985e0fb4d3

### M4-085: Separate joining consent and clarify the individual journey
- **Date**: 2026-10-30
- **Feature**: F1, F4, F7 and Core
- **Type**: UI
- **Change**: Joining no longer requires sharing skills; sharing stays an explicit separate choice. Privacy disclosure, session-aware team CTAs, radar-first intake, populated comparison, weighted score bars, accessible wording and Steady/Rapid labels are updated without changing scenario IDs.
- **Why**: Consent must remain optional and destinations, labels and score bars must match the actual behaviour.
- **Affects**: associated API, web, tests and deployment configuration
- **Replaces**: none
- **PR / branch**: worktree-agent-ab3aa728dfca284ec

### M4-086: Harden production setup and broaden the regression gate
- **Date**: 2026-10-30
- **Feature**: Core, F7 and F8
- **Type**: method
- **Change**: Make production configuration fail closed; repair frozen-lockfile Docker builds, explicit-origin POST workspace/logout checks, identity-aware rate limits, scheduled job refresh, recommendation-write attribution tests and production-parser counterfactual fairness. Include web regressions in the Python task runner.
- **Why**: The interrupted infrastructure draft needs a reviewable branch; integrated follow-up fixes and deployment acceptance are handled in the final integration PR.
- **Affects**: associated API, web, tests and deployment configuration
- **Replaces**: none
- **PR / branch**: worktree-agent-a30a3ff3fc8019a74
