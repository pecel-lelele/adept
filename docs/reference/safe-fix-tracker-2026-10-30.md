# Archived safe-fix tracker - 30 October 2026

This is a shareable historical snapshot of the locally maintained
`docs/daftar-perbaikan-aman.md` used by the [ownership handoff](../issue-ownership-and-conflict-analysis.md).
The original local file is excluded by `.gitignore`; it was not part of PR #30.
The source bytes have SHA-256 `b6889b9998d12a26fc8d816690c2e02d2adcdcd87fcdb41f9c3b6ca4e9aa4600`.

The historical statuses, dates, test counts and unresolved failures below are
preserved as recorded. In particular, statements that work was uncommitted are
historical statements, not the current repository state or fresh validation.
This archive does not independently reproduce the original measurements.

Publication edits are limited to this introduction and link destinations: links
to files included in PR #30 resolve to immutable commit `ff04b64b9b1b330922f797f0a3498f06c2e20990`;
unpublished local-only drafts are labelled as such rather than linked to missing files.
Line endings are normalized to LF for repository storage.
No private credentials or real CV data are included.

---

# Safe Fixes and Verification Log

Date: 30 October 2026. Code base: `8bb8115`.

This log distinguishes completed fixes, preparation that has not been integrated,
and work that has not been done. All changes remain uncommitted.

## 1. A1 — Offline KPI measurement tools

**Implementation complete; human measurements have not been collected.**

- The calculator reads JSON trial records without accessing the application, `.env`, database or models.
- It calculates trial counts, failures, the percentage of valid plans, median time and the
  reduction between paired manual/Adept medians where both plans are valid.
- It provides an empty template for 5 synthetic CVs × 3 testers × 2 workflows = 30 trials.
- It provides a stopwatch protocol, counterbalanced trial order and reviewer assessment of validity.
- Empty data does not produce a baseline or a claim that the 20% target has been achieved.
- Account creation time is not used as a substitute for the start of intake.

Branch: `feat/a1-offline-planning-kpi`.

Files in a separate checkout:

- [Calculator](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/src/scripts/kpi_time_to_plan.py)
- [Measurement protocol](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/kpi-time-to-plan.md)
- [Trial template](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/kpi-trials-template.json)
- [Calculator tests](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/tests/scripts/test_kpi_time_to_plan.py)

The `tmp/` links above work only in this local workspace. The A1 files are in a separate
Git worktree and are not automatically included in a commit on the documentation branch.

## 2. A2 — Presentation tool declarations and statistical sources

**Documentation updated; final assets still need confirmation.**

- Added section 4.4, “Content and presentation tools”.
- Recorded Kokoro TTS, Remotion 4.0.538, Mixkit and ElevenLabs according to the supplied prompt.
- Distinguished information from the prompt, repository evidence and unverified asset/version details.
- Referenced the existing MiniLM, job feed, BNM and O*NET declarations without duplicating them.
- Recorded the limitations of the undocumented Workday interface.
- Added a source register, publication/event dates and interpretation limits for demo statistics.
- Corrected the WEF narrative so that not all projected job changes are attributed solely to AI.
- Marked application figures in the storyboard as historical examples that must be recorded again.

Files:

