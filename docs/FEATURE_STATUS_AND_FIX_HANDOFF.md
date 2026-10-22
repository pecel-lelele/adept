# Feature status and fix handoff — 22 October 2026

Most requested features are implemented. The app is not fully ready: scheduled trend refresh, synthetic-only enforcement, review of SDG mappings, consistent ranking context, complete translations, and mobile development navigation need attention.

## Fix status — 22 October 2026 (after `46477ee`, branch `feat/core-insight-design`)

Fixes since the audited revision `968182b`. Each line says what changed and how it was checked. Findings below keep their original text; read this table first.

| ID | Status | What changed | Verified by |
|---|---|---|---|
| H01 | Fixed in code; deployment unverified | `pipelines/trends/run.py` chains ingest → score → validate → publish. Validation refuses one-week, short, unknown-id or non-finite snapshots; nothing is written on failure. Snapshot rows and provenance go in one transaction. `.github/workflows/trends-refresh.yml` runs weekly when `TREND_DATABASE_URL` is set. | `tests/pipelines/trends/test_run.py`. Controlled local run with synthetic signals published snapshot 2026-10-22; the API served it as latest with `observed_from/to` 2026-10-12..18; test rows were then removed. Not run against a deployed database or a fresh arXiv pull (needs `sentence-transformers` and network). |
| H02 | Closed by design (user decision, 22 Oct 2026) | The app behaves as a real product: sign-up and CV upload accept real input. The hackathon demo is run by the team with synthetic accounts and synthetic CVs only; no in-app restriction or warning is added. | — |
| H03 | Wording fixed; human review still open | The UN Goals score part no longer says "reviewed links"; it states how many of the role's links a person reviewed. No mapping was marked reviewed. | `test_ranking_explanation_says_how_many_links_are_drafts`. |
| H04 | Fixed | Weight (`sdg`) and snapshot carried from the matches list to role detail and replay (`/matches/replay?sdg_weight=`); outlook takes `snapshot_date`; replay reasons use the scorer's percentile positions. | `tests/api/matching/test_sdg_weight_and_replay.py` (detail score = list score; weighted replay order = weighted list order; percentile driver; outlook date). |
| H05 | Fixed | `/sdg/contribution/org` and `/region/{state}` take `role_id`; the Impact page passes the team plan's role. | `test_org_and_region_contribution_follow_the_selected_role`. |
| H06 | Fixed for interface strings | Every BM/Chinese string the app uses is translated; ~100 unused keys removed; badges named from their id. API-generated sentences (plan warnings, replan messages, SDG reasons) remain English. | `i18n-check`; TypeScript (removed keys are type-checked). |
| H07 | Fixed | Next.js dev indicator off. | Mobile "More" and the sidebar language switch receive clicks. Production build not separately rechecked. |
| H08 | Fixed (policy decided 22 Oct 2026) | Completed courses raise a skill's level for matching only with accepted evidence: confirmed by the organisation's reviewer, or a certificate link that opens on the provider's own verification page. Self-ticked, unreachable-link and rejected completions show progress but do not change matches. Matching uses the higher of the intake level and the evidenced level (`pathway.service.evidenced_levels`). | `tests/api/pathway/test_earned_levels.py` (policy and matching profile). |
| H09 | Fixed | `observed_from` / `observed_to` on snapshot and recommendation metadata; the sources line shows the measured period; the Radar warns when 2024 observations are replayed as a 2026 snapshot. | `tests/api/trends/test_provenance.py`; API returns 2024-10-13..19 for the 2026-10-20 demo snapshot. |
| H10 | Fixed | Evidence text says a certificate link only shows the page opens on the provider's site; a reviewer confirms it. Landing "Verified completions" → "Reviewed completions". | Existing `test_reviewers_only_see_their_own_members` / `test_learners_cannot_review` still pass. |

Also done in the same pass:

- **Data audit:** every number on Home, My skills, Radar, Roles, Plan, Progress, Courses, Impact and the team pages comes from the API. Checked in the browser with a synthetic account:
  - saving a plan updates Home;
  - marking a course done updates Progress (2%, 1/6 courses, first badge) and Home;
  - a member joining with a code updates the team dashboard (members, profiles complete, target gap, plan, goals).
