---
name: configuration-change-impact-review
description: Deterministic impact analysis for configuration changes. Use whenever you build, modify, run or explain change-impact logic, snapshot diffs, graph traversal over configuration dependencies, regression-coverage checks, or answer questions like "what breaks if we change this pay rule / pay code / accrual / integration mapping", "is this change safe", or "which tests cover this", including reviews of such code.
---

# Configuration change impact review

Engineers use this to decide whether a change can go to a customer. A missed impact means a payroll or integration incident; a false "safe" is the worst output this product can produce. So the analysis is deterministic, directional, explainable path by path, and honest about what it cannot see.

The full semantics, including the propagation rule for every relationship type, are in `docs/architecture/impact-propagation.md`. The edge-status model is in `docs/architecture/relationship-model.md`. Read both before changing traversal code.

## Determinism

- Impact is computed by code over the dependency graph, never by an LLM. An LLM may narrate the computed result; it may not add, remove or rank impacts.
- Same snapshots + same graph ⇒ byte-identical result. Sort by stable keys; no time, randomness or dict-order dependence. Test it by running twice and comparing hashes.

## Method

1. **Derive the change set by diffing two snapshots** (before/after IR: added, removed, modified with field-level changes). Never accept a hand-typed change description as the seed.
2. **Traverse directionally.** Follow only edge types whose propagation rule carries a change in the direction of travel. Reachability in an undirected graph is not impact. Edge types without a rule are not traversed; they are reported as boundaries. Skip rejected and superseded edges. Detect cycles; enforce a depth limit and report cut-offs.
3. **Sort results into four categories**, never merged:
   - *Impact candidates*: may change behaviour, output or validity.
   - *Upstream constraints*: one hop against propagation from each seed. They constrain the change; they are not impacted.
   - *Context*: non-propagating links (documents, past defects).
   - *Not modelled / unknown boundaries*: unparsed sources, unknown product profile, untyped edges, external systems, depth cut-offs.
4. **Tier impact candidates:**
   - *Established*: at least one path made only of established edges (human-accepted, or unreviewed with an explicit source reference). "Established" means documented or accepted, not verified against UKG runtime behaviour.
   - *Possible*: every path contains a rule- or LLM-based unreviewed edge. Show the weakest edge's basis, method and confidence.
   Do not use the word "confirmed" for impact tiers. CONFIRMED/accepted describes a human review of an edge, not an impact.
5. **Check coverage.** Every affected requirement and integration lists its linked tests. No test ⇒ coverage gap. Tests that hard-code the old value are flagged.

## Never say "safe"

Passing tests only prove the behaviour those tests check. Never declare a change safe because existing tests pass or because no impacts were found. The strongest allowed conclusion is "No impact candidates found in the modelled graph", followed by the not-modelled list. Never state pay amounts or pay deltas: rule-engine semantics (evaluation order, rounding, effective dating) cannot be known from documents.

## Report shape

```
Change set (from snapshot diff): <object.attribute: before → after>
Impact candidates — established: <node> via <path>  (evidence refs)
Impact candidates — possible:    <node> via <path>  (weakest edge: <basis>, <method>, confidence <x>)
Upstream constraints:            <node> (<relationship>)
Context:                         <document / defect> on <node>
Coverage gaps:                   <requirement or integration> has no linked test; <test> hard-codes old value
Not modelled / boundaries:       <what the analysis could not see, and why>
```

Every line cites the nodes and evidence it rests on. Use synthetic organisations and data, and label fictional configuration structures as fictional assumptions.
