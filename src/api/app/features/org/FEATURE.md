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

## Goal and tasks (from docs/tasks.md)

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

HR chooses a target role and up to 50 completed, consenting profiles at `/org/plan`.
Team plans, package previews/selections, programme options/generation and organisation SDG
contributions require `ORG_MIN_COHORT` sharing members with usable completed profiles. Selected
subsets must meet the same configured minimum. Below it, the API returns HTTP 409 with
`insufficient_cohort`; the web shows a translated "too few members" state without skill-derived
plans, readiness or assignments. Individual members can still see their own accepted programme.
`GET /org/packages` returns free-first, member-budget-capped and broader-catalogue proposals
using F5 for every member. Each proposal includes dated course prices, each member's study
time, remaining gaps and source metadata. Options can coincide when free courses provide
the same coverage. HR sends one via `POST /org/packages/select`; a hash refuses stale quotes.
Members see only their own assignment and explicitly adopt it at `/app/pathway` or
`/app/funding`. Selection is not enrolment, funding approval or a hiring decision.

`/org/funding` ("Training budgets") sets a yearly MYR budget per member. It is a planning
input only: `/org/packages` uses it for the budget-capped option. The organisation chooses and
pays for training directly (often under its HRD Corp levy). Members do not pay upfront, request
purchases, upload receipts or claim reimbursement (decision M4-062): those endpoints and the
member `/work/funding` page were removed, and old links go to `/work/plan`, where members review
the programme HR assigned. Claim records stored by the earlier flow remain in
`learning_funding.state` only for account export and deletion.

## Funding contention and year rollover (PR #10 review, historical)

Superseded in part by M4-062: the claim, receipt and payment flow described here no longer exists.


Read-only ledger and assignment requests use a snapshot without a write lock and release the
database connection before other repository work. Mutations bind their existing connection to
nested synchronous repository calls; nested borrowers cannot commit or return it to the pool.
The binding is reset on exit and cannot be reused by a different thread. Receipt approval and
payment checks hold shared locks on the completion/evidence rows until the ledger commits.
Certificate probing and pathway calculations run outside the funding transaction; a final
revision check prevents a concurrent cancellation being overwritten.

Budgets follow Malaysia's calendar (UTC+08). Both funding pages expose accessible prior budget
years, and action forms retain each claim's original year. A December approval can complete,
submit evidence and receipts, and record external payment in January against its original
budget; funds are not silently moved to the new year. Historical views do not depend on live
course/matching reads. Only current-year requests can be newly created.

Regression coverage includes slow certificate/cancellation races, year rollover and local
midnight, plus ten concurrent approvals and a full receipt/payment flow with a one-connection
PostgreSQL pool. Run the optional real-database check with `ADEPT_TEST_PG_ADMIN_URL` pointing
to a local PostgreSQL admin database, then `python -m pytest tests/integration/test_funding_postgres.py`.
It creates and removes a separate synthetic database; it never migrates the application DB.


## Personal and organisation workspaces

Every account has a personal workspace. `/org/workspaces` lists current memberships;
`X-Workspace` selects a membership-checked employer context. Employee `/work` views expose
agreements, sharing, progress and funding; manager `/org/programmes` supports the four-step
brief, deterministic proposal and explicit sending. A member reviews the agreement before
adoption. Progress and evidence are scoped to `personal` or `org:<id>` and personal
completions enter employer routes only through explicit sharing.

Programme schemas live in `contracts/programmes.py`; behaviour is covered by
`tests/api/org/test_programmes.py` and `test_workspaces.py`. Personal saved plans and Adi
conversations remain separate. Last-manager deletion is blocked when it would orphan a team.

## Small-cohort heatmap privacy

`ORG_MIN_COHORT=3` counts only consenting, completed-intake members whose profile is
available through `member_learners`. All roles currently use that same cohort. Below the
threshold, `cells[].gap` and `role_gaps[role]` are null, `suppressed` and
`role_suppressed[role]` are true, and `cohort_size` / `min_cohort` explain the boundary.
Never convert these nulls into zeroes, green cells, gap percentages or a ranked gap.
The manager's other authorised planning tools are unchanged.

The synthetic test/demo fixtures currently have 4 bank members (2 complete and consenting)
and 2 polytechnic members (1 complete and consenting), excluding managers/advisors. Both
heatmaps are therefore suppressed at the safe default. They are test fixtures, not automatic
production seed accounts. A meaningful demo of numeric heatmap data requires at least three
completed synthetic member profiles with explicit sharing consent; the above-threshold
regressions install a third synthetic bank learner without lowering the threshold.
