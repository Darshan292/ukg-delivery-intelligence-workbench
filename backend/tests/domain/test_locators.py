# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
from datetime import UTC, datetime
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.domain.locators import LOCATOR_ADAPTER, PdfWordBbox, XlsxCell, content_key

T = datetime(2026, 1, 1, tzinfo=UTC)
COMMON: dict[str, Any] = {
    "id": 1,
    "document_version_id": 2,
    "snippet": "v",
    "extractor": "openpyxl@3.1",
    "extracted_at": T,
}
XLSX: dict[str, Any] = {**COMMON, "kind": "xlsx_cell", "sheet": "S", "cell": "B2"}
PDF: dict[str, Any] = {
    **COMMON,
    "kind": "pdf_word_bbox",
    "page": 3,
    "x0": 1.5,
    "top": 2.5,
    "x1": 10.0,
    "bottom": 12.0,
}


def test_xlsx_cell_valid_round_trip() -> None:
    loc = LOCATOR_ADAPTER.validate_python(XLSX)
    back = LOCATOR_ADAPTER.validate_json(LOCATOR_ADAPTER.dump_json(loc))
    assert back == loc
    assert isinstance(back, XlsxCell)


@pytest.mark.parametrize("cell", ["A1", "Z9", "AA10", "XFD1048576"])
def test_xlsx_cell_a1_accepts(cell: str) -> None:
    assert LOCATOR_ADAPTER.validate_python({**XLSX, "cell": cell})


@pytest.mark.parametrize("cell", ["a1", "A0", "A01", "$A$1", "A1:B2", "XFE1", "A1048577", "1A", ""])
def test_xlsx_cell_a1_rejects(cell: str) -> None:
    with pytest.raises(ValidationError):
        LOCATOR_ADAPTER.validate_python({**XLSX, "cell": cell})


def test_xlsx_cell_sheet_must_be_non_empty() -> None:
    with pytest.raises(ValidationError):
        LOCATOR_ADAPTER.validate_python({**XLSX, "sheet": ""})


def test_pdf_word_bbox_valid_round_trip() -> None:
    loc = LOCATOR_ADAPTER.validate_python(PDF)
    back = LOCATOR_ADAPTER.validate_json(LOCATOR_ADAPTER.dump_json(loc))
    assert back == loc
    assert isinstance(back, PdfWordBbox)


@pytest.mark.parametrize("page", [0, -1, 1.0, True, "1"])
def test_pdf_page_must_be_int_at_least_one(page: object) -> None:
    with pytest.raises(ValidationError):
        LOCATOR_ADAPTER.validate_python({**PDF, "page": page})


@pytest.mark.parametrize("field", ["x0", "top", "x1", "bottom"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_pdf_bbox_rejects_nan_and_inf(field: str, bad: float) -> None:
    with pytest.raises(ValidationError):
        LOCATOR_ADAPTER.validate_python({**PDF, field: bad})


def test_pdf_bbox_requires_ordered_corners() -> None:
    for bad in ({"x0": 11.0}, {"top": 13.0}):
        with pytest.raises(ValidationError):
            LOCATOR_ADAPTER.validate_python({**PDF, **bad})
    assert LOCATOR_ADAPTER.validate_python({**PDF, "x0": 10.0})  # x0 == x1


def test_pdf_bbox_accepts_int_coordinates_as_float() -> None:
    loc = LOCATOR_ADAPTER.validate_python({**PDF, "x0": 1, "x1": 2, "top": 1, "bottom": 2})
    assert isinstance(loc, PdfWordBbox)
    assert loc.x0 == 1.0


def test_unknown_kind_rejected() -> None:
    with pytest.raises(ValidationError) as e:
        LOCATOR_ADAPTER.validate_python({**PDF, "kind": "pdf_bbox"})
    assert e.value.errors()[0]["type"] == "union_tag_invalid"


@pytest.mark.parametrize("base", [XLSX, PDF])
def test_extra_field_rejected(base: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        LOCATOR_ADAPTER.validate_python({**base, "file": "x.xlsx"})


@pytest.mark.parametrize(
    ("base", "field"),
    [(XLSX, f) for f in XLSX] + [(PDF, f) for f in PDF],
)
def test_missing_field_rejected(base: dict[str, Any], field: str) -> None:
    d = {k: v for k, v in base.items() if k != field}
    with pytest.raises(ValidationError):
        LOCATOR_ADAPTER.validate_python(d)


def test_locator_requires_document_version_and_versioned_extractor() -> None:
    d = {k: v for k, v in XLSX.items() if k != "document_version_id"}
    with pytest.raises(ValidationError):
        LOCATOR_ADAPTER.validate_python(d)
    with pytest.raises(ValidationError):
        LOCATOR_ADAPTER.validate_python({**XLSX, "extractor": "openpyxl"})


@pytest.mark.parametrize("raw", [XLSX, PDF])
def test_snippet_rejects_nul(raw: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):  # Postgres text cannot store NUL
        LOCATOR_ADAPTER.validate_python({**raw, "snippet": "a\x00b"})


def test_locator_is_frozen() -> None:
    loc = LOCATOR_ADAPTER.validate_python(XLSX)
    with pytest.raises(ValidationError):
        loc.snippet = "z"  # pyright: ignore[reportAttributeAccessIssue]


def test_locator_content_key_ignores_id_and_time() -> None:
    a = LOCATOR_ADAPTER.validate_python(XLSX)
    b = LOCATOR_ADAPTER.validate_python(
        {**XLSX, "id": 9, "snippet": "other", "extracted_at": datetime(2027, 1, 1, tzinfo=UTC)}
    )
    assert content_key(a) == content_key(b)
    for change in ({"cell": "C3"}, {"document_version_id": 3}, {"extractor": "openpyxl@3.2"}):
        assert content_key(LOCATOR_ADAPTER.validate_python({**XLSX, **change})) != content_key(a)


_common = {
    "id": st.integers(1, 10**6),
    "document_version_id": st.integers(1, 10**6),
    "snippet": st.text(
        alphabet=st.characters(blacklist_characters="\x00", blacklist_categories=("Cs",))
    ),
    "extractor": st.just("x@1"),
    "extracted_at": st.just(T),
}
xlsx_cells = st.fixed_dictionaries(
    {
        **_common,
        "kind": st.just("xlsx_cell"),
        "sheet": st.text(min_size=1),
        "cell": st.from_regex(r"[A-Z]{1,2}[1-9][0-9]{0,5}", fullmatch=True),
    }
)
_f = st.floats(0, 1000, allow_nan=False)
pdf_boxes = st.tuples(_f, _f, _f, _f).flatmap(
    lambda t: st.just(
        {
            **PDF,
            "x0": min(t[0], t[2]),
            "x1": max(t[0], t[2]),
            "top": min(t[1], t[3]),
            "bottom": max(t[1], t[3]),
        }
    )
)


@given(st.one_of(xlsx_cells, pdf_boxes))
def test_locator_json_round_trip(d: dict[str, Any]) -> None:
    loc = LOCATOR_ADAPTER.validate_python(d)
    assert LOCATOR_ADAPTER.validate_json(LOCATOR_ADAPTER.dump_json(loc)) == loc
