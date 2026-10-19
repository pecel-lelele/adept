# F7 Organisation mode (M4)

- **Feature ID**: F7
- **Owner**: M4
- **API code**: `apps/api/app/features/org/` (router → service → repository → mocks)
- **Contracts**: `apps/api/app/contracts/org.py`
- **Web code**: `apps/web/src/features/org/`
- **Translations**: `apps/web/messages/{en,ms,zh}/org.json`
- **Seed data**: `data/seed/org/`

## Status

Skeleton: endpoints return mock data from `mocks.py` with `meta.sources = MOCK DATA`.
Replace `repository.py` reads with real data, keep the contracts stable.

## Goal and tasks (from docs/TASKS.md)

**Goal:** serve HR/L&D managers and career centres with team-level views.

**Open choices:** chart library, invite mechanism, export format.

| Phase | Task | Works with |
|---|---|---|
| Final | Organisation setup (company / institution) and member invites | Core |
| Final | Team skills-gap heatmap | F4 |
| Final | Team reskilling plan: assign to members, members can adjust | F5 |
| Final | Aggregated SDG view for a company or cohort | F6 |
| Final | Institution extras: advisor notes, report export | |

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
