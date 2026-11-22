# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Helpers for tests that talk to Postgres. FICTIONAL data only."""

import importlib.util
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from app.db import sqlstate

_MIG = Path(__file__).resolve().parent.parent / "migrations" / "versions" / "0002_d3_schema.py"


def _load_migration() -> Any:
    spec = importlib.util.spec_from_file_location("mig0002", _MIG)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TABLES: tuple[str, ...] = _load_migration().TABLES


@contextmanager
def sqlstate_raised(code: str | tuple[str, ...]) -> Generator[None]:
    codes = (code,) if isinstance(code, str) else code
    with pytest.raises(DBAPIError) as e:
        yield
    assert sqlstate(e.value) in codes, sqlstate(e.value)  # the code only, never the message


def truncate(engine: Engine) -> None:
    """As the owner: append-only triggers do not cover TRUNCATE, and app roles never hold it."""
    with engine.begin() as c:
        c.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY"))
