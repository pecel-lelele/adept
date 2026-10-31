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


The 2026-10-31 digital/green focus release removes out-of-scope target requirements while
retaining intake and current-role references, and adds 16 dated free course records.
See [coverage and course evidence](../../../docs/skill-bank-coverage.md),
[catalogue provenance](courses/skill_bank_provenance.json) and
[taxonomy provenance](taxonomy/provenance.json). Coverage means course presence, not
complete professional qualification or attainment of every required skill level.
