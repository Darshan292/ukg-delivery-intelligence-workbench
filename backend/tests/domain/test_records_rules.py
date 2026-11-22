# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""FICTIONAL: not UKG behaviour."""

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from app.domain.model import Actor, Claim, ClaimReviewEvent
from app.domain.records import Records
from tests.domain.builders import World


class Fx:
    """One scoped relationship (cfg uses cfg), one unscoped (cfg implements req)."""

    def __init__(self, w: World) -> None:
        self.w = w
        self.s1, self.s2 = w.snapshot("s1"), w.snapshot("s2")
        self.e1, self.e2, self.d = w.export(self.s1), w.export(self.s2), w.design()
        self.a, self.b = w.entity("cfg", "A"), w.entity("cfg", "B")
        self.c, self.q = w.entity("cfg", "C"), w.entity("req", "Q")
        self.uses = w.rel("uses", self.a, self.b)
        self.uses2 = w.rel("uses", self.a, self.c)
        self.impl = w.rel("implements", self.a, self.q)
        self.claim = w.claim(self.uses, self.e1)


@pytest.fixture
def fx(world: World) -> Fx:
    return Fx(world)


def human_no_role(w: World) -> Actor:
    a = Actor(id=900, kind="human", display_name="H", roles=frozenset())
    w.actors.append(a)
    return a


EVENTS: list[Callable[[Fx, Actor], object]] = [
    lambda f, by: f.w.reject_claim(f.claim, by=by),
    lambda f, by: f.w.reinstate_claim(f.claim, by=by),
    lambda f, by: f.w.accept(f.uses, f.s1, by=by),
    lambda f, by: f.w.reject(f.uses, f.s1, by=by),
    lambda f, by: f.w.supersede(f.uses, f.s1, f.uses2, by=by),
]


@pytest.mark.parametrize("event", EVENTS)
def test_records_rejects_review_event_by_service_actor(
    fx: Fx, event: Callable[..., object]
) -> None:
    event(fx, fx.w.service())
    with pytest.raises(ValidationError, match="review: actor is not a human reviewer"):
        fx.w.build()


@pytest.mark.parametrize("event", EVENTS)
def test_records_rejects_review_event_by_human_without_reviewer_role(
    fx: Fx, event: Callable[..., object]
) -> None:
    event(fx, human_no_role(fx.w))
    with pytest.raises(ValidationError, match="review: actor is not a human reviewer"):
        fx.w.build()


def test_reviewer_events_accepted(fx: Fx) -> None:
    for e in EVENTS:
        e(fx, fx.w.reviewer())
    assert fx.w.build()


def test_lineage_requires_human_declarer(fx: Fx) -> None:
    fx.w.new_version(fx.d, by=fx.w.service())
    with pytest.raises(ValidationError, match="lineage: declarer"):
        fx.w.build()


def test_unlinked_version_may_be_uploaded_by_service(fx: Fx) -> None:
    assert fx.w.build()  # builder uploads first versions as a service actor


def test_lineage_requires_same_document(fx: Fx) -> None:
    v2 = fx.w.new_version(fx.d)
    fx.w.document_versions[-1] = v2.model_copy(update={"supersedes_version_id": fx.e1.id})
    with pytest.raises(ValidationError, match="lineage: document"):
        fx.w.build()


def test_lineage_requires_same_snapshot(fx: Fx) -> None:
    v2 = fx.w.new_version(fx.e1)
    fx.w.document_versions[-1] = v2.model_copy(update={"snapshot_id": fx.s2.id})
    with pytest.raises(ValidationError, match="lineage: snapshot"):
        fx.w.build()


def test_entity_version_snapshot_equals_its_document_version(fx: Fx) -> None:
    ev = fx.w.version(fx.a, fx.e1, x=1)
    fx.w.entity_versions[-1] = ev.model_copy(update={"snapshot_id": fx.s2.id})
    with pytest.raises(ValidationError, match="entity_version: snapshot"):
        fx.w.build()


def test_entity_version_locators_belong_to_its_version(fx: Fx) -> None:
    ev = fx.w.version(fx.a, fx.e1, x=1)
    other = fx.w.locator(fx.e2)
    fx.w.entity_versions[-1] = ev.model_copy(update={"locator_ids": (other.id,), "attributes": ()})
    with pytest.raises(ValidationError, match="entity_version: locator"):
        fx.w.build()


