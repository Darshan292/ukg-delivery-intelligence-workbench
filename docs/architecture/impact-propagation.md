# Impact propagation semantics

Status: **rev 2, approved 2026-11-20 (D4); not yet implemented.** It replaces "traverse both directions". Items marked *Recommendation* are proposals for you to choose.

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
| **Re-validation task** | A **work item** on an artefact (test, requirement, mapping row) that must be re-checked, re-run or updated because something it refers to changed or was deleted. Not an impact: the artefact's own behaviour does not change. Tiered by the path that triggered it | No (terminal) |
| **Coverage gap** | An **absence**: an affected requirement or integration has no live test link, or a requirement has no implementing configuration. Variant: "possible coverage only" when every link is *possible* | No |
| **Upstream constraint** | An object a **seed** depends on. It does not change, but it constrains whether the change is valid. One hop, seeds only | No |
| **Context** | Non-propagating information on seeds and candidates (documents, past defects) | No |
| **Not modelled / boundary** | Where the analysis cannot see: untyped edges, dangling references, external systems, `unknown` profile, unparsed documents, depth cut-offs | No |

The plan's report shape (`docs/plans/milestone-1.md` slice 8 and the `configuration-change-impact-review` skill) gains a **Re-validation tasks** section. Hard-coded old values move from coverage gaps to re-validation tasks. That edit is pending approval of this document.

## Relationship types

> **FICTIONAL CATALOGUE.** Every type, direction and cardinality below is a **Milestone 1 modelling choice** for the synthetic profile. None of it is a documented UKG semantic. Each real profile (Pro WFM, WFC) needs its own evidence-backed catalogue.

**Documented UKG fact (cited, not used by the M1 catalogue).** UKG states that "Employment terms are used to group employees who share a number of pay policies, including pay rule, accrual profile, cascading profile, holiday profile, and timeoff rule". Its sample `employment_terms` response nests `payRule`, `accrualProfile` and `holidayProfile` inside effective-dated `employmentTermVersion`s (`research_notes/UKG delivery intelligence research/verified_ukg_technical.md`, §4). So a real Pro WFM catalogue would probably store the reference on the employment term, pointing at the policy, which matches `assigns` below. Effective dating is **not modelled** in Milestone 1. Pay rule → work rule and pay code → payroll mapping are **unverified**.

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

"Change to X" means X is a seed with a semantic change, or X is an impact candidate. `asserts_value` alone needs the specific attribute to be in the seed's field-level diff.

| Type (A → B) | Change to source A | Change to target B | Delete source A | Delete target B |
|---|---|---|---|---|
| `uses` | B: UC | A: **IC** | — | A: **IC**, plus NM "dangling reference" if A still names B |
| `contains` | — | A: **IC** (the composite changes) | B: **RV** "orphaned part; confirm intended" | A: **IC**, plus NM if dangling |
| `assigns` | B: UC | A: **IC** (affected population) | — | A: **IC**, plus NM if dangling |
| `consumes` | B: UC | A: **IC** | — | A: **IC**, plus NM if dangling |
| `maps_to` (M → T) | T: **IC** (what T receives may change), plus NM if T's system is not modelled | M: **RV** "recheck mapping target" | T: **IC** (loses its feed) | M: **IC**, plus NM dangling |
| `implements` (A → R) | R: **RV** "recheck requirement still met" | A: **RV** "recheck configuration against changed requirement" | R: **CG** if no other live `implements`, and **RV** | A: **RV** "justification removed; confirm still needed" |
| `verifies` (T → X) | — | T: **RV** "re-run" | X: **CG** if no other live `verifies` | T: **RV** "retire or retarget" |
| `asserts_value` (T → A, attribute q) | — | If q changed: T: **RV** "update expected value", showing old and new value; otherwise — | — | T: **RV** "retire or retarget" |
| `mentions` | — | X gains D as **CX** | — | D: **CX** "mentions a deleted object" |
| `defect_on` | — | A gains X as **CX** ("past defects") | — | X: **CX** |
| `same_as` | see below | see below | see below | see below |
| no rule | **NM** (edge not traversed) | **NM** | **NM** | **NM** |

**Edge-change seeds.** An added or removed scoped edge, as found by the snapshot diff of edge presence, is a change to the entity that holds the reference: its stored source. That entity becomes a seed. **A seed inherits the tier of the edge that created it.** A link that appears only through a rule or LLM claim yields a *possible* seed, so everything reached from it is at most *possible*. A seed whose changed attribute carries an attribute conflict (`relationship-model.md` h) is also *possible*.

**Coverage gaps** (rule fixed by the builder check):
- a requirement or integration is a **test gap** when it is in scope (below) and has **zero live `verifies` edges** that are not excluded. If every such edge is *possible*, it is reported as "possible coverage only";
- a requirement is an **implementation gap** only on deletion (the `implements` delete column).

