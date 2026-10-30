# Isolated fixes manifest

Scope: current working tree only. No Git mutation, remote operation, migration, seed or live
inference is authorised or performed. Pre-existing files below are preserved without edits.

## Step 0 — pre-existing changes

```text
 M README.md
 M docs/README.md
 M docs/demo-script.md
 M docs/project-context.md
 M docs/rubric-check.md
 M docs/submission-proposal.md
 M docs/submission-technical-declaration.md
?? .qoder/
?? docs/a-safe-work-status.md
?? docs/daftar-perbaikan-aman.md
?? docs/submission-deliverables.md
```

Baseline on Python 3.11.17: 980 tests passed, 32 skipped, 48 subtests passed, one existing
Starlette deprecation warning. Ruff check/format, ESLint, TypeScript and i18n parity passed.
Initial pnpm commands required sandbox escalation for cache/registry access. An initial test
attempt mistakenly enabled optional PostgreSQL tests on an unreachable dummy address; it was
stopped and rerun with the opt-in variable removed. No live database was contacted.

## Task results

### T1 — public PDF limits

- Files: `src/api/app/features/profile/cv_parser.py`,
  `src/api/app/features/preview/router.py`, `tests/api/profile/test_pdf_public_limits.py`.
- Red first: four new failures, two passes. The generated 500-page PDF was accepted before
  the fix. Green: six new tests passed; all profile/preview tests passed (221 total).
- Reject PDFs above the existing module-level 30-page cap. Public PDF preview uses a
  short-lived subprocess with a five-second deadline, two concurrent slots and 384 MiB memory
  cap (POSIX resource limits; Windows Job Object), plus CPU limits. Timeout kills and joins
  the process. Errors use existing AppError envelopes and codes; no new router message text.
- Python extraction retains at most the text limit plus one character, preserving truncation.
- Ruff/ESLint and i18n passed. Windows subprocess tests required escalation after sandbox
  denial of named-pipe access. Linux resource-limit behaviour still needs CI verification.
- Ownership check: only the two allowed source files and a new test were changed; no
  forbidden/pre-existing file was edited. `git status --short` and `git diff --stat` reviewed.

### T2 — posting location precedence

- Files: `src/pipelines/jobs/sources.py`, `tests/pipelines/jobs/test_primary_location.py`.
- Red first: 13 failures and two passes. Green: all 15 new cases passed; jobs pipeline suite
  73 passed, one optional database test skipped. The same baseline tests remain enabled.
- Use the first nonempty posting location, with word boundaries and MY/MYS country codes.
  Lever no longer joins every alternative location into its primary location. Foreign primary
  locations cannot be overridden by offices in Malaysia. No live feed refresh was run.
- Ruff/ESLint and i18n passed; ownership/status/diff review found only allowed/new files.
- `data-sources.yml` was not needed for this fix; dependency installation changes belong to T4.

### T3 — RunPod cancellation and run budget

- Files: `src/pipelines/trends/encoder.py`,
  `tests/pipelines/trends/test_encoder_cancellation.py`.
- Red first: three failures and one pass; an additional cancellation-failure regression was
  also observed failing before its fix. Green: five new cases; trend pipeline suite 93 passed,
  two skipped, 48 subtests passed. Ruff/ESLint and i18n passed.
- One encode deadline covers all batches. Pending known-ID jobs receive cancellation in
  `finally` on timeout/error, but completed jobs do not. Cleanup failure preserves and annotates
  the original error. Submission includes provider-side execution/TTL bounds for lost-ID cases.
- RunPod's documented minimums are five seconds execution and ten seconds TTL; cancellation
  is best effort on network failure. No live inference/billing outcome is claimed.
- API reference: https://github.com/runpod/docs/blob/main/serverless/endpoints/operation-reference.mdx
  and endpoint-configurations.mdx. Credentials, endpoint configuration and worker are unchanged.
- Ownership/status/diff review found only the allowed encoder and a new test file.

### T4 — workflow configuration (not verifiable locally)

- Files: `.github/workflows/trends-refresh.yml`, `.github/workflows/data-sources.yml`,
  `tests/test_isolated_workflow_yaml.py`.
- Manual refresh fails when any required configuration is empty; values are never printed.
  Scheduled runs retain the explicit skip notice. Successful publication extracts the date
  from the publisher confirmation into the job summary, with pipefail preserving failures.
- Both workflows install from the existing `uv.lock` with `uv sync --frozen --python 3.11`
  and invoke the resulting virtualenv. The setup-uv action uses the existing CI pin.
- Per T4's explicit syntax-only exception, both YAML syntax tests passed before and after;
  no local behavioural workflow execution or red/green dispatch is claimed. Lint/i18n passed.
- Human must dispatch in a disposable/staging context: missing configuration fails without
  revealing values; frozen install succeeds; preflight/publisher failure stays red; successful
  publication writes the actual published date to the summary. Live dispatch is not run here.
