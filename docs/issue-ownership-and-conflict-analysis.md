# Your fixes and the 13 GitHub issues: ownership and integration guide

Review date: 30 October 2026. Local revision: `95a2505` on
`fix/react-version-mismatch`. Fetched review branch:
`origin/fix/core-review-regressions` at `8cc9ed0`.

## 1. What this document is for

Your strongest technical follow-up is **#51, MyCOL integration and fairness-harness
review**. You can also contribute to **#61, encoder/workflow integration**, and
**#58, infrastructure verification**, but those already have integration owners.
**#49** needs human measurements using your existing tools.

You asked to keep submission documentation in Google Docs. This file is the requested
technical explanation and handoff; it does not restart local submission writing or
PDF export work. **#50 remains outside the local implementation scope.** Creating
this analysis does not implement, close, claim ownership of, or authorize live
execution for any issue.

“Your work” here means the package delivered in [PR #30](https://github.com/pecel-lelele/adept/pull/30),
cross-checked against its file diff and the [safe-fix tracker](daftar-perbaikan-aman.md).
It does not mean that you originally authored every underlying subsystem. Issue
assignment identifies the current coordinator, not who caused a defect.

The issue descriptions were read live from GitHub during this review. Assignments,
drafts and branch contents can change after this snapshot. The tracker contains
historical stages: early statements such as “uncommitted” or “not implemented” must
be read alongside later sections and the merged PR, rather than treated as current
Git status.

## 2. What “conflict” means here

| Kind | Plain-language meaning | Example in this work |
|---|---|---|
| Text conflict | Two changes edit the same lines, and Git cannot combine them automatically. | Two people rewrite the encoder's submission/cleanup block. |
| Behaviour conflict | Git can merge the files, but the combined behaviour is wrong. | A new async submission path accidentally drops your cancellation or global deadline. |
| Contract/data conflict | Producers and consumers disagree about fields, identifiers or meaning. | A badge mapping uses a role ID that the catalogue branch renames. |
| Coordination conflict | Two people solve the same task or build on different drafts. | Rebuilding Docker while Rayen is integrating an existing infrastructure worktree. |

**No merge was attempted for this review, so no unresolved Git merge conflict was
observed.** The risks below describe file overlap, semantic dependencies and reported
drafts. A clean merge alone would not prove compatibility.

There is an important distinction between a completed foundation and a finished
product feature. Your reference CSV, calculator and mock-tested encoder cleanup can
be valid deliverables even when badges, human measurements or production publication
remain unfinished. A follow-up issue is not automatically evidence that the original
deliverable was broken.

## 3. All 13 issues compared with your contributions

All 13 issues were open when checked.

| Issue | Current GitHub assignee | Relationship to your work | Recommended role for you |
|---|---|---|---|
| [#49: Human KPI trials](https://github.com/pecel-lelele/adept/issues/49) | keanullimen | Direct continuation of A1 calculator/protocol delivery. | Run and analyse real trials; keep submission prose in Google Docs. |
| [#50: Technical declaration export](https://github.com/pecel-lelele/adept/issues/50) | keanullimen | Direct continuation of A2/A4 documentation and asset confirmation. | Handle in Google Docs; excluded from local coding. |
| [#51: MyCOL badge and fairness follow-up](https://github.com/pecel-lelele/adept/issues/51) | keanullimen | Direct continuation of A14 reference data and A13 harness. | Lead verified badge integration; review the existing fairness rewrite before duplicating it. |
| [#52: Heatmap dates and batched profile reads](https://github.com/pecel-lelele/adept/issues/52) | LouSens | Existing organisation behaviour outside your PR's technical fixes. | Leave implementation with the owner; preserve metadata expectations if your badge appears in team views. |
| [#53: Small-group SDG privacy](https://github.com/pecel-lelele/adept/issues/53) | LouSens | Adjacent to your A11 privacy notice, but backend aggregation is a different feature. | Optional review of user-facing explanations after suppression behaviour is implemented. |
| [#54: Bound pathway trend I/O](https://github.com/pecel-lelele/adept/issues/54) | LouSens | Similar resource-cleanup principle to A9, but different code and operation. | Share relevant testing ideas; do not treat encoder cancellation as a repair for this thread. |
| [#55: Replit proxy trust verification](https://github.com/pecel-lelele/adept/issues/55) | DarrenSuw | Separate deployment/security boundary. | No direct continuation of your fixes. |
| [#56: Sourced catalogue coverage](https://github.com/pecel-lelele/adept/issues/56) | LouSens | Adjacent to MyCOL research; shares role identifiers and source requirements. | Coordinate the catalogue IDs used by #51; avoid a parallel catalogue expansion. |
| [#57: Workspace switch POST](https://github.com/pecel-lelele/adept/issues/57) | rayensetyawan | Separate workspace/auth flow. | No direct implementation role; consume the final navigation convention. |
| [#58: Infrastructure integration/verification](https://github.com/pecel-lelele/adept/issues/58) | rayensetyawan | Continues your A10 Docker investigation and touches CI you changed. | Help verify the integrated draft, especially locked builds, startup and test coverage. |
| [#59: Navigation and return paths](https://github.com/pecel-lelele/adept/issues/59) | rayensetyawan | Separate navigation feature; may share badge display pages. | Keep badge rendering changes small so navigation fixes remain intact. |
| [#60: DB, admin identity and member cleanup](https://github.com/pecel-lelele/adept/issues/60) | LouSens | Separate backend/security work; stable admin IDs are a dependency of #61. | Do not create a second admin authorization design while supporting refresh tests. |
| [#61: Dashboard-triggered trend refresh](https://github.com/pecel-lelele/adept/issues/61) | LouSens | Direct overlap with A8 workflow hardening and A9 encoder cleanup. | Review and extend mocked integration tests; let the owner integrate hosting and refresh. |

Several issues were revised after the initial list. In particular, #52, #53, #54,
#56 and #60 are now assigned to LouSens. Their updated descriptions distinguish
historical authorship from later maintenance. Use these current assignments rather
than the first issue table from the conversation.

## 4. Issue #51, part A: connecting your MyCOL data to the application

### What you already delivered

You supplied a reference table of 66 occupation groups from MyCOL 2024/2025, MASCO
codes, page locators, retrieval dates and source checksums. The relevant files are:

- [Reference CSV](reference/critical-occupations.csv).
- [Provenance record](reference/critical-occupations.provenance.json).
- [Reference scope and limits](reference/critical-occupations.md).
- [Reference tests](../tests/reference/test_critical_occupations.py).

The reference explicitly says that it is outside runtime seeds and has no role-ID
crosswalk. Its tests validate the delivered data and provenance; they do not prove
that any Adept role qualifies for a MyCOL badge.

### What the issue adds

A badge needs a traceable chain:

```text
Existing Adept role ID
  -> reviewed mapping to a supported MASCO/MyCOL occupation
  -> verified MyCOL record and edition
  -> API badge with source metadata
  -> visible user-facing badge
```

The missing step is the reviewed mapping, not another copy of the 66-row CSV.
A broad occupational group can include titles that the report does not list as
critical. A similar-looking role label is insufficient evidence. If no supported
mapping exists for a role, it should receive no badge.

### Where your work meets other people's work

| Shared area | Likely point of contact | How to avoid incompatibility |
|---|---|---|
| Role catalogue | LouSens's #56 coverage enhancement | Map stable stored IDs; recheck any renamed/new role and verify its evidence independently. |
| Matching API | Existing `RoleMatch` consumers | Choose an additive badge representation; update affected consumers and generate contracts together. |
| Match cards/detail pages | Active review-branch display changes | Add the badge to the current component version without replacing unrelated wording, scenario or consent fixes. |
| SDG display | Existing SDG target fields | Keep a critical-occupation badge distinct from an SDG target or contribution score. |
| Metadata | Existing recommendation attribution | Preserve the actual source edition/retrieval date; do not reuse today's date as the source date. |

The fetched review branch changes
`src/web/src/features/matching/components/MatchesView.tsx`,
`MatchDetailView.tsx`, `MatchSdgTargets.tsx` and matching translations. These are
real shared display areas to reconcile. This is observed file overlap, not evidence
that Git will necessarily report a conflict.

### Recommended implementation boundary

Start with a badge only. Do not add MyCOL score bonuses or reorder matches as an
incidental side effect: that would change the matching formula and introduce a
separate product decision. The issue's badge request does not require a ranking change.

Keep the reviewed role mapping separate from the original transcribed source table.
Preserve source labels and provenance. Generate OpenAPI/TypeScript bindings from the
production contract if the API changes; do not edit generated files by hand.

Completion should demonstrate that supported IDs get the correct sourced badge,
unsupported/unknown IDs get none, existing match scores remain correct, and badge
output has meaningful coverage in
[the attribution regression](../tests/api/guardrails/test_sources_everywhere.py).
Record the eventual schema/data/method change in the normal decisions log as part
of implementation. This analysis itself introduces no such implementation change.

If runtime integration is postponed, distinguish a retained reference dataset from
an unsupported claim that the application already uses MyCOL. Removing an inaccurate
product claim does not logically require deleting a correctly labelled reference.
The issue owner should resolve the chosen delivery outcome before closure.

## 5. Issue #51, part B: your fairness harness and the teammate's rewrite

### What the existing code actually does

Your [offline harness](../src/pipelines/guardrails/matching_counterfactual.py)
uses `model_copy(update=...)` to vary age, gender and background. However,
[the Profile contract](../src/api/app/contracts/profile.py) has no fields with those
names. Changing extra attributes that the matching path does not consume cannot
establish that sensitive information is handled correctly throughout that path.

The harness also temporarily replaces profile reads using `unittest.mock.patch`.
That is contained in an offline pipeline module, not evidence that the web server
automatically runs it. The concrete concern is the validity and placement of the
evaluation method, rather than an observed production mocking incident.

The previous dummy-query unit tests show harness mechanics. They are not production
fairness evidence, as the tracker already discloses. This limitation does not by
itself prove that the ranking algorithm discriminates.

### Where the conflict is

The issue says a rewrite is underway. At fetched commit `8cc9ed0`, this harness has
no diff relative to the local base. The rewrite may therefore be in another or
uncommitted worktree; it was not verified in the published branch. Absence from that
branch does not mean the teammate has done no work.

Two simultaneous replacements of the same harness would duplicate the task and may
produce contradictory fairness claims. The best split is for one person to own
implementation and the other to review inputs, production-path coverage and conclusions.

Review whether the eventual test exercises real supported input boundaries and
production scoring, keeps non-sensitive inputs/snapshot fixed, rejects empty
results, and includes a meaningful control showing the test can detect an unintended
change. Do not add protected attributes to production ranking just to make a test
appear more realistic. Any demographic data used for evaluation must remain clearly
synthetic and outside persisted learner ranking inputs.

## 6. Issue #61: preserving your encoder guarantees during refresh integration

### Your completed foundation

Your changes to [the encoder](../src/pipelines/trends/encoder.py) added one deadline
across batches, known-job cleanup on failure/timeout, provider-side execution/TTL
bounds, and preservation of the original error when cancellation fails. You also
hardened [trends-refresh.yml](../.github/workflows/trends-refresh.yml) and
[data-sources.yml](../.github/workflows/data-sources.yml): frozen installs, explicit
manual configuration failure and publication-derived summary dates.

The encoder still submits through `/runsync` in the reviewed code. It can poll a
returned queued job, but that does not avoid the initial synchronous cold-start wait.
Mock cleanup tests do not establish successful live publication or billing outcomes.

### What LouSens is adding

The updated issue describes an authorized administrator launching the existing
pipeline from the dashboard, seeing job status, and seeing the actual served snapshot
after publication. It proposes async `/run` submission and polling, server-side GitHub
dispatch, no duplicate active dispatches, and a production publication check.

### Exact integration risks

| Risk | Why it matters | Behaviour to preserve/test |
|---|---|---|
| Rewrite drops cleanup | A failed request can leave provider work running. | Cancel unfinished known-ID jobs; keep provider limits when the submission ID is lost. |
| Deadline restarts per poll/batch | Total work can exceed the intended budget. | Retain a bounded overall operation and explicitly bounded requests/cleanup. |
| Success means only “workflow green” | A skipped/no-publication run can be misrepresented. | Verify publication output, database snapshot and actual application display separately. |
| Missing settings silently skip manual work | The dashboard can appear successful without execution. | Preserve explicit manual failure and honest status reporting. |
| UI invents another admin rule | Web and API disagree about who can start paid jobs. | Reuse the stable account-ID authorization being addressed in #60. |
| Stale snapshot is relabelled fresh | New request time becomes false data freshness. | Preserve actual selected/served snapshot metadata and fallback disclosure. |

Your suitable contribution is focused mocked regression coverage in
[encoder cancellation tests](../tests/pipelines/trends/test_encoder_cancellation.py)
and review of the workflow changes. LouSens remains the integration owner. At the
fetched branch tip, encoder/workflow rewrites were not visible in the branch diff;
the issue reports an additional trends worktree that has not been inspected here.

There is also an important boundary with #54: cancelling an external RunPod job is
not the same operation as interrupting a database read inside a pathway thread.
Repairing either one does not automatically repair the other.

## 7. Issue #58: your Docker diagnosis and Rayen's infrastructure draft

### What you did, and what you did not do

Your A10 work was an investigation. It identified the missing web-local lockfile,
workspace/standalone packaging concerns and automatic migration/seeding at API boot.
It did not rebuild or remove Docker, start containers, or verify database persistence.

Current local code still shows the concrete issues:

- [web.Dockerfile](../src/docker/web.Dockerfile) copies `src/web/pnpm-lock.yaml`,
  while this repository uses the root lockfile.
- [boot.py](../src/docker/boot.py) automatically runs migration and seed commands.
- [docker-compose.yml](../docker-compose.yml) publishes API/web ports without an
  explicit loopback host binding.

### The teammate overlap

The updated issue reports infrastructure changes in an uncommitted worktree named
`agent-a30a3ff3fc8019a74`. That identifier was not present in this checkout's
`git worktree list`; its path, contents and readiness have not been independently
verified. Do not assume that a draft visible on another machine is part of `main`.

Rayen owns reconciliation of that draft. A fresh Docker implementation by you could
discard their packaging or environment decisions even if the two branches merge cleanly.
Your existing CI changes also overlap the issue's requirement to include complete
static, HTTP and regression test selection.

### A useful division of work

Rayen integrates the existing Compose/Docker/environment draft. You independently
verify root lockfile/workspace inputs, correct production output/assets, explicit
loopback host mappings, no migration/seed at ordinary image startup, and retained
CI coverage. Binding a process to `0.0.0.0` inside its container is different from
publishing a host port on every host interface; check the host mapping itself.

Build/start and migration/seed checks need an explicitly selected disposable database.
Never run `make setup` against whichever database happens to be in a developer `.env`.
Existing uncommitted React changes to `src/web/package.json` and `pnpm-lock.yaml`
are a separate compatibility input: they can affect Docker dependency resolution
without having been introduced by this infrastructure issue.

## 8. Issue #49: your measurement tool versus human outcome evidence

The [calculator](../src/scripts/kpi_time_to_plan.py),
[protocol](kpi-time-to-plan.md) and [trial template](kpi-trials-template.json)
already exist. The missing deliverable is observed data, not another timing formula.

Use five synthetic cases and three anonymous testers, each completing manual and
Adept workflows: 15 matched pairs, 30 trials. Freeze revision, catalogue, snapshot,
target roles and intake settings. Counterbalance order, record failures/timeouts,
and assess plan validity independently before interpreting speed.

The overlap with teammates is experimental stability. If a branch changes the
catalogue (#56), snapshot/refresh behaviour (#61), navigation (#59), or plans during
the study, results may no longer describe a single comparable version. Record any
changes and do not silently pool incompatible runs.

Your earlier backend HTTP journeys are useful integration tests, but do not measure
human thinking, corrections, browser navigation or a manual planning baseline.
Likewise, three testers completing five cases are three people, not fifteen
independent participants. Analyse the data honestly with the existing tool; write
submission results in Google Docs as you requested. Do not invent results to replace
the template's `not_run` entries.

## 9. Adjacent work and actual shared-file changes

**#56 and MyCOL:** coordinate stable catalogue IDs and evidence, but do not treat
critical-occupation inclusion as proof of demand growth, current vacancies or
availability of a Malay course. Those are different source claims.

**#53 and your privacy page:** the notice explains data flows; it does not implement
minimum group sizes. Backend suppression must count distinct consenting people,
including duplicates across organisations, before translated wording can accurately
describe the result. The current issue leaves implementation with LouSens.

There is already a concrete overlap in your A11 files: the fetched review branch
changes `src/web/messages/en/privacy.json`, `ms/privacy.json` and `zh/privacy.json`,
plus `src/web/src/components/shell/Site.tsx`. The English diff adds browser-storage,
sharing and contact explanations. These are observed edits to files in your PR,
not proof of an error or ownership violation. Preserve accurate new behaviour when
reconciling them; do not restore the old notice wholesale. Provider/retention facts
still require evidence.

## 10. Important corrections and unresolved findings

1. **Heatmap scenario invariance is not automatically a bug.** #52 now correctly
   distinguishes observed skill gaps from trend-weighted recommendations. Do not
   force numerical differences simply to make the toggle appear active.
2. **The duplicate migration pair already has a narrow compatibility exception.**
   #60 now asks to test/preserve it, rather than edit historical migrations.
   Effective RLS and admin checks remain separate concerns.
3. **Your tracker records an unresolved guest-preview HTTP 503.** Its latest recorded
   suite result is 1,030 passed, 32 skipped and one failure. This is historical
   evidence, not a test result from this document's creation. It involves matching's
   two-second trend wait with an intentionally unavailable test database; #54's
   pathway thread and #61's publication work are related reliability areas, not
   demonstrated fixes for that regression.
4. **A15/T5 empty-jobs freshness remains separately deferred in the tracker.**
   It depends on truthful no-data contract semantics. Do not assume any of these
   13 issue closures will automatically resolve it.
5. **An issue assignment is not a causal finding.** Historical authorship claims
   in issue bodies are the author's evidence unless separately verified here.
   This review verified PR file membership, current selected code, published
   branch diffs and current assignments; it did not audit every historical commit.

## 11. Suggested working order and coordination checkpoints

| Order | Your bounded task | Reconcile before editing | Evidence needed before calling it complete |
|---|---|---|---|
| 1 | #51 MyCOL role mapping and badge | #56 catalogue IDs; current matching display changes | Reviewed mappings, source metadata, negative cases, generated contracts, unchanged intended scores. |
| 2 | #51 fairness review | Locate the teammate's actual rewrite/draft | Meaningful production-boundary tests and appropriately limited conclusions. |
| 3 | #61 encoder/workflow test contribution | Existing trends worktree and #60 admin convention | Mocked cold-start/failure/cleanup tests; production publication remains a separate verification step. |
| 4 | #58 verification contribution | Rayen's existing infrastructure draft | Disposable build/start results, loopback mappings, explicit DB operations and complete regression selection. |
| Alongside | #49 human trials and calculator analysis | Freeze a coherent application version | Real trial records, failures, validity assessment, sample size and measured output. |

Use one implementation owner for each shared rewrite and a second person for review
or independent tests. Necessary shared-file changes are within an authorized
implementation task; file ownership alone is not a reason for repeated approvals.
Unresolved product choices and externally consequential operations still need their
appropriate coordination/authorization. No teammate messages were sent by this review.

## 12. Evidence and verification of this handoff

Evidence used: live GitHub issue bodies/assignments, PR #30's local merge diff,
the safe-fix tracker and manifests, selected production files, local worktree inventory,
and the fetched review-branch diff. Remote branch tips above were refreshed; this
review did not switch, merge or reset branches.

Only this handoff file is intentionally added. Existing React/package-lock edits
are preserved. No application code, catalogue, migration, workflow, submission
document or decisions entry is changed by this analysis. No live inference,
workflow dispatch, database migration/seed or deployment is performed.

### Verification performed for this file

| Check | Observed outcome |
|---|---|
| Local Markdown links | PASS: all 18 local targets exist. |
| Issue coverage and formatting | PASS: links to all 13 issues, balanced code fences and no trailing whitespace. |
| Existing React edits | PASS: SHA-256 hashes for the package manifest and root lockfile match the values recorded before this work. |
| Ruff lint/format and ESLint | PASS on the approved quality-gate run. |
| EN/MS/ZH key parity | PASS. |
| TypeScript | PASS. |
| Generated contracts | PASS: regeneration reported contracts in sync; no tracked contract diff remains. |
| Approved full pytest run | 1,177 passed, 32 skipped, 13 setup errors, 54 subtests passed; exit was nonzero. |
| Focused recovery run | PASS: 17 cases, including all 13 affected setup cases, completed successfully after using an existing temporary-directory parent outside the sandbox. |
| Original combined quality-gate command | PARTIAL: it exited nonzero on test setup; its other stages passed. No single clean full-gate rerun is claimed. |
| Frontend build, browser and production checks | Not run for this analysis-only file. |

The first sandbox gate also encountered Windows temporary-file/subprocess restrictions
and pnpm cache access failures. The approved full run resolved those restrictions,
but the configured `.pytest-tmp/` parent did not exist, causing `FileNotFoundError`
in the 13 fixture setups. Only the affected tests were rerun, under the existing
`tmp/` parent with a unique directory. That rerun selected 17 cases because it also
included the complete session-secret module. These counts are separate runs and
must not be added together as a new full-suite result.

The approved full run did not reproduce the historical guest-preview 503. No runtime
repair was made here; one successful run does not establish that an intermittent
regression has been resolved. The 32 skips remain skips, not passing database checks.
One existing FastAPI/Starlette TestClient deprecation warning remains.

The commands used CSV test storage, unavailable loopback database access and disabled
paid providers; database test opt-ins were removed from the child process environment.
Local command logs are in ignored `tmp/issue-conflict-*.log` files. No tests were
modified, removed or given new skips. Existing historical figures in earlier sections
must not be read as fresh results.

Suggested commit after review: `docs(core): explain issue ownership and integration conflicts`.
