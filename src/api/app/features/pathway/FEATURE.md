# F5 Reskilling pathway (M3)

- **Feature ID**: F5
- **Owner**: M3
- **API code**: `src/api/app/features/pathway/` (router → service → repository → mocks)
- **Contracts**: `src/api/app/contracts/pathway.py`
- **Web code**: `src/web/src/features/pathway/`
- **Translations**: `src/web/messages/{en,ms,zh}/pathway.json`
- **Seed data**: `src/data/seed/courses/`

## Status

Real data. `engine.py` (pure) builds plans; `service.py` wires profile (F1), taxonomy (F4),
trend snapshots (F2) and SDG links (F6) into it; `repository.py` stores saved plans, progress and
badges in memory (`M3_BACKEND=csv`) or PostgreSQL (`M3_BACKEND=postgres`: `pathway_plans`,
`course_progress`, `user_badges`). The catalogue is defined in `catalogue_sources.py` and
refreshed live by `sync.py` (`POST /pathway/catalogue/sync`, `python -m app.features.pathway.sync`).
Endpoints: `GET /pathway`, `GET /pathway/catalogue` (filters: skill, format, audience,
provider_type, hrd_claimable, max_cost_myr), `POST /pathway/plans`,
`GET /pathway/plans/me` (re-plan check), `POST /pathway/plans/me/accept-replan`,
`GET|POST /pathway/progress`, `POST /pathway/progress/evidence` (certificate link, checked by
`verification.py`), `GET|POST /pathway/verifications` (HR / advisor review of their own org's
members; evidence in `course_evidence`). F7 uses `group_pathway` and `team_gaps`.
Web: `/app/pathway`, `/app/progress`, `/app/courses`, `/org/plan`, `/org/courses`, `/org/verify`.
Flows per audience: `docs/UX_FLOWS.md`.

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

| Stage | Choice | Notes |
|---|---|---|
| Source | Microsoft Learn Catalog API (20 items), Coursera (5 free-to-enrol courses, checked live via its catalog API), 8 HRD Corp-claimable provider courses quoted from their pages (incl. UKM and FMM paid courses), 1 subscription bundle (Coursera Plus; USD converted at Bank Negara Malaysia's live rate) | `catalogue_sources.py`; seeds via `src/pipelines/pathway`, DB via live sync |
| Preprocessing / cleaning | strip tracking params, minutes → hours, validate skill IDs, https URLs, levels | pipeline fails if a curated UID is retired |
| Features | gap = required − current level; priority = importance × gap share × (1 + growth × w), w = 1 moderate / 2 fast | growth from the latest trend snapshot |
| Model / method | topological sort over `skill_prerequisites` (prerequisites inherit the urgency of what they unlock); ascending-level course selection, cheapest out-of-pocket (HRD Corp-claimable = RM 0 if eligible) then shortest, within budget; multi-skill course booked once; weeks = ⌈hours ÷ hours/week⌉ | never invents a course: uncovered skills are reported as unmet |
| Evaluation | 38 tests: catalogue-only, every match has a pathway, budget, HRD, prerequisites, re-plan diff, badges, counterfactual fairness | `tests/api/pathway` |
| Serving | endpoints above; web `/app/pathway`, `/app/progress`, `/org/plan` | |
