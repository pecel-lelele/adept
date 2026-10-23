# Publish Adept on Replit Autoscale

The repository has two servers. Replit publishes Next.js on one public port;
Next.js calls FastAPI privately at `127.0.0.1:8000`. Use the versioned
[`.replit`](../.replit) and [production launcher](../src/scripts/replit.py).
The development runner (`dev.py dev`, or a workspace's `replit_dev.py`) is for
Preview: it must not be the deployment run command.

## Update an existing workspace safely

GitHub merges do not update the Replit workspace. Check `git status --short --branch`
and `git log -1 --oneline` there. Preserve local commits with a backup branch and
uncommitted changes with a named stash **before** switching to main. Check ignored
files separately: `git stash --include-untracked` does not include ignored files.
Do not use `reset --hard`, `clean`, or a forced checkout to synchronize.

For a workspace with local Replit configuration, keep its environment settings,
Nix packages and Preview workflow. Add this block if absent, or replace its existing
deployment block (do not duplicate TOML tables):

```toml
[deployment]
deploymentTarget = "cloudrun"
build = ["python3", "src/scripts/replit.py", "build"]
run = ["python3", "src/scripts/replit.py", "start"]
```

The launcher reads the local port mapped to external port 80 from `.replit`;
the repository uses 3000, while an existing Preview workspace can keep 5000.
An explicit `PORT` overrides that selection and must match the Networking mapping.
Keep `gcc` in `[nix].packages`: the launcher locates its `libstdc++` runtime for
PyMuPDF on Nix without a machine-specific library path.

## Publishing settings

Select **Autoscale**, initially **one maximum machine**. Keep secrets in Replit
Secrets / deployment secrets, never in Git or a screenshot. Set these production
environment values before publishing:

| Setting | Value |
| --- | --- |
| `DATABASE_URL` | Replit's attached **production** PostgreSQL connection string; leave the development connection unchanged. |
| `SESSION_SECRET` | Existing stable random secret, at least 32 characters; keep it across deployments. |
| `PROXY_SHARED_SECRET` | Existing random secret shared by the co-hosted web and API. |
| `TRUSTED_PROXY_HOPS` | Set only after verifying the platform's trusted proxy path; see below. Default `0` disables client-IP forwarding. |
| `WEB_ORIGIN` | Exact published origin, for example `https://adept-corp.replit.app`, without a trailing slash. |
| `CORS_ORIGINS` | Same exact origin; if unset, the launcher uses `WEB_ORIGIN`. |
| `APP_ENV`, `NODE_ENV`, `M3_BACKEND` | Launcher enforces `production`, `production`, `postgres`. |
| `API_URL` | Launcher enforces `http://127.0.0.1:8000`; never the public MiniLM endpoint. |

For per-visitor rate limits, verify how Replit's load balancer sanitizes/appends
`X-Forwarded-For` on the deployed domain, using platform documentation or support
and controlled requests (including a deliberately supplied header). If exactly one
trusted proxy appends the client address, set `TRUSTED_PROXY_HOPS=1`; use the verified
count for another topology. Do not infer trust from an arbitrary header or guess a
larger count: clients can supply the entries to its left. Keep the default `0` until
verified; with the private API this means visitors share a rate-limit bucket,
including the login-attempt limit. A shared proxy secret alone does not enable
per-visitor limits. Recheck the count when adding a proxy or changing domains.

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

After production is reachable, put its externally accessible connection string in
GitHub's `TREND_DATABASE_URL` secret and follow the
[MiniLM deployment handoff](../src/pipelines/trends/runpod/DEPLOYMENT_HANDOFF.md).
GitHub Actions cannot reach the private development hostname `helium`.

References: [Replit configuration](https://docs.replit.com/pt/references/project-setup/configuration),
[production database lifecycle](https://docs.replit.com/features/data-and-storage/development-and-production).
