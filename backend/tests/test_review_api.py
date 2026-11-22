# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""GET /review/items and the verdict endpoints (the app runs as a wb_review member)."""

from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.domain.records import Records
from tests.db_helpers import reviewer_client, save_as_roles
from tests.domain.builders import World


@dataclass(frozen=True)
class Q:
    client: TestClient
    s1: int
    s2: int
    r_open: int  # uses A->B: unreviewed, in conflict with r_card
    r_card: int  # uses A->C
    r_clean: int  # implements A->Q: accepted, no flags
    r_lost: int  # uses B->C: accepted in s1, then its only claim is rejected
    c_s2: int  # a claim on r_open that is scoped to s2
    c_lost: int
    r_solo: int  # asserts_value A->B 'q': no cardinality conflict, claims in both snapshots
    c_open: int  # the s1 claim on r_open
    service: int


def build_world() -> tuple[Records, dict[str, int]]:
    w = World()
    w.reviewer()
    s1, s2 = w.snapshot("s1"), w.snapshot("s2")
    ex1, ex2, design = w.export(s1), w.export(s2), w.design()
    a, b, c, q = (
        w.entity("cfg", "A"),
        w.entity("cfg", "B"),
        w.entity("cfg", "C"),
        w.entity("req", "Q"),
    )
    r_open, r_card = w.rel("uses", a, b), w.rel("uses", a, c)
    r_clean, r_lost = w.rel("implements", a, q), w.rel("uses", b, c)
    c_open = w.claim(r_open, ex1)
    w.claim(r_open, ex1)  # a second s1 claim, so rejecting c_open leaves the edge in the queue
    r_solo = w.rel("asserts_value", a, b, "q")
    w.claim(r_solo, ex1)
    w.claim(r_solo, ex2)
    c_s2 = w.claim(r_open, ex2)
    w.claim(r_card, ex1)
    w.claim(r_clean, design)
    c_lost = w.claim(r_lost, ex1)
    w.accept(r_clean, None)
    w.accept(r_lost, s1)
    w.reject_claim(c_lost)
    ids = {
        "s1": s1.id, "s2": s2.id, "r_open": r_open.id, "r_card": r_card.id,
        "r_clean": r_clean.id, "r_lost": r_lost.id, "c_s2": c_s2.id, "c_lost": c_lost.id,
        "r_solo": r_solo.id, "c_open": c_open.id, "service": 2,
    }  # fmt: skip
    return w.build(), ids


def make(store: Engine, ingest: Engine, review: Engine) -> Q:
    r, ids = build_world()
    save_as_roles(r, store, ingest, review)
    return Q(reviewer_client(review, 1), **ids)


def _items(q: Q, snapshot: int) -> dict[int, dict[str, Any]]:
    body = q.client.get("/review/items", params={"snapshot_id": snapshot}).json()
    return {i["relationship_id"]: i for i in body["items"]}


