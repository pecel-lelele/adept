# Shared automatic data refresh (Core)

The scheduler, signed-in dashboard/radar button and admin panel share the same durable
background job. GitHub calls the app; it never connects to the Replit database.

See [the operating guide](../../../../../docs/data-refresh.md) for endpoints, bounded I/O,
dates, source assessment, deployment steps and compatibility requirements.

- Contracts: `app/contracts/data_refresh.py`; worker: `jobs.py`; sources: `service.py`.
- Trends: `automatic_trends.py` reuses the production MiniLM/scorer/validator/publisher.
- One site-wide advisory lock, cooldown, per-user rate limits, admin-only bypass.
- Source failures retain the previous data; interrupted jobs fail visibly after lease loss.
- Four append-only refresh/input migrations; apply explicitly, never during startup.
- Default cadence: complete ISO weeks for trends, daily jobs/catalogue/labour checks.
- No upstream I/O on page reads or a fully current refresh check.

Publication stays on the lock-owning session, with a heartbeat and a conservative replacement
fence after session loss. Stored measured inputs support inference-free reconstruction.
Incomplete course checks and scheduler cooldown are reported as unfinished work, not success.
See the operating guide for the 2026-10-31 review corrections and real PostgreSQL regressions.

Job freshness exposes the actual maximum posting `last_seen` as `data_as_of`, separately from
the most recent successful feed read. `JOBS_STALE_DAYS` controls labelled stale ads and fresh
counts consistently; daily automatic work includes jobs. Static trend runtime evidence comes
only from committed/fetched byte-bound sidecars. A course deadline reached on the final page
also reports incomplete checks and retains the previous catalogue.

## Trend fallback (2026-10-31, M1-017)

The trends step tries RunPod MiniLM first and keeps 90 s of its budget back. If the worker is
missing or fails and Gemini embeddings are enabled, `trend_fallback` measures the same weeks with a
threshold calibrated to the stored MiniLM mention rate. The method and model are stored with the
inputs and named in the snapshot note. No stored measurement means no calibration: the refresh
fails and the last snapshot stays live. `trends-refresh.yml` is a manual backup, not scheduled.

## Rolling, accumulated trends (2026-10-31, M1-018)

`trend_store` keeps every fetched arXiv paper with the skills it mentions. A refresh fetches
only days not stored yet (from 6 Oct 2026 to 3 days ago, ≤14 days and ≤50 papers per day per
run) and matches only those papers. The snapshot compares the last 7 stored days with the 7
before, so the window moves daily. With no new announced day, a refresh returns immediately
without network or model calls. Press refresh once after deploying to backfill the history.
