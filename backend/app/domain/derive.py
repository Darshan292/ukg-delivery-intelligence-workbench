# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Derived state: pure functions of (Records, snapshot id). Nothing here is stored.

Every output is a tuple sorted by a stated key (determinism, decision 0001 test 5).
"""

from app.domain.model import Claim, RelationshipReviewEvent
from app.domain.records import Records, is_scoped


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
