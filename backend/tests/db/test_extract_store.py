# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""ingest, extract and save as the ingest role, then load. FICTIONAL data."""

from openpyxl import Workbook
from sqlalchemy import Engine, text

from app.extract.xlsx import Extracted
from app.store import load, save
from tests.db_helpers import norm
from tests.extract.helpers import Build, base_records, put, run
from tests.extract.test_xlsx_messy import messy

LIMITS = ["limit_id", "hours", "product_profile"]
BUNDLES = ["bundle_id", "limit", "product_profile"]


def saved(store: Engine, ingest_engine: Engine, build: Build) -> Extracted:
    base = base_records()
    with store.begin() as c:  # catalogue and actors are owner-only
        save(c, base)
    _, x = run(build, records=base)
    with ingest_engine.begin() as c:
        save(c, x.records, since=base)
    return x


def n(store: Engine, table: str, where: str = "true") -> int:
    with store.connect() as c:
        return int(c.scalar(text(f"SELECT count(*) FROM {table} WHERE {where}")) or 0)  # noqa: S608


def test_ingest_extract_save_load(store: Engine, ingest_engine: Engine) -> None:
    x = saved(store, ingest_engine, messy)
    assert x.records.extraction_boundaries and x.records.unresolved_references
    with store.connect() as c:
        assert norm(load(c)) == norm(x.records)


def test_issue_25_one_unknown_end_through_store(store: Engine, ingest_engine: Engine) -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [LIMITS, ["L-1", 40, None], ["L-2", 41, "unknown"]])
        put(wb, "Bundles", [BUNDLES, ["B-1", "L-2", None]])

    saved(store, ingest_engine, build)
    assert n(store, "relationship") == 1  # the explicit claim is a relationship
    assert n(store, "extraction_boundary", "reason = 'unknown_profile_entity'") == 1
    assert n(store, "unresolved_reference") == 0


def test_issue_25_two_unknown_through_store(store: Engine, ingest_engine: Engine) -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [LIMITS, ["L-2", 41, "unknown"]])
        put(wb, "Bundles", [BUNDLES, ["B-3", "L-2", "unknown"]])

    saved(store, ingest_engine, build)
    assert n(store, "unresolved_reference", "reason = 'unknown_profile'") == 1
    assert n(store, "relationship") == 0
