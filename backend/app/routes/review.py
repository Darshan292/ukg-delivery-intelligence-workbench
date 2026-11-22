# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Human review API. The actor always comes from a server-side credential, never from a body."""

import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.models import Actor


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
