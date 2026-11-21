# Impact propagation: worked example

> **DO NOT READ BEFORE THE ORACLE IS FROZEN.** This worked example overlaps the Milestone 1 scenario and would make the hand-written oracle less independent. After the oracle is frozen, a test will check that the oracle and this example agree where they overlap.

Moved from `impact-propagation.md` in rev 2.1 (`docs/decisions/0002-oracle-rule-clarifications.md`). Changed for consistency with decision 0002: one re-validation task added (`MR-07` via `OT1`, item 3: a terminal entry may land on a node already on its path), and the closing line no longer calls these entries the oracle.

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
| Re-validation tasks | `TC-017` re-run (verifies OT-WEEKLY, established); `TC-031` update expected value, 40 hard-coded against new value 37.5 (asserts_value, possible: rule); `REQ-012` recheck (OT-WEEKLY implements, established); `REQ-019` recheck (WR-HOURLY implements, established); `MR-07` recheck mapping target (OT1 may change; maps_to, possible: rule) |
| Coverage gaps | `REQ-019` has no linked test; `INT-PAYROLL-01` has no linked test |
| Upstream constraints | `PP-WEEKLY` (OT-WEEKLY uses it) |
| Context | design document §3 mentions OT-WEEKLY; `DEF-004`, a past defect on INT-PAYROLL-01 |
| Not modelled | the payroll system's own handling of `OT1` (external target); effective dating; any object with profile `unknown` |

**Mutation illustrating a conflict:**
- Add a design-PDF rule claim "PR-STANDARD uses WR-SALARIED", with `uses` declared `single_valued` for pay rule → work rule in the fictional catalogue.
- Expected: a cardinality conflict on both edges. `PR-STANDARD` and `ET-HOURLY` drop to *possible*, citing the conflict.
- After a human rejects the PDF claim as stale, they return to *established*.

The hand-authored oracle (Milestone 1 plan, slice 2a) is derived from `tests/oracle/harborline-scenario.md`, not from this example.
