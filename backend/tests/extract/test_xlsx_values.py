# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Unreadable values and row boundaries. Test-only. FICTIONAL: not UKG behaviour."""

from typing import Any

from openpyxl import Workbook

from tests.extract.helpers import Build, attrs, bounds, edges, entities, nm_refs, put, run

LIMIT_HEAD = ["limit_id", "hours"]


def limits(*rows: list[Any]) -> Build:
    return lambda wb: put(wb, "Limits", [LIMIT_HEAD, *rows])


def bundles(ref: Any) -> Build:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [LIMIT_HEAD, ["L-1", 40]])
        put(wb, "Bundles", [["bundle_id", "limit"], ["B-1", ref]])

    return build


def test_formula_without_cached_value_attribute() -> None:
    ing, x = run(limits(["L-1", "=40*2"]))
    cell = next(c for c in ing.parsed.cells if c.formula)
    assert (cell.value_type, cell.value) == ("empty", None)  # the IR says no cached value
    assert bounds(x) == {("no_cached_value", ("Limits!B2",))}
    assert attrs(x, "L-1") == {}  # omitted, never None


def test_formula_without_cached_value_key() -> None:
    _, x = run(limits(['="L-1"', 40]))
    assert bounds(x) == {("no_cached_value", ("Limits!A2", "Limits!B2"))}
    assert not x.records.entities


def test_formula_without_cached_value_reference() -> None:
    _, x = run(bundles('="L-1"'))  # the formula text names L-1; it is never parsed
    assert bounds(x) == {("no_cached_value", ("Bundles!B2",))}
    assert not edges(x) and not nm_refs(x)


def test_error_value() -> None:
    ing, x = run(limits(["L-1", "#N/A"]))
    assert [c.value_type for c in ing.parsed.cells if c.value == "#N/A"] == ["error"]
    assert bounds(x) == {("error_value", ("Limits!B2",))}
    _, y = run(bundles("#N/A"))
    assert bounds(y) == {("error_value", ("Bundles!B2",))}


def test_numeric_key() -> None:
    _, x = run(limits([7, 40]))
    assert bounds(x) == {("unsupported_value", ("Limits!A2", "Limits!B2"))}
    assert not x.records.entities


def test_missing_key() -> None:
    _, x = run(limits([None, 40], ["L-1", 1]))
    assert bounds(x) == {("missing_key", ("Limits!B2",))}
    assert entities(x) == {("synthetic", "limit", "L-1")}


def test_blank_reference_structural() -> None:
    ing, x = run(bundles("   "))
    assert not x.records.extraction_boundaries and not nm_refs(x) and not edges(x)
    blank = next(c.locator_id for c in ing.parsed.cells if c.value == "   ")
    assert blank in x.structural_locator_ids
