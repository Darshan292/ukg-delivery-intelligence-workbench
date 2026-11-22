# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Derived state: pure functions of (Records, snapshot id). Nothing here is stored.

Every output is a tuple sorted by a stated key (determinism, decision 0001 test 5).
"""

from typing import Literal

from app.domain.model import (
    BASIS_RANK,
    SAME_AS,
    Basis,
    Claim,
    EntityVersion,
    Id,
    JsonScalar,
    Record,
    RelationshipReviewEvent,
    SortedIds0,
)
from app.domain.records import Records, is_scoped

EffectiveState = Literal["accepted", "rejected", "superseded", "unreviewed", "unsupported"]
Flag = Literal["SUPPORT_LOST", "SUCCESSOR_EXCLUDED"]
DisplayLabel = Literal["CONFIRMED", "OBSERVED", "INFERRED"]


def is_claim_superseded(r: Records, c: Claim) -> bool:
    """Superseded if any of its locators sits in a version that has a successor (RM c)."""
    return any(
        r.locator_by_id[i].document_version_id in r.superseded_version_ids for i in c.locator_ids
    )


def live_claims(r: Records, rel_id: int, s: int) -> tuple[Claim, ...]:
    """Unscoped or scoped to s (decision 0001), not superseded, latest claim event not rejected.

    Sorted by claim id.
    """
    out: list[Claim] = []
    for c in r.claims_by_relationship.get(rel_id, ()):
        if c.scope_snapshot_id not in (None, s) or is_claim_superseded(r, c):
            continue
        events = r.claim_events_by_claim.get(c.id, ())
        if events and events[-1].verdict == "rejected":
            continue
        out.append(c)
    return tuple(out)


def verdict(r: Records, rel_id: int, s: int) -> RelationshipReviewEvent | None:
    """Latest event (at, id) for the relationship in s; unscoped relationships ignore s."""
    scope = s if is_scoped(r, r.relationship_by_id[rel_id]) else None
    events = [
        e
        for e in r.relationship_events_by_relationship.get(rel_id, ())
        if e.scope_snapshot_id == scope
    ]
    return events[-1] if events else None


class EdgeState(Record):
    relationship_id: Id
    state: EffectiveState
    flags: tuple[Flag, ...]
    basis_strength: Basis | None  # strongest live present claim
    live_claim_ids: tuple[Id, ...]
    label: DisplayLabel | None


def edge_state(r: Records, rel_id: int, s: int) -> EdgeState:
    """Effective state of a relationship in snapshot context s (RM derived-state rules 1-3)."""
    rel = r.relationship_by_id[rel_id]
    if r.snapshot_by_id[s].product_profile != r.relationship_profile(rel):
        raise ValueError("edge_state: snapshot profile differs from relationship profile")
    live = live_claims(r, rel_id, s)
    present = [c for c in live if c.polarity == "present"]
    basis: Basis | None = None
    for c in present:
        if basis is None or BASIS_RANK[c.basis] > BASIS_RANK[basis]:
            basis = c.basis
    v = verdict(r, rel_id, s)
    flags: list[Flag] = []
    if v is not None and v.verdict == "superseded":
        state: EffectiveState = "superseded"
        # owner question Q14 (pending): only a rejected or superseded successor, same snapshot
        succ = v.successor_relationship_id
        sv = verdict(r, succ, s) if succ is not None else None
        if sv is not None and sv.verdict in ("rejected", "superseded"):
            flags.append("SUCCESSOR_EXCLUDED")
    elif v is not None and v.verdict == "rejected":
        state = "rejected"
    elif v is not None:
        state = "accepted"
        if not present:
            flags.append("SUPPORT_LOST")
    else:
        state = "unreviewed" if present else "unsupported"
    label: DisplayLabel | None = None
    if state == "accepted":
        label = "CONFIRMED"
    elif state == "unreviewed":
        label = "OBSERVED" if basis == "explicit_source" else "INFERRED"
    return EdgeState(
        relationship_id=rel_id,
        state=state,
        flags=tuple(flags),
        basis_strength=basis,
        live_claim_ids=tuple(c.id for c in live),
        label=label,
    )


ConflictKind = Literal["polarity", "cardinality", "documentary_only", "identity", "attribute"]
_KIND_ORDER: tuple[ConflictKind, ...] = (
    "polarity",
    "cardinality",
    "documentary_only",
    "identity",
    "attribute",
)
_COUNTS: frozenset[EffectiveState] = frozenset({"accepted", "unreviewed"})  # RM BC 16, 19, 25


class Conflict(Record):
    kind: ConflictKind
    snapshot_id: Id
    relationship_ids: SortedIds0 = ()
    claim_ids: SortedIds0 = ()
    entity_ids: SortedIds0 = ()
    entity_version_ids: SortedIds0 = ()
    attribute: str | None = None


def edge_states(r: Records, s: int) -> dict[int, EdgeState]:
    """Every relationship of the snapshot's profile, computed once."""
    profile = r.snapshot_by_id[s].product_profile
    return {
        rel.id: edge_state(r, rel.id, s)
        for rel in r.relationships
        if r.relationship_profile(rel) == profile
    }