- **Consistency fixes:**
  - the sidebar ticks the same steps as the Home and team journeys;
  - My skills follows the selected AI pace;
  - hand-typed "110+ skills" copy removed;
  - the replan banner shows skill names.
- **UI:**
  - team pages (dashboard, Team, Skill gaps, Team plan, Reviews, Settings) use the shared layout;
  - "Join a team" is in the sidebar, the mobile menu and on Home for learners without an organisation;
  - the sign-in and sign-up pages are one top-aligned panel showing the landing drawings, with no jump when switching;
  - every dropdown is styled.

## Start here: teammates and future Claude/Codex sessions

- **Audited revision:** `968182b` on `feat/core-insight-design`. This records observations at that revision; recheck the code before fixing an item.
- **Purpose:** a shared implementation-status report and repair backlog. A feature being present does not mean every integration or deployment condition has been verified.
- **Keep all six must-haves:** skills intake, updatable AI-trend signals, explainable future-role matching, personalised pathways, SDG mapping, and uncertainty/scenarios. Improvements below are additive or correct existing flows.
- **Scope of this handoff change:** documentation only. No issues below have been fixed merely by adding this report. Earlier UI work excluded backend and landing-page changes. This report does not grant permission to change those areas; follow the current user's scope and the repository ownership/shared-change rules.
- **Status language:** implemented = code exists with the evidence described; exercised = a synthetic browser/API journey was checked; partial = some required integration or quality is missing; unverified = no reliable result was established. None means production-certified or “working perfectly”.
- **Updating this document:** retain issue IDs, add the fixing commit/date and checks, and move an item to resolved only when its acceptance criteria have been verified. Do not erase verification limits or convert proposed features into current capabilities.

## What was completed in the dashboard work

- Restored the missing workspace CSS used by the revised dashboard components. Added selectors are scoped under `.a-shell`; added animation names were made distinct.
- Unified KPI strips, skill levels, score bars, charts, page layouts and navigation grouping across Home, My skills, Radar, Roles, Plan, Progress, Courses and Impact.
- Added matching dashboard translation keys for EN/BM/Chinese; **key parity does not establish complete translation quality** (see H06).
- Captured desktop and mobile screenshots of 14 individual/organisation screens. These were synthetic-fixture checks, not a production deployment review.
- Source work was split into 14 local commits ending at `968182b`; no push was performed. Machine-specific `.claude/` helper files were excluded.

## Repair order and owners

Priorities below are recommendations for the next owners, not changes to feature ownership. P0 = resolve before a compliant public demonstration or external readiness claim; P1 = resolve before presenting the affected journey as complete; P2 = quality improvement.

| ID | Priority | Open item | Suggested owners | Scope |
|---|---|---|---|---|
| H01 | P0 | Scheduled trend ingestion/persistence missing | M1 | Pipeline, workflow, deployment |
| H02 | P0 | Synthetic-only policy not enforced | M2 + Core/M4; M3 guardrail review | Account/upload flow; backend required |
| H03 | P0 | Draft SDG mappings described as reviewed | M3 + M2 | Mapping review, ranking logic/copy |
| H04 | P1 | SDG weight and historical snapshot lost between views | M2 + M1 + M4 | UI, API parameters and contracts where needed |
| H05 | P1 | Organisation impact ignores selected role | M3 + M4 | UI and contribution API/service |
| H06 | P2 | English labels remain in BM/Chinese | M4 + M3 | Messages, badge presentation/contract |
| H07 | P2 | Next.js dev indicator intercepts mobile More | Core/M4 | Development configuration and UI verification |
| H08 | P1 | Earned learning does not feed matching | M2 + M3 | Shared skill-level semantics/integration |
| H09 | P0 | Historical observations assigned to newer demo dates | M1 + M4 disclosure | Pipeline provenance and visible source dates |
| H10 | P1 | Certificate link checks do not establish competence | M3 + M2 integration | Evidence semantics, review and UI claims |

## Scope and verification limits

