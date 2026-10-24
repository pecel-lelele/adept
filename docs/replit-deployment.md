# Publish Adept on Replit Autoscale

The repository has two servers. Replit publishes them through the Autoscale
application router configured in [`.replit`](../.replit) and the per-service
`artifacts/*/.replit-artifact/artifact.toml` files: the Express proxy
(`artifacts/api-server`) owns `/api/v1` and `/api/healthz` and supervises FastAPI
privately at `127.0.0.1:8000`; Next.js (`src/web`) serves every other path. See
[replit.md](../replit.md) for the current commands. The standalone
[`src/scripts/replit.py`](../src/scripts/replit.py) launcher remains for a
single-port Cloud Run style deployment and local production smoke tests; it is not used
by the artifact-routed deployment. The development runner (`dev.py dev`) is for
Preview: it must not be the deployment run command.

## Update an existing workspace safely

GitHub merges do not update the Replit workspace. Check `git status --short --branch`
and `git log -1 --oneline` there. Preserve local commits with a backup branch and
uncommitted changes with a named stash **before** switching to main. Check ignored
files separately: `git stash --include-untracked` does not include ignored files.
Do not use `reset --hard`, `clean`, or a forced checkout to synchronize.

For a workspace with local Replit configuration, keep its environment settings,
Nix packages and Preview workflow. Keep `gcc` in `[nix].packages`: the API supervisor
locates its `libstdc++` runtime for PyMuPDF on Nix without a machine-specific library path.
When using the single-port launcher instead of the artifact router, set:

```toml
[deployment]
deploymentTarget = "cloudrun"
build = ["python3", "src/scripts/replit.py", "build"]
run = ["python3", "src/scripts/replit.py", "start"]
```

The launcher reads the local port mapped to external port 80 from `.replit`; an explicit
`PORT` overrides that selection and must match the Networking mapping.

## Publishing settings

Select **Autoscale**, initially **one maximum machine**. Keep secrets in Replit
Secrets / deployment secrets, never in Git or a screenshot. Set these production
environment values before publishing:

| Setting | Value |
| --- | --- |
| `DATABASE_URL` | Replit's attached **production** PostgreSQL connection string; leave the development connection unchanged. |
| `SESSION_SECRET` | Existing stable random secret, at least 32 characters; keep it across deployments. |
| `PROXY_SHARED_SECRET` | Existing random secret shared by the co-hosted web and API. |
| `TRUSTED_PROXY_HOPS` | Required in production: a positive count, set only after verifying the platform's trusted proxy path (see below). Zero or missing blocks startup; `0` is for local development only. |
| `WEB_ORIGIN` | Exact published origin, for example `https://adept-corp.replit.app`, without a trailing slash. |
| `CORS_ORIGINS` | Same exact origin; if unset, the launcher uses `WEB_ORIGIN`. |
| `APP_ENV`, `NODE_ENV`, `M3_BACKEND` | Launcher enforces `production`, `production`, `postgres`. |
| `API_URL` | Launcher enforces `http://127.0.0.1:8000`; never the public MiniLM endpoint. |

For per-visitor rate limits, verify how Replit's load balancer sanitizes/appends
`X-Forwarded-For` on the deployed domain, using platform documentation or support
and controlled requests (including a deliberately supplied header). If exactly one
trusted proxy appends the client address, set `TRUSTED_PROXY_HOPS=1`; use the verified
count for another topology. Do not infer trust from an arbitrary header or guess a
larger count: clients can supply the entries to its left. Production startup rejects a
zero, missing or malformed count, so do not publish until the count is verified. Zero is
valid only for local development, where visitors share one rate-limit bucket, including
the login-attempt limit. A shared proxy secret alone does not enable per-visitor limits.
Recheck the count when adding a proxy or changing domains.

Keep the existing `LLM_*`, `RUNPOD_API_KEY` and `GEMINI_API_KEY` configuration to
enable Adi; keys alone do not select a provider. See [`.env.example`](../.env.example).
MiniLM's `TRENDS_*` credentials belong to the offline refresh process; publishing
the web app does not start an embedding job or a persistent GPU worker.

The build installs Python/web dependencies and produces Next.js's standalone server
with public/static assets. It makes no database writes or model requests.
Startup validates production settings and checks API/database health, then starts
the public web server. If either child exits, the container stops with a failure.

## Database initialization

For the first deployment, initialize the **development** database from the current
code before using Replit's option to copy it to production. Run in Replit Shell,
using the workspace's injected development `DATABASE_URL`:

