---
name: configuration-change-impact-review
description: Deterministic impact analysis for configuration changes. Use whenever you build, modify, run or explain change-impact logic, snapshot diffs, graph traversal over configuration dependencies, regression-coverage checks, or answer questions like "what breaks if we change this pay rule / pay code / accrual / integration mapping", "is this change safe", or "which tests cover this", including reviews of such code.
---

# Configuration change impact review

Engineers use this to decide whether a change can go to a customer. A missed impact means a payroll or integration incident; a false "safe" is the worst output this product can produce. So the analysis is deterministic, directional, explainable path by path, and honest about what it cannot see.

The full semantics, including the change and deletion rules for every relationship type, are in `docs/architecture/impact-propagation.md` (rev 2). The claim, review and edge-tier model is in `docs/architecture/relationship-model.md` (rev 2). Both are binding (decisions D3 and D4 approved 2026-11-20). Read both before changing traversal code; if this skill and those documents disagree, fix the disagreement.

## Determinism

- Impact is computed by code over the dependency graph, never by an LLM. An LLM may narrate the computed result; it may not add, remove or rank impacts.
- Same snapshots + same graph ⇒ byte-identical result. Sort by stable keys; no time, randomness or dict-order dependence. Test it by running twice and comparing hashes.

## Method

1. **Derive the change set by diffing two snapshots** (entities added, removed or modified with field-level changes, plus links added or removed). Never accept a hand-typed change description as the seed. Attribute values come only from the snapshot's authoritative export. A seed inherits the tier of the link or attribute conflict that created it.
2. **Traverse directionally.** Follow only edge types whose propagation rule carries a change in the direction of travel. Reachability in an undirected graph is not impact. Edge types without a rule are not traversed; they are reported as boundaries. Skip rejected and superseded edges. Detect cycles; enforce a depth limit and report cut-offs.
3. **Sort results into six kinds**, never merged:
   - *Impact candidates*: modelled objects whose behaviour or output may change. Traversal continues only through these.
   - *Re-validation tasks*: work items (re-run a test, update a hard-coded expected value, recheck a requirement or mapping row). They are not impacts, and traversal stops there.
   - *Coverage gaps*: absences, such as an affected requirement or integration with no live test link. They are evaluated only for affected objects, not the whole graph.
   - *Upstream constraints*: one hop against propagation from each seed. They constrain the change; they are not impacted.
   - *Context*: non-propagating links (documents, past defects, documentation mismatches).
   - *Not modelled / boundaries*: unparsed sources, `unknown` profile, untyped edges, dangling references, external systems, depth cut-offs.
4. **Tier every entry:**
   - *Established*: at least one triggering path in which every edge is established, meaning human-accepted, or unreviewed with explicit-source support, no conflict, and not `same_as`. "Established" means documented or accepted, not verified against UKG runtime behaviour.
   - *Possible*: otherwise. Show the weakest edge's basis, method and confidence, and name any conflict.
   Do not use the word "confirmed" for impact tiers; CONFIRMED is a display label for a human-accepted edge, not an impact. Excluded edges (rejected, superseded, unsupported) are never traversed.

## Never say "safe"

Passing tests only prove the behaviour those tests check. Never declare a change safe because existing tests pass or because no impacts were found. The strongest allowed conclusion is "No impact candidates found in the modelled graph", followed by the not-modelled list. Never state pay amounts or pay deltas: rule-engine semantics (evaluation order, rounding, effective dating) cannot be known from documents.

## Report shape

```
Change set (from snapshot diff): <object.attribute: before → after>
Impact candidates — established: <node> via <path>  (evidence refs)
Impact candidates — possible:    <node> via <path>  (weakest edge: <basis>, <method>, confidence <x>; conflict: <kind>)
Re-validation tasks:             <test / requirement / mapping row>: <re-run | update expected value old → new | recheck>  (tier)
Upstream constraints:            <node> (<relationship>)
Context:                         <document / defect> on <node>
Coverage gaps:                   <requirement or integration> has no live test link
Not modelled / boundaries:       <what the analysis could not see, and why>
```

Every line cites the nodes and evidence it rests on. Use synthetic organisations and data, and label fictional configuration structures as fictional assumptions.