- Read-only audit of `feat/core-insight-design`; no application source was changed.
- Examined the two supplied checklists, frontend wiring, backend services, seed data, tests and workflows.
- The app and API were initially stopped. Browser checks used the actual Next.js frontend with an isolated API test process, the repository's synthetic Aisyah/HR fixtures, in-memory storage, and the existing frozen trend fixtures. No developer database or real user records were used.
- Browser checks covered login, SDG slider, snapshot replay, role detail, pathway saving, progress and badge updates, BM/Chinese switching, mobile navigation, HR dashboard, team target selection, and organisation/region impact.
- Quality gate rerun for this documentation handoff: **584 passed, 21 skipped**; Ruff lint/format, ESLint, TypeScript, translation-key parity and contract comparison passed. The normal `uv` invocation failed on a Windows sandbox cache permission; the same task-runner checks then passed outside the sandbox using installed Node CLIs and temporary contract outputs, without rewriting tracked contracts. One dependency deprecation warning concerned Starlette TestClient's use of HTTPX. Database-dependent checks remain outside this verification. Passing tests do not establish production readiness.
- This handoff reuses the earlier synthetic browser observations and rechecks relevant source wiring; it does not claim a fresh complete browser/deployment audit.
- Fresh external ingestion, deployed scheduling, restart persistence, every external course link, every route at every viewport and live model-provider integration were not verified.

## Checklist results

| Requirement | Result | Evidence / qualification |
|---|---|---|
| Skills profile intake | Implemented; covered by tests | PDF/text extraction, questionnaire, interests, study hours, budget, learning style, skill confirmation and catalogue validation exist. Synthetic PDF fixtures exist for Aisyah, Wei Jie and Ravi. Synthetic-only use is not enforced. |
| AI-trend signal layer | Partial | arXiv ingestion, BLS baseline, scoring, dated snapshots and Radar exist. Scheduled ingestion/storage is not wired; the generic runner is a placeholder. Browser audit used frozen fixtures, not a fresh upstream run. |
| Future-role matching | Implemented; context bugs | Ranked roles, skill/trend/interest parts, missing and partial skills work. Weighted list scores differ from detail scores because SDG weight is dropped. |
| Personalised reskilling pathway | Implemented and exercised | Aisyah's top role generated two ordered steps, four courses, 7.7 hours, two weeks at six hours/week and RM 0 cost. Budget, prerequisite and HRD logic have tests. Saving the plan worked in the browser. Current availability and claimability of every external course were not revalidated. |
| SDG mapping | Partial | All seven catalogue roles and 113 skills have target mappings. Personal/company/region contribution views exist. All 13 role links and 127 skill links in the seed are unreviewed. |
| Handling uncertainty | Implemented; historical context issue | Moderate/Fast changes scores; the role page shows low/high ranges and estimate labels. Historical match detail embeds an outlook from the latest snapshot. |
| Catalogue-only recommendations / validator | Implemented and tested | Deterministic catalogue selection and `validate_ids` rejection of unknown IDs exist. No live language model is enabled. |
| Sources on recommendations | Implemented and tested | Recommendation metadata contains sources, URLs, dates, scenario and estimate status; UI disclosure controls exist. A source citation does not establish that the source is fresh. |
| LLM disclosure | Implemented | About and README disclose `LLM_PROVIDER=none`. Only the null provider is implemented; adding a real provider would need implementation and disclosure updates. |
| Human-in-charge messaging | Implemented and exercised | Disclaimers, explicit plan choice and learner acceptance of proposed replanning exist. No autonomous hiring decision flow was found. |
| Synthetic data only | Not enforced | Synthetic fixtures exist, but sign-up accepts/stores names and email addresses and inserts `is_synthetic=false`. Upload consent does not restrict files to synthetic fixtures. |
| Trend replay / automatic replanning | Partial | Replay UI displays dated comparisons and drivers. Ravi's order changes between the two fixtures; Aisyah and Wei Jie's scores change while rank order stays stable. Replanning proposal/acceptance exists, but live scheduled refresh is missing. Replay ignores SDG weighting. |
| SDG-weighted ranking slider | Implemented; consistency bugs | At 60%, Aisyah's AI Operations Specialist moves above Data Analyst. Clicking the top weighted role changes its displayed fit from 79% to 48%. The replay panel uses the unweighted order. |
| Employer / HR view | Implemented and exercised | Dashboard and 36 heatmap cells loaded. Changing the target to Data Analyst rebuilt a three-step, four-week plan for two members. Organisation impact still used the default Process Automation Analyst target. |
| Fairness checks | Implemented and passing | Protected field checks and counterfactual tests exist; the audit endpoint returned `passed=true`. This verifies the implemented checks, not the absence of all possible bias. |
| EN / BM / Chinese and mobile | Partial | Locale switching works and inspected mobile pages had no horizontal overflow. BM/Chinese retain English interface strings and badge labels. The development badge intercepts pointer clicks on mobile More. |
| Progress tracking / badges | Implemented and exercised | Browser Mark done changed progress to 8%, awarded First course done and raised SQL progress to level 1. Completing all courses through the API reached 100% and awarded milestone/skill badges. Matching scores do not use these earned levels. |
| Aggregated SDG view | Implemented; target-context limitation | Company and Kuala Lumpur regional summaries returned data and rendered. They use the default organisation target rather than the target selected in the team-plan URL. Regional coverage is based on seeded organisation-region records. |
| Chatbot coach | Absent, optional | No chatbot route/UI or live model provider was found. Its absence does not block the mandatory checklist. |

