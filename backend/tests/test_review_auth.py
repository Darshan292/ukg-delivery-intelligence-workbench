# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Reviewer identity for Milestone 1: a static bearer token mapped to one configured actor."""

from collections.abc import Callable, Iterator

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import SecretStr, ValidationError
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.domain.model import Actor
from app.main import create_app
from app.routes.review import require_reviewer
from app.store import save
from tests.domain.builders import World

Maker = Callable[[str | None, int | None], TestClient]
TOKEN = "t" * 40  # FICTIONAL test token, not a secret


def _settings(token: str | None, actor_id: int | None) -> Settings:
    return Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        database_url=SecretStr("postgresql+pg8000://unused"),
        reviewer_token=SecretStr(token) if token is not None else None,
        reviewer_actor_id=actor_id,
    )


@pytest.fixture
def make_client(store: Engine, review_engine: Engine) -> Iterator[Maker]:
    w = World()
    w.reviewer()  # actor 1
    w.service()  # actor 2
    plain = Actor(id=9, kind="human", display_name="Plain", roles=frozenset())
    # a service holding the role name: only the kind check refuses it
    svc_role = Actor(id=8, kind="service", display_name="Svc", roles=frozenset({"reviewer"}))
    with store.begin() as c:
        save(c, w.build().extended(actors=(plain, svc_role)))

    def make(token: str | None, actor_id: int | None) -> TestClient:
        app = create_app()

        @app.get("/_who")
        def who(actor: int = Depends(require_reviewer)) -> dict[str, int]:  # noqa: B008
            return {"actor": actor}

        def _session() -> Iterator[Session]:
            with Session(review_engine) as s:
                yield s

        app.dependency_overrides[get_session] = _session
        app.dependency_overrides[get_settings] = lambda: _settings(token, actor_id)
        return TestClient(app, raise_server_exceptions=False)

    yield make


def _get(make: Maker, token: str | None, actor: int | None, auth: str | None) -> Response:
    client = make(token, actor)
    return client.get("/_who", headers={"Authorization": auth} if auth is not None else {})


@pytest.mark.parametrize("token,actor", [(None, 1), (TOKEN, None), (None, None)])
def test_unconfigured_is_503(make_client: Maker, token: str | None, actor: int | None) -> None:
    r = _get(make_client, token, actor, f"Bearer {TOKEN}")
    assert r.status_code == 503


@pytest.mark.parametrize("auth", [None, "Basic " + TOKEN, "Bearer " + "x" * 40, "Bearer", TOKEN])
def test_missing_or_wrong_credentials_401(make_client: Maker, auth: str | None) -> None:
    r = _get(make_client, TOKEN, 1, auth)
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"
    assert TOKEN not in r.text
    if auth:
        assert auth not in r.text


@pytest.mark.parametrize("actor", [2, 8, 9, 999])  # service, human without the role, no such actor
def test_configured_actor_not_a_reviewer_is_403(make_client: Maker, actor: int) -> None:
    r = _get(make_client, TOKEN, actor, f"Bearer {TOKEN}")
    assert r.status_code == 403


def test_valid_token_returns_configured_actor(make_client: Maker) -> None:
    r = _get(make_client, TOKEN, 1, f"Bearer {TOKEN}")
    assert r.status_code == 200
    assert r.json() == {"actor": 1}


def test_short_token_rejected_without_echo() -> None:
    short = "short-secret-token"
    with pytest.raises(ValidationError) as e:
        _settings(short, 1)
    assert short not in str(e.value)


def test_review_is_off_by_default() -> None:
    s = Settings(_env_file=None, database_url=SecretStr("x"))  # pyright: ignore[reportCallIssue]
    assert s.reviewer_token is None and s.reviewer_actor_id is None
