# Automatic data refresh

GitHub is the clock; the deployed app fetches and publishes through its own reachable
database. `.github/workflows/automatic-data-refresh.yml` runs daily at 03:41 UTC and on
manual dispatch. GitHub needs only **secret `DATA_REFRESH_TOKEN`** and **repository variable
`DATA_REFRESH_APP_URL`** (the public HTTPS origin). It receives no database/model credential.
The stdlib caller retries cold starts with backoff, polls short requests, and fails visibly
on HTTP errors, failed sources, due-but-cooling-down work, or timeout. It never prints response bodies or credentials.

## Activation and verification

Manual refresh workflows and the automatic scheduler run only when the Actions ref is
`main` in the source repository. Do not dispatch from feature refs. The in-workflow guard
prevents accidental execution, but someone who can edit a workflow on a branch can remove
that guard: restrict who may dispatch, protect the main branch, and move deployment secrets
to a GitHub environment restricted to reviewed main before treating it as a security
boundary. Repository secrets without that restriction are not branch-isolated.

1. Review and apply **all pending append-only migrations** to the intended production
   database through the owner's procedure, including the dated provenance, paper-store
   (`20261031180000`) and matcher-series (`20261031220000`) migrations. Replit build/start
   never migrates or seeds; do not run these against an unconfirmed target.
2. Provision a new random `DATA_REFRESH_TOKEN` in Replit Secrets and GitHub Actions secrets.
   Configure GitHub repository variable `DATA_REFRESH_APP_URL` with the public HTTPS origin.
3. Keep Replit's existing `TRENDS_RUNPOD_API_KEY`, `TRENDS_RUNPOD_ENDPOINT_ID` and
   `TRENDS_EMBEDDING_BACKEND=runpod`. These are dedicated to MiniLM, separate from Adi's key.
4. Deploy the reviewed source. Run **Automatic app data refresh** once. Check its conclusion,
   `/api/v1/data/freshness`, and the admin snapshot page's per-source dates/recent runs.
   Verify a later scheduled run succeeds too; a green no-op alone does not prove publication.
   For the line chart, read `GET /api/v1/trends/compare?kind=skill&entities=skill:python&preset=3M`:
   a 404 means the chart API is not deployed; a 200 with no non-null observed points means
   the selected matcher has no complete stored seven-day windows. Record the returned
   `meta` source and observation dates, then run an authorized refresh/backfill to build
   actual paper history. Never add a synthetic line to represent missing observations.
5. Until that proof exists, retain the original `trends-refresh.yml` path and existing secrets.
   After the first successful automatic publication, record the run URL and list
   `TREND_DATABASE_URL` and `TRENDS_RUNPOD_API_KEY` as no longer needed **in GitHub** in the PR.
   Remove legacy scheduling/credentials only after owner review. Keep MiniLM credentials in Replit.

No production run or paid inference is claimed by local tests. Careerjet/Jooble keys are
optional and were not provisioned as part of this change.

## Request and persistence contract

- `POST /api/v1/data/refresh/run`: scheduler token (`X-Data-Refresh-Token`), constant-time
  comparison; rejects user-session headers; independently rate limited.
- `POST /api/v1/data/refresh/check`: administrators only since M1-026. Cheap stored-week/daily-cadence check
  precedes paid work and cooldown. A successful current-data check starts no worker/network
  request. The under-one-second target assumes a warm app/database; cold starts can exceed it.
- Both return 202 and a UUID for queued/running work, 200 for up-to-date/cooldown. An existing
  run is shared across users and app instances. Only `ADMIN_USER_IDS` may request a cooldown
  bypass. `TRENDS_REFRESH_COOLDOWN_MINUTES=10`; per-user check limit is 6/minute. After a failed
  trends step, signed-in non-admin checks skip the paid MiniLM step for
  `TRENDS_FAILURE_BACKOFF_MINUTES=60` (other due sources still run; admins and the scheduler are
  exempt). See TEAM-045.
- `GET /api/v1/data/refresh/status/{run_id}`: signed-in user or scheduler token, 120/minute.
  `GET /api/v1/data/refresh/recent`: admin only, last five parent runs plus next scheduled time.
- `GET /api/v1/data/freshness`: public, reads saved data only. Separates measured dates,
  retrieval/fact-verification dates, last successful refresh and last check; includes age,
  fallback, storage origin and historical replay flags. Course age uses the oldest active
  fact-verification date. A successful URL read alone cannot refresh a manual fee/hours date.
