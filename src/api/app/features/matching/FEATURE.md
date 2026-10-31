# F4 Future-role matching (M2)

- **Feature ID**: F4
- **Owner**: M2
- **API code**: `src/api/app/features/matching/` (router → service → repository → mocks)
- **Contracts**: `src/api/app/contracts/matching.py`
- **Web code**: `src/web/src/features/matching/`
- **Translations**: `src/web/messages/{en,ms,zh}/matching.json`
- **Pipeline**: `src/pipelines/matching/`; seed data `src/data/seed/taxonomy/`, `src/data/seed/personas/`

## Status

Endpoints read saved profiles, the taxonomy catalogue and M1's in-process trend service.
Missing profiles return 400; unavailable trends return 503. Snapshot metadata comes from M1.
In development, matching uses M1's own documented fixture fallback and
shows its data provenance note. `APP_ENV=production` requires M1's strict database snapshot.
Gap responses and SDG badges use M3's service ports. Persona CSVs are harness-only.

## Goal and tasks (from docs/tasks.md)

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

| Stage | Choice | Notes |
|---|---|---|
| Source | Seed taxonomy (`roles.csv`, `role_skills.csv`), user profiles (`user_skills.csv`, `profiles.csv`), trend snapshots | Canonical skills (110) & roles (4 future target roles) |
| Preprocessing / cleaning | Preserve proficiency levels 1–5 in production and evaluation; parse interest tags | Absent skill = 0; credit = `min(user_level / required_level, 1)` |
| Features | Skill overlap (`w=0.45`), trend velocity normalized over the union of both scenarios (`w=0.25`), interest bonus (`w=0.3`) | Interest = `0.5 + 0.5 × matched declared interests / declared interests`, after case-folding and deduplication; missing tags or no overlap stays neutral, no declared interests stays not provided with neutral contribution (M2-030). Shared robust trend scale per dated snapshot: 0.5+0.5·tanh(2·asinh(c/s)/asinh(2/s)), c=clamp(v,±2), s=median\|v\| over both scenarios (M1-014); deterministic weights |
| Model / method | Linear composite scoring with tie-breaking on `(-score, role_id)`, gap bucketing | Pure scoring functions; `MatchProfile` fairness whitelist |
| Evaluation | Precision@k, Recall@k, MRR, nDCG@k on synthetic personas | Mean MRR=1.0, Mean P@3>=0.85, Mean nDCG@3>=0.90 |
| Serving | `/api/v1/matches` (`list_matches`, `get_match`) | Explainable `ScoreComponent` breakdown, missing/partial skills and trend coverage |


## Same-snapshot scenario and skill comparisons

List/detail responses include optional `rank`, `other_scenario`, `other_score` and
`other_rank`. The reference velocities already contain the other scenario from the same
snapshot, so one saved profile and one snapshot read determine both rankings. Missing
reference data leaves the comparison null. Both rankings include the requested SDG weight,
including its production component rounding and role-ID tie-break.

For each role's first three improvements, `new_rank` reruns the production ranker after
raising that skill to the role's required level. Other roles also receive that skill change;
shared skill/level counterfactuals are reused within the request. Labels say estimate, and
all attribution dates, fallback disclosures and catalogue resolution are preserved.

Detail requests still rank the full role catalogue, but build explanations, course options
and top-three improvement counterfactuals only for the requested role. This preserves the
same ranks as the list without discarding responses built for every unrelated role.

## Digital and green target scope (2026-10-31)

M3-042 removes the eight specified soft/clinical skill categories from target requirements
(16 edges), preserving the surviving relative importance weights and all intake/current-role
skill records. Matching continues to normalize over the surviving requirement weights;
no ranking formula or evaluation threshold changes. The digital-health nursing focus
requires healthcare informatics and AI literacy for qualified nurses, not clinical training.
See the [coverage report](../../../../../docs/evidence/skill-bank-coverage.md) and taxonomy provenance.
