# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Helpers for tests that talk to Postgres. FICTIONAL data only."""

import importlib.util
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db import get_session, sqlstate
from app.domain.records import Records
from app.main import create_app
from app.store import ALL, save

_MIG = Path(__file__).resolve().parent.parent / "migrations" / "versions" / "0002_d3_schema.py"


def _load_migration() -> Any:
    spec = importlib.util.spec_from_file_location("mig0002", _MIG)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TABLES: tuple[str, ...] = _load_migration().TABLES


@contextmanager
def sqlstate_raised(code: str | tuple[str, ...]) -> Generator[None]:
    codes = (code,) if isinstance(code, str) else code
    with pytest.raises(DBAPIError) as e:
        yield
    assert sqlstate(e.value) in codes, sqlstate(e.value)  # the code only, never the message


def truncate(engine: Engine) -> None:
    """As the owner: append-only triggers do not cover TRUNCATE, and app roles never hold it."""
    with engine.begin() as c:
        c.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY"))


def norm(r: Records) -> dict[str, Any]:
    """Comparable form of Records: `at` is database-assigned; catalogue types come back by name."""
    d = r.model_dump(exclude={"review_events": {"__all__": {"at"}}})
    for cat in d["catalogues"]:
        cat["entity_types"] = sorted(cat["entity_types"], key=lambda t: t["name"])
        cat["relationship_types"] = sorted(cat["relationship_types"], key=lambda t: t["name"])
    d["catalogues"] = sorted(d["catalogues"], key=lambda c: c["product_profile"])
    return d


def client_for(engine: Engine) -> TestClient:
    """The app served on `engine`; server errors become responses, as in production."""
    app = create_app()

    def _session() -> Iterator[Session]:
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    return TestClient(app, raise_server_exceptions=False)


@dataclass(frozen=True)
class Ids:
    reviewer: int
    service: int
    plain_human: int  # a human without the reviewer role
    s1: int
    s2: int
    scoped_rel: int  # uses A->B (cfg is snapshot-scoped)
    succ_rel: int  # uses A->C
    back_rel: int  # uses B->A
    unscoped_rel: int  # implements A->Q (req is not scoped)
    scoped_claim: int
    unscoped_claim: int
    export_dv: int  # export of s1
    design_dv: int
    export_locator: int
    design_locator: int
    s2_export_dv: int


def has_supersession_cycle(r: Records) -> bool:
    """Per scope (unscoped is its own scope), over every superseded event: a directed cycle."""
    graph: dict[tuple[int | None, int], set[int]] = {}
    for e in r.review_events:
        if e.target_kind == "relationship" and e.successor_relationship_id is not None:
            graph.setdefault((e.scope_snapshot_id, e.relationship_id), set()).add(
                e.successor_relationship_id
            )
    for start_scope, start in list(graph):
        seen: set[int] = set()
        todo = [start]
        while todo:
            for nxt in graph.get((start_scope, todo.pop()), ()):
                if nxt == start:
                    return True
                if nxt not in seen:
                    seen.add(nxt)
                    todo.append(nxt)
    return False


def save_as_roles(r: Records, owner: Engine, ingest: Engine, review: Engine) -> None:
    with owner.begin() as c:
        save(c, r, ("catalogues", "actors"))
    with ingest.begin() as c:
        save(c, r, tuple(f for f in ALL if f not in ("catalogues", "actors", "review_events")))
    with review.begin() as c:
        save(c, r, ("review_events",))


TOKEN = "t" * 40  # FICTIONAL test token, not a secret


def reviewer_client(engine: Engine, actor_id: int | None) -> TestClient:
    """The app on `engine` with review configured for `actor_id` (nothing read from the env)."""
    from pydantic import SecretStr

    from app.config import Settings, get_settings

    app = create_app()

    def _session() -> Iterator[Session]:
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        database_url=SecretStr("postgresql+pg8000://unused"),
        reviewer_token=SecretStr(TOKEN),
        reviewer_actor_id=actor_id,
    )
    return TestClient(
        app, raise_server_exceptions=False, headers={"Authorization": f"Bearer {TOKEN}"}
    )
