# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""GET /neighbourhood: the entity plus everything one stored link away (not impact analysis)."""

from collections.abc import Sequence
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.db import get_session
from app.domain.model import ProductProfile
from app.models import Claim, Document, DocumentVersion, Entity, EvidenceLocator, Relationship
from app.schemas import GraphEdge, GraphNode, LocatorOut, NeighbourhoodResponse

router = APIRouter()

NOTICE = "Tracer bullet: shows stored links around the entity. This is not impact analysis."
_KEY = r"^[A-Za-z0-9._-]+$"


class ProvenanceError(Exception):
    """A stored link has no claim or evidence locator; surfaces as a generic 500."""


def _byte_order(s: str) -> bytes:
    return s.encode()


@router.get("/neighbourhood", response_model=NeighbourhoodResponse)
def neighbourhood(
    entity: Annotated[str, Query(min_length=1, max_length=100, pattern=_KEY)],
    product_profile: ProductProfile | None = None,
    entity_type: Annotated[str | None, Query(min_length=1, max_length=100, pattern=_KEY)] = None,
    session: Session = Depends(get_session),  # noqa: B008
) -> NeighbourhoodResponse | JSONResponse:
    q = select(Entity).where(Entity.natural_key == entity)
    if product_profile is not None:
        q = q.where(Entity.product_profile == product_profile)
    if entity_type is not None:
        q = q.where(Entity.entity_type == entity_type)
    hits = session.scalars(q).all()
    if not hits:
        raise HTTPException(status_code=404, detail="entity not found")
    if len(hits) > 1:  # never "first match": that was the #13 bug
        triples = sorted((e.product_profile, e.entity_type, e.natural_key) for e in hits)
        return JSONResponse(
            {
                "detail": "ambiguous entity",
                "candidates": [
                    {"product_profile": p, "entity_type": t, "natural_key": k}
                    for p, t, k in triples
                ],
            },
            status_code=409,
        )
    seed = hits[0]
    src, tgt = aliased(Entity), aliased(Entity)
    # one statement for all edges: lowest-id claim, its first locator; outer so gaps are caught
    other = aliased(Claim)
    first_claim = (
        select(func.min(other.id)).where(other.relationship_id == Relationship.id).scalar_subquery()
    )
    rows: Sequence[Any] = session.execute(
        select(
            Relationship.id,
            Relationship.type,
            src.natural_key.label("s_key"),
            src.entity_type.label("s_type"),
            tgt.natural_key.label("t_key"),
            tgt.entity_type.label("t_type"),
            EvidenceLocator.kind,
            EvidenceLocator.locator,
            EvidenceLocator.snippet,
            Document.title,
        )
        .join(src, src.id == Relationship.source_entity_id)
        .join(tgt, tgt.id == Relationship.target_entity_id)
        .outerjoin(Claim, Claim.id == first_claim)
        .outerjoin(EvidenceLocator, EvidenceLocator.id == Claim.locator_ids[1])
        .outerjoin(DocumentVersion, DocumentVersion.id == EvidenceLocator.document_version_id)
        .outerjoin(Document, Document.id == DocumentVersion.document_id)
        .where(or_(src.id == seed.id, tgt.id == seed.id))
    ).all()
    # label is the natural key: D3 entities have no label (owner question S5-Q11, decided)
    nodes = {
        seed.natural_key: GraphNode(
            id=seed.natural_key,
            label=seed.natural_key,
            entity_type=seed.entity_type,
            role="seed",
        )
    }
    edges: list[GraphEdge] = []
    for row in rows:
        for key, etype in ((row.s_key, row.s_type), (row.t_key, row.t_type)):
            nodes.setdefault(key, GraphNode(id=key, label=key, entity_type=etype, role="linked"))
        if row.kind is None:
            raise ProvenanceError(row.id)
        edges.append(
            GraphEdge(
                id=f"{row.s_key}|{row.type}|{row.t_key}",
                source=row.s_key,
                target=row.t_key,
                type=row.type,
                locator=LocatorOut(
                    kind=row.kind,
                    locator={"file": row.title, **{k: str(v) for k, v in row.locator.items()}},
                    snippet=row.snippet,
                ),
            )
        )
    return NeighbourhoodResponse(
        entity=seed.natural_key,
        fictional=True,
        notice=NOTICE,
        nodes=sorted(nodes.values(), key=lambda n: _byte_order(n.id)),
        edges=sorted(edges, key=lambda e: _byte_order(e.id)),
    )
