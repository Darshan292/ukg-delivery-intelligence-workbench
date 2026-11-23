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
from typing import Literal, Self

from openpyxl.utils.cell import column_index_from_string, coordinate_from_string, range_boundaries
from pydantic import SkipValidation, model_validator

from app.domain.locators import XlsxCell
from app.domain.model import (
    Attribute,
    Basis,
    BoundaryReason,
    Claim,
    Entity,
    EntityVersion,
    ExtractionBoundary,
    Id,
    JsonScalar,
    ProductProfile,
    Record,
    Relationship,
    SortedIds0,
    UnresolvedReference,
    normalise_key_v1,
)
from app.domain.records import Records
from app.extract.catalogue import (
    CatalogueMismatch,
    ReferenceColumn,
    SheetCatalogue,
    SheetSpec,
    check_against,
    header_norm,
)
from app.ingest.fragments import ParsedDocument

log = logging.getLogger(__name__)

UnresolvedReason = Literal["missing_target", "uncatalogued_type", "unknown_profile"]


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


# owner question S4-P5 (pending): a formula without a cached value is a `no_cached_value`
# boundary; the attribute is omitted and the formula is never evaluated or parsed.
_BAD: dict[str, BoundaryReason] = {"no_cached": "no_cached_value", "error": "error_value"}


def _cell_kind(formula: str | None, value_type: str, value: JsonScalar) -> str:
    """The reading of one cell. A formula without a cached value is `no_cached` (S4-P5): it is
    never evaluated or parsed."""
    if formula is not None and value_type == "empty":
        return "no_cached"
    if value_type == "string":
        return "string" if str(value).strip() else "blank"
    return value_type


def _bad_reason(kind: str) -> BoundaryReason:
    return _BAD.get(kind, "unsupported_value")


# owner question S4-P3 (pending): hidden rows, columns and sheets are ordinary data
def _hidden_policy(
    row_hidden: bool, column_hidden: bool, sheet_state: str
) -> Literal["extract", "boundary"]:
    """hidden is not deleted: extract as ordinary data. A different answer returns "boundary"
    and the cell is stated as `hidden_cell`, never blanked. The flags live in the IR only."""
    return "extract"


# owner question S4-P6 (pending): a declared notes sheet is structural, no boundary
def _is_notes_sheet(name: str, cat: SheetCatalogue) -> bool:
    """a declared notes sheet (the FICTIONAL label) is
    structural and states no boundary; any other unrecognised sheet is one unknown_sheet."""
    return header_norm(name) in {header_norm(n) for n in cat.notes_sheets}


# owner question S4-P2 (pending): alias spelling is missing_target, verbatim, no folding
def _not_found_reason(other_types_with_key: set[str]) -> UnresolvedReason:
    """an alias spelling (`l-1` for `L-1`) is `missing_target`
    with the verbatim text: no case folding and no same_as suggestion in Milestone 1."""
    return "uncatalogued_type" if other_types_with_key else "missing_target"


# owner question S4-P4 (pending): explicit asserts_value columns give an explicit_source claim
def _assertion_basis() -> Basis:
    """an asserts_value relationship from explicit object and
    attribute columns is an `explicit_source` claim (established), not a value-match rule."""
    return "explicit_source"


def _load(
    records: Records, parsed: ParsedDocument
) -> tuple[dict[str, dict[tuple[int, int], _Cell]], dict[str, list[int]]]:
    sheets: dict[str, dict[tuple[int, int], _Cell]] = {}
    hidden: dict[str, list[int]] = {}
    state = {s.name: s.state for s in parsed.sheets}
    for f in parsed.cells:
        loc = records.locator_by_id[f.locator_id]
        if not isinstance(loc, XlsxCell):
            raise ValueError("extract: not a cell locator")
        letters, row = coordinate_from_string(loc.cell)
        col = column_index_from_string(letters)
        kind = _cell_kind(f.formula, f.value_type, f.value)
        if _hidden_policy(
            f.row_hidden, f.column_hidden, state.get(loc.sheet, "visible")
        ) == "boundary" and (
            f.row_hidden or f.column_hidden or state.get(loc.sheet, "visible") != "visible"
        ):
            hidden.setdefault(loc.sheet, []).append(f.locator_id)
            continue
        span = (col, col)
        if f.merged_range:
            lo, _, hi, _ = range_boundaries(f.merged_range)
            span = (lo or col, hi or col)
        sheets.setdefault(loc.sheet, {})[(row, col)] = _Cell(
            f.locator_id, loc.sheet, row, col, kind, f.value, span
        )
    return sheets, hidden


