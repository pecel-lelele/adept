# Selected synthetic demo CVs and complete intake profiles

These are the five CVs selected by the team for Adept's presentation and manual demos.
Each supplied PDF includes a fictional identity, professional summary, skills, work history,
project, education and an explicit synthetic-data notice. All employers, institutions,
qualifications and achievements are fictional. Contact addresses use `example.test`.

| Profile | Current role | Supplied CV |
|---|---|---|
| Imran Hakim | Compliance Analytics Officer | [PDF](cv_imran_hakim_compliance_analytics_officer.pdf) |
| Sofia Tan | Process Automation Analyst | [PDF](cv_sofia_tan_process_automation_analyst.pdf) |
| Meera Anand | Logistics Supervisor | [PDF](cv_meera_anand_logistics_supervisor.pdf) |
| Adrian Lim | Data Analyst | [PDF](cv_adrian_lim_data_analyst.pdf) |
| Nur Hana | Bank Operations Executive | [PDF](cv_nur_hana_bank_operations_executive.pdf) |

## Complete intake settings

The PDFs do not specify study time, training budget, HRD Corp status or learning preferences.
The following **editable synthetic demo assumptions** complete those intake fields. They are
not facts extracted from the CVs, real funding entitlements or measured skill assessments.
The same values and existing catalogue skill IDs are available in [profiles.json](profiles.json).
That file is a manual-demo reference, not an account-seeding script or automatic upload.

| Profile | Segment | Interests | Hours/week | Budget (MYR) | HRD eligible (demo) | Learning style |
|---|---|---|---:|---:|---|---|
| Imran | working | finance, risk, data, compliance | 6 | 500 | yes | mixed |
| Sofia | working | process improvement, operations, automation | 8 | 800 | yes | hands-on |
| Meera | switcher | operations, analytics, process improvement | 8 | 800 | yes | hands-on |
| Adrian | working | data, analytics, software | 10 | 300 | no | mixed |
| Nur Hana | working | finance, operations, process improvement | 6 | 500 | yes | mixed |

The starter skill levels in the JSON are all 2/5, chosen as conservative demo inputs for
human review. They are not proof of competence or a promise of a particular top-ranked role.
Change them during confirmation if the demonstration calls for a different synthetic case.
HRD eligibility alone does not establish that any course is funded.

## Run a demo

1. Download one PDF above. Create a synthetic account using its fictional `example.test`
   address and a password chosen for the session; no shared/demo password is published here.
2. Complete the questionnaire using the profile's settings above and upload the PDF.
3. Review the extracted catalogue skills and estimated levels. Approve only supported skills;
   leave unfamiliar phrases as review items unless choosing an existing catalogue equivalent.
4. Inspect dated radar signals, compare role matches and choose a target role. Generate and
   save a plan, then inspect cost, duration, unmet gaps, progress and relevant job openings.
5. To demonstrate organisation mode, create a separate synthetic manager/team account and
   explicitly join/share through its code. Personal plans remain separate from work plans.

## Parser observations

All five supplied PDFs were parsed locally with Adept's existing deterministic parser and
committed catalogue, with optional model calls disabled; none was truncated. These are
observed extraction results, not a new evaluation benchmark or a guaranteed future output.

| CV | Core catalogue matches observed | Wording left for review |
|---|---|---|
| Imran | Excel, SQL, data visualisation, responsible AI, AI literacy, risk/compliance | audit evidence; control testing |
| Sofia | RPA, Python, SQL, responsible AI, AI literacy, process mapping | workflow validation; exception handling |
| Meera | Excel, logistics planning, customer service, process mapping | inventory reconciliation; shift coordination |
| Adrian | Data visualisation, Excel, Python, SQL | data validation; reporting; stakeholder communication |
| Nur Hana | Excel, customer service, manual data entry, risk/compliance | document reconciliation; exception handling |

The current parser also proposes `bank-reconciliation` for Meera and Sofia from generic
reconciliation wording. Review and remove that banking-specific match for these cases;
it is omitted from their starter profiles. Nur Hana's parser result also includes
`bank-reconciliation` and `process-mapping`; the starter JSON keeps only the core skills
explicitly listed in that CV. The confirmation step is part of the demo, not a formality.

The older Aisyah, Wei Jie and Ravi CVs and edge-case PDFs under
[`tests/api/profile/fixtures/cvs/`](../../tests/api/profile/fixtures/cvs/) remain regression
fixtures. They are not the selected presentation CVs. Adding these demo documents does not
replace historical seed identities, change matching logic or create accounts in a database.
