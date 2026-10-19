# F6 SDG mapping (M3)

- **Feature ID**: F6
- **Owner**: M3
- **API code**: `src/api/app/features/sdg/` (router → service → repository → mocks)
- **Contracts**: `src/api/app/contracts/sdg.py`
- **Web code**: `src/web/src/features/sdg/`
- **Translations**: `src/web/messages/{en,ms,zh}/sdg.json`
- **Pipeline**: `src/pipelines/sdg/`; seed data `src/data/seed/sdg/`

## Status

Real data. All 17 goals and 169 targets from the UN SDG API (`src/pipelines/sdg`). Every role
and skill in the taxonomy links to ≥1 target with a reason and a direct/enabling strength
(drafts, `reviewed_by` empty until a human signs off). Endpoints: `GET /sdg/goals`,
`/sdg/roles/{id}`, `/sdg/roles/{id}/alignment?goals=`, `/sdg/skills/{id}`,
`/sdg/contribution/me?role_id=`, `/sdg/contribution/org`, `/sdg/regions`,
`/sdg/contribution/region/{state}`.

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

| Stage | Choice | Notes |
|---|---|---|
| Source | UN Statistics Division SDG API `Goal/List?includechildren=true` | 17 goals, 169 targets, official wording |
| Preprocessing / cleaning | keep codes and titles; validate 1..17 and target prefixes | |
| Features | curated role/skill → target links with reason + strength; plan-level links from plan facts (skills built → 4.4; RM 0 out of pocket → 4.3) | focus goals 4, 5, 8, 9, 10; any of the 17 may be used |
| Model / method | manual mapping (M3 draft, pending review); contribution = union of links for a person / members of an org / orgs in a state; alignment = Σ(direct 1.0, enabling 0.5) ÷ 2, capped at 1 | alignment is for F4's SDG-weighted ranking |
| Evaluation | tests: every role and skill mapped, every target exists, reasons name their target, all 17 goals in every summary | `tests/api/sdg`, CI SQL check |
| Serving | endpoints above; web `/app/sdg`, `/org/sdg` (organisation and region tabs) | |
