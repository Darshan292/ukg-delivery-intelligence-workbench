# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Database engine and FastAPI session dependency."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
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
