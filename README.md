# Adept

Adept connects skills profiles, AI/job-market evidence, explainable role matching and
personalised learning pathways. Personal, employee, employer and institution workspaces use
the same FastAPI engine. People make their own career and learning decisions.

## Workspace layout

- `artifacts/adept/`: Next.js web app, server actions and same-origin API routes.
- `artifacts/api-server/`: public Express API proxy and private FastAPI supervisor.
- `artifacts/api-server/python/src/`: Python API, pipelines, migrations and public reference data.
- `artifacts/api-server/python/tests/`: the original regression suite, running against active source.
- `.github/workflows/`: active CI, weekly public-source checks, weekly trend refresh and manual MiniLM publication.
- `.migration-backup/`: historical import only; excluded from deployment and active checks.

## Development and checks

Use Python 3.11, Node.js 24 and the pinned pnpm version:

```bash
uv sync --frozen
corepack pnpm install --frozen-lockfile
uv run --frozen python src/scripts/dev.py check
corepack pnpm test:proxy
corepack pnpm build
```

For a full local workspace build, also set `PORT=3000` and `BASE_PATH=/` for the
Replit mockup sandbox configuration. The production artifact builds receive their own ports.

The compatibility `src/scripts/dev.py` entry point runs the relocated quality gate. It checks
Python lint/format, ESLint, translations, unit tests, TypeScript and generated OpenAPI types.
CI additionally checks proxy requests, database upgrades and the guarded worker publisher.
Replit Preview and Publishing use the artifact commands documented in [replit.md](replit.md).

For a local PostgreSQL development database, the optional Compose configuration is in
`artifacts/api-server/python/docker-compose.yml`; set a local `POSTGRES_PASSWORD` first.
Do not run migrations or seed loading against an existing production database without the
database owner's deployment procedure. Public and synthetic reference data only.

## Production proxy configuration

Set `DATABASE_URL`, a stable `SESSION_SECRET` of at least 32 characters, and
`PROXY_SHARED_SECRET` in the hosting platform's production secrets. Web and API services must
receive the same proxy secret. Never commit `.env` files or session-signing material.

Set `TRUSTED_PROXY_HOPS` to the **verified positive number of trusted forwarding proxies**
in front of each public service. No count is guessed or hard-coded in artifact settings.
Check the platform's sanitization/appending of `X-Forwarded-For`, including a deliberately
supplied client header and every route to each service. A larger guessed count permits
spoofing; zero merges visitors into the server's rate-limit bucket. Production startup now
fails for missing/invalid proxy configuration. Development may use zero for direct sockets.

The public proxy discards supplied `X-Real-IP` and `X-Internal-Proxy-Secret`, derives the
trusted client address, and attaches its own secret. CORS origin/preflight headers continue
to FastAPI, which remains the authority for the configured CORS policy. Web requests use
the equivalent trusted-hop selection for private API calls.

## Public data and MiniLM

Scheduled trend refreshes use arXiv AI research and the existing BLS labour baseline, invoking
`sentence-transformers/all-MiniLM-L6-v2` on RunPod for 384-dimensional embeddings. The model
revision is pinned; deterministic scoring and catalogue validation precede publication.
The API serves saved snapshots. Adi optionally uses RunPod GLM-5.3 with Gemini fallbacks;
Gemini skill suggestions are separately configured. Providers are disclosed in the app's
About page; absent optional credentials retain deterministic/built-in behaviour.

The worker source and its updated build instructions are in
[the MiniLM handoff](artifacts/api-server/python/src/pipelines/trends/runpod/DEPLOYMENT_HANDOFF.md).
GitHub Actions reads `TREND_DATABASE_URL` and `TRENDS_RUNPOD_API_KEY` secrets plus the
`TRENDS_RUNPOD_ENDPOINT_ID` variable. They are distinct from the optional Adi credentials.
Only a reviewed manual dispatch on the source repository's `main` can publish the image to
`ghcr.io/pecel-lelele/adept-minilm`. Updating dependencies requires rebuilding that image and
redeploying RunPod separately; this PR does not publish images or change the live endpoint.

See [decisions](docs/decisions.md) for design and validation records.
