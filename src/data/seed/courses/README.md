# Courses seed (F5, M3)

Written by `pipelines.pathway.run`; do not edit by hand. Rows are defined in
`src/api/app/features/pathway/catalogue_sources.py` (`CURATED`, `COURSERA`, `MANUAL`, `FREE_DIGITAL`, `FREE_MS`, `BUNDLES`), which
live sync also uses.

- **Microsoft Learn** rows: title, URL and duration from the Microsoft Learn Catalog API on
  `verified_at`. Free; `hrd_claimable=false` (nothing to claim).
- **Coursera** rows: free to enrol; hours are the module-hour sums on the course page.
- **Manual** rows: paid, HRD Corp-claimable courses. `hrd_note` quotes what the provider's page
  says and `duration_note` states any assumption (e.g. hours per training day).
- `level` = the skill level (1-5) Adept estimates the course brings a learner to. It is an
  Adept judgment and the UI labels it as an estimate.
- **Bahasa Melayu rows** use the established `language=ms` code for Malaysian Malay
  (`ms-MY`); language is verified from provider content, never inferred from a URL locale.

The 2026-10-30 release adds five provider pages opened on that date:

| Course / source | Provider | Hours | Listed MYR fee | Language evidence |
|---|---|---:|---:|---|
| [Kursus Microsoft Excel](https://www.modernlms.com/learning/courses/kursus-microsoft-excel/) | ModernLMS | 2 | Free | Explicit Bahasa Melayu label |
| [Kursus Google Ads](https://www.modernlms.com/learning/courses/kursus-google-ads/) | ModernLMS | 4 | 149 | Explicit Bahasa Melayu label |
| [AI Ready Malaysia: Edisi Pendidik](https://pepper-s-site-1c7b.thinkific.com/courses/ai-ready-malaysia-asia-pacific-edisi-pendidik) | Pepper Labs | 2 | Free | Malay curriculum and lesson titles |
| [AI Ready Malaysia: Edisi Tenaga Kerja MSME](https://pepper-s-site-1c7b.thinkific.com/courses/ai-ready-malaysia-asia-pacific-edisi-tenaga-kerja-MSME) | Pepper Labs | 2 | Free | Malay curriculum and lesson titles |
| [AI Ready Malaysia: Edisi Pelajar](https://pepper-s-site-1c7b.thinkific.com/courses/ai-ready-malaysia-asia-pacific-edisi-pelajar) | Pepper Labs | 2 | Free | Malay curriculum and lesson titles |

Pepper Labs durations are video-content hours, not total study-time guarantees; its pages do
not establish certificate entitlement. ModernLMS lists Google Ads as HRD Corp claimable;
actual reimbursement remains subject to eligibility and employer approval. Its free Excel
course is not priced as a claim. Google certification exams are separate.

No Microsoft Learn or e-LATiH course is labelled Malay without a course-level record
supporting language, hours and price. This release does not establish that either platform
lacks Malay content. Existing rows retain their historical `verified_at` dates and pricing
caveats; opening a link alone does not refresh its fee or eligibility verification.

Pipeline: public provider pages / Microsoft Learn API → URL and duration normalization →
existing catalogue skill IDs and estimated levels → deterministic shared source definitions →
full source/seed equality and graph regressions → CSV seed and live sync. Regeneration from
an older saved API response must retain its original retrieval date.

The digital-skills pass also adds [Introduction to Git](https://learn.microsoft.com/en-us/training/modules/intro-to-git/)
from Microsoft Learn, opened 2026-10-30: free learning, English, 86 minutes across six units
(1.4 hours after the existing rounding rule), GitHub account and CLI familiarity required.
It is a dated manually checked row in `FREE_DIGITAL`, distinct from API-refreshed `CURATED` rows.
All 104 course URLs were opened in this review (103 in the bulk HTTP audit and the Git page
separately). HTTP availability does not establish current enrollment or refresh older price facts.

## Completion-certificate evidence (2026-10-31)

Learning price and completion-certificate availability are separate facts. The versioned
`certificate_evidence.json` records only provider-verified inclusion in the listed course
price, with its own source and retrieval date. It is a serving-side annotation of canonical
course IDs, shared by CSV and database catalogues; it does not change ingestion CSV columns
or need a migration. Missing evidence defaults to `unknown` and never satisfies an HR
certificate-required brief, even when learning is free or the course has a listed fee.

Both ModernLMS pages were reopened on 2026-10-31: [Google Ads](https://www.modernlms.com/learning/courses/kursus-google-ads/)
lists a completion certificate and RM149; [Microsoft Excel](https://www.modernlms.com/learning/courses/kursus-microsoft-excel/)
lists a completion certificate and FREE. These are course-completion documents, not Google
or Microsoft professional certification exams. Other course certificates and their fees
remain unverified. In particular, the three Pepper Labs pages do not establish a certificate.
Existing course fee/hour verification dates remain 2026-10-30; certificate verification does
not refresh unrelated facts. Certificate restrictions apply to selected courses and all
alternatives through the same filtered catalogue. Personal learning remains available.


## Digital and green skill-bank pass (2026-10-31)

Adds 16 free-learning records (120 catalogue rows total), frozen in `FREE_DIGITAL` for both
pipeline regeneration and live sync. Each provider course URL was opened on 2026-10-31.
[skill_bank_provenance.json](skill_bank_provenance.json) records exact titles, dates,
duration/price evidence, skill mapping estimates and access limitations; the
[coverage report](../../../../docs/skill-bank-coverage.md) lists every course with its URL.
Microsoft Learn durations are from its Catalog API retrieved the same day. Older rows
retain their historical dates and facts. Kaggle live pages are JavaScript shells; their
metadata came from indexed official course pages. ECMWF materials require login.
Precision Farming and ECMWF use disclosed upper bounds of provider duration ranges.
RM0 describes learning only; resource usage, licensed software and exams may cost extra.
No new certificate entitlement or HRD reimbursement is assumed.

All target requirements now have at least one course record. This is course presence,
not proof that a learner can reach every required level: introductory FinTech AI and
Selenium courses still leave higher proficiency explicitly unmet.
