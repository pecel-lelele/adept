# Synthetic CV HTTP flow verification - 30 October 2026

All five signed-in journeys passed through the actual FastAPI HTTP server. Guest preview
availability is not fully green: a trend lookup exceeded its two-second deadline while the
test database was deliberately unavailable. This report does not claim production or browser
verification, a measured human planning-time improvement, or complete skill-gap coverage.

## Execution boundary

- New test: `tests/integration/test_synthetic_cv_http_flow.py`.
- Existing five labelled fictional PDFs and intake settings in `docs/demo-cvs/` were reused.
- Uvicorn ran the unmodified application on an ephemeral `127.0.0.1` port.
- Real HTTP multipart uploads, password hashing, sign-up, login and signed-token verification
  ran without mocks of the parser, matcher, planner or authentication service.
- `AUTH_RAW_USER_IDS=false` and an empty default user disabled test identity shortcuts in
  the child API. Each learner received a new account and signed sessions.
- `M3_BACKEND=csv` provided disposable process-local stores and seed catalogues. The database
  address was explicitly set to unreachable loopback port 1. No ambient database was used.
- Language models, embeddings and sync credentials were disabled for the child. No live
  job feeds, model inference, migrations, seeding or external account changes ran.
- The frozen snapshot actually returned by the flow was **2026-10-20**. No freshness claim
  was inferred from the request date.
- The child API was stopped in fixture cleanup; its final port, 63866, refused connections
  after the approved run. Sessions and saved plans disappeared with its memory stores.

## Signed-in journey checked for every CV

1. Sign up, then retrieve the account using its signed token.
2. Confirm the new account starts without a saved plan.
3. Submit the documented synthetic questionnaire assumptions.
4. Upload the real PDF bytes using multipart HTTP; verify expected catalogue skills and
   absence of truncation.
5. Verify upload alone does not save skills.
6. Submit the explicitly reviewed synthetic skills from `profiles.json`, then read them back.
   This deliberately excludes the known over-broad reconciliation aliases described in
   the demo README. It is a scripted review fixture, not a human competence assessment.
7. Request matches for both moderate and fast scenarios; check sources and estimate metadata.
8. Explicitly select the case's existing catalogue target role, generate its plan and check
   that recommended course IDs resolve in the actual catalogue response.
9. Check the plan respects the case's study hours and reports within-budget status.
10. Save the plan, log in again, and verify the complete saved object reloads unchanged.

## Final approved-run results

| Synthetic CV | Extracted / confirmed skills | Chosen target | Steps | Estimated weeks | Unmet gaps | Signed-in save/reload | Guest preview |
|---|---:|---|---:|---:|---:|---|---|
| Imran Hakim | 6 / 6 | compliance-analytics-officer | 1 | 1 | 1 | Pass | Pass |
| Sofia Tan | 7 / 6 | process-automation-analyst | 4 | 1 | 2 | Pass | Pass |
| Meera Anand | 5 / 4 | logistics-supervisor | 2 | 1 | 3 | Pass | Pass |
| Adrian Lim | 4 / 4 | data-analyst | 3 | 2 | 1 | Pass | Pass |
| Nur Hana | 6 / 4 | bank-operations-executive | 1 | 1 | 3 | Pass | Fail: HTTP 503 |

All five selected plans reported MYR 0 out-of-pocket in this frozen catalogue. Their unmet
gaps remain visible; saving a plan does not imply the catalogue can close every gap. Both
scenario requests succeeded in the signed-in flows. The top role happened to be identical
between scenarios for these inputs; no scenario-ranking improvement is claimed.

| Additional check | Result |
|---|---|
| Generated 500-page PDF sent to the real anonymous upload endpoint | HTTP 422, `pdf_too_many_pages` |
| New HTTP test group in the approved full run | 10 passed, 1 failed |
| Full Python suite | **1030 passed, 32 skipped, 1 failed; 54 subtests passed**, 85.87 s |
| Python warning | One existing FastAPI/Starlette TestClient deprecation |
| Ruff lint and format, ESLint | Pass |
| TypeScript (`tsc --noEmit`) | Pass |
| EN/MS/ZH translation-key parity | Pass |
| Contract generation into temporary files compared with tracked artifacts | Pass; tracked contracts unchanged |
| Existing web Node regression group | 32 passed, zero failures |
| `git diff --check` | Pass; pre-existing CRLF normalisation warning only |

