# Impact propagation semantics

Status: **rev 2.1 (2026-11-20), see decision 0002** (`docs/decisions/0002-oracle-rule-clarifications.md`). Rev 2 approved 2026-11-20 (D4); not yet implemented. It replaces "traverse both directions". Items marked *Recommendation* are proposals for you to choose.

## Changes in rev 2.1 (decision 0002)

- Two-pass traversal replaces the rev 2 rule of path keeping with a node-visited check; path lists, counts and the depth cut-off are defined exactly (Traversal algorithm).
- A removed link applies the "Delete source A" column to that link only; its holder is the seed.
- Coverage gaps are evaluated in `after` only; a removed `implements` or `verifies` link can raise one.
- `asserts_value` fires only from a seed; the sort order, the identity-conflict scope and the "explicit basis" definition are fixed; two-hop `maps_to` reach is decided.
- The worked example moved to `docs/architecture/impact-propagation-worked-example.md` (do not read it before the oracle is frozen).

## Changes from rev 1

- Impact candidates, **re-validation tasks** and **coverage gaps** are now separate output kinds. Rev 1 mixed them (for example, "REQ-012 is a candidate", and "REQ-019 has no test" was filed under not modelled).
- One table declares, for every type: change to source, change to target, deletion of source, deletion of target, and the output kind each produces.
- `assigned_through` is renamed `assigns`, and its direction is fixed.
- `maps_to` has one stored direction: mapping row → target. The mapping row is an entity, not an edge attribute.
- `same_as`, conflicts and edge tiers now follow `relationship-model.md` rev 2. Traversal uses both snapshots' edges, as defined below.
- Ambiguous directions are listed as open questions.

## Why directed

Reachability is not impact. Undirected, almost everything is reachable from a pay rule within a few hops, through shared org units, documents and tests. Reporting all of it trains engineers to ignore the report. Traversal follows only edge types whose rule says a change flows that way, in that direction.

## Output kinds

| Kind | Definition | Does traversal continue through it? |
|---|---|---|
| **Impact candidate** | A modelled object whose **behaviour or output may change** because of the change set. Tiered *established* or *possible* | Yes |
| **Re-validation task** | A **work item** on any object (configuration object, test, requirement, mapping row) that must be re-checked, re-run or updated because something it refers to changed or was deleted. Not an impact: the task is to re-check the object, not a claim that its behaviour changes. Tiered by the path that triggered it | No (terminal) |
| **Coverage gap** | An **absence**: an affected requirement or integration has no live test link, or a requirement has no implementing configuration. Variant: "possible coverage only" when every link is *possible* | No |
| **Upstream constraint** | An object a **seed** depends on. It does not change, but it constrains whether the change is valid. One hop, seeds only | No |
| **Context** | Non-propagating information on seeds and candidates (documents, past defects) | No |
| **Not modelled / boundary** | Where the analysis cannot see: untyped edges, dangling references, external systems, `unknown` profile, unparsed documents, depth cut-offs | No |

The plan's report shape (`docs/plans/milestone-1.md` slice 8 and the `configuration-change-impact-review` skill) gains a **Re-validation tasks** section. Hard-coded old values move from coverage gaps to re-validation tasks. That edit is pending approval of this document.

## Relationship types

> **FICTIONAL CATALOGUE.** Every type, direction and cardinality below is a **Milestone 1 modelling choice** for the synthetic profile. None of it is a documented UKG semantic. Each real profile (Pro WFM, WFC) needs its own evidence-backed catalogue.

**Documented UKG fact (cited, not used by the M1 catalogue).** UKG states that "Employment terms are used to group employees who share a number of pay policies, including pay rule, accrual profile, cascading profile, holiday profile, and timeoff rule". Its sample `employment_terms` response nests `payRule`, `accrualProfile` and `holidayProfile` inside effective-dated `employmentTermVersion`s (`docs/research/notes/verified_ukg_technical.md`, §4). So a real Pro WFM catalogue would probably store the reference on the employment term, pointing at the policy, which matches `assigns` below. Effective dating is **not modelled** in Milestone 1. Pay rule → work rule and pay code → payroll mapping are **unverified**.

