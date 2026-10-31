# Digital and green skill-bank coverage (issue #84)

Provider pages opened: **2026-10-31**. Before: **19/33 target profiles** had at least one requirement with no course (**24 distinct skills**). After: **2/33** have a course-presence gap (`business-analyst` and `digital-health-nurse`, whose restored soft/clinical requirements have no course and stay `no_catalogue_course` by design, M3-045); **0** digital/green skills remain `no_catalogue_course`. The catalogue grows from **104 to 120** entries.

## Measurement

For each target role, uncovered share = sum of importance for requirements absent from every course / sum of importance for all requirements. The `src/scripts/course_coverage.py` script reads the CSV graph and uses production skill canonicalization (Excel/RPA aliases); it excludes current roles and does not change the data. Course presence is distinct from required-level attainment, prerequisites, budget, availability after login, or certificate entitlement. Existing pathway logic still reports those limitations.

Run `uv run --frozen python src/scripts/course_coverage.py --out REPORT.json`. The original and updated JSON evidence are `.claude/jobs/out/07-skill-bank.before.json` and `07-skill-bank.after.json` (local job artifacts).

## Per-target-role coverage

Percentages below are the **importance-weighted uncovered share**, not the covered share. Stable IDs identify profiles that can share an official occupation.

| Role profile ID | Before uncovered weight / total | Before uncovered | After uncovered | Originally uncovered skills |
|---|---:|---:|---:|---|
| `data-analyst` | 0 / 3.1 | 0.00% | 0.00% | none |
| `ai-operations-specialist` | 0 / 4.4 | 0.00% | 0.00% | none |
| `process-automation-analyst` | 0 / 3.6 | 0.00% | 0.00% | none |
| `compliance-analytics-officer` | 0 / 3.4 | 0.00% | 0.00% | none |
| `machine-learning-engineer` | 0 / 5.8 | 0.00% | 0.00% | none |
| `data-engineer` | 1 / 4.5 | 22.22% | 0.00% | sql-advanced |
| `cloud-solutions-architect` | 1.9 / 3.5 | 54.29% | 0.00% | cloud-ai-services, enterprise-architecture, stakeholder-management |
| `cybersecurity-analyst` | 1 / 3.8 | 26.32% | 0.00% | critical-thinking, security-ai |
| `ai-product-manager` | 1.8 / 4.9 | 36.73% | 0.00% | ai-product-management, stakeholder-management |
| `ux-designer` | 0.4 / 2.7 | 14.81% | 0.00% | stakeholder-management |
| `digital-marketing-specialist` | 0 / 3.2 | 0.00% | 0.00% | none |
| `business-analyst` | 0.6 / 3.6 | 16.67% | 16.67% (restored, M3-045) | stakeholder-management |
| `solar-pv-engineer` | 0 / 2.4 | 0.00% | 0.00% | none |
| `energy-manager` | 0.5 / 2.9 | 17.24% | 0.00% | stakeholder-management |
| `esg-sustainability-analyst` | 1 / 3.4 | 29.41% | 0.00% | regulatory-affairs, stakeholder-management |
| `smart-manufacturing-engineer` | 0 / 3.8 | 0.00% | 0.00% | none |
| `semiconductor-process-engineer` | 0 / 3.4 | 0.00% | 0.00% | none |
| `supply-chain-analyst` | 0 / 3.8 | 0.00% | 0.00% | none |
| `precision-agriculture-specialist` | 1.4 / 2.6 | 53.85% | 0.00% | climate-ai, precision-agriculture |
| `health-informatics-specialist` | 0 / 3.4 | 0.00% | 0.00% | none |
| `digital-health-nurse` | 2.3 / 3.3 | 69.70% | 69.70% (restored, M3-045) | clinical-judgement, cross-cultural-communication, patient-care |
| `learning-experience-designer` | 1.2 / 3.2 | 37.50% | 0.00% | coaching-mentoring, learning-development |
| `tvet-digital-skills-trainer` | 0.9 / 3.1 | 29.03% | 0.00% | coaching-mentoring, public-speaking |
| `customer-success-specialist` | 0.5 / 3.2 | 15.62% | 0.00% | stakeholder-management |
| `islamic-finance-analyst` | 1.4 / 3.4 | 41.18% | 0.00% | financial-analysis, fintech-ai |
| `people-analytics-specialist` | 1.9 / 3.6 | 52.78% | 0.00% | bias-auditing, change-management, workforce-planning |
| `hospitality-experience-manager` | 0.6 / 3.2 | 18.75% | 0.00% | cross-cultural-communication |
| `responsible-ai-officer` | 2.5 / 5 | 50.00% | 0.00% | ai-safety, bias-auditing, explainable-ai, regulatory-affairs |
| `web-developers` | 0 / 3.5 | 0.00% | 0.00% | none |
| `database-administrators` | 0.8 / 3.6 | 22.22% | 0.00% | sql-advanced |
| `network-systems-administrators` | 0 / 3.3 | 0.00% | 0.00% | none |
| `software-quality-assurance-testers` | 1 / 3.6 | 27.78% | 0.00% | selenium |
| `business-intelligence-analysts` | 0 / 4.1 | 0.00% | 0.00% | none |