def _sort_key(c: Conflict) -> tuple[int, tuple[int, ...], tuple[int, ...], str]:
    return (_KIND_ORDER.index(c.kind), c.relationship_ids, c.entity_ids, c.attribute or "")


def _edge_conflicts(r: Records, s: int, states: dict[int, EdgeState]) -> list[Conflict]:
    out: list[Conflict] = []
    counting = {i: st for i, st in states.items() if st.state in _COUNTS}
    cardinality: dict[tuple[int, str, str], list[int]] = {}
    for rel_id in counting:
        rel = r.relationship_by_id[rel_id]
        live = live_claims(r, rel_id, s)
        # owner question Q12 (pending): accepted edge with only absent claims = polarity
        if any(c.polarity == "absent" for c in live):
            out.append(
                Conflict(
                    kind="polarity",
                    snapshot_id=s,
                    relationship_ids=(rel_id,),
                    claim_ids=tuple(c.id for c in live),
                )
            )
        src = r.entity_by_id[rel.source_entity_id]
        tgt = r.entity_by_id[rel.target_entity_id]
        cat = r.catalogue_by_profile.get(r.snapshot_by_id[s].product_profile)
        spec = (
            next((t for t in cat.relationship_types if t.name == rel.type), None) if cat else None
        )
        if spec and (src.entity_type, tgt.entity_type) in spec.single_valued_for:
            cardinality.setdefault((src.id, rel.type, tgt.entity_type), []).append(rel_id)
        present = [c for c in live if c.polarity == "present"]
        # owner question Q11 (pending): includes accepted edges (flag only, tier unchanged)
        if (
            is_scoped(r, rel)
            and present
            and all(c.scope_snapshot_id is None for c in present)
            and any(c.basis == "explicit_source" for c in present)
            and any(ev.snapshot_id == s for ev in r.entity_versions if ev.entity_id == src.id)
        ):
            out.append(
                Conflict(
                    kind="documentary_only",
                    snapshot_id=s,
                    relationship_ids=(rel_id,),
                    claim_ids=tuple(c.id for c in present),
                )
            )
    for ids in cardinality.values():
        if len(ids) > 1:
            # owner question Q13 (pending): counted on stored edges, not on same_as clusters
            claim_ids = [c.id for i in ids for c in live_claims(r, i, s) if c.polarity == "present"]
            out.append(
                Conflict(
                    kind="cardinality",
                    snapshot_id=s,
                    relationship_ids=tuple(sorted(ids)),
                    claim_ids=tuple(sorted(claim_ids)),
                )
            )
    return out


class Cluster(Record):
    member_ids: tuple[Id, ...]  # ordered by natural key
    representative_id: Id  # smallest key (RM g)
    conflicted: bool


def _cluster_parts(
    r: Records, s: int, states: dict[int, EdgeState]
) -> list[tuple[list[int], list[int]]]:
    """(member ids, same_as relationship ids inside) per cluster of size >= 2, members by key."""
    parent: dict[int, int] = {}

    def find(x: int) -> int:
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    same = [
        r.relationship_by_id[i] for i in sorted(states) if r.relationship_by_id[i].type == SAME_AS
    ]
    for rel in same:
        if states[rel.id].state == "accepted":
            parent[find(rel.source_entity_id)] = find(rel.target_entity_id)
    groups: dict[int, list[int]] = {}
    for e in list(parent):
        groups.setdefault(find(e), []).append(e)
    out: list[tuple[list[int], list[int]]] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda i: r.entity_by_id[i].natural_key)
        inside = [
            rel.id
            for rel in same
            if rel.source_entity_id in members and rel.target_entity_id in members
        ]
        out.append((members, inside))
    return sorted(out, key=lambda t: t[0])


