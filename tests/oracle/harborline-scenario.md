# Harborline Logistics: Milestone 1 synthetic scenario (version 1)

> **FICTIONAL. NOT UKG BEHAVIOUR.**
> Harborline Logistics is an invented company. Every object, key, attribute, value, document and relationship below is invented for testing. Product profile: **`synthetic`** (never `ukg_pro_wfm` or `workforce_central`).
> The structures (an overtime rule contained in a work rule, used by a pay rule, assigned by an employment term) and the relationship catalogue do **not** describe how UKG Pro WFM or Workforce Central model anything. UKG documents "Overtime Rules" as their own API resource group; the real containment between pay rules, work rules and overtime rules is **unverified**.
> No real company, employee, customer or person data appears here. Defect and test texts are invented.

## Purpose and rules of use

- This is the **single human-readable spec** shared by the (future) fixture generator (slice 2b) and the hand-authored oracle (slice 2a, decision D10).
- It states **inputs only**: fixtures, catalogue declarations, review events. It deliberately states **no expected impact results**. The oracle author derives them by hand from this file plus `docs/architecture/relationship-model.md` rev 2 and `docs/architecture/impact-propagation.md` rev 2.
- The generator must implement this file and must never read the oracle.
- The worked example in `impact-propagation.md` covers a subset of this scenario. This scenario adds objects that are not in it, so the worked example's table is not the oracle.

## 1. The organisation (fictional)

Harborline Logistics is a fictional regional freight and warehousing company. Warehouse staff are hourly and earn weekly overtime. Office staff are salaried. One outbound integration sends time results to a fictional external payroll system, "FPS" (Fictional Payroll System), which is not modelled.

## 2. Snapshots and the change

| Snapshot | Profile | Environment | Authoritative export (assigned to the snapshot) |
|---|---|---|---|
| `before` | `synthetic` | `synthetic-dev` | `harborline-config-before.xlsx` |
| `after` | `synthetic` | `synthetic-dev` | `harborline-config-after.xlsx` |

Unscoped documents (not assigned to any snapshot, one version each): `harborline-design.pdf`, `harborline-tests.xlsx`.

**The single semantic difference between the two exports:** `OT-WEEKLY.threshold_hours` is `40` in `before` and `37.5` in `after`. Every other cell of the two config workbooks is identical. No edge is added or removed between the snapshots in the base scenario.

**Review state in the base scenario:** there are **no review events** at all (no claim verdicts, no relationship verdicts, no lineage declarations). Every relationship is unreviewed.

## 3. Catalogue declarations (fictional `synthetic` catalogue inputs)

| Entity type | Scope | `external` flag | Display-only attributes |
|---|---|---|---|
| `overtime_rule` | snapshot-scoped | no | `description` |
| `pay_period` | snapshot-scoped | no | `description` |
| `work_rule` | snapshot-scoped | no | `description` |
| `pay_rule` | snapshot-scoped | no | `description` |
| `employment_term` | snapshot-scoped | no | `description` |
| `integration` | snapshot-scoped | no | `description` |
| `mapping_row` | snapshot-scoped | no | `description` |
| `external_payroll_code` | unscoped | **yes** | `description` |
| `requirement` | unscoped | no | `title` |
| `test` | unscoped | no | `title` |
| `defect` | unscoped | no | `title` |
| `design_section` | unscoped | no | `heading` |

All other attributes listed in section 4 are **semantic**.

Relationship-type declarations: the catalogue contains exactly the eleven approved types (`uses`, `contains`, `assigns`, `consumes`, `maps_to`, `implements`, `verifies`, `asserts_value`, `mentions`, `defect_on`, `same_as`). `uses` is declared **`single_valued` for `pay_rule` → `work_rule`**. No other type or pair is single-valued. `reference_held_by` is the stored source for every type.

Traversal depth limit: the default, 6.

## 4. Artefacts and their layout

Every workbook has a first sheet `README` holding the FICTIONAL banner text above. Row 1 of every data sheet is the header; data rows follow in the order listed. Multi-valued reference cells use `; ` as separator. Empty means the cell is blank.

### 4.1 `harborline-config-before.xlsx` and `harborline-config-after.xlsx` (identical layout)

**OvertimeRules**

| key | description (display) | threshold_hours | period_type | pay_period | implements |
|---|---|---|---|---|---|
| OT-WEEKLY | Weekly overtime for hourly staff | 40 (before) / 37.5 (after) | weekly | PP-WEEKLY | REQ-012 |
| OT-DAILY | Daily overtime for hourly staff | 8 | daily | | |