## Target requirements and retention

Remove 16 requirement edges across 13 target profiles for stakeholder management, coaching/mentoring, public speaking, cross-cultural communication, critical thinking, organisational change, patient care and clinical judgement. Keep all eight skill records: canonical intake/CV aliases, job/certification reference data and SDG mappings still use them; clinical and coaching skills also remain in current-role requirements. `taxonomy/provenance.json` records the exact removed edges and original weights.

Surviving importance values remain positive and at most one. Their relative priorities remain unchanged; matching and role-trend calculations normalize by the surviving total, and pathway priorities use relative importance. Renormalizing the stored weights would add no information. No role loses all requirements.

**digital-health-nurse stays a target focus for already qualified nurses.** Its requirements are healthcare informatics (level 2, importance 0.6) and AI literacy (level 2, importance 0.4), plus the clinical prerequisites restored in M3-045 (patient care, clinical judgement, cross-cultural communication) so a non-nurse is not shown as qualified. This is a credible digital-health upskilling direction, not a nursing conversion or clinical qualification. The official Registered Nurses occupation crosswalk is retained. Current `registered-nurses` still includes patient care and clinical judgement.

## Added courses

All rows use the existing self-paced, English, `hrd_claimable=false`, `currency=MYR`, `cost_myr=0` convention for free learning. No currency conversion or paid certificate entitlement is inferred. Levels are Adept estimates, not provider credentials. Azure resource/licence charges can be separate.

