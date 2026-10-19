# F3 Scenarios & uncertainty (M1)

- **Feature ID**: F3
- **Owner**: M1
- **API code**: `src/api/app/features/scenarios/` (router → service → repository → mocks)
- **Contracts**: `src/api/app/contracts/scenarios.py`
- **Web code**: `src/web/src/features/scenarios/`
- **Translations**: `src/web/messages/{en,ms,zh}/scenarios.json`

## Status

Skeleton: endpoints return mock data from `mocks.py` with `meta.sources = MOCK DATA`.
Replace `repository.py` reads with real data, keep the contracts stable.

## Goal and tasks (from docs/TASKS.md)

**Goal:** more than one future scenario; predictions clearly marked as estimates.

**Open choices:** scenario parameters and their sources, forecasting method, range method.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Define moderate vs fast AI disruption parameters | |
| Preliminary | Outlook per role per scenario with low/high ranges | F2 |
| Preliminary | Scenario/outlook endpoint used by matching | F4 |
| Preliminary | "Estimate" labelling on every prediction | Core (UI kit) |

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