def replace_claim(fx: Fx, **update: Any) -> None:
    fx.w.claims[-1] = fx.w.claims[-1].model_copy(update=update)


@pytest.mark.parametrize("scope", [None, 2])
def test_claim_scope_equals_locator_snapshot(fx: Fx, scope: int | None) -> None:
    assert fx.claim.scope_snapshot_id == fx.s1.id
    replace_claim(fx, scope_snapshot_id=scope)
    with pytest.raises(ValidationError, match="claim: scope"):
        fx.w.build()


def test_unscoped_locators_require_null_scope(fx: Fx) -> None:
    fx.w.claim(fx.uses2, fx.d)
    replace_claim(fx, scope_snapshot_id=fx.s1.id)
    with pytest.raises(ValidationError, match="claim: scope"):
        fx.w.build()


def test_claim_locators_span_at_most_one_snapshot(fx: Fx) -> None:
    other = fx.w.locator(fx.e2)
    replace_claim(fx, locator_ids=(fx.claim.locator_ids[0], other.id))
    with pytest.raises(ValidationError, match="claim: locators span"):
        fx.w.build()


def test_claim_mixing_scoped_and_unscoped_locators_rejected(fx: Fx) -> None:
    other = fx.w.locator(fx.d)
    replace_claim(fx, locator_ids=(fx.claim.locator_ids[0], other.id))
    with pytest.raises(ValidationError, match="claim: mixed"):
        fx.w.build()


def test_scoped_relationship_verdict_must_name_snapshot_of_same_profile(fx: Fx) -> None:
    fx.w.accept(fx.uses, None)
    with pytest.raises(ValidationError, match="review: scope"):
        fx.w.build()


def test_scoped_verdict_snapshot_of_other_profile_rejected(fx: Fx) -> None:
    other = fx.w.snapshot("x", profile="ukg_pro_wfm")
    fx.w.accept(fx.uses, other)
    with pytest.raises(ValidationError, match="review: scope"):
        fx.w.build()


def test_unscoped_relationship_verdict_must_have_null_scope(fx: Fx) -> None:
    fx.w.accept(fx.impl, fx.s1)
    with pytest.raises(ValidationError, match="review: scope"):
        fx.w.build()
    fx.w.review_events.clear()
    fx.w.accept(fx.impl, None)
    assert fx.w.build()


def test_successor_must_share_source_entity(fx: Fx) -> None:
    other = fx.w.rel("uses", fx.b, fx.c)
    fx.w.supersede(fx.uses, fx.s1, other)
    with pytest.raises(ValidationError, match="review: successor"):
        fx.w.build()


def test_extended_appends_and_revalidates(fx: Fx) -> None:
    r = fx.w.build()
    bad = ClaimReviewEvent(
        id=77, at=fx.w.claims[0].created_at, actor_id=r.actors[0].id,
        target_kind="claim", claim_id=fx.claim.id, verdict="rejected", reason="r",
    )  # fmt: skip
    with pytest.raises(ValidationError):
        r.extended(review_events=(bad,))
    fx.w.reject_claim(fx.claim)
    r2 = fx.w.build()
    extra: Claim = fx.w.claim(fx.uses2, fx.e1)
    r3 = r2.extended(claims=(extra,), locators=(fx.w.locators[-1],))
    for f in Records.model_fields:
        assert getattr(r3, f)[: len(getattr(r2, f))] == getattr(r2, f)
    assert len(r3.claims) == len(r2.claims) + 1
    with pytest.raises(TypeError):
        r.extended(nonsense=())


def test_records_has_no_update_or_remove_api() -> None:
    own = set(dir(Records)) - set(
        dir(BaseModel)
    )  # BaseModel ships a deprecated update_forward_refs
    names = {n for n in own if n.startswith(("remove", "delete", "update", "replace"))}
    assert names == set()


def test_records_model_copy_raises_use_extended(fx: Fx) -> None:
    r = fx.w.build()
    with pytest.raises(TypeError, match="extended"):
        r.model_copy(update={"claims": ()})


def test_invalid_leaf_made_by_copy_is_rejected_in_records(fx: Fx) -> None:
    bad = fx.claim.model_copy(
        update={"locator_ids": fx.claim.locator_ids * 2}
    )  # copy skips validation
    fx.w.claims[-1] = bad
    with pytest.raises(ValidationError):
        fx.w.build()
