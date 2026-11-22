# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test fixtures.

DB path 1: TEST_DATABASE_URL points at a running server (e.g. scripts/pg-local.sh url);
a throwaway database is created and dropped per session.
DB path 2: otherwise pytest-postgresql starts a local server (needs pg_ctl, non-root).
Set REQUIRE_DB_TESTS=1 (CI) so that a missing Postgres fails instead of skipping.
"""

import os
import secrets
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Final

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import create_app
from tests.db_helpers import client_for, truncate
from tests.pg_locate import find_pg_ctl


def _no_db(reason: str) -> None:
    if os.environ.get("REQUIRE_DB_TESTS") == "1":
        pytest.fail(reason)
    pytest.skip(reason)


def _admin_url(request: pytest.FixtureRequest) -> URL:
    env = os.environ.get("TEST_DATABASE_URL")
    if env:
        return make_url(env)
    pg_ctl = find_pg_ctl()
    if pg_ctl is None:
        _no_db("pg_ctl not found: install PostgreSQL or set TEST_DATABASE_URL")
    else:
        request.config.option.postgresql_exec = pg_ctl  # the plugin's default path rarely exists
    proc = request.getfixturevalue("postgresql_proc")
    return URL.create(
        "postgresql+pg8000",
        username=proc.user,
        password=proc.password or None,
        host=proc.host,
        port=proc.port,
        database="postgres",
    )


@pytest.fixture(scope="session")
def db_url(request: pytest.FixtureRequest) -> Iterator[URL]:
    admin = _admin_url(request)
    name = f"t_{uuid.uuid4().hex[:12]}"
    eng = create_engine(admin, isolation_level="AUTOCOMMIT")
    with eng.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    yield admin.set(database=name)
    with eng.connect() as c:
        c.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    eng.dispose()


@pytest.fixture
def db_engine(db_url: URL) -> Iterator[Engine]:
    eng = create_engine(db_url)
    yield eng
    eng.dispose()


@pytest.fixture
def client(db_engine: Engine) -> Iterator[TestClient]:
    app = create_app()

    def _session() -> Iterator[Session]:
        with Session(db_engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    yield TestClient(app)


ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def migrated_url(db_url: URL) -> URL:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.attributes["url"] = db_url.render_as_string(hide_password=False)
    command.upgrade(cfg, "head")
    return db_url


APP_ROLES: Final = ("wb_ingest", "wb_review")


@pytest.fixture(scope="session")
def role_urls(migrated_url: URL) -> Iterator[dict[str, URL]]:
    """Throwaway LOGIN members of the group roles; tests connect AS the app role, not the owner."""
    pw, tag = secrets.token_hex(16), uuid.uuid4().hex[:8]
    logins = {g: f"{g}_t{tag}" for g in APP_ROLES}  # unique per session
    eng = create_engine(migrated_url, isolation_level="AUTOCOMMIT")
    with eng.connect() as c:
        for (
            g,
            login,
        ) in logins.items():  # constants plus hex: no injection
            c.execute(text(f"CREATE ROLE {login} LOGIN PASSWORD '{pw}' IN ROLE {g}"))  # noqa: S608
    yield {g: migrated_url.set(username=login, password=pw) for g, login in logins.items()}
    with eng.connect() as c:
        for login in logins.values():
            c.execute(text(f"DROP ROLE IF EXISTS {login}"))
    eng.dispose()


@pytest.fixture
def ingest_engine(role_urls: dict[str, URL]) -> Iterator[Engine]:
    eng = create_engine(role_urls["wb_ingest"])
    yield eng
    eng.dispose()


@pytest.fixture
def review_engine(role_urls: dict[str, URL]) -> Iterator[Engine]:
    eng = create_engine(role_urls["wb_review"])
    yield eng
    eng.dispose()


@pytest.fixture
def store(migrated_url: URL) -> Iterator[Engine]:
    """Owner engine over empty tables."""
    eng = create_engine(migrated_url)
    truncate(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def graph_client(store: Engine, review_engine: Engine) -> TestClient:
    """Tracer seed saved as the owner; the app is served as a wb_review member (least privilege)."""
    from app.seed import seed_tracer_graph

    with store.begin() as c:
        seed_tracer_graph(c)
    return client_for(review_engine)
