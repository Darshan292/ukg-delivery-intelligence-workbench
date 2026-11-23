# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour."""

from decimal import Decimal
from typing import Any

from openpyxl import Workbook

from tests.extract.helpers import attrs, bounds, edges, nm_refs, put, run

CHECK_HEAD = ["check_id", "expected", "asserts", "asserts_attribute"]


def build_with(*check_rows: list[Any]) -> Any:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [["limit_id", "hours"], ["L-1", 40]])
        put(wb, "Checks", [CHECK_HEAD, *check_rows])

    return build


def test_asserts_value_edge() -> None:
    _, x = run(build_with(["C-1", 40, "L-1", "hours"]))
    assert edges(x) == {
        ("asserts_value", "C-1", "L-1", "hours", ("Checks!A2", "Checks!C2", "Checks!D2"))
    }
    assert attrs(x, "C-1") == {"expected": Decimal("40")}


def test_missing_qualifier() -> None:
    _, x = run(build_with(["C-1", 40, "L-1", "   "]))
    assert bounds(x) == {("missing_qualifier", ("Checks!C2", "Checks!D2"))}
    assert not edges(x)


def test_qualifier_trimmed() -> None:
    _, x = run(build_with(["C-1", 40, "L-1", " hours "]))
    assert {e[3] for e in edges(x)} == {"hours"}
    snippets = {loc.snippet for loc in x.records.locators if getattr(loc, "cell", "") == "D2"}
    assert snippets == {" hours "}


def test_qualifier_of_unresolved_reference_is_accounted() -> None:
    _, x = run(build_with(["C-1", 40, "L-9", "hours"]))
    assert nm_refs(x) == {("missing_target", "C-1", "L-9", "Checks!C2")}
    assert not edges(x)  # the invariant (Extracted) already proves D2 is accounted for


def test_orphan_qualifier_is_stated() -> None:
    _, x = run(build_with(["C-1", 40, None, "hours"]))
    assert bounds(x) == {("unsupported_value", ("Checks!D2",))}
