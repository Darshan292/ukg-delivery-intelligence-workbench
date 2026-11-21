# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
#
# Developer entry points. `make help` lists them.
.DEFAULT_GOAL := help
.PHONY: help db-up db-down migrate seed dev dev-local test lint e2e

DB_URL := postgresql+pg8000://tracer:tracer@127.0.0.1:5432/tracer

help: ## List targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

db-up: ## Start the Postgres container
	docker compose up -d --wait db

db-down: ## Stop the Postgres container
	docker compose down

migrate: ## Apply migrations (DATABASE_URL, default: the Docker db)
	cd backend && DATABASE_URL=$${DATABASE_URL:-$(DB_URL)} uv run alembic upgrade head

seed: ## Load the fictional seed data (DATABASE_URL, default: the Docker db)
	cd backend && DATABASE_URL=$${DATABASE_URL:-$(DB_URL)} uv run python -m app.seed

dev: ## Docker db, migrate, seed, backend :8000, frontend :3000
	MODE=docker bash scripts/dev.sh

dev-local: ## Same as dev, with a local Postgres instead of Docker
	MODE=local bash scripts/dev.sh

test: ## Backend pytest and frontend vitest
	cd backend && if docker info >/dev/null 2>&1; then uv run pytest; \
	  else bash ../scripts/pg-local.sh start >/dev/null && TEST_DATABASE_URL=$$(bash ../scripts/pg-local.sh url) uv run pytest; fi
	cd frontend && npm test

lint: ## ruff, pyright, eslint, tsc
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run pyright
	cd frontend && npm run lint && npm run typecheck

e2e: ## Start the stack, run Playwright, tear down
	bash scripts/e2e.sh
