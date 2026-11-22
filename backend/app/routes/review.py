# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Human review API. The actor always comes from a server-side credential, never from a body."""

import hmac
import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session, sqlstate
from app.domain.derive import evaluate
from app.domain.model import Claim, ClaimReviewEvent, Entity, RelationshipReviewEvent
from app.domain.records import Records, is_scoped
from app.models import Actor, ReviewEvent
from app.schemas import (
    ClaimVerdictIn,
    KeyTriple,
    LocatorOut,
    RelationshipVerdictIn,
    ReviewClaimOut,
    ReviewItem,
    ReviewItemsResponse,
    VerdictOut,
)
from app.store import load

log = logging.getLogger(__name__)
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


_TRAILER = re.compile(r": [a-z_]+ id \d+$")


def _rule(exc: ValidationError) -> str:
    """The domain's rule text without the trailing record kind and id. Fixed store logic, never
    input (domain messages name the rule, the kind and the id only)."""
    msg = exc.errors()[0]["msg"].removeprefix("Value error, ")
    return _TRAILER.sub("", msg)


def _submit(
    session: Session,
    actor_id: int,
    event: dict[str, Any],
    check: Callable[[Records], bool],
) -> JSONResponse:
    # shortcut: load() per request is O(store); fine at M1 synthetic scale (unmeasured)
    r = load(session.connection())
    if not check(r):
        raise HTTPException(404, "not found")
    candidate = {
        **event,
        "id": max((e.id for e in r.review_events), default=0) + 1,
        "at": datetime.now(UTC),
        "actor_id": actor_id,
    }
    try:
        cls = ClaimReviewEvent if candidate["target_kind"] == "claim" else RelationshipReviewEvent
        r.extended(review_events=(cls.model_validate(candidate),))
    except ValidationError as exc:
        return JSONResponse({"detail": "invalid review", "rule": _rule(exc)}, status_code=422)
    cols = {k: v for k, v in candidate.items() if k not in ("id", "at")}  # granted columns only
    try:
        row = session.execute(
            insert(ReviewEvent).values(**cols).returning(ReviewEvent.id, ReviewEvent.at)
        ).one()
        session.commit()
    except DBAPIError as exc:
        session.rollback()
        code = sqlstate(exc)
        if code is not None and (code.startswith("WB") or code.startswith("23")):
            log.warning("review rejected by the store: %s", code)  # the code only
            return JSONResponse({"detail": "rejected by the store"}, status_code=409)
        raise  # anything else, 42501 (misconfigured role) included, is a generic 500
    out = VerdictOut(id=row.id, at=row.at, verdict=str(candidate["verdict"]))
    return JSONResponse(out.model_dump(mode="json"), status_code=201)


@router.post("/relationships/{relationship_id}/verdicts", status_code=201)
def relationship_verdict(
    relationship_id: Annotated[int, Path(ge=1)],
    body: RelationshipVerdictIn,
    actor_id: int = Depends(require_reviewer),
    session: Session = Depends(get_session),  # noqa: B008
) -> JSONResponse:
    def known(r: Records) -> bool:
        return (
            relationship_id in r.relationship_by_id
            and (body.snapshot_id is None or body.snapshot_id in r.snapshot_by_id)
            and (
                body.successor_relationship_id is None
                or body.successor_relationship_id in r.relationship_by_id
            )
        )

    event = {
        "target_kind": "relationship",
        "relationship_id": relationship_id,
        "scope_snapshot_id": body.snapshot_id,
        "verdict": body.verdict,
        "reason": body.reason,
        "successor_relationship_id": body.successor_relationship_id,
    }
    return _submit(session, actor_id, event, known)


@router.post("/claims/{claim_id}/verdicts", status_code=201)
def claim_verdict(
    claim_id: Annotated[int, Path(ge=1)],
    body: ClaimVerdictIn,
    actor_id: int = Depends(require_reviewer),
    session: Session = Depends(get_session),  # noqa: B008
) -> JSONResponse:
    event = {
        "target_kind": "claim",
        "claim_id": claim_id,
        "verdict": body.verdict,
        "reason": body.reason,
    }
    return _submit(session, actor_id, event, lambda r: claim_id in r.claim_by_id)
