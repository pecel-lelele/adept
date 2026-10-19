# F4 Future-role matching (M2)

- **Feature ID**: F4
- **Owner**: M2
- **API code**: `src/api/app/features/matching/` (router → service → repository → mocks)
- **Contracts**: `src/api/app/contracts/matching.py`
- **Web code**: `src/web/src/features/matching/`
- **Translations**: `src/web/messages/{en,ms,zh}/matching.json`
- **Pipeline**: `src/pipelines/matching/`; seed data `src/data/seed/taxonomy/`, `src/data/seed/personas/`

## Status

Skeleton: endpoints return mock data from `mocks.py` with `meta.sources = MOCK DATA`.
Replace `repository.py` reads with real data, keep the contracts stable.

## Goal and tasks (from docs/TASKS.md)

**Goal:** ranked future roles with an explainable score and a clear skills gap.

**Open choices:** taxonomy (ESCO / O*NET / hybrid), scoring formula and weights, retrieval method, evaluation metrics, fairness test design, chart library.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Load skill and role taxonomy as shared reference data | F1, F2, F6 |
| Preliminary | Explainable score: skill overlap + trend outlook (per scenario) + interest fit, shown as parts | F3 |
| Preliminary | Skills gap: have / partial / missing | |
| Preliminary | Matches page and role detail: score breakdown, gap, sources, SDG badges; re-rank on scenario toggle | F6, Core |
| Preliminary | Evaluation on labelled synthetic personas (e.g. precision@k, nDCG@k) | |
| Final | SDG-weighted ranking slider | F6 |
| Final | Fairness: age, gender, background excluded from matching | |
| Final | Counterfactual fairness tests (swapped personas → identical results) | |
| Final | Team-level aggregates for the HR heatmap | F7 |

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
