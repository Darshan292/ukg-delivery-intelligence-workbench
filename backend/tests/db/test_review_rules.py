# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Scope, successor and supersession-cycle rules (DB half of invariant 6), as wb_review."""

from typing import Any

from sqlalchemy import Engine, text

from tests.db_helpers import Ids, sqlstate_raised

_EV = (
    "INSERT INTO review_event (target_kind, relationship_id, scope_snapshot_id, verdict, reason,"
    " successor_relationship_id, actor_id)"
    " VALUES ('relationship', :rel, :s, :v, :reason, :succ, :a)"
)


def _ev(
    i: Ids, rel: int, scope: int | None, v: str = "accepted", succ: int | None = None
) -> dict[str, Any]:
    return {"rel": rel, "s": scope, "v": v, "reason": None if v == "accepted" else "r",
            "succ": succ, "a": i.reviewer}  # fmt: skip


def _insert(engine: Engine, p: dict[str, Any]) -> None:
    with engine.begin() as c:
        c.execute(text(_EV), p)


def _sup(i: Ids, rel: int, succ: int, scope: int) -> dict[str, Any]:
    return _ev(i, rel, scope, "superseded", succ)


def test_scoped_verdict_without_snapshot_fails(review_engine: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("WB003"):
        _insert(review_engine, _ev(world_ids, world_ids.scoped_rel, None))
    _insert(review_engine, _ev(world_ids, world_ids.scoped_rel, world_ids.s1))  # control


def test_scoped_verdict_other_profile_snapshot_fails(
    store: Engine, review_engine: Engine, world_ids: Ids
) -> None:
    with store.begin() as c:
        c.execute(text("INSERT INTO snapshot VALUES (88, 'ukg_pro_wfm', 'dev', 'x', now())"))
    with sqlstate_raised("WB003"):
        _insert(review_engine, _ev(world_ids, world_ids.scoped_rel, 88))


def test_unscoped_verdict_with_snapshot_fails(review_engine: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("WB003"):
        _insert(review_engine, _ev(world_ids, world_ids.unscoped_rel, world_ids.s1))
    _insert(review_engine, _ev(world_ids, world_ids.unscoped_rel, None))  # control


def test_unknown_endpoint_counts_as_scoped(
    store: Engine, review_engine: Engine, world_ids: Ids
) -> None:
    with store.begin() as c:
        c.execute(text("INSERT INTO entity (id, product_profile, entity_type, natural_key)"
                       " VALUES (40, 'unknown', 'x', 'U')"))  # fmt: skip
        c.execute(text("INSERT INTO relationship VALUES (40, 'uses', 1, 40, NULL, now())"))
    with sqlstate_raised("WB003"):
        _insert(review_engine, _ev(world_ids, 40, None))
    _insert(review_engine, _ev(world_ids, 40, world_ids.s1))


def test_successor_must_share_source(review_engine: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("WB003"):  # A->B superseded by B->A
        _insert(
            review_engine, _sup(world_ids, world_ids.scoped_rel, world_ids.back_rel, world_ids.s1)
        )
    _insert(review_engine, _sup(world_ids, world_ids.scoped_rel, world_ids.succ_rel, world_ids.s1))


def test_supersession_cycle_fails_same_scope(
    store: Engine, review_engine: Engine, world_ids: Ids
) -> None:
    i = world_ids
    _insert(review_engine, _sup(i, i.scoped_rel, i.succ_rel, i.s1))
    with sqlstate_raised("WB003"):  # two-cycle
        _insert(review_engine, _sup(i, i.succ_rel, i.scoped_rel, i.s1))
    with store.begin() as c:  # a third relationship from A: three-cycle r1 -> r2 -> r3 -> r1
        c.execute(text("INSERT INTO entity (id, product_profile, entity_type, natural_key)"
                       " VALUES (41, 'synthetic', 'cfg', 'D')"))  # fmt: skip
        c.execute(text("INSERT INTO relationship VALUES (41, 'uses', 1, 41, NULL, now())"))
    _insert(review_engine, _sup(i, i.succ_rel, 41, i.s1))
    with sqlstate_raised("WB003"):
        _insert(review_engine, _sup(i, 41, i.scoped_rel, i.s1))


def test_supersession_other_scope_is_not_a_cycle(review_engine: Engine, world_ids: Ids) -> None:
    i = world_ids
    _insert(review_engine, _sup(i, i.scoped_rel, i.succ_rel, i.s1))
    _insert(review_engine, _sup(i, i.succ_rel, i.scoped_rel, i.s2))


def test_claim_target_skips_relationship_rules(review_engine: Engine, world_ids: Ids) -> None:
    with review_engine.begin() as c:
        c.execute(
            text("INSERT INTO review_event (target_kind, claim_id, verdict, reason, actor_id)"
                 " VALUES ('claim', :c, 'rejected', 'r', :a)"),
            {"c": world_ids.scoped_claim, "a": world_ids.reviewer},
        )  # fmt: skip
