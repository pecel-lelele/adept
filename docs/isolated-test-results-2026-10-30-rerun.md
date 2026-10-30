# Isolated fixes — test rerun and failure reasons

Date: 30 October 2026. This is a new test report; existing source, tests, manifests and
pre-existing documentation were not edited during this rerun. No Git mutation was performed.

## Result

The implemented changes passed the local automated suites. A separate diagnostic reproduced
the explicitly deferred **T5 empty-jobs freshness bug**. Legacy Docker defects remain, as
expected for the read-only T10 investigation. Neither is concealed by the passing suite.

| Check | Observed result |
|---|---|
| Full Python suite (`pytest -ra`) | **1013 passed, 32 skipped, 48 subtests passed**, one existing warning; 71.20 seconds |
| Python baseline comparison | Previously 980 passed and 32 skipped; no reduction in passing tests |
| All six local Node test files, excluding HTTP-only file | **32 passed**, zero failed/skipped |
| Privacy HTTP checks against rebuilt local frontend | **3 passed**: EN/MS/ZH each returned 200 with translated headings and footer link |
| Ruff lint | Passed |
| Ruff format validation | Passed; 334 files already formatted |
| ESLint | Passed |
| TypeScript | Passed |
| Translation-key parity | Passed |
| Frontend production build | Passed; `/privacy` included in route output |
| OpenAPI and generated TypeScript comparison | Both matched tracked files; generation used temporary files only |
| `git diff --check` | Passed; existing CRLF normalisation warning is not a test failure |

The Python suite used local/CSV fixtures, with the PostgreSQL opt-in removed and AI providers
disabled. No live job source, model, production database, GitHub workflow or Dependabot run
was invoked. The temporary frontend bound only to `127.0.0.1:3107` and was stopped afterward.

## Per-task findings

| Task | Test result | Reason for any remaining failure or limit |
|---|---|---|
| T1 — PDF limits | Passed in the full suite | Includes generated 500-page rejection, normal PDF, public endpoint, timeout cleanup and busy-parser tests. This Windows run does not verify Linux resource-limit behaviour. |
| T2 — jobs location | Passed in the full suite | Foreign primary-location fixtures are excluded despite Malaysian offices; Malaysian/remote-Malaysian fixtures remain. Stored/live postings were not refreshed. |
| T3 — RunPod cancellation | Passed with mock HTTP transport | Timeout/error cancellation, success without cancellation, cancellation-error preservation and cross-batch deadline checks passed. Actual provider cancellation/billing requires an authorised live test. |
| T4 — workflows | Both YAML syntax tests passed | No workflow dispatch was run. Syntax does not verify missing-secret failure, frozen dependency installation, publisher failure propagation or GitHub job summary behaviour. |
| T5 — empty jobs freshness | **Separate diagnostic failed the desired no-data expectation** | `_meta([], "moderate")` still uses today's date. This fix was explicitly deferred because shared metadata requires a date and the contract is owned by the other engineer. |
| T6 — dead assets | Both Node assertions, TypeScript and build passed | No global insight import or unused panel remains. Automated compilation is not visual regression coverage. |
| T7 — privacy | Static checks, parity, build and three real HTTP checks passed | Controller/contact placeholders and actual provider/region/retention details still require team completion; HTTP success does not establish legal compliance. |
| T8 — counterfactual harness | Dummy-query unit tests passed | Production matching evaluation was deliberately not run while scoring is changing. No fairness-result logs or fairness evidence were generated. |
| T9 — Dependabot | YAML parse and ecosystem coverage test passed | Actual update discovery/PR generation depends on GitHub after human merge and repository configuration. No remote setting was accessed or changed. |
| T10 — Docker | Static defects reconfirmed; no image build/start | The specified task remains read-only. Missing lockfile and automatic migration/seed problems are described below. |

## T5: reproduced failure

The read-only diagnostic called the existing `_meta` function with no posting records.
It did not query a database or modify a file.

```text
Empty jobs metadata uses today: True
No-data date indicator: False
AssertionError: T5 remains unresolved: empty jobs metadata has a date instead of a no-data indicator
```

The diagnostic intentionally asserted the requested future no-data behaviour and exited 1.
This is separate from the unchanged repository suite, which currently does not catch that
expectation. The source still computes its empty default using `date.today()` and creates
a pipeline source with that date. An empty dataset therefore appears to have a dated snapshot.

No fix was applied: the user chose **“Tunda T5 sampai kontrak siap”**. Coordinate the shared
nullable/no-data metadata contract first; keep `jobs/service.py` and forbidden contracts
untouched until that decision is resolved.

## Why 32 Python tests were skipped

- **30 cases** require `ADEPT_TEST_DATABASE_URL`, which was deliberately not set. These
  cover PostgreSQL rate limits, accepted learning levels, reference data, plan storage/sync,
  database recovery and jobs refresh.
- **2 cases** compare frozen trend fixtures against a PostgreSQL export and reported
  PostgreSQL unavailable.

These are unexecuted integration checks, not passing checks. No new skip marker or weakened
assertion was introduced. Running them requires an explicitly selected disposable test
database with the expected schema and fixtures; no ambient `.env` database was used.

## T10: confirmed legacy Docker problems

Read-only checks returned:

```text
Test-Path src/web/pnpm-lock.yaml -> False
src/docker/web.Dockerfile:4 -> COPY src/web/package.json src/web/pnpm-lock.yaml ./
src/docker/boot.py:11 -> runs src/db/migrate.py and src/db/seed.py
src/docker/api.Dockerfile:13 -> starts src/docker/boot.py
```

The web image references a missing build input; the real pnpm lockfile is at repository root.
The legacy API boot path unconditionally migrates/seeds whichever database is configured.
No Docker build or boot was attempted, so there is no claimed runtime Docker test result.
The existing [implementation manifest](isolated-fixes-manifest.md#t10--docker-investigation-read-only)
records the additional workspace/standalone-path concerns and removal-versus-rebuild options.

## Warnings and checks that remain outside this run

- The existing FastAPI/Starlette test-client deprecation warning did not fail pytest.
- `next start` warned about the repository's standalone-output configuration. It nevertheless
  served all three local HTTP tests; this does not verify the actual deployment launcher.
- Git reported an existing CRLF-to-LF normalisation warning in pre-existing `rubric-check.md`.
  That file was not edited and `git diff --check` passed.
- Linux PDF limits, visual layout checks, staging/live provider behaviour, manual workflow
  dispatch and remote Dependabot operation remain unverified rather than passed.

## Commands used

The main checks were:

```text
.venv\Scripts\python.exe -m pytest -ra
.venv\Scripts\python.exe src/scripts/dev.py lint
.venv\Scripts\python.exe src/scripts/dev.py typecheck
.venv\Scripts\python.exe src/scripts/dev.py i18n-check
.venv\Scripts\python.exe tmp/isolated_contract_check.py
node --experimental-strip-types --test tests/web-proxy.test.ts tests/web-navigation.test.ts tests/web-api-recovery.test.ts tests/profile-skill-search.test.ts tests/dead-assets.test.mjs tests/privacy-page.test.mjs
node node_modules/next/dist/bin/next build --webpack
node --test tests/privacy-http.test.mjs
git diff --check
```

The build ran from `src/web`; HTTP tests ran only while the temporary loopback frontend
was running. Environment isolation and synthetic configuration were set before execution.
No source fixes, dependency installation, migration, seed, commit, push or deployment occurred.

Suggested report-only commit: `docs(qa): record isolated fix rerun and deferred failures`.
