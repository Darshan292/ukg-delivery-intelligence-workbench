# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Human review API. The actor always comes from a server-side credential, never from a body."""

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.domain.derive import evaluate
from app.domain.model import Claim, Entity
from app.domain.records import Records, is_scoped
from app.models import Actor
from app.schemas import KeyTriple, LocatorOut, ReviewClaimOut, ReviewItem, ReviewItemsResponse
from app.store import load

router = APIRouter(prefix="/review")
_LOC_COLUMNS = {"id", "document_version_id", "kind", "snippet", "extractor", "extracted_at"}


def require_reviewer(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> int:
    """The configured reviewer's actor id. The token identifies the human; the client never
    supplies an id or a kind. owner question S5-Q2 (pending): static bearer token, off by default.
    """
    token, actor_id = settings.reviewer_token, settings.reviewer_actor_id
    if token is None or actor_id is None:
        raise HTTPException(503, "review is not configured")
    scheme, _, given = (authorization or "").partition(" ")
    if scheme != "Bearer" or not hmac.compare_digest(
        given.encode(), token.get_secret_value().encode()
    ):
        raise HTTPException(401, "authentication required", headers={"WWW-Authenticate": "Bearer"})
    a = session.get(Actor, actor_id)
    if a is None or a.kind != "human" or "reviewer" not in a.roles:  # the DB re-checks as well
        raise HTTPException(403, "not permitted to review")
    return actor_id


def _key(e: Entity) -> KeyTriple:
    return KeyTriple(
        product_profile=e.product_profile, entity_type=e.entity_type, natural_key=e.natural_key
    )


def _claim_out(r: Records, c: Claim, live: bool) -> ReviewClaimOut:
    locators: list[LocatorOut] = []
    for i in c.locator_ids:
        loc = r.locator_by_id[i]
        title = r.document_by_id[r.version_by_id[loc.document_version_id].document_id].title
        rest = {k: str(v) for k, v in loc.model_dump(mode="json").items() if k not in _LOC_COLUMNS}
        locators.append(
            LocatorOut(kind=loc.kind, locator={"file": title, **rest}, snippet=loc.snippet)
        )
    return ReviewClaimOut(
        id=c.id,
        basis=c.basis,
        polarity=c.polarity,
        method=c.method,
        confidence=None if c.confidence is None else str(c.confidence),
        scope_snapshot_id=c.scope_snapshot_id,
        live=live,
        locators=locators,
    )


@router.get("/items", response_model=ReviewItemsResponse)
def review_items(
    snapshot_id: Annotated[int, Query(ge=1)],
    _actor: int = Depends(require_reviewer),
    session: Session = Depends(get_session),  # noqa: B008
) -> ReviewItemsResponse:
    # shortcut: load() per request is O(store); fine at M1 synthetic scale (unmeasured)
    r = load(session.connection())
    if snapshot_id not in r.snapshot_by_id:
        raise HTTPException(404, "not found")
    items: list[ReviewItem] = []
    for edge in evaluate(r, snapshot_id).edges:
        if edge.state != "unreviewed" and not edge.flags and not edge.conflict_kinds:
            continue
        rel = r.relationship_by_id[edge.relationship_id]
        claims = [
            _claim_out(r, c, c.id in edge.live_claim_ids)
            for c in r.claims_by_relationship.get(rel.id, ())
            if c.scope_snapshot_id in (None, snapshot_id)
        ]
        items.append(
            ReviewItem(
                relationship_id=rel.id,
                type=rel.type,
                qualifier=rel.qualifier,
                source=_key(r.entity_by_id[rel.source_entity_id]),
                target=_key(r.entity_by_id[rel.target_entity_id]),
                scoped=is_scoped(r, rel),
                state=edge.state,
                label=edge.label,
                flags=list(edge.flags),
                conflict_kinds=list(edge.conflict_kinds),
                claims=claims,
            )
        )
    return ReviewItemsResponse(snapshot_id=snapshot_id, items=items)
