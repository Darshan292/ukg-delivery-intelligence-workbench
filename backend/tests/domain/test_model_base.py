# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
from typing import get_args

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import TypeAdapter, ValidationError

from app.domain.model import (
    BASIS_RANK,
    Basis,
    Id,
    ProductProfile,
    Record,
    Versioned,
    normalise_key_v1,
)


class _P(Record):
    p: ProductProfile


class _I(Record):
    i: Id


def test_product_profiles_are_exactly_four() -> None:
    assert get_args(ProductProfile) == ("synthetic", "ukg_pro_wfm", "workforce_central", "unknown")


@pytest.mark.parametrize("v", ["Synthetic", ""])
def test_profile_is_case_sensitive(v: str) -> None:
    with pytest.raises(ValidationError):
        _P(p=v)  # pyright: ignore[reportArgumentType]


def test_record_is_frozen_and_forbids_extra() -> None:
    x = _I(i=1)
    with pytest.raises(ValidationError):
        x.i = 2  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(ValidationError) as e:
        _I(i=1, z=2)  # pyright: ignore[reportCallIssue]
    assert e.value.errors()[0]["type"] == "extra_forbidden"


def test_record_is_strict() -> None:
    for bad in ("1", True, 0):
        with pytest.raises(ValidationError):
            _I(i=bad)  # pyright: ignore[reportArgumentType]
    assert _I(i=1).i == 1


def test_basis_rank_order() -> None:
    r = BASIS_RANK
    assert r["explicit_source"] > r["deterministic_rule"] > r["llm_suggestion"]
    assert set(r) == set(get_args(Basis))


@given(st.text())
def test_normalise_key_v1_trims_only(s: str) -> None:
    assert normalise_key_v1(s) == s.strip()
    assert normalise_key_v1(normalise_key_v1(s)) == normalise_key_v1(s)
    assert normalise_key_v1("Ab") == "Ab"


def test_versioned_requires_name_at_version() -> None:
    ta = TypeAdapter(Versioned)
    assert ta.validate_python("xlsx-ref@1.0.0")
    for bad in ("xlsx-ref", "@1", "a@", "a@b@c", "a b@1"):
        with pytest.raises(ValidationError):
            ta.validate_python(bad)
