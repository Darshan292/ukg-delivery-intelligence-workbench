# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""FastAPI application factory."""

import logging

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_session

log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="UKG Delivery Intelligence Workbench (tracer)")

    @app.get("/health")
    def health() -> dict[str, str]:  # liveness: never touches the DB
        return {"status": "ok"}

    @app.get("/health/ready", response_model=None)
    def ready(session: Session = Depends(get_session)) -> JSONResponse:  # noqa: B008
        try:
            session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            # Log the class only: driver messages can contain host and user details.
            log.warning("readiness check failed")
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return JSONResponse({"status": "ready"})

    return app


app = create_app()