- `data-sources.yml` is changed only by T4, so no T2/T4 source overlap occurred.
- Ownership/status/diff reviewed; no remote setting, secret or workflow dispatch changed.

### T5 — blocked / deferred by user

- No source or test changes. `RecommendationMeta.snapshot_date` requires a real date.
  A nullable no-data response would require the forbidden shared contract. The user explicitly
  chose to defer T5 rather than return HTTP 503 with `jobs_no_data`.
- `jobs/service.py`, `pathway/service.py` and all shared metadata contracts remain untouched.

### T6 — unused assets

- Files: remove `src/web/src/features/core/components/SkillBankPanel.tsx` and
  `src/web/src/app/insight.css`; remove only the latter import from `src/web/src/app/layout.tsx`;
  add `tests/dead-assets.test.mjs`.
- `rg` found no panel import and only the root-layout import of insight.css. The layout is
  neither forbidden nor pre-existing work. No forbidden stylesheet was edited.
- Red first: two assertion failures; green: both Node tests pass. TypeScript, lint and i18n
  passed. No test is disabled; Node required escalation for sandbox-denied subprocess access.
- Ownership/status/diff reviewed. Human should visually check legacy public/admin layouts
  after removal of the global overrides; compilation is not visual verification.

### T7 — privacy notice

- New files: three `src/web/messages/{en,ms,zh}/privacy.json` files; thin
  `src/web/src/app/privacy/page.tsx`; feature `src/web/src/features/privacy/` with its own CSS
  module; `tests/privacy-page.test.mjs` and `tests/privacy-http.test.mjs`.
- Minimal shared edits: add one namespace entry to `src/web/src/lib/i18n/config.ts`;
  add an import and type member to `src/web/src/lib/i18n/global.d.ts`; add a translation
  lookup and one footer link in `src/web/src/components/shell/Site.tsx`. No footer styling,
  signup/join form, existing locale file, or forbidden CSS was changed.
- Red first: four route/locale checks failed. Green: four static checks, three HTTP 200
  locale/render checks, i18n parity, lint, TypeScript and the frontend production build passed.
- A temporary frontend served only 127.0.0.1:3107 using synthetic configuration; it was stopped
  after HTTP tests. No API server/database/model was started. The Next start command emitted
  its standalone-output warning but served all three tested pages successfully.
- Code traces: profile upload/parser and `core/embeddings.py` for transient CV parsing and
  redacted Google skill phrases; assistant service and LLM provider for conversation/context;
  accounts router for export/deletion. Deployment config supplies Replit/PostgreSQL architecture.
- Rights reference: https://www.pdp.gov.my/ppdpv1/en/data-subject-rights/ . This is a notice,
  not a claim of legal certification or provider/backup erasure guarantees.
- Human must fill controller/contact placeholders and confirm actual hosting regions,
  provider terms and retention before real personal-data use. No assertion about consent
  defaults, freshness/fallback, or proxy behaviour is included.
- Ownership/status/diff reviewed; pre-existing work and all forbidden paths preserved.

### T8 — prepared matching counterfactual harness

- New files only: `src/pipelines/guardrails/matching_counterfactual.py` and
  `tests/pipelines/guardrails/test_matching_counterfactual.py`.
- Builds five synthetic profile variants: baseline, separate age/gender/background swaps,
  and a combined swap. Profile reads are temporarily substituted in the standalone harness;
  the default calls the unchanged production matching service API at a fixed snapshot.
- Compares complete ordered matches, including scores; rejects empty output and mismatched
  snapshots. Does not save profiles, duplicate scoring, print results or create result logs.
- Red first: four failures before implementation. Green: four dummy-query tests passed;
  all guardrails pipeline tests passed (six total). Lint and i18n passed.
- Production-query evaluation was NOT run. These unit results are not fairness evidence.
  Existing matching already has demographic-swap regressions; this adds a reusable harness,
  not proof that the earlier review's lack-of-coverage claim was current.
- Ownership/status/diff reviewed; no existing matching/scoring/test file was edited.

### T9 — Dependabot preparation

- New files only: `.github/dependabot.yml` and `tests/test_dependabot_config.py`.
- Weekly updates cover root `uv.lock`, the separate pip MiniLM worker requirements, the
  root pnpm workspace via the npm ecosystem, and GitHub Actions. No duplicate root pip job
  competes with uv for the same Python project. No existing workflow changed in T9.
- Red first: missing configuration failure. Green: configuration parse/coverage test and
  both workflow syntax tests passed; lint/i18n passed. YAML parsing is not remote validation.
- Official references: https://docs.astral.sh/uv/guides/integration/dependabot/ and
  https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference .
- Human must review Dependabot diagnostics after merging to the default branch and separately
  confirm repository alert/security-update settings. No remote setting or update PR was created.
- Ownership/status/diff reviewed; only the new configuration/test are in this task.

### T10 — Docker investigation (read-only)

