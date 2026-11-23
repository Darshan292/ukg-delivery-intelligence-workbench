# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""The sheet catalogue: how a workbook expresses the domain catalogue's types.

The domain `Catalogue` says which types exist; this says only which columns carry them.
Nothing is declared twice; `check_against` fails fast where the two disagree. Error messages
name catalogue type names only, never workbook content.
"""

import re
from typing import Annotated, Final, Self

from pydantic import Field, model_validator

from app.domain.model import NonBlank, ProductProfile, Record, Versioned

RESERVED_HEADERS: Final = frozenset({"product_profile"})  # never attributes, in every sheet


def header_norm(s: str) -> str:
    """Header recognition only (never keys): strip, casefold, runs of non-word chars and _ to one _."""
    return re.sub(r"[\W_]+", "_", s.strip().casefold()).strip("_")


class CatalogueMismatch(ValueError):
    """The sheet catalogue and the domain catalogue disagree (a configuration error)."""


class AttributeColumn(Record):
    header: NonBlank
    name: NonBlank  # EntityVersion attribute name


class ReferenceColumn(Record):
    header: NonBlank
    relationship_type: NonBlank  # the holder (row entity) is always the source
    target_type: NonBlank
    qualifier_header: NonBlank | None = None  # same-row column giving the qualifier


class SheetSpec(Record):
    entity_type: NonBlank
    key_header: NonBlank
    required_headers: tuple[NonBlank, ...] = ()  # signature = {key_header, *required_headers}
    attributes: tuple[AttributeColumn, ...] = ()
    references: tuple[ReferenceColumn, ...] = ()

    @property
    def declared(self) -> list[str]:
        """Every header the spec names, normalised, in declaration order."""
        qual = [r.qualifier_header for r in self.references if r.qualifier_header]
        raw = [self.key_header, *(a.header for a in self.attributes)]
        raw += [r.header for r in self.references] + qual
        return [header_norm(h) for h in raw]

    @property
    def signature(self) -> frozenset[str]:
        return frozenset(header_norm(h) for h in (self.key_header, *self.required_headers))


class SheetCatalogue(Record):
    product_profile: ProductProfile
    method: Versioned  # claim method, e.g. "test_xlsx@1"; a catalogue change is a new version
    sheets: tuple[SheetSpec, ...]
    notes_sheets: tuple[NonBlank, ...] = ()  # label/README sheets, matched by header_norm
    header_scan_rows: Annotated[int, Field(ge=1, le=50)] = 10

    @model_validator(mode="after")
    def _static_rules(self) -> Self:
        if self.product_profile == "unknown":
            raise ValueError("sheet catalogue: unknown profile has no catalogue")
        for s in self.sheets:
            names = s.declared
            if len(set(names)) != len(names) or RESERVED_HEADERS & set(names):
                raise ValueError("sheet catalogue: headers must be distinct and not reserved")
            if not {header_norm(h) for h in s.required_headers} <= set(names):
                raise ValueError("sheet catalogue: required header is not declared")
        for field in ("entity_type", "key_header"):
            vals = [header_norm(getattr(s, field)) for s in self.sheets]
            if len(set(vals)) != len(vals):
                raise ValueError(f"sheet catalogue: {field} must be unique")
        for a in self.sheets:  # a well-formed sheet of B must never be recognised as A
            for b in self.sheets:
                if a is not b and a.signature <= set(b.declared):
                    raise ValueError("sheet catalogue: overlapping signatures")
        return self
