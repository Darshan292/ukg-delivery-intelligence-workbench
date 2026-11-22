# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Typed records of the canonical relationship model (rev 2.1). Pure, in-memory, no I/O."""

import math
import re
from decimal import Decimal
from typing import Annotated, Final, Literal, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


class Record(BaseModel):
    # hide_input_in_errors: untrusted strings must never be echoed in error text
    # revalidate_instances: a leaf made by an unvalidated copy is re-checked inside Records
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )


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

# Numbers are Decimal only (decision 0003 Q10): parsed from source cell text, never float.
Number = Annotated[Decimal, Field(allow_inf_nan=False)]
JsonScalar = str | Number | bool | None
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


def number_from_cell_text(text: str) -> Decimal:
    """Strict plain decimal: optional sign, digits, optional point and exponent."""
    t = text.strip()
    if not _NUMBER.fullmatch(t):
        raise ValueError("number: not a plain decimal number")
    return Decimal(t)


def number_from_cell_value(v: int | float) -> Decimal:
    """For cells a reader returns as int or float; `repr` keeps the shortest round-trip text."""
    if isinstance(v, bool) or (isinstance(v, float) and not math.isfinite(v)):
        raise ValueError("number: not a finite number")
    return Decimal(repr(v))


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
    reason: Literal["missing_target", "uncatalogued_type", "unknown_profile"]


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


class Claim(Record):
    id: Id
    relationship_id: Id
    basis: Basis
    polarity: Polarity
    method: Versioned
    confidence: Annotated[Decimal, Field(ge=0, le=1)] | None = None
    model_id: NonBlank | None = None
    prompt_version: NonBlank | None = None
    scope_snapshot_id: Id | None
    locator_ids: SortedIds
    created_at: AwareDatetime

    @model_validator(mode="after")
    def _basis_fields(self) -> Self:
        llm = self.basis == "llm_suggestion"
        # owner Q3: explicit claims carry no confidence (a number on a parsed reference is invented)
        if (self.basis == "explicit_source") == (self.confidence is not None):
            raise ValueError(
                "claim: confidence required for rule/llm claims, forbidden for explicit"
            )
        if llm != (self.model_id is not None and self.prompt_version is not None) or (
            not llm and (self.model_id is not None or self.prompt_version is not None)
        ):
            raise ValueError("claim: model_id and prompt_version are for llm claims only")
        return self

    @property
    def dedup_key(self) -> tuple[int, str, str, str, tuple[int, ...]]:
        # RM e; the locator_set_hash is a Slice 5 storage detail, the sorted tuple is the key here
        return (self.relationship_id, self.basis, self.method, self.polarity, self.locator_ids)


class _EventBase(Record):
    id: Id
    at: AwareDatetime
    actor_id: Id


class ClaimReviewEvent(_EventBase):
    target_kind: Literal["claim"]
    claim_id: Id
    verdict: Literal["rejected", "reinstated"]
    reason: NonBlank


class RelationshipReviewEvent(_EventBase):
    target_kind: Literal["relationship"]
    relationship_id: Id
    scope_snapshot_id: Id | None
    verdict: Literal["accepted", "rejected", "superseded"]
    reason: NonBlank | None = None
    successor_relationship_id: Id | None = None

    @model_validator(mode="after")
    def _verdict_rules(self) -> Self:
        if self.verdict != "accepted" and self.reason is None:
            raise ValueError("review: reason required for every verdict except accepted")
        if (self.verdict == "superseded") != (self.successor_relationship_id is not None):
            raise ValueError("review: successor required for, and only for, superseded")
        if self.successor_relationship_id == self.relationship_id:
            raise ValueError("review: successor cannot be the relationship itself")
        return self


# One id space for both kinds (one table in Slice 5); ordering key is (at, id).
ReviewEvent = Annotated[
    ClaimReviewEvent | RelationshipReviewEvent, Field(discriminator="target_kind")
]