## Findings to resolve

### H01. Scheduled trend ingestion is missing

The weekly workflow is a dry-run source check for SDGs, courses and links; it does not fetch, score or persist trend updates. `src/pipelines/trends/run.py` prints “not implemented yet”. Manual lower-level ingestion modules exist, so the entire trend implementation is not a stub.

Evidence: [trend runner](../src/pipelines/trends/run.py), [source-check workflow](../.github/workflows/data-sources.yml).

**Fix direction:** wire the existing ingestion, embedding, scoring and persistence stages into one scheduled job. Pin the worker's dependencies/model revision, validate IDs and metadata before publishing, and retain the last valid snapshot on failure.

**Acceptance:** a controlled scheduled run publishes a new valid snapshot that the Radar/matching can resolve; a failed run preserves the last valid snapshot and visibly reports its age/status. A dry-run link check alone does not satisfy this.

### H02. The synthetic-only guardrail is not enforced

The app offers ordinary registration and stores submitted account identity fields. The database insert explicitly sets `is_synthetic=false`. Sample personas and PII cleaning do not restrict account registration or CV ingestion to synthetic material. No real personal data was used during this audit.

Evidence: [account insertion](../src/api/app/core/accounts.py), [CV endpoint](../src/api/app/features/profile/router.py), [public upload consent](../src/web/messages/en/ui.json).

**Fix direction:** introduce an enforceable synthetic demonstration mode using supplied personas/files or a constrained synthetic intake. Apply it to all public, preview and authenticated ingress paths. A checkbox or PII redaction alone cannot guarantee synthetic input. Reporting a public upload-copy defect does not authorise landing-page edits under the current user restriction.

**Acceptance:** approved synthetic journeys still work, while arbitrary real identity/CV submission paths are unavailable in the demo deployment. Document how synthetic records are retained/deleted. Verify API enforcement as well as interface wording.

### H03. Draft SDG links are treated as reviewed in ranking explanations

Coverage is complete, but review is not: seed review counts are 0/13 role links and 0/127 skill links. `role_links()` returns drafts too; the slider consumes them while describing its input as reviewed links. The contribution view does label them as drafts, but this qualification is lost in ranking explanations.

Evidence: [review status](../src/api/app/features/sdg/repository.py), [ranking lookup](../src/api/app/features/matching/sdg_weight.py), [ranking explanation](../src/api/app/features/matching/sdg_weight.py).

**Fix direction:** have a human check each role/skill-to-target rationale and record reviewer/date. Ensure ranking either uses eligible reviewed links or clearly identifies draft input consistently. Do not mark records reviewed simply to clear a test.

**Acceptance:** every displayed “reviewed” mapping has genuine review evidence; draft status is preserved wherever drafts remain visible. Zero SDG weight still reproduces the base ranking, and the weighted breakdown agrees with the final score.

