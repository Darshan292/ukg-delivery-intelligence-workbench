# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Tracer subset; replaced by the D3 model in Slice 1.

Only entity, relationship and evidence_locator exist. Documents, versions, claims, review
events and snapshots (docs/architecture/relationship-model.md) arrive in Slice 1, as do
the final ID scheme and locator ownership. Rows here are fictional fixtures, not claims.
"""

from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Identity, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Entity(Base):
    __tablename__ = "entity"
    __table_args__ = (
        UniqueConstraint("product_profile", "entity_type", "natural_key"),
        CheckConstraint(
            "product_profile in ('synthetic','ukg_pro_wfm','workforce_central','unknown')",
            name="ck_entity_product_profile",
        ),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    product_profile: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    natural_key: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)


class Relationship(Base):
    __tablename__ = "relationship"
    __table_args__ = (
        UniqueConstraint("type", "source_entity_id", "target_entity_id"),
        CheckConstraint("source_entity_id <> target_entity_id", name="ck_relationship_no_self"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    type: Mapped[str] = mapped_column(Text)
    source_entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))
    target_entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"))


class EvidenceLocator(Base):
    __tablename__ = "evidence_locator"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    relationship_id: Mapped[int] = mapped_column(ForeignKey("relationship.id"))
    kind: Mapped[str] = mapped_column(Text)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONB)
    snippet: Mapped[str] = mapped_column(Text)
