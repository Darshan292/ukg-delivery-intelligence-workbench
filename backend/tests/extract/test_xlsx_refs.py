# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Test-only. FICTIONAL: not UKG behaviour."""

from decimal import Decimal

from openpyxl import Workbook

from tests.extract.helpers import edges, nm_refs, put, run

LIMITS = [["limit_id", "hours"], ["L-1", 40]]
BUNDLES = [["bundle_id", "limit"], ["B-1", "L-1"]]


def config(wb: Workbook) -> None:
    put(wb, "Limits", LIMITS)
    put(wb, "Bundles", BUNDLES)


def test_contains_edge() -> None:
    _, x = run(config)
    assert edges(x) == {("contains", "B-1", "L-1", None, ("Bundles!A2", "Bundles!B2"))}
    (c,) = x.records.claims
    assert (c.basis, c.polarity, c.method, c.confidence) == (
        "explicit_source",
        "present",
        "test_xlsx@1",
        None,
    )
    assert c.scope_snapshot_id == 1
    assert not x.records.unresolved_references and not x.records.extraction_boundaries


def test_relationship_reused_across_snapshots() -> None:
    def second(wb: Workbook) -> None:
        put(wb, "Limits", [*LIMITS, ["L-9", Decimal(1)]])  # one extra row: a different sha
        put(wb, "Bundles", BUNDLES)

    _, x1 = run(config, snapshot_id=1)
    _, x2 = run(second, records=x1.records, snapshot_id=2)
    r = x2.records
    assert len(r.relationships) == 1
    assert sorted(c.scope_snapshot_id for c in r.claims if c.scope_snapshot_id) == [1, 2]
    assert len(r.claims) == 2


def test_unscoped_doc_resolves_existing() -> None:
    def checks(wb: Workbook) -> None:
        put(wb, "Checks", [["check_id", "verifies"], ["C-1", "B-1"]])

    _, x1 = run(config, snapshot_id=1)
    _, x2 = run(checks, records=x1.records, snapshot_id=None)
    new = {e for e in edges(x2) if e[0] == "verifies"}
    assert new == {("verifies", "C-1", "B-1", None, ("Checks!A2", "Checks!B2"))}
    (c,) = [
        c for c in x2.records.claims if c.method == "test_xlsx@1" and c.scope_snapshot_id is None
    ]
    assert c.scope_snapshot_id is None


def test_scoped_doc_never_borrows() -> None:
    def checks(wb: Workbook) -> None:
        put(wb, "Checks", [["check_id", "verifies"], ["C-1", "B-1"]])

    _, x1 = run(config, snapshot_id=1)
    _, x2 = run(checks, records=x1.records, snapshot_id=2)
    assert nm_refs(x2) == {("missing_target", "C-1", "B-1", "Checks!B2")}
    assert len(x2.records.relationships) == len(x1.records.relationships)