### H04. Ranking and snapshot context are inconsistent across views

- With SDG weight 60%, the top role displays 79%; its detail link omits the weight and the detail displays 48%.
- With weight 60% and the older snapshot, the replay panel calls Data Analyst #3 while the cards place AI Operations Specialist #3. Replay is called without the selected SDG weight.
- The historical match page cites 2026-10-13 while its outlook panel cites 2026-10-20.

Evidence: [list/detail link and replay call](../src/web/src/features/matching/components/MatchesView.tsx), [detail fetch](../src/web/src/features/matching/components/MatchDetailView.tsx), [outlook fetch](../src/web/src/features/scenarios/components/RoleOutlookPanel.tsx).

**Reproduce:** with the synthetic Aisyah profile, set SDG weight to 60%, record a role's score and open its detail. Select the older snapshot and compare replay ordering and outlook metadata with the cards. The exact percentages depend on the fixture revision; the invariant is identical inputs/context must produce consistent results.

**Fix direction:** carry `scenario`, `snapshot_date` and `sdg_weight` through navigation, fetch helpers and endpoint contracts. Resolve a consistent context for each view; a UI-only query-string fix is insufficient where the endpoint cannot receive that parameter.

**Acceptance:** list/detail agree on the same weighted score; replay uses the selected weight on both snapshots; the historical outlook and match data cite the selected period. Context survives navigation and reload.

### H05. Organisation impact ignores the selected target role

Selecting Data Analyst on `/org/plan` successfully recomputes the plan. Following Impact preserves `role=data-analyst` in the URL, but the content says `For role: process-automation-analyst`. The contribution endpoint receives no chosen role and rebuilds member plans using the default target.

Evidence: [frontend contribution fetch](../src/web/src/features/sdg/api.ts), [organisation contribution](../src/api/app/features/sdg/service.py).

**Fix direction:** carry the selected role through the contribution request and service, with the existing default retained only when no role is supplied. Apply the same rule to any affected organisation/region aggregation. Check access controls and known-role validation.

**Acceptance:** selecting Data Analyst produces a plan and impact view for Data Analyst; switching targets updates both. A URL parameter that is never consumed does not count as passing.

### H06. Localisation is incomplete

Both BM and Chinese show English “Sources & methodology”, “Details & sources” and “First course done”. The first two are English values in the translated message files; badge labels are supplied in English by the API and rendered directly. Catalogue course titles may appropriately remain in their provider's original language.

Evidence: [BM messages](../src/web/messages/ms/common.json), [Chinese messages](../src/web/messages/zh/common.json), [badge labels](../src/api/app/features/pathway/service.py).

**Fix direction:** translate interface strings and render badge labels from stable badge IDs/message keys rather than relying on English API display text. Coordinate a contract change only if needed; preserve provider course titles where appropriate.

**Acceptance:** EN/BM/Chinese key parity passes, and manual checks of the three affected labels plus progress/evidence screens show correct user-facing translations in every locale.

### H07. Development badge overlaps mobile navigation

At 390px width, clicking More opened Next.js Dev Tools instead. Keyboard activation of More opened the correct navigation sheet. This is a development-only issue; production behavior was not tested.

Evidence: [badge position](../src/web/next.config.ts).

**Fix direction:** choose a non-overlapping development-indicator placement or disable the indicator during screenshot/testing sessions. Check the actual production build separately; do not claim a production navigation failure from a dev-only overlay.

**Acceptance:** pointer and keyboard activation of More work at mobile widths with the development configuration, and the navigation sheet is checked in a production build. Preserve focus trapping/restoration.

### H08. Completed learning does not improve future-role matching

This goes beyond the screenshot's basic progress/badges requirement, but is promised in `docs/TASKS.md`. Completing all four courses reached 100% progress and earned SQL/data-visualisation badges; matching results stayed identical. Matching reads the original profile levels, while progress derives earned levels separately.

Evidence: [matching profile levels](../src/api/app/features/matching/repository.py), [progress update](../src/api/app/features/pathway/service.py).

**Reproduce:** record matching for the same synthetic profile/context, complete its four-course fixture plan, inspect progress/earned levels and request matching again. Progress reaches 100% but the matching inputs remain the original profile levels.

