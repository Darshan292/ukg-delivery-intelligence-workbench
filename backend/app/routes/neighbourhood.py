# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""GET /neighbourhood: the entity plus everything one stored link away (not impact analysis)."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.db import get_session
from app.models import Entity, EvidenceLocator, Relationship
from app.schemas import GraphEdge, GraphNode, ImpactResponse, LocatorOut

router = APIRouter()

NOTICE = "Tracer bullet: shows stored links around the entity. This is not impact analysis."


class ProvenanceError(Exception):
    """A stored link has no evidence locator; surfaces as a generic 500."""


def _byte_order(s: str) -> bytes:
    return s.encode()


@router.get("/neighbourhood", response_model=ImpactResponse)
def neighbourhood(
    entity: Annotated[str, Query(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")],
    session: Session = Depends(get_session),  # noqa: B008
) -> ImpactResponse:
    seed = session.scalar(select(Entity).where(Entity.natural_key == entity).order_by(Entity.id))
    if seed is None:
        raise HTTPException(status_code=404, detail="entity not found")
    src, tgt, first = aliased(Entity), aliased(Entity), aliased(EvidenceLocator)
    rows = session.execute(
        select(Relationship, src, tgt, EvidenceLocator)
        .join(src, src.id == Relationship.source_entity_id)
        .join(tgt, tgt.id == Relationship.target_entity_id)
        # one statement for all edges; first locator per edge (lowest id), outer so gaps are caught
        .outerjoin(
            EvidenceLocator,
            EvidenceLocator.id
            == select(func.min(first.id))
            .where(first.relationship_id == Relationship.id)
            .scalar_subquery(),
        )
        .where(or_(src.id == seed.id, tgt.id == seed.id))
    ).all()
    nodes = {
        seed.natural_key: GraphNode(
            id=seed.natural_key, label=seed.label, entity_type=seed.entity_type, role="seed"
        )
    }
    edges: list[GraphEdge] = []
    for rel, s, t, found in rows:
        loc = cast("EvidenceLocator | None", found)  # outer join: may be absent
        for e in (s, t):
            nodes.setdefault(
                e.natural_key,
                GraphNode(
                    id=e.natural_key, label=e.label, entity_type=e.entity_type, role="linked"
                ),
            )
        if loc is None:
            raise ProvenanceError(rel.id)
        edges.append(
            GraphEdge(
                id=f"{s.natural_key}|{rel.type}|{t.natural_key}",
                source=s.natural_key,
                target=t.natural_key,
                type=rel.type,
                locator=LocatorOut(kind=loc.kind, locator=loc.locator, snippet=loc.snippet),
            )
        )
    return ImpactResponse(
        entity=seed.natural_key,
        fictional=True,
        notice=NOTICE,
        nodes=sorted(nodes.values(), key=lambda n: _byte_order(n.id)),
        edges=sorted(edges, key=lambda e: _byte_order(e.id)),
    )
