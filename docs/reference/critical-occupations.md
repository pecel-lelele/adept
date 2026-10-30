# MyCOL 2024/2025 reference table

This is a manually curated copy of the **66 occupation groups in Table 7** of TalentCorp's
MyMahir Malaysia Critical Occupations List 2024/2025. Matching reads this frozen reference for a historical badge, using the explicit
[stored role-ID crosswalk](critical-occupation-roles.csv). It never changes scores.

- Data: [CSV](critical-occupations.csv).
- Provenance and hashes: [source record](critical-occupations.provenance.json).
- Official [publication page](https://www.talentcorp.com.my/resources/publications/mymahir-malaysia-critical-occupations-list-mycol20242025/).
- Official [report PDF](https://www.talentcorp.com.my/images/uploads/publication/204/MyMahir-Malaysia-Critical-Occupations-List-MyCOL20242025-1773385490.pdf).

The full source PDF was downloaded and its Table 7 inspected visually. The source is scanned,
so a text-only extraction is insufficient. Table 7 spans printed pages **85-87**, corresponding
to PDF pages **44-45** (each PDF page contains a two-page spread). Line breaks in labels were
joined with spaces; labels and MASCO 4D codes otherwise follow the table.

The actual download was **2026-10-29 17:49:55 UTC**, or **30 October 2026 MYT**. CSV
`retrieved_at` uses the UTC calendar date. This is not the publication date, a new edition,
or proof of current vacancies. The exact publication date is unverified and remains null
in the provenance record rather than being inferred from the filename or download time.

## Schema

| Column | Meaning |
|---|---|
| `row_no` | Source Table 7 row, 1 through 66 |
| `masco4d` | Four-character MASCO group identifier; treat as text |
| `occupation_label` | Source occupation-group description |
| `edition` | Source edition, `2024/2025` |
| `source_id` | Key into the adjacent provenance record |
| `source_page` | Printed source page |
| `pdf_page` | One-based PDF page containing the spread |
| `retrieved_at` | Actual UTC retrieval date |

## Limits and future use

These are occupation groups, not a role-ID crosswalk or a list of all included detailed
job titles. The report's occupation profiles further restrict included titles. Do not
automatically badge every Adept role under a broad group or infer a forecast, vacancy,
salary or hiring decision from inclusion. The mapping adds no scoring integration.

This supersedes the earlier nine-label preparation as the reference deliverable. The
earlier checkout was left untouched. Public access does not establish an open-data licence;
source attribution and applicable publication terms must be retained on redistribution.

Pipeline: **official PDF -> inspect Table 7 spreads -> transcribe codes/labels and page
locators -> reference CSV, without ranking -> offline schema, uniqueness, row-count,
anchor-label and provenance/hash tests -> documentation reference only**.

Validate locally with:

```powershell
.venv\Scripts\python.exe -m pytest tests/reference/test_critical_occupations.py
```

The tests do not fetch the source or call Adept services. The source PDF SHA-256 records
the reviewed version; a later source replacement requires reinspection, not a silent refresh.

## Reviewed role mapping (30 October 2026)

Only `data-analyst` is mapped to MASCO **2524, Data Professionals**. The official
report's printed page **272** (PDF page **137**) explicitly includes **Data Analyst**
in its restricted title list; printed page 273 (PDF 138) repeats the nomination.
Both spreads were rendered and visually checked against the saved source checksum.
No other role has been inferred from a broad group, label similarity or a model.

The badge exposes its own RecommendationMeta, edition, group, title and page locator.
Its snapshot date is the frozen reference's UTC retrieval date, 2026-10-29, not
the request date or the separate trend snapshot date. `is_estimate=false` describes
historical list inclusion, not a forecast. This is not evidence of a current vacancy.
Deployment must include `docs/reference/critical-occupation*.csv` and the provenance JSON.
The frozen reference files are loaded and indexed once per worker process. Restart
workers after publishing a new reference release. Each lookup still creates its own
scenario-specific badge and source metadata; profiles, scores and the live role
catalogue are not part of this cache.

Badge pipeline: official PDF -> reviewed restricted title and Table 7 group -> exact
existing role-ID crosswalk -> metadata-only badge -> positive/negative API and source
regressions -> matching list/detail cards. New mappings require source-profile review.
