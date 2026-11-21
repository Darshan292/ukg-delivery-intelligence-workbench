# Oracle rules cheat sheet (rev 2.1 docs)

**IP** = `docs/architecture/impact-propagation.md`; **RM** = `docs/architecture/relationship-model.md`; **DR1** = `docs/decisions/0001-snapshot-scoped-claims.md`; **DR2** = `docs/decisions/0002-oracle-rule-clarifications.md`. "BC n" = row n of that file's "Builder-check resolutions" table. **Never open `docs/architecture/impact-propagation-worked-example.md` before the oracle is frozen: it leaks answers.**

## A. Derivation order (IP > Traversal algorithm (deterministic))
1. **Seeds** from the diff only: entity added (= "change to E") or removed (delete columns), semantic attribute changed, edge added/removed, scoped or unscoped (BC 45; DR1).
2. **Edges**: union of both snapshots; in *after* → *after* state, else *before* state. Excluded edges never used.
3. **Pass 1**: breadth-first from established seeds over established IC-producing steps, depth ≤ 6 → established IC. **Pass 2**: all seeds, all non-excluded steps, depth ≤ 6 → other ICs possible (DR2 3).
4. Terminal entries (C), paths, sort (H).

## B. Edge state and tier (RM > Derived-state rules, bold "Edge tier"; DR1)
- **Live claims in S** (any R) = unscoped + scoped-to-S, not superseded, latest claim event not `rejected`. **Verdict** = latest (R, S) event by `at`, `id`; unscoped R: null scope, every S.
- **Effective state** = verdict if any (accepted without live present claims: flag `SUPPORT LOST`); else no live present claims → `unsupported`, else `unreviewed`.
- **Explicit basis** = the strongest live present claim is `explicit_source`.
- **Tier**: established = accepted (conflicted too, flagged: DR2 1), or unreviewed + explicit basis + no conflict + not `same_as`. Possible = other unreviewed. Excluded = rejected, superseded, unsupported.

## C. Seed, path and entry tier (IP BC 4/8/11, 38, 21/22; IP > Traversal algorithm steps 2-3)
- Seed tier: edge-change seed = its edge's tier (removed: *before*); attribute-conflict seed possible; others established.
- Path tier = weakest of seed and edges, **including the final edge**. Entry tier = best path of ≤ 6 hops. The two passes compute exactly this.
- Terminal entry (RV, CG, UC, CX, NM) from X via triggering edge e, hop depth(X)+1: **established** iff e established and X in pass 1 at depth ≤ 5; else **possible** iff X in pass 2 at depth ≤ 5. No own edge: use the X and e that brought it into scope.

## D. Six output kinds (IP > Output kinds)
**IC** behaviour or output may change (only kind that continues). **RV** any object (configuration object, test, requirement, mapping row) to re-check. **CG** missing test or implementation link. **UC** a seed's dependency. **CX** documents, defects, documentation mismatches. **NM** where analysis cannot see.

## E. Rules table (IP > Propagation and deletion rules)
"Change to X" = X is a semantic-change seed or an IC. `*` = plus NM dangling if the holder still names the target.

| Type (A→B) | Change A | Change B | Delete A | Delete B |
|---|---|---|---|---|
| uses | B: UC | A: IC | — | A: IC* |
| contains | — | A: IC | B: RV orphaned part | A: IC* |
| assigns | B: UC | A: IC (affected population) | — | A: IC* |
| consumes | B: UC | A: IC | — | A: IC* |
| maps_to (M→T) | T: IC (+NM if T's system not modelled) | M: RV recheck target | T: IC loses feed | M: IC + NM dangling |
| implements (A→R) | R: RV | A: RV | R: CG if no other live implements, + RV | A: RV justification removed |
| verifies (T→X) | — | T: RV re-run | X: CG if no other live verifies | T: RV retire/retarget |
| asserts_value (T→A, q) | — | T: RV update expected value (old, new), **only if A is a seed whose field diff contains q**; from an IC nothing (DR2 5) | — | T: RV retire/retarget |
| mentions (D→X) | — | X gains D: CX | — | D: CX mentions deleted object |
| defect_on (X→A) | — | A gains X: CX | — | X: CX |
| same_as | joins nodes only (G) | | | |
| no rule / untyped | NM, not traversed | | | |

- Display-only changes: reported, not propagated; uncatalogued = semantic. Edge-change seed = **stored source**; none for edges touching an added/removed entity (BC 45).
- **Removed link** (BC 21/22; DR2 4): holder (stored source) = seed, *before*-state tier. On **that link only**, "Delete A" replaces "Change A", effects on the target; holder not otherwise deleted; its other edges use "change to".
- **Two-hop `maps_to`** (decided, DR2 12): change to M's input → M: IC → T: IC, tiered by the weaker edge.

## F. Coverage gaps (IP > Propagation and deletion rules > "Coverage gaps")
- Evaluated in **`after` only** (DR2 6); live = *after* state accepted or unreviewed.
- Only for: requirements with an RV; integrations that are a seed or IC; "Delete A" of implements/verifies (entity deletion or removed link).
- **Test gap**: zero live `verifies`. **Possible coverage only**: some, all possible. Removed `verifies` link: test gap on the target if no other live `verifies` remains.
- **Implementation gap**: on deletion of the implementing entity **and** on a removed `implements` link, if no other live `implements` remains.

## G. Conflicts and same_as (RM f, g, h; IP > Tiering, conflicts and `same_as`)
- Unreviewed conflicted edge → possible. Polarity: live present and live absent claims on one R. Cardinality: `single_valued` type, one source with more than one accepted/unreviewed present edge (RM BC 16/19/25). Documentary-only: scoped edge in S backed only by unscoped explicit claims, source has an EntityVersion in S (RM BC 20).
- Identity: accepted A~B, B~C, rejected A~C → cluster still formed; paths entering, leaving or crossing it → possible (IP BC 3; DR2 8).
- Attribute: two authoritative values in S → "changed with conflict"; seed possible.
- Both sides traversed and named. Accepted conflicted edge stays established, flagged (DR2 1).
- Accepted `same_as` cluster = one node; rules on each member's stored edges; deleting a member seeds it only; *after* clusters, else *before* (IP BC 33, 34). Unreviewed: one hop, both ways, possible, "identity unconfirmed". Rejected/superseded: ignored. Never an IC.

## H. Limits, paths and output (IP BC 35-40; IP > Traversal algorithm steps 3, 4, 7)
- Depth 6: hops 1-6 give entries; a node first reachable only at hop 7 → one NM "depth cut-off"; nothing beyond (BC 35; DR2 2).
- **Edge string** `A -type-> B`: stored direction, stored keys (`A -asserts_value[q]-> B`). **Path**: edge strings from a seed in travel order, steps then triggering edge, ≤ 6 edges. **Simple**: no repeat among the seed and nodes entered by steps.
- Path set: established entry → established seeds and edges; possible → all seeds and non-excluded edges. Order by length, then edge strings element by element in UTF-8 byte order. List the first, then up to 3 more; count further simple paths up to 1000, else `"1000+"` (DR2 3).
- One entry per (kind, node); seeds never IC (BC 36/37).
- NM: unresolved references (RM BC 24/39), `external` (IP BC 40), `unknown` profile, unparsed documents, depth cut-off. Global caveats once, in the header.
- Sort: kind **IC, RV, CG, UC, CX, NM**; established before possible; node type; node key; path; UTF-8 byte order (DR2 7).
- Never write "safe" or pay amounts. Strongest: "No impact candidates found in the modelled graph", then the NM list.

Where the docs are silent or ambiguous, do not guess: write the question down and send it to the engineering team.
