# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from app.domain.model import ClaimReviewEvent, RelationshipReviewEvent, ReviewEvent

T = datetime(2026, 1, 1, tzinfo=UTC)
ADAPTER: TypeAdapter[Any] = TypeAdapter(ReviewEvent)
CLAIM: dict[str, Any] = {
    "id": 1,
    "at": T,
    "actor_id": 1,
    "target_kind": "claim",
    "claim_id": 1,
    "verdict": "rejected",
    "reason": "r",
}
REL: dict[str, Any] = {
    "id": 1,
    "at": T,
    "actor_id": 1,
    "target_kind": "relationship",
    "relationship_id": 1,
    "scope_snapshot_id": None,
    "verdict": "accepted",
}


def test_review_event_union_dispatches_on_target_kind() -> None:
    assert isinstance(ADAPTER.validate_python(CLAIM), ClaimReviewEvent)
    assert isinstance(ADAPTER.validate_python(REL), RelationshipReviewEvent)
    with pytest.raises(ValidationError):
        ADAPTER.validate_python({**CLAIM, "target_kind": "document"})


@pytest.mark.parametrize(
    ("v", "ok"),
    [("rejected", True), ("reinstated", True), ("accepted", False), ("superseded", False)],
)
def test_claim_event_verdicts(v: str, ok: bool) -> None:
    if ok:
        assert ADAPTER.validate_python({**CLAIM, "verdict": v})
    else:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python({**CLAIM, "verdict": v})


def test_claim_event_has_no_scope_field() -> None:
    with pytest.raises(ValidationError) as e:
        ADAPTER.validate_python({**CLAIM, "scope_snapshot_id": 1})
    assert e.value.errors()[0]["type"] == "extra_forbidden"


def rel_ev(**kw: Any) -> Any:
    return ADAPTER.validate_python({**REL, **kw})


def test_relationship_event_verdicts() -> None:
    for v in ("accepted", "rejected"):
        assert rel_ev(verdict=v, reason="r")
    assert rel_ev(verdict="superseded", reason="r", successor_relationship_id=2)
    for v in ("reinstated", "other"):
        with pytest.raises(ValidationError):
            rel_ev(verdict=v, reason="r")


ALL_VERDICTS: list[dict[str, Any]] = [
    {**CLAIM, "verdict": "rejected"},
    {**CLAIM, "verdict": "reinstated"},
    {**REL, "verdict": "accepted"},
    {**REL, "verdict": "rejected"},
    {**REL, "verdict": "superseded", "successor_relationship_id": 2},
]


@pytest.mark.parametrize("base", ALL_VERDICTS)
def test_reason_required_except_accepted(base: dict[str, Any]) -> None:
    base = {k: v for k, v in base.items() if k != "reason"}
    if base["verdict"] == "accepted":
        assert ADAPTER.validate_python(base)
    else:
        with pytest.raises(ValidationError):
            ADAPTER.validate_python(base)
    assert ADAPTER.validate_python({**base, "reason": "r"})


def test_superseded_requires_successor_not_self() -> None:
    with pytest.raises(ValidationError):
        rel_ev(verdict="superseded", reason="r")
    with pytest.raises(ValidationError):
        rel_ev(verdict="superseded", reason="r", successor_relationship_id=1)


def test_successor_only_with_superseded() -> None:
    with pytest.raises(ValidationError):
        rel_ev(verdict="rejected", reason="r", successor_relationship_id=2)


def test_event_time_must_be_aware() -> None:
    with pytest.raises(ValidationError):
        ADAPTER.validate_python({**CLAIM, "at": datetime(2026, 1, 1)})  # noqa: DTZ001
