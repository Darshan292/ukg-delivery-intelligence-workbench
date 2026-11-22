# Backend

FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic, sync, pg8000 driver. Fictional data only.
The schema is the D3 model (relationship-model rev 2.1), created by migration 0002.

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

## Database roles and review

- Two URLs. The **owner** (`tracer` in dev) runs `alembic upgrade head` and `python -m app.seed`
  and owns every table. The **API** connects as a member of the group role `wb_review`
  (`wb_api_dev` in dev; `scripts/dev.sh` creates it). `wb_ingest` is the ingestion role.
  Migration 0002 creates both group roles; login members are created by `dev.sh` and by the
  test fixtures. Migration 0002 is not downgradable: drop and recreate a dev database after
  editing it.
- Only a human reviewer can accept or reject: privileges, constraint triggers and the API all
  check it (triggers raise SQLSTATE `WB002`; append-only is `WB001`; other model rules `WB003`).
- Review is **off by default**. To enable it for a local demo, set `REVIEWER_TOKEN` (32+
  characters) and `REVIEWER_ACTOR_ID` (2 is the seeded fictional reviewer), then send
  `Authorization: Bearer <token>`. The actor comes from the server setting, never the body.
- Tests connect as the app roles, not the owner, so a missing grant fails a test.
