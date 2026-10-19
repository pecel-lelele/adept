# All targets delegate to scripts/dev.py so they behave the same on macOS, Linux
# and Windows. Without `make`, run: uv run --no-project python scripts/dev.py <target>
PY ?= uv run --no-project python
DEV := $(PY) scripts/dev.py

.PHONY: help setup dev check lint format test typecheck contracts contracts-check db-up db-down db-migrate seed

help:            ## List targets
	@grep -E '^[a-z-]+:.*##' Makefile | sed 's/:.*##/ -/'

setup:           ## Install deps, create .env, start db, migrate, seed
	$(DEV) setup
dev:             ## Run API (:8000) and web (:3000) with reload
	$(DEV) dev
check:           ## Quality gate: lint, test, typecheck, contract drift
	$(DEV) check
lint:            ## ruff + eslint
	$(DEV) lint
format:          ## Auto-fix Python formatting and lint
	$(DEV) format
test:            ## pytest
	$(DEV) test
typecheck:       ## tsc --noEmit
	$(DEV) typecheck
contracts:       ## Regenerate openapi.json and web TS types from Pydantic contracts
	$(DEV) contracts
contracts-check: ## Regenerate contracts and fail if they changed
	$(DEV) contracts-check
db-up:           ## Start PostgreSQL + pgvector
	$(DEV) db-up
db-down:         ## Stop the database
	$(DEV) db-down
db-migrate:      ## Apply pending SQL migrations in db/migrations
	$(DEV) db-migrate
seed:            ## Load synthetic seed data from data/seed
	$(DEV) seed
