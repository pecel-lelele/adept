# Isolated offline follow-up: A1 and A14

This follow-up closes only two remaining delivery gaps. Previously implemented fixes were
not repeated. No app/runtime/scoring file, workflow, dependency manifest, shared locale,
README, environment example, migration, session file or forbidden contract was edited.

## A1: current-tree delivery

New files:

- `src/scripts/kpi_time_to_plan.py`
- `tests/scripts/test_kpi_time_to_plan.py`
- `docs/kpi-time-to-plan.md`
- `docs/kpi-trials-template.json`

The earlier offline calculator was brought into this working tree without changing its
method, interface or formulas. Ruff formatting was applied only to new files. Its test
first failed with the missing current-tree module, then all five tests passed on Python 3.11.
The original checkout was left intact. No account-age SQL proxy or production telemetry
was added. Human stopwatch measurements and the 20% target remain unverified.

## A14: verified reference data

New files:

- `docs/reference/critical-occupations.csv`
- `docs/reference/critical-occupations.provenance.json`
- `docs/reference/critical-occupations.md`
- `tests/reference/test_critical_occupations.py`

The complete official TalentCorp PDF was downloaded for read-only review. Because it is
scanned, Table 7 was visually inspected on printed pages 85-87 (PDF pages 44-45). All 66
occupation groups, codes and labels were transcribed with page-level provenance. PDF/CSV
checksums identify the reviewed versions. Exact publication date remains unknown; actual
retrieval is recorded separately, in UTC and with the MYT interpretation documented.

The two tests first failed for missing CSV/provenance files, then passed. They cover schema,
row control, unique codes, page locators, representative labels and provenance/hash consistency.
No test fetches a source. Data is outside runtime seeds and has no role-ID crosswalk,
badge integration, model, score or user-facing recommendation output.

No additional library was installed. The CSV is a plain repository reference file and was
validated with Python's standard library; workbook authoring runtime/helper tools were not
available. Source images/PDF were reviewed locally and remain in ignored temporary storage.

## Verification

- New targeted tests: **7 passed**, including 6 unittest subtests.
- Full suite: **1020 passed, 32 skipped, 54 subtests passed**, one existing Starlette warning,
  in 76.22 seconds. Prior result was 1013 passed/32 skipped/48 subtests.
- Ruff lint/format, ESLint, TypeScript and i18n parity passed.
- Contract generation into temporary files matched both tracked artifacts; no tracked
  contract was overwritten.
- KPI CLI accepts the delivered empty template, reports zero attempts and null baselines.
- `git diff --check` passed. Existing tracked diffs retained their earlier statistics.

The same 32 PostgreSQL-dependent tests remain skipped. No live DB/model/feed/workflow,
deployment, commit, branch operation, push or PR was used. Git commands were read-only.
The only pre-existing file edited was the explicitly requested status document
`docs/daftar-perbaikan-aman.md`, by appending sections 21-24. Earlier modified/untracked
work, including `.qoder/`, prior manifests and the earlier test report, was not edited.

## Remaining items intentionally excluded

- A7 scheduling/live refresh can cause external execution and data changes after activation.
- README/`.env.example`, freshness contracts/services, scoring and shared i18n remain reserved.
- Docker remains a read-only investigation under the prior instruction.
- Real KPI measurement needs testers; rubric names, final asset credits and privacy controller
  details need verified team information. Matching fairness evidence waits for scoring changes.
- `docs/decisions.md` remains untouched under the explicit shared-file restriction; data
  provenance/method are recorded in the adjacent reference document for later coordination.

Suggested separate human commits:

- `chore(core): deliver offline planning KPI tools in current tree`
- `docs(matching): curate verified MyCOL reference table`

Stage only the corresponding new file lists above. The common status-document update may
be staged with the handoff documentation after review. No automatic staging was performed.
