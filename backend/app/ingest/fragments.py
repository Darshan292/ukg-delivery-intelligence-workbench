# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Intake IR: facts a locator cannot hold. Position and snippet live once, on the locator."""

from typing import Annotated, Literal, Self

from pydantic import Field, FiniteFloat, model_validator

from app.domain.model import Id, JsonScalar, NonBlank, ProductProfile, Record

ValueType = Literal["string", "number", "boolean", "date", "error", "empty"]


class SheetFragment(Record):
    name: NonBlank  # equals XlsxCell.sheet of its cells
    position: Annotated[int, Field(ge=0)]  # workbook order
    state: Literal["visible", "hidden", "veryHidden"]
    merged_ranges: tuple[str, ...]  # sorted, e.g. ("A1:C1",)


class CellFragment(Record):
    locator_id: Id  # an XlsxCell; its snippet = rendering of `value`
    formula: str | None  # from the formula workbook, e.g. "=A1*2"
    value: JsonScalar  # cached value; Decimal for numbers, ISO text for dates
    value_type: ValueType  # "empty" = no cached value
    row_hidden: bool
    column_hidden: bool
    merged_range: str | None  # set on the anchor cell of a merged range


class PageFragment(Record):
    page: Annotated[int, Field(ge=1)]
    width: FiniteFloat
    height: FiniteFloat
    word_locator_ids: tuple[Id, ...]  # extract_words order; () = no text layer


class ParsedDocument(Record):
    document_version_id: Id
    product_profile: ProductProfile
    kind: Literal["xlsx", "pdf"]
    sheets: tuple[SheetFragment, ...] = ()
    cells: tuple[CellFragment, ...] = ()
    pages: tuple[PageFragment, ...] = ()

    @property
    def locator_ids(self) -> tuple[int, ...]:
        return (
            *(c.locator_id for c in self.cells),
            *(i for p in self.pages for i in p.word_locator_ids),
        )

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.kind == "xlsx" and self.pages:
            raise ValueError("parsed: xlsx document cannot have pages")
        if self.kind == "pdf" and (self.sheets or self.cells):
            raise ValueError("parsed: pdf document cannot have sheets or cells")
        ids = self.locator_ids
        if len(set(ids)) != len(ids):
            raise ValueError("parsed: locator referenced twice")
        return self
