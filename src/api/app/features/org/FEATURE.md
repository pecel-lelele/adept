# F7 Organisation mode (M4)

- **Feature ID**: F7
- **Owner**: M4
- **API code**: `src/api/app/features/org/` (router → service → repository → mocks)
- **Contracts**: `src/api/app/contracts/org.py`
- **Web code**: `src/web/src/features/org/`
- **Translations**: `src/web/messages/{en,ms,zh}/org.json`
- **Seed data**: `src/data/seed/org/`

## Status

Real data in PostgreSQL (`organizations`, `memberships`, `users`, member `profiles`). A manager
creates the organisation at sign-up (`POST /auth/signup`, workspace `organisation`) and shares
its join code; learners join at sign-up or with `POST /org/join`. Endpoints: `GET|PUT /org/me`,
`POST /org/me/join-code`, `GET /org/members`, `DELETE /org/members/{id}`, `POST /org/join`,
`GET /org/gaps` (every taxonomy target role × skills, share of completed members below the
required level), `GET /org/plan` (default role = largest average team gap). No built-in
organisations; tests install fixtures from `tests/harness/fixtures.py`.

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
