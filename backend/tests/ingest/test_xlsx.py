# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import datetime as dt
import logging
from decimal import Decimal
from io import BytesIO
from typing import Any

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from openpyxl.worksheet.formula import ArrayFormula

from app.domain.locators import XlsxCell
from app.ingest.errors import IntakeRejected, Limits, Reason
from app.ingest.fragments import CellFragment
from app.ingest.xlsx import parse_xlsx
from tests.ingest.hostile import SS_NS, rewrite_zip, workbook_bytes

NOW = dt.datetime(2026, 11, 22, 9, 0, tzinfo=dt.UTC)
L = Limits()


def _parse(data: bytes, *, first: int = 1, limits: Limits = L):  # noqa: ANN202
    return parse_xlsx(data, version_id=7, first_locator_id=first, now=NOW, limits=limits)


def _rejects(data: bytes, reason: Reason, limits: Limits = L) -> None:
    with pytest.raises(IntakeRejected) as ei:
        _parse(data, limits=limits)
    assert ei.value.reason == reason


def _by_cell(data: bytes, sheet: str = "Sheet") -> dict[str, tuple[XlsxCell, CellFragment]]:
    locs, _, cells = _parse(data)
    by_id = {c.locator_id: c for c in cells}
    return {loc.cell: (loc, by_id[loc.id]) for loc in locs if loc.sheet == sheet}


def _hand(rows: str) -> bytes:
    """A one-sheet workbook whose sheet1.xml is hand-written (so cached <v> values exist)."""
    xml = f'<worksheet xmlns="{SS_NS}"><sheetData>{rows}</sheetData></worksheet>'
    base = workbook_bytes(lambda wb: None)
    return rewrite_zip(base, replace={"xl/worksheets/sheet1.xml": xml.encode()})


def test_value_types() -> None:
    data = _hand(
        '<row r="1"><c r="A1" t="inlineStr"><is><t>text</t></is></c><c r="B1"><v>40</v></c>'
        '<c r="C1"><v>37.5</v></c><c r="D1" t="b"><v>1</v></c><c r="E1" t="e"><v>#DIV/0!</v></c>'
        '<c r="F1" t="b"><v>0</v></c></row>'
    )
    got = _by_cell(data)
    assert (got["A1"][1].value, got["A1"][1].value_type, got["A1"][0].snippet) == (
        "text",
        "string",
        "text",
    )
    for ref, text in (("B1", "40"), ("C1", "37.5")):
        loc, frag = got[ref]
        assert type(frag.value) is Decimal and frag.value == Decimal(text)
        assert (frag.value_type, loc.snippet) == ("number", text)
    assert (got["D1"][1].value, got["D1"][1].value_type, got["D1"][0].snippet) == (
        True,
        "boolean",
        "TRUE",
    )
    assert got["F1"][0].snippet == "FALSE"
    assert (got["E1"][1].value, got["E1"][1].value_type, got["E1"][0].snippet) == (
        "#DIV/0!",
        "error",
        "#DIV/0!",
    )


def test_date_cell_is_iso_text() -> None:
    def build(wb: Workbook) -> None:
        wb.active["A1"] = dt.datetime(2026, 3, 1, 8, 30)  # type: ignore[index]  # pyright: ignore

    loc, frag = _by_cell(workbook_bytes(build))["A1"]
    # owner question S3-Q8 (pending): date cells as ISO text with value_type "date"
    assert (frag.value, frag.value_type, loc.snippet) == (
        "2026-03-01T08:30:00",
        "date",
        "2026-03-01T08:30:00",
    )


def test_formula_and_cached_value_read_separately() -> None:
    got = _by_cell(
        _hand('<row r="1"><c r="A1"><v>37.5</v></c><c r="B1"><f>A1*2</f><v>75</v></c></row>')
    )
    loc, frag = got["B1"]
    assert frag.formula == "=A1*2" and frag.value == Decimal("75") and loc.snippet == "75"
    assert got["A1"][1].formula is None


