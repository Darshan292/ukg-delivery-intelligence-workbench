# Impact propagation semantics

Status: **proposal, awaiting approval (decision D4).** It replaces the earlier instruction to "traverse both directions".

## Why "traverse both directions" was wrong

Reachability is not impact. In an undirected graph almost everything is reachable from a pay rule within a few hops, through shared org units, documents, defects and tests. Reporting every reachable node as impacted produces noise that engineers learn to ignore, which is as dangerous as missing an impact. Traversal must be **directed**, and only along edge types whose propagation rule says a change actually flows that way.

## Four output categories

| Category | What it means | How it is found |
|---|---|---|
| **Impact candidates** | Objects whose behaviour, output or validity may change because of this change | Directed traversal along propagating edges, in their declared direction, from the changed objects. Tiered *established* or *possible* (see `relationship-model.md`) |
| **Upstream constraints and dependencies** | Objects the changed object depends on. They do not change, but they constrain whether the change is valid | One hop against the propagation direction from each **seed** object only. Not recursive, and never counted as impacts |
| **Context** | Related information an engineer should see: source documents, historical defects, notes | Non-propagating edges attached to seeds and impact candidates. Never counted as impacts |
| **Not modelled / unknown boundaries** | Where the analysis cannot see | Edge types with no propagation rule; references to objects outside the graph; entities with `product_profile = unknown`; documents that failed to parse; depth-limit cut-offs; external systems with no modelled consumers |

## Propagation rules per relationship type

Notation: `A —type→ B` is the stored direction. "Change to B ⇒ A" means a change to B makes A an impact candidate.

These types are the **Milestone 1 synthetic catalogue**. They are generic modelling choices for a fictional organisation, **not** documented UKG object semantics. Each real product profile (Pro WFM, WFC) needs its own catalogue, built from evidence (see `ukg-domain-guardrails`).

| Type (stored direction) | Meaning | Change to target ⇒ | Change to source ⇒ | Deletion |
|---|---|---|---|---|
| `uses` (config A uses config B) | A's behaviour depends on B | **A is a candidate** | B is an upstream constraint | Deleting B leaves A with a dangling reference: **candidate, flagged** |
| `contains` (composite A contains part B) | B is a component of A | **A is a candidate** (the composite's behaviour changes) | B: none (a change to A's own attributes does not change B) | Deleting A orphans B: **flag B** |
| `assigned_through` (group A assigns config B) | A applies B to a population | **A is a candidate** (the affected population) | B is an upstream constraint | Dangling: **flag A** |
| `consumes` (integration A consumes config or data B) | A reads B's values or outputs | **A is a candidate** | B is an upstream constraint | Dangling: **flag A** |
| `maps_to` (mapping A maps source S to target T; stored as S —maps_to→ T, carrying a mapping-row id) | A value from S is translated to T in another system | **T and the mapping row are candidates** when S changes | When T changes: S is an upstream constraint, and the mapping row is a candidate | Unmapped S or T: **flag** |
| `implements` (config A implements requirement R) | A exists to satisfy R | Change to R ⇒ **A is a candidate for review** (the requirement changed, so does the configuration still satisfy it?) | Change to A ⇒ **R needs re-validation** (a candidate of kind *re-validate*) | Deleting A ⇒ R is **uncovered** (coverage gap) |
| `verifies` (test T verifies A, a config or requirement) | T checks A | Change to A ⇒ **T is a candidate** (re-run or update) | Change to T ⇒ none (a test change does not change configuration) | Deleting T ⇒ A may be **uncovered** |
| `asserts_value` (test T hard-codes value V of A's attribute; rule basis) | T's expected result embeds a configuration value | Change to that attribute of A ⇒ **T is a candidate, with the stale value highlighted** | none | n/a |
| `documents` / `mentions` (document D mentions A) | Provenance or context | none: **context only** | none | n/a |
| `defect_on` (defect X was raised against A) | Historical risk signal | none: **context only**, shown as "past defects on impacted objects" | none | n/a |
| `same_as` (A is the same object as B) | Identity across sources | Treated as one node **only if accepted**. If unreviewed, a path through it is at most *possible* | same | n/a |
| any type without a rule | n/a | **Not traversed. Reported as an unknown boundary** | same | same |

### Attribute sensitivity
A change seeds propagation when it modifies a **semantic** attribute: anything that affects calculation, assignment, mapping or validity. Changes to display-only attributes (description, display name) are reported but do not propagate. The list of display-only attributes is part of each product profile's catalogue. If an attribute is not catalogued, treat it as semantic and say so.

## Traversal algorithm (deterministic)
1. **Seeds:** changed objects come from a diff of two snapshots (added, removed, modified, with field-level changes). The change set is never typed by hand.
2. **Impact candidates:** breadth-first search from the seeds, following only edges whose rule propagates in the direction of travel, and skipping rejected and superseded edges. Keep the path to every reached node. Detect cycles (a visited set keyed on node id). Depth limit configurable (default 6). A node reached at the limit is reported as a boundary, not silently dropped.
3. **Tier:** a candidate is *established* if at least one path to it consists only of established edges. Otherwise it is *possible*, and the report shows the weakest edge's basis, method and confidence. A candidate reachable both ways is reported once, as established, with its alternative paths listed.
4. **Upstream constraints:** for each seed, one hop against the propagation direction.
5. **Context:** non-propagating edges on seeds and candidates.
6. **Boundaries:** collected throughout. Also list every seed or candidate whose product profile is `unknown`, and every document in scope that failed to parse.
7. **Output:** sorted by stable keys (category, tier, node type, node id, path). The same inputs must produce byte-identical output.

## Worked example (fictional, Milestone 1)

> **FICTIONAL ASSUMPTION:** Harborline Logistics, its objects and this structure are invented for testing. They do not describe how UKG Pro WFM or Workforce Central model overtime. UKG documents "Overtime Rules" as their own API resource group, and the real containment between pay rules, work rules and overtime rules is **unverified**.

Snapshots *before* and *after* differ in one semantic attribute: `OT-WEEKLY.threshold_hours` changes from 40 to 37.5.

| Category | Expected entries (illustrative) |
|---|---|
| Impact candidates, established | `WR-HOURLY` (contains OT-WEEKLY); `PR-STANDARD` (uses WR-HOURLY); `ET-HOURLY` (assigned_through PR-STANDARD); `INT-PAYROLL-01` (consumes WR-HOURLY output); requirement `REQ-012` (implemented by OT-WEEKLY, needs re-validation); test `TC-017` (verifies OT-WEEKLY) |
| Impact candidates, possible | `TC-031` (asserts_value 40, found by a value-match rule, confidence < 1); `INT-PAYROLL-01 → earning code OT1` via a mapping row extracted by rule from the PDF |
| Upstream constraints | the pay period definition OT-WEEKLY uses (it constrains whether a weekly threshold is meaningful) |
| Context | design document §3 (mentions OT-WEEKLY); defect `DEF-004` (past defect on INT-PAYROLL-01) |
| Not modelled | the payroll system's own calculation of OT1 (target system not modelled); requirement `REQ-019` with no linked test (coverage gap); any object with `product_profile = unknown` |

These entries are written into the **hand-authored expected result** (see the Milestone 1 plan), not generated.