**PayPeriods**

| key | description (display) | length_days | start_day |
|---|---|---|---|
| PP-WEEKLY | Standard weekly pay period | 7 | Monday |

**WorkRules**

| key | description (display) | overtime_rules | rounding_minutes | implements |
|---|---|---|---|---|
| WR-HOURLY | Hourly warehouse work rule | OT-WEEKLY; OT-DAILY | 15 | REQ-019 |
| WR-SALARIED | Salaried office work rule | | 0 | |

**PayRules**

| key | description (display) | work_rule | rounding_rule | pay_frequency |
|---|---|---|---|---|
| PR-STANDARD | Standard hourly pay rule | WR-HOURLY | RND-15 | weekly |
| PR-SALARIED | Salaried pay rule | WR-SALARIED | | monthly |

`RND-15` matches no entity in any artefact (there is no rounding-rule sheet).

**EmploymentTerms**

| key | description (display) | pay_rule | population_label |
|---|---|---|---|
| ET-HOURLY | Hourly warehouse terms | PR-STANDARD | warehouse-hourly |
| ET-SALARIED | Salaried office terms | PR-SALARIED | office-salaried |

**Integrations**

| key | description (display) | direction | consumes | mapping_rows |
|---|---|---|---|---|
| INT-PAYROLL-01 | Time results to FPS | outbound | WR-HOURLY | MR-07; MR-08 |

**MappingRows**

| key | description (display) | source | source_field | target_code |
|---|---|---|---|---|
| MR-07 | Overtime hours line | WR-HOURLY | overtime_hours | |
| MR-08 | Regular hours line | WR-SALARIED | regular_hours | REG1 |

The MR-07 `target_code` cell is deliberately blank; its target is stated only in the design PDF (4.2).

### 4.2 `harborline-design.pdf` (unscoped, one version)

- Page 1: title "Harborline Logistics time-to-pay design (FICTIONAL)" and the banner.
- Section 3 "Overtime" (page 2), one prose sentence: "OT-WEEKLY applies weekly overtime to hourly warehouse staff." No number appears in section 3.
- Section 4 "Payroll mapping" (page 3), a table with header `Mapping row | Payroll code | Code system` and one data row `MR-07 | OT1 | FPS`.
- No other object IDs appear anywhere in the PDF.

### 4.3 `harborline-tests.xlsx` (unscoped, one version)

**Requirements**

| key | title (display) | text |
|---|---|---|
| REQ-012 | Weekly overtime threshold | Hourly staff accrue overtime after the weekly threshold |
| REQ-019 | Hourly time rounding | Hourly punches are rounded per the work rule |

**Tests**

| key | title (display) | verifies | expected_result |
|---|---|---|---|
| TC-017 | Weekly overtime triggers | OT-WEEKLY; REQ-012 | Overtime is recorded once the weekly threshold is passed |
| TC-031 | Weekly overtime boundary | | OT-WEEKLY: hours above 40 in the week are overtime |
| TC-040 | Salaried pay rule smoke test | PR-SALARIED | Salaried pay rule produces no overtime lines |

**Defects**

| key | title (display) | raised_against | status |
|---|---|---|---|
| DEF-004 | Overtime lines missing from FPS export | INT-PAYROLL-01 | closed |

## 5. Entities (21)

Stable key = (`synthetic`, entity type, key). Semantic attributes in **bold**; display-only in plain text. "Stated in" is where the EntityVersion comes from.

