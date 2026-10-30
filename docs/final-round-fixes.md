# Final-round issues: fixes and observed verification

Reviewed on **30 October 2026**. Final working branch: `fix/core-final-round-integration`,
based on freshly fetched `fix/core-review-regressions` at
`cb8bbf0f697e6b937aa46389ab0c18d545a15e96` plus the uncommitted changes described here.

The original worktree remains on `fix/react-version-mismatch`; its React edits and
existing ownership analysis were preserved. Work first started against `8cc9ed0`,
then was reconciled into a second isolated worktree when the requested review branch
advanced. The final results below describe the newer baseline only. No commit,
push, PR, merge into the shared branch, deployment or live model request was made.

| Problem | Implemented solution / review finding | Verification | Status |
|---|---|---|---|
| MyCOL CSV existed without a runtime reader | Matching reads the frozen source table through a separate exact role-ID crosswalk. Only stored `data-analyst` maps to MASCO 2524; all other roles remain unbadged pending detailed-title evidence. | API list/detail in both scenarios; unknown, display-label, case-mismatched and unsupported IDs receive no badge; before/after outputs prove ranking and scores are unchanged. | PASS |
| Badge lacked a UI and attribution contract | Add optional `CriticalOccupationBadge` with its own full RecommendationMeta, edition, source group/title and page locator. Render the badge and MetaBar in list/detail views with EN/MS/ZH limits. | Four explicit sources-everywhere cases require a non-null badge and the actual source/retrieval date. Production TSX rendering checks all locales and the source link. Generated OpenAPI/TypeScript stay in sync. | PASS |
| API image would omit the new reference reader's files | Add `COPY docs/reference docs/reference` to the existing API Dockerfile. | Packaging regression checks the COPY; existing Dockerfile source-path checks pass. An image build/start was not performed. | PASS for source packaging; runtime image unverified |
| PR #30's original fairness harness changed nonexistent Profile fields and imported production mocks | Review the published rewrite, retain it, and extend its synthetic-CV regression to both scenarios. The rewrite introspects real types and varies actual CV text through production extraction/ranking without patching production. Add separate real stored-name/segment invariance and skill-sensitivity tests. | 65 variants per scenario, 130 total, invariant. Existing negative control deliberately changes a name to catalogue skill wording and must be detected. Baseline skills and ranks must be nonempty. All relevant regressions pass in the full gate. | PASS for the scoped review |
| Technical declaration PDF lagged current services | Align source/export with RunPod MiniLM, RunPod GLM-5.3 plus separately authenticated Gemini failover, Replit, Google Fonts/Fontsource and the new MyCOL data usage. Re-export with a reusable script using the existing PDF dependency. | All eight final pages rendered and visually inspected; text checks confirm required services, actual-use disclosures and the human-KPI limit. | PASS; unsigned draft |
| ElevenLabs usage was uncertain | The user explicitly confirmed actual use. Retain it for presentation audio; preserve the newer branch's recorded stock-voice detail. Do not claim it runs career recommendations. | Session confirmation plus reviewed declaration and PDF wording. Exact synthesis model remains unrecorded. | PASS for disclosure |
| All human KPI records are not_run | User confirmed no human trials exist. Preserve the human template, run its calculator, record 0 attempted human trials, 0 valid pairs and null baseline/reduction. Update active submission sources with the dated status and separate automated evidence. | Calculator output is committed as evidence; no human results or speed-up were fabricated. | PARTIAL: human study still requires participants |
| No recorded synthetic API journeys | Measure the five selected demo PDFs three times each through real CV upload, questionnaire, reviewed fixture confirmation, radar, matching and plan saving, using signed synthetic sessions and isolated memory/CSV storage. | 15/15 final journeys complete; catalogue IDs, basic plan structure and source metadata checked. Detailed step records and hashes retained. | PASS for automated local timing only |
| Decisions log needed to explain the cross-feature changes | Add TEAM-037 at the bottom of the Team section, preserving all newer branch entries and their IDs. | Existing ID scheme, source dates, limitations and branch recorded; diff whitespace check passes. | PASS |