- Existing admin per-source and legacy trend endpoints remain available for compatibility.

One PostgreSQL session advisory lock is held throughout the shared worker. Parent UUIDs and
steps are durable; each source gets its own result/counts/times/error code. A lost worker is
marked failed on the next status check or start after the lock becomes available. Individual
source failures preserve that source's previous data while other steps can succeed. Network
operations have time/size limits; redirect forwarding is disabled; database deadline timers
actively cancel SQL and roll back; MiniLM deadline/shutdown cancellation cancels its RunPod job.
Total budget is 840 seconds, trends up to 600, other steps up to 90 each within that total.

Heartbeat checks are serialized with publication, so a handled transaction rollback does
not masquerade as loss of the session. The worker heartbeats its original lock-owning
database session and cancels model work if
that session fails. Every publication uses that same session; it cannot reconnect and publish
after losing ownership. A lost-session run is marked interrupted after a locked re-read, so
a concurrently completed successful run is never overwritten. Replacement paid work waits
until the old run's maximum lifetime plus 15 seconds has expired (up to 14 minutes 15 seconds
from its start), even for an administrator. This safety fence is distinct from normal cooldown.
The existing RunPod execution/TTL policy bounds orphan inference if cancellation loses its
acknowledgement. Each publishing transaction owns its pre-commit deadline check.

Measured inputs are saved atomically beside each snapshot: exact week ranges, mention counts,
paper denominators, skill IDs, BLS values/provenance, exposure values, model revision and the
sample's public paper identifiers/publication dates. Authors and abstract text are not stored.
Both automatic recovery and the stored-signal rescore can rebuild from these inputs without
arXiv or RunPod calls, preserving the original retrieval dates. Missing input schema prevents
new paid work. An exhausted catalogue-check budget fails without publishing or setting daily
success; retries rotate the course order. A successful zero-row database read stays labelled
as database data, rather than substituting nonzero seed counts. Partial-source failures still
refresh successful page regions while retaining the failed state.

## Datasets and method

| Stage | Implementation |
|---|---|
| Data source | arXiv public cs.AI submissions, versioned BLS baseline, documented employer APIs, provider course pages/API, DOSM LFS |
| Cleaning | Validate arXiv publication days against exact completed ISO weeks; cap 350 papers/week; HTTPS allowlist, size/time limits; posting's own Malaysian location; valid catalogue IDs |
| Features | Existing MiniLM sentence cosine mention counts; job title/skill rules; dated provider facts; official monthly survey rates |
| Model / method | Production trend scorer/validator, two prior complete weeks, moderate/fast estimates; existing job classifier/catalogue synchronizer |
| Evaluation | Mocked shared-lock/auth/cooldown/skip/failure/date/deadline regressions, production UI state rendering in all locales; full quality gate reported in PR |
| Serving | Atomic per-source transactions; last good data retained; saved provenance and public freshness; short polling and RSC data refresh |

Trend snapshot dates equal the measured week end; retrieval dates describe the actual fetch.
BLS remains the static 2023–2033 baseline acquired on 2026-10-20. The original October 2024
observations remain explicitly historical under their old demo labels. The old backdating
population script is retired and stored replay signals cannot be re-published as fresh.
Re-scoring stored signals does not call RunPod. Research attention is an estimate input,
not observed Malaysian vacancies. A bounded sample is disclosed rather than called a census.

The refresh UI immediately acknowledges a click, then shows source status/elapsed time after
one second and a warm-up explanation after fifteen seconds. Existing cards stay visible with
a refreshing tag. Polling backs off 1/2/5 seconds and stops when hidden/unmounted or terminal.
Completion uses `router.refresh()`; errors retain the last good snapshot. Status is polite
live text, words accompany colours, and reduced-motion users see no rotating spinner.

The daily job also refreshes job feeds. Ads older than `JOBS_STALE_DAYS` (default 14)
remain visible with their last observation date and a "may have closed" label, after fresh
ads; they do not inflate open counts or readiness totals. Jobs freshness separates the last
successful fetch from the actual posting `last_seen` (`data_as_of`), so a newer fetch log
cannot make retained old postings appear current. Runtime BLS evidence comes from its
committed, byte-bound provenance sidecar; missing evidence fails without invoking Git.

## Job-source assessment (opened 2026-10-30)

