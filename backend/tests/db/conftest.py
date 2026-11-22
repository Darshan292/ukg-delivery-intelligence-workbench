# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""A small FICTIONAL world saved as the owner, with the ids the DB rule tests need."""

import pytest
from sqlalchemy import Engine

from app.domain.model import Actor
from app.store import save
from tests.db_helpers import Ids
from tests.domain.builders import World


@pytest.fixture
def world_ids(store: Engine) -> Ids:
    w = World()
    rev, svc = w.reviewer(), w.service()
    s1, s2 = w.snapshot("s1"), w.snapshot("s2")
    ex, ex2, design = w.export(s1), w.export(s2), w.design()
    a, b, c, q = (
        w.entity("cfg", "A"),
        w.entity("cfg", "B"),
        w.entity("cfg", "C"),
        w.entity("req", "Q"),
    )
    scoped, succ, back = w.rel("uses", a, b), w.rel("uses", a, c), w.rel("uses", b, a)
    unscoped = w.rel("implements", a, q)
    c1, c2 = w.claim(scoped, ex), w.claim(unscoped, design)
    w.claim(succ, ex)
    w.claim(back, ex)
    human = Actor(id=99, kind="human", display_name="Plain human", roles=frozenset())
    r = w.build().extended(actors=(human,))
    with store.begin() as conn:
        save(conn, r)
    return Ids(
        reviewer=rev.id, service=svc.id, plain_human=human.id, s1=s1.id, s2=s2.id,
        scoped_rel=scoped.id, succ_rel=succ.id, back_rel=back.id, unscoped_rel=unscoped.id,
        scoped_claim=c1.id, unscoped_claim=c2.id, export_dv=ex.id, design_dv=design.id,
        export_locator=c1.locator_ids[0], design_locator=c2.locator_ids[0], s2_export_dv=ex2.id,
    )  # fmt: skip
