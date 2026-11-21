# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.models import Entity, EvidenceLocator, Relationship
from app.seed import seed_tracer_graph


def _counts(engine: Engine) -> tuple[int, int, int]:
    with Session(engine) as s:
        return tuple(  # type: ignore[return-value]
            s.scalar(select(func.count()).select_from(m)) or 0
            for m in (Entity, Relationship, EvidenceLocator)
        )


def test_seed_creates_expected_rows(graph_engine: Engine) -> None:
    with Session(graph_engine) as s:
        seed_tracer_graph(s)
    assert _counts(graph_engine) == (3, 2, 2)
    with Session(graph_engine) as s:
        profiles = set(s.scalars(select(Entity.product_profile)))
        labels = list(s.scalars(select(Entity.label)))
    assert profiles == {"synthetic"}
    assert all(label.startswith("Fictional") for label in labels)


def test_seed_twice_is_idempotent(graph_engine: Engine) -> None:
    for _ in range(2):
        with Session(graph_engine) as s:
            seed_tracer_graph(s)
    assert _counts(graph_engine) == (3, 2, 2)
