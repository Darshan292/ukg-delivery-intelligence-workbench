# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour."""

from app.domain.model import Catalogue, EntityTypeSpec, RelationshipTypeSpec
from app.extract.catalogue import AttributeColumn, ReferenceColumn, SheetCatalogue, SheetSpec

DOMAIN = Catalogue(
    product_profile="synthetic",
    entity_types=(
        EntityTypeSpec(name="limit", snapshot_scoped=True, display_only_attributes=("label",)),
        EntityTypeSpec(name="bundle", snapshot_scoped=True),
        EntityTypeSpec(name="check", snapshot_scoped=False),
    ),
    relationship_types=(
        RelationshipTypeSpec(name="contains"),
        RelationshipTypeSpec(name="verifies"),
        RelationshipTypeSpec(name="asserts_value", qualifier_required=True),
    ),
)
SHEETS = SheetCatalogue(
    product_profile="synthetic",
    method="test_xlsx@1",
    notes_sheets=("About",),
    sheets=(
        SheetSpec(
            entity_type="limit",
            key_header="limit_id",
            required_headers=("hours",),
            attributes=(
                AttributeColumn(header="hours", name="hours"),
                AttributeColumn(header="label", name="label"),
            ),
        ),
        SheetSpec(
            entity_type="bundle",
            key_header="bundle_id",
            references=(
                ReferenceColumn(header="limit", relationship_type="contains", target_type="limit"),
            ),
        ),
        SheetSpec(
            entity_type="check",
            key_header="check_id",
            attributes=(AttributeColumn(header="expected", name="expected"),),
            references=(
                ReferenceColumn(
                    header="verifies", relationship_type="verifies", target_type="bundle"
                ),
                ReferenceColumn(
                    header="asserts",
                    relationship_type="asserts_value",
                    target_type="limit",
                    qualifier_header="asserts_attribute",
                ),
            ),
        ),
    ),
)


# ---- fixtures and readable views (keyed by cell address, never by id) ----

from collections.abc import Callable, Sequence  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from typing import Any  # noqa: E402

from openpyxl import Workbook  # noqa: E402
from openpyxl.worksheet.worksheet import Worksheet  # noqa: E402

from app.domain.model import Actor, Snapshot  # noqa: E402
from app.domain.records import Records  # noqa: E402
from app.extract.xlsx import Extracted, extract_xlsx  # noqa: E402
from app.ingest.intake import Ingested, ingest  # noqa: E402
from tests.ingest.hostile import workbook_bytes  # noqa: E402

NOW = datetime(2026, 11, 23, tzinfo=UTC)


def base_records() -> Records:
    snaps = tuple(
        Snapshot(
            id=i, product_profile="synthetic", environment="dev", label=f"S{i}", captured_at=NOW
        )
        for i in (1, 2)
    )
    up = Actor(id=1, kind="human", display_name="Uploader", roles=frozenset())
    return Records(catalogues=(DOMAIN,), actors=(up,), snapshots=snaps)


def put(wb: Workbook, name: str, rows: Sequence[Sequence[Any]]) -> Worksheet:
    """Write `rows` (None = no cell) to a sheet named `name`; the first call renames the default."""
    if wb.sheetnames == ["Sheet"] and wb.active is not None and wb.active.max_row == 1:
        ws = wb.active
        ws.title = name
    else:
        ws = wb.create_sheet(name)
    for r, row in enumerate(rows, 1):
        for c, v in enumerate(row, 1):
            if v is not None:
                ws.cell(row=r, column=c, value=v)
    return ws


def run(
    build: Callable[[Workbook], object],
    *,
    records: Records | None = None,
    snapshot_id: int | None = 1,
    sheets: SheetCatalogue = SHEETS,
) -> tuple[Ingested, Extracted]:
    ing = ingest(
        records or base_records(),
        workbook_bytes(lambda wb: (build(wb), None)[1]),
        declared_kind="xlsx",
        product_profile="synthetic",
        title="t",
        uploaded_by=1,
        snapshot_id=snapshot_id,
        now=NOW,
    )
    return ing, extract_xlsx(ing.records, ing.parsed, sheets, now=NOW)


def addr(x: Extracted, locator_id: int) -> str:
    loc = x.records.locator_by_id[locator_id]
    assert loc.kind == "xlsx_cell"
    return f"{loc.sheet}!{loc.cell}"


def entities(x: Extracted) -> set[tuple[str, str, str]]:
    return {e.key for e in x.records.entities}


def attrs(x: Extracted, key: str) -> dict[str, Any]:
    e = next(e for e in x.records.entities if e.natural_key == key)
    ev = [v for v in x.records.entity_versions if v.entity_id == e.id][-1]
    return {a.name: a.value for a in ev.attributes}


def edges(x: Extracted) -> set[tuple[Any, ...]]:
    r = x.records
    out: set[tuple[Any, ...]] = set()
    for c in r.claims:
        rel = r.relationship_by_id[c.relationship_id]
        out.add(
            (
                rel.type,
                r.entity_by_id[rel.source_entity_id].natural_key,
                r.entity_by_id[rel.target_entity_id].natural_key,
                rel.qualifier,
                tuple(addr(x, i) for i in c.locator_ids),
            )
        )
    return out


def nm_refs(x: Extracted) -> set[tuple[str, str, str, str]]:
    r = x.records
    return {
        (u.reason, r.entity_by_id[u.holder_entity_id].natural_key, u.raw_reference,
         addr(x, u.locator_id))
        for u in r.unresolved_references
    }  # fmt: skip


def bounds(x: Extracted) -> set[tuple[str, tuple[str, ...]]]:
    return {
        (b.reason, tuple(addr(x, i) for i in b.locator_ids))
        for b in x.records.extraction_boundaries
    }