Semantics (`A —type→ B` is the stored direction; the stored source is the entity whose record holds the reference):

- `uses`: A's behaviour depends on B.
- `contains`: B is a part of composite A.
- `assigns`: group A applies policy B to a population. Rev 1's `assigned_through` read backwards ("employment term assigned through pay rule").
- `consumes`: integration A reads B's values or outputs.
- `maps_to`: mapping row M sends a translated value to target T in another system. The row's **input** is an ordinary `M —uses→ S`, and the integration owns its rows through `I —contains→ M`. A row is a snapshot-scoped entity with its own attributes and evidence (the MappingRows sheet), so its changes are diffable.
- `implements`: configuration A exists to satisfy requirement R (A → R).
- `verifies`: test T checks X, which is a configuration object, a requirement or an integration.
- `asserts_value`: test T's expected result embeds the value of attribute `qualifier` of A. Found by a value-match rule.
- `mentions`: document D mentions X.
- `defect_on`: defect X was raised against A.
- `same_as`: identity. Stored once, with the smaller key as source.

## Propagation and deletion rules

Notation:
- **IC** impact candidate
- **RV** re-validation task
- **CG** coverage gap
- **UC** upstream constraint (only when the source is a seed)
- **CX** context
- **NM** not modelled or boundary
- **—** nothing

"Change to X" means X is a seed with a semantic change, or X is an impact candidate. `asserts_value` is the exception: it fires only when X is a **seed** whose field-level diff contains the attribute q. An `asserts_value` edge on an impact candidate (not a seed) produces nothing (decision 0002, item 5).

| Type (A → B) | Change to source A | Change to target B | Delete source A | Delete target B |
|---|---|---|---|---|
| `uses` | B: UC | A: **IC** | — | A: **IC**, plus NM "dangling reference" if A still names B |
| `contains` | — | A: **IC** (the composite changes) | B: **RV** "orphaned part; confirm intended" | A: **IC**, plus NM if dangling |
| `assigns` | B: UC | A: **IC** (affected population) | — | A: **IC**, plus NM if dangling |
| `consumes` | B: UC | A: **IC** | — | A: **IC**, plus NM if dangling |
| `maps_to` (M → T) | T: **IC** (what T receives may change), plus NM if T's system is not modelled | M: **RV** "recheck mapping target" | T: **IC** (loses its feed) | M: **IC**, plus NM dangling |
| `implements` (A → R) | R: **RV** "recheck requirement still met" | A: **RV** "recheck configuration against changed requirement" | R: **CG** if no other live `implements`, and **RV** | A: **RV** "justification removed; confirm still needed" |
| `verifies` (T → X) | — | T: **RV** "re-run" | X: **CG** if no other live `verifies` | T: **RV** "retire or retarget" |
| `asserts_value` (T → A, attribute q) | — | Only if A is a seed whose field diff contains q: T: **RV** "update expected value", showing old and new value; otherwise — | — | T: **RV** "retire or retarget" |
| `mentions` | — | X gains D as **CX** | — | D: **CX** "mentions a deleted object" |
| `defect_on` | — | A gains X as **CX** ("past defects") | — | X: **CX** |
| `same_as` | see below | see below | see below | see below |
| no rule | **NM** (edge not traversed) | **NM** | **NM** | **NM** |

**Two-hop `maps_to` reach (decided, decision 0002 item 12).** A change to S, the input of mapping row M (`M —uses→ S`), makes M an impact candidate, and M's change then makes the target T an impact candidate: S → M → T over two hops. T's entry is tiered by the weaker of the two edges (and the rest of its path, as for any entry).

**Edge-change seeds.** An added or removed edge, scoped or unscoped (decision 0001: the diff evaluates every relationship in `before` and in `after`), as found by the snapshot diff of edge presence, is a change to the entity that holds the reference: its stored source. That entity becomes a seed. **A seed inherits the tier of the edge that created it.** A link that appears only through a rule or LLM claim yields a *possible* seed, so everything reached from it is at most *possible*. A seed whose changed attribute carries an attribute conflict (`relationship-model.md` h) is also *possible*.

