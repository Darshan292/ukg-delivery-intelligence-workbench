# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Cross-cutting invariants as properties. FICTIONAL: not UKG behaviour."""

import hashlib
from datetime import timedelta
from typing import Any

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.domain.derive import edge_state, evaluate, live_claims, verdict
from app.domain.locators import XlsxCell
from app.domain.model import Claim, DocumentVersion
from app.domain.records import Records
from tests.domain.builders import T0, with_rel_event
from tests.domain.strategies import neutral_extension, worlds

PROPS = settings(max_examples=200, deadline=None)


def reingest(r: Records, data: st.DataObject) -> Records:
    """A new design version (declared by a human) plus fresh explicit claims on it."""
    old = next(
        v
        for v in r.document_versions
        if v.snapshot_id is None and v.id not in r.superseded_version_ids
    )
    reviewer = next(a for a in r.actors if a.is_reviewer)
    dv_id = max(v.id for v in r.document_versions) + 1
    dv = DocumentVersion(
        id=dv_id,
        document_id=old.document_id,
        sha256=hashlib.sha256(f"reingest{dv_id}".encode()).hexdigest(),
        snapshot_id=None,
        supersedes_version_id=old.id,
        declared_by=reviewer.id,
        uploaded_at=T0 + timedelta(days=30),
    )
    locs: list[XlsxCell] = []
    claims: list[Claim] = []
    rels = list(r.relationships)
    chosen = data.draw(st.lists(st.sampled_from(rels), unique_by=lambda x: x.id)) if rels else []
    for rel in chosen:
        lid = max((x.id for x in r.locators), default=0) + len(locs) + 1
        locs.append(
            XlsxCell(
                id=lid,
                document_version_id=dv_id,
                snippet="n",
                extractor="re@1",
                extracted_at=T0 + timedelta(days=30),
                kind="xlsx_cell",
                sheet="RE",
                cell=f"A{lid}",
            )  # fmt: skip
        )
        claims.append(
            Claim(
                id=max((c.id for c in r.claims), default=0) + len(claims) + 1,
                relationship_id=rel.id,
                basis="explicit_source",
                polarity=data.draw(st.sampled_from(["present", "absent"])),
                method="re@1",
                scope_snapshot_id=None,
                locator_ids=(lid,),
                created_at=T0 + timedelta(days=30),
            )  # fmt: skip
        )
    return r.extended(document_versions=(dv,), locators=tuple(locs), claims=tuple(claims))


@PROPS
@given(worlds(), st.data())
def test_reingest_never_changes_any_verdict(r: Records, data: st.DataObject) -> None:
    r2 = reingest(r, data)
    for rel in r.relationships:
        for s in r.snapshots:
            assert verdict(r2, rel.id, s.id) == verdict(r, rel.id, s.id)
            st_ = edge_state(r2, rel.id, s.id)
            if st_.state == "accepted" and not any(
                c.polarity == "present" for c in live_claims(r2, rel.id, s.id)
            ):
                assert "SUPPORT_LOST" in st_.flags


@PROPS
@given(worlds(), st.data())
def test_scoped_verdict_is_isolated_to_its_snapshot(r: Records, data: st.DataObject) -> None:
    scoped = [x for x in r.relationships if x.type != "implements"]
    assume(scoped)
    rel = data.draw(st.sampled_from(scoped))
    s1, s2 = r.snapshots[0], r.snapshots[1]
    r2 = with_rel_event(r, rel.id, data.draw(st.sampled_from(["accepted", "rejected"])), s1.id)
    assert evaluate(r2, s2.id).edges == evaluate(r, s2.id).edges


def _flags(r: Records, s: int) -> set[tuple[str, str, int]]:
    out: set[tuple[str, str, int]] = set()
    for c in evaluate(r, s).conflicts:
        out |= {(c.kind, "relationship", i) for i in c.relationship_ids}
        out |= {(c.kind, "entity", i) for i in c.entity_ids}
    return out


@PROPS
@given(worlds(), st.data())
def test_conflicts_are_monotone_under_neutral_extension(r: Records, data: st.DataObject) -> None:
    r2 = r.extended(**data.draw(neutral_extension(r)))
    for s in r.snapshots:
        assert _flags(r, s.id) <= _flags(r2, s.id)


@PROPS
@given(worlds(), st.data())
def test_evaluation_is_independent_of_record_order(r: Records, data: st.DataObject) -> None:
    shuffled: dict[str, Any] = {}
    for f in Records.model_fields:
        items = list(getattr(r, f))
        shuffled[f] = tuple(items[i] for i in data.draw(st.permutations(range(len(items)))))
    r2 = Records.model_validate(shuffled)
    for s in r.snapshots:
        assert evaluate(r2, s.id) == evaluate(r, s.id)


@PROPS
@given(worlds())
def test_evaluate_twice_is_equal(r: Records) -> None:
    for s in r.snapshots:
        assert evaluate(r, s.id) == evaluate(r, s.id)


@PROPS
@given(worlds())
def test_evaluate_does_not_mutate_records(r: Records) -> None:
    before = r.model_dump_json()
    for s in r.snapshots:
        evaluate(r, s.id)
    assert r.model_dump_json() == before
