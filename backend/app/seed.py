# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Idempotent fictional tracer fixture. CLI: python -m app.seed (uses DATABASE_URL)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import create_db_engine
from app.models import Entity, EvidenceLocator, Relationship

PROFILE = "synthetic"
ENTITIES = [
    ("REQ-T1", "requirement", "Fictional requirement"),
    ("RULE-T1", "rule", "Fictional rule"),
    ("TEST-T1", "test", "Fictional test"),
]
# (source, type, target, cell)
LINKS = [("RULE-T1", "implements", "REQ-T1", "B2"), ("TEST-T1", "verifies", "RULE-T1", "B3")]


def seed_tracer_graph(session: Session) -> None:
    ids: dict[str, int] = {}
    for key, etype, label in ENTITIES:
        ent = session.scalar(
            select(Entity).where(
                Entity.product_profile == PROFILE,
                Entity.entity_type == etype,
                Entity.natural_key == key,
            )
        )
        if ent is None:
            ent = Entity(product_profile=PROFILE, entity_type=etype, natural_key=key, label=label)
            session.add(ent)
            session.flush()
        ids[key] = ent.id
    for src, rtype, tgt, cell in LINKS:
        rel = session.scalar(
            select(Relationship).where(
                Relationship.type == rtype,
                Relationship.source_entity_id == ids[src],
                Relationship.target_entity_id == ids[tgt],
            )
        )
        if rel is None:
            rel = Relationship(type=rtype, source_entity_id=ids[src], target_entity_id=ids[tgt])
            session.add(rel)
            session.flush()
        if (
            session.scalar(
                select(EvidenceLocator.id).where(EvidenceLocator.relationship_id == rel.id)
            )
            is None
        ):
            session.add(
                EvidenceLocator(
                    relationship_id=rel.id,
                    kind="xlsx_cell",
                    locator={"file": "tracer-fixture.xlsx", "sheet": "Links", "cell": cell},
                    snippet=f"{src} {rtype} {tgt} (FICTIONAL, fake locator)",
                )
            )
    session.commit()


if __name__ == "__main__":
    engine = create_db_engine(get_settings().database_url.get_secret_value())
    with Session(engine) as s:
        seed_tracer_graph(s)
    engine.dispose()
    print("seeded")
