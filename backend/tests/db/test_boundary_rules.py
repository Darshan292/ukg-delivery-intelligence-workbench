# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""extraction_boundary: round trip, CHECKs, locator trigger, append-only. FICTIONAL data."""

from typing import Any

import pytest
from sqlalchemy import Engine, text

from app.domain.model import ExtractionBoundary
from app.domain.records import Records
from app.store import load, save
from tests.db_helpers import norm, sqlstate_raised
from tests.domain.builders import World

INSERT = text(
    "INSERT INTO extraction_boundary (id, document_version_id, reason, locator_ids)"
    " VALUES (:i, :v, :r, :l)"
)


def world() -> tuple[Records, int, int, list[int], int]:
    """Records with two versions; (r, version, other version, locators of v, locator of other)."""
    w = World()
    w.reviewer()
    v, other = w.design(), w.design()
    locs = [w.locator(v).id for _ in range(3)]
    return w.build(), v.id, other.id, locs, w.locator(other).id


def boundary(i: int, v: int, locs: tuple[int, ...], reason: str = "unknown_sheet") -> Any:
    return ExtractionBoundary(id=i, document_version_id=v, reason=reason, locator_ids=locs)  # type: ignore[arg-type]


def test_boundary_roundtrip(store: Engine) -> None:
    r, v, _, locs, _ = world()
    r = r.extended(
        extraction_boundaries=(
            boundary(1, v, (locs[1], locs[0])),
            boundary(2, v, (locs[2],), "missing_key"),
        )
    )
    with store.begin() as c:
        save(c, r)
    with store.connect() as c:
        assert norm(load(c)) == norm(r)


def _saved(store: Engine) -> tuple[int, int, list[int], int]:
    r, v, other, locs, other_loc = world()
    with store.begin() as c:
        save(c, r)
    return v, other, locs, other_loc


def test_boundary_reason_check(store: Engine) -> None:
    v, _, locs, _ = _saved(store)
    with sqlstate_raised("23514"), store.begin() as c:
        c.execute(INSERT, {"i": 1, "v": v, "r": "dropped", "l": [locs[0]]})


def test_boundary_locator_other_version(store: Engine) -> None:
    v, _, locs, other_loc = _saved(store)
    with sqlstate_raised("WB003"), store.begin() as c:
        c.execute(INSERT, {"i": 1, "v": v, "r": "unknown_sheet", "l": [locs[0], other_loc]})
    with sqlstate_raised("WB003"), store.begin() as c:  # repeated, missing
        c.execute(INSERT, {"i": 1, "v": v, "r": "unknown_sheet", "l": [locs[0], locs[0]]})
    with sqlstate_raised("WB003"), store.begin() as c:
        c.execute(INSERT, {"i": 1, "v": v, "r": "unknown_sheet", "l": [999]})
    with sqlstate_raised(("23514", "WB003")), store.begin() as c:  # empty (the trigger is first)
        c.execute(INSERT, {"i": 1, "v": v, "r": "unknown_sheet", "l": []})


def test_boundary_stored_sorted(store: Engine) -> None:
    v, _, locs, _ = _saved(store)
    with store.begin() as c:  # positive control for the trigger tests above
        c.execute(INSERT, {"i": 1, "v": v, "r": "unknown_sheet", "l": [locs[2], locs[0]]})
        got = c.scalar(text("SELECT locator_ids FROM extraction_boundary WHERE id = 1"))
    assert got == sorted([locs[2], locs[0]])


@pytest.mark.parametrize("sql", ["UPDATE extraction_boundary SET reason = 'x'",
                                 "DELETE FROM extraction_boundary"])  # fmt: skip
def test_boundary_append_only(store: Engine, ingest_engine: Engine, sql: str) -> None:
    v, _, locs, _ = _saved(store)
    with ingest_engine.begin() as c:  # positive control: the ingest role may insert
        c.execute(INSERT, {"i": 1, "v": v, "r": "unknown_sheet", "l": [locs[0]]})
    with sqlstate_raised(("WB001", "42501")), ingest_engine.begin() as c:
        c.execute(text(sql))
    with sqlstate_raised("WB001"), store.begin() as c:  # the owner too: the trigger, not privileges
        c.execute(text(sql))
