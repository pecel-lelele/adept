# Review, refresh and demo runbook

## App refresh configuration

Use the existing published MiniLM endpoint. API and Next server need the same comma-separated `ADMIN_USER_IDS` of actual accounts; an email address grants no admin rights. Empty means no admins. The API checks the signed account on every refresh operation.

Set API-only `GITHUB_DISPATCH_TOKEN` to a repository-scoped token with Actions read/write for this repository; keep it out of browser variables and logs. Set `GITHUB_REPOSITORY=pecel-lelele/adept`, `TRENDS_REFRESH_WORKFLOW=trends-refresh.yml`, and `GITHUB_DISPATCH_REF=main`. The workflow must exist on that ref. Before a production refresh, configure repository secrets `TREND_DATABASE_URL` (the database served by the app) and `TRENDS_RUNPOD_API_KEY`, and variable `TRENDS_RUNPOD_ENDPOINT_ID`. The MiniLM key is separate from Adi's key.

Authorized admins see the refresh panel on their app/team dashboard and `/admin/snapshots`. Fetch latest starts the workflow, polls status and invalidates local caches after success. Re-score only processes stored signals and may report no new data. Workflow progress is not per-stage model telemetry. A successful dispatch alone does not prove a published snapshot; inspect the workflow result, selected snapshot date, sources and fallback indicator.

This setup can incur RunPod charges and publish to the deployment database. Perform a production run only with explicit authorization for that environment and paid operation. No such run is part of local verification.

## Proxy and deployment security

Both Next.js and FastAPI require `PROXY_SHARED_SECRET` in production. The Next.js web server forwards client requests with `x-internal-proxy-secret`, and FastAPI's security middleware trusts `X-Real-IP` only when the secret matches.

In Replit production, Replit's ingress proxy is 1 hop in front of the container: set `TRUSTED_PROXY_HOPS=1`. Alternatively, set `PROXY_CLIENT_IP_MODE=best-effort` with `TRUSTED_PROXY_HOPS=0`, which safely extracts the edge-stamped right-most address without manual hop verification. For local development, use `TRUSTED_PROXY_HOPS=0`.

## Other stored public data

`data-sources.yml` uses `CATALOGUE_DATABASE_URL` for existing provider course sync plus DOSM monthly observations, and `JOBS_DATABASE_URL` for job-board writes. Missing secrets do not silently select a developer database. Keyed job boards also need their own provider keys. Missing manual catalogue configuration fails visibly. A dry source check is not evidence that the app database was updated.

DOSM is national survey context, not an occupational prediction or a scoring input. Stored and fallback responses preserve actual observation/retrieval dates. Three added non-technical O*NET occupations are current-role intake choices, not fabricated emerging jobs. Malay course entries remain pending verified provider metadata.

## Database rollout

Use `src/db/migrate.py`, the repository migration runner. It recognizes only the known equivalent historical aliases timestamp collision; other duplicate timestamps fail. Do not run raw dbmate across that historical collision or edit either historical file.

New migrations are `20261030140000_core_workspace_integrity.sql` and `20261030143000_public_labour_context.sql`. The first checks new writes immediately while retaining old rows under NOT VALID foreign keys. Before validating those keys, count/join legacy learning rows against roles and generated workspace organisation IDs, review missing references, then agree a repair policy. Do not delete historical rows automatically. Down sections remove new schema/policy enforcement; rolling back weakens protection and removing the national-context table loses those public observations.

Funding uses transaction-local `app.funding_org`. Production application users must be non-superuser and lack BYPASSRLS; FORCE RLS cannot restrain a superuser. Verify ownership/grants and a second organisation with that actual role after rollout. Application membership/manager checks remain required in addition to the storage policy.

## Isolated verification

Use the pinned Python/JavaScript environments. Run `uv run --no-project python src/scripts/dev.py check`; the task includes Python lint/format, web lint, translations, pytest, web regressions, TypeScript and generated-contract drift. Windows may require the supported execution approval because sandboxed TestClient requests can hang.

Opt-in PostgreSQL tests require `ADEPT_TEST_DATABASE_URL` pointing to a deliberately created disposable database. Migrate and seed that exact target first; never infer isolation from `.env`. Never create new Docker containers or spin up ad-hoc review containers (e.g. `docker run`); use only the established Compose database service or isolated synthetic test fixtures. Ordinary tests disable paid providers and ambient databases. Run `pnpm build`, then `pnpm test:e2e` for desktop/mobile. The browser harness starts only loopback ports 18091/13091 with memory fixtures and signed synthetic sessions. It never uses ambient database/model credentials.

Run the counterfactual harness for both scenarios with `PYTHONPATH=src/api;src` on Windows (colon on Unix): `python -m pipelines.guardrails.matching_counterfactual --scenario moderate --out tmp/fairness-moderate.json`; repeat with fast. Identity invariance on synthetic fixtures is useful regression evidence, not proof of universal fairness.

## Demo preparation

`GET /api/v1/meta/version` reports version, known 40-character revision, build dirty state and environment. Build files record Git identity; `dirty=true` means the commit alone does not identify all built source. Set `BUILD_REVISION` in deployments without a Git checkout; unknown identity remains null.

`python src/scripts/demo.py warmup --base-url http://127.0.0.1:8000` reads stored health/version/snapshot only. Synthetic account creation/reset additionally requires an HTTP loopback development API, `synthetic.*@example.test`, and a 12+ character `ADEPT_DEMO_PASSWORD` supplied through the environment. `account --reset` removes only that authenticated synthetic account before creating it again. No token/password is printed. Use the actual web sign-in afterward.

Before recording, confirm the clean committed revision, selected snapshot and fallback status; use clearly synthetic CVs; run both audience journeys and prepare a stored-data fallback. Record human timings and observations separately without committing participant identities. Follow [final-round status](final-round-status.md) for unfinished acceptance evidence.
