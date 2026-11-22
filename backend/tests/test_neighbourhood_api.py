# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

import re
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import Engine, delete, event
from sqlalchemy.orm import Session

from app.db import create_db_engine, get_session
from app.main import create_app
from app.models import Entity, EvidenceLocator, Relationship

pytestmark = pytest.mark.xfail(strict=True, reason="re-pointed in Task 3")

NOTICE = "Tracer bullet: shows stored links around the entity. This is not impact analysis."


def _loc(cell: str, snippet: str) -> dict[str, Any]:
    return {
        "kind": "xlsx_cell",
        "locator": {"file": "tracer-fixture.xlsx", "sheet": "Links", "cell": cell},
        "snippet": snippet,
    }


E1: dict[str, Any] = {
    "id": "RULE-T1|implements|REQ-T1",
    "source": "RULE-T1",
    "target": "REQ-T1",
    "type": "implements",
    "locator": _loc("B2", "RULE-T1 implements REQ-T1 (FICTIONAL, fake locator)"),
}
E2: dict[str, Any] = {
    "id": "TEST-T1|verifies|RULE-T1",
    "source": "TEST-T1",
    "target": "RULE-T1",
    "type": "verifies",
    "locator": _loc("B3", "TEST-T1 verifies RULE-T1 (FICTIONAL, fake locator)"),
}


def _node(i: str, label: str, t: str, role: str) -> dict[str, str]:
    return {"id": i, "label": label, "entity_type": t, "role": role}


def test_neighbourhood_rule_t1_exact(graph_client: TestClient) -> None:
    r = graph_client.get("/neighbourhood", params={"entity": "RULE-T1"})
    assert r.status_code == 200
    assert r.json() == {
        "entity": "RULE-T1",
        "fictional": True,
        "notice": NOTICE,
        "nodes": [
            _node("REQ-T1", "Fictional requirement", "requirement", "linked"),
            _node("RULE-T1", "Fictional rule", "rule", "seed"),
            _node("TEST-T1", "Fictional test", "test", "linked"),
        ],
        "edges": [E1, E2],
    }


def test_neighbourhood_req_t1_one_hop(graph_client: TestClient) -> None:
    body = graph_client.get("/neighbourhood", params={"entity": "REQ-T1"}).json()
    assert [(n["id"], n["role"]) for n in body["nodes"]] == [
        ("REQ-T1", "seed"),
        ("RULE-T1", "linked"),
    ]
    assert body["edges"] == [E1]


def test_neighbourhood_test_t1_one_hop(graph_client: TestClient) -> None:
    body = graph_client.get("/neighbourhood", params={"entity": "TEST-T1"}).json()
    assert [(n["id"], n["role"]) for n in body["nodes"]] == [
        ("RULE-T1", "linked"),
        ("TEST-T1", "seed"),
    ]
    assert body["edges"] == [E2]


def test_unknown_valid_key_404(graph_client: TestClient) -> None:
    r = graph_client.get("/neighbourhood", params={"entity": "NOPE-1"})
    assert r.status_code == 404
    assert r.json() == {"detail": "entity not found"}


HOSTILE = [
    "",
    "a" * 10_000,
    "'; DROP TABLE entity;--",
    "ünïcode",
    "../../etc/passwd",
    "A B",
    "%00",
    "RULE-T1\n",
]


@pytest.mark.parametrize("value", HOSTILE)
def test_hostile_entity_never_500_or_leaks(graph_client: TestClient, value: str) -> None:
    r = graph_client.get("/neighbourhood", params={"entity": value})
    assert r.status_code in (404, 422)
    if r.status_code == 422:
        body = r.json()
        assert body["detail"] == "invalid request"
        assert body["errors"][0]["loc"] == ["query", "entity"]
        if value:
            assert value not in r.text
    assert "Traceback" not in r.text
    # the table must survive
    assert graph_client.get("/neighbourhood", params={"entity": "RULE-T1"}).status_code == 200


def test_missing_param_422(graph_client: TestClient) -> None:
    r = graph_client.get("/neighbourhood")
    assert r.status_code == 422
    assert r.json()["detail"] == "invalid request"


