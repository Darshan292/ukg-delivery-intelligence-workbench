# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine import URL

from app.db import sqlstate
from app.models import Base
from tests.db_helpers import TABLES, sqlstate_raised, truncate

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def migrated(db_engine: Engine, db_url: URL) -> Engine:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.attributes["url"] = db_url.render_as_string(hide_password=False)
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")  # idempotent: second run is a no-op
    return db_engine


@pytest.fixture
def base(migrated: Engine) -> Iterator[Engine]:
    """Owner engine with a small FICTIONAL world inserted by raw SQL (no triggers needed)."""
    truncate(migrated)
    with migrated.begin() as c:
        for sql in _BASE:
            c.execute(text(sql))
    yield migrated


_BASE = [
    "INSERT INTO actor VALUES (1,'service','svc','{}'), (2,'human','rev','{reviewer}')",
    "INSERT INTO catalogue_entity_type VALUES ('synthetic','cfg',true,'{}'),"
    " ('synthetic','req',false,'{}')",
    "INSERT INTO catalogue_relationship_type VALUES ('synthetic','uses',false,'[]'),"
    " ('synthetic','implements',false,'[]')",
    "INSERT INTO snapshot VALUES (1,'synthetic','dev','s1', now())",
    "INSERT INTO document VALUES (1,'synthetic','design')",
    "INSERT INTO document_version VALUES (1,1,repeat('a',64),NULL,NULL,1, now())",
    'INSERT INTO evidence_locator VALUES (1,1,\'xlsx_cell\',\'{"sheet":"S","cell":"A1"}\','
    "'FICTIONAL','x@1', now())",
    "INSERT INTO entity (id, product_profile, entity_type, natural_key) VALUES"
    " (1,'synthetic','cfg','A'), (2,'synthetic','cfg','B')",
    "INSERT INTO relationship VALUES (1,'uses',1,2,NULL, now())",
]


def test_sqlstate_reads_pg8000_code(migrated: Engine) -> None:
    with sqlstate_raised("22012"), migrated.connect() as c:
        c.execute(text("SELECT 1/0"))


def test_tracer_tables_gone_d3_tables_present(migrated: Engine) -> None:
    insp = inspect(migrated)
    assert set(insp.get_table_names()) == {*TABLES, "alembic_version"}
    assert "label" not in {c["name"] for c in insp.get_columns("entity")}
    assert "relationship_id" not in {c["name"] for c in insp.get_columns("evidence_locator")}


def test_models_match_migration(migrated: Engine) -> None:
    with migrated.connect() as conn:
        ctx = MigrationContext.configure(conn)
        assert compare_metadata(ctx, Base.metadata) == []


def test_downgrade_refused(db_url: URL) -> None:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.attributes["url"] = db_url.render_as_string(hide_password=False)
    command.upgrade(cfg, "head")
    with pytest.raises(RuntimeError, match="irreversible"):
        command.downgrade(cfg, "0001")


def test_relationship_key_nulls_not_distinct(base: Engine) -> None:
    with sqlstate_raised("23505"), base.begin() as c:
        c.execute(text("INSERT INTO relationship VALUES (2,'uses',1,2,NULL, now())"))


def test_key_columns_collate_c(base: Engine) -> None:
    with base.connect() as c:
        rows = c.execute(
            text(
                "SELECT c.relname, a.attname, coll.collname FROM pg_attribute a"
                " JOIN pg_class c ON c.oid = a.attrelid"
                " JOIN pg_collation coll ON coll.oid = a.attcollation"
                " WHERE c.relname = ANY(:t) AND a.attname = ANY(:n)"
            ),
            {
                "t": [
                    "entity",
                    "relationship",
                    "catalogue_entity_type",
                    "catalogue_relationship_type",
                ],
                "n": ["natural_key", "entity_type", "type", "name"],
            },
        ).all()
    got = {(r[0], r[1]): r[2] for r in rows}
    assert got == {
        ("entity", "natural_key"): "C",
        ("entity", "entity_type"): "C",
        ("relationship", "type"): "C",
        ("catalogue_entity_type", "name"): "C",
        ("catalogue_relationship_type", "name"): "C",
    }


def test_entity_key_triple_unique(base: Engine) -> None:
    with sqlstate_raised("23505"), base.begin() as c:
        c.execute(
            text(
                "INSERT INTO entity (id, product_profile, entity_type, natural_key)"
                " VALUES (9,'synthetic','cfg','A')"
            )
        )
    with base.begin() as c:  # same key, other type; same key, other profile
        c.execute(
            text(
                "INSERT INTO entity (id, product_profile, entity_type, natural_key)"
                " VALUES (9,'synthetic','req','A'), (10,'unknown','cfg','A')"
            )
        )


