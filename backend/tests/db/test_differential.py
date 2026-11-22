# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Invariant 11 (state derived from stored rows equals the in-memory evaluation) and the DB half
of invariant 3 (re-ingest never changes a verdict), both through the app roles.

Interpretation (owner question S5-Q1, decided): "DB evaluation" is `evaluate` on rows read back
from the database; no SQL re-implementation of `derive` exists in this slice.
"""

from hypothesis import HealthCheck, given, settings
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from app.db import sqlstate
from app.domain.derive import evaluate
from app.domain.records import Records
from app.store import ALL, load, save
from tests.db_helpers import Ids, has_supersession_cycle, norm, truncate
from tests.domain.strategies import worlds


def save_as_roles(r: Records, owner: Engine, ingest: Engine, review: Engine) -> None:
    with owner.begin() as c:
        save(c, r, ("catalogues", "actors"))
    with ingest.begin() as c:
        save(c, r, tuple(f for f in ALL if f not in ("catalogues", "actors", "review_events")))
    with review.begin() as c:
        save(c, r, ("review_events",))


@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@given(r=worlds())
def test_db_state_equals_in_memory(
    r: Records, store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    truncate(store)
    cyclic = has_supersession_cycle(r)
    try:
        save_as_roles(r, store, ingest_engine, review_engine)
    except DBAPIError as e:  # the DB is stricter than the domain only on cycles
        assert cyclic and sqlstate(e) == "WB003"
        return
    assert not cyclic
    with review_engine.connect() as c:
        loaded = load(c)
    assert norm(loaded) == norm(r)
    for s in r.snapshots:
        assert evaluate(loaded, s.id) == evaluate(r, s.id)


def test_reingest_never_changes_verdicts(
    store: Engine, ingest_engine: Engine, review_engine: Engine, world_ids: Ids
) -> None:
    rel = world_ids.unscoped_rel
    with review_engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO review_event (target_kind, relationship_id, verdict, actor_id)"
                " VALUES ('relationship', :r, 'accepted', :a)"
            ),
            {"r": rel, "a": world_ids.reviewer},
        )

    def events() -> list[object]:
        with review_engine.connect() as c:
            return [tuple(x) for x in c.execute(text("SELECT * FROM review_event ORDER BY id"))]

    before = events()
    with ingest_engine.begin() as c:  # a new design version; the edge gets no claim in it
        doc = c.scalar(
            text("SELECT document_id FROM document_version WHERE id = :d"),
            {"d": world_ids.design_dv},
        )
        c.execute(
            text(
                "INSERT INTO document_version VALUES (50, :doc, repeat('e', 64), NULL, :old, :by,"
                " now())"
            ),
            {"doc": doc, "old": world_ids.design_dv, "by": world_ids.reviewer},
        )
    assert events() == before
    with review_engine.connect() as c:
        edge = evaluate(load(c), world_ids.s1).edge(rel)
    assert edge.state == "accepted"
    assert "SUPPORT_LOST" in edge.flags
