# Role choice, plans and learning progress

Review date: 2026-10-31. Branch: `feat/trends-radar-lists`.

The implementation uses Adept's existing catalogue and pathway engine. The supplied mockup's
invented roles, courses and prices were not added to production data. Existing uncommitted
work, including removal of the dedicated comparison feature, remains in place.

## Behaviour and implementation

| Requirement | Status | Result |
|---|---|---|
| Personal Plan/Progress locked before choice | PASS | Desktop, mobile tabs and More show a lock. Clicking goes to Roles with “Choose a target role first.” Direct URLs with an arbitrary role also require a saved choice. |
| Choose a role and open Plan | PASS | Every role card and detail page saves the existing `SavedPlan.role_id` and opens Plan. This record is the persistent target; a duplicate `target_role_id` column is unnecessary. Personal writes are explicitly pinned to the personal workspace. |
| Real steps, weeks, MYR cost and HRD flags | PASS | Individual and employer routes reuse catalogue-backed step cards, provider links, schedules, source dates and verified claimability flags. Totals come from the server, with each course booked once. Missing catalogue coverage stays explicit. Claimable does not mean a grant has been approved. |
| Complete/undo and update the bar | PASS | Existing workspace-bound completion actions update the hours-weighted progress bar and evidence badges. The bar exposes accessible progress values. |
| Update an estimated fit percentage | PASS | `estimated_skill_fit` reuses production importance-weighted skill overlap, the saved plan's baseline and non-rejected completion records. It is labelled as including self-reported study. Actual role ranking still requires the existing evidence gate. |
| Retain progress after switching roles | PASS | Progress remains keyed by member, workspace, role and course. Previous saved role/scenario plans can be retrieved from existing plan history. Switching roles does not delete completion or evidence records. |
| HR assigns a target to a member/cohort | PASS | Existing manager programme/package flows select catalogue roles and a cohort. Member rows link to a preselected member in the reviewed programme wizard. Proposed-role links preselect the requested role. Existing server membership, manager and stale-quote checks remain authoritative. A cohort is the programme's selected members; no new named-group entity is introduced. |
| Member accepts or proposes another role | PASS | Employer origin is visible. Full programmes and quick team plans accept a validated alternative-role request. A proposal retains the assigned target and requires HR review plus member acceptance of a replacement. Personal targets are separate. |
| Progress for an accepted employer role | PASS | The existing accepted-programme rule opens work Progress without choosing a personal target. Work estimates and progress remain in that employer's scope. |
| HR sees progress only with sharing | PASS | Dashboard and heatmap pages show course counts grouped by skill for consenting completed-profile members on accepted programmes. Only this organisation's records count. Each skill suppresses its totals below `ORG_MIN_COHORT`; withdrawal removes the member on the next read. Self-reported course totals are separate from evidenced skill gains in the gap heatmap. |
| EN/MS/ZH and catalogue attribution | PASS | New actions, lock messages, fit explanations, proposal choices and team-progress labels are translated. Existing sources, dates and estimate disclosures remain available. |

## Verification

- Full repository quality gate passed before browser follow-ups: 1,986 Python tests,
  50 skips, 54 subtests and 135 web tests; Ruff, ESLint, TypeScript, translations and generated
  contract synchronization passed. The final gate log is `tmp/role-journey-check-final.log`.
- Focused regressions cover target switching, undo, unchanged actual matching after
  self-reports, proposal ownership, invented-role rejection, quick-package decisions,
  organisation scope, rejected evidence and sharing withdrawal below the cohort threshold.
- Browser tests use signed synthetic accounts, isolated in-memory API state and an isolated
  web-source copy. Employer desktop/mobile flows and personal desktop passed; the final
  mobile verification is recorded in `tmp/role-journey-mobile-browser.log`.
- The production build compiled, passed TypeScript and generated pages. Standalone packaging
  failed on Windows with `EPERM` creating a Next.js dependency symlink. Browser checks use
  development mode; they do not establish production packaging or deployment.
- Tests did not opt into a real PostgreSQL database or live model provider. SQL persistence
  integration and deployment remain unverified. Proposal fields are additive defaults within
  the existing JSON ledger; no SQL schema migration is required.

## Review and handoff

Significant behaviour is recorded as `TEAM-052` in `docs/decisions.md`. Generated OpenAPI and
TypeScript files come from production contracts. There was no commit, push, merge or deploy.

Suggested commit: `feat(pathway): require role choice and add consent-aware team progress`.

## Follow-up corrections (TEAM-053)

A later review found these problems, and all of them are now fixed:

- The quality gate was failing at lint (`pathway/service.py`), although this review recorded a
  pass.
- A proposal after acceptance withdrew the acceptance and removed work Progress.
- The API accepted progress on a role the person never chose.
- A failed plan-status check appeared as a lock or a "choose a role" redirect.
- Roles did not mark the current target, and choosing it again skipped re-plan review.
- The programme wizard selected the whole team when a linked member was not eligible.

Still open: HR has no explicit "reject proposal" action, and a replacement programme does not
close the old proposal.
