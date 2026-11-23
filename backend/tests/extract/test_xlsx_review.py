# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Review findings 2, 3, 5, 11 (xlsx). Test-only. FICTIONAL: not UKG behaviour."""

from typing import Any

from openpyxl import Workbook

from app.extract.catalogue import ReferenceColumn
from tests.extract.helpers import SHEETS, bounds, edges, entities, nm_refs, put, run


def test_notes_sheet_holding_a_signature_is_ambiguous_not_dropped() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "about", [["limit_id", "hours"], ["L-1", 40]])

    _, x = run(build)
    assert bounds(x) == {("ambiguous_sheet", ("about!A1", "about!B1", "about!A2", "about!B2"))}
    assert not x.records.entities


def test_non_string_cell_above_header_is_stated() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [["L-0", 99], ["limit_id", "hours"], ["L-1", 40]])

    _, x = run(build)
    assert bounds(x) == {("unsupported_value", ("Limits!B1",))}
    assert entities(x) == {("synthetic", "limit", "L-1")}


def test_unscoped_target_in_two_profiles_is_ambiguous() -> None:
    def checks(wb: Workbook) -> None:
        put(wb, "Checks", [["check_id", "verifies"], ["C-1", "B-1"]])

    # one key as a synthetic and as an unknown bundle, from two documents
    def known(wb: Workbook) -> None:
        put(wb, "Bundles", [["bundle_id"], ["B-1"]])

    def unknown(wb: Workbook) -> None:
        put(wb, "Bundles", [["bundle_id", "product_profile"], ["B-1", "unknown"]])

    _, x1 = run(known, snapshot_id=None)
    _, x2 = run(unknown, records=x1.records, snapshot_id=None)
    _, x3 = run(checks, records=x2.records, snapshot_id=None)
    assert ("ambiguous_target", ("Checks!B2",)) in bounds(x3)
    assert not edges(x3) and not nm_refs(x3)


def test_self_reference_of_unknown_entity_is_self_reference() -> None:
    bundle = SHEETS.sheets[1]
    parent = ReferenceColumn(header="parent", relationship_type="contains", target_type="bundle")
    bundle = bundle.model_copy(update={"references": (*bundle.references, parent)})
    sheets = SHEETS.model_copy(update={"sheets": (SHEETS.sheets[0], bundle, SHEETS.sheets[2])})

    def build(wb: Workbook) -> None:
        rows: list[list[Any]] = [
            ["bundle_id", "parent", "product_profile"],
            ["B-1", "B-1", "unknown"],
        ]
        put(wb, "Bundles", rows)

    _, x = run(build, sheets=sheets)
    assert ("self_reference", ("Bundles!B2",)) in bounds(x)
    assert not nm_refs(x)
