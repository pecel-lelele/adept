# Taxonomy seed (F4, M2)

48 role profiles covering 41 distinct official occupations, and 142 skills, read by the shared reference loader and matching/pathway services.
`provenance.json` records the official O*NET occupation code, source URL, stored title and
retrieval date for every role. All displayed labels are official occupation titles. The 2026-10-31 verification pass opened
the 26 distinct O*NET pages behind the older editorial labels and replaced those labels with
their official occupation titles. Stable IDs and estimated requirement profiles are retained;
former labels exist only as `legacy_label` history in provenance. Several profiles map to the
same official occupation: 48 stored profiles must not be reported as 48 distinct occupations.
No title is an independently verified growth forecast.

The 2026-10-30 release adds nine current occupations (`is_target=false`): bookkeeping clerks,
secretaries, registered nurses, retail supervisors, shipping clerks, teaching assistants,
accountants, tellers and team assemblers. Their `O*NET-SOC` labels are the official titles.
Each occupation page was opened on 2026-10-30. Retail salespersons, customer service
representatives and the production-worker aggregate from the preceding release are retained.

`role_skills.csv` maps tasks, software and knowledge on the cited pages to existing skill IDs.
The manifest's `requirements_basis` explains the new mappings. **Levels and importance are
Adept estimates**, not O*NET ratings, a complete qualification framework or professional
licensure. Retail and customer-service roles now have baseline requirements. O*NET supplies
no detailed requirements for `Production Workers, All Other` (51-9199.00), so that aggregate
deliberately has no inferred skills; the separately sourced Team Assemblers (51-2092.00)
provides production-line coverage. No current occupation is added to future-role ranking.

Pipeline: official occupation pages → preserve IDs/titles and validate references → curated
role-skill edges with estimated levels/importance → existing matching and pathway methods →
graph, current-role exclusion and missing-trend regressions → reference seeds/API.

The same release adds five official tech target roles: Web Developers, Database Administrators,
Network and Computer Systems Administrators, Software Quality Assurance Analysts and Testers,
and Business Intelligence Analysts. These are learner-selectable directions, not growth claims.
Git and Selenium are added using the exact software names in O*NET technology lists, with
digital aliases. Existing digital skills (SQL, Python, cloud, security and visualisation) are
reused. No fresh trend signals are invented for the new skills; absent course coverage
(e.g. Selenium) remains an explicit unmet gap. All new tech role links are digital skills.

Synthetic benchmark annotation update: Business Intelligence Analysts is relevant to Aisyah
(data/finance interests, spreadsheet and process work) and Ravi (analytics interest and
spreadsheet/logistics reporting). It replaces their weaker third direction in the three-label
benchmark; Aisyah retains Business Analyst, while Ravi retains Data Analyst and Supply Chain
Analyst. These are curated fixture judgments, not human study outcomes. The ranking formula
and evaluation thresholds are unchanged.


## Digital and green focus (2026-10-31, issue #84)

The 33 target profiles now exclude the eight soft/clinical skill categories specified
in M3-042: 16 edges removed across 13 profiles. Surviving relative importance estimates
are retained; scoring normalizes by the remaining sum. All eight skill records remain
for intake/CV aliases, job reference data, SDG links and current-role requirements.
`provenance.json` records removed pairs, original values and the digital-health decision.
The digital-health nursing profile remains a focus for qualified nurses with healthcare
informatics and AI literacy only; it does not establish clinical or professional readiness.
An append-only exact-pair migration removes the old edges in existing databases;
reference upserts alone cannot delete them. Current-role clinical requirements remain.
See the [before/after report](../../../../docs/evidence/skill-bank-coverage.md) for every target profile.
