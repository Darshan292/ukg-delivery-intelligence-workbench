# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Evidence locators (issue #14): a discriminated union, one model per kind.

Each locator binds to a content-hashed DocumentVersion by id; the sha256 lives once there.
"""

import json
import re
from typing import Annotated, Final, Literal, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    Field,
    FiniteFloat,
    StringConstraints,
    TypeAdapter,
    model_validator,
)

from app.domain.model import Id, Record, Versioned

_MAX_COL, _MAX_ROW = 16384, 1_048_576  # Excel sheet limits (vendor fact, not product semantics)
_CELL = re.compile(r"^([A-Z]{1,3})([1-9][0-9]{0,6})$")


def _no_nul(s: str) -> str:
    if "\x00" in s:
        raise ValueError("locator: snippet contains NUL")  # Postgres text cannot store it
    return s


class _LocatorBase(Record):
    id: Id
    document_version_id: Id
    snippet: Annotated[
        str, AfterValidator(_no_nul)
    ]  # verbatim value or word; may be "" (an empty cell is evidence too)
    extractor: Versioned
    extracted_at: AwareDatetime


def _check_cell(cell: str) -> str:
    m = _CELL.match(cell)
    col = 0
    for ch in m.group(1) if m else "":
        col = col * 26 + ord(ch) - 64
    if not m or col > _MAX_COL or int(m.group(2)) > _MAX_ROW:
        raise ValueError("xlsx_cell: cell outside A1 range")
    return cell


class XlsxCell(_LocatorBase):
    kind: Literal["xlsx_cell"]
    sheet: Annotated[str, StringConstraints(min_length=1)]
    cell: Annotated[str, AfterValidator(_check_cell)]


class PdfWordBbox(_LocatorBase):
    kind: Literal["pdf_word_bbox"]
    page: Annotated[int, Field(ge=1)]  # 1-based pdfplumber page_number
    x0: FiniteFloat
    top: FiniteFloat
    x1: FiniteFloat
    bottom: FiniteFloat

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.x0 > self.x1 or self.top > self.bottom:
            raise ValueError("pdf_word_bbox: corners out of order")
        return self


EvidenceLocator = Annotated[XlsxCell | PdfWordBbox, Field(discriminator="kind")]
LOCATOR_ADAPTER: Final = TypeAdapter(EvidenceLocator)


def content_key(loc: XlsxCell | PdfWordBbox) -> str:
    # same position, version and extractor = same locator (re-extraction must reuse it, Q4)
    d = loc.model_dump(mode="json", exclude={"id", "snippet", "extracted_at"})
    return json.dumps(d, sort_keys=True)