**Fix direction:** M2/M3 should agree on a single skills view consumed by matching and pathways, while retaining the provenance of self-report, completion and assessed evidence. Distinguish a completed course from demonstrated competence. The learning/evidence policy is a design decision to log before implementation, not an instruction to blindly raise scores for every click.

**Acceptance:** evidence accepted under the agreed policy updates the relevant skill gap and recomputes matching/pathways consistently; rejected/unverified evidence retains its correct status. Unrelated skills are unaffected. Scores may remain unchanged when the new skill is irrelevant to that role; do not force every score to rise.

### H09. Demo dates differ from the underlying observation periods

The dual-snapshot pipeline explicitly uses arXiv windows **2024-10-06 through 2024-10-12** and **2024-10-13 through 2024-10-19**, assigning them to demo snapshots dated **2026-10-13** and **2026-10-20**. Stored provenance exists, but a newer snapshot date must not be presented as evidence of newer research observations.

Evidence: [dual-snapshot generator](../src/pipelines/trends/populate_dual_snapshot.py), [snapshot fixture exporter](../src/pipelines/trends/export_fixtures_from_db.py).

**Fix direction:** distinguish observation period, retrieval time, snapshot generation time and historical-demo status in the data and presentation. Keep historical replay available; obtain fresh observations through H01 for any live-data claim.

**Acceptance:** a user can identify the actual period measured without reading source code, and no card implies that the 2024 input was observed in 2026. New ingestion uses honest dates and retains provenance.

### H10. A reachable certificate URL is not a verified skill assessment

This is an evidence limitation and enhancement boundary; URL reachability checking is not itself a malfunction. Reproduce any misleading UI claim before classifying it as a separate defect.

The certificate verifier checks the submitted domain and HTTP response using HEAD/GET; it explicitly does not inspect page content. Existing `self_reported`, `certificate_link` and `org_confirmed` statuses are useful, but URL reachability alone cannot verify certificate ownership, authenticity or skill competence.

Evidence: [certificate verifier](../src/api/app/features/pathway/verification.py), [evidence UI](../src/web/src/features/pathway/components/EvidenceBadge.tsx), [organisation review](../src/web/src/features/pathway/components/VerificationQueueView.tsx).

**Fix direction:** keep evidence labels precise and route substantive verification to an authorised reviewer. An optional practical assessment can strengthen the workflow later. Do not describe the current URL probe as content/identity verification or automatically certified competence.

**Acceptance:** UI and documentation distinguish link availability, reviewer confirmation and assessed skill. Failed links and unreviewed submissions do not acquire stronger evidence status; users outside the organisation cannot review its members.

## Current AI, data and privacy facts

- **Runtime GenAI:** only `NullProvider` is implemented; default `LLM_PROVIDER=none`. Setting another provider name is not a working integration. The absence of an optional chatbot is not a missing must-have. See [provider implementation](../src/api/app/core/llm/provider.py).
- **Offline AI:** the trend pipeline uses `sentence-transformers/all-MiniLM-L6-v2` embeddings to relate research text to skill labels. Matching/pathway selection also use explicit catalogue-based rules. Do not claim a custom-trained foundation model or active Claude/OpenAI runtime from development-tool use.
- **Signal meaning:** arXiv attention and the BLS baseline do not establish Malaysian vacancies or an individual's job-loss probability. Moderate/fast ranges are heuristic estimates, not calibrated confidence intervals. See [trend scoring](../src/pipelines/trends/score.py).
- **Catalogue scope:** seven roles and 113 skills in the audited custom catalogue. Official ESCO/ONET/MASCO integration has not been established; do not describe the catalogue as an official national taxonomy. See [taxonomy notes](../src/data/seed/taxonomy/README.md).
- **Privacy:** the application can store account/profile, membership, plan, progress and evidence-URL data. Raw CV upload bytes are parsed in memory. Session expiry does not delete stored data. Automated retention/deletion and encryption at rest were not verified. See H02 before any public-demo claim.
- **Certificate probes:** submitted links can result in outbound requests to their providers. No active generative-model provider currently receives CVs.
- **Course cost/HRD assumptions:** catalogue prices and claimability were not all revalidated live. “Free to enrol” need not include a free certificate, and an HRD-claimable tag does not guarantee eligibility, approval or reimbursement. Preserve the conditions behind any RM 0 estimate.
- **Licences:** PyMuPDF is offered under AGPLv3 or commercial terms, not MIT. Reconcile all shipped dependency/model/data licences before deployment; this is a dependency declaration item, not a claim of legal compliance.