- No Docker file was changed, built or executed. Searches of README, Makefile, docs, CI,
  root `.replit`, package scripts and development scripts found no reference to `src/docker/`,
  `web.Dockerfile`, `api.Dockerfile` or `docker/boot.py`. The only direct internal reference
  is `src/docker/api.Dockerfile:9,13`, which copies and invokes `src/docker/boot.py`.
- README references the root database-only compose file at line 113; Makefile delegates to
  `src/scripts/dev.py`. Root compose starts only PostgreSQL, not these API/web images.
- `web.Dockerfile:4` copies `src/web/pnpm-lock.yaml`, which does not exist. The actual lockfile,
  workspace file and root package manager pin are at repository root. Copying only the web
  directory also omits root workspace/build-script inputs. Node 22 differs from CI's Node 24.
- The web runtime copies standalone output straight into the working directory and expects
  a top-level `server.js`, whereas configured tracing is rooted at the monorepo root. A
  rebuilt image must validate the nested standalone layout and static/public asset paths.
- `api.Dockerfile:4-9` installs loose requirements and omits `src/pipelines`, unlike the root
  deployment layout. `boot.py:11-12` runs migrations and seed unconditionally before API
  startup, against whichever database environment is supplied. It then binds to 0.0.0.0.
- Option A: remove these unused legacy files in a separately authorised change. Risk:
  out-of-repository users/manual commands may still depend on them despite no tracked caller.
- Option B: rebuild a documented offline-backup profile using root lockfiles/workspace,
  correct standalone paths/assets, complete API inputs, loopback host mappings, and explicit
  separate migration/seed operations against a verified disposable database. Risk: a second
  deployment path adds maintenance and needs actual image/build/start/security tests; model
  downloads or live migrations must never occur implicitly at boot.

This manifest is a shared audit artifact updated sequentially for each task. No source-file
overlap between tasks is intended. T4 owns any workflow dependency edits, including
`data-sources.yml`; T2 will not modify that workflow unless its filtering fix requires it.

## Explicit exclusions

Do not edit `.env.example`, README/test counts, `pathway/service.py` freshness, shared locale
wording, `docs/decisions.md`, or any Phase 1–3 owned file. Do not run matching counterfactual
evaluation as fairness evidence or save its run logs while scoring is changing.

## Final verification and staging guide

- Full final suite: **1013 passed, 32 skipped, 48 subtests passed**, versus baseline
  **980 passed, 32 skipped, 48 subtests passed**. Net addition: 33 passing Python cases;
  no baseline tests were removed, skipped or weakened. Existing Starlette warning remains.
- Ruff check/format, ESLint, TypeScript and i18n passed. The production frontend build passed.
- Node regression/static checks: 18 passed, plus three real HTTP privacy locale checks.
- Contract drift: generated OpenAPI and TypeScript into an owned `tmp/isolated-contract-*`
  directory and compared both against tracked artifacts; both matched. Tracked generated
  files were never overwritten. This safely replaces the mutating contract-generation step.
- `git diff --check` passed. Pre-existing document diff statistics remain unchanged. All
  editing/formatting commands targeted only task-owned paths; no forbidden path was edited.
- The temporary frontend stopped after testing; no task-owned server remains on port 3107.
- No Git state-changing command, `.git` edit, remote setting change, commit, push, PR,
  database mutation, paid inference, live pipeline or workflow dispatch was performed.

| Task | Status | Human verification |
|---|---|---|
| T1 | done locally | Linux resource-limit behaviour and public PDF errors in staging |
| T2 | done | Review refreshed rows only after a separately authorised feed run |
| T3 | done with mocks | Cancellation/billing behaviour in an explicitly authorised provider test |
| T4 | not verifiable locally | Manual dispatch checks listed above |
| T5 | blocked / deferred | Coordinate nullable metadata contract; user chose to wait |
| T6 | done | Visual check after removal of legacy global overrides |
| T7 | done locally | Fill controller/contact and confirm operational/provider facts |
| T8 | prepared; evaluation deferred | Run only after scoring settles; unit results are not fairness evidence |
| T9 | done locally | Review Dependabot diagnostics/settings after human merge |
| T10 | investigation done | Choose removal or rebuild separately; Docker files remain unchanged |

Stage only the per-task file lists in this manifest, never all workspace changes. The new
manifest is a common audit artifact rather than a source dependency between tasks. Neither
T2 nor another task edited T4's workflow files. Suggested human commit messages:

- T1: `fix(profile): bound public PDF parsing resources`
- T2: `fix(jobs): respect primary posting location`
- T3: `fix(trends): cancel abandoned encoder jobs`
- T4: `fix(ci): fail incomplete manual trend refreshes and use frozen installs`
- T6: `chore(web): remove unused legacy assets`
- T7: `feat(core): add translated privacy notice`
- T8: `test(matching): prepare isolated counterfactual harness`
- T9: `chore(deps): configure weekly Dependabot updates`