def test_422_body_omits_submitted_value(graph_client: TestClient) -> None:
    probe = "zz-probe-value!"
    r = graph_client.get("/neighbourhood", params={"entity": probe})
    assert r.status_code == 422
    assert probe not in r.text
    assert "input" not in r.json()["errors"][0]


def test_other_routes_still_work(graph_client: TestClient) -> None:
    assert graph_client.get("/health").status_code == 200
    assert graph_client.get("/nonexistent").status_code == 404


def test_db_down_503_no_details() -> None:
    engine = create_db_engine("postgresql+pg8000://u:secretpw@db.internal.example:1/none")
    app = create_app()

    def _session() -> Iterator[Session]:
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    r = TestClient(app, raise_server_exceptions=False).get(
        "/neighbourhood", params={"entity": "RULE-T1"}
    )
    assert r.status_code == 503
    assert r.json() == {"detail": "database unavailable"}
    low = r.text.lower()
    for bad in ("db.internal", "secretpw", "password", "postgresql", ":1", "pg8000"):
        assert bad not in low


def test_two_calls_byte_identical(graph_client: TestClient) -> None:
    a = graph_client.get("/neighbourhood", params={"entity": "RULE-T1"}).content
    b = graph_client.get("/neighbourhood", params={"entity": "RULE-T1"}).content
    assert a == b


def test_edge_without_locator_is_generic_500(
    graph_client: TestClient, graph_engine: Engine
) -> None:
    with Session(graph_engine) as s, s.begin():
        s.execute(delete(EvidenceLocator))
    r = graph_client.get("/neighbourhood", params={"entity": "RULE-T1"})
    assert r.status_code == 500
    assert r.text == "Internal Server Error"


ALLOWED = re.compile(r"[A-Za-z0-9._-]{1,100}")


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(key=st.from_regex(ALLOWED, fullmatch=True))
def test_any_allowed_unseeded_key_is_404(graph_client: TestClient, key: str) -> None:
    if key in {"REQ-T1", "RULE-T1", "TEST-T1"}:
        return
    assert graph_client.get("/neighbourhood", params={"entity": key}).status_code == 404


def test_old_impact_path_is_gone(graph_client: TestClient) -> None:
    # /impact is reserved for the directional traversal (Slice 6)
    assert graph_client.get("/impact", params={"entity": "RULE-T1"}).status_code == 404


def _count_sql(engine: Engine, client: TestClient, key: str) -> int:
    n = 0

    def _inc(*_: Any) -> None:
        nonlocal n
        n += 1

    event.listen(engine, "before_cursor_execute", _inc)
    try:
        assert client.get("/neighbourhood", params={"entity": key}).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", _inc)
    return n


def test_sql_statement_count_is_constant_in_edge_count(
    graph_client: TestClient, graph_engine: Engine
) -> None:
    def add_edges(prefix: str, count: int) -> None:
        with Session(graph_engine) as s, s.begin():
            hub = Entity(
                product_profile="synthetic", entity_type="rule", natural_key=prefix, label="Hub"
            )
            s.add(hub)
            s.flush()
            for i in range(count):
                leaf = Entity(
                    product_profile="synthetic",
                    entity_type="test",
                    natural_key=f"{prefix}-L{i}",
                    label="Leaf",
                )
                s.add(leaf)
                s.flush()
                rel = Relationship(
                    type="verifies", source_entity_id=leaf.id, target_entity_id=hub.id
                )
                s.add(rel)
                s.flush()
                s.add(
                    EvidenceLocator(
                        relationship_id=rel.id,
                        kind="xlsx_cell",
                        locator={"file": "f.xlsx", "sheet": "S", "cell": f"B{i}"},
                        snippet="FICTIONAL",
                    )
                )

    add_edges("HUB-2", 2)
    add_edges("HUB-10", 10)
    assert _count_sql(graph_engine, graph_client, "HUB-2") == _count_sql(
        graph_engine, graph_client, "HUB-10"
    )