**Removed links (decision 0002, item 4).** For a link A → B present in *before* but excluded or absent in *after*:
- The **holder** A (stored source) is the seed, with the removed edge's *before*-state tier.
- For **that one link only**, the "Delete source A" column applies, and its effects land on the **target** B. A is not otherwise treated as deleted: on that link the "Delete source A" column replaces "Change to source A", and none of A's other edges use a delete column.
- All of A's other edges use A's "change to" columns, as for any seed.
- So a removed `implements` link gives R an **RV** and, if no other live `implements` edge to R remains in *after*, an implementation gap. A removed `verifies` link gives X a test gap if no other live `verifies` edge to X remains in *after*. A removed `maps_to` link makes T an impact candidate ("loses its feed").

**Coverage gaps** (decision 0002, items 4 and 6). Every check is evaluated in the **`after` snapshot only**: "live" means an edge whose *after* effective state is `accepted` or `unreviewed`.
- **Test gap:** a requirement or integration in scope (below) with **zero live `verifies` edges**. If at least one exists and every one is *possible*, it is reported as "possible coverage only".
- **Implementation gap:** a requirement R with no other live `implements` edge, raised only by the "Delete source A" column of `implements`: on deletion of the implementing entity, **and** on a removed `implements` link.

Coverage gaps are evaluated only for:
- every requirement that has a re-validation task,
- every integration that is a seed or an impact candidate,
- the "Delete source A" column of `implements` and `verifies` (entity deletion or removed link).

Not for the whole graph.

**Attribute sensitivity.** Only semantic attributes seed propagation. Display-only attributes are listed per profile catalogue; a display-only change is reported but does not propagate. An uncatalogued attribute is treated as semantic, and the report says so.

## Builder-check resolutions (coordinator calls, open to your veto)

| # | Topic | Call |
|---|---|---|
| 45 | **Added entity** | An added entity is a seed treated as "change to E" (every semantic attribute is new). A removed entity is a seed that uses the delete columns. Edges incident to an added or removed entity do not also create edge-change seeds (no double seeding) |
| 4, 8, 11 | Path and entry tier | A path's tier is its weakest edge, **including** the final edge that produced the entry (so an `asserts_value` rule edge makes its re-validation task *possible*), and the tier of the seed it starts from. An entry's tier is the best over all its paths of at most 6 hops. The two-pass traversal computes exactly this (Traversal algorithm, "Equivalence") |
| 3 | Identity-conflict scope | Every path **entering, leaving or crossing** a cluster that carries an identity conflict is capped at *possible* (decision 0002, item 8) |
| 33 | Clusters | An accepted `same_as` cluster is one node: a seed on any member seeds the cluster, and the rules apply to each member's stored edges. Deleting a member is a deletion seed for that member only |
| 34 | Clusters across snapshots | Clusters are computed per snapshot; traversal over both snapshots uses the *after* clusters, falling back to *before* for edges present only in *before* |
| 21, 22 | Removed links | A link present in *before* but excluded or absent in *after* seeds its holder (stored source) with the *before*-state tier. For that one link only, the "Delete source A" column applies, with its effects on the target; the holder's other edges use its "change to" columns (Propagation and deletion rules, "Removed links"; decision 0002, item 4) |
| 35 | Depth and paths | Depth is counted in hops, an unreviewed `same_as` hop counts, and the limit is 6: hops 1 to 6 can produce entries; a node first reachable only at hop 7 is reported as NM "depth cut-off". Paths are listed and counted as in Traversal algorithm step 4 (decision 0002, items 2 and 3) |
| 36, 37 | De-duplication | One entry per (kind, node). Seeds are listed in the change set, never as impact candidates |
| 38 | Upstream constraint tier | The tier of the one edge, and *possible* if the seed was not reached in pass 1 (the general rule in Traversal algorithm step 3; decision 0002, item 3) |
| 40 | External targets | The entity-type flag `external` produces the not-modelled entry. Global caveats (effective dating not modelled) appear once in the report header |
| 26 | Display-only attributes | Catalogued per (profile, entity_type, attribute) |
| 42 | Determinism | Canonical JSON (sorted keys, UTF-8, no insignificant whitespace). Confidences are serialised as decimal strings |