```bash
.venv/bin/python src/db/migrate.py up
.venv/bin/python src/db/seed.py
```

Review the output: migrations and catalogue seed loading must succeed. Use only
synthetic test accounts and CVs. Copying development data also copies any existing
test state. If a production database already exists, explicitly apply pending
migrations against that database before republishing; do not copy over it blindly.
Autoscale startup deliberately does not migrate or reseed on every cold start.

## Verify before and after publishing

In Replit Shell, after synchronizing the code:

```bash
python3 src/scripts/replit.py build
python3 src/scripts/replit.py doctor
```

`doctor` checks artifact/configuration presence without displaying secret values;
it does not establish database connectivity or validate the Replit account's ability
to publish. A Shell can have development settings while Publishing has separate
production settings. A local production smoke test needs the intended values in
that Shell, including `WEB_ORIGIN`; stop the Preview servers before testing
`python3 src/scripts/replit.py start` to avoid a port conflict.

Reload Replit after updating `.replit`, then reopen **Publish → Advanced settings**.
Confirm Autoscale and the public-port mapping. Publish and inspect **Build** and
**Run** logs. Successful runtime logs include `Starting private API`, an HTTP 200
health request, then `Starting public web` and Next.js's ready message.
Visit `/`, `/about`, and sign in with a synthetic account; verify a stored trend
snapshot and an existing feature workflow. A build success alone is insufficient.

If Publish remains disabled **before any build starts**, capture the specific
validation message in Publishing. Check the owning account's publish permissions,
billing eligibility and [Replit status](https://status.replit.com). The generic
"Publishing is not available right now" banner does not establish which account
or platform check failed. Missing startup commands are a confirmed configuration
gap; fixing them does not prove that a separate account restriction is resolved.

If the build reports `ERR_PNPM_FETCH_403` at `package-firewall.replit.internal`,
the package download was denied before Next.js compilation. Check the pinned
package version against vendor advisories and review Replit's rejection details;
the generic "No authorization header" message does not establish that a public
package needs a token. Next.js is pinned to the vendor-patched `16.4.1` release,
with its matching lint configuration and frozen lockfile. An old workspace still
requesting `next-16.2.12.tgz` has not loaded that dependency update. Keep the
platform's package checks enabled; if the patched download is also denied, collect
the exact URL and rejection body for Replit Support. No Replit-internal registry
URL is committed in the repository.

After production is reachable, put its externally accessible connection string in
GitHub's `TREND_DATABASE_URL` secret and follow the
[MiniLM deployment handoff](../src/pipelines/trends/runpod/DEPLOYMENT_HANDOFF.md).
GitHub Actions cannot reach the private development hostname `helium`.

## Recovering from terminated database connections

`terminating connection due to administrator command` means PostgreSQL terminated
the session. App logs alone do not identify the initiating platform event. Check
Replit's production database events around the same UTC timestamp; app log times
may be displayed separately in the browser's local timezone.

Both API pools check connections before use and replace terminated idle sessions.
Rate-limit queries have a 2-second statement timeout and a 1-second lock timeout;
when unavailable, the limiter retains its bounded, thread-safe per-process fallback.
The web API client retries GET/HEAD once for network failures or HTTP 502/503/504.
Transactions that have already started and HTTP writes are never automatically
replayed because their commit outcome may be unknown. An ongoing database outage
can still return 503 for authentication and writes; seed-backed catalogue reads
are degraded service, not proof that production storage is healthy.

After publishing this repair, verify sign-in, `/app`, and a saved-data workflow,
then repeat after an idle period. Confirm `/auth/me` succeeds in the API run logs.
If terminations continue with fresh connections, collect database events and
sanitized run logs for Replit Support. Do not reset or copy over production data.

The regression test below intentionally terminates only sessions it creates.
Run it **only on a disposable, migrated and seeded test database**, never production:

```bash
ADEPT_TEST_DATABASE_URL='<disposable test database URL>' .venv/bin/python -m pytest tests/integration/test_database_recovery.py
node --test tests/web-api-recovery.test.ts
```

Pool behavior follows [Psycopg's connection quality documentation](https://www.psycopg.org/psycopg3/docs/advanced/pool.html#connection-quality).

References: [Replit configuration](https://docs.replit.com/pt/references/project-setup/configuration),
[production database lifecycle](https://docs.replit.com/features/data-and-storage/development-and-production).