| # | Key | Entity type | Stated in | Attributes |
|---|---|---|---|---|
| E01 | OT-WEEKLY | overtime_rule | config (both) OvertimeRules | **threshold_hours** (40 / 37.5), **period_type**, description |
| E02 | OT-DAILY | overtime_rule | config (both) OvertimeRules | **threshold_hours** 8, **period_type**, description |
| E03 | PP-WEEKLY | pay_period | config (both) PayPeriods | **length_days**, **start_day**, description |
| E04 | WR-HOURLY | work_rule | config (both) WorkRules | **rounding_minutes** 15, description |
| E05 | WR-SALARIED | work_rule | config (both) WorkRules | **rounding_minutes** 0, description |
| E06 | PR-STANDARD | pay_rule | config (both) PayRules | **pay_frequency**, description |
| E07 | PR-SALARIED | pay_rule | config (both) PayRules | **pay_frequency**, description |
| E08 | ET-HOURLY | employment_term | config (both) EmploymentTerms | **population_label**, description |
| E09 | ET-SALARIED | employment_term | config (both) EmploymentTerms | **population_label**, description |
| E10 | INT-PAYROLL-01 | integration | config (both) Integrations | **direction**, description |
| E11 | MR-07 | mapping_row | config (both) MappingRows | **source_field**, description |
| E12 | MR-08 | mapping_row | config (both) MappingRows | **source_field**, description |
| E13 | OT1 | external_payroll_code (external) | design PDF §4 table | **code_system** FPS |
| E14 | REG1 | external_payroll_code (external) | config (both) MappingRows target_code | none beyond key |
| E15 | REQ-012 | requirement | tests.xlsx Requirements | **text**, title |
| E16 | REQ-019 | requirement | tests.xlsx Requirements | **text**, title |
| E17 | TC-017 | test | tests.xlsx Tests | **expected_result**, title |
| E18 | TC-031 | test | tests.xlsx Tests | **expected_result**, title |
| E19 | TC-040 | test | tests.xlsx Tests | **expected_result**, title |
| E20 | DEF-004 | defect | tests.xlsx Defects | **status**, title |
| E21 | DESIGN-S3 | design_section | design PDF §3 (page 2) | heading "Overtime" |

Reference columns (`pay_period`, `overtime_rules`, `work_rule`, `rounding_rule`, `pay_rule`, `consumes`, `mapping_rows`, `source`, `target_code`, `implements`, `verifies`, `raised_against`) become relationships or UnresolvedReferences, not attributes.

## 6. Relationships (22) and the unresolved reference (1)

Stored direction is `source —type→ target`. Config-workbook claims exist once per snapshot export (one claim from `before`, one from `after`). Rule claims carry the fixture-declared method and confidence shown; these numbers are fictional extractor constants, not measurements.

| # | Stored edge | Stated by | Evidence basis |
|---|---|---|---|
| R01 | WR-HOURLY —contains→ OT-WEEKLY | config WorkRules `overtime_rules` cell of WR-HOURLY | explicit_source |
| R02 | WR-HOURLY —contains→ OT-DAILY | same cell as R01 | explicit_source |
| R03 | OT-WEEKLY —uses→ PP-WEEKLY | config OvertimeRules `pay_period` cell of OT-WEEKLY | explicit_source |
| R04 | PR-STANDARD —uses→ WR-HOURLY | config PayRules `work_rule` cell of PR-STANDARD | explicit_source |
| R05 | PR-SALARIED —uses→ WR-SALARIED | config PayRules `work_rule` cell of PR-SALARIED | explicit_source |
| R06 | ET-HOURLY —assigns→ PR-STANDARD | config EmploymentTerms `pay_rule` cell of ET-HOURLY | explicit_source |
| R07 | ET-SALARIED —assigns→ PR-SALARIED | config EmploymentTerms `pay_rule` cell of ET-SALARIED | explicit_source |
| R08 | INT-PAYROLL-01 —consumes→ WR-HOURLY | config Integrations `consumes` cell | explicit_source |
| R09 | INT-PAYROLL-01 —contains→ MR-07 | config Integrations `mapping_rows` cell | explicit_source |
| R10 | INT-PAYROLL-01 —contains→ MR-08 | same cell as R09 | explicit_source |
| R11 | MR-07 —uses→ WR-HOURLY | config MappingRows `source` cell of MR-07 | explicit_source |
| R12 | MR-08 —uses→ WR-SALARIED | config MappingRows `source` cell of MR-08 | explicit_source |
| R13 | MR-07 —maps_to→ OT1 | design PDF §4 table row (page 3, row bbox) | deterministic_rule; method `pdf_table_row@1`; confidence 0.8 |
| R14 | MR-08 —maps_to→ REG1 | config MappingRows `target_code` cell of MR-08 | explicit_source |
| R15 | OT-WEEKLY —implements→ REQ-012 | config OvertimeRules `implements` cell of OT-WEEKLY | explicit_source |
| R16 | WR-HOURLY —implements→ REQ-019 | config WorkRules `implements` cell of WR-HOURLY | explicit_source |
| R17 | TC-017 —verifies→ OT-WEEKLY | tests.xlsx Tests `verifies` cell of TC-017 | explicit_source |
| R18 | TC-017 —verifies→ REQ-012 | same cell as R17 | explicit_source |
| R19 | TC-040 —verifies→ PR-SALARIED | tests.xlsx Tests `verifies` cell of TC-040 | explicit_source |
| R20 | TC-031 —asserts_value[threshold_hours]→ OT-WEEKLY | value match: TC-031 `expected_result` cell names OT-WEEKLY and contains `40`, equal to OT-WEEKLY.threshold_hours in `before`. Locator: the TC-031 `expected_result` cell only | deterministic_rule; method `value_match@1`; confidence 0.7 |
| R21 | DESIGN-S3 —mentions→ OT-WEEKLY | design PDF §3 sentence (page 2, word bbox of "OT-WEEKLY") | deterministic_rule; method `pdf_id_mention@1`; confidence 0.9 |
| R22 | DEF-004 —defect_on→ INT-PAYROLL-01 | tests.xlsx Defects `raised_against` cell | explicit_source |

