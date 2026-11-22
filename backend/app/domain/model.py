# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Typed records of the canonical relationship model (rev 2.1). Pure, in-memory, no I/O."""

from typing import Annotated, Final, Literal, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StringConstraints,
    model_validator,
)


class Record(BaseModel):
    # hide_input_in_errors: untrusted strings must never be echoed in error text
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, hide_input_in_errors=True)


Id = Annotated[int, Field(ge=1)]
ProductProfile = Literal["synthetic", "ukg_pro_wfm", "workforce_central", "unknown"]
Basis = Literal["explicit_source", "deterministic_rule", "llm_suggestion"]
BASIS_RANK: Final[dict[Basis, int]] = {
    "explicit_source": 3,
    "deterministic_rule": 2,
    "llm_suggestion": 1,
}
Polarity = Literal["present", "absent"]
NonBlank = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Versioned = Annotated[str, StringConstraints(pattern=r"^[^@\s]+@[^@\s]+$")]  # name@version
SAME_AS: Final = "same_as"
KEY_NORMALISATION: Final = "v1"


def normalise_key_v1(raw: str) -> str:
    """Trim whitespace only (RM g): no case or punctuation folding.

    Strings compare with Python `<`; code-point order equals UTF-8 byte order, which is the
    byte order the docs require.
    """
    return raw.strip()


Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class Actor(Record):
    id: Id
    kind: Literal["human", "service"]
    display_name: NonBlank
    roles: frozenset[NonBlank]

    @property
    def is_reviewer(self) -> bool:
        return self.kind == "human" and "reviewer" in self.roles


class Snapshot(Record):
    id: Id
    product_profile: ProductProfile
    environment: NonBlank
    label: NonBlank
    captured_at: AwareDatetime


class Document(Record):
    id: Id
    product_profile: ProductProfile
    title: NonBlank


class DocumentVersion(Record):
    id: Id
    document_id: Id
    sha256: Sha256Hex
    snapshot_id: Id | None
    supersedes_version_id: Id | None
    declared_by: Id
    uploaded_at: AwareDatetime

    @model_validator(mode="after")
    def _not_self(self) -> Self:
        if self.supersedes_version_id == self.id:
            raise ValueError("lineage: version cannot supersede itself")
        return self


def _sorted_unique(ids: tuple[int, ...]) -> tuple[int, ...]:
    if len(set(ids)) != len(ids):
        raise ValueError("ids: duplicates not allowed")
    return tuple(sorted(ids))


SortedIds0 = Annotated[tuple[Id, ...], AfterValidator(_sorted_unique)]
SortedIds = Annotated[SortedIds0, Field(min_length=1)]

JsonScalar = str | int | FiniteFloat | bool | None


class Entity(Record):
    id: Id
    product_profile: ProductProfile
    entity_type: NonBlank
    natural_key: NonBlank

    @model_validator(mode="after")
    def _normalised(self) -> Self:
        if self.natural_key != normalise_key_v1(self.natural_key):
            raise ValueError("entity: natural_key not normalised")
        return self

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.product_profile, self.entity_type, self.natural_key)


class Attribute(Record):
    name: NonBlank
    value: JsonScalar
    locator_id: Id


class EntityVersion(Record):
    id: Id
    entity_id: Id
    document_version_id: Id
    snapshot_id: Id | None
    # tuple, not dict: a dict inside a frozen model is still mutable
    attributes: tuple[Attribute, ...]
    locator_ids: SortedIds

    @model_validator(mode="after")
    def _attributes(self) -> Self:
        names = [a.name for a in self.attributes]
        if len(set(names)) != len(names):
            raise ValueError("entity_version: duplicate attribute names")
        if any(a.locator_id not in self.locator_ids for a in self.attributes):
            raise ValueError("entity_version: attribute locator not listed")
        object.__setattr__(self, "attributes", tuple(sorted(self.attributes, key=lambda a: a.name)))
        return self


class Relationship(Record):
    id: Id
    type: NonBlank
    source_entity_id: Id
    target_entity_id: Id
    qualifier: NonBlank | None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def _no_self_loop(self) -> Self:
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("relationship: self loop")
        return self

    @property
    def key(self) -> tuple[str, int, int, str | None]:
        return (self.type, self.source_entity_id, self.target_entity_id, self.qualifier)


class UnresolvedReference(Record):
    id: Id
    holder_entity_id: Id
    raw_reference: NonBlank
    locator_id: Id
    reason: Literal["missing_target", "uncatalogued_type"]


class EntityTypeSpec(Record):
    name: NonBlank
    snapshot_scoped: bool
    display_only_attributes: tuple[NonBlank, ...] = ()


class RelationshipTypeSpec(Record):
    name: NonBlank
    qualifier_required: bool = False
    single_valued_for: tuple[tuple[NonBlank, NonBlank], ...] = ()  # (source type, target type)


class Catalogue(Record):
    product_profile: ProductProfile
    entity_types: tuple[EntityTypeSpec, ...]
    relationship_types: tuple[RelationshipTypeSpec, ...]

    @model_validator(mode="after")
    def _names(self) -> Self:
        if self.product_profile == "unknown":
            raise ValueError("catalogue: unknown profile has no catalogue")
        for names in (
            [t.name for t in self.entity_types],
            [t.name for t in self.relationship_types],
        ):
            if len(set(names)) != len(names):
                raise ValueError("catalogue: duplicate type names")
        return self