def identity_clusters(
    r: Records, s: int, states: dict[int, EdgeState] | None = None
) -> tuple[Cluster, ...]:
    states = edge_states(r, s) if states is None else states
    return tuple(
        Cluster(
            member_ids=tuple(members),
            representative_id=members[0],
            # owner question Q13 (pending): only a rejected same_as inside a cluster conflicts
            conflicted=any(states[i].state == "rejected" for i in inside),
        )
        for members, inside in _cluster_parts(r, s, states)
    )


def _same_value(a: JsonScalar, b: JsonScalar) -> bool:
    # owner question Q10 (pending): bool never equals a number; 40 == 40.0
    return (type(a) is bool) == (type(b) is bool) and a == b


def _identity_conflicts(r: Records, s: int, states: dict[int, EdgeState]) -> list[Conflict]:
    out: list[Conflict] = []
    for members, inside in _cluster_parts(r, s, states):
        if any(states[i].state == "rejected" for i in inside):
            out.append(
                Conflict(
                    kind="identity",
                    snapshot_id=s,
                    relationship_ids=tuple(sorted(inside)),
                    entity_ids=tuple(sorted(members)),
                )
            )
    return out


def _attribute_conflicts(r: Records, s: int) -> list[Conflict]:
    # owner question Q10 (pending): superseded versions excluded; an attribute in one version
    # only is no conflict; display-only attributes are never conflicts (uncatalogued = semantic)
    profile = r.snapshot_by_id[s].product_profile
    by_entity: dict[int, list[EntityVersion]] = {}
    for ev in r.entity_versions:
        if ev.snapshot_id == s and ev.document_version_id not in r.superseded_version_ids:
            ent = r.entity_by_id[ev.entity_id]
            if ent.product_profile in (profile, "unknown"):
                by_entity.setdefault(ev.entity_id, []).append(ev)
    out: list[Conflict] = []
    for ent_id, evs in by_entity.items():
        spec = r.entity_spec(r.entity_by_id[ent_id])
        display = spec.display_only_attributes if spec else ()
        seen: dict[str, list[tuple[int, JsonScalar]]] = {}
        for ev in evs:
            for a in ev.attributes:
                if a.name not in display:
                    seen.setdefault(a.name, []).append((ev.id, a.value))
        for name, vals in seen.items():
            if len(vals) >= 2 and any(not _same_value(vals[0][1], v) for _, v in vals[1:]):
                out.append(
                    Conflict(
                        kind="attribute",
                        snapshot_id=s,
                        entity_ids=(ent_id,),
                        entity_version_ids=tuple(sorted(i for i, _ in vals)),
                        attribute=name,
                    )
                )
    return out


def conflicts(
    r: Records, s: int, states: dict[int, EdgeState] | None = None
) -> tuple[Conflict, ...]:
    states = edge_states(r, s) if states is None else states
    found = _edge_conflicts(r, s, states) + _identity_conflicts(r, s, states)
    return tuple(sorted(found + _attribute_conflicts(r, s), key=_sort_key))


Tier = Literal["established", "possible", "excluded"]
_EDGE_LEVEL: frozenset[ConflictKind] = frozenset({"polarity", "cardinality", "documentary_only"})


class EdgeView(EdgeState):
    conflict_kinds: tuple[ConflictKind, ...]
    tier: Tier


class Evaluation(Record):
    snapshot_id: Id
    edges: tuple[EdgeView, ...]  # sorted by relationship id
    conflicts: tuple[Conflict, ...]
    clusters: tuple[Cluster, ...]

    def edge(self, rel_id: int) -> EdgeView:
        return next(e for e in self.edges if e.relationship_id == rel_id)


def evaluate(r: Records, s: int) -> Evaluation:
    states = edge_states(r, s)
    found = conflicts(r, s, states)
    views: list[EdgeView] = []
    for rel_id in sorted(states):
        st = states[rel_id]
        kinds = {k for c in found for k in [c.kind] if rel_id in c.relationship_ids}
        # an accepted conflicted edge stays established and is flagged (decision 0002, item 1)
        if st.state == "accepted":
            tier: Tier = "established"
        elif st.state != "unreviewed":
            tier = "excluded"
        elif (
            st.basis_strength == "explicit_source"
            and not kinds & _EDGE_LEVEL
            and r.relationship_by_id[rel_id].type != SAME_AS
        ):
            tier = "established"
        else:
            tier = "possible"
        views.append(
            EdgeView(
                **st.model_dump(),
                conflict_kinds=tuple(k for k in _KIND_ORDER if k in kinds),
                tier=tier,
            )
        )
    return Evaluation(
        snapshot_id=s,
        edges=tuple(views),
        conflicts=found,
        clusters=identity_clusters(r, s, states),
    )