Thirty skipped cases require an explicitly supplied PostgreSQL test database; two compare
against an unavailable PostgreSQL export. They remain unverified, rather than passed.
Frontend build, browser clicks, privacy HTTP rendering and deployment were not rerun here.

## Failure and diagnosis

The failing test is:

```text
tests/integration/test_synthetic_cv_http_flow.py::test_synthetic_guest_pdf_preview[demo-nur-hana]
POST /api/v1/preview/cv?include_suggestions=false -> HTTP 503
code: trend_unavailable
message: Trend snapshot for scenario 'moderate' timed out after 2s - M1 service may be unavailable.
```

The message above uses an ASCII dash for readability. The original response is retained as
a JUnit test property in `tmp/synthetic-cv-full-suite-approved-results.xml`.

Observed: the PDF reached the preview route but no preview result was returned; the error
specifically identifies trend retrieval, not a page-limit rejection. Earlier targeted runs
failed on different CVs while other cases completed, so the failure is intermittent and
not tied to Nur Hana's PDF contents.

Code-based explanation: guest preview calls `matching.trend_port.fetch_snapshot`, whose
adapter waits two seconds. Trend source resolution first attempts the database before
falling back to a frozen fixture, and fixture/negative caches expire after five seconds.
With the deliberately unavailable database, that resolution can consume the adapter's
deadline. This is consistent with the captured timeout, including after cache expiry.
It is not evidence that a healthy production database has the same failure.

No retry, warm-up, increased timeout, skip, changed expected status or removed assertion was
added to conceal this result. The failing regression is retained. Repairs require reviewing
the reserved matching/trend fallback paths with the other engineer; they were not edited.

An initial full run inside the sandbox also encountered Windows temporary-directory and
PDF-worker permission errors: 1008 passed, 32 skipped, 11 failed and 12 setup errors.
The approved rerun removed those permission errors and left only the trend timeout above.
The sandbox result is not treated as a source regression or as a successful quality gate.

## Reproduce

Run from the repository root with the existing environment and dependencies:

```powershell
Remove-Item Env:ADEPT_TEST_DATABASE_URL -ErrorAction SilentlyContinue
$env:ADEPT_TEST_M3_BACKEND='csv'
$env:LLM_PROVIDER='none'
$env:EMBEDDINGS_PROVIDER='none'
.venv\Scripts\python.exe -m pytest tests/integration/test_synthetic_cv_http_flow.py -o junit_family=xunit1 --junitxml=tmp/synthetic-cv-http-flow-results.xml
```

To reproduce the full approved result, replace the test path with `-ra` and use a separate
JUnit output file. Windows needs permission for temporary directories, subprocesses and
PDF-worker pipes. Use the supported approval mechanism when the sandbox denies them.
The test starts/stops its own isolated API and never attaches to a running deployment.
Do not set `ADEPT_TEST_DATABASE_URL` to an ambient or production database.

## Scope and remaining limits

Only this report and the new HTTP test were added for this request. All pre-existing
modified/untracked work was preserved, including the cumulative safe-fix list. No runtime
source, shared locale, dependency, workflow, migration, session file or scoring code changed.
No Git mutation, commit, branch, push, PR or external message was performed.

This is a real backend HTTP flow with disposable memory persistence. It does not exercise
Next.js file-picker interaction, cookies/proxy/server actions or PostgreSQL persistence
across a process restart. Automated request durations cannot populate the human KPI study;
the manual comparator and tester trials are still outstanding. MyCOL remains reference-only
and was not connected to ranking or badges during the test.

Suggested human commit message after reviewing the failing regression:
`test(profile): exercise synthetic CV journeys over loopback HTTP`.
