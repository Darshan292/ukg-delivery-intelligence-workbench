# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Tracer graph: entity, relationship, evidence_locator.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("product_profile", sa.Text, nullable=False),
        sa.Column("entity_type", sa.Text, nullable=False),
        sa.Column("natural_key", sa.Text, nullable=False),
        sa.Column("label", sa.Text, nullable=False),
        sa.UniqueConstraint("product_profile", "entity_type", "natural_key"),
        sa.CheckConstraint(
            "product_profile in ('synthetic','ukg_pro_wfm','workforce_central','unknown')",
            name="ck_entity_product_profile",
        ),
    )
    op.create_table(
        "relationship",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("source_entity_id", sa.BigInteger, sa.ForeignKey("entity.id"), nullable=False),
        sa.Column("target_entity_id", sa.BigInteger, sa.ForeignKey("entity.id"), nullable=False),
        sa.UniqueConstraint("type", "source_entity_id", "target_entity_id"),
        sa.CheckConstraint("source_entity_id <> target_entity_id", name="ck_relationship_no_self"),
    )
    op.create_table(
        "evidence_locator",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "relationship_id", sa.BigInteger, sa.ForeignKey("relationship.id"), nullable=False
        ),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("locator", JSONB, nullable=False),
        sa.Column("snippet", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evidence_locator")
    op.drop_table("relationship")
    op.drop_table("entity")
