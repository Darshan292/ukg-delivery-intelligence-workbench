# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""FICTIONAL: not UKG behaviour."""

from datetime import timedelta
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.derive import is_claim_superseded, live_claims, verdict
from app.domain.model import ClaimReviewEvent, RelationshipReviewEvent
from app.domain.records import Records
from tests.domain.builders import T0, World, with_claim_event
from tests.domain.strategies import worlds


def ids(cs: Any) -> list[int]:
    return [c.id for c in cs]


def claim_ev(w: World, claim_id: int, ev_id: int, at: int, v: str) -> ClaimReviewEvent:
    return ClaimReviewEvent.model_validate(
        {
            "id": ev_id, "at": T0 + timedelta(days=1, seconds=at),
            "actor_id": w.default_reviewer().id,
            "target_kind": "claim", "claim_id": claim_id, "verdict": v, "reason": "r",
        }
    )  # fmt: skip


def rel_ev(w: World, rel_id: int, ev_id: int, at: int, v: str) -> RelationshipReviewEvent:
    return RelationshipReviewEvent.model_validate(
        {
            "id": ev_id, "at": T0 + timedelta(days=1, seconds=at),
            "actor_id": w.default_reviewer().id,
            "target_kind": "relationship", "relationship_id": rel_id, "scope_snapshot_id": None,
            "verdict": v, "reason": None if v == "accepted" else "r",
        }
    )  # fmt: skip


def test_claim_scoped_to_other_snapshot_is_not_live(world: World) -> None:
    s1, s2 = world.snapshot("s1"), world.snapshot("s2")
    e1 = world.export(s1)
    a, b = world.entity("cfg", "A"), world.entity("cfg", "B")
    uses = world.rel("uses", a, b)
    c = world.claim(uses, e1)
    r = world.build()
    assert ids(live_claims(r, uses.id, s1.id)) == [c.id]
    assert live_claims(r, uses.id, s2.id) == ()


def test_unscoped_claim_is_live_in_every_snapshot(world: World) -> None:
    s1, s2 = world.snapshot("s1"), world.snapshot("s2")
    d = world.design()
    a, b = world.entity("cfg", "A"), world.entity("cfg", "B")
    uses = world.rel("uses", a, b)
    c = world.claim(uses, d)
    r = world.build()
    for s in (s1, s2):
        assert ids(live_claims(r, uses.id, s.id)) == [c.id]


def test_unscoped_relationship_with_both_scoped_claims_live_in_both(world: World) -> None:
    s1, s2 = world.snapshot("s1"), world.snapshot("s2")
    e1, e2 = world.export(s1), world.export(s2)
    a, q = world.entity("cfg", "A"), world.entity("req", "Q")
    impl = world.rel("implements", a, q)
    c1, c2 = world.claim(impl, e1), world.claim(impl, e2)
    r = world.build()
    assert ids(live_claims(r, impl.id, s1.id)) == [c1.id]
    assert ids(live_claims(r, impl.id, s2.id)) == [c2.id]


def test_superseded_version_claims_are_not_live(world: World) -> None:
    s1, s2 = world.snapshot("s1"), world.snapshot("s2")
    d = world.design()
    a, b = world.entity("cfg", "A"), world.entity("cfg", "B")
    uses = world.rel("uses", a, b)
    c = world.claim(uses, d)
    world.new_version(d)
    r = world.build()
    assert is_claim_superseded(r, c)
    for s in (s1, s2):
        assert live_claims(r, uses.id, s.id) == ()


def test_claim_with_any_locator_in_superseded_version_is_superseded(world: World) -> None:
    world.snapshot("s1")
    d, d_b = world.design(), world.design()
    a, b = world.entity("cfg", "A"), world.entity("cfg", "B")
    uses = world.rel("uses", a, b)
    c = world.claim(uses, d)
    other = world.locator(d_b)
    world.claims[-1] = c.model_copy(update={"locator_ids": (c.locator_ids[0], other.id)})
    world.new_version(d_b)  # only the second locator's version is replaced
    r = world.build()
    assert is_claim_superseded(r, r.claims[0])


