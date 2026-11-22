# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""SQLAlchemy mapping of the D3 schema (relationship-model rev 2.1; migration 0002).

The migration is the source of truth for constraints and triggers; these classes mirror the
tables so the API and Alembic's `compare_metadata` can see them. Ids are supplied by the writer
and equal the domain ids; only `review_event.id` and `.at` are assigned by the database.
Rows are append-only: nothing here is ever updated or deleted.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_TZ = DateTime(timezone=True)
_C = Text(collation="C")
_PK = BigInteger


class Base(DeclarativeBase):
    pass


class Actor(Base):
    __tablename__ = "actor"
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=False)
    kind: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    roles: Mapped[list[str]] = mapped_column(ARRAY(Text))


class CatalogueEntityType(Base):
    __tablename__ = "catalogue_entity_type"
    product_profile: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(_C, primary_key=True)
    snapshot_scoped: Mapped[bool] = mapped_column(Boolean)
    display_only_attributes: Mapped[list[str]] = mapped_column(ARRAY(Text))


class CatalogueRelationshipType(Base):
    __tablename__ = "catalogue_relationship_type"
    product_profile: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(_C, primary_key=True)
    qualifier_required: Mapped[bool] = mapped_column(Boolean)
    single_valued_for: Mapped[Any] = mapped_column(JSONB)


class Snapshot(Base):
    __tablename__ = "snapshot"
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=False)
    product_profile: Mapped[str] = mapped_column(Text)
    environment: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(_TZ)


class Document(Base):
    __tablename__ = "document"
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=False)
    product_profile: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)


class DocumentVersion(Base):
    __tablename__ = "document_version"
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=False)
    document_id: Mapped[int] = mapped_column(_PK, ForeignKey("document.id"))
    sha256: Mapped[str] = mapped_column(Text, unique=True)
    snapshot_id: Mapped[int | None] = mapped_column(_PK, ForeignKey("snapshot.id"))
    supersedes_version_id: Mapped[int | None] = mapped_column(
        _PK, ForeignKey("document_version.id"), unique=True
    )
    declared_by: Mapped[int] = mapped_column(_PK, ForeignKey("actor.id"))
    uploaded_at: Mapped[datetime] = mapped_column(_TZ)


class EvidenceLocator(Base):
    __tablename__ = "evidence_locator"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id", "kind", "extractor", "locator", name="uq_locator_content"
        ),
    )
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=False)
    document_version_id: Mapped[int] = mapped_column(_PK, ForeignKey("document_version.id"))
    kind: Mapped[str] = mapped_column(Text)
    locator: Mapped[Any] = mapped_column(JSONB)
    snippet: Mapped[str] = mapped_column(Text)
    extractor: Mapped[str] = mapped_column(Text)
    extracted_at: Mapped[datetime] = mapped_column(_TZ)


class Entity(Base):
    __tablename__ = "entity"
    __table_args__ = (
        UniqueConstraint("product_profile", "entity_type", "natural_key", name="uq_entity_key"),
        ForeignKeyConstraint(
            ["catalogue_profile", "entity_type"],
            ["catalogue_entity_type.product_profile", "catalogue_entity_type.name"],
        ),
    )
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=False)
    product_profile: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(_C)
    natural_key: Mapped[str] = mapped_column(_C)
    # unknown-profile entities have no catalogue (decision 0003 Q7): NULL skips the FK
    catalogue_profile: Mapped[str | None] = mapped_column(
        Text, Computed("NULLIF(product_profile, 'unknown')", persisted=True)
    )


class EntityVersion(Base):
    __tablename__ = "entity_version"
    __table_args__ = (
        UniqueConstraint("entity_id", "document_version_id", name="uq_entity_version"),
    )
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=False)
    entity_id: Mapped[int] = mapped_column(_PK, ForeignKey("entity.id"))
    document_version_id: Mapped[int] = mapped_column(_PK, ForeignKey("document_version.id"))
    snapshot_id: Mapped[int | None] = mapped_column(_PK, ForeignKey("snapshot.id"))
    attributes: Mapped[Any] = mapped_column(JSONB)
    locator_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger))


class Relationship(Base):
    __tablename__ = "relationship"
    __table_args__ = (
        UniqueConstraint(
            "type",
            "source_entity_id",
            "target_entity_id",
            "qualifier",
            name="uq_relationship_key",
            postgresql_nulls_not_distinct=True,
        ),
    )
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=False)
    type: Mapped[str] = mapped_column(_C)
    source_entity_id: Mapped[int] = mapped_column(_PK, ForeignKey("entity.id"))
    target_entity_id: Mapped[int] = mapped_column(_PK, ForeignKey("entity.id"))
    qualifier: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_TZ)


class Claim(Base):
    __tablename__ = "claim"
    __table_args__ = (
        UniqueConstraint(
            "relationship_id",
            "basis",
            "method",
            "polarity",
            "locator_set_hash",
            name="uq_claim_dedup",
        ),
    )
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=False)
    relationship_id: Mapped[int] = mapped_column(_PK, ForeignKey("relationship.id"))
    basis: Mapped[str] = mapped_column(Text)
    polarity: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric)
    model_id: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    scope_snapshot_id: Mapped[int | None] = mapped_column(_PK, ForeignKey("snapshot.id"))
    # owner question S5-Q3 (pending): an array column instead of a ClaimEvidence table;
    # a trigger sorts it and sets the hash
    locator_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger))
    locator_set_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_TZ)


class ReviewEvent(Base):
    __tablename__ = "review_event"
    id: Mapped[int] = mapped_column(_PK, Identity(always=True), primary_key=True)
    target_kind: Mapped[str] = mapped_column(Text)
    claim_id: Mapped[int | None] = mapped_column(_PK, ForeignKey("claim.id"))
    relationship_id: Mapped[int | None] = mapped_column(_PK, ForeignKey("relationship.id"))
    scope_snapshot_id: Mapped[int | None] = mapped_column(_PK, ForeignKey("snapshot.id"))
    verdict: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    successor_relationship_id: Mapped[int | None] = mapped_column(
        _PK, ForeignKey("relationship.id")
    )
    actor_id: Mapped[int] = mapped_column(_PK, ForeignKey("actor.id"))
    at: Mapped[datetime] = mapped_column(_TZ, server_default=func.now())


class UnresolvedReference(Base):
    __tablename__ = "unresolved_reference"
    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=False)
    holder_entity_id: Mapped[int] = mapped_column(_PK, ForeignKey("entity.id"))
    raw_reference: Mapped[str] = mapped_column(Text)
    locator_id: Mapped[int] = mapped_column(_PK, ForeignKey("evidence_locator.id"))
    reason: Mapped[str] = mapped_column(Text)
