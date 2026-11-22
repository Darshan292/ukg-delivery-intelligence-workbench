# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Human-only review and lineage, enforced by constraint triggers (slice 5 done criterion)."""

from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import Engine, text

from tests.db_helpers import Ids, sqlstate_raised

_REL = (
    "INSERT INTO review_event (target_kind, relationship_id, scope_snapshot_id, verdict, reason,"
    " successor_relationship_id, actor_id)"
    " VALUES ('relationship', :rel, :s, :v, :reason, :succ, :a)"
)
_CLAIM = (
    "INSERT INTO review_event (target_kind, claim_id, verdict, reason, actor_id)"
    " VALUES ('claim', :claim, :v, 'r', :a)"
)


def _rel(
    v: str, reason: str | None, succ: bool
) -> Callable[[Ids, int], tuple[str, dict[str, Any]]]:
    def make(i: Ids, actor: int) -> tuple[str, dict[str, Any]]:
        return _REL, {"rel": i.scoped_rel, "s": i.s1, "v": v, "reason": reason,
                      "succ": i.succ_rel if succ else None, "a": actor}  # fmt: skip

    return make


def _claim(v: str) -> Callable[[Ids, int], tuple[str, dict[str, Any]]]:
    return lambda i, actor: (_CLAIM, {"claim": i.scoped_claim, "v": v, "a": actor})


CASES = {
    "accept": _rel("accepted", None, False),
    "reject": _rel("rejected", "r", False),
    "supersede": _rel("superseded", "r", True),
    "claim_reject": _claim("rejected"),
    "claim_reinstate": _claim("reinstated"),
}


def _count(engine: Engine) -> int:
    with engine.connect() as c:
        return c.scalar(text("SELECT count(*) FROM review_event")) or 0


def test_service_actor_insert_accept_fails(review_engine: Engine, world_ids: Ids) -> None:
    """Slice 5 done criterion: direct SQL, as the role that HOLDS the INSERT privilege."""
    with sqlstate_raised("WB002"), review_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO review_event (target_kind, relationship_id, scope_snapshot_id,"
                " verdict, actor_id) VALUES ('relationship', :r, :s, 'accepted', :a)"
            ),
            {"r": world_ids.scoped_rel, "s": world_ids.s1, "a": world_ids.service},
        )
    assert _count(review_engine) == 0


@pytest.mark.parametrize("case", CASES)
def test_service_actor_any_event_fails(review_engine: Engine, world_ids: Ids, case: str) -> None:
    sql, params = CASES[case](world_ids, world_ids.service)
    with sqlstate_raised("WB002"), review_engine.begin() as c:
        c.execute(text(sql), params)
    assert _count(review_engine) == 0


@pytest.mark.parametrize("case", CASES)
def test_same_cases_succeed_for_reviewer(review_engine: Engine, world_ids: Ids, case: str) -> None:
    sql, params = CASES[case](world_ids, world_ids.reviewer)
    with review_engine.begin() as c:
        c.execute(text(sql), params)
    assert _count(review_engine) == 1


def test_human_without_reviewer_role_fails(review_engine: Engine, world_ids: Ids) -> None:
    sql, params = CASES["accept"](world_ids, world_ids.plain_human)
    with sqlstate_raised("WB002"), review_engine.begin() as c:
        c.execute(text(sql), params)


@pytest.mark.parametrize("case", CASES)
def test_service_actor_holding_reviewer_role_fails(
    review_engine: Engine, world_ids: Ids, case: str
) -> None:
    """Only the `kind = 'human'` half of the check can refuse this actor."""
    sql, params = CASES[case](world_ids, world_ids.service_with_role)
    with sqlstate_raised("WB002"), review_engine.begin() as c:
        c.execute(text(sql), params)
    assert _count(review_engine) == 0


def test_constraint_trigger_not_deferrable(review_engine: Engine, world_ids: Ids) -> None:
    sql, params = CASES["accept"](world_ids, world_ids.service)
    with review_engine.connect() as c:
        c.execute(text("SET CONSTRAINTS ALL DEFERRED"))
        with sqlstate_raised("WB002"):  # at the statement, not at commit
            c.execute(text(sql), params)
        c.rollback()


_DV = (
    "INSERT INTO document_version (id, document_id, sha256, snapshot_id, supersedes_version_id,"
    " declared_by, uploaded_at) VALUES (:id, :doc, repeat(:h, 64), :snap, :sup, :by, now())"
)


def _doc_of(engine: Engine, dv: int) -> int:
    with engine.connect() as c:
        return c.scalar(text("SELECT document_id FROM document_version WHERE id = :d"), {"d": dv})  # type: ignore[return-value]


def _new_version(
    i: Ids, doc: int, by: int, snap: int | None = None, h: str = "e"
) -> dict[str, Any]:
    return {"id": 50, "doc": doc, "h": h, "snap": snap, "sup": i.design_dv, "by": by}


def test_lineage_by_service_actor_fails(ingest_engine: Engine, world_ids: Ids) -> None:
    doc = _doc_of(ingest_engine, world_ids.design_dv)
    with sqlstate_raised("WB002"), ingest_engine.begin() as c:
        c.execute(text(_DV), _new_version(world_ids, doc, world_ids.service))
    with ingest_engine.begin() as c:  # positive control: a human declarer is accepted
        c.execute(text(_DV), _new_version(world_ids, doc, world_ids.reviewer))


def test_lineage_other_document_or_snapshot_fails(ingest_engine: Engine, world_ids: Ids) -> None:
    other_doc = _doc_of(ingest_engine, world_ids.export_dv)
    with sqlstate_raised("WB003"), ingest_engine.begin() as c:
        c.execute(text(_DV), _new_version(world_ids, other_doc, world_ids.reviewer))
    doc = _doc_of(ingest_engine, world_ids.design_dv)
    with sqlstate_raised("WB003"), ingest_engine.begin() as c:  # design has no snapshot
        c.execute(text(_DV), _new_version(world_ids, doc, world_ids.reviewer, snap=world_ids.s1))


def test_document_version_snapshot_profile_mismatch_fails(
    ingest_engine: Engine, world_ids: Ids
) -> None:
    with ingest_engine.begin() as c:
        c.execute(text("INSERT INTO snapshot VALUES (77, 'ukg_pro_wfm', 'dev', 'x', now())"))
    doc = _doc_of(ingest_engine, world_ids.design_dv)  # a synthetic document
    params = {"id": 51, "doc": doc, "h": "f", "snap": 77, "sup": None, "by": world_ids.service}
    with sqlstate_raised("WB003"), ingest_engine.begin() as c:
        c.execute(text(_DV), params)


def test_lineage_cannot_be_rewired(store: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("WB001"), store.begin() as c:
        c.execute(
            text("UPDATE document_version SET supersedes_version_id = :d WHERE id = :e"),
            {"d": world_ids.design_dv, "e": world_ids.export_dv},
        )
