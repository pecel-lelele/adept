# F5 Reskilling pathway (M3)

- **Feature ID**: F5
- **Owner**: M3
- **API code**: `apps/api/app/features/pathway/` (router → service → repository → mocks)
- **Contracts**: `apps/api/app/contracts/pathway.py`
- **Web code**: `apps/web/src/features/pathway/`
- **Translations**: `apps/web/messages/{en,ms,zh}/pathway.json`
- **Seed data**: `data/seed/courses/`

## Status

Skeleton: endpoints return mock data from `mocks.py` with `meta.sources = MOCK DATA`.
Replace `repository.py` reads with real data, keep the contracts stable.

## Goal and tasks (from docs/TASKS.md)

**Goal:** ordered learning plan with estimated time, using free/low-cost and HRD Corp-claimable resources.

**Open choices:** course sources, prerequisite graph method, time-estimation approach.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Course catalogue: real URLs, hours, cost, HRD Corp-claimable flag (manually verified, with date) | |
| Preliminary | Pathway page (static preview for the demo persona) | Core |
| Final | Prerequisite graph and step ordering | F4 |
| Final | Time estimate: total weeks from course hours and the user's hours per week | F1 |
| Final | Progress tracking + skill badges; match score rises as steps complete | F4 |
| Final | Recompute pathway on new trend data | F2 |

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