## MyCOL evidence and exact matching boundary

The source is TalentCorp's [official MyCOL 2024/2025 publication](https://www.talentcorp.com.my/resources/publications/mymahir-malaysia-critical-occupations-list-mycol20242025/).
The downloaded report's printed page **272** (PDF page **137**) explicitly names
**Data Analyst** in the restricted list under **2524, Data Professionals**; printed
page 273 (PDF 138) repeats the nomination. Both spreads were rendered and inspected.
The 66-row Table 7 reference and its original checksum were retained.

The runtime join is `stored role ID -> reviewed crosswalk -> source MASCO row`.
It does not compare labels, search text, call a model, infer all roles in a broad
group, add a score bonus or reorder results. A missing stored role never enters
matching's scored-role output. The badge itself describes historical list inclusion,
so its `is_estimate` is false; its frozen reference snapshot/retrieval date is
**2026-10-29 UTC**, distinct from the selected trend snapshot and today's date.
Its source link opens the verified report page. This does not establish a current vacancy.

Relevant files: [crosswalk](reference/critical-occupation-roles.csv),
[source evidence](reference/critical-occupations.md),
[runtime reader](../src/api/app/features/matching/critical_occupations.py),
[API tests](../tests/api/matching/test_critical_occupations.py),
[source sweep](../tests/api/guardrails/test_sources_everywhere.py),
[rendered badge test](../tests/web-mycol.test.ts).

## Fairness rewrite review

The rewrite was initially absent at the first fetched tip, but is present in the
final `cb8bbf0` baseline. This review uses that published rewrite rather than replacing
it with a parallel implementation. It removes `unittest.mock` from the offline production
module and removes invented age/gender/background fields on Profile.

The evaluation now varies five real synthetic CV texts: alternate synthetic names,
titles, pronouns, gender wording, stated age and a combined change. It uses production
PDF extraction, production `extract_cv`, production role loading and `rank_roles`.
The snapshot is fetched once per scenario, so variants share the same trend values.
Nonempty baseline assertions and the deliberately failing skill-wording control
make this substantially stronger than the original harness mechanics tests.

Limits: CV variants are a finite synthetic sample. Direct ranking in the harness
holds interests empty and does not exercise every saved-profile/enrichment path.
The declared profile-field whitelist is partly an explicit maintenance assertion,
not complete runtime data-flow analysis. New boundary tests cover real saved names,
segments and skill input sensitivity. This does not establish universal fairness,
equal employment outcomes or coverage of every identity/background proxy.

Observed reports: [moderate](fairness-review-moderate.json) and
[fast](fairness-review-fast.json), **65 cases each; all invariant**. They log variant
labels and outcomes without retaining CV text. Human fairness/outcome research remains separate.

## Measured synthetic journey results

Measured at **2026-10-30T06:39:12.709799+00:00**; **5 personas, 15 API journeys, 0 human testers/trials**.

| Persona | Completed | CV upload seconds | Radar seconds | Match seconds | Saved pathway seconds | Total median seconds | Total min-max seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| imran | 3/3 | 0.019 | 0.012 | 0.053 | 0.019 | 0.151 | 0.109-2.270 |
| sofia | 3/3 | 0.015 | 0.010 | 0.039 | 0.014 | 0.093 | 0.091-0.101 |
| meera | 3/3 | 0.013 | 0.010 | 0.039 | 0.015 | 0.091 | 0.090-0.136 |
| adrian | 3/3 | 0.014 | 0.010 | 0.168 | 0.025 | 0.236 | 0.121-0.297 |
| nur-hana | 3/3 | 0.027 | 0.011 | 0.053 | 0.018 | 0.127 | 0.119-0.155 |

