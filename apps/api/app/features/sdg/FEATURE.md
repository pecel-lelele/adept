# F6 SDG mapping (M3)

- **Feature ID**: F6
- **Owner**: M3
- **API code**: `apps/api/app/features/sdg/` (router → service → repository → mocks)
- **Contracts**: `apps/api/app/contracts/sdg.py`
- **Web code**: `apps/web/src/features/sdg/`
- **Translations**: `apps/web/messages/{en,ms,zh}/sdg.json`
- **Pipeline**: `pipelines/sdg/`; seed data `data/seed/sdg/`

## Status

Skeleton: endpoints return mock data from `mocks.py` with `meta.sources = MOCK DATA`.
Replace `repository.py` reads with real data, keep the contracts stable.

## Goal and tasks (from docs/TASKS.md)

**Goal:** every role and skill tagged to at least one SDG; show how the chosen path contributes. Meaningful, not decorative.

**Open choices:** SDG data source, mapping method (embedding, LLM-assisted, manual), review process.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Load official 17 SDGs and their targets | |
| Preliminary | Map roles and skills to target level (e.g. 7.2, 4.4) with a one-line reason; human review for demo roles | F4 |
| Preliminary | SDG badge data for roles and skills | F4 |
| Final | Personal SDG contribution panel | |

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
