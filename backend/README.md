# Backend (tracer scaffold)

FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic, sync, pg8000 driver. Fictional data only.
The schema is a tracer subset that Slice 1 replaces.

## Setup

    cd backend
    uv sync

## Checks

    uv run ruff check . && uv run ruff format --check .
    uv run pyright
    uv run pytest

## Database for tests (pick one)

1. **pytest-postgresql** (default): starts its own server from local PostgreSQL binaries.
   Needs `pg_ctl` and a non-root user. With `REQUIRE_DB_TESTS=1` a missing Postgres fails
   the run instead of skipping.
2. **`TEST_DATABASE_URL`**: use a server you already run. A throwaway database is created and
   dropped per test session. For a local server (also works as root):

       ../scripts/pg-local.sh start
       TEST_DATABASE_URL=$(../scripts/pg-local.sh url) uv run pytest
       ../scripts/pg-local.sh stop

3. **Docker Compose**: `docker compose up -d --wait db` at the repo root, then
   `TEST_DATABASE_URL=postgresql+pg8000://tracer:tracer@127.0.0.1:5432/tracer uv run pytest`.
   The compose credentials are dev-only.

## Migrations

    DATABASE_URL=postgresql+pg8000://tracer:tracer@127.0.0.1:5432/tracer uv run alembic upgrade head
