# Decision 0001: which claims are live in a snapshot

Status: **approved by the owner, 2026-11-20.** Closes the gap found while writing the Milestone 1 scenario. Applies `docs/architecture/relationship-model.md` rev 2 (D3).

## Context

Claims can be tied to a snapshot (they come from an export assigned to that snapshot) or tied to none (they come from a document that belongs to no snapshot, such as a design document or a test inventory).

Rev 2 said that for a scoped relationship the live claims are those scoped to S plus unscoped claims, and that "S is ignored when R is unscoped". That left open how snapshot-scoped claims count on an unscoped relationship. Example: a configuration object that implements a requirement. The requirement belongs to no snapshot, but the claim comes from an export that does.

## Decision

Every analysis runs in a **snapshot context S**. For **any** relationship R, scoped or not:

> live claims of R in S = R's **unscoped** claims + R's claims **scoped to S**

excluding claims that are superseded or whose latest claim event is `rejected`. Claims scoped to another snapshot are kept as history and ignored in S.

**Verdicts are unchanged.** A relationship verdict on a scoped relationship names a snapshot and applies only there. A verdict on an unscoped relationship has no scope and applies in every S.

## Consequences

- A snapshot diff evaluates each relationship twice, in `before` and in `after`. "Present in S" uses the derived effective state in that S.
- An unscoped relationship whose only live claims are scoped to `before` is `unsupported` in `after`, so the diff reports the link as removed. That is intended: the link is not in the later export.
- A human `accepted` verdict on an unscoped relationship holds in every S. If its claims vanish in `after`, it stays `accepted` and is flagged `SUPPORT LOST`, so it is still present and the diff reports no removal.
- No schema change. `Claim.scope_snapshot_id` already exists, and only the derived-state rule changes.

## Tests to add (Slice 1 and Slice 6)

1. A claim scoped to `before` never makes a relationship live in `after`.
2. An unscoped claim is live in both snapshots.
3. An unscoped relationship with claims scoped to both snapshots is live in both.
4. An unscoped relationship with a `before`-only claim reports as removed in the diff, unless a human `accepted` verdict exists.
5. Two runs over the same inputs give identical live-claim sets (determinism).
