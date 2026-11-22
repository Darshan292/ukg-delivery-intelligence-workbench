# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Claim scope, server-side locator_set_hash, dedup and entity-version rules, as wb_ingest."""

import hashlib

from sqlalchemy import Engine, text

from tests.db_helpers import Ids, sqlstate_raised

_CLAIM = (
    "INSERT INTO claim (id, relationship_id, basis, polarity, method, scope_snapshot_id,"
    " locator_ids, locator_set_hash, created_at) VALUES (:id, :rel, 'explicit_source', 'present',"
    " 'm2@1', :scope, CAST(:ids AS bigint[]), :h, now())"
)
_EV = (
    "INSERT INTO entity_version VALUES (:id, :e, :dv, :snap, CAST('[]' AS jsonb),"
    " CAST(:ids AS bigint[]))"
)


def _claim(
    engine: Engine, id_: int, rel: int, scope: int | None, ids: list[int], h: str = "x"
) -> None:
    with engine.begin() as c:
        c.execute(text(_CLAIM), {"id": id_, "rel": rel, "scope": scope, "ids": ids, "h": h})


def _ev(engine: Engine, id_: int, e: int, dv: int, snap: int | None, ids: list[int]) -> None:
    with engine.begin() as c:
        c.execute(text(_EV), {"id": id_, "e": e, "dv": dv, "snap": snap, "ids": ids})


# world: locators 1 (export s1, scoped claim), 2 (design), 3 and 4 (export s1)


def test_same_claim_twice_rejected(ingest_engine: Engine, world_ids: Ids) -> None:
    _claim(ingest_engine, 20, world_ids.scoped_rel, world_ids.s1, [3, 4])
    with sqlstate_raised("23505"):
        _claim(ingest_engine, 21, world_ids.scoped_rel, world_ids.s1, [3, 4])


def test_reordered_locators_still_duplicate(ingest_engine: Engine, world_ids: Ids) -> None:
    _claim(ingest_engine, 20, world_ids.scoped_rel, world_ids.s1, [3, 4])
    with sqlstate_raised("23505"):
        _claim(ingest_engine, 21, world_ids.scoped_rel, world_ids.s1, [4, 3])


def test_hash_is_server_computed(ingest_engine: Engine, world_ids: Ids) -> None:
    _claim(ingest_engine, 20, world_ids.scoped_rel, world_ids.s1, [4, 3], h="bogus")
    with ingest_engine.connect() as c:
        row = c.execute(text("SELECT locator_ids, locator_set_hash FROM claim WHERE id = 20")).one()
    assert row.locator_ids == [3, 4]
    assert row.locator_set_hash == hashlib.sha256(b"3,4").hexdigest()


def test_repeated_or_missing_locator_fails(ingest_engine: Engine, world_ids: Ids) -> None:
    for n, ids in enumerate(([3, 3], [999], []), start=30):
        with sqlstate_raised("WB003"):
            _claim(ingest_engine, n, world_ids.scoped_rel, world_ids.s1, ids)


def test_mixed_scope_locators_fail(ingest_engine: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("WB003"):  # one export locator, one design locator
        _claim(ingest_engine, 20, world_ids.scoped_rel, world_ids.s1, [3, 2])


def test_scope_must_match_locators(ingest_engine: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("WB003"):
        _claim(ingest_engine, 20, world_ids.scoped_rel, None, [3])


def test_duplicate_locator_content_rejected(ingest_engine: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("23505"), ingest_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO evidence_locator VALUES (90, :dv, 'xlsx_cell',"
                ' CAST(\'{"sheet": "S", "cell": "A1"}\' AS jsonb),'
                " 'other', 'openpyxl@1', now())"
            ),
            {"dv": world_ids.export_dv},
        )


def test_entity_version_unique_and_rules(
    store: Engine, ingest_engine: Engine, world_ids: Ids
) -> None:
    i = world_ids
    _ev(ingest_engine, 1, 2, i.design_dv, None, [i.design_locator])
    with sqlstate_raised("23505"):  # same (entity, document version)
        _ev(ingest_engine, 2, 2, i.design_dv, None, [i.design_locator])
    with sqlstate_raised("WB003"):  # snapshot differs from its version's
        _ev(ingest_engine, 3, 1, i.export_dv, None, [3])
    with sqlstate_raised("WB003"):  # locator belongs to another version
        _ev(ingest_engine, 4, 1, i.design_dv, None, [3])
    with sqlstate_raised("WB003"):  # no locators
        _ev(ingest_engine, 5, 1, i.design_dv, None, [])
    with store.begin() as c:
        c.execute(text("INSERT INTO catalogue_entity_type VALUES ('ukg_pro_wfm','cfg',true,'{}')"))
    with ingest_engine.begin() as c:
        c.execute(
            text("INSERT INTO entity (id, product_profile, entity_type, natural_key)"
                 " VALUES (60, 'ukg_pro_wfm', 'cfg', 'P')")
        )  # fmt: skip
    with sqlstate_raised("WB003"):  # a ukg_pro_wfm entity in a synthetic document
        _ev(ingest_engine, 6, 60, i.design_dv, None, [i.design_locator])