# ---- the run ------------------------------------------------------------------------------


@dataclass
class _Row:
    spec: SheetSpec
    cells: dict[int, _Cell]  # non-blank cells in recognised columns, by column
    roles: dict[int, str]  # column -> role of the sheet
    blanks: dict[int, _Cell]  # whitespace-only cells in recognised columns (structural)


_Triple = tuple[ProductProfile, str, str]
_EdgeKey = tuple[str, _Triple, _Triple, str | None]  # type, source, target, qualifier
_Unresolved = tuple[_Triple, str, int, UnresolvedReason]  # holder, raw, locator id, reason


def _rel_sort(k: _EdgeKey) -> tuple[str, _Triple, _Triple, str]:
    return (k[0], k[1], k[2], k[3] or "")


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
    def _find_header(
        self, by_row: dict[int, list[_Cell]]
    ) -> tuple[int, SheetSpec] | Literal["ambiguous"] | None:
        for r in sorted(by_row):
            if r > self.cat.header_scan_rows:
                break
            heads = {header_norm(str(c.value)) for c in by_row[r] if c.kind == "string"}
            hits = [s for s in self.cat.sheets if s.signature <= heads]
            if len(hits) > 1:
                return "ambiguous"
            if hits:
                return (r, hits[0])
        return None

    def scan(self, name: str, cells: dict[tuple[int, int], _Cell]) -> None:
        by_row: dict[int, list[_Cell]] = {}
        for c in cells.values():
            by_row.setdefault(c.row, []).append(c)
        found = self._find_header(by_row)
        if _is_notes_sheet(name, self.cat):
            if found is None:
                self.structural.update(c.id for c in cells.values())  # labels, not data
                return
            # a "notes" sheet that carries a real header would hide data: state it instead
            self.structural.update(c.id for c in cells.values() if c.kind == "blank")
            live = [c for c in cells.values() if c.kind != "blank"]
            if live:
                self.bound("ambiguous_sheet", live)
            return
        if found == "ambiguous":
            self.bound("ambiguous_sheet", cells.values())
            return
        if found is None:
            self.bound("unknown_sheet", cells.values())
            return
        hrow, spec = found
        roles = _roles(spec)
        colmap: dict[int, str] = {}
        stray: dict[int, list[int]] = {}  # unrecognised column -> its header and data cells
        for c in by_row[hrow]:
            role = roles.get(header_norm(str(c.value))) if c.kind == "string" else None
            if role is not None:
                for col in range(c.span[0], c.span[1] + 1):
                    colmap[col] = role
            if role is not None or c.kind == "blank":
                self.structural.add(c.id)
            else:
                for col in range(c.span[0], c.span[1] + 1):
                    stray.setdefault(col, []).append(c.id)
        for r in sorted(by_row):
            if r <= hrow:
                if r == hrow:
                    continue  # header cells were sorted into structural or stray above
                self.structural.update(c.id for c in by_row[r] if c.kind in ("string", "blank"))
                odd = [c for c in by_row[r] if c.kind not in ("string", "blank")]
                if odd:  # a number, date, error or formula above the header is data: state it
                    self.bound("unsupported_value", odd)
                continue
            kept: dict[int, _Cell] = {}
            blanks: dict[int, _Cell] = {}
            for c in by_row[r]:
                if c.kind == "blank":
                    self.structural.add(c.id)
                    if c.col in colmap:
                        blanks[c.col] = c
                elif c.col in colmap:
                    kept[c.col] = c
                else:
                    stray.setdefault(c.col, []).append(c.id)
            if kept:
                self.rows.append(_Row(spec, kept, colmap, blanks))
        for ids in stray.values():
            self.bound("unrecognised_column", ids)


