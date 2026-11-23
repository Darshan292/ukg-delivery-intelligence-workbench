# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour."""

from openpyxl import Workbook

from app.extract.catalogue import ReferenceColumn
from tests.extract.helpers import SHEETS, bounds, edges, entities, nm_refs, put, run

LIMITS = [["limit_id", "hours"], ["L-1", 40]]


def with_bundles(*rows: list[object]) -> object:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", LIMITS)
        put(wb, "Bundles", [["bundle_id", "limit"], *rows])

    return build


def test_dangling_reference() -> None:
    _, x = run(with_bundles(["B-1", "L-9"]))  # type: ignore[arg-type]
    assert nm_refs(x) == {("missing_target", "B-1", "L-9", "Bundles!B2")}
    assert not edges(x)
    assert ("synthetic", "limit", "L-9") not in entities(x)  # no entity is invented


def test_alias_spelling() -> None:
    _, x = run(with_bundles(["B-1", "l-1"]))  # type: ignore[arg-type]
    assert nm_refs(x) == {("missing_target", "B-1", "l-1", "Bundles!B2")}
    assert not edges(x)  # no same_as, no case folding


def test_wrong_type_reference() -> None:
    _, x = run(with_bundles(["B-1", "L-1"], ["B-2", "B-1"]))  # type: ignore[arg-type]
    assert nm_refs(x) == {("uncatalogued_type", "B-2", "B-1", "Bundles!B3")}


def test_self_reference() -> None:
    bundle = SHEETS.sheets[1]
    parent = ReferenceColumn(header="parent", relationship_type="contains", target_type="bundle")
    bundle = bundle.model_copy(update={"references": (*bundle.references, parent)})
    sheets = SHEETS.model_copy(update={"sheets": (SHEETS.sheets[0], bundle, SHEETS.sheets[2])})

    def build(wb: Workbook) -> None:
        put(wb, "Limits", LIMITS)
        put(wb, "Bundles", [["bundle_id", "limit", "parent"], ["B-1", "L-1", "B-1"]])

    _, x = run(build, sheets=sheets)
    assert bounds(x) == {("self_reference", ("Bundles!C2",))}
    assert edges(x) == {("contains", "B-1", "L-1", None, ("Bundles!A2", "Bundles!B2"))}


def test_ambiguous_target() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [["limit_id", "hours"], ["L-1", 40], ["L-1", 41]])
        put(wb, "Bundles", [["bundle_id", "limit"], ["B-1", "L-1"]])

    _, x = run(build)
    assert bounds(x) == {
        ("duplicate_key", ("Limits!A2", "Limits!B2")),
        ("duplicate_key", ("Limits!A3", "Limits!B3")),
        ("ambiguous_target", ("Bundles!B2",)),
    }
    assert ("synthetic", "limit", "L-1") not in entities(x)
    assert not edges(x) and not nm_refs(x)
