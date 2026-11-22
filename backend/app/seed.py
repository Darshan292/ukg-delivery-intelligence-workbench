# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Idempotent fictional tracer fixture. CLI: python -m app.seed (owner DATABASE_URL).

Everything here is FICTIONAL. The records are built through the domain, so the fixture obeys
the same rules as real data.
"""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import Connection, select

from app import models
from app.config import get_settings
from app.db import create_db_engine
from app.domain.locators import XlsxCell
from app.domain.model import (
    Actor,
    Catalogue,
    Claim,
    Document,
    DocumentVersion,
    Entity,
    EntityTypeSpec,
    Relationship,
    RelationshipTypeSpec,
)
from app.domain.records import Records
from app.store import save

T0 = datetime(2026, 1, 1, tzinfo=UTC)
SERVICE_ID, REVIEWER_ID = 1, 2
EXTRACTOR = "tracer-seed@1"
# (source, type, target, cell)
LINKS = [("RULE-T1", "implements", "REQ-T1", "B2"), ("TEST-T1", "verifies", "RULE-T1", "B3")]
ENTITIES = [("REQ-T1", "requirement"), ("RULE-T1", "rule"), ("TEST-T1", "test")]


def build_tracer_records() -> Records:
    ents = {
        key: Entity(id=i, product_profile="synthetic", entity_type=t, natural_key=key)
        for i, (key, t) in enumerate(ENTITIES, 1)
    }
    locs = [
        XlsxCell(
            id=i,
            document_version_id=1,
            snippet=f"{src} {rtype} {tgt} (FICTIONAL, fake locator)",
            extractor=EXTRACTOR,
            extracted_at=T0,
            kind="xlsx_cell",
            sheet="Links",
            cell=cell,
        )
        for i, (src, rtype, tgt, cell) in enumerate(LINKS, 1)
    ]
    rels = [
        Relationship(
            id=i,
            type=rtype,
            source_entity_id=ents[src].id,
            target_entity_id=ents[tgt].id,
            qualifier=None,
            created_at=T0,
        )
        for i, (src, rtype, tgt, _cell) in enumerate(LINKS, 1)
    ]
    return Records(
        catalogues=(
            Catalogue(
                product_profile="synthetic",
                entity_types=(
                    EntityTypeSpec(name="requirement", snapshot_scoped=False),
                    EntityTypeSpec(name="rule", snapshot_scoped=True),
                    EntityTypeSpec(name="test", snapshot_scoped=False),
                ),
                relationship_types=(
                    RelationshipTypeSpec(name="implements"),
                    RelationshipTypeSpec(name="verifies"),
                ),
            ),
        ),
        actors=(
            Actor(id=SERVICE_ID, kind="service", display_name="tracer-seed", roles=frozenset()),
            Actor(
                id=REVIEWER_ID,
                kind="human",
                display_name="Local reviewer (fictional)",
                roles=frozenset({"reviewer"}),
            ),
        ),
        documents=(Document(id=1, product_profile="synthetic", title="tracer-fixture.xlsx"),),
        document_versions=(
            DocumentVersion(
                id=1,
                document_id=1,
                sha256=hashlib.sha256(b"tracer-fixture (FICTIONAL)").hexdigest(),
                snapshot_id=None,
                supersedes_version_id=None,
                declared_by=SERVICE_ID,
                uploaded_at=T0,
            ),
        ),
        locators=tuple(locs),
        entities=tuple(ents.values()),
        relationships=tuple(rels),
        claims=tuple(
            Claim(
                id=rel.id,
                relationship_id=rel.id,
                basis="explicit_source",
                polarity="present",
                method=EXTRACTOR,
                scope_snapshot_id=None,
                locator_ids=(rel.id,),
                created_at=T0,
            )
            for rel in rels
        ),
    )


def seed_tracer_graph(conn: Connection) -> None:
    """Run as the owner: actors and the catalogue are never writable by an app role."""
    if conn.scalar(select(models.Actor.id).where(models.Actor.id == SERVICE_ID)) is not None:
        return
    save(conn, build_tracer_records())


if __name__ == "__main__":
    engine = create_db_engine(get_settings().database_url.get_secret_value())
    with engine.begin() as c:
        seed_tracer_graph(c)
    engine.dispose()
    print("seeded")