def _roles(spec: SheetSpec) -> dict[str, str]:
    out = {header_norm(spec.key_header): "key", "product_profile": "profile"}
    for a in spec.attributes:
        out[header_norm(a.header)] = f"attr:{a.name}"
    for rc in spec.references:
        out[header_norm(rc.header)] = f"ref:{header_norm(rc.header)}"
        if rc.qualifier_header:
            out[header_norm(rc.qualifier_header)] = f"qual:{header_norm(rc.header)}"
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
    sheets, hidden = _load(records, parsed)
    for name in sorted(hidden):
        run.bound("hidden_cell", hidden[name])  # S4-P3 answered "do not extract hidden"
    for name in sorted(sheets):
        run.scan(name, sheets[name])
    return _finish(run)


def _finish(run: _Run) -> Extracted:
    r, parsed, cat = run.records, run.parsed, run.cat
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
        if len(kcells) > 1:  # a merged key header over two filled cells
            run.bound("duplicate_value", whole)
            continue
        kc = kcells[0]
        if kc.kind != "string":
            run.bound(_bad_reason(kc.kind), whole)
            continue
        key = normalise_key_v1(str(kc.value))
        ent_profile, pc, ok = _row_profile(run, row, profile)
        if not ok:
            continue
        ents.append(
            _Ent(row.spec, row, key, ent_profile, kc, pc, (ent_profile, row.spec.entity_type, key))
        )
    ents, dups = _split_duplicates(run, ents)
    existing = {e.key: e for e in r.entities}
    new_ents = sorted({e.triple for e in ents} - existing.keys())
    ent_id = {t: existing[t].id for t in existing}
    for i, t in enumerate(new_ents, _next(r.entities)):
        ent_id[t] = i
    resolver = _Resolver(run, ents, dups)
    versions: list[EntityVersion] = []
    for i, e in enumerate(sorted(ents, key=lambda e: e.triple), _next(r.entity_versions)):
        attrs: list[Attribute] = []
        ids = [e.key_cell.id]
        if e.profile_cell is not None:
            ids.append(e.profile_cell.id)
        if e.profile == "unknown":  # decision 0007 R1-3: the entity states itself once
            run.bound("unknown_profile_entity", ids)
        per_role: dict[str, list[_Cell]] = {}
        for col, c in sorted(e.row.cells.items()):
            per_role.setdefault(e.row.roles[col], []).append(c)
        for col, c in sorted(e.row.cells.items()):
            role = e.row.roles[col]
            if role.startswith("attr:"):
                if len(per_role[role]) > 1:  # one attribute, two values: no way to choose
                    run.bound("duplicate_value", per_role[role])
                    continue
                if c.kind in _BAD:  # the attribute is omitted, never stored as None
                    run.bound(_bad_reason(c.kind), [c])
                    continue
                attrs.append(Attribute(name=role[5:], value=c.value, locator_id=c.id))
                ids.append(c.id)
            elif role.startswith("ref:"):
                resolver.reference(e, role, c)
        resolver.leftovers(e)
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
    # relationships: reuse an existing key, else a new row in content order
    have = {
        (x.type, x.source_entity_id, x.target_entity_id, x.qualifier): x.id for x in r.relationships
    }
    rel_id: dict[_EdgeKey, int] = {}
    new_rels: list[_EdgeKey] = []
    for k in sorted(resolver.edges, key=_rel_sort):
        known = have.get((k[0], ent_id[k[1]], ent_id[k[2]], k[3]))
        if known is None:
            new_rels.append(k)
        else:
            rel_id[k] = known
    for i, k in enumerate(new_rels, _next(r.relationships)):
        rel_id[k] = i
    pairs = [
        (k, ids) for k in sorted(resolver.edges, key=_rel_sort) for ids in sorted(resolver.edges[k])
    ]
    claims = [
        Claim(
            id=i,
            relationship_id=rel_id[k],
            basis=_assertion_basis() if k[3] is not None else "explicit_source",
            polarity="present",
            method=cat.method,
            confidence=None,
            scope_snapshot_id=ver.snapshot_id,
            locator_ids=ids,
            created_at=run.now,
        )
        for i, (k, ids) in enumerate(pairs, _next(r.claims))
    ]
    unresolved = [
        UnresolvedReference(
            id=i,
            holder_entity_id=ent_id[holder],
            raw_reference=raw,
            locator_id=loc,
            reason=reason,
        )
        for i, (holder, raw, loc, reason) in enumerate(
            sorted(resolver.unresolved, key=lambda u: (u[2], u[3])), _next(r.unresolved_references)
        )
    ]
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
        relationships=tuple(
            Relationship(
                id=rel_id[k],
                type=k[0],
                source_entity_id=ent_id[k[1]],
                target_entity_id=ent_id[k[2]],
                qualifier=k[3],
                created_at=run.now,
            )
            for k in new_rels
        ),
        claims=tuple(claims),
        unresolved_references=tuple(unresolved),
        extraction_boundaries=bounds,
    )
    log.info(
        "extracted %d entities, %d relationships, %d boundaries",
        len(new_ents),
        len(new_rels),
        len(bounds),
    )
    return Extracted(
        records=out,
        document_version_id=vid,
        structural_locator_ids=tuple(sorted(run.structural)),
    )