Each cell is a median of three final runs; medians of steps need not sum to the
median total. Totals also include questionnaire submission, scripted confirmation,
client setup and automatic checks. The first journey has cold process caches;
later journeys share caches. These timings exclude browser rendering, network
transit, human thinking/corrections and independent plan-validity review.

Targets are selected automatically from the first ranked stored role ID. Skill
confirmation uses the documented reviewed synthetic fixtures, with no invented
skills or real CVs. Checks confirm catalogue membership, source metadata and basic
step/week structure; this is not a substitute for the protocol's independent reviewer.
Unmet skills and warnings are retained in the [raw final measurements](kpi-automated-journeys.json).

The [initial raw-ID run](kpi-automated-initial-raw-id-attempts.json), from the earlier
baseline, is retained separately: 10/15 completed and five uploads received 429.
The timing harness originally used raw test IDs, which the actual limiter treats
as anonymous traffic. Final runs use normal signed synthetic sessions, with the
limiter still enabled. Do not pool these different runs or omit the initial failures.

The [human calculator output](kpi-human-summary.json) correctly has 0 attempted
human trials, 0 valid pairs and null medians/reduction. The [template](kpi-trials-template.json)
remains unrun because the user confirmed there were no human trials. Active
submission sources label 20% as a proposed target only; no achieved reduction is
quoted. The existing preliminary PDF also labels its older numeric objectives as
targets, not measured outcomes. It has not been re-exported as a final-round submission.

## Validation and practical limits

| Check | Observed final result |
|---|---|
| Full production quality gate through src/scripts/dev.py check | PASS: Ruff, formatting, ESLint, translation parity, tests, TypeScript and generated contract drift |
| Python suite within that gate | **1,435 passed, 34 skipped, 54 subtests passed**; one existing FastAPI/Starlette TestClient deprecation warning |
| Frontend suite within that gate | **78 passed, 0 failed, 0 skipped** |
| Extra frontend run using the CI-style web/static selection | 74 passed; a separate subset run, not added to the 78 |
| Standalone production frontend build | PASS: compiled, typechecked, generated 51 static pages and prepared standalone output |
| Fairness reports | PASS: 130/130 synthetic CV cases invariant across both scenarios |
| Final automated API journeys | PASS: 15/15 completed |
| Human planning-time reduction KPI | NOT MEASURED: 0 testers, 0 trials, no manual baseline |
| Final technical PDF | PASS: 8 pages exported, text checked and all pages rendered for visual review |
| Docker image, live Replit, paid inference, production database | Not run; no production verification claimed |

The 34 skips remain skips, including opt-in/environment-dependent checks. Initial
sandbox attempts failed on Windows parser/subprocess/temp-directory permissions,
npm cache access and SWC's native cache. Approved retries passed. The temporary
standalone fairness launcher also initially lacked a Windows multiprocessing main
guard; that launcher was corrected and its final reports completed successfully.
No application assertion, guardrail or rate limit was weakened to obtain these results.

Commands and isolation:

- Full gate used an ignored wrapper that delegates to `src/scripts/dev.py` and points
  it at the existing root virtualenv, since isolated worktrees have no `.venv` of their own.
  It selected CSV storage, an unavailable loopback test database, disabled paid providers,
  removed database test opt-ins and used an owned temporary directory.
- Frontend build: `node src/web/scripts/build.mjs`.
- Reproduce scripted measurements in a fresh process:
  `python src/scripts/measure_synthetic_journeys.py --run-local-isolated`.
- Human calculator: `python src/scripts/kpi_time_to_plan.py docs/kpi-trials-template.json`.
- Re-export the unsigned declaration:
  `python src/scripts/export_technical_declaration.py`.

Local command logs are under the final worktree's ignored `tmp/` directory.
All task-owned commands have finished; no listening server or Docker container
was created. The earlier working copy remains as a preserved intermediate, while
`tmp/final-round-integration` is the final reviewable worktree.

Suggested commit: `fix(core): ground MyCOL badges and refresh submission evidence`.
Commit: not created. Push: not performed. PR: not opened.
