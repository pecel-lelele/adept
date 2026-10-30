# Isolated safe-work handoff

Date: 30 October 2026. Base revision: `8bb8115`.
The supplied prompt identifies item 1.1 as active and the remaining Phase 1-3 work as
queued; actual IDE progress is not observed. All listed forbidden files remain excluded.
No commits, push, PR publication, migrations, seed, workflow dispatch or inference were performed.

## Prepared changes

| Item | Branch / checkout | Result and limits |
|---|---|---|
| A1 | `feat/a1-offline-planning-kpi`, `tmp/a1-offline-planning-kpi/` | Standalone JSON calculator, empty 30-trial template, manual protocol and five standard-library tests. No DB/application imports. Real trials and impact measurements remain outstanding. |
| A2-A4 | `docs/a2-submission-evidence`, primary checkout | Presentation-tool inventory, dated evidence register, corrected synthetic CV/document/video references, six-weight final-round checklist. Criterion names remain pending the participant handbook. Existing PDFs are not regenerated. |
| A5, wording only | Same documentation branch | README timezone wording corrected to MYT. Existing test counts are preserved as requested; no CI or environment configuration changes. |
| A14, preparation only | `docs/a14-mycol-reference`, `tmp/a14-mycol-reference/` | Nine occupation-group labels in a JSON reference outside runtime seeds. Indexed official excerpt only; direct brochure URL failed. Full-source review and role crosswalk remain pending. No badge or scoring integration. |

Each checkout has uncommitted changes on its own branch. Worktrees start at the same base;
they do not inherit the primary checkout's uncommitted documentation changes. Paths under
`tmp/` are ignored by the primary checkout but normal files within their individual worktrees.

## Deliberately excluded pending coordination

The table in the task is a proposed ownership split, not proof of semantic independence.
These items were not applied because the current instruction prioritises avoiding any effect
on the friend's active/queued features:

| Item | Reason for deferral |
|---|---|
| A5 configuration / Dependabot | Changes shared environment documentation and repository automation; defer until configuration ownership is confirmed. |
| A6 PDF parser / preview | Changes shared intake execution and preview behaviour while profile/UI changes are queued. A page-count check alone would not prove CPU/memory isolation. |
| A7 jobs filter / schedule | Runtime filtering affects openings and dependent cards; scheduling introduces external execution. No feeds or seed rows were refreshed. |
| A8 trend CI | Workflow controls live database publication and paid inference; no automation change or dispatch was made. |
| A9 encoder | Shared trend pipeline behaviour feeds snapshots under active freshness work. Cancellation requires mocked provider-contract tests in a separate coordinated change. |
| A10 Docker | Removal or boot changes affect alternative deployment and scripts; retained. |
| A11 privacy UI | A working translated route requires shared namespace registration, navigation/footer and review of provider/retention facts; shared UI/disclosure changes are queued. |
| A12 dead assets | Removing a globally loaded stylesheet requires a global import/layout change and visual verification; global CSS is queued work. |
| A13 matching evaluation | Production ranking and fixture interfaces can change under 2.2; no premature fairness evidence is generated. |
| A15 empty-data freshness | Metadata semantics depend on 1.1 and unavailable-data behaviour; leave shared attribution and callers unchanged. |

No B items or Phase 1-3 files were edited. Do not rebase a dirty checkout or merge these
packages automatically when another branch moves; inspect and preserve concurrent work first.

## Validation

- A1: five standard-library tests passed using local Python 3.15; this is not verification
  on the project's Python 3.11 runtime. Empty template produces no measured baseline.
- Documentation: all 106 local Markdown link targets in the eight submission-related
  documents resolved; external media-folder access and final exported files remain unverified.
- `git diff --check` passed.
- Full `dev.py check` attempted with database forced to loopback port 1 and providers disabled:
  i18n parity passed; lint, application pytest and contracts could not run without `.venv`;
  TypeScript failed because `node_modules` / `tsc` were absent. No setup/install was run.

## Decision-log handoff

The task explicitly defers `docs/decisions.md` (B4), overriding the usual requirement to
append material decisions immediately. Leave that shared file untouched. After coordination,
append entries with the next available IDs, without renumbering historical entries:

- Core documentation method: final-round evidence checklist separates verified source,
  storyboard, unmeasured targets and outstanding handbook fields; no runtime change.
- KPI method: manual stopwatch trials over matched synthetic cases, independent validity
  review, failures and valid-plan share alongside matched medians; no account-age proxy.
- MyCOL data preparation: partial edition-specific occupation-group reference kept outside
  runtime seeds pending full-source verification and a reviewed role crosswalk.

Suggested commit messages (after review, one per branch):

- `docs(submission): correct evidence declarations and deliverable links`
- `feat(core): add offline matched planning KPI calculator`
- `docs(matching): prepare isolated MyCOL reference for review`
