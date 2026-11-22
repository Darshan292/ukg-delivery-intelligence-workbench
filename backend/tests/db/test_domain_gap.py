# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""No DB-valid / domain-invalid gap: every row the database accepts must load through the domain.

Rows are append-only, so one row the domain rejects would brick `load()` for good.
"""

from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from app.store import load
from tests.db_helpers import Ids, sqlstate_raised

SPACES = [c for c in map(chr, range(0x110000)) if c.isspace()]
EXTRA = [chr(0xFEFF), chr(0x180E)]  # not isspace, but invisible: the DB treats them as blank too
ALPHABET = st.sampled_from([*SPACES, *EXTRA, "a", "@", "Z", "9"])
GOOD = st.sampled_from(["a", "k1", "x y"])  # keeps plenty of valid rows in the mix
TEXT = st.one_of(st.text(max_size=6), st.text(alphabet=ALPHABET, max_size=6), GOOD, GOOD)
VERS = st.one_of(  # name@version
    TEXT, st.builds(lambda a, b: f"{a}@{b}", TEXT, TEXT), st.just("a@1")
)
IDS = st.sampled_from([-1, 0, 500])


def test_python_whitespace_is_blank_to_the_database(store: Engine) -> None:
    assert len(SPACES) >= 25  # sanity: the full Unicode set, not just ASCII
    for c in SPACES:
        with sqlstate_raised("23514"), store.begin() as conn:
            conn.execute(text("INSERT INTO document VALUES (500, 'synthetic', :t)"), {"t": c})


def test_versioned_names_reject_every_whitespace(store: Engine, world_ids: Ids) -> None:
    sql = (
        "INSERT INTO evidence_locator VALUES (500, :dv, 'xlsx_cell',"
        ' CAST(\'{"sheet": "S", "cell": "B9"}\' AS jsonb), \'x\', :ex, now())'
    )
    for c in SPACES:
        with sqlstate_raised("23514"), store.begin() as conn:
            conn.execute(text(sql), {"dv": world_ids.design_dv, "ex": f"a{c}b@1"})
    with store.begin() as conn:  # control
        conn.execute(text(sql), {"dv": world_ids.design_dv, "ex": "ab@1"})


def test_keys_with_surrounding_whitespace_rejected(store: Engine) -> None:
    ins = (
        "INSERT INTO entity (id, product_profile, entity_type, natural_key)"
        " VALUES (500, 'unknown', 'x', :k)"
    )
    for c in SPACES:
        for key in (f"k{c}", f"{c}k"):
            with sqlstate_raised("23514"), store.begin() as conn:
                conn.execute(text(ins), {"k": key})
    with store.begin() as conn:  # control: interior whitespace is a legal key
        conn.execute(text(ins), {"k": "a b"})


def _case(sql: str, **strategies: st.SearchStrategy[Any]) -> tuple[str, dict[str, Any]]:
    return sql, strategies


CASES: dict[str, Callable[[Ids], tuple[str, dict[str, Any]]]] = {
    "actor": lambda i: _case(
        "INSERT INTO actor VALUES (:i, 'human', :t, CAST(:roles AS text[]))",
        i=IDS, t=TEXT, roles=st.lists(TEXT, max_size=2),
    ),
    "snapshot": lambda i: _case(
        "INSERT INTO snapshot VALUES (:i, 'synthetic', :e, :t, now())", i=IDS, e=TEXT, t=TEXT
    ),
    "document": lambda i: _case("INSERT INTO document VALUES (:i, 'synthetic', :t)", i=IDS, t=TEXT),
    "document_version": lambda i: _case(
        "INSERT INTO document_version VALUES (:i, 1, repeat('d', 64), NULL, NULL, :by, now())",
        i=IDS, by=st.just(i.reviewer),
    ),
    "entity": lambda i: _case(
        "INSERT INTO entity (id, product_profile, entity_type, natural_key)"
        " VALUES (:i, 'unknown', :t, :k)",
        i=IDS, t=TEXT, k=TEXT,
    ),
    "entity_version": lambda i: _case(
        "INSERT INTO entity_version VALUES (:i, 2, :dv, NULL, CAST('[]' AS jsonb),"
        " CAST(:loc AS bigint[]))",
        i=IDS, dv=st.just(i.design_dv), loc=st.just([i.design_locator]),
    ),
    "catalogue_entity_type": lambda i: _case(
        "INSERT INTO catalogue_entity_type VALUES ('synthetic', :n, true, CAST(:d AS text[]))",
        n=TEXT, d=st.lists(TEXT, max_size=2),
    ),
    "catalogue_relationship_type": lambda i: _case(
        "INSERT INTO catalogue_relationship_type"
        " VALUES ('synthetic', :n, false, CAST('[]' AS jsonb))",
        n=TEXT,
    ),
    "relationship": lambda i: _case(
        "INSERT INTO relationship VALUES (:i, 'asserts_value', 1, 2, :q, now())", i=IDS, q=TEXT
    ),
    "evidence_locator": lambda i: _case(
        "INSERT INTO evidence_locator VALUES (:i, :dv, 'xlsx_cell',"
        " CAST('{\"sheet\": \"S\", \"cell\": \"B9\"}' AS jsonb), :sn, :ex, now())",
        i=IDS, dv=st.just(i.design_dv), sn=TEXT, ex=VERS,
    ),
    "claim": lambda i: _case(
        "INSERT INTO claim (id, relationship_id, basis, polarity, method, confidence, model_id,"
        " prompt_version, scope_snapshot_id, locator_ids, created_at) VALUES (:i, :rel,"
        " 'llm_suggestion', 'present', :m, 0.5, :mi, :pv, :s, CAST(:loc AS bigint[]), now())",
        i=IDS, rel=st.just(i.scoped_rel), m=VERS, mi=TEXT, pv=TEXT, s=st.just(i.s1),
        loc=st.just([i.export_locator]),
    ),
    "review_event_id": lambda i: _case(
        "INSERT INTO review_event (id, target_kind, relationship_id, scope_snapshot_id, verdict,"
        " reason, actor_id) OVERRIDING SYSTEM VALUE VALUES (:i, 'relationship', :rel, :s,"
        " 'rejected', :t, :a)",
        i=IDS, rel=st.just(i.scoped_rel), s=st.just(i.s1), t=TEXT, a=st.just(i.reviewer),
    ),
    "unresolved_reference": lambda i: _case(
        "INSERT INTO unresolved_reference VALUES (:i, 1, :raw, :loc, 'missing_target')",
        i=IDS, raw=TEXT, loc=st.just(i.design_locator),
    ),
}  # fmt: skip


@pytest.mark.parametrize("name", CASES)
def test_every_accepted_row_loads(store: Engine, world_ids: Ids, name: str) -> None:
    sql, strategies = CASES[name](world_ids)

    accepted = 0

    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
    )
    @given(params=st.fixed_dictionaries(strategies))
    def check(params: dict[str, Any]) -> None:
        with store.connect() as c:
            try:
                c.execute(text(sql), params)
            except DBAPIError:
                c.rollback()
                return  # refused by the database: nothing can be stored
            nonlocal accepted
            accepted += 1
            try:
                load(c)  # a stored row the domain rejects would brick this for good
            finally:
                c.rollback()

    check()
    assert accepted > 0  # positive control: the case inserts valid rows at all
