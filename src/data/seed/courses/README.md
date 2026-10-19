# Courses seed (F5, M3)

Written by `pipelines.pathway.run`; do not edit by hand (edit `CURATED` / `MANUAL` there).

- **Microsoft Learn** rows: title, URL and duration from the Microsoft Learn Catalog API on
  `verified_at`. Free; `hrd_claimable=false` (nothing to claim).
- **Manual** rows: paid, HRD Corp-claimable courses. `hrd_note` quotes what the provider's page
  says and `duration_note` states any assumption (e.g. hours per training day).
- `level` = the skill level (1-5) Adept estimates the course brings a learner to. It is an
  Adept judgment and the UI labels it as an estimate.
