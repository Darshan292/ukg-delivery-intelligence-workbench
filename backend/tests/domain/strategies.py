# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Hypothesis strategies over `World`. FICTIONAL: not UKG behaviour."""

from datetime import timedelta
from decimal import Decimal
from itertools import permutations
from typing import Any

from hypothesis import strategies as st

from app.domain.locators import XlsxCell
from app.domain.model import (
    Basis,
    Claim,
    DocumentVersion,
    Entity,
    JsonScalar,
    Polarity,
    Relationship,
    UnresolvedReference,
)
from app.domain.records import Records
from tests.domain.builders import T0, World

CFG_KEYS = ["A", "B", "C", "D"]
BASES: list[Basis] = ["explicit_source", "deterministic_rule", "llm_suggestion"]
POLARITIES: list[Polarity] = ["present", "absent"]
VALUES: list[JsonScalar] = [Decimal(40), Decimal("37.5"), "x", True, None]
Cand = tuple[str, Entity, Entity, str | None]


def _booleans() -> st.SearchStrategy[bool]:
    return st.booleans()


@st.composite
def worlds(draw: st.DrawFn) -> Records:
    w = World()
    w.reviewer()
    w.service()
    s1, s2 = w.snapshot("s1"), w.snapshot("s2")
    exports = [w.export(s1), w.export(s2)]
    design = [w.design()]
    if draw(_booleans()):
        design.append(w.new_version(design[0]))
    if draw(_booleans()):
        exports.append(w.export(s1))  # a second export in S1 enables attribute conflicts
    dvs = [*exports, *design]

    cfg_keys = draw(st.lists(st.sampled_from(CFG_KEYS), min_size=2, max_size=4, unique=True))
    req_keys = draw(st.lists(st.sampled_from(["Q", "R"]), max_size=2, unique=True))
    cfgs = [w.entity("cfg", k) for k in cfg_keys]
    reqs = [w.entity("req", k) for k in req_keys]

    cands: list[Cand] = []
    for a, b in permutations(cfgs, 2):
        cands += [("uses", a, b, None), ("asserts_value", a, b, "q")]
        if a.natural_key < b.natural_key:
            cands.append(("same_as", a, b, None))
    cands += [("implements", a, q, None) for a in cfgs for q in reqs]
    picked = draw(st.lists(st.sampled_from(cands), max_size=5, unique=True))
    # scenarios that make cardinality and identity conflicts reachable
    card: list[Cand] = []
    if len(cfgs) >= 3 and draw(_booleans()):
        card = [("uses", cfgs[0], cfgs[1], None), ("uses", cfgs[0], cfgs[2], None)]
    tri: list[Cand] = []
    if len(cfgs) >= 3 and draw(_booleans()):
        x, y, z = sorted(cfgs[:3], key=lambda e: e.natural_key)
        tri = [("same_as", x, y, None), ("same_as", y, z, None), ("same_as", x, z, None)]
    picked += [c for c in card + tri if c not in picked]
    rels = [w.rel(t, a, b, q) for t, a, b, q in picked]
    by_key = {(t, a.id, b.id): rel for (t, a, b, _q), rel in zip(picked, rels, strict=True)}

    claims: list[Claim] = []
    for rel in rels:
        for _ in range(draw(st.integers(0, 3))):
            basis = draw(st.sampled_from(BASES))
            conf = Decimal(draw(st.sampled_from(["0", "0.5", "1"])))
            claims.append(
                w.claim(
                    rel, draw(st.sampled_from(dvs)), basis, draw(st.sampled_from(POLARITIES)), conf
                )
            )

    for t, a, b, _q in card:
        claims.append(w.claim(by_key[(t, a.id, b.id)], draw(st.sampled_from(dvs))))

    for e in cfgs:
        for dv in exports:
            # at most one per (entity, export): the store is unique on (entity, document version)
            if draw(_booleans()):
                w.version(e, dv, q=draw(st.sampled_from(VALUES)))

    def scope_of(rel: Relationship) -> Any:
        return None if rel.type == "implements" else draw(st.sampled_from([s1, s2]))

    for _ in range(draw(st.integers(0, 6))):
        kinds = ["accept", "reject", "supersede"] + (["claim", "reinstate"] if claims else [])
        kind = draw(st.sampled_from(kinds)) if rels else None
        if kind in ("claim", "reinstate"):
            c = draw(st.sampled_from(claims))
            (w.reject_claim if kind == "claim" else w.reinstate_claim)(c)
        elif kind is not None:
            rel = draw(st.sampled_from(rels))
            scope = scope_of(rel)
            sibs = [
                x for x in rels if x.source_entity_id == rel.source_entity_id and x.id != rel.id
            ]
            if kind == "accept":
                w.accept(rel, scope)
            elif kind == "supersede" and sibs:
                w.supersede(rel, scope, draw(st.sampled_from(sibs)))
            else:
                w.reject(rel, scope)
    if tri:
        scope = draw(st.sampled_from([s1, s2]))
        xy, yz, xz = (by_key[(t, a.id, b.id)] for t, a, b, _q in tri)
        w.accept(xy, scope)
        w.accept(yz, scope)
        w.reject(xz, scope)
    return w.build()


