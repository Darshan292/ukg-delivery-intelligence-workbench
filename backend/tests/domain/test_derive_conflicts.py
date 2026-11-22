# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""FICTIONAL: not UKG behaviour."""

import pytest

from app.domain.derive import conflicts, edge_state
from tests.domain.builders import World


class Fx:
    def __init__(self, w: World) -> None:
        self.w = w
        self.s1, self.s2 = w.snapshot("s1"), w.snapshot("s2")
        self.e1, self.e2, self.d = w.export(self.s1), w.export(self.s2), w.design()
        self.a, self.b, self.c = w.entity("cfg", "A"), w.entity("cfg", "B"), w.entity("cfg", "C")
        self.q = w.entity("req", "Q")
        self.ab = w.rel("uses", self.a, self.b)

    def kinds(self, s: int | None = None) -> list[str]:
        return [c.kind for c in conflicts(self.w.build(), s or self.s1.id)]


@pytest.fixture
def fx(world: World) -> Fx:
    return Fx(world)


def test_polarity_conflict_present_and_absent(fx: Fx) -> None:
    p = fx.w.claim(fx.ab, fx.d)
    n = fx.w.claim(fx.ab, fx.d, polarity="absent")
    [c] = conflicts(fx.w.build(), fx.s1.id)
    assert (c.kind, c.relationship_ids, c.claim_ids) == ("polarity", (fx.ab.id,), (p.id, n.id))
    assert c.snapshot_id == fx.s1.id


def test_accepted_edge_with_only_absent_claims_is_polarity_conflict(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d, polarity="absent")
    fx.w.accept(fx.ab, fx.s1)
    r = fx.w.build()
    st = edge_state(r, fx.ab.id, fx.s1.id)
    assert (st.state, st.flags) == ("accepted", ("SUPPORT_LOST",))
    assert fx.kinds() == ["polarity"]


