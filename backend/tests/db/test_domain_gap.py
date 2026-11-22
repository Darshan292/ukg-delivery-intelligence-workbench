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
    TEXT, st.tuples(TEXT, TEXT).map(lambda t: f"{t[0]}@{t[1]}"), st.just("a@1")
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


# ---- jsonb payloads: raw JSON text is built by hand so NaN, 1e999 and duplicates can be sent ----

XLSX = {"sheet": '"S"', "cell": '"B9"'}
PDF = {"page": "1", "x0": "1.5", "top": "2", "x1": "3", "bottom": "4"}
LITS = st.sampled_from([
    '"S"', '""', '" "', "5", "null", "true", "[]", "{}", '"B9"', '"XFD1048576"', '"XFE1"',
    '"A1048577"', '"A0"', '"AAAA1"', '"a1"', '"B9\\n"', "0", "1", "1.0", "-1", "2.5", "1e999",
    "1.7976931348623157e308", "1.8e308", "-1e999", '"1"', "3", "4", "10", "1e2",
])  # fmt: skip
EXTRA_KEYS = st.sampled_from(["kind", "id", "zz", "Sheet"])


@st.composite
def raw_object(draw: st.DrawFn, base: dict[str, str]) -> str:
    """The base object with up to two mutations: set a key, drop a key, or add an extra key."""
    obj = dict(base)
    for _ in range(draw(st.integers(0, 2))):
        op = draw(st.sampled_from(["set", "drop", "add"]))
        if op == "set":
            obj[draw(st.sampled_from(sorted(base)))] = draw(LITS)
        elif op == "drop":
            obj.pop(draw(st.sampled_from(sorted(base))), None)
        else:
            obj[draw(EXTRA_KEYS)] = draw(LITS)
    return "{" + ", ".join(f'"{k}": {v}' for k, v in obj.items()) + "}"


LOCATOR_JSON = st.tuples(
    st.sampled_from(
        ["xlsx_cell", "pdf_word_bbox"]
    ),  # the kind column may disagree with the payload
    st.one_of(raw_object(XLSX), raw_object(PDF), st.sampled_from(["[]", "null", "5", '"x"'])),
)
VALS = st.sampled_from([
    *['"x"', "true", "null", '{"n": "1.5"}'] * 3,
    '"x"', "true", "null", "5", "1.5", "[]", "{}", '"\\u00fcn"', '{"n": "1.5"}', '{"n": "4E+1"}',
    '{"n": "NaN"}', '{"n": "Infinity"}', '{"n": "1e9999999999"}', '{"n": "abc"}', '{"n": 1}',
    '{"n": "1", "x": 2}', '{"n": " 1 "}', '{"n": "1_0"}', '{"n": "-.5"}',
])  # fmt: skip
# mostly-good values, so that fully valid attributes (and duplicates of them) are common
ATTR_NAMES = st.sampled_from(['"q"'] * 6 + ['"r"', '""', '" "', "5", "null"])
ATTR_LOCATORS = st.sampled_from(["LOC"] * 8 + ["999", "0", "-1", '"LOC"', "1.5", "null"])


@st.composite
def attributes_json(draw: st.DrawFn, loc: int) -> str:
    out: list[str] = []
    for _ in range(draw(st.integers(0, 3))):
        item = {"name": draw(ATTR_NAMES), "value": draw(VALS), "locator_id": draw(ATTR_LOCATORS)}
        if draw(st.integers(0, 6)) == 0:
            item.pop(draw(st.sampled_from(sorted(item))))
        if draw(st.integers(0, 6)) == 0:
            item["extra"] = "1"
        out.append(
            "{" + ", ".join(f'"{k}": {v}'.replace("LOC", str(loc)) for k, v in item.items()) + "}"
        )
        if draw(st.integers(0, 12)) == 0:
            out.append("5")  # an element that is not an object
    return "[" + ", ".join(out) + "]"


PAIRS = st.sampled_from([
    "[]", '[["a", "b"]]', '[["a"]]', '[["a", "b", "c"]]', '[["a", " "]]', "[[1, 2]]", "{}",
    '[["a", "b"], "x"]', "null", '[["a", "b"], ["c", "d"]]', '[[]]',
])  # fmt: skip

CASES["locator_json"] = lambda i: _case(
    "INSERT INTO evidence_locator VALUES (500, :dv, :kind, CAST(:loc AS jsonb), 'x', 'a@1', now())",
    dv=st.just(i.design_dv), kl=LOCATOR_JSON,
)  # fmt: skip
CASES["attributes_json"] = lambda i: _case(
    "INSERT INTO entity_version VALUES (500, 2, :dv, NULL, CAST(:attrs AS jsonb),"
    " CAST(:ids AS bigint[]))",
    dv=st.just(i.design_dv), attrs=attributes_json(i.design_locator),
    ids=st.sampled_from([[i.design_locator], [i.design_locator, i.export_locator]]),
)  # fmt: skip
CASES["catalogue_pairs"] = lambda i: _case(
    "INSERT INTO catalogue_relationship_type VALUES ('synthetic', 'zz', false, CAST(:p AS jsonb))",
    p=PAIRS,
)  # fmt: skip


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
        if "kl" in params:
            kind, loc = params["kl"]
            params = {**{k: v for k, v in params.items() if k != "kl"}, "kind": kind, "loc": loc}
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


def _loc(store: Engine, ids: Ids, kind: str, payload: str) -> None:
    sql = "INSERT INTO evidence_locator VALUES (500, :dv, :k, CAST(:p AS jsonb), 'x', 'a@1', now())"
    with store.begin() as c:
        c.execute(text(sql), {"dv": ids.design_dv, "k": kind, "p": payload})


