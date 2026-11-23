# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Deterministic xlsx extraction: the Slice 3 IR of one workbook in, new `Records` out.

Pure and in-memory. It reads only the IR and the locators already in `Records`: it never reopens
the file, evaluates a formula or parses formula text, and it creates no locators. Every cell
locator of the version ends as exactly one of: cited by an entity version, a claim, an
unresolved reference or an extraction boundary, or structural (see `Extracted`).

The IR is untrusted content: no cell text, sheet name or header appears in an exception or a
log line.
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Self

from openpyxl.utils.cell import column_index_from_string, coordinate_from_string, range_boundaries
from pydantic import SkipValidation, model_validator

from app.domain.locators import XlsxCell
from app.domain.model import (
    Attribute,
    BoundaryReason,
    Entity,
    EntityVersion,
    ExtractionBoundary,
    Id,
    JsonScalar,
    ProductProfile,
    Record,
    SortedIds0,
    normalise_key_v1,
)
from app.domain.records import Records
from app.extract.catalogue import (
    CatalogueMismatch,
    SheetCatalogue,
    SheetSpec,
    check_against,
    header_norm,
)
from app.ingest.fragments import ParsedDocument

log = logging.getLogger(__name__)


class AlreadyExtracted(ValueError):
    """The version already has extraction output; re-extraction would duplicate claims."""


class Extracted(Record):
    # SkipValidation: as `Ingested`, Records is validated when built
    records: SkipValidation[Records]
    document_version_id: Id
    structural_locator_ids: SortedIds0  # header, preamble, notes-sheet and blank cells

    @model_validator(mode="after")
    def _no_silent_drop(self) -> Self:
        r, vid = self.records, self.document_version_id
        want = {x.id for x in r.locators if x.document_version_id == vid}
        got = set(self.structural_locator_ids)
        for ev in r.entity_versions:
            if ev.document_version_id == vid:
                got.update(ev.locator_ids)
        for c in r.claims:
            got.update(i for i in c.locator_ids if i in want)
        got.update(u.locator_id for u in r.unresolved_references if u.locator_id in want)
        for b in r.extraction_boundaries:
            if b.document_version_id == vid:
                got.update(b.locator_ids)
        if got != want:
            raise ValueError("extracted: locator not accounted")
        return self


# ---- cells --------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Cell:
    id: int
    sheet: str
    row: int
    col: int
    kind: str  # string, blank (whitespace only), number, boolean, date, error, no_cached
    value: JsonScalar
    span: tuple[int, int]  # columns a merged header covers (anchor only); else (col, col)


_BAD: dict[str, BoundaryReason] = {"no_cached": "no_cached_value", "error": "error_value"}


def _bad_reason(kind: str) -> BoundaryReason:
    return _BAD.get(kind, "unsupported_value")


def _load(records: Records, parsed: ParsedDocument) -> dict[str, dict[tuple[int, int], _Cell]]:
    sheets: dict[str, dict[tuple[int, int], _Cell]] = {}
    for f in parsed.cells:
        loc = records.locator_by_id[f.locator_id]
        if not isinstance(loc, XlsxCell):
            raise ValueError("extract: not a cell locator")
        letters, row = coordinate_from_string(loc.cell)
        col = column_index_from_string(letters)
        if f.formula is not None and f.value_type == "empty":
            kind = "no_cached"  # a formula is never evaluated or parsed
        elif f.value_type == "string":
            kind = "string" if str(f.value).strip() else "blank"
        else:
            kind = f.value_type
        span = (col, col)
        if f.merged_range:
            lo, _, hi, _ = range_boundaries(f.merged_range)
            span = (lo or col, hi or col)
        sheets.setdefault(loc.sheet, {})[(row, col)] = _Cell(
            f.locator_id, loc.sheet, row, col, kind, f.value, span
        )
    return sheets


# ---- the run ------------------------------------------------------------------------------


@dataclass
class _Row:
    spec: SheetSpec
    cells: dict[int, _Cell]  # non-blank cells in recognised columns, by column
    roles: dict[int, str]  # column -> role of the sheet


_Triple = tuple[ProductProfile, str, str]


@dataclass
class _Ent:
    spec: SheetSpec
    row: _Row
    key: str
    profile: ProductProfile
    key_cell: _Cell
    profile_cell: _Cell | None = None
    triple: _Triple = ("unknown", "", "")


