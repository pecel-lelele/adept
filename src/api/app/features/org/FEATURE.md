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
required level), `GET /org/plan` (default role = strongest existing team skill fit). No built-in
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

## Learning packages and employer funding

HR chooses a target role and a cohort of 1–50 completed profiles at `/org/plan`.
`GET /org/packages` returns free-first, member-budget-capped and broader-catalogue proposals
using F5 for every member. Each proposal includes dated course prices, each member's study
time, remaining gaps and source metadata. Options can coincide when free courses provide
the same coverage. HR sends one via `POST /org/packages/select`; a hash refuses stale quotes.
Members see only their own assignment and explicitly adopt it at `/app/pathway` or
`/app/funding`. Selection is not enrolment, funding approval or a hiring decision.

`/org/funding` sets annual MYR budgets per member; `/app/funding` requests a specific course
purchase against a provider quote. Purchase approval reserves the full cap atomically.
Members submit completion certificates (including approved courses outside the generated
plan) to the existing F5 HR verification queue. Receipt claims require current-manager
confirmed completion, a purchase after approval and an amount within the cap. HR reviews
receipts before marking payable, then separately records an external finance payment
reference. Revoked/replaced evidence blocks payment. Rejection/cancellation releases the
reservation, actual payment releases any unused cap. Subscriptions and group purchases
require employer procurement. Members unable to pay upfront can ask HR to purchase directly;
Adept does not process that purchase or transfer money.

`learning_funding` uses one locked PostgreSQL row per organisation across budget years,
private behind RLS with no public policy. A separate volatile backend is for synthetic tests
only. Writes fail closed, current membership is checked for money operations, and records
participate in account export and deletion. No receipts, certificate pages or real personal
records were ingested in development. Only synthetic test evidence is permitted by the
current repository policy.
