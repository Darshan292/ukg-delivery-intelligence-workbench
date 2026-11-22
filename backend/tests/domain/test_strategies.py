# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
from collections import Counter
from collections.abc import Callable

import pytest
from hypothesis import find, given, settings
from hypothesis import strategies as st

from app.domain.derive import evaluate
from app.domain.records import Records
from tests.domain.strategies import neutral_extension, worlds


@settings(max_examples=200, deadline=None)
@given(worlds())
def test_worlds_always_validate(r: Records) -> None:
    assert r.relationships is not None


@settings(max_examples=100, deadline=None)
@given(st.data())
def test_neutral_extensions_validate_and_only_add(data: st.DataObject) -> None:
    r = data.draw(worlds())
    more = data.draw(neutral_extension(r))
    r2 = r.extended(**more)
    assert len(r2.entities) > len(r.entities)
    assert r2.review_events == r.review_events


def _absent_claim(r: Records) -> bool:
    return any(c.polarity == "absent" for c in r.claims)


def _superseded_design(r: Records) -> bool:
    return bool(r.superseded_version_ids)


def _accepted_scoped(r: Records) -> bool:
    return any(
        e.target_kind == "relationship" and e.verdict == "accepted" and e.scope_snapshot_id
        for e in r.review_events
    )


def _rejected_claim(r: Records) -> bool:
    return any(e.target_kind == "claim" and e.verdict == "rejected" for e in r.review_events)


def _two_versions_in_s1(r: Records) -> bool:
    counts = Counter((v.entity_id, v.snapshot_id) for v in r.entity_versions if v.snapshot_id)
    return any(n >= 2 for n in counts.values())


@pytest.mark.parametrize(
    "pred",
    [_absent_claim, _superseded_design, _accepted_scoped, _rejected_claim, _two_versions_in_s1],
)
def test_worlds_cover_the_interesting_cases(pred: Callable[[Records], bool]) -> None:
    find(worlds(), pred, settings=settings(max_examples=2000, deadline=None, database=None))


@pytest.mark.parametrize(
    "kind", ["polarity", "cardinality", "documentary_only", "identity", "attribute"]
)
def test_worlds_produce_every_conflict_kind(kind: str) -> None:
    """Fixed budget: the conflict properties must not be vacuous."""

    def has(r: Records) -> bool:
        return any(c.kind == kind for s in r.snapshots for c in evaluate(r, s.id).conflicts)

    find(worlds(), has, settings=settings(max_examples=300, deadline=None, database=None))