## Additive enhancements proposed — not implemented

These are follow-up concepts discussed with the user. Preserve all must-haves. Stabilise H01–H10 before presenting these as a complete product. They are suggestions for later design/approval, not instructions overriding frontend-only scope or existing ownership.

| Proposal | Existing foundation | Additional work | Owner discussion |
|---|---|---|---|
| Optional organisation workflow change brief | Org roster, heatmap, selected target and team plan | Reviewed workflow-to-skill mapping, affected skill confirmation; keep direct individual intake | M4 + M2/M3 |
| Transition Stress Test | Role comparison, budget/hours, scenarios and prerequisite-aware pathway engine | Request-scoped hours/budget/deadline sandbox; show feasibility reasons; preserve saved data until accepted | M3 + M2 + M1, M4 UI |
| Shared useful first steps | Role requirements and ordered catalogue courses | Identify valid foundational actions across multiple feasible candidate roles/scenarios; disclose when none are shared | M3 + M2 |
| Practical assessment loop | Progress, evidence submissions, org reviewer queue | Start with one reviewed synthetic-data task/rubric, retain assessment history, feed accepted evidence into H08 | M3 + M2 |
| Reproducible transition decision record | Recommendation metadata and plan persistence | Record profile/evidence version, snapshot, scenario, SDG weight, constraints and reasons; contract/migration review if persisted | Feature owners + Core |
| Malaysian demand evidence adapter | Source ports, snapshots and semantic mapping | Obtain permitted data, review taxonomy mapping/coverage and evaluate against labelled examples | M1 + M2 |
| Aggregate programme outcomes | Existing company/region contribution summaries | Declare periods/denominators, distinguish completion from assessed gap closure, evaluate coverage and appropriate access | M4 + M3 |

Suggested architecture for discussion: extend the existing modular FastAPI application and use one scheduled ingestion worker. A large microservice rewrite is not required by these proposals. Follow the decisions-log protocol if an architecture/method/schema is selected.

Suggested evaluation target: at least **20% lower median time to produce a valid, evidence-supported plan** compared with a static catalogue workflow, without reducing valid-plan rate. This is an unmeasured proposal. Establish the baseline first using matched fictional cases. Do not claim job placements, income gains, national underemployment reduction or carbon savings from the current prototype.

## Handoff verification checklist

- [ ] Reproduce the assigned issue at the current revision and check whether another member already fixed it.
- [ ] Confirm the permitted frontend/backend/data scope and affected feature owners before editing.
- [ ] Keep the six must-haves and human approval of career/training decisions.
- [ ] Add focused regression coverage for the broken invariant; use synthetic fixtures only.
- [ ] If changing a method, model, formula, dataset, dependency, schema or architecture, append the required member decision entry. Regenerate clients for approved contract changes; use a new migration for schema changes.
- [ ] Run `make check` or `uv run --no-project python src/scripts/dev.py check`; report skips and deployment checks separately.
- [ ] Recheck the affected user journey, including scenario/date/role/SDG context, mobile behaviour and attribution where relevant.
- [ ] Update this report with fixing commit, verification evidence, remaining limits and status. A green unit suite alone does not establish the browser integration.

## Demonstration guidance

- Use Ravi to demonstrate a real rank-order change across 2026-10-13 and 2026-10-20; Aisyah/Wei Jie demonstrate score changes without rank movement.
- Run the demo with synthetic accounts and the synthetic sample CVs only (H02 decision: no in-app restriction).
- Do not describe seeded SDG mappings as human-reviewed.
- Do not describe frozen fixtures as continuously refreshed live data.
- Keep PostgreSQL persistence and fresh-source validation marked unverified until tested against the intended deployment.
