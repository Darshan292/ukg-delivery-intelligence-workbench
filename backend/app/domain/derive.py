# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Derived state: pure functions of (Records, snapshot id). Nothing here is stored.

Every output is a tuple sorted by a stated key (determinism, decision 0001 test 5).
"""

from typing import Literal

from app.domain.model import BASIS_RANK, Basis, Claim, Id, Record, RelationshipReviewEvent
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
