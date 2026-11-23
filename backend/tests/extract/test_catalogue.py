# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.extract.catalogue import (
    AttributeColumn,
    ReferenceColumn,
    SheetCatalogue,
    SheetSpec,
    header_norm,
)


def cat(*sheets: SheetSpec, profile: str = "synthetic") -> SheetCatalogue:
    return SheetCatalogue.model_validate(
        {"product_profile": profile, "method": "test_xlsx@1", "sheets": sheets}
    )


def spec(**kw: Any) -> SheetSpec:
    return SheetSpec.model_validate({"entity_type": "limit", "key_header": "limit_id", **kw})


def attr(h: str) -> AttributeColumn:
    return AttributeColumn(header=h, name=h)


def ref(h: str, **kw: Any) -> ReferenceColumn:
    return ReferenceColumn.model_validate(
        {"header": h, "relationship_type": "contains", "target_type": "limit", **kw}
    )


def test_header_norm() -> None:
    for s in (" Threshold Hours ", "threshold-hours", "THRESHOLD_HOURS"):
        assert header_norm(s) == "threshold_hours"
    assert header_norm("a__b") == "a_b"


def test_valid_minimal() -> None:
    assert cat(spec(attributes=(attr("hours"),)))


def test_duplicate_header_in_sheet_rejected() -> None:
    with pytest.raises(ValidationError):
        cat(spec(attributes=(attr("Hours"),), references=(ref("hours"),)))


def test_reserved_header_rejected() -> None:
    with pytest.raises(ValidationError):
        cat(spec(attributes=(attr("Product Profile"),)))


def test_required_header_must_be_declared() -> None:
    with pytest.raises(ValidationError):
        cat(spec(required_headers=("nope",)))
    assert cat(spec(required_headers=("hours",), attributes=(attr("hours"),)))


def test_duplicate_entity_type_or_key_header_rejected() -> None:
    other = spec(key_header="other_id", attributes=(attr("x"),))
    with pytest.raises(ValidationError):  # same entity type
        cat(spec(attributes=(attr("hours"),)), other)
    clash = spec(entity_type="bundle", key_header="Limit ID", attributes=(attr("x"),))
    with pytest.raises(ValidationError):  # same key header after header_norm
        cat(spec(attributes=(attr("hours"),)), clash)


def test_overlapping_signature_rejected() -> None:
    b = SheetSpec(entity_type="bundle", key_header="bundle_id", references=(ref("limit_id"),))
    with pytest.raises(ValidationError):
        cat(spec(), b)
    a = spec(required_headers=("hours",), attributes=(attr("hours"),))
    assert cat(a, b)


def test_unknown_profile_rejected() -> None:
    with pytest.raises(ValidationError):
        cat(spec(), profile="unknown")
