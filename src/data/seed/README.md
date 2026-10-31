# Seed data (synthetic only)

Tiny synthetic samples so every table has something to show. **No real people or CVs.** Courses
and SDG targets are real, public, dated records (see their folders). Load with `make seed` (runs `src/db/seed.py`).

- One folder per area; each owner edits only their folder.
- File name = table name (`skills.csv` → `skills`), header row = column names.
- Empty cell = NULL. Arrays use Postgres literal syntax: `"{a,b}"`.
- Large or raw downloads go in `src/data/raw/` (gitignored), never here.

| Folder | Owner | Tables |
|---|---|---|
| `taxonomy/` | M2 (F4) | skills, roles, role_skills |
| `personas/` | M2 (F1) | users, profiles, user_skills |
| `trends/` | M1 (F2) | snapshots, trend_signals |
| `courses/` | M3 (F5) | courses (written by `pipelines.pathway`) |
| `pathway/` | M3 (F5) | skill_prerequisites |
| `sdg/` | M3 (F6) | sdg_goals, sdg_targets (written by `pipelines.sdg`), role_sdg_map, skill_sdg_map, org_regions |
| `org/` | M4 (F7) | users (employees), organizations, memberships |

`trends/paper_store/` holds the portable trend history (`trend_fetched_days`,
`trend_paper_mentions`, `trend_matcher_calibration`) and the matcher `equivalence.json`, written by
`pipelines/trends/backfill.py export-seed`. Public arXiv IDs, dates and catalogue skill IDs only;
no abstract text. `taxonomy/role_categories.csv` is a reviewed role grouping (M1-025), read by the
API and not loaded as a database table.