def test_polarity_conflict_clears_when_absent_claim_rejected(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    n = fx.w.claim(fx.ab, fx.d, polarity="absent")
    assert fx.kinds() == ["polarity"]
    fx.w.reject_claim(n)
    assert fx.kinds() == []


def test_polarity_conflict_clears_when_relationship_rejected(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    fx.w.claim(fx.ab, fx.d, polarity="absent")
    fx.w.reject(fx.ab, fx.s1)
    assert fx.kinds() == []


def test_polarity_absent_claim_in_other_snapshot_is_no_conflict(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    fx.w.claim(fx.ab, fx.e2, polarity="absent")
    assert fx.kinds(fx.s1.id) == []
    assert fx.kinds(fx.s2.id) == ["polarity"]


def two_targets(fx: Fx) -> tuple[int, int]:
    ac = fx.w.rel("uses", fx.a, fx.c)
    fx.w.claim(fx.ab, fx.e1)
    fx.w.claim(ac, fx.d, basis="deterministic_rule")
    return fx.ab.id, ac.id


def test_cardinality_conflict_flags_both_edges(fx: Fx) -> None:
    ab, ac = two_targets(fx)
    [c] = conflicts(fx.w.build(), fx.s1.id)
    assert (c.kind, c.relationship_ids) == ("cardinality", (ab, ac))


def test_cardinality_conflict_survives_accepting_one_side(fx: Fx) -> None:
    two_targets(fx)
    fx.w.accept(fx.ab, fx.s1)
    assert fx.kinds() == ["cardinality"]


def test_cardinality_conflict_clears_when_stale_claim_rejected(fx: Fx) -> None:
    two_targets(fx)
    fx.w.reject_claim(fx.w.claims[1])  # the edge becomes unsupported
    assert fx.kinds() == []


def test_cardinality_ignores_non_single_valued_types_and_other_target_types(fx: Fx) -> None:
    r2 = fx.w.entity("req", "R")
    for t in (fx.q, r2):
        fx.w.claim(fx.w.rel("implements", fx.a, t), fx.d)
    fx.w.claim(fx.ab, fx.d)
    fx.w.claim(fx.w.rel("uses", fx.a, fx.q), fx.d)  # target type req: not in single_valued_for
    assert fx.kinds() == []


def doc_only(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    fx.w.version(fx.a, fx.e1, x=1)


def test_documentary_only_conflict(fx: Fx) -> None:
    doc_only(fx)
    [c] = conflicts(fx.w.build(), fx.s1.id)
    assert (c.kind, c.relationship_ids) == ("documentary_only", (fx.ab.id,))
    assert fx.kinds(fx.s2.id) == []  # A has no EntityVersion in S2


def test_documentary_only_not_raised_in_the_other_cases(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    assert fx.kinds() == []  # no EntityVersion for A in S1
    fx.w.version(fx.a, fx.e1, x=1)
    fx.w.claim(fx.ab, fx.e1)  # an S1-scoped claim also exists
    assert fx.kinds() == []


def test_documentary_only_not_raised_for_rule_only_unscoped_claim(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d, basis="deterministic_rule")
    fx.w.version(fx.a, fx.e1, x=1)
    assert fx.kinds() == []


def test_documentary_only_applies_to_accepted_edges_too(fx: Fx) -> None:
    doc_only(fx)
    fx.w.accept(fx.ab, fx.s1)
    assert fx.kinds() == ["documentary_only"]


def test_conflicts_sorted_and_deterministic(fx: Fx) -> None:
    ac = fx.w.rel("uses", fx.a, fx.c)
    fx.w.claim(fx.ab, fx.d)
    fx.w.claim(fx.ab, fx.d, polarity="absent")
    fx.w.claim(ac, fx.d)
    fx.w.version(fx.a, fx.e1, x=1)
    r = fx.w.build()
    first = conflicts(r, fx.s1.id)
    assert [c.kind for c in first] == [
        "polarity",
        "cardinality",
        "documentary_only",
        "documentary_only",
    ]
    assert first == conflicts(r, fx.s1.id)


def test_documentary_only_ignores_superseded_export_versions(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    fx.w.version(fx.a, fx.e1, x=1)
    assert fx.kinds() == ["documentary_only"]  # v1 not superseded: conflict
    fx.w.new_version(fx.e1)  # v2 supersedes v1 and has no EntityVersion for A
    assert fx.kinds() == []


def test_unscoped_relationship_never_gets_documentary_only(fx: Fx) -> None:
    impl = fx.w.rel("implements", fx.a, fx.q)
    fx.w.claim(impl, fx.d)
    fx.w.version(fx.a, fx.e1, x=1)
    assert fx.kinds() == []


class Fx2:
    """Source Z with single-valued `uses` to A and to B; A same_as B."""

    def __init__(self, w: World) -> None:
        self.w = w
        self.s1 = w.snapshot("s1")
        self.d = w.design()
        z = w.entity("cfg", "Z")
        a, b = w.entity("cfg", "A"), w.entity("cfg", "B")
        w.claim(w.rel("uses", z, a), self.d)
        w.claim(w.rel("uses", z, b), self.d)
        self.same = w.rel("same_as", a, b)

    def kinds(self) -> list[str]:
        return [c.kind for c in conflicts(self.w.build(), self.s1.id)]


def test_cardinality_collapses_accepted_same_as_cluster(world: World) -> None:
    f = Fx2(world)
    world.accept(f.same, f.s1)
    assert f.kinds() == []


def test_cardinality_does_not_collapse_unreviewed_same_as(world: World) -> None:
    f = Fx2(world)
    world.claim(f.same, f.d)
    assert f.kinds() == ["cardinality"]


def test_cardinality_does_not_collapse_rejected_same_as(world: World) -> None:
    f = Fx2(world)
    world.reject(f.same, f.s1)
    assert f.kinds() == ["cardinality"]


def test_cardinality_does_not_collapse_superseded_same_as(world: World) -> None:
    f = Fx2(world)
    other = world.rel("same_as", world.entities[1], world.entity("cfg", "C"))
    world.supersede(f.same, f.s1, other)
    assert f.kinds() == ["cardinality"]
