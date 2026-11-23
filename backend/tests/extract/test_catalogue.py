# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.model import Catalogue
from app.extract.catalogue import (
    AttributeColumn,
    CatalogueMismatch,
    ReferenceColumn,
    SheetCatalogue,
    SheetSpec,
    check_against,
    header_norm,
)
from tests.extract.helpers import DOMAIN, SHEETS


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


# --- check_against ---


def test_fixture_catalogue_fits() -> None:
    check_against(SHEETS, DOMAIN)


def _sheets(**edit: Any) -> SheetCatalogue:
    return SHEETS.model_copy(update=edit)


def _replace_spec(which: str, **kw: Any) -> SheetCatalogue:
    new = tuple(s.model_copy(update=kw) if s.entity_type == which else s for s in SHEETS.sheets)
    return _sheets(sheets=new)


def _ref0(which: str, **kw: Any) -> SheetCatalogue:
    s = next(s for s in SHEETS.sheets if s.entity_type == which)
    refs = (s.references[0].model_copy(update=kw), *s.references[1:])
    return _replace_spec(which, references=refs)


def _check_ref(**kw: Any) -> SheetCatalogue:
    s = next(s for s in SHEETS.sheets if s.entity_type == "check")
    refs = tuple(
        r.model_copy(update=kw) if r.relationship_type == "asserts_value" else r
        for r in s.references
    )
    return _replace_spec("check", references=refs)


BAD: dict[str, SheetCatalogue] = {
    "unknown_entity_type": _replace_spec("limit", entity_type="gadget"),
    "unknown_relationship_type": _ref0("bundle", relationship_type="gizmo"),
    "unknown_target_type": _ref0("bundle", target_type="gadget"),
    "qualifier_on_plain_type": _ref0("bundle", qualifier_header="extra"),
    "missing_qualifier_header": _check_ref(qualifier_header=None),
    "display_only_must_be_declared": _replace_spec(
        "limit", attributes=(AttributeColumn(header="hours", name="hours"),)
    ),
    "profile_mismatch": _sheets(product_profile="ukg_pro_wfm"),
}


@pytest.mark.parametrize("case", sorted(BAD))
def test_mismatch_raises_without_header_text(case: str) -> None:
    with pytest.raises(CatalogueMismatch) as e:
        check_against(BAD[case], DOMAIN)
    msg = str(e.value)
    for h in ("limit_id", "hours", "label", "asserts_attribute", "gadget", "gizmo", "extra"):
        assert h not in msg


def test_domain_is_a_catalogue() -> None:
    assert isinstance(DOMAIN, Catalogue)
