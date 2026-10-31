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
trend snapshots (F2, through `trend_port.py`: M1's snapshot, seed fallback) and SDG links (F6) into it; `repository.py` stores saved plans, progress and
badges in memory (`M3_BACKEND=csv`) or PostgreSQL (`M3_BACKEND=postgres`: `pathway_plans`,
`course_progress`, `user_badges`). The catalogue is defined in `catalogue_sources.py` and
refreshed live by `sync.py` (`POST /pathway/catalogue/sync`, `python -m app.features.pathway.sync`).
Endpoints: `GET /pathway`, `GET /pathway/catalogue` (filters: skill, format, audience,
provider_type, hrd_claimable, max_cost_myr), `POST /pathway/plans`,
`GET /pathway/plans/me` (re-plan check), `POST /pathway/plans/me/accept-replan`,
`GET /pathway/compare` (compare target roles before choosing), `GET|POST /pathway/progress`, `POST /pathway/progress/evidence` (certificate link, checked by
`verification.py`), `GET|POST /pathway/verifications` (HR / advisor review of their own org's
members; evidence in `course_evidence`). F7 uses `group_pathway` and `team_gaps`.
Web: `/app/pathway`, `/app/progress`, `/app/courses`, `/org/plan`, `/org/courses`, `/org/verify`.
Current routes and flows: `docs/project-context.md` and `docs/solution-design.md`.

Progress stores immutable course facts in `course_progress.course_snapshot`. Accepted course
evidence across all target roles contributes to `service.evidenced_levels`; changing the saved
target or retiring a course does not erase earned credit. `service.combined_levels` merges it
with intake skills for matching, individual plans/comparisons/re-planning and team gaps/plans.
Undo and rejected evidence still revoke the corresponding credit. Migration `20261022220000`
backfills existing records from the surviving saved plan, or otherwise the current catalogue.

Only `org_confirmed` completions earn skill credit. A reachable certificate URL is `submitted`,
pending review of both learner and course; old `provider_verified` links also remain unearned.
Direct pathway previews require a saved profile, using the same `learner_for` gate as matching.

## Integration points (M1, M2, M4)

Completed course facts and evidence are read independently of the remaining plan.
`Progress.history` keeps completed courses visible with their original target and editable
evidence/undo actions after re-planning. Saved plan contexts are archived for badge
re-evaluation; rejection and undo revoke current eligibility. Team inputs use one joined
`learning_records(user_ids)` read across members and targets, and reuse loaded members when
choosing the default target.

| Port | Who calls it | What it gives |
|---|---|---|
| `trend_port.current(scenario, snapshot_date=None)` | F5, F6, F8 internally | M1's snapshot (in process, 3 s timeout, 60 s back-off) or the seed fallback; `growth`, sources, `available_dates`, `uncovered()` |
| `GET /pathway/compare?role_ids=&scenario=&snapshot_date=` | web `/app/pathway/compare`; M2 matches page should link here | weeks, cost, skills to close, trend outlook + coverage, F6 SDG targets per role; never ranks |
| `GET /pathway?snapshot_date=` | M1 trend replay | the plan on an older M1 snapshot |
| `service.skills_gap(levels, role_id)` | M2 matching, M4 heatmap | have / partial / missing by `required_level` (one gap rule for the app) |
| `service.role_trend(reqs, trend)` | M2 if it wants the same role outlook | importance-weighted velocity and coverage |

Still waiting on others: M1 `connect_timeout` in `trends/repository.resolve_context` (it can hang);
M1 skill IDs for `excel`, `rpa`, `sql` (shown as "no trend data"); M2 matching to use the saved
profile, `skills_gap` and `sdg.service.role_badges`.

## Goal and tasks (from docs/tasks.md)

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
| Source | 98 dated catalogue records from Microsoft Learn, Coursera and cited local providers, including a subscription bundle; foreign prices converted with BNM rates | `catalogue_sources.py`; seeds via `src/pipelines/pathway`, DB via live sync |
| Preprocessing / cleaning | strip tracking params, minutes → hours, validate skill IDs, https URLs, levels | pipeline fails if a curated UID is retired |
| Features | gap = required − current level; priority = importance × gap share × (1 + growth × w), w = 1 moderate / 2 fast | growth from the latest trend snapshot |
| Model / method | topological sort over `skill_prerequisites` (prerequisites inherit the urgency of what they unlock); ascending-level course selection, cheapest verified upfront price (HRD eligibility alone does not establish funding) then shortest, within budget; multi-skill course booked once; weeks = ⌈hours ÷ hours/week⌉ | never invents a course: uncovered skills are reported as unmet |
| Evaluation | Regression tests: catalogue-only, every match has a pathway, budget, HRD, prerequisites, re-plan diff, badges, counterfactual fairness | `tests/api/pathway` |
| Serving | endpoints above; web `/app/pathway`, `/app/progress`, `/org/plan` | |

## Catalogue enrichment (2026-10-23)

The catalogue has 98 courses as of 23 October 2026, retaining the original 34, adding
37 verified Microsoft Learn entries and 27 further cited provider courses. Coverage includes RAG, agents, evaluation, MLOps, security, digital twins,
emissions reporting and health-information systems. Learning achievements are not professional
certifications; exams can have separate fees. Free-to-enrol Coursera records remain browsable
with `certificate_price_unknown`. Their free learning can appear in plans at RM 0; a
certificate-required programme excludes them until the certificate price is known. Original list prices retain their verification dates;
confirm taxes, availability and the checkout price before buying.

Matching, profile/CV, role requirements and pathways share the DB-first reference reader.
Legacy `excel-basic`/`excel` and `robotic-process-automation`/`rpa` records remain, with effective
credit merged at the highest level per canonical skill. Prerequisites outside role requirements
are scheduled too; an unavailable foundation blocks dependent courses. Completing available
courses does not imply every role requirement is met. Uncovered levels remain explicit gaps,
including regulated clinical and engineering work.

The taxonomy has 140 skills, 31 roles and 160 role-skill links: 28 target roles plus 3 current
roles with baseline requirements excluded from future-role ranking. All have SDG links;
new role mappings are draft enabling hypotheses, not measured impact. Public occupation
crosswalks are in `taxonomy/provenance.json`; role labels and requirements are Adept curated
specialisations, not official O*NET titles or new job-growth forecasts. Missing trend coverage
remains visible rather than being invented for expanded roles.

Six stages: Microsoft Learn public API + O*NET 31.0 + official UN targets → validate IDs,
URLs, durations and crosswalks while preserving existing records → estimated role/skill edges
and prerequisites → F4 scoring and F5 budgeted topological plans → graph, coverage,
prerequisite and finance concurrency regressions → shared reference loader, append-only
role-scope migration, reference-only seed upserts and API/UI.

## Settings drive the plan (2026-10-31, M3-044)

Hours per week set the weeks; budget filters paid courses; learning style prefers delivery
formats within budget (classroom → taught formats, video/reading → self-paced). A saved plan
proposes `schedule_changed` / `cost_changed` re-plans when these settings change.
Measure with `.claude/toolbox/onboarding_effects.py` (production code, seed data).
