# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Privileges of the two app roles. Every negative test has a positive control."""

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.engine import URL

from tests.db_helpers import Ids, sqlstate_raised

INGEST_INSERT = {
    "snapshot", "document", "document_version", "evidence_locator", "entity", "entity_version",
    "relationship", "claim", "unresolved_reference",
}  # fmt: skip
REVIEW_COLS = {
    "target_kind", "claim_id", "relationship_id", "scope_snapshot_id", "verdict", "reason",
    "successor_relationship_id", "actor_id",
}  # fmt: skip
PRIVS = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")
ACCEPT = text(
    "INSERT INTO review_event (target_kind, relationship_id, verdict, actor_id)"
    " VALUES ('relationship', :r, 'accepted', :a) RETURNING id, at"
)


def test_privilege_matrix(store: Engine, role_urls: dict[str, URL]) -> None:
    roles = {g: u.username for g, u in role_urls.items()}
    with store.connect() as c:
        tables = c.scalars(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        ).all()
        cols = c.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns"
                " WHERE table_schema = 'public'"
            )
        ).all()
        got_tab: set[tuple[str, str, str]] = set()
        got_col: set[tuple[str, str, str]] = set()
        for group, login in roles.items():
            for t in tables:
                for p in PRIVS:
                    if c.scalar(
                        text("SELECT has_table_privilege(:r, :t, :p)"),
                        {"r": login, "t": f"public.{t}", "p": p},
                    ):
                        got_tab.add((group, t, p))
            for t, col in cols:
                if c.scalar(
                    text("SELECT has_column_privilege(:r, :t, :c, 'INSERT')"),
                    {"r": login, "t": f"public.{t}", "c": col},
                ):
                    got_col.add((group, t, col))
    want_tab = {(g, t, "SELECT") for g in roles for t in tables}
    want_tab |= {("wb_ingest", t, "INSERT") for t in INGEST_INSERT - {"document_version"}}
    want_tab |= {("wb_review", "document_version", "INSERT")}
    assert got_tab == want_tab
    # column level: wb_ingest through its table grants, wb_review only the eight review columns
    # wb_ingest cannot name supersedes_version_id: lineage is a human act (wb_review only)
    want_col = {
        ("wb_ingest", t, col)
        for t, col in cols
        if t in INGEST_INSERT and (t, col) != ("document_version", "supersedes_version_id")
    }
    want_col |= {("wb_review", "review_event", col) for col in REVIEW_COLS}
    want_col |= {("wb_review", t, col) for t, col in cols if t == "document_version"}
    assert got_col == want_col


def test_review_role_positive_control(review_engine: Engine, world_ids: Ids) -> None:
    with review_engine.begin() as c:
        row = c.execute(ACCEPT, {"r": world_ids.unscoped_rel, "a": world_ids.reviewer}).one()
    assert row.id == 1 and row.at is not None


def test_ingest_role_cannot_insert_review_event(ingest_engine: Engine, world_ids: Ids) -> None:
    # the actor is a human reviewer, so the human-only trigger would not stop this: privileges do
    with sqlstate_raised("42501"), ingest_engine.begin() as c:
        c.execute(ACCEPT, {"r": world_ids.unscoped_rel, "a": world_ids.reviewer})


@pytest.mark.parametrize(
    "sql", ["UPDATE review_event SET reason = 'x'", "DELETE FROM review_event",
            "TRUNCATE review_event"]
)  # fmt: skip
def test_review_role_cannot_update_or_delete_review_event(review_engine: Engine, sql: str) -> None:
    with sqlstate_raised("42501"), review_engine.begin() as c:
        c.execute(text(sql))


def test_review_role_cannot_set_at(review_engine: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("42501"), review_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO review_event (target_kind, relationship_id, verdict, actor_id, at)"
                " VALUES ('relationship', :r, 'accepted', :a, '2001-01-01')"
            ),
            {"r": world_ids.unscoped_rel, "a": world_ids.reviewer},
        )


def test_review_role_cannot_set_id(review_engine: Engine, world_ids: Ids) -> None:
    # the rewriter may reject GENERATED ALWAYS (428C9) before the privilege check (42501)
    with sqlstate_raised(("42501", "428C9")), review_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO review_event (id, target_kind, relationship_id, verdict, actor_id)"
                " VALUES (500, 'relationship', :r, 'accepted', :a)"
            ),
            {"r": world_ids.unscoped_rel, "a": world_ids.reviewer},
        )


@pytest.mark.parametrize("role", ["ingest_engine", "review_engine"])
def test_app_roles_cannot_insert_actor(
    role: str, request: pytest.FixtureRequest, world_ids: Ids
) -> None:
    eng: Engine = request.getfixturevalue(role)
    with sqlstate_raised("42501"), eng.begin() as c:
        c.execute(text("INSERT INTO actor VALUES (500, 'human', 'forged', '{reviewer}')"))


@pytest.mark.parametrize("role", ["ingest_engine", "review_engine"])
@pytest.mark.parametrize(
    "sql", ["ALTER TABLE review_event DISABLE TRIGGER ALL", "CREATE TABLE x (i int)"]
)
def test_app_roles_cannot_disable_triggers_or_create(
    role: str, sql: str, request: pytest.FixtureRequest
) -> None:
    eng: Engine = request.getfixturevalue(role)
    with sqlstate_raised("42501"), eng.begin() as c:
        c.execute(text(sql))


def test_review_event_time_is_statement_time_not_transaction_start(
    review_engine: Engine, world_ids: Ids
) -> None:
    """A client holding a transaction open must not backdate (at, id) ordering to its start."""
    with review_engine.begin() as c:
        c.execute(text("SELECT pg_sleep(0.6)"))
        gap = c.scalar(
            text(
                "WITH e AS (INSERT INTO review_event (target_kind, relationship_id, verdict,"
                " actor_id) VALUES ('relationship', :r, 'accepted', :a) RETURNING at)"
                " SELECT extract(epoch FROM (SELECT at FROM e) - now())"
            ),
            {"r": world_ids.unscoped_rel, "a": world_ids.reviewer},
        )
    assert gap is not None and gap > 0.5


def test_every_function_pins_its_search_path(store: Engine) -> None:
    with store.connect() as c:
        rows = c.execute(
            text(
                "SELECT p.proname, coalesce(p.proconfig, '{}') FROM pg_proc p"
                " JOIN pg_namespace n ON n.oid = p.pronamespace"
                " WHERE n.nspname = 'public' AND p.proname LIKE 'wb\\_%'"
            )
        ).all()
    assert len(rows) >= 9
    for name, config in rows:
        assert "search_path=pg_catalog, public" in config, name
