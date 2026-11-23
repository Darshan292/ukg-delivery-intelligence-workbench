# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Merged headers. Test-only. FICTIONAL: not UKG behaviour."""

from decimal import Decimal

from openpyxl import Workbook

from tests.extract.helpers import addr, attrs, bounds, edges, put, run


def test_merged_reference_header() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [["limit_id", "hours"], ["L-1", 1], ["L-2", 2]])
        ws = put(wb, "Bundles", [["bundle_id", "limit"], ["B-1", "L-1", "L-2"]])
        ws.merge_cells("B1:C1")

    ing, x = run(build)
    bundle_cells = {
        addr(x, c.locator_id) for c in ing.parsed.cells if addr(x, c.locator_id).startswith("Bund")
    }
    assert "Bundles!C1" not in bundle_cells  # intake emits the anchor only
    assert edges(x) == {
        ("contains", "B-1", "L-1", None, ("Bundles!A2", "Bundles!B2")),
        ("contains", "B-1", "L-2", None, ("Bundles!A2", "Bundles!C2")),
    }
    assert not x.records.extraction_boundaries


def test_merged_attribute_two_values() -> None:
    def build(wb: Workbook) -> None:
        ws = put(wb, "Limits", [["limit_id", "hours"], ["L-1", 40, 41], ["L-2", 40]])
        ws.merge_cells("B1:C1")

    _, x = run(build)
    assert bounds(x) == {("duplicate_value", ("Limits!B2", "Limits!C2"))}
    assert attrs(x, "L-1") == {}  # two values and no way to choose: none is stored
    assert attrs(x, "L-2") == {"hours": Decimal("40")}


def test_two_row_merged_header() -> None:
    def build(wb: Workbook) -> None:
        ws = put(wb, "Limits", [["limit_id", "hours"], [None, 99], ["L-1", 40]])
        ws.merge_cells("A1:A2")

    ing, x = run(build)
    assert "Limits!A2" not in {addr(x, c.locator_id) for c in ing.parsed.cells}
    assert bounds(x) == {("missing_key", ("Limits!B2",))}  # row 2 is data, without a key cell
    assert attrs(x, "L-1") == {"hours": Decimal("40")}