def test_exact_json_for_a_small_world(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    w = World()
    w.reviewer()
    s1 = w.snapshot("s1")
    a, b = w.entity("cfg", "A"), w.entity("cfg", "B")
    w.claim(w.rel("uses", a, b), w.export(s1))
    save_as_roles(w.build(), store, ingest_engine, review_engine)
    r = reviewer_client(review_engine, 1).get("/review/items", params={"snapshot_id": 1})
    key = {"product_profile": "synthetic", "entity_type": "cfg"}
    assert r.status_code == 200
    assert r.json() == {
        "snapshot_id": 1,
        "items": [
            {
                "relationship_id": 1,
                "type": "uses",
                "qualifier": None,
                "source": {**key, "natural_key": "A"},
                "target": {**key, "natural_key": "B"},
                "scoped": True,
                "state": "unreviewed",
                "label": "OBSERVED",
                "flags": [],
                "conflict_kinds": [],
                "claims": [
                    {
                        "id": 1,
                        "basis": "explicit_source",
                        "polarity": "present",
                        "method": "explicit_source-m@1",
                        "confidence": None,
                        "scope_snapshot_id": 1,
                        "live": True,
                        "locators": [
                            {
                                "kind": "xlsx_cell",
                                "locator": {"file": "export", "sheet": "S", "cell": "A1"},
                                "snippet": "v1",
                            }
                        ],
                    }
                ],
            }
        ],
    }


def test_two_calls_byte_identical(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)
    url = {"snapshot_id": q.s1}
    assert (
        q.client.get("/review/items", params=url).content
        == q.client.get("/review/items", params=url).content
    )


def test_queue_membership(store: Engine, ingest_engine: Engine, review_engine: Engine) -> None:
    q = make(store, ingest_engine, review_engine)
    items = _items(q, q.s1)
    assert q.r_clean not in items  # accepted, no flags
    assert items[q.r_lost]["state"] == "accepted"  # accepted but flagged: still shown
    assert items[q.r_lost]["flags"] == ["SUPPORT_LOST"]
    assert sorted(items) == [q.r_open, q.r_card, q.r_lost, q.r_solo]
    assert list(items) == sorted(items)  # relationship id order


def test_conflicted_unreviewed_edges_list_both_sides(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)
    items = _items(q, q.s1)
    assert items[q.r_open]["conflict_kinds"] == ["cardinality"]
    assert items[q.r_card]["conflict_kinds"] == ["cardinality"]


def test_claim_scoped_to_other_snapshot_is_not_listed(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)
    assert q.c_s2 not in [c["id"] for c in _items(q, q.s1)[q.r_open]["claims"]]
    assert q.c_s2 in [c["id"] for c in _items(q, q.s2)[q.r_open]["claims"]]


def test_unknown_snapshot_404_no_echo(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)
    r = q.client.get("/review/items", params={"snapshot_id": 987654})
    assert r.status_code == 404
    assert r.json() == {"detail": "not found"}
    assert "987654" not in r.text


def test_invalid_or_missing_snapshot_id_422(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)
    for params in ({}, {"snapshot_id": 0}, {"snapshot_id": "zz-probe"}):
        r = q.client.get("/review/items", params=params)
        assert r.status_code == 422
        assert "zz-probe" not in r.text


def test_items_need_the_reviewer_credential(review_engine: Engine, store: Engine) -> None:
    client = reviewer_client(review_engine, 1)
    r = client.get(
        "/review/items", params={"snapshot_id": 1}, headers={"Authorization": "Bearer x"}
    )
    assert r.status_code == 401


# ---- verdicts -------------------------------------------------------------------------------

REL = "/review/relationships/{}/verdicts"
CLAIM = "/review/claims/{}/verdicts"
RULE_SCOPE = "review: scope must name a snapshot of the profile"


def _events(store: Engine) -> list[Any]:
    with store.connect() as c:
        return [tuple(x) for x in c.execute(text("SELECT * FROM review_event ORDER BY id"))]


def _post(q: Q, path: str, body: object) -> Any:
    return q.client.post(path, json=body)


def test_accept_scoped_edge_in_snapshot(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)
    assert q.r_solo in _items(q, q.s1) and q.r_solo in _items(q, q.s2)
    r = _post(q, REL.format(q.r_solo), {"verdict": "accepted", "snapshot_id": q.s1})
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id", "at", "verdict"} and body["verdict"] == "accepted"
    assert _events(store)[-1][8] == 1  # actor_id: the configured reviewer
    assert q.r_solo not in _items(q, q.s1)
    assert q.r_solo in _items(q, q.s2)  # invariant 6: the verdict holds in one snapshot only


@pytest.mark.parametrize(
    "field,value", [("actor_id", 2), ("kind", "human"), ("at", "2001-01-01T00:00:00Z")]
)
def test_body_actor_fields_rejected(
    store: Engine, ingest_engine: Engine, review_engine: Engine, field: str, value: object
) -> None:
    q = make(store, ingest_engine, review_engine)
    before = _events(store)
    r = _post(q, REL.format(q.r_solo), {"verdict": "accepted", "snapshot_id": q.s1, field: value})
    assert r.status_code == 422
    assert _events(store) == before


def test_scoped_without_snapshot_422_rule(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)
    r = _post(q, REL.format(q.r_solo), {"verdict": "accepted"})
    assert r.status_code == 422
    assert r.json() == {"detail": "invalid review", "rule": RULE_SCOPE}


def test_unscoped_with_snapshot_422(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)
    r = _post(q, REL.format(q.r_clean), {"verdict": "rejected", "reason": "r", "snapshot_id": q.s1})
    assert r.status_code == 422
    assert r.json()["rule"] == "review: scope must be null for unscoped relationship"


def test_reason_and_successor_rules_422(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)
    before = _events(store)
    for body in (
        {"verdict": "rejected", "snapshot_id": q.s1},  # reason required
        {"verdict": "rejected", "reason": "   ", "snapshot_id": q.s1},
        {"verdict": "superseded", "reason": "r", "snapshot_id": q.s1},  # successor required
        {"verdict": "accepted", "successor_relationship_id": q.r_card, "snapshot_id": q.s1},
    ):
        r = _post(q, REL.format(q.r_solo), body)
        assert r.status_code == 422, body
    assert _events(store) == before


@pytest.mark.parametrize("which", ["path", "snapshot", "successor"])
def test_unknown_ids_404_no_echo(
    store: Engine, ingest_engine: Engine, review_engine: Engine, which: str
) -> None:
    q = make(store, ingest_engine, review_engine)
    rel, snap, succ = q.r_open, q.s1, q.r_card
    if which == "path":
        rel = 9876
    elif which == "snapshot":
        snap = 9876
    else:
        succ = 9876
    r = _post(
        q,
        REL.format(rel),
        {
            "verdict": "superseded",
            "reason": "r",
            "successor_relationship_id": succ,
            "snapshot_id": snap,
        },
    )
    assert r.status_code == 404
    assert r.json() == {"detail": "not found"}
    assert "9876" not in r.text
    assert _post(q, CLAIM.format(9876), {"verdict": "rejected", "reason": "r"}).status_code == 404


def test_cycle_409(store: Engine, ingest_engine: Engine, review_engine: Engine) -> None:
    q = make(store, ingest_engine, review_engine)
    n = len(_events(store))
    sup = {"verdict": "superseded", "reason": "r", "snapshot_id": q.s1}
    first = _post(q, REL.format(q.r_open), {**sup, "successor_relationship_id": q.r_card})
    assert first.status_code == 201
    r = _post(q, REL.format(q.r_card), {**sup, "successor_relationship_id": q.r_open})
    assert r.status_code == 409
    assert r.json() == {"detail": "rejected by the store"}
    assert len(_events(store)) == n + 1


def test_claim_reject_then_reinstate(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)

    def live() -> bool:
        claims = _items(q, q.s1)[q.r_open]["claims"]
        return next(c for c in claims if c["id"] == q.c_open)["live"]

    assert live()
    assert (
        _post(q, CLAIM.format(q.c_open), {"verdict": "rejected", "reason": "r"}).status_code == 201
    )
    assert not live()
    assert (
        _post(q, CLAIM.format(q.c_open), {"verdict": "reinstated", "reason": "r"}).status_code
        == 201
    )
    assert live()


def test_service_actor_configured_403_no_row(
    store: Engine, ingest_engine: Engine, review_engine: Engine
) -> None:
    q = make(store, ingest_engine, review_engine)
    before = _events(store)
    client = reviewer_client(review_engine, q.service)
    r = client.post(REL.format(q.r_solo), json={"verdict": "accepted", "snapshot_id": q.s1})
    assert r.status_code == 403
    assert _events(store) == before


@pytest.mark.parametrize(
    "body",
    [
        {"verdict": "rejected", "reason": "x" * 5000, "snapshot_id": 1},
        {"verdict": "accepted", "snapshot_id": "zz-probe"},
        {"verdict": "zz-probe-verdict"},
        {"verdict": "accepted", "snapshot_id": 1, "successor_relationship_id": "zz-probe"},
        ["zz-probe"],
    ],
)
def test_hostile_bodies_422_no_echo(
    store: Engine, ingest_engine: Engine, review_engine: Engine, body: object
) -> None:
    q = make(store, ingest_engine, review_engine)
    before = _events(store)
    r = _post(q, REL.format(q.r_solo), body)
    assert r.status_code == 422
    assert "zz-probe" not in r.text and "xxxxx" not in r.text
    assert _events(store) == before
