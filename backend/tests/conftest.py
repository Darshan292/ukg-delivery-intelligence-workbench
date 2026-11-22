# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test fixtures.

DB path 1: TEST_DATABASE_URL points at a running server (e.g. scripts/pg-local.sh url);
a throwaway database is created and dropped per session.
DB path 2: otherwise pytest-postgresql starts a local server (needs pg_ctl, non-root).
Set REQUIRE_DB_TESTS=1 (CI) so that a missing Postgres fails instead of skipping.
"""

import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import create_app
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
