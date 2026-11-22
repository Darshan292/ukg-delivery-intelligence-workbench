# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Relationship catalogue, profile and same_as rules, as wb_ingest."""

from sqlalchemy import Engine, text

from tests.db_helpers import Ids, sqlstate_raised

_REL = "INSERT INTO relationship VALUES (:id, :t, :s, :g, :q, now())"
_ENT = "INSERT INTO entity (id, product_profile, entity_type, natural_key) VALUES (:id, :p, :t, :k)"


def _rel(engine: Engine, id_: int, t: str, s: int, g: int, q: str | None = None) -> None:
    with engine.begin() as c:
        c.execute(text(_REL), {"id": id_, "t": t, "s": s, "g": g, "q": q})


def _ent(engine: Engine, id_: int, p: str, t: str, k: str) -> None:
    with engine.begin() as c:
        c.execute(text(_ENT), {"id": id_, "p": p, "t": t, "k": k})


def _owner(store: Engine, *sql: str) -> None:
    with store.begin() as c:
        for q in sql:
            c.execute(text(q))


def test_cross_profile_endpoints_fail(store: Engine, ingest_engine: Engine, world_ids: Ids) -> None:
    _owner(store, "INSERT INTO catalogue_entity_type VALUES ('ukg_pro_wfm','cfg',true,'{}')")
    _ent(ingest_engine, 60, "ukg_pro_wfm", "cfg", "P")
    with sqlstate_raised("WB003"):
        _rel(ingest_engine, 70, "uses", 1, 60)


def test_two_unknown_ends_fail_one_unknown_ok(ingest_engine: Engine, world_ids: Ids) -> None:
    _ent(ingest_engine, 61, "unknown", "x", "U1")
    _ent(ingest_engine, 62, "unknown", "x", "U2")
    with sqlstate_raised("WB003"):
        _rel(ingest_engine, 71, "uses", 61, 62)
    _rel(ingest_engine, 72, "uses", 1, 61)


def test_uncatalogued_type_fails(ingest_engine: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("WB003"):
        _rel(ingest_engine, 73, "nope", 1, 2)


def test_qualifier_rules(ingest_engine: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("WB003"):  # present where not required
        _rel(ingest_engine, 74, "uses", 3, 1, "q")
    with sqlstate_raised("WB003"):  # absent where required
        _rel(ingest_engine, 75, "asserts_value", 1, 2)
    _rel(ingest_engine, 76, "asserts_value", 1, 2, "q")


def test_same_as_key_order_is_byte_order(ingest_engine: Engine, world_ids: Ids) -> None:
    _ent(ingest_engine, 80, "synthetic", "cfg", "aa")
    _ent(ingest_engine, 81, "synthetic", "cfg", "Zz")
    with sqlstate_raised("WB003"):  # byte order: "Zz" (0x5A) sorts before "aa" (0x61)
        _rel(ingest_engine, 82, "same_as", 80, 81)
    _rel(ingest_engine, 83, "same_as", 81, 80)


def test_same_as_across_types_fails(ingest_engine: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("WB003"):  # A (cfg) -> Q (req)
        _rel(ingest_engine, 84, "same_as", 1, 4)
