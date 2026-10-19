# F1 Skills profile intake (M2)

- **Feature ID**: F1
- **Owner**: M2
- **API code**: `apps/api/app/features/profile/` (router → service → repository → mocks)
- **Contracts**: `apps/api/app/contracts/profile.py`
- **Web code**: `apps/web/src/features/profile/`
- **Translations**: `apps/web/messages/{en,ms,zh}/profile.json`
- **Seed data**: `data/seed/personas/`, `data/seed/taxonomy/`

## Status

Skeleton: endpoints return mock data from `mocks.py` with `meta.sources = MOCK DATA`.
Replace `repository.py` reads with real data, keep the contracts stable.

## Goal and tasks (from docs/TASKS.md)

**Goal:** capture current skills **and potential** via CV upload, form or questionnaire.

**Open choices:** PDF parser, extraction method (LLM / NER / rules / hybrid), embedding or similarity method, form library.

| Phase | Task | Works with |
|---|---|---|
| Preliminary | Questionnaire: segment (working / graduate / switcher), interests, hours per week, learning style, budget, HRD Corp eligibility | Core (UI kit) |
| Preliminary | CV pipeline: parse → clean text → extract skills → normalise to taxonomy → confidence score | F4 (taxonomy) |
| Preliminary | Skill confirmation screen: user edits extracted skills and levels | |
| Preliminary | 3–5 synthetic personas and fake CVs (Aisyah, Wei Jie, Ravi) + a synthetic team for the HR demo | F7 |
| Final | Capture potential: interests, transferable skills for switchers, current-role risk for working adults | F2, F3 |

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
