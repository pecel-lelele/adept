# Seed data (synthetic only)

Tiny synthetic samples so every table has something to show. **No real people, CVs or
course claims.** Load with `make seed` (runs `src/db/seed.py`).

- One folder per area; each owner edits only their folder.
- File name = table name (`skills.csv` → `skills`), header row = column names.
- Empty cell = NULL. Arrays use Postgres literal syntax: `"{a,b}"`.
- Large or raw downloads go in `src/data/raw/` (gitignored), never here.

| Folder | Owner | Tables |
|---|---|---|
| `taxonomy/` | M2 (F4) | skills, roles, role_skills |
| `personas/` | M2 (F1) | users, profiles, user_skills |
| `trends/` | M1 (F2) | snapshots, trend_signals |
| `courses/` | M3 (F5) | courses |
| `sdg/` | M3 (F6) | sdg_targets, role_sdg_map, skill_sdg_map |
| `org/` | M4 (F7) | users (employees), organizations, memberships |
