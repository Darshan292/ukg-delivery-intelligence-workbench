# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""FICTIONAL: not UKG behaviour."""

import pytest

from app.domain.derive import Cluster, conflicts, identity_clusters
from app.domain.model import JsonScalar
from tests.domain.builders import World


class Fx:
    def __init__(self, w: World) -> None:
        self.w = w
        self.s1, self.s2 = w.snapshot("s1"), w.snapshot("s2")
        self.e1, self.e2, self.d = w.export(self.s1), w.export(self.s2), w.design()
        self.a, self.b, self.c = w.entity("cfg", "A"), w.entity("cfg", "B"), w.entity("cfg", "C")
        self.ab = w.rel("same_as", self.a, self.b)
        self.bc = w.rel("same_as", self.b, self.c)
        self.ac = w.rel("same_as", self.a, self.c)

    def kinds(self) -> list[tuple[str, str | None]]:
        return [(c.kind, c.attribute) for c in conflicts(self.w.build(), self.s1.id)]


@pytest.fixture
def fx(world: World) -> Fx:
    return Fx(world)


def test_accepted_same_as_forms_cluster_with_smallest_key_representative(fx: Fx) -> None:
    fx.w.accept(fx.ab, fx.s1)
    fx.w.accept(fx.bc, fx.s1)
    assert identity_clusters(fx.w.build(), fx.s1.id) == (
        Cluster(
            member_ids=(fx.a.id, fx.b.id, fx.c.id), representative_id=fx.a.id, conflicted=False
        ),
    )


def test_unreviewed_same_as_does_not_join_cluster(fx: Fx) -> None:
    fx.w.claim(fx.ab, fx.d)
    assert identity_clusters(fx.w.build(), fx.s1.id) == ()


def test_clusters_are_per_snapshot(fx: Fx) -> None:
    fx.w.accept(fx.ab, fx.s1)
    r = fx.w.build()
    assert len(identity_clusters(r, fx.s1.id)) == 1
    assert identity_clusters(r, fx.s2.id) == ()


def conflicted(fx: Fx) -> None:
    fx.w.accept(fx.ab, fx.s1)
    fx.w.accept(fx.bc, fx.s1)
    fx.w.reject(fx.ac, fx.s1)


def test_identity_conflict(fx: Fx) -> None:
    conflicted(fx)
    r = fx.w.build()
    [cl] = identity_clusters(r, fx.s1.id)
    assert cl.conflicted
    [c] = conflicts(r, fx.s1.id)
    assert c.kind == "identity"
    assert c.relationship_ids == (fx.ab.id, fx.bc.id, fx.ac.id)
    assert c.entity_ids == (fx.a.id, fx.b.id, fx.c.id)


def test_identity_conflict_clears_when_rejection_superseded_by_accept(fx: Fx) -> None:
    conflicted(fx)
    fx.w.accept(fx.ac, fx.s1)  # later event on A~C
    r = fx.w.build()
    assert conflicts(r, fx.s1.id) == ()
    assert not identity_clusters(r, fx.s1.id)[0].conflicted


def two_exports(fx: Fx, v1: JsonScalar, v2: JsonScalar, name: str = "q") -> tuple[int, int]:
    e1b = fx.w.export(fx.s1)
    x = fx.w.entity("cfg", "X")
    ev1 = fx.w.version(x, fx.e1, **{name: v1})
    ev2 = fx.w.version(x, e1b, **{name: v2})
    return ev1.id, ev2.id


def test_attribute_conflict_two_exports_in_same_snapshot(fx: Fx) -> None:
    v1, v2 = two_exports(fx, 40, 37.5)
    [c] = conflicts(fx.w.build(), fx.s1.id)
    assert (c.kind, c.attribute, c.entity_version_ids) == ("attribute", "q", (v1, v2))


def test_attribute_no_conflict_for_documentary_values(fx: Fx) -> None:
    x = fx.w.entity("cfg", "X")
    fx.w.version(x, fx.e1, q=40)
    fx.w.version(x, fx.d, q=37.5)  # unscoped design document
    assert fx.kinds() == []


def test_attribute_no_conflict_for_display_only_attribute(fx: Fx) -> None:
    two_exports(fx, "a", "b", name="label")
    assert fx.kinds() == []


@pytest.mark.parametrize(
    ("a", "b", "conflict"),
    [(True, 1, True), (1, True, True), (40, 40.0, False), (None, None, False), ("x", "x", False)],
)
def test_attribute_bool_is_not_number(fx: Fx, a: JsonScalar, b: JsonScalar, conflict: bool) -> None:
    two_exports(fx, a, b)
    assert (fx.kinds() == [("attribute", "q")]) is conflict


def test_attribute_missing_in_one_version_is_no_conflict(fx: Fx) -> None:
    e1b = fx.w.export(fx.s1)
    x = fx.w.entity("cfg", "X")
    fx.w.version(x, fx.e1, q=40)
    fx.w.version(x, e1b, other=1)
    assert fx.kinds() == []


def test_attribute_superseded_version_excluded(fx: Fx) -> None:
    x = fx.w.entity("cfg", "X")
    fx.w.version(x, fx.e1, q=40)
    v2 = fx.w.new_version(fx.e1)
    fx.w.version(x, v2, q=37.5)
    assert fx.kinds() == []