def test_entity_type_must_be_catalogued(base: Engine) -> None:
    with sqlstate_raised("23503"), base.begin() as c:
        c.execute(
            text(
                "INSERT INTO entity (id, product_profile, entity_type, natural_key)"
                " VALUES (9,'synthetic','nope','Z')"
            )
        )
    with base.begin() as c:
        c.execute(
            text(
                "INSERT INTO entity (id, product_profile, entity_type, natural_key)"
                " VALUES (9,'unknown','nope','Z')"
            )
        )


_CLAIM: dict[str, Any] = {
    "basis": "explicit_source", "method": "m@1", "conf": None, "model": None, "prompt": None,
}  # fmt: skip


@pytest.mark.parametrize(
    "over",
    [
        {"conf": "0.5"},  # explicit claim with confidence
        {"basis": "deterministic_rule"},  # rule claim without confidence
        {"basis": "deterministic_rule", "conf": "1.5"},
        {"basis": "llm_suggestion", "conf": "0.5", "prompt": "p1"},  # llm without model_id
        {"basis": "deterministic_rule", "conf": "0.5", "model": "m"},  # rule with model_id
        {"method": "m"},  # not name@ver
    ],
)
def test_claim_checks(base: Engine, over: dict[str, Any]) -> None:
    p = {**_CLAIM, **over}
    with sqlstate_raised("23514"), base.begin() as c:
        c.execute(
            text(
                "INSERT INTO claim VALUES (1,1,:basis,'present',:method,CAST(:conf AS numeric),"
                ":model,:prompt,NULL,'{1}','h', now())"
            ),
            p,
        )


@pytest.mark.parametrize(
    "sql",
    [
        # claim target with accepted
        "(target_kind, claim_id, verdict, reason, actor_id) VALUES ('claim',1,'accepted','r',2)",
        # claim target with a scope
        "(target_kind, claim_id, scope_snapshot_id, verdict, reason, actor_id)"
        " VALUES ('claim',1,1,'rejected','r',2)",
        # relationship rejected without reason
        "(target_kind, relationship_id, scope_snapshot_id, verdict, actor_id)"
        " VALUES ('relationship',1,1,'rejected',2)",
        # superseded without successor
        "(target_kind, relationship_id, scope_snapshot_id, verdict, reason, actor_id)"
        " VALUES ('relationship',1,1,'superseded','r',2)",
        # successor equal to self
        "(target_kind, relationship_id, scope_snapshot_id, verdict, reason,"
        " successor_relationship_id, actor_id)"
        " VALUES ('relationship',1,1,'superseded','r',1,2)",
        # blank reason
        "(target_kind, relationship_id, scope_snapshot_id, verdict, reason, actor_id)"
        " VALUES ('relationship',1,1,'rejected','  ',2)",
        # both target ids set
        "(target_kind, claim_id, relationship_id, verdict, reason, actor_id)"
        " VALUES ('claim',1,1,'rejected','r',2)",
    ],
)
def test_review_event_shape_checks(base: Engine, sql: str) -> None:
    with base.begin() as c:  # a claim to point at (the placeholder hash is fine here)
        c.execute(
            text(
                "INSERT INTO claim VALUES (1,1,'explicit_source','present','m@1',NULL,"
                "NULL,NULL,NULL,'{1}','h', now())"
            )
        )
    with sqlstate_raised("23514"), base.begin() as c:
        c.execute(text(f"INSERT INTO review_event {sql}"))


def test_document_version_self_supersede_and_single_successor(base: Engine) -> None:
    with sqlstate_raised("23514"), base.begin() as c:
        c.execute(text("INSERT INTO document_version VALUES (5,1,repeat('b',64),NULL,5,2, now())"))
    with base.begin() as c:
        c.execute(text("INSERT INTO document_version VALUES (2,1,repeat('c',64),NULL,1,2, now())"))
    with sqlstate_raised("23505"), base.begin() as c:
        c.execute(text("INSERT INTO document_version VALUES (3,1,repeat('d',64),NULL,1,2, now())"))


def test_sqlstate_none_for_non_server_error() -> None:
    from sqlalchemy.exc import DBAPIError

    assert sqlstate(DBAPIError("s", None, Exception("x"))) is None
