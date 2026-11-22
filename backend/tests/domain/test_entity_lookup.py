# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Issue #13: stable key triple; ambiguity is reported, never first match."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.records import AmbiguousEntity, EntityNotFound, Records, resolve_entity
from tests.domain.builders import World


def two_types() -> Records:
    w = World()
    w.entity("req", "X")  # inserted first: "first match" would be wrong
    w.entity("cfg", "X")
    w.entity("cfg", "Y")
    w.entity("cfg", "X", profile="unknown")
    return w.build()


def test_resolve_unique_match_returns_entity() -> None:
    assert resolve_entity(two_types(), "Y").key == ("synthetic", "cfg", "Y")


def test_resolve_no_match_raises_not_found() -> None:
    with pytest.raises(EntityNotFound):
        resolve_entity(two_types(), "nope")


def test_resolve_same_key_two_types_without_type_is_ambiguous() -> None:
    with pytest.raises(AmbiguousEntity) as e:
        resolve_entity(two_types(), "X", product_profile="synthetic")
    assert e.value.candidates == (("synthetic", "cfg", "X"), ("synthetic", "req", "X"))


def test_resolve_same_key_two_profiles_without_profile_is_ambiguous() -> None:
    with pytest.raises(AmbiguousEntity) as e:
        resolve_entity(two_types(), "X", entity_type="cfg")
    assert e.value.candidates == (("synthetic", "cfg", "X"), ("unknown", "cfg", "X"))


def test_resolve_full_triple_is_never_ambiguous() -> None:
    r = two_types()
    got = resolve_entity(r, "X", product_profile="synthetic", entity_type="req")
    assert got.key == ("synthetic", "req", "X")


def test_resolve_normalises_input_key() -> None:
    assert resolve_entity(two_types(), " Y ").natural_key == "Y"


def test_errors_do_not_echo_raw_input() -> None:
    r = two_types()
    with pytest.raises(EntityNotFound) as nf:
        resolve_entity(r, "SECRET-KEY")
    with pytest.raises(AmbiguousEntity) as amb:
        resolve_entity(r, "X")
    for e in (nf.value, amb.value):
        assert "SECRET-KEY" not in str(e)
        assert all("SECRET-KEY" not in str(a) for a in e.args)
    assert nf.value.args == ()


@given(st.permutations(range(4)))
def test_resolution_independent_of_entity_order(perm: list[int]) -> None:
    r = two_types()
    shuffled = Records.model_validate(
        {
            **{f: getattr(r, f) for f in Records.model_fields},
            "entities": tuple(r.entities[i] for i in perm),
        }
    )

    def cands(rec: Records) -> object:
        with pytest.raises(AmbiguousEntity) as e:
            resolve_entity(rec, "X")
        return e.value.candidates

    assert cands(r) == cands(shuffled)
    assert resolve_entity(r, "Y") == resolve_entity(shuffled, "Y")
