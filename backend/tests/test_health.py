# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import inspect
import logging
from collections.abc import Iterator

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import create_db_engine, get_session
from app.logging_config import JsonFormatter
from app.main import create_app


def test_health_returns_ok() -> None:
    r = TestClient(create_app()).get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_ok_with_db(client: TestClient) -> None:
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_ready_503_without_db() -> None:
    engine = create_db_engine("postgresql+pg8000://u:secretpw@127.0.0.1:1/none")
    app = create_app()

    def _session() -> Iterator[Session]:
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    c = TestClient(app)
    assert c.get("/health").status_code == 200
    r = c.get("/health/ready")
    assert r.status_code == 503
    assert r.json() == {"status": "unavailable"}
    low = r.text.lower()
    assert "postgresql" not in low
    assert "password" not in low
    assert "secretpw" not in low


def test_health_is_async() -> None:
    routes = [r for r in create_app().routes if isinstance(r, APIRoute) and r.path == "/health"]
    assert inspect.iscoroutinefunction(routes[0].endpoint)


def test_startup_enables_json_logging(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+pg8000://u:pw@127.0.0.1:1/x")
    from app.config import get_settings

    get_settings.cache_clear()
    saved = logging.getLogger().handlers[:]
    try:
        with TestClient(create_app()):
            assert isinstance(logging.getLogger().handlers[0].formatter, JsonFormatter)
    finally:
        logging.getLogger().handlers[:] = saved
        get_settings.cache_clear()
