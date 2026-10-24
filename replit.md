# Adept

Career matching and personalised reskilling, with personal, employee, and organisation workspaces.

## Framework and scope

- Keep the original Next.js app. The user explicitly chose Next.js over a Vite conversion.
- Do not publish this project. The user's friend is preparing publication from their own Replit account.
- Preserve the existing Python/FastAPI backend and PostgreSQL schema; do not rewrite business logic for the workspace scaffold.

## Run

Use the managed workflows:

- `artifacts/adept: web` â€” original Next.js app, including server components, server actions, and BFF routes.
- `artifacts/api-server: API Server` â€” Express entry point supervising the imported FastAPI process.

The web service uses its assigned `PORT` and binds to `0.0.0.0`. Next.js calls FastAPI internally at port 8000. Public `/api/v1` and `/api/healthz` routes belong to the API service; other `/api/*` routes belong to Next.js.

## Files

- `artifacts/adept/` â€” original web source, translations, Next config.
- `artifacts/api-server/python/src/` â€” original API, pipelines, database migrations, reference data.
- `.migration-backup/` â€” preserved import, excluded from deployment.
- `pyproject.toml` / `uv.lock` â€” Python dependencies.

## Checks

- `pnpm --filter @workspace/adept run build` â€” production build and TypeScript.
- `pnpm --filter @workspace/api-server run build` â€” API supervisor build.

Development database migrations and reference seeding were applied from the imported project. Database contents and secrets do not transfer simply by copying files to a friend's account; that account needs its own configured database, reference data and `SESSION_SECRET`. No production database migration should run automatically at app startup.

## Environment

Required: `DATABASE_URL`, `SESSION_SECRET`, `PROXY_SHARED_SECRET`, and a verified positive `TRUSTED_PROXY_HOPS`. Optional external model credentials remain optional; Adi defaults to the original built-in guide.

`WEB_ORIGIN` may pin the public origin; if unset, web request handlers use proxy-forwarded origin headers. Production must run Next.js as a server, not as static files.

## Publishing handoff

- Keep the existing Autoscale application router and artifact production commands. The sample root commands `src/scripts/replit.py` and `src/scripts/dev.py` are not in this workspace; production configuration belongs in each artifact's `.replit-artifact/artifact.toml`.
- In the friend's Replit copy, use Replit-managed PostgreSQL. Replit provisions `DATABASE_URL`; do not set that runtime-managed value manually.
- Before publishing that copy, apply SQL migrations and reference data to its **development** database:
  `cd artifacts/api-server/python && python src/db/migrate.py up && python src/db/seed.py`
- On the first publish, select **Autoscale** and enable **Set up your production database with your current development data** to copy the migrated schema and reference data. Review development records first because this option copies the development database's data too.
- Do not run the SQL migration script against the managed production database or from the deployment build/start command. Replit's publish flow handles managed production schema changes.
- Add a new random `SESSION_SECRET` (32+ characters) and a `PROXY_SHARED_SECRET` to the friend's production Secrets. The same proxy secret must be available to both web and API services. Set `TRUSTED_PROXY_HOPS` only after verifying the actual forwarding chain to each public service; production rejects zero, missing and malformed counts. Do not guess a value. Secrets in this workspace do not transfer to the friend's account.
- After the published hostname is known, set `CORS_ORIGINS` to that exact HTTPS origin with no trailing slash. `WEB_ORIGIN` can remain unset; the app derives it from forwarded request headers. `API_URL` and service ports are configured by the artifact settings, not by replacing them with `localhost` or port `3000`.
- The Runpod/Gemini model settings are configured for production. Add `RUNPOD_API_KEY` and `GEMINI_API_KEY` to the friend's production Secrets to enable that optional assistant setup; those credentials are not present in this workspace.

## Repository checks and scheduled data

Active workflows are restored at `.github/workflows`, with Python commands using
`artifacts/api-server/python` and pnpm commands using the workspace root. Run
`uv run --frozen python src/scripts/dev.py check`, `pnpm test:proxy`, and `pnpm build`.
The manual MiniLM publisher retains its main/source-repository guard and uses the
Python artifact as its Docker build context. The archive is not an active application.