| Exact course title (provider page) | Provider | Hours | Estimated skill level | Opened / verified | Skill |
|---|---|---:|---:|---|---|
| [Integrate AI services to enrich your applications with intelligent features in Azure Database for PostgreSQL](https://learn.microsoft.com/en-us/training/modules/integrate-ai-services-enrich-azure-database-postgresql/) | Microsoft Learn | 1.2 | 3 | 2026-10-31 | cloud-ai-services |
| [AZ-305: Design infrastructure solutions](https://learn.microsoft.com/en-us/training/paths/design-infranstructure-solutions/) | Microsoft Learn | 3.6 | 3 | 2026-10-31 | enterprise-architecture |
| [Evaluate generative AI applications](https://learn.microsoft.com/en-us/training/paths/evaluate-generative-ai-apps/) | Microsoft Learn | 1.6 | 2 | 2026-10-31 | ai-safety |
| [Enhance security operations by using Microsoft Security Copilot](https://learn.microsoft.com/en-us/training/paths/security-copilot-and-ai/) | Microsoft Learn | 6.2 | 2 | 2026-10-31 | security-ai |
| [Transform your business with AI](https://learn.microsoft.com/en-us/training/paths/transform-your-business-with-microsoft-ai/) | Microsoft Learn | 2.6 | 2 | 2026-10-31 | ai-product-management |
| [Design responsible AI security, governance, risk management, and compliance](https://learn.microsoft.com/en-us/training/modules/design-responsible-ai-security-governance-risk-management-compliance/) | Microsoft Learn | 0.9 | 3 | 2026-10-31 | regulatory-affairs |
| [21st century learning design](https://learn.microsoft.com/en-us/training/paths/21st-century-learning-design/) | Microsoft Learn | 6.7 | 2 | 2026-10-31 | learning-development |
| [Optimize staffing with workforce management in Dynamics 365 Contact Center](https://learn.microsoft.com/en-us/training/modules/optimize-staffing-workforce-management-contact-center/) | Microsoft Learn | 0.7 | 2 | 2026-10-31 | workforce-planning |
| [Advanced SQL](https://www.kaggle.com/learn/advanced-sql/course) | Kaggle Learn | 4 | 3 | 2026-10-31 | sql-advanced |
| [Machine Learning Explainability](https://www.kaggle.com/learn/machine-learning-explainability/course) | Kaggle Learn | 4 | 3 | 2026-10-31 | explainable-ai |
| [Intro to AI Ethics](https://www.kaggle.com/learn/intro-to-ai-ethics/course) | Kaggle Learn | 4 | 2 | 2026-10-31 | bias-auditing |
| [AI in Finance Masterclass](https://courses.cfte.education/online-artificial-intelligence-in-finance-masterclass-learn-ai-for-free/) | CFTE | 0.8 | 1 | 2026-10-31 | fintech-ai |
| [Financial Modelling for Energy Transitions MINFin, FinTrack & FinCoRE](https://www.open.edu/openlearncreate/course/view.php?id=17735) | OpenLearn Create (Climate Compatible Growth) | 15 | 3 | 2026-10-31 | financial-analysis |
| [Precision Farming ? Basics](https://28digital.ea.education/courses/precision-farming-basics/) | 28DIGITAL (Agri-Digital Growth consortium) | 48 | 2 | 2026-10-31 | precision-agriculture |
| [Machine Learning for Earth Systems Modelling - Course 3](https://learning.ecmwf.int/course/view.php?id=100) | ECMWF | 24 | 3 | 2026-10-31 | climate-ai |
| [Use Selenium to Create a Web Scraping Bot](https://www.freecodecamp.org/news/use-selenium-to-create-a-web-scraping-bot/) | freeCodeCamp | 3 | 2 | 2026-10-31 | selenium |

## Evidence and limits

Exact provider facts, source URLs, access notes, duration evidence and mapping rationale are in [skill_bank_provenance.json](../../src/data/seed/courses/skill_bank_provenance.json). Microsoft durations came from its Catalog API, retrieved on the same date as the opened course pages. New entries are frozen in the existing `FREE_DIGITAL` source group, so a later sync date cannot refresh manual verification dates.

Kaggle URLs were opened, but their live HTML is a JavaScript shell; metadata was available in the indexed official course pages. Authenticated exercises were not inspected. ECMWF course 3 redirects to login; its public provider catalogue supplies the title, free price, prerequisites and 16?24-hour estimate. The course is stored with 24 hours as a disclosed upper-bound planning estimate. Precision Farming uses 48 hours as the disclosed upper bound of the provider's 20?48-hour range; both its EIT Campus and 28DIGITAL pages were opened. CFTE specifies about 45 minutes in its FAQ (rounded to 0.8 hours), despite a broader ?under 2 hours? hero.

The freeCodeCamp Selenium course was published in 2021; its provider page lists three hours of video. It offers browser-automation foundations at estimated level 2, so the role's level-3 gap remains `catalogue_tops_out`. The finance masterclass is introductory level 1 and leaves higher proficiency unmet. Financial modelling is taught through energy-transition cashflow tools, not Islamic finance certification. Regulatory/policy coverage is technical AI compliance, not Malaysian legal qualification. The educator learning-design path covers digital learning design, not an entire corporate L&D qualification. These scope limits are also stored in course notes.

The inactive FutureLearn agriculture course and the TAU Selenium page without established duration were not added. No course was invented to close a gap.

## Serving and rollout

CSV fallback uses the revised requirements immediately. PostgreSQL reference upserts do not remove old edges, so the append-only migration `20261031130000_pathway_digital_skill_focus.sql` deletes only the 16 exact removed pairs. Its rollback restores their original estimated values without overwriting later edits. Apply migrations and seed reference data only to an explicitly selected authorized database; this job did not touch an ambient database. Course source definitions and generated CSV share the existing pipeline/live-sync path. No API contract or environment setting changed.

## Verification

- `uv run --frozen python .claude/toolbox/seed_integrity.py`: **seed integrity OK**.
- `uv run --frozen ruff check src tests`: **all checks passed**; `ruff format --check src tests`: **360 files already formatted**.
- Targeted `uv run --frozen pytest tests/api/pathway tests/pipelines/pathway tests/api/matching tests/pipelines/matching tests/api/guardrails/test_sources_everywhere.py -p no:cacheprovider -k 'not test_main_writes_the_seed and not test_committed_provider_facts_match_shared_sync_definitions'`: **335 passed, 21 skipped, 2 deselected**, one existing Starlette deprecation warning (31.07 seconds). The 21 skips are explicit PostgreSQL/opt-in checks; the new temporary-table migration up/down/re-up regression is among them.
- All four new `test_skill_bank_focus.py` regressions failed against the original seeds and pass against the revised graph: digital scope/intake retention, complete course presence with residual level gaps, dated provider evidence reaching the catalogue API, Selenium selection plus a genuinely empty-catalogue fallback. The existing missing-signal regression now expects `catalogue_tops_out` for Selenium, rather than incorrectly claiming there is no course.
- The two deselected CSV-generation tests encountered **WinError 5** creating/reading pytest temporary directories (the same limitation reproduced under both workspace and configured temp roots). Their production flows were checked directly using ordinary output files in `.claude/jobs/out`: `pipelines.pathway.run.main` produced **120** valid courses from the saved API fixture, and `catalogue_sources.write_csv` matched **all fields of 63** hand-verified committed records. No assertions were removed; the runner must run the two tests normally outside the sandbox.
- `git diff --check`: **passed**. The final status contains only the 16 intended tracked/untracked source, seed, migration, test and documentation paths. Toolbox/playbook registration and job outputs are ignored local artifacts by repository convention.
- No API contract, dependency, environment variable, UI or runtime configuration changed; contract regeneration and UI screenshots are not applicable. No private dotenv, paid model, shared database, Docker container or production resource was used.
- **Full quality gate remains pending with the job runner**, including Node workers and disposable PostgreSQL migration/seed verification. This worker did not run or claim a successful full gate. Database rollout and rollback were not exercised locally because no explicit disposable database was selected.
- Existing checkout HEAD: `942db458b8b72ed9268a2eaceecfbd728b57143d`. **No new commit SHA**: Git is runner-owned and `.git` is read-only. Branch remains `feat/pathway-skill-bank-focus`; no Git mutation was attempted. Commit message is saved at `.claude/jobs/out/07-skill-bank.commit.txt` with `Fixes #84` and the required co-author line.

## Proof of done (feature-change playbook)

- [ ] Full gate `uv run --no-project python src/scripts/dev.py check` passes: **runner pending**. Local evidence is 335 passed / 21 skipped / 2 fixture-blocked tests deselected; Ruff and seed integrity passed.
- [x] Changed tests named and failing-then-passing: four `test_skill_bank_focus.py` regressions failed before implementation and passed after; Selenium/provenance regressions and the optional PostgreSQL migration regression are included above.
- [x] UI screenshot/rendered text: **not applicable**, data/source change with catalogue API assertions.
- [x] Intended status and commit evidence: 16 intended paths, diff whitespace check passed; no worker commit permitted. Existing HEAD and runner-owned branch are recorded above; commit message prepared.
- [x] Reusable script committed: `src/scripts/course_coverage.py`.

## Update (M3-045)

Four edges were restored after review (business-analyst stakeholder-management; digital-health-nurse patient-care, clinical-judgement, cross-cultural-communication). They have no catalogue course and are reported as uncovered, so the audit now shows **2/33** target profiles with an uncovered requirement (business-analyst and digital-health-nurse) instead of 0/33. Rerun with `uv run --frozen python src/scripts/course_coverage.py --out REPORT.json`.