The §4 PDF table yields only R13. It is not also extracted as `mentions` (fixture decision).

| # | UnresolvedReference | Holder | Raw text | Locator | Reason |
|---|---|---|---|---|---|
| U01 | intended type `uses` | PR-STANDARD | `RND-15` | config PayRules `rounding_rule` cell of PR-STANDARD (both snapshots) | `missing_target` |

No `same_as`, no `absent` claim and no conflict exists in the base scenario. `same_as` and `absent` appear only in mutations.

## 7. Fixture decisions the oracle author should confirm or veto

These are spec choices, not results. Each is open to the owner's veto before freezing.

1. Requirements, Tests and Defects live in the unscoped `harborline-tests.xlsx`, not in the config workbooks. (The plan's sheet list put Requirements and Tests in the config workbook; moving them keeps test and requirement claims unscoped.) A `PayPeriods` sheet is added to the config workbooks for PP-WEEKLY.
2. R15 and R16 (`implements`) are unscoped relationships (requirement is unscoped) whose claims come from snapshot-assigned exports, so each has one claim scoped to `before` and one to `after`. The model's derived-state rules say "S is ignored when R is unscoped"; how scoped claims on an unscoped relationship count as live is for the owner to apply.
3. R20's claim cites only the TC-031 cell, so it is unscoped, although the value it matched (40) exists only in `before`.
4. OT1 exists only through the design PDF (unscoped). REG1 exists through both config exports.

## 8. Mutations (input changes only)

Each mutation is applied alone to the base scenario unless it says "on top of". "Config `after`" means `harborline-config-after.xlsx`; "both configs" means both exports. Review events are inserted by a human actor with the `reviewer` role; the reason text is given. Expected effects are for the oracle author to write.

| # | Input change |
|---|---|
| M01 | **Delete a `uses` reference.** Config `after`: blank the PayRules `work_rule` cell of PR-STANDARD (R04 absent in `after`). |
| M02 | **Dangling ID.** Config `after`: change the MappingRows `source` cell of MR-07 from `WR-HOURLY` to `WR-HOURLX` (no such entity). |
| M03 | **Rejected edge.** Add relationship verdict `rejected` on R08 (INT-PAYROLL-01 —consumes→ WR-HOURLY), scope `after`, reason "integration reads mapping rows only". |
| M04 | **Unreviewed rule edge.** Design PDF: add §5 "Population changes" table, header `Employment term | Pay rule`, one row `ET-SALARIED | PR-STANDARD` (rule claim ET-SALARIED —assigns→ PR-STANDARD, method `pdf_table_row@1`, confidence 0.8). |
| M05 | **Removed test link.** tests.xlsx: change TC-017 `verifies` to `OT-WEEKLY` only (R18 removed). |
| M06 | **Display-only change.** Config `after`: change the `description` of OT-DAILY to "Daily overtime (hourly staff)". |
| M07 | **Cycle.** Both configs: add a WorkRules column `uses` with value `PR-STANDARD` on WR-HOURLY (new explicit edge WR-HOURLY —uses→ PR-STANDARD in both snapshots). |
| M08 | **Profile unknown.** Ingest ET-HOURLY (both snapshots) with `product_profile = unknown` (graph-level mutation; its R06 claim is kept). |
| M09 | **Depth limit.** Both configs: add integrations INT-CHAIN-1 (`consumes` ET-HOURLY), INT-CHAIN-2 (`consumes` INT-CHAIN-1), INT-CHAIN-3 (`consumes` INT-CHAIN-2), INT-CHAIN-4 (`consumes` INT-CHAIN-3). |
| M10 | **Polarity conflict.** Design PDF: add §6 sentence "PR-STANDARD no longer uses WR-HOURLY." extracted as an `absent` rule claim on R04 (method `pdf_negation@1`, confidence 0.8). |
| M11 | **Cardinality conflict.** Design PDF: add §6 sentence "PR-STANDARD uses WR-SALARIED." extracted as a `present` rule claim PR-STANDARD —uses→ WR-SALARIED (method `pdf_sentence@1`, confidence 0.8). |
| M12 | **Conflict cleared by claim rejection.** On top of M11: a claim verdict `rejected` on the M11 claim, reason "stale design text". |
| M13 | **Attribute conflict.** Add a second authoritative document `harborline-config-after-supplement.xlsx`, assigned to snapshot `after`, with one OvertimeRules row: OT-WEEKLY, threshold_hours `38`, other cells as in config `after`. |
| M14 | **`same_as` unreviewed.** Both configs: add work rule WR-HOURLY-B (rounding_minutes 15) and pay rule PR-NIGHT (`work_rule` WR-HOURLY-B, pay_frequency weekly). Design PDF: add §7 sentence "WR-HOURLY-B is the same work rule as WR-HOURLY." extracted as a rule claim WR-HOURLY —same_as→ WR-HOURLY-B (method `pdf_sentence@1`, confidence 0.8). No verdict. |
| M15 | **`same_as` accepted.** On top of M14: relationship verdict `accepted` on the `same_as` edge, scope `after`. |
| M16 | **`same_as` rejected.** On top of M14: relationship verdict `rejected` on the `same_as` edge, scope `after`, reason "different work rules". |
| M17 | **Added entity.** Config `after`: add OvertimeRules row OT-HOLIDAY (threshold_hours 0, period_type holiday, no pay_period, no implements) and change WR-HOURLY `overtime_rules` to `OT-WEEKLY; OT-DAILY; OT-HOLIDAY`. |
| M18 | **Removed entity.** Config `after`: delete the OT-DAILY row and change WR-HOURLY `overtime_rules` to `OT-WEEKLY`. |
| M19 | **Removed link seed.** Config `after`: blank the Integrations `consumes` cell of INT-PAYROLL-01 (R08 absent in `after`), entities unchanged. |
| M20 | **No semantic change (control).** Config `after`: set OT-WEEKLY threshold_hours back to `40`, so the two exports are identical. |
| M21 | **Rule edge unsupported.** Claim verdict `rejected` on the only R13 claim, reason "mapping table superseded by FPS spec". |
| M22 | **Rule edge accepted.** Relationship verdict `accepted` on R20 (unscoped, no scope). |
| M23 | **Document supersession.** Upload `harborline-design.pdf` version 2, declared by a human as superseding version 1, identical except the §4 table row is removed. |
| M24 | **Unparsed document.** Replace `harborline-design.pdf` with a truncated copy that fails to parse. |
| M25 | **Uncatalogued type.** Both configs: add an Integrations column `feeds` with value `WR-SALARIED` on INT-PAYROLL-01 (no catalogue type for `feeds`). |
| M26 | **Removed requirement link.** Config `after`: blank the WorkRules `implements` cell of WR-HOURLY (R16 claim absent in `after`). |

## 9. Messy variants (input changes only)

Each is a separate file derived from `harborline-config-before.xlsx` (file `harborline-config-before-messy-<n>.xlsx`), one change per file, all other content unchanged. Expected boundaries or claims are for the oracle author to write.

| # | Variant | Input change |
|---|---|---|
| X1 | Renamed sheet | Sheet `OvertimeRules` renamed to `Overtime Rules` |
| X2 | Merged header | In `WorkRules`, header cells for `overtime_rules` and `rounding_minutes` merged into one cell reading `overtime_rules` |
| X3 | Hidden row | In `PayRules`, the PR-SALARIED row is hidden (data unchanged) |
| X4 | Dangling ID | In `EmploymentTerms`, ET-SALARIED `pay_rule` changed to `PR-SALARY` |
| X5 | Alias spelling | In `Integrations`, `consumes` changed to `WR_HOURLY` (underscore) |
| X6 | Formula without cached value | In `OvertimeRules`, OT-DAILY `threshold_hours` is the formula `=4*2`, saved with no cached value |
| X7 | Trailing whitespace | In `WorkRules`, `overtime_rules` of WR-HOURLY is `OT-WEEKLY ; OT-DAILY ` (trailing spaces) |
| X8 | Unknown sheet | An extra sheet `Scratch` with header `key | notes` and one row `OT-WEEKLY | check with payroll` |
