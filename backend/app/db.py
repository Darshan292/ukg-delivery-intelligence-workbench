# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Database engine and FastAPI session dependency."""

from collections.abc import Iterator
from functools import lru_cache
from typing import cast

from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.config import get_settings


def create_db_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True, connect_args={"timeout": 5})


@lru_cache
def _engine() -> Engine:
    return create_db_engine(get_settings().database_url.get_secret_value())


def get_session() -> Iterator[Session]:
    with Session(_engine()) as session:
        yield session


def sqlstate(exc: DBAPIError) -> str | None:
    """SQLSTATE of a pg8000 server error (args[0] is the server's field dict)."""
    fields = exc.orig.args[0] if exc.orig is not None and exc.orig.args else None
    return cast("dict[str, str]", fields).get("C") if isinstance(fields, dict) else None
