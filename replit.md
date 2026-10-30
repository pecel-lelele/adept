# Adept: root deployment, one public server

Keep the required root `docs/`, `submission/`, `src/` and `tests/` layout. All product code
lives in `src/`. Do not recreate an artifact scaffold or move the repository into a backup.

## Run and build

- Preview: `uv run --frozen python src/scripts/dev.py dev` (root `.replit` run command).
- Publish build: `python3 src/scripts/replit.py build`.
- Publish start: `python3 src/scripts/replit.py start`.
- Local checks: `uv run --frozen python src/scripts/dev.py check` and `pnpm test:proxy`.

Build uses frozen uv/pnpm dependencies and generates the standalone web server and assets.
If uv is unavailable, Python installation uses the constraints in `requirements.txt`.
The web build uses webpack consistently across Windows and Linux to avoid the observed
Turbopack standalone-tracing race on Windows.
Start supervises private FastAPI on `127.0.0.1:8000`, checks API/database readiness, then
starts one public Next.js server on `0.0.0.0:3000` (mapped to external port 80). `PORT` is the
public port; `API_PORT` is private and must be different. The root config has no application
router, artifact metadata, Express process, Drizzle schema push or mockup build.

Next.js serves pages, server actions, `/api/v1/*` and health aliases. Use the standalone
launcher; never replace it with `next start` or a static-file server. `GET /api/healthz` and
`GET /api/v1` return 200 only when FastAPI reports a healthy database, otherwise 503.
The public health probes need no forwarded visitor header. Normal proxied requests derive
trusted visitor identity and ignore supplied internal-secret/IP headers.

## Production configuration

Replit supplies its managed `DATABASE_URL`. Set a stable random `SESSION_SECRET` of at least
32 characters and a matching `PROXY_SHARED_SECRET` for web/API. Set `TRUSTED_PROXY_HOPS`
only after verifying the live ingress chain; a settings screenshot is not evidence of
header sanitisation. Until then, `PROXY_CLIENT_IP_MODE=best-effort` with zero hops keeps
serving without signing an unverified address, so anonymous requests share the private
API peer's rate bucket. Signed-in limits still use verified session IDs.
Follow [the count-only verification procedure](docs/replit-proxy-verification.md) before
enabling a positive hop count and trusted mode. Keep `APP_ENV=production`,
`AUTH_RAW_USER_IDS=false`, an empty `AUTH_DEFAULT_USER`, and `M3_BACKEND=postgres`.
`AUTH_MODE=demo` means normal local PostgreSQL accounts, not a fixture/demo session.
Set `WEB_ORIGIN` and `CORS_ORIGINS` to the exact published HTTPS origin without a trailing
slash. The supervisor sets the private `API_URL` and public bind address itself.

RunPod/Gemini assistant keys are optional. The MiniLM `TRENDS_RUNPOD_API_KEY` and endpoint
configuration are separate from Adi's GLM key. Do not print or commit any key or database URL.

## Publishing handoff

Pull the reviewed branch/merged source into the target Replit project. In Publishing,
confirm the root build/start commands above and one public port. Remove saved artifact or
`next start` command overrides left from the prior deployment setup. GitHub changes do not
copy a friend's production secrets or database.

Prepare schema/reference data in the intended development database explicitly before first
publish. If needed, use Replit's production-database initialization from reviewed development
data. Never run migration/seed scripts automatically at production build or start, or point
local setup at production. Production schema changes follow the database owner's procedure.

Before publishing, set `ADMIN_USER_IDS` (comma-separated account IDs of trend-refresh admins) to
the same value on both web and API; it replaces `ADMIN_EMAILS`. Replit startup never migrates, so
apply the two new migrations manually to the production database first:
`20261030140000_core_workspace_integrity.sql` and `20261030143000_public_labour_context.sql`.

Publish only when the owner is ready. Verify `/`, `/about`, `/auth/login`, a static asset,
`/api/healthz`, `/api/v1` and `/api/v1/health`, then test signed-in flows with synthetic accounts.
A live old release can remain healthy while a new publish attempt fails; verify the source
revision and run command for that specific deployment rather than inferring from the URL.

## CI and background data

CI checks Python lint/tests, web lint/types/translations, contracts, proxy regressions,
PostgreSQL upgrades/recovery and the actual root production build/start. Its deployment
smoke uses an explicit disposable loopback database and never calls a model.
Weekly source/trend jobs and the guarded manual MiniLM publisher stay at `.github/workflows`;
worker Docker builds use the repository root as context. Public pages read saved snapshots.