Coverage gaps are evaluated only for:
- every requirement that has a re-validation task,
- every integration that is a seed or an impact candidate,
- deletions, as in the table.

Not for the whole graph.

**Attribute sensitivity.** Only semantic attributes seed propagation. Display-only attributes are listed per profile catalogue; a display-only change is reported but does not propagate. An uncatalogued attribute is treated as semantic, and the report says so.

## Builder-check resolutions (coordinator calls, open to your veto)

| # | Topic | Call |
|---|---|---|
| 45 | **Added entity** | An added entity is a seed treated as "change to E" (every semantic attribute is new). A removed entity is a seed that uses the delete columns. Edges incident to an added or removed entity do not also create edge-change seeds (no double seeding) |
| 4, 8, 11 | Path and entry tier | A path's tier is its weakest edge, **including** the final edge that produced the entry (so an `asserts_value` rule edge makes its re-validation task *possible*). An entry's tier is the best over all its paths |
| 3 | Identity-conflict scope | Every path that enters or leaves a cluster carrying an identity conflict is capped at *possible* |
| 33 | Clusters | An accepted `same_as` cluster is one node: a seed on any member seeds the cluster, and the rules apply to each member's stored edges. Deleting a member is a deletion seed for that member only |
| 34 | Clusters across snapshots | Clusters are computed per snapshot; traversal over both snapshots uses the *after* clusters, falling back to *before* for edges present only in *before* |
| 21, 22 | Removed links | A link present in *before* but excluded or absent in *after* seeds its holder with the *before*-state tier and is traversed through the delete rule |
| 35 | Depth and paths | Depth is counted in hops, a `same_as` hop counts, and the limit is 6. Every entry lists its shortest path plus at most 3 alternative paths (sorted); more are counted, not listed |
| 36, 37 | De-duplication | One entry per (kind, node). Seeds are listed in the change set, never as impact candidates |
| 38 | Upstream constraint tier | The tier of the one edge |
| 40 | External targets | The entity-type flag `external` produces the not-modelled entry. Global caveats (effective dating not modelled) appear once in the report header |
| 26 | Display-only attributes | Catalogued per (profile, entity_type, attribute) |
| 42 | Determinism | Canonical JSON (sorted keys, UTF-8, no insignificant whitespace). Confidences are serialised as decimal strings |

## Tiering, conflicts and `same_as`

The edge tier comes from `relationship-model.md` (derived-state rules):
- **established**: accepted, or unreviewed explicit with no conflict and not `same_as`;
- **possible**: any other unreviewed edge;
- **excluded**: rejected, superseded or unsupported.

An output entry is *established* if at least one triggering path is all established. Otherwise it is *possible*, showing the representative claim of the weakest edge (basis, method, confidence).

- **Conflicts** (polarity, cardinality, documentary-only, identity):
  - An unreviewed conflicted edge is *possible* and is still traversed. Both competing edges are traversed.
  - The report line names the conflict and both claims.
  - An accepted conflicted edge stays *established* and is flagged.
  - Conflicts never remove an entry and never resolve silently.
- **Accepted `same_as`:** the union-find cluster is one traversal node. The report lists every member key and which member each edge was stored on.
- **Unreviewed `same_as`**, of any basis: crossable in both directions, as one hop. It caps the path at *possible* and is shown as "identity unconfirmed".
- **Rejected or superseded `same_as`:** not crossed. It does not appear in the report.
- **Identity conflict** (accepted A~B and B~C, rejected A~C): the cluster is still formed, every path through it is *possible*, and the conflict is listed.
- `same_as` itself never produces an impact candidate. It only joins nodes.

## Traversal algorithm (deterministic)

1. **Seeds** come from diffing two snapshots: entity added, removed or modified (field-level), plus edge presence added or removed (see above). The change set is never typed by hand.
2. **Which edges to use:**
   - The union of edges present in either snapshot.
   - An edge present in *after* uses its *after* state. An edge present only in *before* uses its *before* state; these matter for removals.
   - Unscoped edges have one state.
3. **Breadth-first search** from the seeds:
   - Cross only edges whose rule produces an **IC** in the direction of travel. Record RV, CG, CX and NM entries as they are met; those are terminal.
   - Skip excluded edges.
   - Keep every path, use a visited set on node or cluster id, and apply a depth limit (default 6). A node reached at the limit is reported as NM.
4. **Upstream constraints:** one hop, from seeds only.
5. **Tier** each entry. An entry reachable both ways is reported once, at the stronger tier, with alternative paths listed.
6. **Boundaries:**
   - every seed or candidate with an `unknown` profile;
   - every document in scope that failed to parse;
   - untyped edges;
   - external targets with no modelled behaviour.
