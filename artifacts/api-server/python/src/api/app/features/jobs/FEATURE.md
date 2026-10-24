# Live job openings and certifications (M4)

- **Owner**: M4 (works with F4 matching, F5 pathway, F7 organisation mode)
- **API code**: `src/api/app/features/jobs/` (router → service → repository; `fit.py` is pure)
- **Contracts**: `src/api/app/contracts/jobs.py`
- **Pipeline**: `src/pipelines/jobs/` → `src/data/seed/jobs/` and tables `job_postings`,
  `job_fetch_log`, `certifications` (migration `20261023160000`)
- **Web code**: `src/web/src/features/jobs/`; page `/app/jobs`; cards on `/app/matches`,
  `/app/matches/[role]`, `/app/pathway` and `/org/plan`
- **Translations**: `src/web/messages/{en,ms,zh}/jobs.json`

## Why

Matching ranks future roles from trend projections; learners also need to see that the role is
hiring today, who is hiring, which skills the ads ask for, and whether their plan gets them
there. Mentor feedback (Oct 2026): link learning to real job positions and certifications, and
show the path to a job after training, not only the learning.

## What it does

- **Openings per role** (`GET /jobs/roles/{role_id}`): live ads matched to the role by job
  title, the skills the ads ask for most, and how many ads are within reach today and after the
  learner's plan (an ad is within reach at >= 60% of the catalogue skills it names; ads naming
  fewer than two are not rated). Uses the saved plan when it is for this role and scenario, else
  the plan F5 would build, so the numbers match the plan page.
- **Job board** (`GET /jobs/board`): every matched opening, filtered by role, work mode and text.
- **Counts** (`GET /jobs/summary`): openings per role, for the matches list.
- **Certifications** (`GET /jobs/certifications?role_id=&payer=`): paid exams that cover the
  role's required skills, with the official fee for Malaysia, the page it was read from, its
  date, ringgit at the BNM rate, which plan courses prepare for it, and how many current ads
  name it. `payer=employer` (team programmes) shows no personal skill status.

Openings are information. Adept never applies, never shares a profile with an employer and never
ranks people for an employer. Exam fees are paid to the issuer; Adept takes no payment.

## Sources and rules

Only official public feeds: employer applicant-tracking APIs (Greenhouse, Lever, Ashby, Workday
career sites, Jibe) and remote-job APIs (Himalayas, Jobicy, Remote OK, Remotive), plus Careerjet,
Jooble and web3.career when a key is set. robots.txt is checked for every host, with a delay
per host. Not used: JobStreet (terms clause 7(d) bans scraping), LinkedIn and Indeed (no public
jobs API), EY (robots.txt disallows its feed), SmartRecruiters (API host disallows crawlers).
Only Malaysian openings or remote ones open to Malaysians are kept. Ad text is read in memory
for skills and never stored; the apply link is kept unchanged and the source is credited, as the
remote boards' terms require.

## Pipeline

| Stage | Choice | Notes |
|---|---|---|
| Source | 45 employer feeds + 4 remote boards (+3 keyed) in `boards.py` | official public APIs only |
| Preprocessing / cleaning | Malaysia / Malaysia-eligible remote only; HTML → text; dedupe by source + board + id | ad text never stored |
| Features | skills named (CV parser's catalogue matcher), certifications named (exam code / name), seniority | every skill id exists in the taxonomy |
| Model / method | role = ordered job-title patterns per Adept role; unmatched ads stay unassigned | a skills-only fallback was dropped for poor precision |
| Evaluation | per-source counts, share assigned, skills per ad, unassigned job families; title rules >= 95% on a hand-labelled set | `tests/pipelines/jobs`, `fetch_log.json` |
| Serving | seed CSVs + `--db` upsert; openings not listed in a successful re-read are closed; stale after 14 days | `GET /jobs/*` |

Refresh: `PYTHONPATH=src/api:src .venv/bin/python -m pipelines.jobs.run --db`.
