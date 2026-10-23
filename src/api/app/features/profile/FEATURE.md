# F1 Skills profile intake (M2)

- **Feature ID**: F1
- **Owner**: M2
- **API code**: `src/api/app/features/profile/` (router → service → repository → mocks)
- **Contracts**: `src/api/app/contracts/profile.py`
- **Web code**: `src/web/src/features/profile/`
- **Translations**: `src/web/messages/{en,ms,zh}/profile.json`
- **Seed data**: `src/data/seed/personas/`, `src/data/seed/taxonomy/`

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

## Catalogue omissions (2026-10-23 integration)

CV responses include `unmatched_terms`: up to 30 short entries from explicit
EN/MS/ZH skills lists which do not exactly match an approved label or alias.
These are unverified wording for transient review, not skill IDs. They are never
saved as profile skills, ranked, sent to an LLM or added to the taxonomy. Users
may search the existing catalogue and explicitly choose a valid equivalent.

This bounded rule cannot find every unfamiliar skill in prose or every CV layout.
Both guest preview and intake state that limitation, preserve truncation warnings,
and distinguish zero recognised catalogue skills from zero actual skills. Unknown
only previews produce no role or score. Existing exact aliases, level review,
file limits, scanned/encrypted PDF errors and ID validation remain in force.
