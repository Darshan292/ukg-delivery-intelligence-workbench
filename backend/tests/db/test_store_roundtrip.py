# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from pydantic import ValidationError
from sqlalchemy import Engine, text

from app.domain.locators import PdfWordBbox
from app.domain.records import Records
from app.store import load, save
from tests.db_helpers import norm, truncate
from tests.domain.builders import World
from tests.domain.strategies import worlds


@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@given(r=worlds())
def test_roundtrip_hypothesis(r: Records, store: Engine) -> None:
    truncate(store)
    with store.begin() as c:
        save(c, r)
    with store.connect() as c:
        assert norm(load(c)) == norm(r)


def _one_version_world(**attrs: Any) -> Records:
    w = World()
    w.reviewer()
    dv = w.design()
    e = w.entity("req", "Q")
    w.version(e, dv, **attrs)
    return w.build()


def test_decimal_attribute_exact(store: Engine) -> None:
    vals: dict[str, Any] = {
        "tiny": Decimal("0.1000000000000000055511151231257827"),
        "half": Decimal("37.5"),
        "exp": Decimal("4E+1"),
        "txt": "37.5",
        "flag": True,
        "none": None,
    }
    r = _one_version_world(**vals)
    with store.begin() as c:
        save(c, r)
    with store.connect() as c:
        got = {a.name: a.value for a in load(c).entity_versions[0].attributes}
    assert got == vals
    for k, v in vals.items():  # equality alone cannot tell 40 from 4E+1 or True from 1
        assert type(got[k]) is type(v)
    assert str(got["exp"]) == "4E+1"


def test_pdf_locator_roundtrip(store: Engine) -> None:
    w = World()
    w.reviewer()
    dv = w.design()
    w.locators.append(
        PdfWordBbox(
            id=1,
            document_version_id=dv.id,
            snippet="FICTIONAL",
            extractor="pdfplumber@1",
            extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
            kind="pdf_word_bbox",
            page=3,
            x0=1.5,
            top=2.25,
            x1=100.125,
            bottom=12.1,
        )
    )
    r = w.build()
    with store.begin() as c:
        save(c, r)
    with store.connect() as c:
        got = load(c)
    assert norm(got) == norm(r)
    assert got.locators[0] == r.locators[0]


def test_load_revalidates(store: Engine) -> None:
    w = World()
    w.reviewer()
    dv = w.design()
    w.entity("req", "Q")
    w.locator(dv)
    w.locator(dv)
    with store.begin() as c:
        save(c, w.build())
        # an attribute whose locator is not listed: jsonb, so only the domain can refuse it
        c.execute(
            text(
                "INSERT INTO entity_version VALUES (1, 1, 1, NULL,"
                ' \'[{"name": "q", "value": "x", "locator_id": 2}]\', \'{1}\')'
            )
        )
    with store.connect() as c, pytest.raises(ValidationError):
        load(c)


def test_load_revalidates_cross_record_rules(store: Engine) -> None:
    """A rule that lives in `Records`, not in one leaf: the owner briefly disables the trigger."""
    w = World()
    w.reviewer()
    svc = w.service()
    dv = w.design()
    a, q = w.entity("cfg", "A"), w.entity("req", "Q")
    w.claim(w.rel("implements", a, q), dv)
    with store.begin() as c:
        save(c, w.build())
        c.execute(text("ALTER TABLE review_event DISABLE TRIGGER wb_review_event_rules"))
        c.execute(
            text(
                "INSERT INTO review_event (target_kind, relationship_id, verdict, actor_id)"
                " VALUES ('relationship', 1, 'accepted', :a)"
            ),
            {"a": svc.id},
        )
        c.execute(text("ALTER TABLE review_event ENABLE TRIGGER wb_review_event_rules"))
    with store.connect() as c, pytest.raises(ValidationError):
        load(c)
