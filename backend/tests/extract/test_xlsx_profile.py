# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Reserved product_profile column and the unknown-profile shapes of issue #25.

Decisions 0003 Q7 and 0007 R1-3: a known-to-unknown reference is a relationship; the unknown
entity itself carries one entity-level boundary; only a would-be two-unknown relationship is an
UnresolvedReference(unknown_profile) with no relationship. Test-only. FICTIONAL.
"""

from openpyxl import Workbook

from tests.extract.helpers import addr, attrs, bounds, edges, entities, nm_refs, put, run

LIMITS = ["limit_id", "hours", "product_profile"]
BUNDLES = ["bundle_id", "limit", "product_profile"]


def test_profile_column_not_an_attribute() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [LIMITS, ["L-1", 40, None], ["L-2", 41, "synthetic"]])

    _, x = run(build)
    assert entities(x) == {("synthetic", "limit", "L-1"), ("synthetic", "limit", "L-2")}
    assert attrs(x, "L-2") == {"hours": 41}
    cited = {addr(x, i) for v in x.records.entity_versions for i in v.locator_ids}
    assert "Limits!C3" in cited  # the profile cell is evidence of the version
    assert not x.records.extraction_boundaries


def test_issue_25_m08_shape_one_unknown_end() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [LIMITS, ["L-1", 40, None], ["L-2", 41, "unknown"]])
        put(wb, "Bundles", [BUNDLES, ["B-1", "L-2", None]])

    _, x = run(build)
    # (a) the explicit claim is a relationship, typed against the known side's catalogue
    assert edges(x) == {("contains", "B-1", "L-2", None, ("Bundles!A2", "Bundles!B2"))}
    # (b) the unknown entity states itself once, as an entity-level boundary
    assert bounds(x) == {("unknown_profile_entity", ("Limits!A3", "Limits!C3"))}
    # (c) and it is not an unresolved reference
    assert nm_refs(x) == set()
    assert ("unknown", "limit", "L-2") in entities(x)
    assert len(x.records.entity_versions) == 3  # L-2 has its version too


def test_issue_25_two_unknown_shape() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [LIMITS, ["L-2", 41, "unknown"]])
        put(wb, "Bundles", [BUNDLES, ["B-3", "L-2", "unknown"]])

    _, x = run(build)
    assert nm_refs(x) == {("unknown_profile", "B-3", "L-2", "Bundles!B2")}
    assert not x.records.relationships and not x.records.claims
    assert {b[0] for b in bounds(x)} == {"unknown_profile_entity"} and len(bounds(x)) == 2


def test_unknown_holder_known_target() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [LIMITS, ["L-1", 40, None]])
        put(wb, "Bundles", [BUNDLES, ["B-2", "L-1", "unknown"]])

    _, x = run(build)
    assert edges(x) == {("contains", "B-2", "L-1", None, ("Bundles!A2", "Bundles!B2"))}
    assert bounds(x) == {("unknown_profile_entity", ("Bundles!A2", "Bundles!C2"))}
    assert nm_refs(x) == set()


def test_invalid_profile() -> None:
    def build(wb: Workbook) -> None:
        put(wb, "Limits", [LIMITS, ["L-1", 40, "ukg_pro_wfm"]])

    _, x = run(build)
    assert bounds(x) == {("invalid_profile", ("Limits!A2", "Limits!B2", "Limits!C2"))}
    assert not x.records.entities
