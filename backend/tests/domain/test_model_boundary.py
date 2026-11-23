# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""ExtractionBoundary (decision T1). FICTIONAL: not UKG behaviour."""

import pytest
from pydantic import ValidationError

from app.domain.model import ExtractionBoundary
from app.domain.records import Records
from tests.domain.builders import World


def base() -> tuple[Records, int, int, int]:
    """Records with two versions; returns (records, v1, loc a of v1, loc b of v1)."""
    w = World()
    s = w.snapshot("s1")
    v1, v2 = w.export(s), w.design()
    a, b = w.locator(v1), w.locator(v2)
    a2 = w.locator(v1)
    assert b.document_version_id == v2.id
    return w.build(), v1.id, a.id, a2.id


def boundary(v: int, locs: tuple[int, ...], reason: str = "unknown_sheet", i: int = 1) -> object:
    return {"id": i, "document_version_id": v, "reason": reason, "locator_ids": locs}


def with_boundaries(r: Records, *bs: object) -> Records:
    return r.extended(extraction_boundaries=tuple(ExtractionBoundary.model_validate(b) for b in bs))


def test_boundary_valid() -> None:
    r, v, a, a2 = base()
    got = with_boundaries(r, boundary(v, (a2, a)))
    assert got.extraction_boundaries[0].locator_ids == (a, a2)


def test_boundary_needs_locators() -> None:
    with pytest.raises(ValidationError):
        ExtractionBoundary.model_validate(boundary(1, ()))


def test_boundary_unknown_reason() -> None:
    with pytest.raises(ValidationError):
        ExtractionBoundary.model_validate(boundary(1, (1,), reason="dropped"))


@pytest.mark.parametrize("bad", ["version", "locator"])
def test_boundary_dangling_version_or_locator(bad: str) -> None:
    r, v, a, _ = base()
    b = boundary(999, (a,)) if bad == "version" else boundary(v, (999,))
    with pytest.raises(ValidationError, match="references: dangling"):
        with_boundaries(r, b)


def test_boundary_locator_in_other_version() -> None:
    r, v, a, _ = base()
    other = next(x.id for x in r.locators if x.document_version_id != v)
    with pytest.raises(ValidationError, match="boundary: locator in another version"):
        with_boundaries(r, boundary(v, (a, other)))


def test_boundary_duplicate() -> None:
    r, v, a, _ = base()
    with pytest.raises(ValidationError, match="uniqueness"):
        with_boundaries(r, boundary(v, (a,), i=1), boundary(v, (a,), i=2))


def test_boundary_ids_unique() -> None:
    r, v, a, a2 = base()
    with pytest.raises(ValidationError, match="ids: duplicate"):
        with_boundaries(r, boundary(v, (a,), i=1), boundary(v, (a2,), i=1))
