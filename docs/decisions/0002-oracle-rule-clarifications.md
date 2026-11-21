# Decision 0002: oracle rule clarifications

Status: **approved by the owner 2026-11-20 (items 1,2,5,6,7,8-12 as proposed; 3 and 4 as the owner reworded them).** Applied in `docs/architecture/impact-propagation.md` (IP) rev 2.1.

## Rules

1. An accepted conflicted edge stays *established* and is flagged.
2. Depth limit 6: hops 1-6 can be candidates; a node first reachable only at hop 7 is NM.
3. **Two passes.** Pass 1: breadth-first over established edges from established seeds, depth 6: established. Pass 2: all non-excluded edges, all seeds, depth 6: reached and not in pass 1 is possible. A terminal entry is established iff its triggering edge is established and its node X was reached in pass 1 (depth ≤ 5), else possible if X was reached in pass 2. Paths (edge strings `A -type-> B`, stored direction, node keys; IP step 4): shortest at the entry's tier, then up to 3 alternatives by (length, edge strings, UTF-8 byte order); further simple paths counted to 1000, else "1000+". Equals "weakest edge, final edge included; best path" within depth 6. SQL and in-memory results are byte-identical, paths and counts included.
4. **Removed link.** The holder (stored source) is the seed, *before*-state tier. For that link only, "Delete source A" applies, effects on the target; the holder is not deleted; its other edges use "change to". Removed `implements`: RV on the requirement, plus an implementation gap if no other live `implements` remains in `after`. Removed `verifies`: test gap on the target if no other live `verifies` remains in `after`.
5. `asserts_value` fires only from a seed whose field diff contains q, never from an impact candidate.
6. Coverage gaps are evaluated in `after` only.
7. Sort: IC, RV, CG, UC, CX, NM; established first; node type, key, path; UTF-8 byte order.
8. Identity conflict caps every path entering, leaving or crossing the cluster.
9. Attribute conflicts join the IP conflict list.
10. "Explicit basis" = the strongest live present claim is `explicit_source`.
11. A re-validation task can target any object (configuration object, test, requirement, mapping row).
12. Two-hop `maps_to` reach (input → row → target, weaker edge) is decided.

## Worked example

Moved to `docs/architecture/impact-propagation-worked-example.md` (do not read before the oracle is frozen). **Follow-up:** after the oracle is frozen, add a test that checks the oracle and the worked example agree where they overlap.

## Consequences for the oracle author

Mutations touched (scenario section 8 inputs; no outcomes implied):
- Item 2: M09.
- Item 3: all; notably M04, M07, M10, M11, M14.
- Item 4: removed links M01, M02, M03, M19, M26; M05 only if its link differs between snapshots.
- Item 6: M05, M26. Item 9: M13.
- Items 1, 8: none.
- Item 7: all.
