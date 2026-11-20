# Oracle rules cheat sheet (rev 2 docs)

**IP** = `docs/architecture/impact-propagation.md`; **RM** = `docs/architecture/relationship-model.md`; **DR1** = `docs/decisions/0001-snapshot-scoped-claims.md`. "BC n" = row n of that file's "Builder-check resolutions" table. **Never use IP > Worked example: it leaks answers.**

## A. Derivation order (IP > Traversal algorithm (deterministic))
1. **Seeds** from the snapshot diff only: entity added (= "change to E"), removed (delete columns), semantic attribute changed, scoped edge added/removed (IP BC 45).
2. **Edges per snapshot**: union of both; in *after* → *after* state; only in *before* → *before* state.
3. **Traverse** breadth-first, crossing only IC-producing rules.
4. **Tier**. 5. **De-duplicate, sort**.

## B. Edge state and tier (RM > Derived-state rules, incl. bold "Edge tier"; DR1)
- **Live claims of R in S** (DR1, scoped or unscoped R) = unscoped + scoped-to-S claims, not superseded, latest claim event not `rejected`.
- **Verdict** = latest event for (R, S) by `at`, `id`. Scoped R: names S, applies only there. Unscoped R: null scope, applies in every S.
- **Effective state**: verdict rejected/superseded/accepted → same (accepted + no live present claims → flag `SUPPORT LOST`, still accepted). No verdict: no live present claims → `unsupported`, else `unreviewed`.

| Tier | Condition |
|---|---|
| established | accepted; or unreviewed + explicit_source basis + no conflict + not `same_as` |
| possible | every other unreviewed edge |
| excluded | rejected, superseded, unsupported |

## C. Path and entry tier (IP BC 4/8/11, 38, 21/22; IP > Propagation and deletion rules > "Edge-change seeds")
- Path tier = weakest edge, **including the final edge**; the seed's tier counts. Entry tier = best path.
- Seed inherits the tier of the edge that created it (removed link: *before* state). Attribute-conflict seed → possible.
- Conflicts and unreviewed `same_as` cap at possible. UC = tier of its one edge.

## D. Six output kinds (IP > Output kinds)
Rev 2 has **six output kinds**, replacing rev 1's "four categories". Only IC continues traversal; the rest are terminal.

| Kind | Definition |
|---|---|
| IC impact candidate | behaviour or output may change |
| RV re-validation task | artefact to re-check or update |
| CG coverage gap | missing test or implementation link |
| UC upstream constraint | a seed's dependency; one hop, seeds only |
| CX context | documents, past defects, documentation mismatches (RM h) |
| NM not modelled | where analysis cannot see |

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
| asserts_value (T→A, q) | — | T: RV update expected value (old, new), **only if q is in the seed's field diff** | — | T: RV retire/retarget |
| mentions (D→X) | — | X gains D: CX | — | D: CX mentions deleted object |
| defect_on (X→A) | — | A gains X: CX | — | X: CX |
| same_as | joins nodes only (G) | | | |
| no rule / untyped | NM, not traversed | | | |

- "Attribute sensitivity": display-only changes are reported, never propagated; uncatalogued = semantic (say so).
- "Edge-change seeds": an added/removed scoped edge seeds its **stored source**; none for edges touching an added/removed entity (BC 45). A removed link uses the delete rule (BC 21/22).

## F. Coverage gaps (IP > Propagation and deletion rules > "Coverage gaps")
- Evaluate **only** for: requirements with an RV; integrations that are a seed or IC; deletions per table.
- **Test gap**: zero live `verifies` edges that are not excluded. **Possible coverage only**: at least one exists, but all are possible.
- **Implementation gap**: only on deletion (implements, "Delete A" column).

## G. Conflicts and same_as (RM > f. Conflicting claims; RM > g. Entity identity and `same_as`; RM > h. Attribute values and attribute conflicts; IP > Tiering, conflicts and `same_as`)
Conflicted unreviewed edge → possible:
- Polarity: live present and live absent claims on one R.
- Cardinality: `single_valued` type, one source with more than one accepted/unreviewed present edge (RM BC 16/19/25).
- Documentary-only: scoped edge in S backed only by unscoped explicit claims while its source has an EntityVersion in S (RM BC 20).
- Identity: accepted A~B, B~C, rejected A~C → cluster still formed; paths entering, leaving or crossing it → possible (IP BC 3).
- Attribute: two authoritative values in S → "changed with conflict"; seed possible.
- Both sides traversed and named. Accepted conflicted edge stays established, flagged (RM open question 3: record your call).
- Accepted `same_as` cluster = one node; rules apply to each member's stored edges; deleting a member seeds that member only; use *after* clusters, else *before* (IP BC 33, 34). Unreviewed: one hop, both ways, possible, "identity unconfirmed". Rejected/superseded: ignored. Never an IC.

## H. Limits and output (IP > Builder-check resolutions; IP > Traversal algorithm (deterministic))
- Depth limit 6 hops, `same_as` hop counts; node reached at the limit → NM. Shortest path + max 3 sorted alternatives; count the rest (BC 35).
- One entry per (kind, node); seeds never listed as IC (BC 36/37).
- NM: unresolved references (`missing_target`, `uncatalogued_type`; RM BC 24/39), `external` targets (IP BC 40), `unknown` profile, untyped edges, unparsed documents, depth cut-off. Global caveats once, in the header.
- Sort by (kind, tier, node type, node key, path).
- Never write "safe"; never state pay amounts. Strongest allowed conclusion: "No impact candidates found in the modelled graph", then the not-modelled list.

Where the docs are silent or ambiguous, do not guess: write the question down and send it to the engineering team.