## Tiering, conflicts and `same_as`

The edge tier comes from `relationship-model.md` (derived-state rules):
- **established**: accepted, or unreviewed with an **explicit basis** (the strongest live present claim is `explicit_source`), no conflict and not `same_as`;
- **possible**: any other unreviewed edge;
- **excluded**: rejected, superseded or unsupported.

An output entry is *established* if at least one triggering path (of at most 6 hops, starting at an established seed) is all established. Otherwise it is *possible*, showing the representative claim of the weakest edge (basis, method, confidence).

- **Conflicts** (polarity, cardinality, documentary-only, identity, attribute):
  - An unreviewed conflicted edge is *possible* and is still traversed. Both competing edges are traversed.
  - An attribute conflict (`relationship-model.md` h) makes its seed *possible*.
  - The report line names the conflict and both claims (for an attribute conflict, every value and its locator).
  - An accepted conflicted edge stays *established* and is flagged (decision 0002, item 1).
  - Conflicts never remove an entry and never resolve silently.
- **Accepted `same_as`:** the union-find cluster is one traversal node. The report lists every member key and which member each edge was stored on.
- **Unreviewed `same_as`**, of any basis: crossable in both directions, as one hop. It caps the path at *possible* and is shown as "identity unconfirmed".
- **Rejected or superseded `same_as`:** not crossed. It does not appear in the report.
- **Identity conflict** (accepted A~B and B~C, rejected A~C): the cluster is still formed, every path entering, leaving or crossing it is *possible*, and the conflict is listed.
- `same_as` itself never produces an impact candidate. It only joins nodes.

## Traversal algorithm (deterministic)

1. **Seeds** come from diffing two snapshots: entity added, removed or modified (field-level), plus edge presence added or removed (see above). The change set is never typed by hand.
2. **Which edges to use:**
   - The union of edges present in either snapshot.
   - An edge present in *after* uses its *after* state. An edge present only in *before* uses its *before* state; these matter for removals.
   - Unscoped edges have one state (in context S, per decision 0001).
   - Excluded edges are never used.
   - **Traversal tier of an edge** = its edge tier, except that an edge with an endpoint in a cluster carrying an identity conflict counts as *possible*. This is exactly "every path entering, leaving or crossing that cluster is possible".
   - **Seed tier:** an edge-change seed has the tier of its edge (removed link: *before* state); a seed whose changed attribute has an attribute conflict is *possible*; every other seed is *established*.
3. **Two passes** (decision 0002, item 3). A **step** goes from node X to node Y across a non-excluded edge whose rule, given the change to X (its "change to" column, or its delete column for a deleted entity or a removed link), makes Y an **IC**. An accepted `same_as` cluster is one node; an unreviewed `same_as` edge is a step in both directions. Seeds are at depth 0.
   - **Pass 1:** breadth-first search from the *established* seeds over *established* steps only, to depth 6. Every non-seed node reached is an **established IC**. depth₁(X) = X's depth in pass 1.
   - **Pass 2:** breadth-first search from **all** seeds over **all** steps (all non-excluded edges), to depth 6. Every non-seed node reached and not reached in pass 1 is a **possible IC**. depth₂(X) = X's depth in pass 2.
   - **Terminal entries** (RV, CG, UC, CX, NM). Each comes from a node X that is a seed or IC and a **triggering edge** e (the table cell that produced it), at hop depth(X) + 1. The entry is **established** iff, for some such (X, e), e is established and X was reached in pass 1 with depth₁(X) ≤ 5; otherwise it is **possible** iff, for some (X, e), depth₂(X) ≤ 5. A UC always hangs off a seed (depth 0). An entry with no edge of its own takes the X and e of the entry that brought it into scope: a test gap on a requirement takes those of the requirement's RV; a coverage gap or `unknown`-profile NM on a seed or IC takes that node's tier. An NM entry tied to no seed or IC (an unparsed document) has no tier; its position within NM is **open** (not settled by decision 0002).
   - **Depth cut-off:** a node Y that is not a seed and has no entry at hop 1 to 6, but is reached by a step or a terminal rule from some X with depth₂(X) = 6, gets **one** NM "depth cut-off" entry, tiered by the same rule with hop 7 allowed (established iff e is established and depth₁(X) = 6). Nothing beyond hop 7 is examined.
   - **Equivalence.** Within depth 6 this equals BC 4/8/11 ("path tier = weakest edge including the final edge, and the seed's tier; entry tier = best over paths"). If an all-established path of at most 6 hops from an established seed exists, every node on it is reached in pass 1 no deeper than its position, so the passes say *established*. Conversely, pass 1's breadth-first predecessor chain to X, plus e, is such a path, and it is simple. The same argument over all non-excluded edges and all seeds gives *possible* for the rest.
