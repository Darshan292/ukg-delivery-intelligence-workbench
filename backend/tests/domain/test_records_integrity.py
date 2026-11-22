# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Each test builds a valid world, then breaks one thing. FICTIONAL: not UKG behaviour."""

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.model import Attribute, Entity, UnresolvedReference
from app.domain.records import Records
from tests.domain.builders import CATALOGUE, World

FIELDS = list(Records.model_fields)


def rich() -> Records:
    w = World()
    s1, s2 = w.snapshot("s1"), w.snapshot("s2")
    e1, w_e2, d = w.export(s1), w.export(s2), w.design()
    w.new_version(d)
    a, b, c = w.entity("cfg", "A"), w.entity("cfg", "B"), w.entity("cfg", "C")
    w.entity("req", "Q")
    ab, ac = w.rel("uses", a, b), w.rel("uses", a, c)
    c1 = w.claim(ab, e1)
    c2 = w.claim(ab, w_e2)
    w.claim(ac, d)
    w.version(a, e1, x=1)
    w.accept(ab, s1)
    w.supersede(ab, s2, ac)
    w.reject_claim(c2)
    w.unresolved_references.append(
        UnresolvedReference(
            id=1,
            holder_entity_id=a.id,
            raw_reference="r",
            locator_id=c1.locator_ids[0],
            reason="missing_target",
        )
    )
    return w.build()


def rebuild(r: Records, **repl: Any) -> Records:
    return Records.model_validate({**{f: getattr(r, f) for f in FIELDS}, **repl})


def grow(r: Records, field: str, *items: Any) -> Records:
    return rebuild(r, **{field: (*getattr(r, field), *items)})


def brk(
    r: Records, field: str, update: dict[str, Any], where: Callable[[Any], bool] = lambda _: True
) -> Records:
    items = list(getattr(r, field))
    i = next(i for i, x in enumerate(items) if where(x))
    items[i] = items[i].model_copy(update=update)
    return rebuild(r, **{field: tuple(items)})


def test_rich_world_is_valid() -> None:
    assert rich()


ID_FIELDS = [f for f in FIELDS if f != "catalogues"]


@pytest.mark.parametrize("field", ID_FIELDS)
def test_records_rejects_duplicate_ids(field: str) -> None:
    r = rich()
    with pytest.raises(ValidationError, match="ids: duplicate"):
        grow(r, field, getattr(r, field)[0])


def test_review_event_ids_shared_across_targets() -> None:
    r = rich()
    claim_ev = next(e for e in r.review_events if e.target_kind == "claim")
    rel_ev = next(e for e in r.review_events if e.target_kind == "relationship")
    with pytest.raises(ValidationError, match="ids: duplicate"):
        grow(r, "review_events", claim_ev.model_copy(update={"id": rel_ev.id}))


DANGLING: list[tuple[str, dict[str, Any], Callable[[Any], bool]]] = [
    ("document_versions", {"document_id": 999}, lambda _: True),
    ("document_versions", {"snapshot_id": 999}, lambda d: d.snapshot_id is not None),
    ("document_versions", {"declared_by": 999}, lambda _: True),
    (
        "document_versions",
        {"supersedes_version_id": 999},
        lambda d: d.supersedes_version_id is None,
    ),
    ("locators", {"document_version_id": 999}, lambda _: True),
    ("entity_versions", {"entity_id": 999}, lambda _: True),
    ("entity_versions", {"document_version_id": 999}, lambda _: True),
    ("entity_versions", {"attributes": (), "locator_ids": (999,)}, lambda _: True),
    (
        "entity_versions",
        {"attributes": (Attribute(name="x", value=1, locator_id=999),), "locator_ids": (999,)},
        lambda _: True,
    ),
    ("relationships", {"source_entity_id": 999}, lambda _: True),
    ("relationships", {"target_entity_id": 999}, lambda _: True),
    ("claims", {"relationship_id": 999}, lambda _: True),
    ("claims", {"locator_ids": (999,)}, lambda _: True),
    ("review_events", {"actor_id": 999}, lambda _: True),
    ("review_events", {"claim_id": 999}, lambda e: e.target_kind == "claim"),
    ("review_events", {"relationship_id": 999}, lambda e: e.target_kind == "relationship"),
    (
        "review_events",
        {"successor_relationship_id": 999},
        lambda e: e.target_kind == "relationship" and e.successor_relationship_id is not None,
    ),
    ("unresolved_references", {"holder_entity_id": 999}, lambda _: True),
    ("unresolved_references", {"locator_id": 999}, lambda _: True),
]


@pytest.mark.parametrize(("field", "update", "where"), DANGLING)
def test_records_rejects_dangling_reference(
    field: str, update: dict[str, Any], where: Callable[[Any], bool]
) -> None:
    with pytest.raises(ValidationError, match="references: dangling"):
        brk(rich(), field, update, where)


def test_records_rejects_duplicate_entity_key_triple() -> None:
    r = rich()
    with pytest.raises(ValidationError, match="uniqueness: entity key"):
        grow(r, "entities", r.entities[0].model_copy(update={"id": 99}))


def test_records_allows_same_natural_key_in_two_types_or_profiles() -> None:
    r = rich()
    a = r.entities[0]
    other = [
        a.model_copy(update={"id": 98, "entity_type": "req"}),
        a.model_copy(update={"id": 99, "product_profile": "unknown"}),
    ]
    assert grow(r, "entities", *other)


