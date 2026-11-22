# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""FastAPI application factory."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import InterfaceError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.logging_config import configure_logging
from app.routes.impact import router as impact_router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    # Fails fast at startup when DATABASE_URL is missing.
    configure_logging(get_settings().log_level)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Evidence-first impact workbench (tracer)", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:  # liveness: async so it never waits on the threadpool
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

    app.include_router(impact_router)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Never echo exc.errors()[i]["input"]: it is the submitted value.
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return JSONResponse({"detail": "invalid request", "errors": errors}, status_code=422)

    @app.exception_handler(OperationalError)
    @app.exception_handler(InterfaceError)
    async def _db_down(_: Request, exc: Exception) -> JSONResponse:
        log.warning("database unavailable: %s", type(exc).__name__)  # class only, no details
        return JSONResponse({"detail": "database unavailable"}, status_code=503)

    return app


app = create_app()
