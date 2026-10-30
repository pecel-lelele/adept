# Shared automatic data refresh (Core)

The scheduler, signed-in dashboard/radar button and admin panel share the same durable
background job. GitHub calls the app; it never connects to the Replit database.

See [the operating guide](../../../../../docs/data-refresh.md) for endpoints, bounded I/O,
dates, source assessment, deployment steps and compatibility requirements.

- Contracts: `app/contracts/data_refresh.py`; worker: `jobs.py`; sources: `service.py`.
- Trends: `automatic_trends.py` reuses the production MiniLM/scorer/validator/publisher.
- One site-wide advisory lock, cooldown, per-user rate limits, admin-only bypass.
- Source failures retain the previous data; interrupted jobs fail visibly after lease loss.
- Three append-only refresh migrations; apply explicitly, never during startup.
- Default cadence: complete ISO weeks for trends, daily jobs/catalogue/labour checks.
- No upstream I/O on page reads or a fully current refresh check.