def test_rejected_claim_not_live_reinstated_claim_live_again(world: World) -> None:
    s1 = world.snapshot("s1")
    d = world.design()
    a, b = world.entity("cfg", "A"), world.entity("cfg", "B")
    uses = world.rel("uses", a, b)
    c = world.claim(uses, d)
    world.reject_claim(c)
    assert live_claims(world.build(), uses.id, s1.id) == ()
    world.reinstate_claim(c)
    assert ids(live_claims(world.build(), uses.id, s1.id)) == [c.id]


def test_claim_event_order_uses_at_then_id(world: World) -> None:
    s1 = world.snapshot("s1")
    d = world.design()
    a, b = world.entity("cfg", "A"), world.entity("cfg", "B")
    uses = world.rel("uses", a, b)
    c = world.claim(uses, d)
    rej, rein = claim_ev(world, c.id, 50, 5, "rejected"), claim_ev(world, c.id, 51, 5, "reinstated")
    world.review_events += [rein, rej]  # insertion order must not matter
    assert ids(live_claims(world.build(), uses.id, s1.id)) == [c.id]
    rej2 = claim_ev(world, c.id, 52, 5, "rejected")
    world.review_events.append(rej2)  # same `at`, higher id wins
    assert live_claims(world.build(), uses.id, s1.id) == ()


def test_verdict_latest_by_at_then_id(world: World) -> None:
    world.snapshot("s1")
    a, q = world.entity("cfg", "A"), world.entity("req", "Q")
    impl = world.rel("implements", a, q)
    world.review_events += [
        rel_ev(world, impl.id, 60, 2, "accepted"),
        rel_ev(world, impl.id, 61, 1, "rejected"),
    ]
    v = verdict(world.build(), impl.id, 1)
    assert v is not None
    assert v.verdict == "accepted"
    world.review_events.append(rel_ev(world, impl.id, 62, 2, "rejected"))
    v = verdict(world.build(), impl.id, 1)
    assert v is not None
    assert v.verdict == "rejected"


def test_scoped_verdict_only_in_its_snapshot(world: World) -> None:
    s1, s2 = world.snapshot("s1"), world.snapshot("s2")
    a, b = world.entity("cfg", "A"), world.entity("cfg", "B")
    uses = world.rel("uses", a, b)
    world.accept(uses, s1)
    r = world.build()
    assert verdict(r, uses.id, s1.id) is not None
    assert verdict(r, uses.id, s2.id) is None


def test_unscoped_verdict_applies_in_every_snapshot(world: World) -> None:
    s1, s2 = world.snapshot("s1"), world.snapshot("s2")
    a, q = world.entity("cfg", "A"), world.entity("req", "Q")
    impl = world.rel("implements", a, q)
    world.accept(impl, None)
    r = world.build()
    assert verdict(r, impl.id, s1.id) is not None
    assert verdict(r, impl.id, s2.id) is not None


def test_live_claims_sorted_by_id(world: World) -> None:
    s1 = world.snapshot("s1")
    d = world.design()
    a, b = world.entity("cfg", "A"), world.entity("cfg", "B")
    uses = world.rel("uses", a, b)
    cs = [
        world.claim(uses, d, basis=bs)
        for bs in ("llm_suggestion", "explicit_source", "deterministic_rule")
    ]
    got = ids(live_claims(world.build(), uses.id, s1.id))
    assert got == sorted(c.id for c in cs)


@settings(max_examples=200, deadline=None)
@given(worlds())
def test_live_claims_never_include_foreign_scope(r: Records) -> None:
    for rel in r.relationships:
        for s in r.snapshots:
            for c in live_claims(r, rel.id, s.id):
                assert c.scope_snapshot_id in (None, s.id)


@settings(max_examples=200, deadline=None)
@given(worlds(), st.data())
def test_rejecting_one_claim_never_changes_other_claims_liveness(
    r: Records, data: st.DataObject
) -> None:
    pairs = [
        (rel.id, s.id, c)
        for rel in r.relationships
        for s in r.snapshots
        for c in live_claims(r, rel.id, s.id)
    ]
    if not pairs:
        return
    _rel_id, _s, victim = data.draw(st.sampled_from(pairs))
    r2 = with_claim_event(r, victim.id, "rejected")
    for rel in r.relationships:
        for s in r.snapshots:
            before = {c.id for c in live_claims(r, rel.id, s.id)}
            after = {c.id for c in live_claims(r2, rel.id, s.id)}
            assert after == before - {victim.id}
