# Adept

Career matching and personalised reskilling, with personal, employee, and organisation workspaces.

## Framework and scope

- Keep the original Next.js app. The user explicitly chose Next.js over a Vite conversion.
- Do not publish this project. The user's friend is preparing publication from their own Replit account.
- Preserve the existing Python/FastAPI backend and PostgreSQL schema; do not rewrite business logic for the workspace scaffold.

## Run

Use the managed workflows:

- `artifacts/adept: web` — original Next.js app, including server components, server actions, and BFF routes.
- `artifacts/api-server: API Server` — Express entry point supervising the imported FastAPI process.

The web service uses its assigned `PORT` and binds to `0.0.0.0`. Next.js calls FastAPI internally at port 8000. Public `/api/v1` and `/api/healthz` routes belong to the API service; other `/api/*` routes belong to Next.js.

## Files

- `artifacts/adept/` — original web source, translations, Next config.
- `artifacts/api-server/python/src/` — original API, pipelines, database migrations, reference data.
- `.migration-backup/` — preserved import, excluded from deployment.
- `pyproject.toml` / `uv.lock` — Python dependencies.

## Checks

- `pnpm --filter @workspace/adept run build` — production build and TypeScript.
- `pnpm --filter @workspace/api-server run build` — API supervisor build.

Development database migrations and reference seeding were applied from the imported project. Database contents and secrets do not transfer simply by copying files to a friend's account; that account needs its own configured database, reference data and `SESSION_SECRET`. No production database migration should run automatically at app startup.

## Environment

Required: `DATABASE_URL`, `SESSION_SECRET`. Optional external model credentials remain optional; Adi defaults to the original built-in guide.

`WEB_ORIGIN` may pin the public origin; if unset, web request handlers use proxy-forwarded origin headers. Production must run Next.js as a server, not as static files.
