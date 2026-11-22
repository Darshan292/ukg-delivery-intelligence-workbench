# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""xlsx to locators and IR fragments. Pure and deterministic; every failure is a reason code.

shortcut: defined names, data validations, comments, hyperlinks and the values openpyxl
overwrites in non-anchor merged cells are not extracted; add them when a slice needs them.
"""

import datetime as dt
import warnings
from datetime import datetime
from io import BytesIO
from typing import Any

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.worksheet.worksheet import Worksheet

from app.domain.locators import XlsxCell
from app.domain.model import number_from_cell_value
from app.ingest.errors import IntakeRejected, Limits
from app.ingest.fragments import CellFragment, SheetFragment, ValueType
from app.ingest.ooxml import inspect_xlsx_package

EXTRACTOR = "xlsx_cells@1"


def _render(v: object, data_type: str) -> tuple[Any, ValueType, str]:
    """(model value, value type, snippet) for one cached cell value."""
    if v is None:
        return None, "empty", ""
    if data_type == "e":
        return str(v), "error", str(v)
    if isinstance(v, bool):
        return v, "boolean", "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        try:
            n = number_from_cell_value(v)
        except ValueError:
            raise IntakeRejected("unsupported_cell") from None
        return n, "number", str(n)
    if isinstance(v, str):
        return v, "string", v  # verbatim: no strip (key normalisation is Slice 4's job)
    if isinstance(v, (dt.datetime, dt.date, dt.time)) and not isinstance(v, dt.timedelta):
        # owner question S3-Q8 (pending): date cells as ISO text with value_type "date"
        iso = v.isoformat()
        return iso, "date", iso
    raise IntakeRejected("unsupported_cell")  # timedelta and anything else


def _hidden_columns(ws: Worksheet) -> set[int]:
    out: set[int] = set()
    for d in ws.column_dimensions.values():
        if d.hidden and d.min is not None and d.max is not None:
            out.update(range(d.min, min(d.max, ws.max_column) + 1))
    return out


def _parse(
    data: bytes, version_id: int, first_locator_id: int, now: datetime, limits: Limits
) -> tuple[tuple[XlsxCell, ...], tuple[SheetFragment, ...], tuple[CellFragment, ...]]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # openpyxl exposes either formulas or cached values, never both: load twice
        wb_f = load_workbook(BytesIO(data), data_only=False, keep_vba=False, keep_links=False)
        wb_v = load_workbook(BytesIO(data), data_only=True, keep_vba=False, keep_links=False)
    locs: list[XlsxCell] = []
    sheets: list[SheetFragment] = []
    cells: list[CellFragment] = []
    next_id = first_locator_id
    for position, ws_f in enumerate(wb_f.worksheets):
        ws_v = wb_v[ws_f.title]
        if ws_f.max_row * ws_f.max_column > limits.sheet_max_cells:
            raise IntakeRejected("sheet_too_large")
        merges = sorted(str(r) for r in ws_f.merged_cells.ranges)
        anchors = {(r.min_row, r.min_col): str(r) for r in ws_f.merged_cells.ranges}
        hidden_rows = {i for i, d in ws_f.row_dimensions.items() if d.hidden}
        hidden_cols = _hidden_columns(ws_f)
        sheets.append(
            SheetFragment(
                name=ws_f.title,
                position=position,
                state=ws_f.sheet_state,
                merged_ranges=tuple(merges),
            )
        )
        for row_f, row_v in zip(ws_f.iter_rows(), ws_v.iter_rows(), strict=True):
            for c_f, c_v in zip(row_f, row_v, strict=True):
                if isinstance(c_f, MergedCell):
                    continue  # owner question S3-Q13 (pending): non-anchor merged cells not emitted
                formula: str | None = None
                if c_f.data_type == "f":
                    raw = c_f.value
                    if isinstance(raw, ArrayFormula):
                        formula = raw.text
                    elif isinstance(raw, str):
                        formula = raw
                    else:
                        raise IntakeRejected("unsupported_cell")
                value, vtype, snippet = _render(c_v.value, c_v.data_type)
                if formula is None and vtype == "empty":
                    continue
                locs.append(
                    XlsxCell(
                        id=next_id,
                        document_version_id=version_id,
                        snippet=snippet,
                        extractor=EXTRACTOR,
                        extracted_at=now,
                        kind="xlsx_cell",
                        sheet=ws_f.title,
                        cell=c_f.coordinate,
                    )
                )
                cells.append(
                    CellFragment(
                        locator_id=next_id,
                        formula=formula,
                        value=value,
                        value_type=vtype,
                        row_hidden=c_f.row in hidden_rows,
                        column_hidden=c_f.column in hidden_cols,
                        merged_range=anchors.get((c_f.row, c_f.column)),
                    )
                )
                next_id += 1
    return tuple(locs), tuple(sheets), tuple(cells)


def parse_xlsx(
    data: bytes, *, version_id: int, first_locator_id: int, now: datetime, limits: Limits
) -> tuple[tuple[XlsxCell, ...], tuple[SheetFragment, ...], tuple[CellFragment, ...]]:
    parts = inspect_xlsx_package(data, limits)
    if any(
        e.get("Type", "").endswith("/chartsheet")
        for n, root in parts.items()
        if n.endswith(".rels")
        for e in root
    ):
        # owner question S3-Q13 (pending): chartsheets are refused (checked here: openpyxl
        # itself raises on an empty one)
        raise IntakeRejected("unsupported_cell")
    try:
        return _parse(data, version_id, first_locator_id, now, limits)
    except IntakeRejected:
        raise
    except Exception:  # openpyxl and pydantic raise many types on hostile input
        raise IntakeRejected("workbook_malformed") from None
