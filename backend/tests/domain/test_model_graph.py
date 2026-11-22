# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import TypeAdapter, ValidationError

from app.domain.model import (
    Attribute,
    Catalogue,
    Entity,
    EntityTypeSpec,
    EntityVersion,
    JsonScalar,
    Relationship,
    RelationshipTypeSpec,
    UnresolvedReference,
)

T = datetime(2026, 1, 1, tzinfo=UTC)


def ent(**kw: Any) -> Entity:
    d: dict[str, Any] = {
        "id": 1,
        "product_profile": "synthetic",
        "entity_type": "cfg",
        "natural_key": "OT-1",
    }
    return Entity(**{**d, **kw})


def ev(**kw: Any) -> EntityVersion:
    d: dict[str, Any] = {
        "id": 1,
        "entity_id": 1,
        "document_version_id": 1,
        "snapshot_id": None,
        "attributes": (),
        "locator_ids": (1,),
    }
    return EntityVersion(**{**d, **kw})


def rel(**kw: Any) -> Relationship:
    d: dict[str, Any] = {
        "id": 1,
        "type": "uses",
        "source_entity_id": 1,
        "target_entity_id": 2,
        "qualifier": None,
        "created_at": T,
    }
    return Relationship(**{**d, **kw})


def test_entity_key_must_be_normalised() -> None:
    with pytest.raises(ValidationError) as e:
        ent(natural_key=" OT-1")
    assert "OT-1" not in str(e.value)
    assert ent().key == ("synthetic", "cfg", "OT-1")


def test_entity_is_frozen() -> None:
    with pytest.raises(ValidationError):
        ent().natural_key = "x"  # pyright: ignore[reportAttributeAccessIssue]


def test_entity_version_needs_a_locator() -> None:
    with pytest.raises(ValidationError):
        ev(locator_ids=())


def test_entity_version_attribute_locator_must_be_listed() -> None:
    with pytest.raises(ValidationError):
        ev(attributes=(Attribute(name="a", value=1, locator_id=9),), locator_ids=(1,))


def test_entity_version_attribute_names_unique_and_sorted() -> None:
    a = Attribute(name="a", value=1, locator_id=1)
    b = Attribute(name="b", value=2, locator_id=1)
    assert ev(attributes=(b, a)).attributes == (a, b)
    with pytest.raises(ValidationError):
        ev(attributes=(a, a))


@pytest.mark.parametrize("v", [40, 37.5, "x", True, None])
def test_attribute_value_accepts_scalar(v: object) -> None:
    assert Attribute(name="a", value=v, locator_id=1).value == v  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize("v", [[1], {"a": 1}, float("nan")])
def test_attribute_value_rejects_non_scalar(v: object) -> None:
    with pytest.raises(ValidationError):
        Attribute(name="a", value=v, locator_id=1)  # pyright: ignore[reportArgumentType]


def test_json_scalar_alias_exists() -> None:
    assert TypeAdapter(JsonScalar).validate_python(None) is None


def test_relationship_rejects_self_loop() -> None:
    with pytest.raises(ValidationError):
        rel(target_entity_id=1)


def test_relationship_key() -> None:
    assert rel().key == ("uses", 1, 2, None)
    assert rel(qualifier="q").key == ("uses", 1, 2, "q")


@pytest.mark.parametrize(
    ("reason", "ok"), [("missing_target", True), ("uncatalogued_type", True), ("other", False)]
)
def test_unresolved_reference_reasons(reason: str, ok: bool) -> None:
    d: dict[str, Any] = {
        "id": 1,
        "holder_entity_id": 1,
        "raw_reference": "r",
        "locator_id": 1,
        "reason": reason,
    }
    d2: dict[str, Any] = {**d, "reason": "missing_target", "raw_reference": " "}
    if ok:
        assert UnresolvedReference(**d)
    else:
        with pytest.raises(ValidationError):
            UnresolvedReference(**d)
    with pytest.raises(ValidationError):
        UnresolvedReference(**d2)


def test_catalogue_names_unique() -> None:
    e = EntityTypeSpec(name="cfg", snapshot_scoped=True)
    r = RelationshipTypeSpec(name="uses")
    assert Catalogue(product_profile="synthetic", entity_types=(e,), relationship_types=(r,))
    with pytest.raises(ValidationError):
        Catalogue(product_profile="synthetic", entity_types=(e, e), relationship_types=())
    with pytest.raises(ValidationError):
        Catalogue(product_profile="synthetic", entity_types=(), relationship_types=(r, r))
    with pytest.raises(ValidationError):
        Catalogue(product_profile="unknown", entity_types=(), relationship_types=())


def test_sorted_unique_id_tuples() -> None:
    assert ev(locator_ids=(3, 1)).locator_ids == (1, 3)
    with pytest.raises(ValidationError):
        ev(locator_ids=(1, 1))
