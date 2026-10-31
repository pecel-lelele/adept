# F3 Scenarios & uncertainty (M1)

- **Feature ID**: F3
- **Owner**: M1
- **API code**: `src/api/app/features/scenarios/` (router → service → repository → mocks)
- **Contracts**: `src/api/app/contracts/scenarios.py`
- **Web code**: `src/web/src/features/scenarios/`
- **Translations**: `src/web/messages/{en,ms,zh}/scenarios.json`

## Status

Implemented: moderate and fast scenarios and role outlooks derived from dated F2 snapshots.
Role requirements weight skill velocities; stored snapshot variation and missing coverage
widen the estimate range. These are heuristic assumptions, not calibrated employment
forecasts. See `service.py` and `tests/api/scenarios/`.

Each scenario reports its own importance-weighted skill signal, clipped to the demand
index band. Mixed positive/negative skill signals can cancel differently, so fast is
not forced to be more extreme than moderate (M1-016). Comparison responses use
`RecommendationMeta.scenario = "both"`; individual outlook rows retain `moderate` or
`fast`. Snapshot/source dates and fallback disclosures are preserved.

## Goal and tasks (from docs/tasks.md)

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