@st.composite
def neutral_extension(draw: st.DrawFn, r: Records) -> dict[str, tuple[object, ...]]:
    """Only new entities, new relationships between them with their own claims, and references."""
    nid = {
        "entity": max((e.id for e in r.entities), default=0),
        "relationship": max((x.id for x in r.relationships), default=0),
        "claim": max((c.id for c in r.claims), default=0),
        "locator": max((x.id for x in r.locators), default=0),
        "ref": max((u.id for u in r.unresolved_references), default=0),
    }

    def nxt(k: str) -> int:
        nid[k] += 1
        return nid[k]

    t = T0 + timedelta(days=1)
    ents = [
        Entity(id=nxt("entity"), product_profile="synthetic", entity_type="cfg", natural_key=k)
        for k in ("N1", "N2")
    ]
    locs: list[XlsxCell] = []
    rels: list[Relationship] = []
    claims: list[Claim] = []
    dvs: list[DocumentVersion] = list(r.document_versions)

    def new_locator() -> XlsxCell:
        n = nxt("locator")
        dv = draw(st.sampled_from(dvs))
        loc = XlsxCell(
            id=n, document_version_id=dv.id, snippet="x", extractor="ext@1", extracted_at=t,
            kind="xlsx_cell", sheet="EXT", cell=f"A{n}",
        )  # fmt: skip
        locs.append(loc)
        return loc

    if draw(_booleans()):
        rel = Relationship(
            id=nxt("relationship"), type="uses", source_entity_id=ents[0].id,
            target_entity_id=ents[1].id, qualifier=None, created_at=t,
        )  # fmt: skip
        rels.append(rel)
        for _ in range(draw(st.integers(1, 2))):
            loc = new_locator()
            basis = draw(st.sampled_from(BASES))
            dv = next(d for d in dvs if d.id == loc.document_version_id)
            claims.append(
                Claim(
                    id=nxt("claim"),
                    relationship_id=rel.id,
                    basis=basis,
                    polarity=draw(st.sampled_from(POLARITIES)),
                    method=f"{basis}-ext@1",
                    confidence=None if basis == "explicit_source" else Decimal("0.5"),
                    model_id="m" if basis == "llm_suggestion" else None,
                    prompt_version="p1" if basis == "llm_suggestion" else None,
                    scope_snapshot_id=dv.snapshot_id,
                    locator_ids=(loc.id,),
                    created_at=t,
                )  # fmt: skip
            )
    refs: list[UnresolvedReference] = []
    if draw(_booleans()):
        refs.append(
            UnresolvedReference(
                id=nxt("ref"),
                holder_entity_id=ents[0].id,
                raw_reference="r",
                locator_id=new_locator().id,
                reason="missing_target",
            )  # fmt: skip
        )
    return {
        "entities": tuple(ents),
        "locators": tuple(locs),
        "relationships": tuple(rels),
        "claims": tuple(claims),
        "unresolved_references": tuple(refs),
    }