@pytest.mark.parametrize(
    "kind,payload",
    [
        ("xlsx_cell", '{"sheet": "S", "cell": "B9", "zz": 1}'),  # extra key
        ("xlsx_cell", '{"sheet": "S"}'),  # missing key
        ("xlsx_cell", '{"sheet": "", "cell": "B9"}'),
        ("xlsx_cell", '{"sheet": "S", "cell": "XFE1"}'),  # column past XFD
        ("xlsx_cell", '{"sheet": "S", "cell": "A1048577"}'),  # row past the sheet
        ("xlsx_cell", '{"sheet": "S", "cell": "A0"}'),
        ("xlsx_cell", '{"page": 1, "x0": 1, "top": 1, "x1": 2, "bottom": 2}'),  # wrong kind
        ("pdf_word_bbox", '{"page": 0, "x0": 1, "top": 1, "x1": 2, "bottom": 2}'),
        ("pdf_word_bbox", '{"page": 1.0, "x0": 1, "top": 1, "x1": 2, "bottom": 2}'),
        ("pdf_word_bbox", '{"page": 1, "x0": 3, "top": 1, "x1": 2, "bottom": 2}'),  # inverted
        ("pdf_word_bbox", '{"page": 1, "x0": 1, "top": 3, "x1": 2, "bottom": 2}'),
        ("pdf_word_bbox", '{"page": 1, "x0": 1e999, "top": 1, "x1": 1e999, "bottom": 2}'),
        ("pdf_word_bbox", '{"page": 1, "x0": "1", "top": 1, "x1": 2, "bottom": 2}'),
        ("pdf_word_bbox", '{"page": 1, "x0": 1, "top": 1, "x1": 2, "bottom": 2, "kind": 1}'),
    ],
)
def test_malformed_locator_rejected(store: Engine, world_ids: Ids, kind: str, payload: str) -> None:
    with sqlstate_raised("23514"):
        _loc(store, world_ids, kind, payload)


def test_wellformed_locators_accepted_and_load(store: Engine, world_ids: Ids) -> None:
    _loc(store, world_ids, "xlsx_cell", '{"sheet": "S", "cell": "XFD1048576"}')
    with store.begin() as c:
        c.execute(
            text(
                "INSERT INTO evidence_locator VALUES (501, :dv, 'pdf_word_bbox', CAST("
                '\'{"page": 2, "x0": 1.5, "top": 2, "x1": 1.5, "bottom": 2}\' AS jsonb),'
                " 'x', 'a@1', now())"
            ),
            {"dv": world_ids.design_dv},
        )
    with store.connect() as c:
        assert len(load(c).locators) >= 2


def test_attribute_locator_must_be_in_the_versions_set(store: Engine, world_ids: Ids) -> None:
    sql = (
        "INSERT INTO entity_version VALUES (500, 2, :dv, NULL, CAST(:a AS jsonb),"
        " CAST(:ids AS bigint[]))"
    )
    loc = world_ids.design_locator
    good = f'[{{"name": "q", "value": {{"n": "1.5"}}, "locator_id": {loc}}}]'
    bad = good.replace(f'"locator_id": {loc}', f'"locator_id": {world_ids.export_locator}')
    params = {"dv": world_ids.design_dv, "ids": [loc]}
    with sqlstate_raised("23514"), store.begin() as c:
        c.execute(text(sql), {**params, "a": bad})
    with store.begin() as c:  # control
        c.execute(text(sql), {**params, "a": good})
    with store.connect() as c:
        assert load(c).entity_versions[-1].attributes[0].value is not None


@pytest.mark.parametrize(
    "attrs",
    [
        '[{"name": "q", "value": 5, "locator_id": L}]',  # a bare number would load as float
        '[{"name": "q", "value": 1.5, "locator_id": L}]',
        '[{"name": "q", "value": [], "locator_id": L}]',
        '[{"name": "q", "value": {"n": "NaN"}, "locator_id": L}]',
        '[{"name": "q", "value": {"n": "Infinity"}, "locator_id": L}]',
        '[{"name": "q", "value": {"n": "1e9999999999"}, "locator_id": L}]',
        '[{"name": "q", "value": {"n": 1}, "locator_id": L}]',
        '[{"name": "q", "value": {"n": "1", "x": 1}, "locator_id": L}]',
        '[{"name": "q", "value": "a", "locator_id": L},'
        ' {"name": "q", "value": "b", "locator_id": L}]',
        '[{"name": " ", "value": "a", "locator_id": L}]',
        '[{"name": "q", "value": "a", "locator_id": 0}]',
        '[{"name": "q", "value": "a", "locator_id": 1.0}]',
        '[{"name": "q", "value": "a", "locator_id": L, "extra": 1}]',
        '[{"name": "q", "locator_id": L}]',
        '[5]',
        '{}',
    ],
)  # fmt: skip
def test_malformed_attributes_rejected(store: Engine, world_ids: Ids, attrs: str) -> None:
    sql = (
        "INSERT INTO entity_version VALUES (500, 2, :dv, NULL, CAST(:a AS jsonb),"
        " CAST(:ids AS bigint[]))"
    )
    params = {
        "dv": world_ids.design_dv,
        "ids": [world_ids.design_locator],
        "a": attrs.replace("L}", f"{world_ids.design_locator}}}").replace(
            "L,", f"{world_ids.design_locator},"
        ),
    }
    with sqlstate_raised("23514"), store.begin() as c:
        c.execute(text(sql), params)