Public availability is not a blanket licence. Use only published board metadata/apply links,
respect robots/cadence, never collect applicant data, and stop on denied access. Existing
connectors are preserved; automatic refresh is restricted to the documented sources below.

| Candidate | Access / key | Malaysia coverage | Docs / terms evidence and decision |
|---|---|---|---|
| Greenhouse | Public Job Board API GET, no key | Employer-specific; posting must name Malaysia/local city | [Official docs](https://docs.greenhouse.io/job-board.html) explicitly document unauthenticated public GET. No universal redistribution licence verified; retain metadata/source links only. Enable configured boards, robots-aware. |
| Lever | Public postings API, no key | Employer-specific own-location filter | [Official API](https://github.com/lever/postings-api) documents building a public jobs site; [customer terms](https://www.lever.co/legal/terms-of-service) are not a blanket data licence. Enable published posting metadata and original apply links. |
| Ashby | Public job-posting endpoint, no key | Employer-specific own-location filter | [Official docs](https://developers.ashbyhq.com/docs/public-job-posting-api), [terms](https://www.ashbyhq.com/resources/terms). Published roles only; no interference/circumvention/non-public data. Enable. |
| SmartRecruiters | Public Posting API, no applicant credentials | Employer-specific | [Official docs](https://developers.smartrecruiters.com/docs/posting-api). API-host robots restrictions recorded in existing connector policy; separate terms permission not verified. Keep disabled. |
| Workable | Employer API token from Super Admin | Employer-specific | [Official guide](https://help.workable.com/hc/en-us/articles/115012771647-Using-the-Workable-API-to-create-a-careers-page). No universal keyless feed or redistribution permission verified. Defer. |
| OpenDOSM / data.gov.my | Public static CSV/API, no key | Official national monthly survey | [API](https://developer.data.gov.my/static-api/opendosm), [LFS catalogue and CC BY 4.0 licence](https://data.gov.my/data-catalogue/lfs_month). Enable existing DOSM labour context, cite it as national context, not individual openings or role-ranking vacancy evidence. No vacancy dataset asserted. |
| Adzuna | Registration/app ID and key | Malaysia API support not verified | [Overview](https://developer.adzuna.com/overview), [interactive docs](https://developer.adzuna.com/activedocs). Country support and applicable reuse terms remain unverified. Defer; do not invent Malaysian availability. |
| MyFutureJobs / PERKESO | No permitted documented public feed verified | Malaysian portal | [Official terms PDF](https://myfuturejobs.gov.my/wp-content/uploads/2024/03/TermsAndConditions.pdf), clauses 4.3–4.4 restrict reproduction/server storage without written permission. Do not scrape or add a connector. |
| Careerjet / Jooble | Optional keys; absent keys logged as skipped board names | Existing MY connectors | Preserve opt-in code; no keys required for automatic operation. No new keyed integration enabled. |
| Workday / Jibe | Historical connectors retained for CLI compatibility | Existing exports may contain credited rows | Undocumented career-site endpoints are not sufficient for this automatic path. Skip them automatically. |
| Himalayas / Jobicy / Remote OK / Remotive | Public remote-job APIs, no key | Remote ads; a stored "Worldwide" scope may mean the feed named no region, so it is not a claim about Malaysia | Read automatically (M4-095) so remote ads stay live for `/app/jobs` and `/app/matches/[roleId]`, labelled by Malaysia relevance. Terms were not re-verified for this path: only the existing credit and unchanged apply link are kept. All other surfaces still serve only a posting's own Malaysian location. |

Open pages do not establish permission for every future use. Unverified candidates stay
disabled; the assessment records those limits rather than claiming terms were approved.

## Gemini trend matcher rollout (M1-024, M1-027)

`TRENDS_MATCHER=auto` (the default) keeps the series on MiniLM until a passing
`src/data/seed/trends/paper_store/equivalence.json` is committed, then uses Gemini, which needs
`EMBEDDINGS_PROVIDER=gemini` and `GEMINI_API_KEY`. `TRENDS_EMBEDDING_BACKEND` still only configures
the MiniLM encoder. Apply `20261031220000_trend_matcher_series.sql` before deploying this code. To
move a database after the switch: run `make seed` against it (it loads the paper store, keeping
existing rows), set the two settings, then let the daily job continue. `TRENDS_MATCHER=minilm`
stays on MiniLM; its stored rows are never altered. See `src/pipelines/trends/README.md`.
