# Courses seed (F5, M3)

Written by `pipelines.pathway.run`; do not edit by hand. Rows are defined in
`src/api/app/features/pathway/catalogue_sources.py` (`CURATED`, `COURSERA`, `MANUAL`), which
live sync also uses.

- **Microsoft Learn** rows: title, URL and duration from the Microsoft Learn Catalog API on
  `verified_at`. Free; `hrd_claimable=false` (nothing to claim).
- **Coursera** rows: free to enrol; hours are the module-hour sums on the course page.
- **Manual** rows: paid, HRD Corp-claimable courses. `hrd_note` quotes what the provider's page
  says and `duration_note` states any assumption (e.g. hours per training day).
- `level` = the skill level (1-5) Adept estimates the course brings a learner to. It is an
  Adept judgment and the UI labels it as an estimate.
