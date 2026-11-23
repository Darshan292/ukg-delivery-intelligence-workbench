# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour."""

from datetime import date
from decimal import Decimal

import pytest
from openpyxl import Workbook
from pydantic import ValidationError

from app.extract.catalogue import CatalogueMismatch, ReferenceColumn
from app.extract.xlsx import Extracted
from tests.extract.helpers import SHEETS, addr, attrs, entities, put, run

HEAD = ["limit_id", "hours", "label"]


def test_limits_sheet() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [HEAD, ["L-1", 40, "Weekly"], ["L-2", 37.5, True]])

    _, x = run(build)
    assert entities(x) == {("synthetic", "limit", "L-1"), ("synthetic", "limit", "L-2")}
    a1, a2 = attrs(x, "L-1"), attrs(x, "L-2")
    assert a1 == {"hours": Decimal("40"), "label": "Weekly"}
    assert a2 == {"hours": Decimal("37.5"), "label": True}
    assert all(type(a["hours"]) is Decimal for a in (a1, a2))
    cited = {
        e.natural_key: {addr(x, i) for i in v.locator_ids}
        for e in x.records.entities
        for v in x.records.entity_versions
        if v.entity_id == e.id
    }
    assert cited["L-1"] == {"Limits!A2", "Limits!B2", "Limits!C2"}
    assert {v.snapshot_id for v in x.records.entity_versions} == {1}


def test_date_attribute_iso_text() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [HEAD, ["L-1", 1, date(2026, 1, 2)]])

    ing, x = run(build)
    got = attrs(x, "L-1")["label"]
    assert isinstance(got, str) and got.startswith("2026-01-02")
    assert got in {c.value for c in ing.parsed.cells}


def test_header_and_preamble_structural() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [["FICTIONAL: not UKG behaviour"], HEAD, ["L-1", 40, "w"]])

    _, x = run(build)
    structural = {addr(x, i) for i in x.structural_locator_ids}
    assert structural == {"Limits!A1", "Limits!A2", "Limits!B2", "Limits!C2"}
    assert entities(x) == {("synthetic", "limit", "L-1")}


def test_existing_entity_reused() -> None:
    def first(wb: Workbook) -> None:
        put(wb, "Limits", [HEAD, ["L-1", 40, "w"]])

    def second(wb: Workbook) -> None:
        put(wb, "Limits", [HEAD, ["L-1", 41, "w"]])

    _, x1 = run(first, snapshot_id=1)
    _, x2 = run(second, records=x1.records, snapshot_id=2)
    assert len(x2.records.entities) == 1
    assert [v.snapshot_id for v in x2.records.entity_versions] == [1, 2]


def test_invariant_rejects_unaccounted() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [["banner"], HEAD, ["L-1", 40, "w"]])

    ing, x = run(build)
    short = x.structural_locator_ids[1:]
    with pytest.raises(ValidationError):
        Extracted(
            records=x.records,
            document_version_id=ing.parsed.document_version_id,
            structural_locator_ids=short,
        )


def test_profile_or_catalogue_mismatch() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [HEAD, ["L-1", 40, "w"]])

    with pytest.raises(CatalogueMismatch):
        run(build, sheets=SHEETS.model_copy(update={"product_profile": "ukg_pro_wfm"}))
    bad = SHEETS.sheets[1].model_copy(
        update={"references": (ReferenceColumn(header="limit", relationship_type="nope",
                                               target_type="limit"),)}
    )  # fmt: skip
    with pytest.raises(CatalogueMismatch):
        run(build, sheets=SHEETS.model_copy(update={"sheets": (SHEETS.sheets[0], bad)}))


def test_invariant_rejects_structural_id_of_another_version() -> None:
    def a(wb: Workbook) -> None:
        put(wb, "Limits", [HEAD, ["L-1", 40, "w"]])

    def b(wb: Workbook) -> None:
        put(wb, "Limits", [HEAD, ["L-2", 41, "w"]])

    _, x1 = run(a, snapshot_id=1)
    ing, x2 = run(b, records=x1.records, snapshot_id=2)
    foreign = x1.records.locators[0].id  # a locator of the first version
    with pytest.raises(ValidationError):
        Extracted(
            records=x2.records,
            document_version_id=ing.parsed.document_version_id,
            structural_locator_ids=tuple(sorted({*x2.structural_locator_ids, foreign})),
        )