def test_formula_without_cached_value() -> None:
    loc, frag = _by_cell(_hand('<row r="1"><c r="B1"><f>A1*2</f></c></row>'))["B1"]
    assert frag.formula == "=A1*2" and frag.value is None
    assert frag.value_type == "empty" and loc.snippet == ""


def test_array_formula_text() -> None:
    def build(wb: Workbook) -> None:
        wb.active["A1"] = ArrayFormula("C1:C2", "=SUM(A1:A2)")  # type: ignore[index]  # pyright: ignore

    assert _by_cell(workbook_bytes(build))["A1"][1].formula == "=SUM(A1:A2)"


def test_hidden_row_column_sheet_recorded() -> None:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws.title = "Sheet"
        ws["A1"] = "a"
        ws["A2"] = "b"
        ws["C1"] = "c"
        ws.row_dimensions[2].hidden = True
        ws.column_dimensions["C"].hidden = True
        wb.create_sheet("H")["A1"] = "h"
        wb.create_sheet("V")["A1"] = "v"
        wb["H"].sheet_state = "hidden"
        wb["V"].sheet_state = "veryHidden"

    data = workbook_bytes(build)
    got = _by_cell(data)
    assert (got["A1"][1].row_hidden, got["A1"][1].column_hidden) == (False, False)
    assert got["A2"][1].row_hidden is True and got["C1"][1].column_hidden is True
    _, sheets, _ = _parse(data)
    assert [(s.name, s.position, s.state) for s in sheets] == [
        ("Sheet", 0, "visible"),
        ("H", 1, "hidden"),
        ("V", 2, "veryHidden"),
    ]
    assert _by_cell(data, "H")["A1"][1].value == "h" and _by_cell(data, "V")["A1"][1].value == "v"


def test_merged_cells_recorded() -> None:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["A1"] = "Hdr"
        ws.merge_cells("A1:C1")

    data = workbook_bytes(build)
    got = _by_cell(data)
    # owner question S3-Q13 (pending): merged non-anchor cells are not emitted
    assert set(got) == {"A1"} and got["A1"][1].merged_range == "A1:C1"
    assert _parse(data)[1][0].merged_ranges == ("A1:C1",)


def test_text_verbatim() -> None:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["A1"] = "OT-1  "
        ws["A2"] = " x"

    got = _by_cell(workbook_bytes(build))
    for ref, text in (("A1", "OT-1  "), ("A2", " x")):
        assert got[ref][1].value == text and got[ref][0].snippet == text


def test_empty_cells_not_emitted() -> None:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["A1"] = "x"
        ws["B2"].font = Font(bold=True)

    assert set(_by_cell(workbook_bytes(build))) == {"A1"}


def test_sheet_grid_cap() -> None:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["A1"] = 1
        ws["Z200"] = 2

    _rejects(workbook_bytes(build), "sheet_too_large", Limits(sheet_max_cells=1000))


def test_chartsheet_refused() -> None:
    # owner question S3-Q13 (pending): chartsheets are refused
    _rejects(workbook_bytes(lambda wb: (wb.create_chartsheet(), None)[1]), "unsupported_cell")


def test_timedelta_refused() -> None:
    def build(wb: Workbook) -> None:
        wb.active["A1"] = dt.timedelta(hours=1)  # type: ignore[index]  # pyright: ignore

    _rejects(workbook_bytes(build), "unsupported_cell")


def _render(v: object) -> str:
    # the test's own copy of the snippet rule
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(Decimal(repr(v)))
    if isinstance(v, (dt.date, dt.time)):
        return v.isoformat()
    return str(v)


