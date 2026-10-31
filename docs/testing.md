# Test results and isolated PostgreSQL verification

A passed test ran its assertions successfully. A skipped test did not run because a
prerequisite was missing; it is neither a passing assertion nor a data record.

## Offline checks

`python src/scripts/dev.py check` uses the existing pytest defaults: synthetic
in-memory/CSV fixtures, disabled model providers, and no application database access.
The PostgreSQL integration tests intentionally skip unless explicitly configured.
This safety boundary should not be removed just to obtain a green count.

The 31 October 2026 baseline was **2,148 passed and 50 skipped**. All 50 were
PostgreSQL prerequisites, not failed model calls or missing real user data:

| Group | Skipped |
|---|---:|
| Shared PostgreSQL rate limiter | 4 |
| Plan/progress/badge persistence | 5 |
| Database catalogue/reference reads | 3 |
| Catalogue/SDG/FX synchronisation | 7 |
| Evidence-backed skill credit in PostgreSQL | 5 |
| Pooled connection recovery | 5 |
| Refresh lease, rollback and concurrent chart reads | 3 |
| Workspace constraints and row-level security | 2 |
| Job-refresh preservation | 1 |
| Trend provenance/migration round trips | 13 |
| Frozen trend export versus database rows | 2 |

Counts describe that baseline, not a permanent suite size. Conditional programme
assignment skips exist in older tests but were not activated in this run.

## Run all tests with PostgreSQL

Use an **already running local PostgreSQL server with pgvector**. The repository's
existing Compose database is suitable. This command never starts another container.
Configure `ADEPT_TEST_PG_ADMIN_URL` through your terminal/secret environment to point
to the server's **postgres admin database**, using its existing credentials.
The variable is already illustrated, without a real secret, in `.env.example`.
Do not commit or paste the real value into logs or issue comments.

```powershell
.venv/Scripts/python.exe src/scripts/test_postgres.py
```

```bash
.venv/bin/python src/scripts/test_postgres.py
```

The runner:

1. Requires an explicit loopback host and `dbname=postgres`; it does not load `.env`
   or fall back to an ambient application database.
2. Creates uniquely named primary and refresh-review databases on that server.
3. Migrates and seeds only the newly created primary database using production scripts.
4. Supplies the explicit database opt-ins while retaining fixture storage defaults
   and disabled paid providers. Refresh tests use their own separate database/schema.
5. Runs pytest and fails if the requested run still contains a skipped test.
6. Cleans up only its own generated database names after checking their original OIDs,
   including after test/migration failure. It never drops the configured admin database.

The admin role needs database creation and the role/extension capabilities used by
integration tests. Do not use production credentials or a remote production server.
If cleanup fails, the runner names only its own leftover databases and exits with
an error; investigate before deleting anything manually.

To run the entire repository quality gate using the same disposable databases, use
`python src/scripts/test_postgres.py --check`. Lint/type/contract failures retain a
nonzero exit status even when the pytest report has no skips.

To run only the database regressions, pass their test paths, for example:

```powershell
.venv/Scripts/python.exe src/scripts/test_postgres.py tests/integration/test_refresh_postgres.py tests/integration/test_workspace_integrity.py
```

The CI database job calls the same runner with the persistence, evidence, rate-limit,
job, recovery, refresh, workspace and provenance suites. Existing upgrade/migration/
seed checks remain against the CI service database; the test runner creates its own
fresh databases on that existing service. Unexpected integration skips fail that job.

The offline job may still report intentional database skips. Combined evidence comes
from the offline suite plus the zero-skip PostgreSQL run; do not relabel skipped
assertions as passed. Optional paid inference is not needed for these regressions.
