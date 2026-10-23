#!/usr/bin/env bash
# Reconcile declared dependencies only. Never migrate, seed, or refresh application data here.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export CI=true

for tool in uv node npx; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'Post-merge setup requires %s on PATH.\n' "$tool" >&2
    exit 1
  fi
done

# Match the development launcher, without creating an environment or invoking make setup.
if [[ -x .venv/bin/python ]]; then
  api_python="$PWD/.venv/bin/python"
else
  api_python="$(command -v python)"
fi

printf 'Installing declared API dependencies and pinned quality tools.\n'
uv pip install --python "$api_python" -r requirements.txt

package_manager="$(node -p "require('./src/web/package.json').packageManager")"
if [[ ! "$package_manager" =~ ^pnpm@[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  printf 'Expected a pinned pnpm version in src/web/package.json.\n' >&2
  exit 1
fi
printf 'Installing locked frontend dependencies.\n'
npx --yes "$package_manager" --dir src/web install --frozen-lockfile

printf 'Post-merge dependencies ready; database schema and data were not changed.\n'