def test_records_rejects_duplicate_relationship_key() -> None:
    r = rich()
    assert r.relationships[0].qualifier is None
    with pytest.raises(ValidationError, match="uniqueness: relationship key"):
        grow(r, "relationships", r.relationships[0].model_copy(update={"id": 99}))


def test_records_rejects_duplicate_sha256() -> None:
    r = rich()
    dv = next(d for d in r.document_versions if d.snapshot_id is not None)
    with pytest.raises(ValidationError, match="uniqueness: sha256"):
        grow(r, "document_versions", dv.model_copy(update={"id": 99}))


def test_records_rejects_two_successors_for_one_version() -> None:
    r = rich()
    dv = next(d for d in r.document_versions if d.supersedes_version_id is not None)
    with pytest.raises(ValidationError, match="uniqueness: successor"):
        grow(r, "document_versions", dv.model_copy(update={"id": 99, "sha256": "b" * 64}))


def test_records_rejects_duplicate_entity_version_per_document_version() -> None:
    r = rich()
    ev = r.entity_versions[0]
    with pytest.raises(ValidationError, match="uniqueness: entity version"):
        grow(r, "entity_versions", ev.model_copy(update={"id": 99}))


def test_records_rejects_duplicate_locator_content_key() -> None:
    r = rich()
    with pytest.raises(ValidationError, match="uniqueness: locator content_key"):
        grow(r, "locators", r.locators[0].model_copy(update={"id": 99}))


def test_records_rejects_duplicate_claim_dedup_key() -> None:
    r = rich()
    with pytest.raises(ValidationError, match="uniqueness: claim dedup_key"):
        grow(r, "claims", r.claims[0].model_copy(update={"id": 99}))


def test_records_rejects_uncatalogued_entity_type() -> None:
    r = rich()
    with pytest.raises(ValidationError, match="catalogue: entity type"):
        grow(r, "entities", r.entities[0].model_copy(update={"id": 99, "entity_type": "zzz"}))


def test_unknown_profile_entity_type_not_checked() -> None:
    r = rich()
    e = r.entities[0].model_copy(
        update={"id": 99, "entity_type": "zzz", "product_profile": "unknown"}
    )
    assert grow(r, "entities", e)


def test_records_rejects_uncatalogued_relationship_type() -> None:
    r = rich()
    with pytest.raises(ValidationError, match="catalogue: relationship type"):
        grow(r, "relationships", r.relationships[0].model_copy(update={"id": 99, "type": "zzz"}))


def test_records_rejects_two_catalogues_for_one_profile() -> None:
    with pytest.raises(ValidationError, match="uniqueness: profile"):
        grow(rich(), "catalogues", CATALOGUE)


def test_qualifier_required_iff_catalogue_says_so() -> None:
    r = rich()
    base = r.relationships[0]
    with pytest.raises(ValidationError, match="catalogue: qualifier"):
        grow(r, "relationships", base.model_copy(update={"id": 99, "type": "asserts_value"}))
    with pytest.raises(ValidationError, match="catalogue: qualifier"):
        grow(r, "relationships", base.model_copy(update={"id": 99, "qualifier": "q"}))
    assert grow(
        r,
        "relationships",
        base.model_copy(update={"id": 99, "type": "asserts_value", "qualifier": "q"}),
    )


def test_same_as_requires_same_profile_and_type_and_key_order() -> None:
    r = rich()
    a, b, c = r.entities[:3]
    q = r.entities[3]
    base = r.relationships[0].model_copy(update={"id": 99, "type": "same_as"})
    assert grow(
        r,
        "relationships",
        base.model_copy(update={"source_entity_id": a.id, "target_entity_id": b.id}),
    )
    for src, tgt in ((b, a), (a, q), (c, a)):
        bad = base.model_copy(update={"source_entity_id": src.id, "target_entity_id": tgt.id})
        with pytest.raises(ValidationError, match="same_as"):
            grow(r, "relationships", bad)


def with_other_profile(r: Records) -> Records:
    return grow(r, "catalogues", CATALOGUE.model_copy(update={"product_profile": "ukg_pro_wfm"}))


def test_dv_snapshot_profile_matches_document_profile() -> None:
    r = with_other_profile(rich())
    with pytest.raises(ValidationError, match="profiles: document version"):
        brk(r, "snapshots", {"product_profile": "ukg_pro_wfm"})


def test_entity_version_profile_matches_document() -> None:
    r = with_other_profile(rich())
    e = Entity(id=50, product_profile="ukg_pro_wfm", entity_type="cfg", natural_key="Z")
    ev = r.entity_versions[0].model_copy(update={"id": 50, "entity_id": 50, "attributes": ()})
    with pytest.raises(ValidationError, match="profiles: entity version"):
        grow(grow(r, "entities", e), "entity_versions", ev)
    u = e.model_copy(update={"product_profile": "unknown"})
    assert grow(grow(r, "entities", u), "entity_versions", ev)


def test_relationship_endpoints_share_a_profile_unless_unknown() -> None:
    r = with_other_profile(rich())
    a = r.entities[0]
    other = Entity(id=50, product_profile="ukg_pro_wfm", entity_type="cfg", natural_key="Z")
    unk = Entity(id=51, product_profile="unknown", entity_type="cfg", natural_key="Z")
    base = r.relationships[0].model_copy(update={"id": 99, "source_entity_id": a.id})
    with pytest.raises(ValidationError, match="profiles: relationship"):
        grow(
            grow(r, "entities", other),
            "relationships",
            base.model_copy(update={"target_entity_id": 50}),
        )
    assert grow(
        grow(r, "entities", unk), "relationships", base.model_copy(update={"target_entity_id": 51})
    )
