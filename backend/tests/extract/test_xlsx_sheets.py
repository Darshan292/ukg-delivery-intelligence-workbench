# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour."""

from decimal import Decimal

from openpyxl import Workbook

from tests.extract.helpers import addr, attrs, bounds, entities, put, run

HEAD = ["limit_id", "hours", "label"]
LIMIT_ROWS = [HEAD, ["L-1", 40, "w"]]


def test_renamed_sheet() -> None:
    _, plain = run(lambda wb: put(wb, "Limits", LIMIT_ROWS))
    _, renamed = run(lambda wb: put(wb, "LIMITS (renamed)", LIMIT_ROWS))
    assert entities(renamed) == entities(plain)
    assert attrs(renamed, "L-1") == attrs(plain, "L-1")


def test_header_spelling() -> None:
    _, x = run(lambda wb: put(wb, "Limits", [["Limit ID ", "HOURS"], ["L-1", 40]]))
    assert attrs(x, "L-1") == {"hours": Decimal("40")}
    assert not x.records.extraction_boundaries


def test_unknown_sheet() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", LIMIT_ROWS)
        put(wb, "Scratch", [["a", "b"], ["c"]])

    _, x = run(build)
    assert bounds(x) == {("unknown_sheet", ("Scratch!A1", "Scratch!B1", "Scratch!A2"))}
    assert entities(x) == {("synthetic", "limit", "L-1")}


def test_ambiguous_sheet() -> None:
    _, x = run(lambda wb: put(wb, "Mixed", [["limit_id", "hours", "bundle_id"], ["L-1", 1, "B-1"]]))
    assert bounds(x) == {("ambiguous_sheet", tuple(f"Mixed!{c}{r}" for r in (1, 2) for c in "ABC"))}
    assert not x.records.entities


def test_notes_sheet() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", LIMIT_ROWS)
        put(wb, "about ", [["FICTIONAL: not UKG behaviour"], ["x", "y"]])

    _, x = run(build)
    assert not x.records.extraction_boundaries
    assert {addr(x, i) for i in x.structural_locator_ids} >= {"about !A1", "about !A2", "about !B2"}


def test_header_below_scan_limit() -> None:
    rows = [["pad"]] * 10 + LIMIT_ROWS  # header on row 11, scan limit is 10
    _, x = run(lambda wb: put(wb, "Limits", rows))
    assert [b[0] for b in bounds(x)] == ["unknown_sheet"]
    assert not x.records.entities


def test_unrecognised_column() -> None:
    rows = [["limit_id", "hours", "colour", None], ["L-1", 40, "red", "stray"]]
    _, x = run(lambda wb: put(wb, "Limits", rows))
    assert bounds(x) == {
        ("unrecognised_column", ("Limits!C1", "Limits!C2")),  # header and data cell
        ("unrecognised_column", ("Limits!D2",)),  # data with no header at all
    }
    assert attrs(x, "L-1") == {"hours": Decimal("40")}  # the rest of the row is extracted
