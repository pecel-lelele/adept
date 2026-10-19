# F2 AI-trend signal layer (M1)

- **Feature ID**: F2
- **Owner**: M1
- **API code**: `apps/api/app/features/trends/` (router → service → repository → mocks)
- **Contracts**: `apps/api/app/contracts/trends.py`
- **Web code**: `apps/web/src/features/trends/`
- **Translations**: `apps/web/messages/{en,ms,zh}/trends.json`
- **Pipeline**: `pipelines/trends/`; seed data `data/seed/trends/`

## Status

Skeleton: endpoints return mock data from `mocks.py` with `meta.sources = MOCK DATA`.
Replace `repository.py` reads with real data, keep the contracts stable.

## Goal and tasks (from docs/TASKS.md)

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

Fill this in as the feature takes shape (copy it into the `docs/decisions.md` entry).

| Stage | Choice | Notes |
|---|---|---|
| Source | | |
| Preprocessing / cleaning | | |
| Features | | |
| Model / method | | |
| Evaluation | | metric + result |
| Serving | | endpoint(s) |