4. **Paths** for each entry, drawn from the edge set of the entry's tier: *established* entries use only established seeds and established edges (the triggering edge included); *possible* entries use all seeds and all non-excluded edges.
   - An **edge string** is `A -type-> B` in the **stored** direction with the stored endpoints' natural keys, whatever the direction of travel; `asserts_value` is `A -asserts_value[q]-> B`; `same_as` is stored smaller key first. A **path** is the list of edge strings from a seed, in travel order: its steps, then (for a terminal entry) the triggering edge. Length = number of edges, at most 6.
   - A path is **simple** if no node (a cluster counts as one node) repeats among the seed and the nodes entered by its steps. The far end of a terminal entry's triggering edge is not checked, so a terminal entry may land on a node already on its path.
   - **Order:** by length, then by the sequence of edge strings compared element by element in UTF-8 byte order.
   - **List** the first path in this order (the shortest path at the entry's tier), then up to 3 alternatives, the next in order.
   - **Count** the further simple paths in the same set up to 1000 (`extra_paths_count`); above 1000, report the string `"1000+"`.
   - The SQL and in-memory implementations must produce **byte-identical** results, including path lists and counts (differential check).
5. **Upstream constraints:** one hop, from seeds only; tiered as in step 3. Each lists its one edge.
6. **Boundaries:**
   - every seed or candidate with an `unknown` profile;
   - every document in scope that failed to parse;
   - untyped edges;
   - external targets with no modelled behaviour;
   - depth cut-offs (step 3).
7. **Output:** one entry per (kind, node). Sorted by kind in the order **IC, RV, CG, UC, CX, NM**; within a kind, *established* before *possible*; then node type, then node key, then path (the first listed path, ordered as in step 4). All strings compare in UTF-8 byte order. Identical inputs give byte-identical output.

Never write "safe". The strongest allowed conclusion is "No impact candidates found in the modelled graph", followed by the not-modelled list. Never state pay amounts.

## Open questions on direction (you decide)

| # | Question | Recommendation |
|---|---|---|
| 1 | Keep `assigns` distinct from `uses`? It propagates identically | Keep it: the report labels its candidates "affected population". Drop it if you prefer fewer types |
| 2 | Should a change to a mapping row's input propagate two hops (S → M → T)? | **Decided (decision 0002, item 12):** yes. The T entry is tiered by the weaker of the two edges |
| 3 | Store `implements` as config → requirement, or requirement → config (`satisfied_by`)? | Config → requirement. The configuration workbook holds the reference in the fixtures |
| 4 | Should `verifies` fire for impact candidates, or only for seeds? | Both. A test on WR-HOURLY should be re-run when WR-HOURLY may change |
| 5 | Requirement-document changes as seeds | Deferred. M1 seeds come from configuration snapshots only. The rules for "change to R" are declared but not exercised |
| 6 | `contains`: does a change to the composite affect its parts? | No. Parts do not read the composite. Revisit per real profile |
| 7 | An edge-change seed is the reference holder. Is that always the stored source? | Yes for every M1 type. The catalogue declares `reference_held_by` per type, so a real profile can differ |

## Worked example

**DO NOT READ BEFORE THE ORACLE IS FROZEN.** The worked example is in `docs/architecture/impact-propagation-worked-example.md`. It overlaps the Milestone 1 scenario and would make the hand-written oracle less independent; after the oracle is frozen, a test will check that the oracle and the example agree where they overlap.
