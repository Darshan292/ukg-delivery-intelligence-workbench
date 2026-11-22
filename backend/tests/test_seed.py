# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

from sqlalchemy import Engine, text

from app.seed import build_tracer_records, seed_tracer_graph
from app.store import load
from tests.db_helpers import TABLES

EXPECTED = {
    "actor": 2,
    "catalogue_entity_type": 3,
    "catalogue_relationship_type": 2,
    "snapshot": 0,
    "document": 1,
    "document_version": 1,
    "evidence_locator": 2,
    "entity": 3,
    "entity_version": 0,
    "relationship": 2,
    "claim": 2,
    "review_event": 0,
    "unresolved_reference": 0,
}


def _counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as c:
        return {t: c.scalar(text(f"SELECT count(*) FROM {t}")) or 0 for t in TABLES}  # noqa: S608


def test_seed_creates_expected_rows(store: Engine) -> None:
    with store.begin() as c:
        seed_tracer_graph(c)
    assert _counts(store) == EXPECTED


def test_seed_twice_is_idempotent(store: Engine) -> None:
    for _ in range(2):
        with store.begin() as c:
            seed_tracer_graph(c)
    assert _counts(store) == EXPECTED


def test_seed_is_synthetic_and_fictional(store: Engine) -> None:
    with store.begin() as c:
        seed_tracer_graph(c)
    with store.connect() as c:
        r = load(c)
    assert {x.product_profile for x in (*r.entities, *r.documents)} == {"synthetic"}
    assert all("FICTIONAL" in loc.snippet for loc in r.locators)


def test_seed_actor_2_is_a_human_reviewer_and_actor_1_is_not() -> None:
    r = build_tracer_records()
    assert r.actor_by_id[2].is_reviewer
    assert r.actor_by_id[1].kind == "service"