7. **Output:** sorted by (kind, tier, node type, node key, path). Identical inputs give byte-identical output.

Never write "safe". The strongest allowed conclusion is "No impact candidates found in the modelled graph", followed by the not-modelled list. Never state pay amounts.

## Open questions on direction (you decide)

| # | Question | Recommendation |
|---|---|---|
| 1 | Keep `assigns` distinct from `uses`? It propagates identically | Keep it: the report labels its candidates "affected population". Drop it if you prefer fewer types |
| 2 | Should a change to a mapping row's input propagate two hops (S → M → T)? | Yes. The T entry is tiered by the weaker of the two edges |
| 3 | Store `implements` as config → requirement, or requirement → config (`satisfied_by`)? | Config → requirement. The configuration workbook holds the reference in the fixtures |
| 4 | Should `verifies` fire for impact candidates, or only for seeds? | Both. A test on WR-HOURLY should be re-run when WR-HOURLY may change |
| 5 | Requirement-document changes as seeds | Deferred. M1 seeds come from configuration snapshots only. The rules for "change to R" are declared but not exercised |
| 6 | `contains`: does a change to the composite affect its parts? | No. Parts do not read the composite. Revisit per real profile |
| 7 | An edge-change seed is the reference holder. Is that always the stored source? | Yes for every M1 type. The catalogue declares `reference_held_by` per type, so a real profile can differ |

## Worked example (fictional, Milestone 1, profile `synthetic`)

> **FICTIONAL ASSUMPTION:** Harborline Logistics, its objects, relationship types and this structure are invented for testing. They do not describe how UKG Pro WFM or Workforce Central model overtime. UKG documents "Overtime Rules" as their own API resource group, and the real containment between pay rules, work rules and overtime rules is **unverified**.

**Snapshots:** `before` and `after`, both in environment `synthetic-dev`. **Diff:** `OT-WEEKLY.threshold_hours` 40 → 37.5. No edge changes.

**Fictional graph (all explicit workbook claims unless stated):**
- `WR-HOURLY —contains→ OT-WEEKLY`
- `OT-WEEKLY —uses→ PP-WEEKLY`
- `PR-STANDARD —uses→ WR-HOURLY`
- `ET-HOURLY —assigns→ PR-STANDARD`
- `INT-PAYROLL-01 —consumes→ WR-HOURLY`
- `INT-PAYROLL-01 —contains→ MR-07`
- `MR-07 —uses→ WR-HOURLY`
- `MR-07 —maps_to→ OT1`: a rule claim from the design PDF table, confidence below 1
- `OT-WEEKLY —implements→ REQ-012`
- `WR-HOURLY —implements→ REQ-019`
- `TC-017 —verifies→ OT-WEEKLY`
- `TC-017 —verifies→ REQ-012`
- `TC-031 —asserts_value[threshold_hours]→ OT-WEEKLY`: a value-match rule
- `DESIGN §3 —mentions→ OT-WEEKLY`
- `DEF-004 —defect_on→ INT-PAYROLL-01`

| Kind | Expected entries (illustrative) |
|---|---|
| Impact candidates, established | `WR-HOURLY` (contains); `PR-STANDARD` (uses WR-HOURLY); `ET-HOURLY` (assigns PR-STANDARD: affected population); `MR-07` (uses WR-HOURLY); `INT-PAYROLL-01` (consumes WR-HOURLY; also contains MR-07) |
| Impact candidates, possible | `OT1` via MR-07 —maps_to→ OT1 (weakest edge: deterministic_rule, PDF table, confidence < 1) |
| Re-validation tasks | `TC-017` re-run (verifies OT-WEEKLY, established); `TC-031` update expected value, 40 hard-coded against new value 37.5 (asserts_value, possible: rule); `REQ-012` recheck (OT-WEEKLY implements, established); `REQ-019` recheck (WR-HOURLY implements, established) |
| Coverage gaps | `REQ-019` has no linked test; `INT-PAYROLL-01` has no linked test |
| Upstream constraints | `PP-WEEKLY` (OT-WEEKLY uses it) |
| Context | design document §3 mentions OT-WEEKLY; `DEF-004`, a past defect on INT-PAYROLL-01 |
| Not modelled | the payroll system's own handling of `OT1` (external target); effective dating; any object with profile `unknown` |

**Mutation illustrating a conflict:**
- Add a design-PDF rule claim "PR-STANDARD uses WR-SALARIED", with `uses` declared `single_valued` for pay rule → work rule in the fictional catalogue.
- Expected: a cardinality conflict on both edges. `PR-STANDARD` and `ET-HOURLY` drop to *possible*, citing the conflict.
- After a human rejects the PDF claim as stale, they return to *established*.

These entries go into the **hand-authored oracle** (Milestone 1 plan, slice 2a). They are not generated.
