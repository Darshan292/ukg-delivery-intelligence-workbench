# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.ingest.fragments import CellFragment, PageFragment, ParsedDocument, SheetFragment


def _cell(i: int = 1, **kw: Any) -> CellFragment:
    base: dict[str, Any] = {
        "locator_id": i,
        "formula": None,
        "value": Decimal("37.5"),
        "value_type": "number",
        "row_hidden": False,
        "column_hidden": False,
        "merged_range": None,
    }
    return CellFragment(**{**base, **kw})


def _sheet() -> SheetFragment:
    return SheetFragment(name="S", position=0, state="visible", merged_ranges=())


def _page(ids: tuple[int, ...] = (5,)) -> PageFragment:
    return PageFragment(page=1, width=612.0, height=792.0, word_locator_ids=ids)


def _xlsx(**kw: Any) -> ParsedDocument:
    base: dict[str, Any] = {
        "document_version_id": 1,
        "product_profile": "synthetic",
        "kind": "xlsx",
        "sheets": (_sheet(),),
        "cells": (_cell(1), _cell(2)),
    }
    return ParsedDocument(**{**base, **kw})


def test_cell_value_rejects_float() -> None:
    with pytest.raises(ValidationError):
        _cell(value=37.5)
    assert _cell(value=Decimal("37.5")).value == Decimal("37.5")


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        _cell(surprise=1)


def test_pdf_document_cannot_have_cells() -> None:
    with pytest.raises(ValidationError):
        ParsedDocument(
            document_version_id=1, product_profile="synthetic", kind="pdf", cells=(_cell(),)
        )


def test_xlsx_document_cannot_have_pages() -> None:
    with pytest.raises(ValidationError):
        _xlsx(pages=(_page(),))


def test_duplicate_locator_reference_rejected() -> None:
    with pytest.raises(ValidationError):
        _xlsx(cells=(_cell(1), _cell(1)))
    with pytest.raises(ValidationError):
        ParsedDocument(
            document_version_id=1,
            product_profile="synthetic",
            kind="pdf",
            pages=(_page((5, 5)),),
        )


def test_round_trip_json() -> None:
    # a Decimal value comes back as str: JsonScalar is a str|Decimal union (domain behaviour, noted)
    p = _xlsx(cells=(_cell(1, value="x", value_type="string"), _cell(2, value=None)))
    assert ParsedDocument.model_validate_json(p.model_dump_json()) == p
