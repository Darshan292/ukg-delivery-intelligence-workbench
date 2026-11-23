# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Never a crash and never a silent drop, on drawn messy grids. Test-only. FICTIONAL."""

from typing import Any

from hypothesis import assume, given, settings
from hypothesis import strategies as st
from openpyxl import Workbook

from app.ingest.errors import IntakeRejected
from tests.extract.helpers import SHEETS, put, run

HEADERS = sorted(
    {s.key_header for s in SHEETS.sheets}
    | {a.header for s in SHEETS.sheets for a in s.attributes}
    | {r.header for s in SHEETS.sheets for r in s.references}
    | {"asserts_attribute", "product_profile", "colour", "  ", "#N/A"}
)
CELLS: list[Any] = [
    "L-1", "L-2", "l-1", "L-1 ", "B-1", "unknown", "synthetic", "ukg_pro_wfm",
    7, 3.5, True, False, "=A1", "#N/A", "  ", "  ", "hours", None,
]  # fmt: skip


Grid = tuple[list[list[Any]], tuple[int, int] | None, int | None]


@st.composite
def grids(draw: st.DrawFn) -> Grid:
    """Row 1 is either a random mix of headers or check-shaped, with one or two qualifier
    columns (the shapes that need a reference, a qualifier and duplicates to line up)."""
    if draw(st.booleans()):
        header: list[Any] = ["check_id", "expected", "asserts", "asserts_attribute"]
        header += ["asserts_attribute"] * draw(st.integers(0, 1))
        ncols = len(header)
    else:
        ncols = draw(st.integers(1, 5))
        keys = [s.key_header for s in SHEETS.sheets]
        header = [draw(st.sampled_from(keys))] + [
            draw(st.sampled_from(HEADERS)) for _ in range(ncols - 1)
        ]
    rows = [
        [draw(st.sampled_from(CELLS)) for _ in range(ncols)] for _ in range(draw(st.integers(1, 5)))
    ]
    merge = None
    if ncols >= 2 and draw(st.booleans()):
        first = draw(st.integers(1, ncols - 1))
        merge = (first, first + 1)  # any two adjacent header cells, 1-based columns
    hidden = draw(st.one_of(st.none(), st.integers(2, 7)))
    return [header, *rows], merge, hidden


@settings(max_examples=60, deadline=None)  # each example starts the intake sandbox worker
@given(g=grids())
def test_never_crashes_never_drops(g: Grid) -> None:
    rows, merge, hidden = g

    def build(wb: Workbook) -> None:
        put(wb, "Limits", [["limit_id", "hours"], ["L-1", 40], ["L-2", 41]])
        ws = put(wb, "Drawn", rows)
        if merge:
            ws.merge_cells(start_row=1, start_column=merge[0], end_row=1, end_column=merge[1])
        if hidden is not None:
            ws.row_dimensions[hidden].hidden = True

    try:
        _, x = run(build)  # Extracted validated itself: no locator unaccounted
    except IntakeRejected:
        assume(False)
        return
    r = x.records
    with_claim = {c.relationship_id for c in r.claims}
    for rel in r.relationships:
        assert rel.id in with_claim
        ends = {r.entity_by_id[rel.source_entity_id].product_profile,
                r.entity_by_id[rel.target_entity_id].product_profile}  # fmt: skip
        assert ends != {"unknown"}
