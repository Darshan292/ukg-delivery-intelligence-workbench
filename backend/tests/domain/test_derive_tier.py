# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""FICTIONAL: not UKG behaviour."""

from collections.abc import Callable

import pytest
from hypothesis import given, settings

from app.domain.derive import EdgeView, evaluate
from app.domain.records import Records
from tests.domain.builders import CATALOGUE, World
from tests.domain.strategies import worlds


class Fx:
    def __init__(self, w: World) -> None:
        self.w = w
        self.s1 = w.snapshot("s1")
        self.e1, self.d = w.export(self.s1), w.design()
        self.a, self.b, self.c = w.entity("cfg", "A"), w.entity("cfg", "B"), w.entity("cfg", "C")
        self.ab = w.rel("uses", self.a, self.b)

    def edge(self, rel_id: int | None = None) -> EdgeView:
        return evaluate(self.w.build(), self.s1.id).edge(rel_id or self.ab.id)


@pytest.fixture
def fx(world: World) -> Fx:
    return Fx(world)


def test_accepted_edge_is_established(fx: Fx) -> None:
    fx.w.accept(fx.ab, fx.s1)
    assert fx.edge().tier == "established"


def test_unreviewed_explicit_without_conflict_is_established(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    assert fx.edge().tier == "established"


def test_unreviewed_rule_only_is_possible(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d, basis="deterministic_rule")
    assert fx.edge().tier == "possible"


def test_explicit_claim_rejected_leaves_rule_basis_possible(fx: Fx) -> None:
    ex = fx.w.claim(fx.ab, fx.d)
    fx.w.claim(fx.ab, fx.d, basis="deterministic_rule")
    assert fx.edge().tier == "established"
    fx.w.reject_claim(ex)
    assert fx.edge().tier == "possible"


def _polarity(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    fx.w.claim(fx.ab, fx.d, polarity="absent")


def _cardinality(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    fx.w.claim(fx.w.rel("uses", fx.a, fx.c), fx.d)


def _documentary(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    fx.w.version(fx.a, fx.e1, x=1)


@pytest.mark.parametrize(
    ("setup", "kind"),
    [(_polarity, "polarity"), (_cardinality, "cardinality"), (_documentary, "documentary_only")],
)
def test_unreviewed_explicit_conflicted_is_possible(
    fx: Fx, setup: Callable[[Fx], None], kind: str
) -> None:
    setup(fx)
    v = fx.edge()
    assert kind in v.conflict_kinds
    assert v.tier == "possible"


def test_accepted_conflicted_edge_is_established_and_flagged(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    fx.w.claim(fx.w.rel("uses", fx.a, fx.c), fx.d)
    fx.w.accept(fx.ab, fx.s1)
    v = fx.edge()
    assert v.tier == "established"
    assert "cardinality" in v.conflict_kinds


def test_unreviewed_explicit_same_as_is_possible(fx: Fx) -> None:
    sa = fx.w.rel("same_as", fx.a, fx.c)
    fx.w.claim(sa, fx.d)
    assert fx.edge(sa.id).tier == "possible"


def test_rejected_same_as_is_excluded(fx: Fx) -> None:
    sa = fx.w.rel("same_as", fx.a, fx.c)
    fx.w.claim(sa, fx.d)
    fx.w.reject(sa, fx.s1)
    assert fx.edge(sa.id).tier == "excluded"


def test_excluded_states(fx: Fx) -> None:
    rej, sup, uns = fx.ab, fx.w.rel("uses", fx.b, fx.c), fx.w.rel("uses", fx.c, fx.a)
    new = fx.w.rel("uses", fx.b, fx.a)
    fx.w.reject(rej, fx.s1)
    fx.w.supersede(sup, fx.s1, new)
    assert [fx.edge(i.id).tier for i in (rej, sup, uns)] == ["excluded"] * 3


def test_attribute_conflict_does_not_change_edge_tier(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.e1)  # scoped claim: no documentary-only conflict
    e1b = fx.w.export(fx.s1)
    fx.w.version(fx.a, fx.e1, q=1)
    fx.w.version(fx.a, e1b, q=2)
    ev = evaluate(fx.w.build(), fx.s1.id)
    assert [c.kind for c in ev.conflicts if c.kind == "attribute"] == ["attribute"]
    assert ev.edge(fx.ab.id).tier == "established"


def test_evaluate_only_covers_relationships_of_the_snapshot_profile(fx: Fx) -> None:
    fx.w.catalogues.append(CATALOGUE.model_copy(update={"product_profile": "ukg_pro_wfm"}))
    x, y = fx.w.entity("cfg", "X", "ukg_pro_wfm"), fx.w.entity("cfg", "Y", "ukg_pro_wfm")
    other = fx.w.rel("uses", x, y)
    ev = evaluate(fx.w.build(), fx.s1.id)
    assert [e.relationship_id for e in ev.edges] == [fx.ab.id]
    assert other.id not in {e.relationship_id for e in ev.edges}


@settings(max_examples=200, deadline=None)
@given(worlds())
def test_tier_is_consistent_with_state(r: Records) -> None:
    for s in r.snapshots:
        for v in evaluate(r, s.id).edges:
            hidden = v.state in ("rejected", "superseded", "unsupported")
            assert (v.tier == "excluded") == hidden
            if v.tier == "established" and v.state != "accepted":
                rel = r.relationship_by_id[v.relationship_id]
                assert v.basis_strength == "explicit_source"
                assert rel.type != "same_as"
                assert not {"polarity", "cardinality", "documentary_only"} & set(v.conflict_kinds)