def test_locators_resolve_independently() -> None:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["A1"], ws["B1"], ws["C3"], ws["D4"] = "t", 40, 37.5, True
        ws["E5"] = dt.date(2026, 1, 2)
        wb.create_sheet("Two")["B2"] = "z"

    data = workbook_bytes(build)
    locs, _, cells = _parse(data)
    assert len(locs) == 6 and len(cells) == 6
    wb = load_workbook(BytesIO(data), data_only=True)
    for loc in locs:
        assert loc.snippet == _render(wb[loc.sheet][loc.cell].value)
        assert loc.document_version_id == 7 and loc.extractor == "xlsx_cells@1"
        assert loc.extracted_at == NOW


def test_ids_contiguous_and_ordered() -> None:
    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["B2"], ws["A1"], ws["C1"] = "b", "a", "c"
        wb.create_sheet("Two")["A1"] = "z"

    locs, _, cells = _parse(workbook_bytes(build), first=10)
    assert [(x.id, x.sheet, x.cell) for x in locs] == [
        (10, "Sheet", "A1"),
        (11, "Sheet", "C1"),
        (12, "Sheet", "B2"),
        (13, "Two", "A1"),
    ]
    assert [c.locator_id for c in cells] == [10, 11, 12, 13]


def test_deterministic() -> None:
    data = _hand('<row r="1"><c r="A1"><v>1.50</v></c></row>')
    assert _parse(data) == _parse(data)


def test_profile_text_in_cells_is_just_text() -> None:
    def build(wb: Workbook) -> None:
        wb.active["A1"] = "ukg_pro_wfm"  # type: ignore[index]  # pyright: ignore

    assert _by_cell(workbook_bytes(build))["A1"][1].value_type == "string"
    assert "product_profile" not in CellFragment.model_fields


def test_parse_does_not_iterate_the_grid(monkeypatch: pytest.MonkeyPatch) -> None:
    from openpyxl.worksheet.worksheet import Worksheet

    def boom(*a: object, **k: object) -> None:
        raise AssertionError("iter_rows allocates the full row x column grid")

    monkeypatch.setattr(Worksheet, "iter_rows", boom)

    def build(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["A1"], ws["Z40"] = "a", "z"

    assert set(_by_cell(workbook_bytes(build))) == {"A1", "Z40"}


def test_post_load_check_is_independent_of_the_prescan(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.ingest.xlsx as xlsx_mod

    def noop(data: bytes, limits: Limits) -> dict[str, Any]:
        return {}

    monkeypatch.setattr(xlsx_mod, "inspect_xlsx_package", noop)

    def grid(wb: Workbook) -> None:
        ws = wb.active
        assert ws is not None
        ws["A1"], ws["Z200"] = 1, 2

    _rejects(workbook_bytes(grid), "sheet_too_large", Limits(sheet_max_cells=1000))

    def many(wb: Workbook) -> None:
        for i in range(3):
            ws = wb.active if i == 0 else wb.create_sheet()
            assert ws is not None
            ws["A1"], ws["B1"], ws["A2"], ws["B2"] = 1, 2, 3, 4

    _rejects(
        workbook_bytes(many), "sheet_too_large", Limits(sheet_max_cells=1000, workbook_max_cells=10)
    )


def test_openpyxl_failure_maps_to_workbook_malformed() -> None:
    _rejects(
        _hand('<row r="1"><c r="A1" t="n"><v>not-a-number</v></c></row>'), "workbook_malformed"
    )


def test_any_unexpected_exception_maps_to_a_fixed_reason(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import app.ingest.xlsx as xlsx_mod
    from tests.ingest.hostile import MARKER

    def boom(data: bytes, limits: Limits) -> dict[str, Any]:
        raise RuntimeError(MARKER)

    monkeypatch.setattr(xlsx_mod, "inspect_xlsx_package", boom)
    with caplog.at_level(logging.DEBUG), pytest.raises(IntakeRejected) as ei:
        _parse(workbook_bytes(lambda wb: None))
    exc = ei.value
    assert exc.reason == "workbook_malformed"
    assert MARKER not in str(exc) and MARKER not in repr(exc)
    assert exc.__cause__ is None and exc.__suppress_context__
    assert all(MARKER not in r.getMessage() and r.exc_info is None for r in caplog.records)