def _row_profile(
    run: _Run, row: _Row, doc_profile: ProductProfile
) -> tuple[ProductProfile, _Cell | None, bool]:
    """The reserved product_profile cell: absent or blank is the document's profile (decision
    0003 Q7, team default); `unknown` is explicit content; anything else is stated, not guessed."""
    whole = row.cells.values()
    cells = [c for col, c in sorted(row.cells.items()) if row.roles[col] == "profile"]
    if not cells:
        return doc_profile, None, True
    if len(cells) > 1:
        run.bound("duplicate_value", whole)
        return doc_profile, None, False
    pc = cells[0]
    if pc.kind != "string":
        reason = _bad_reason(pc.kind) if pc.kind in _BAD else "invalid_profile"
        run.bound(reason, whole)
        return doc_profile, None, False
    v = str(pc.value).strip()
    if v == "unknown":
        return "unknown", pc, True
    if v == doc_profile:
        return doc_profile, pc, True
    run.bound("invalid_profile", whole)
    return doc_profile, None, False


def _split_duplicates(run: _Run, ents: list[_Ent]) -> tuple[list[_Ent], set[tuple[str, str]]]:
    """A key on two or more rows is defined but not versioned: a boundary per row."""
    count: dict[tuple[str, str], int] = {}
    for e in ents:
        count[e.triple[1:]] = count.get(e.triple[1:], 0) + 1
    dups = {k for k, n in count.items() if n > 1}
    for e in ents:
        if e.triple[1:] in dups:
            run.bound("duplicate_key", e.row.cells.values())
    return [e for e in ents if e.triple[1:] not in dups], dups


