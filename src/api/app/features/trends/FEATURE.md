# F2 AI-trend signal layer (M1)

- **Feature ID**: F2
- **Owner**: M1
- **API code**: `src/api/app/features/trends/` (router → service → repository → mocks)
- **Contracts**: `src/api/app/contracts/trends.py`
- **Web code**: `src/web/src/features/trends/`
- **Translations**: `src/web/messages/{en,ms,zh}/trends.json`
- **Pipeline**: `src/pipelines/trends/`; seed data `src/data/seed/trends/`

## Status

Implemented: dated snapshots from PostgreSQL or the explicitly selected fixture source,
with source and observation-window metadata. The offline pipeline ingests, scores, validates
and atomically publishes snapshots; scheduled refresh requires a configured database.
See `repository.py`, `src/pipelines/trends/` and the feature tests for current behaviour.

MiniLM is deployed on queue-based RunPod Serverless with a pinned revision and 384-dimensional
output. GitHub Actions runs batch ingestion and publication; page requests read saved
snapshots. The refresh needs a production database reachable from the runner, a dedicated
MiniLM API key and endpoint ID, and checks database access before inference. The live model
test passed on 24 October 2026; the first integrated refresh failed on Replit's private
development host `helium`. See the
[operations guide](../../../../pipelines/trends/runpod/DEPLOYMENT_HANDOFF.md).

Manual refresh from `/admin/snapshots` (`refresh.py`): **Refresh trend data now** dispatches
`trends-refresh.yml` through the GitHub REST API (`POST /trends/refresh`, server-side
`GITHUB_DISPATCH_TOKEN` + `GITHUB_REPOSITORY`; an already queued/running run is returned instead
of a second dispatch), and `GET /trends/refresh/status` polls the run and clears the trend caches
once it succeeds. **Re-score stored signals** (`POST /trends/refresh/rescore`) re-runs the
pipeline's scorer/validator/publisher on the stored weeks and publishes only a newer measured
window, else reports `no_new_data`. All three require a signed-in account listed in
`ADMIN_USER_IDS` (account IDs, set on both web and API; empty = nobody). The workflow's `TREND_DATABASE_URL` secret is the same database
the app reads as `DATABASE_URL`.

## Automatic app refresh (2026-10-30)

The dashboard, radar and admin page now use the shared background refresh job. GitHub's
`automatic-data-refresh.yml` calls the public app with `DATA_REFRESH_TOKEN`; the app writes
through its own database. Trends measure the last two complete real arXiv cs.AI submission
weeks (bounded samples), skip inference when already measured, and atomically publish the
measured Sunday as snapshot date. Static BLS retrieval dates remain unchanged. Historical
October 2024 replay observations stay labelled and the old backdating script is retired.
The legacy workflow/API above remain available until the replacement is proven in production.
See [operations and source assessment](../../../../../docs/data-refresh.md).

## Goal and tasks (from docs/tasks.md)

**Goal:** at least one updatable AI/job-market source; source and date visible; no hard-coded lists.

**Open choices:** data sources, HTTP/data libraries, scheduler, trend scoring formula, snapshot storage format.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Choose ≥1 updatable public source (2 if possible); check licence and stability | |
| Preliminary | Ingestion: fetch → clean → map to taxonomy IDs → store as dated, versioned snapshot | F4 (taxonomy) |
| Preliminary | Cached fallback snapshot for when the source is down | |
| Preliminary | Trend scores per role/skill: growth, AI exposure, automation vs augmentation | |
| Preliminary | Future Skills Radar page: rising / stable / declining with "data as of [date], source: [name]" | Core (UI kit) |
| Preliminary | Every trend response includes source, URL and date | |
| Final | Scheduled automatic refresh | |
| Final | Admin pages: sources, snapshot versions, manual refresh | |
| Final | Snapshot diff: what changed and why | |
| Final | Trend replay: switch snapshot date, rankings change | F4, Core |
| Final | Re-planning: new snapshot → recompute matches and pathways → notify users | F4, F5 |

## Pipeline

| Stage | Choice | Notes |
|---|---|---|
| Source | arXiv cs.AI RSS and BLS 2023-2033 baseline | Public research and cited labour data |
| Preprocessing / cleaning | Strip HTML and split abstracts into sentences | Cached raw ingestion |
| Features | Pinned MiniLM via RunPod; cosine threshold 0.55 | Per-skill mentions per observed ISO week |
| Model / method | Research log-ratio blended 0.6/0.4 with labour decay | Moderate and fast scenarios remain estimates |
| Evaluation | IDs, finite values, two periods and minimum evidence coverage | Failure prevents publication |
| Serving | Atomic PostgreSQL snapshot/provenance transaction | GET `/api/v1/trends/snapshot` |