- [Technical declaration](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/submission-technical-declaration.md#44-content-and-presentation-tools)
- [Demo script and evidence register](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/demo-script.md#evidence-register)

## 3. A3 — Final rubric context and checklist

**Documentation partially updated; official final criterion names still require the participant handbook.**

- Replaced the old self-assessment with an evidence checklist for final-round preparation.
- Recorded the six weights from the prompt: 25/25/20/15/10/5, without inventing criterion names.
- Identified the four-criterion rubric as historical preliminary-round guidance.
- Added a final checklist reference to the proposal while preserving formatting and word-limit markers.
- Retained the Replit description that was already correct in the code base; did not repeat that fix.
- Separated KPI targets, local evidence and deployment verification that is still required.

Files:

- [Rubric check](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/rubric-check.md)
- [Project context](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/project-context.md#10-judging-context)
- [Submission proposal](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/submission-proposal.md)

## 4. A4 — CV and deliverable links

**Local links fixed; anonymous access to external media has not been verified.**

- Corrected links to the five synthetic CVs from `submission/demo-cvs/` to `docs/demo-cvs/`.
- Replaced the reference to the missing `submission/README.md` with a new deliverable checklist.
- Removed the hyperlink to the gitignored local video workspace.
- Referenced the video/slide folders already listed in the README, without uploading or changing sharing.
- Marked existing PDFs as historical exports that were not updated by this work.

Files:

- [Project README](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/README.md)
- [Documentation index](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/README.md)
- [Submission proposal](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/submission-proposal.md)
- [Technical declaration](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/submission-technical-declaration.md)
- [Demo script](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/demo-script.md)
- [New deliverable checklist](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/submission-deliverables.md)

## 5. A5 — README timezone correction

**Only the text correction is complete.**

- Changed the workflow schedule label from WITA to MYT.
- Did not change the workflow schedule, test counts, `.env.example` or Dependabot.

File: [Project README](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/README.md).

## 6. A14 — MyCOL reference preparation

**Preparation only; no completed badge or scoring integration.**

- Created a JSON reference containing nine occupation groups from indexed official brochure excerpts.
- Included the 2024/2025 edition, sources, verification date and source-access limitations.
- Marked the list as an incomplete MyCOL extract with an unknown publication date.
- Placed the reference outside the runtime seed directory.
- Did not add role mappings, MASCO mappings, badges or score weights.

Branch: `docs/a14-mycol-reference`.

Files in a separate checkout, accessible only through links in this local workspace:

- JSON reference (`../tmp/a14-mycol-reference/docs/reference/critical-occupations.json`; local-only draft, not published)
- Source notes and usage limits (`../tmp/a14-mycol-reference/docs/reference/README.md`; local-only draft, not published)

The full source PDF still requires verification: the brochure URL returned 404, while
the full report exceeded the browser tool's size limit.

## 7. Verification results

| Check | Result |
|---|---|
| Five KPI calculator tests | Passed with local Python 3.15; not yet verified with the project's Python 3.11 |
| 106 local Markdown link targets across eight related submission documents | All found |
| MyCOL JSON structure, edition, date and nine unique labels | Passed; not a verification of the complete source |
| `git diff --check` | Passed in the previous check |
| i18n key parity | Passed |
| Lint, application pytest and contracts | Could not run because `.venv` was not available |
| TypeScript | Could not run because web dependencies / `tsc` were not available |

The complete quality gate **has not passed**. No dependency installation, migration,
seeding, human measurement or paid inference was performed.

## 8. Scope limits

- Forbidden Phase 1–3 files, all B items and `docs/decisions.md` were not edited.
- Application runtime, database, CI configuration and scoring were not changed.
- A6–A13 and A15 have not been implemented; A5 configuration work has not been done either.
- A1, A3 and A14 still have the completion limits described above.
- No commit, push, PR, merge or deployment was performed.

Reasons for deferring each item, branch locations and suggested commits are available in
the [work handoff](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/a-safe-work-status.md).


Suggested commit for adding this log:
`docs(submission): list completed isolated fixes and remaining limits`.

## 9. Continued work — update after T1–T10

Sections 1–8 above record the initial stage. The updated status in sections 9–20
supersedes the earlier statements that A6–A13 were not implemented and application checks
were blocked by dependencies. The initial notes remain to preserve the sequence of work.

Follow-up work used the same working tree without creating a new branch, commit or PR.
The other engineer's forbidden files and pre-existing changes were preserved.
Per-task file details and evidence from tests before and after each fix are available in
the [implementation manifest](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/isolated-fixes-manifest.md).

## 10. A6 / T1 — Public PDF parsing limits

**Implementation complete and local tests passed.**

- PDFs exceeding the 30-page limit are rejected with the code `pdf_too_many_pages`.
- Public PDF previews are processed in a subprocess with a five-second timeout, two
  concurrent slots, a 384 MiB memory limit and a CPU limit.
- Timed-out processes are terminated and joined; requests made when all slots are occupied
  receive `pdf_busy` without queuing new parsing work.
- Extracted text is capped while preserving the truncation indicator.
- Errors use the existing `AppError` format; no English messages were added to the router.

Files: `src/api/app/features/profile/cv_parser.py`,
`src/api/app/features/preview/router.py` and
`tests/api/profile/test_pdf_public_limits.py`.

Tests cover a synthetic 500-page PDF, a normal PDF, the public endpoint, timeout cleanup
and exhausted slots. All 221 profile/preview tests passed during implementation verification.
Linux resource limits still require CI/staging verification; local tests used Windows.

## 11. A7 / T2 — Job posting location filter

**Implementation complete and fixture tests passed; live data has not been refreshed.**

- The posting's primary location is evaluated first; another office in Malaysia cannot
  qualify a posting whose primary location is outside Malaysia.
- The Lever connector no longer merges all alternative locations into the primary location.
- Matching uses word boundaries and recognises the country codes `MY`/`MYS`.
- UAE, Singapore, Hong Kong and US fixtures are excluded; Malaysia and remote-Malaysia are retained.

Files: `src/pipelines/jobs/sources.py` and `tests/pipelines/jobs/test_primary_location.py`.

All 15 new cases passed; the jobs pipeline suite recorded 73 passes and one skipped database
test during implementation verification. The live pipeline was not run and seed rows were
not changed. Workflow dependency installation changes were handled separately under T4.

## 12. A9 / T3 — RunPod encoder job cancellation

**Implementation complete and mock tests passed; actual billing has not been verified.**

- A single deadline applies to the entire encode call, including all batches.
- Unfinished jobs with a known ID are cancelled through `finally` on timeout/error.
- Completed jobs are not cancelled.
- Cancellation failures preserve the primary error and add a note about the cleanup failure.
- Requests include provider execution/TTL limits to bound jobs if the ID response is lost.

Files: `src/pipelines/trends/encoder.py` and
`tests/pipelines/trends/test_encoder_cancellation.py`.

Five new cases passed using a mock HTTP transport. RunPod endpoints, credentials and
configuration were not changed; no paid inference ran and no live billing verification is claimed.

## 13. A8 / T4 — Refresh workflows and locked installation

**Configuration changes complete; GitHub behaviour cannot yet be verified locally.**

- Manual `workflow_dispatch` runs fail when required configuration is empty, without printing values.
- Scheduled runs retain an explicit skip notice when configuration is incomplete.
- Dependency installation uses `uv sync --frozen --python 3.11` with the existing `uv.lock`.
- Workflows use the interpreter from the resulting virtual environment.
- The snapshot date in the job summary comes from the publisher's confirmation; pipeline
  failures are still propagated through `pipefail`.

Files: `.github/workflows/trends-refresh.yml`, `.github/workflows/data-sources.yml`
and `tests/test_isolated_workflow_yaml.py`.

Both YAML syntax tests passed. No workflow dispatch or GitHub settings/secrets changes occurred.
A human still needs to test empty configuration, frozen installation, publisher failures
and the summary date through an authorised dispatch in a staging/disposable environment.

## 14. A12 / T6 — Removal of unused legacy assets

**Complete; Node tests, TypeScript and the build passed.**

- Searches found no imports of `SkillBankPanel.tsx`; the component was deleted.
- The global `insight.css` import was removed from the root layout, then the unreferenced
  stylesheet was deleted.
- `adept.css`, `adi.css` and other forbidden files were not changed.

Deleted files: `src/web/src/features/core/components/SkillBankPanel.tsx` and
`src/web/src/app/insight.css`.
Changed file: `src/web/src/app/layout.tsx`.
New tests: `tests/dead-assets.test.mjs`.

Both Node tests passed. Visual layout checks are still required; successful compilation
does not prove that every screen is free of regressions.

## 15. A11 / T7 — EN/MS/ZH privacy page

**Route and translations complete; the team still needs to fill in operational details.**

- Added `/privacy` with a new `privacy.json` namespace for en, ms and zh.
- Content covers the controller, processing purposes, service providers, cross-border
  transfers, retention, and requests for access, correction and withdrawal of consent.
- Data flows were traced to upload/embeddings, Adi/provider and account export/deletion code.
- The controller and contact use clear placeholders; provider/backup regions and retention
  are not claimed to have been verified.
- Added one footer link without changing footer styling or signup/join forms.
- CSS uses a new module; existing locale files and forbidden CSS remain untouched.

New files: `src/web/messages/{en,ms,zh}/privacy.json`,
`src/web/src/app/privacy/page.tsx` and `src/web/src/features/privacy/`.
Minimal registration: `src/web/src/lib/i18n/config.ts` and
`src/web/src/lib/i18n/global.d.ts`.
Footer link: `src/web/src/components/shell/Site.tsx`.
Tests: `tests/privacy-page.test.mjs` and `tests/privacy-http.test.mjs`.

Static tests, i18n parity, TypeScript and the build passed. The page was tested over HTTP:
**EN, MS and ZH each returned 200** with the translated title and footer link.
The loopback test server has been stopped. Successful HTTP responses do not certify legal
compliance; the team still needs to complete placeholders and confirm deployment/provider facts.

## 16. A13 / T8 — Matching counterfactual harness

**Script and unit tests complete; production evaluation was deliberately not run.**

- Prepared five synthetic profile variants: a baseline, separate age/gender/background
  changes and a combined change; all other inputs remain identical.
- The default path calls the existing matching service API at a fixed snapshot, temporarily
  substituting profile reads in the offline harness.
- Compares ranked output, scores and match data; empty output or a different snapshot is
  rejected to prevent a vacuous conclusion.
- Does not persist profiles, copy scoring formulas or write fairness result logs.

New files: `src/pipelines/guardrails/matching_counterfactual.py` and
`tests/pipelines/guardrails/test_matching_counterfactual.py`.

Four unit tests with dummy queries passed. These results are **not evidence of production
matching fairness**. Evaluation against actual scoring still waits for the other engineer's work.

## 17. A5 partial / T9 — Dependabot configuration

**Configuration file complete and local tests passed; GitHub operation has not been verified.**

- Added weekly schedules for root uv, the MiniLM worker's pip requirements, the pnpm
  workspace through the npm ecosystem, and GitHub Actions.
- Did not add a root pip job competing with uv for the same Python project.
- Did not change existing workflows under T9 or any GitHub settings.

New files: `.github/dependabot.yml` and `tests/test_dependabot_config.py`.

YAML parsing and ecosystem coverage tests passed. Update discovery, automatic PR creation
and alerts/security update settings still need human verification after merge.
`.env.example` and README test counts remain unchanged.

## 18. A10 / T10 — Docker investigation without changes

**Investigation complete; Docker has not been fixed.**

- The web Dockerfile references `src/web/pnpm-lock.yaml`, which does not exist;
  the actual lockfile is at the repository root.
- Workspace inputs and the legacy standalone layout need review if the image is rebuilt.
- API boot automatically runs migrations and seeding against the configured database.
- No image was built, container started or Docker file changed.

The options of deletion versus rebuilding an offline-backup profile, with their risks,
are recorded in the [Docker investigation in the manifest](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/isolated-fixes-manifest.md#t10--docker-investigation-read-only).
This item must not be counted as a completed Docker fix.

## 19. A15 jobs side / T5 — Still deferred

**Not fixed, following the user's decision to wait for the contract.**

A separate diagnostic confirmed that `_meta([], "moderate")` still produces today's date
rather than a no-data indicator. The `RecommendationMeta.snapshot_date` contract currently
requires a date and is in the forbidden area. The user chose **“Defer T5 until the contract is ready”**.

`jobs/service.py`, `pathway/service.py` freshness, `trends/repository.py` and the metadata
contract were not changed. This diagnostic failure is recorded separately from the passing
regression suite.

## 20. Latest verification results and remaining limits

The following results come from the latest rerun at this stage and supersede the environment
limitations in section 7. Adding this note itself changed only this document.

| Check | Latest result |
|---|---|
| Full Python suite | **1,013 passed, 32 skipped, 48 subtests passed** |
| Baseline comparison | Baseline: 980 passed and 32 skipped; 33 additional passing cases with no reduction in tests |
| All local Node tests except HTTP tests | **32 passed** |
| HTTP `/privacy` EN/MS/ZH | **3 passed** |
| Ruff lint/format, ESLint, TypeScript | Passed |
| i18n key parity | Passed |
| Frontend build | Passed |
| Comparison of generated OpenAPI and TypeScript types | Identical to tracked files; tracked files were not overwritten |
| `git diff --check` | Passed |
| T5 empty-jobs diagnostic | **Failed because the bug remains deferred** |
| Legacy Docker | Static problems confirmed; not built/run |

Thirty Python cases were skipped because no PostgreSQL test database was opted into;
two others require PostgreSQL for comparison with the trend fixture export.
These skips are not passes. No test was weakened or given a skip to make the suite green.

Human verification is still needed for PDF resource limits on Linux, layout after CSS
removal, actual RunPod cancellation/billing, workflow dispatch, Dependabot operation and
controller/contact/region/retention details. Matching evaluation as evidence remains deferred.

Forbidden files, shared i18n wording, `.env.example`, README/test counts and
`docs/decisions.md` remained untouched during T1–T10. No commit, push, PR, deployment,
live feed refresh, migration/seeding or paid inference was performed.

See [test results and failure reasons](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/isolated-test-results-2026-10-30-rerun.md) for
rerun details, and the [implementation manifest](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/isolated-fixes-manifest.md) for
per-task file lists that a human can stage.

## 21. A1 follow-up — KPI tools available in the main working tree

**The file delivery gap is resolved; human measurements still have not been collected.**

The tools previously available only in the `tmp/a1-offline-planning-kpi/` checkout are now
present as new files in the main working tree. Formulas, inputs and outputs were unchanged;
only Python formatting was adjusted with Ruff. The old checkout remains untouched.

New files:

- [KPI calculator](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/src/scripts/kpi_time_to_plan.py)
- [Calculator tests](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/tests/scripts/test_kpi_time_to_plan.py)
- [Stopwatch protocol](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/kpi-time-to-plan.md)
- [Empty template for 30 trials](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/kpi-trials-template.json)

The tests first failed because the module was unavailable in the main working tree, then
all five passed after the files were delivered. The CLI with the empty template returns
zero valid pairs and null baselines/reduction; no achievement of the 20% target is claimed.

No SQL queries, database changes, telemetry, application imports, model calls or scoring
changes were introduced. The tool is explicitly run as an offline program.

## 22. A14 follow-up — Complete MyCOL CSV with verified sources

**Reference data complete; not connected to the application, badges, seeds or scoring.**

- The complete official TalentCorp PDF was downloaded and Table 7 was visually inspected.
- The CSV contains all **66 occupation groups** in Table 7 of the **2024/2025** edition,
  including MASCO 4D codes, source labels and page locators.
- The table is on printed pages 85–87, corresponding to PDF pages 44–45 in spread format.
- Provenance records official URLs, PDF/CSV checksums and the actual retrieval time.
- The download occurred on 29 October 2026 at 17:49:55 UTC, which is 30 October 2026 MYT.
  CSV dates use UTC; the unverified publication date remains null.
- The two schema/provenance tests first failed when the files were absent, then passed.
- The nine-label reference in the old checkout was left intact as an initial-stage record.

New files:

- [Occupation group CSV](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/reference/critical-occupations.csv)
- [Source provenance and checksums](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/reference/critical-occupations.provenance.json)
- [Curation method, schema and usage limits](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/reference/critical-occupations.md)
- [Reference tests](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/tests/reference/test_critical_occupations.py)

The data is stored in `docs/reference/`, outside runtime seed directories. It is a list
of source occupation groups, not a mapping to Adept roles or evidence of current vacancies,
salaries or growth. Using it for badges or scoring inputs is outside this work's scope.

## 23. Scope limits of this follow-up

Only new offline A1/A14 files and the continuation of this log were written. Files and
changes present at the start were preserved; completed work was not repeated.
No Git mutation, commit, push, PR or change to `.github/`, databases or application runtime occurred.

Other items remain unexecuted: scheduled/live jobs refresh, workflow dispatch,
inference/billing tests, Docker deletion/rebuild, README/`.env.example` updates,
freshness metadata changes and matching evaluation as evidence. These items have
operational consequences, authorisation limits or dependencies on the other engineer's work.

Final asset credits, the participant handbook, controller contact details and retention/region
facts still require actual information from the team; values were not invented to close a checklist.

## 24. A1/A14 follow-up verification

- Seven new-file tests passed: five KPI tests and two MyCOL reference tests.
- Full suite: **1,020 passed, 32 skipped, 54 subtests passed**; previously 1,013 passed
  and 32 skipped. No reduction in passing tests or additional skips.
- Ruff lint/format, ESLint, TypeScript and i18n parity passed.
- OpenAPI and TypeScript types generated in a temporary directory remained identical
  to tracked files; shared contracts were not overwritten.
- The KPI CLI with the empty template succeeded without generating a false baseline or reduction.
- `git diff --check` passed. No new frontend build/HTTP checks were run because no
  frontend files changed in this follow-up.

File details and result limitations are available in the [offline follow-up manifest](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/isolated-reference-follow-up.md).

## 25. Continued testing — HTTP flows with five synthetic CVs

**Integration tests and a report added; no application implementation changes.**

Sections 25–28 continue from section 24. The latest suite results in section 28 supersede
earlier verification results when assessing current status; historical records remain intact.
Testing found a guest preview failure, so the latest quality gate **has not passed**.
Adding these tests does not mean that all A1–A15 issues have been fixed.

New files from the preceding testing work:

- [CV flow tests over HTTP](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/tests/integration/test_synthetic_cv_http_flow.py)
- [Results, diagnosis and reproduction commands](https://github.com/pecel-lelele/adept/blob/ff04b64b9b1b330922f797f0a3498f06c2e20990/docs/synthetic-cv-real-flow-test.md)

Test details:

- Used five labelled synthetic PDFs and intake settings from `docs/demo-cvs/`;
  existing CV documents and demo settings were not changed.
- Ran the actual FastAPI application through Uvicorn on a temporary loopback port.
- Requests used HTTP multipart, signup, password hashing, login and signed tokens;
  the parser, matcher, planner and authentication service were not replaced with mocks.
- Accounts/profiles/plans used temporary `M3_BACKEND=csv` storage in the test process;
  `AUTH_RAW_USER_IDS=false` and an empty default user disabled identity shortcuts.
- The database was explicitly directed to unavailable loopback port 1. Developer/production
  databases were not used; model providers, embeddings and sync credentials were disabled.
- The snapshot actually returned was dated **2026-10-20**, not the request date.
- The test server was stopped after completion; the final port check confirmed connections were refused.

Each signed-in flow tested signup, questionnaire, PDF upload, skill confirmation,
moderate/fast match requests, the synthetic user's choice of target role, plan generation,
save, login again and reloading the same plan. Uploaded skills were not saved before
confirmation. Confirmation used documented synthetic selections, including excluding
reconciliation aliases that were too broad; it was not a human competence assessment.
Course IDs in the plan were checked against the catalogue response, along with study hours
and budget status.

## 26. Per-CV results and PDF limit testing over HTTP

**All five signed-in save/reload flows passed; guest preview did not pass in every case.**

This table refers to the final full run executed through the approval mechanism,
not a combination of the best results from several runs.

| Synthetic CV | Skills extracted / confirmed | Chosen target role | Plan steps | Estimated weeks | Unmet gaps | Signed-in save/reload flow | Guest preview |
|---|---:|---|---:|---:|---:|---|---|
| Imran Hakim | 6 / 6 | compliance-analytics-officer | 1 | 1 | 1 | Passed | Passed |
| Sofia Tan | 7 / 6 | process-automation-analyst | 4 | 1 | 2 | Passed | Passed |
| Meera Anand | 5 / 4 | logistics-supervisor | 2 | 1 | 3 | Passed | Passed |
| Adrian Lim | 4 / 4 | data-analyst | 3 | 2 | 1 | Passed | Passed |
| Nur Hana | 6 / 4 | bank-operations-executive | 1 | 1 | 3 | Passed | **Failed: HTTP 503** |

- A synthetic **500-page** PDF was also sent to the actual public endpoint and rejected
  with **HTTP 422**, code **`pdf_too_many_pages`**. The PDF limit was not the source
  of the HTTP 503 failure discussed in section 27.
- All five plans reported MYR 0 out-of-pocket cost in the frozen catalogue used.
  Unmet gaps remain; a successful save does not prove that all gaps can be closed.
- Both scenario requests succeeded in the signed-in flows. The top role for these inputs
  happened to be the same under moderate and fast; no scenario-ranking fix is claimed.
- Save/reload results verify state within one test process, not PostgreSQL persistence
  after a server restart.

## 27. HTTP 503 finding — diagnosis only, not fixed

**The regression remains open; the other engineer's fallback/trend files were not changed.**

Failing case in the final full run:

```text
tests/integration/test_synthetic_cv_http_flow.py::test_synthetic_guest_pdf_preview[demo-nur-hana]
POST /api/v1/preview/cv?include_suggestions=false -> HTTP 503
error.code: trend_unavailable
error.message: Trend snapshot for scenario 'moderate' timed out after 2s
```

The message summary above is shortened; the complete response is stored as a JUnit property
in `tmp/synthetic-cv-full-suite-approved-results.xml`. The `tmp/` artifact is only available
locally; the new Markdown report contains evidence and reproduction steps that can be read
without that artifact.

- **Observed:** the response reports a two-second trend lookup timeout. Earlier targeted
  runs failed on different CVs while other cases succeeded; the failure is intermittent
  and does not indicate a problem specific to the contents of Nur Hana's PDF.
- **Code-based explanation:** guest preview calls `matching.trend_port.fetch_snapshot`,
  which waits at most two seconds. Trend resolution tries the database before using
  fixtures, with five-second fallback/negative caches. With the test database deliberately
  unavailable, resolution can consume the adapter's deadline, including after cache expiry.
  This is consistent with the recorded error.
- **Conclusion limits:** this result does not prove that a deployment with a healthy
  database has the same failure. No production verification or database changes occurred.
- **Conflict-avoidance boundary:** `matching/trend_port.py`, `trends/repository.py`,
  `trends/service.py`, freshness contracts and the other engineer's UI were not edited.
  A repair must be coordinated with the fallback/trend work already owned by that engineer.
- No retries/warm-up, increased timeout, changed expected status, removed assertions or
  added skips were used to make the test pass. The failing regression is retained.

## 28. Latest verification, scope limits and this log update

**The latest quality gate has not passed because of one guest preview regression.**

| Check | Result from the latest CV test run |
|---|---|
| New HTTP CV group, 11 cases | **10 passed, 1 failed** |
| Full Python suite through approval | **1,030 passed, 32 skipped, 1 failed, 54 subtests passed**, 85.87 seconds |
| Comparison with section 24 | Previously 1,020 passed and 32 skipped; the 11 new cases added 10 passes and 1 failure; no additional skips or reduction in existing tests |
| Remaining failure | Nur Hana guest preview: HTTP 503 `trend_unavailable`, two-second timeout |
| Python warning | One existing FastAPI/Starlette TestClient deprecation |
| Ruff lint/format and ESLint | Passed |
| TypeScript (`tsc --noEmit`) | Passed |
| EN/MS/ZH i18n key parity | Passed |
| Comparison of temporarily generated OpenAPI and TypeScript types | Identical to tracked files; tracked contracts were not overwritten |
| Web Node regression group | **32 passed, 0 failed** |
| `git diff --check` | Passed; the CRLF normalisation warning in an older document remains separate |
| Frontend build, privacy HTTP and browser interaction | Not rerun during this CV testing work |

The initial full sandbox run recorded 1,008 passes, 32 skips, 11 failures and 12 setup errors
because Windows restricted temporary directories and PDF worker pipes. The approved rerun
removed those permission errors and left the single trend timeout above. Sandbox errors
are not treated as source regressions or a passing quality gate.

Thirty cases remain skipped because no PostgreSQL test database was opted into; two other
cases require a PostgreSQL export to compare trend fixtures. Skips are still not passes.

Limits that still apply:

- This testing uses backend HTTP with temporary memory storage. File-picker interaction,
  Next.js cookies/proxy/server actions, visual UI and database persistence remain unverified.
- Automated request durations do not replace tester stopwatch trials. A1 still has no manual
  baseline or evidence of the 20% target; no human results were fabricated.
- A14 remains an offline reference, without badges, runtime seeds or scoring integration.
- A15/T5 remains deferred until the contract is ready. No shared i18n wording,
  README/test counts, `.env.example`, `docs/decisions.md` or forbidden Phase 1–3 areas changed.
- No live pipeline, workflow dispatch, inference/billing, migration/seeding, deployment,
  Git mutation, commit, push or PR occurred during the testing and this log update.

The preceding testing work added only the test file and report listed in section 25.
This log update **changes only `docs/daftar-perbaikan-aman.md`**, continuing section numbering
and preserving all previous records. The test figures above come from the completed CV
run; the suite was not rerun solely to add these notes. Document checks cover preservation
of the previous text, section order, new Markdown link targets and whitespace diffs.

Suggested documentation commit for a human after review:
`docs(qa): update safe-fix tracker with synthetic CV flow results`.