class _Resolver:
    """Reference resolution (plan rules 1 to 9); collects edges and unresolved references."""

    def __init__(self, run: _Run, ents: list[_Ent], dups: set[tuple[str, str]]) -> None:
        self.run = run
        self.dups = dups
        self.profile = run.parsed.product_profile
        self.doc: dict[tuple[str, str], _Ent] = {(e.triple[1], e.triple[2]): e for e in ents}
        self.types_of_key: dict[str, set[str]] = {}
        for e in ents:
            self.types_of_key.setdefault(e.key, set()).add(e.triple[1])
        for x in run.records.entities:
            self.types_of_key.setdefault(x.natural_key, set()).add(x.entity_type)
        self.known = {x.key for x in run.records.entities}
        self.scoped = {
            t.name: t.snapshot_scoped
            for t in run.records.catalogue_by_profile[self.profile].entity_types
        }
        self.snapshot = run.records.version_by_id[run.parsed.document_version_id].snapshot_id
        self.refcols = {
            f"ref:{header_norm(rc.header)}": rc for s in run.cat.sheets for rc in s.references
        }
        self.cited: set[int] = set()  # qualifier cells already in a claim or a boundary
        self.edges: dict[_EdgeKey, list[tuple[int, ...]]] = {}
        self.unresolved: list[_Unresolved] = []

    def target(self, target_type: str, k: str) -> _Triple | Literal["ambiguous"] | None:
        hit = self.doc.get((target_type, k))
        if hit is not None:
            return hit.triple
        if self.snapshot is not None and self.scoped.get(target_type, False):
            return None  # a snapshot export defines its own scoped objects
        hits = [
            (p, target_type, k)
            for p in (self.profile, "unknown")
            if (p, target_type, k) in self.known
        ]
        if len(hits) > 1:  # the same key as a known and an unknown entity: never guess
            return "ambiguous"
        return hits[0] if hits else None  # type: ignore[return-value]

    def reference(self, e: _Ent, role: str, c: _Cell) -> None:
        rc = self.refcols[role]
        if c.kind != "string":
            self.run.bound(_bad_reason(c.kind), [c])
            return
        qual = self.qualifier(e, role, rc, c)
        if qual is False:
            return
        raw = str(c.value)
        k = normalise_key_v1(raw)
        if (rc.target_type, k) in self.dups:
            self.run.bound("ambiguous_target", [c])
            return
        tgt = self.target(rc.target_type, k)
        if tgt == "ambiguous":
            self.run.bound("ambiguous_target", [c])
            return
        if tgt is None:
            other = self.types_of_key.get(k, set()) - {rc.target_type}
            reason = _not_found_reason(other)
            self.unresolved.append((e.triple, raw, c.id, reason))
            return
        if tgt == e.triple:  # the model rejects self loops
            self.run.bound("self_reference", [c])
            return
        if e.profile == "unknown" and tgt[0] == "unknown":
            # the Records invariant rejects an unknown-to-unknown relationship: state it instead
            self.unresolved.append((e.triple, raw, c.id, "unknown_profile"))
            return
        q, qc = qual if qual is not None else (None, None)
        key: _EdgeKey = (rc.relationship_type, e.triple, tgt, q)
        ids = (e.key_cell.id, c.id, *(() if qc is None else (qc.id,)))
        self.cited.update(() if qc is None else (qc.id,))
        self.edges.setdefault(key, []).append(tuple(sorted(ids)))

    def qualifier(
        self, e: _Ent, role: str, rc: ReferenceColumn, c: _Cell
    ) -> tuple[str, _Cell] | None | Literal[False]:
        """(qualifier text, its cell), None when the type takes none, False when reported."""
        if rc.qualifier_header is None:
            return None
        qrole = "qual:" + role[4:]
        cells = [x for col, x in sorted(e.row.cells.items()) if e.row.roles[col] == qrole]
        if not cells:
            blanks = [x for col, x in e.row.blanks.items() if e.row.roles[col] == qrole]
            self.run.bound("missing_qualifier", [c, *blanks])
            self.cited.update(x.id for x in blanks)
            return False
        if len(cells) > 1:
            self.run.bound("duplicate_value", [c, *cells])
            self.cited.update(x.id for x in cells)
            return False
        if cells[0].kind != "string":
            self.run.bound(_bad_reason(cells[0].kind), [c, cells[0]])
            self.cited.add(cells[0].id)
            return False
        return normalise_key_v1(str(cells[0].value)), cells[0]

    def leftovers(self, e: _Ent) -> None:
        """A qualifier cell no claim cites: structural if its reference is reported, else stated."""
        refs = {e.row.roles[col] for col in e.row.cells if e.row.roles[col].startswith("ref:")}
        for col, x in sorted(e.row.cells.items()):
            role = e.row.roles[col]
            if role.startswith("qual:") and x.id not in self.cited:
                if "ref:" + role[5:] in refs:
                    self.run.structural.add(x.id)  # its reference is in the not-modelled list
                else:
                    self.run.bound("unsupported_value", [x])
