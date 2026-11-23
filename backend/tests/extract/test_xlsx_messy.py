# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""One hand-written workbook with every messy feature of the Milestone 1 list.

Expected sets are written out by hand from the plan's outcome table. Test-only. FICTIONAL.
"""

from decimal import Decimal

from openpyxl import Workbook

from app.extract.xlsx import Extracted
from app.ingest.intake import Ingested
from tests.extract.helpers import attrs, bounds, edges, entities, nm_refs, put, run

LIM = "Limit table (renamed)"


def messy(wb: Workbook) -> None:
    ws = put(
        wb,
        LIM,  # renamed sheet
        [
            ["limit_id", "hours", "label"],
            ["L-1 ", 40, "Weekly"],  # trailing whitespace on the key
            ["L-2", "=20*2", None],  # formula without a cached value
            ["L-3", 10, None],  # hidden row
        ],
    )
    ws.row_dimensions[4].hidden = True
    b = put(
        wb,
        "Bundles",
        [
            ["bundle_id", "limit"],
            ["B-1", "L-1 ", "L-2"],  # trailing whitespace on a reference
            ["B-2", "L-9", "l-1"],  # dangling reference, alias spelling
        ],
    )
    b.merge_cells("B1:C1")  # merged header
    put(wb, "Scratch", [["x", "y"]])  # unknown sheet


def extract() -> tuple[Ingested, Extracted]:
    return run(messy)


def test_complete_boundaries_references_and_edges() -> None:
    _, x = extract()
    assert bounds(x) == {
        ("no_cached_value", (f"{LIM}!B3",)),
        ("unknown_sheet", ("Scratch!A1", "Scratch!B1")),
    }
    assert nm_refs(x) == {
        ("missing_target", "B-2", "L-9", "Bundles!B3"),
        ("missing_target", "B-2", "l-1", "Bundles!C3"),
    }
    assert edges(x) == {
        ("contains", "B-1", "L-1", None, ("Bundles!A2", "Bundles!B2")),
        ("contains", "B-1", "L-2", None, ("Bundles!A2", "Bundles!C2")),
    }
    assert entities(x) == {
        ("synthetic", "limit", "L-1"),
        ("synthetic", "limit", "L-2"),
        ("synthetic", "limit", "L-3"),
        ("synthetic", "bundle", "B-1"),
        ("synthetic", "bundle", "B-2"),
    }


def test_trailing_whitespace_resolves_but_snippets_stay_verbatim() -> None:
    _, x = extract()
    snippets = {
        f"{loc.sheet}!{loc.cell}": loc.snippet
        for loc in x.records.locators
        if loc.kind == "xlsx_cell"
    }
    assert snippets[f"{LIM}!A2"] == "L-1 " and snippets["Bundles!B2"] == "L-1 "
    assert ("contains", "B-1", "L-1") in {e[:3] for e in edges(x)}


def test_hidden_row_is_ordinary_data() -> None:
    ing, x = extract()
    assert any(c.row_hidden for c in ing.parsed.cells)  # the IR carries the flag
    assert attrs(x, "L-3") == {"hours": Decimal("10")}