@dataclass
class _Run:
    records: Records
    parsed: ParsedDocument
    cat: SheetCatalogue
    now: datetime
    structural: set[int] = field(default_factory=set[int])
    bounds: set[tuple[BoundaryReason, tuple[int, ...]]] = field(
        default_factory=set[tuple[BoundaryReason, tuple[int, ...]]]
    )
    rows: list[_Row] = field(default_factory=list[_Row])

    def bound(self, reason: BoundaryReason, ids: Iterable[_Cell | int]) -> None:
        got = tuple(sorted({c if isinstance(c, int) else c.id for c in ids}))
        if not got:
            raise ValueError("extract: boundary without a locator")
        self.bounds.add((reason, got))

    # -- sheets
    def scan(self, name: str, cells: dict[tuple[int, int], _Cell]) -> None:
        by_row: dict[int, list[_Cell]] = {}
        for c in cells.values():
            by_row.setdefault(c.row, []).append(c)
        found: tuple[int, SheetSpec] | None = None
        for r in sorted(by_row):
            if r > self.cat.header_scan_rows:
                break
            heads = {header_norm(str(c.value)) for c in by_row[r] if c.kind == "string"}
            hits = [s for s in self.cat.sheets if s.signature <= heads]
            if hits:
                found = (r, hits[0])
                break
        if found is None:
            self.bound("unknown_sheet", cells.values())
            return
        hrow, spec = found
        roles = _roles(spec)
        colmap: dict[int, str] = {}
        for c in by_row[hrow]:
            role = roles.get(header_norm(str(c.value))) if c.kind == "string" else None
            if role is not None:
                for col in range(c.span[0], c.span[1] + 1):
                    colmap[col] = role
            self.structural.add(c.id)
        for r in sorted(by_row):
            if r <= hrow:
                self.structural.update(c.id for c in by_row[r])
                continue
            kept: dict[int, _Cell] = {}
            for c in by_row[r]:
                if c.kind == "blank":
                    self.structural.add(c.id)
                elif c.col in colmap:
                    kept[c.col] = c
            if kept:
                self.rows.append(_Row(spec, kept, colmap))


def _roles(spec: SheetSpec) -> dict[str, str]:
    out = {header_norm(spec.key_header): "key"}
    for a in spec.attributes:
        out[header_norm(a.header)] = f"attr:{a.name}"
    return out


def _next(xs: tuple[object, ...]) -> int:
    return max((getattr(x, "id") for x in xs), default=0) + 1  # noqa: B009


def _prechecks(records: Records, parsed: ParsedDocument, cat: SheetCatalogue) -> None:
    if parsed.kind != "xlsx" or parsed.product_profile != cat.product_profile:
        raise CatalogueMismatch("extract: document does not fit the sheet catalogue")
    domain = records.catalogue_by_profile.get(cat.product_profile)
    if domain is None:
        raise CatalogueMismatch("extract: no domain catalogue for the profile")
    check_against(cat, domain)
    vid = parsed.document_version_id
    mine = set(parsed.locator_ids)
    if (
        any(e.document_version_id == vid for e in records.entity_versions)
        or any(b.document_version_id == vid for b in records.extraction_boundaries)
        or any(u.locator_id in mine for u in records.unresolved_references)
        or any(mine & set(c.locator_ids) for c in records.claims)
    ):
        raise AlreadyExtracted("extract: version already extracted")


def extract_xlsx(
    records: Records, parsed: ParsedDocument, catalogue: SheetCatalogue, *, now: datetime
) -> Extracted:
    _prechecks(records, parsed, catalogue)
    run = _Run(records, parsed, catalogue, now)
    sheets = _load(records, parsed)
    for name in sorted(sheets):
        run.scan(name, sheets[name])
    return _finish(run)


def _finish(run: _Run) -> Extracted:
    r, parsed = run.records, run.parsed
    vid = parsed.document_version_id
    ver = r.version_by_id[vid]
    profile = parsed.product_profile
    ents: list[_Ent] = []
    for row in run.rows:
        kcells = [c for col, c in sorted(row.cells.items()) if row.roles[col] == "key"]
        whole = row.cells.values()
        if not kcells:
            run.bound("missing_key", whole)
            continue
        kc = kcells[0]
        if kc.kind != "string":
            run.bound(_bad_reason(kc.kind), whole)
            continue
        key = normalise_key_v1(str(kc.value))
        ents.append(_Ent(row.spec, row, key, profile, kc))
    existing = {e.key: e for e in r.entities}
    for e in ents:
        e.triple = (e.profile, e.spec.entity_type, e.key)
    new_ents = sorted({e.triple for e in ents} - existing.keys())
    ent_id = {t: existing[t].id for t in existing}
    for i, t in enumerate(new_ents, _next(r.entities)):
        ent_id[t] = i
    versions: list[EntityVersion] = []
    for i, e in enumerate(sorted(ents, key=lambda e: e.triple), _next(r.entity_versions)):
        attrs: list[Attribute] = []
        ids = [e.key_cell.id]
        for col, c in sorted(e.row.cells.items()):
            role = e.row.roles[col]
            if role.startswith("attr:"):
                attrs.append(Attribute(name=role[5:], value=c.value, locator_id=c.id))
                ids.append(c.id)
        versions.append(
            EntityVersion(
                id=i,
                entity_id=ent_id[e.triple],
                document_version_id=vid,
                snapshot_id=ver.snapshot_id,
                attributes=tuple(attrs),
                locator_ids=tuple(ids),
            )
        )
    bounds = tuple(
        ExtractionBoundary(id=i, document_version_id=vid, reason=reason, locator_ids=ids)
        for i, (reason, ids) in enumerate(
            sorted(run.bounds, key=lambda b: (b[1], b[0])), _next(r.extraction_boundaries)
        )
    )
    out = r.extended(
        entities=tuple(
            Entity(id=ent_id[t], product_profile=t[0], entity_type=t[1], natural_key=t[2])
            for t in new_ents
        ),
        entity_versions=tuple(versions),
        extraction_boundaries=bounds,
    )
    log.info("extracted %d entities, %d boundaries", len(new_ents), len(bounds))
    return Extracted(
        records=out,
        document_version_id=vid,
        structural_locator_ids=tuple(sorted(run.structural)),
    )
