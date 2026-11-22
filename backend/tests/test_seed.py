# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import uuid

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL

from app.seed import build_tracer_records, ensure_dev_login, seed_tracer_graph
from app.store import load
from tests.db_helpers import TABLES

EXPECTED = {
    "actor": 2,
    "catalogue_entity_type": 3,
    "catalogue_relationship_type": 2,
    "snapshot": 0,
    "document": 1,
    "document_version": 1,
    "evidence_locator": 2,
    "entity": 3,
    "entity_version": 0,
    "relationship": 2,
    "claim": 2,
    "review_event": 0,
    "unresolved_reference": 0,
}


def _counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as c:
        return {t: c.scalar(text(f"SELECT count(*) FROM {t}")) or 0 for t in TABLES}  # noqa: S608


def test_seed_creates_expected_rows(store: Engine) -> None:
    with store.begin() as c:
        seed_tracer_graph(c)
    assert _counts(store) == EXPECTED


def test_seed_twice_is_idempotent(store: Engine) -> None:
    for _ in range(2):
        with store.begin() as c:
            seed_tracer_graph(c)
    assert _counts(store) == EXPECTED


def test_seed_is_synthetic_and_fictional(store: Engine) -> None:
    with store.begin() as c:
        seed_tracer_graph(c)
    with store.connect() as c:
        r = load(c)
    assert {x.product_profile for x in (*r.entities, *r.documents)} == {"synthetic"}
    assert all("FICTIONAL" in loc.snippet for loc in r.locators)


def test_seed_actor_2_is_a_human_reviewer_and_actor_1_is_not() -> None:
    r = build_tracer_records()
    assert r.actor_by_id[2].is_reviewer
    assert r.actor_by_id[1].kind == "service"


NEW_PW = "second_pw_5678"  # FICTIONAL dev-only value


def test_dev_login_is_a_wb_review_member_and_idempotent(store: Engine, migrated_url: URL) -> None:
    name = f"wb_dev_t{uuid.uuid4().hex[:8]}"
    try:
        for pw in ("first_pw_1234", NEW_PW):  # second run: ALTER, not CREATE
            with store.begin() as c:
                ensure_dev_login(c, name, pw)
        with store.connect() as c:
            assert c.scalar(text("SELECT pg_has_role(:n, 'wb_review', 'MEMBER')"), {"n": name})
            assert not c.scalar(text("SELECT pg_has_role(:n, 'wb_ingest', 'MEMBER')"), {"n": name})
        eng = create_engine(migrated_url.set(username=name, password=NEW_PW))  # noqa: S106
        with eng.connect() as c:
            assert c.scalar(text("SELECT 1")) == 1
        eng.dispose()
    finally:
        with store.begin() as c:
            c.execute(text(f"DROP ROLE IF EXISTS {name}"))  # noqa: S608


@pytest.mark.parametrize(
    "pw", ["short", "has space 12345", "q'uote_12345", "x" * 65, "ünïcode_1234"]
)
def test_dev_login_rejects_bad_password_without_echo(store: Engine, pw: str) -> None:
    with store.begin() as c, pytest.raises(ValueError) as e:
        ensure_dev_login(c, "wb_dev_never", pw)
    assert pw not in str(e.value)


def test_dev_login_rejects_bad_name(store: Engine) -> None:
    with store.begin() as c, pytest.raises(ValueError):
        ensure_dev_login(c, "x; DROP ROLE y", "good_pw_1234")
