# Decision 0007: oracle input and gate answers (Status report #31)

Status: **approved by the owner, 2026-11-22 (4).** Records the owner's answers to Status report #31 (Report 1: oracle input questions R1-3 to R1-10; Report 2: gate questions). Applies decisions 0003 and 0006.

## Decisions

| # | Question | Decision |
|---|---|---|
| R1-3 | Scenario M08 ("its R06 claim is kept") versus 0003 Q7 | No conflict. R06 `ET-HOURLY —assigns→ PR-STANDARD` is a known-to-unknown edge, allowed by Q7. It is kept, typed against the synthetic catalogue, and `ET-HOURLY` gets the unknown-profile not-modelled boundary. Only a two-`unknown` edge becomes `UnresolvedReference(reason="unknown_profile")`. |
| R1-4 | PDF section numbering | Section headings carry their number ("3 Overtime"). "No number appears in section 3" means no numeric value in the section's prose. |
| R1-5 | Numeric cells | 40, 37.5, 8, 15 and 0 are read as `Decimal` (0003 Q10). TC-031's "40" stays text inside its sentence. |
| R1-6 | Unstated mutation content | §6 heading "6 Pay rule notes" and §7 "7 Work rule equivalence", each on its own new page 4 in the mutated PDF. Other unstated cells are blank (M09 description and direction, M14 and M17 descriptions). New columns are appended last. The M13 supplement holds only README and OvertimeRules. |
| R1-7 | X2 merged header | Merge C1:D1 with value "overtime_rules". D1 has no header; D2 and D3 keep their values. |
| R1-8 | Slice 3 xlsx intake | Date cells become ISO-8601 text (`value_type` "date"). Merged ranges emit only the anchor cell. Hidden rows and cells are kept with a hidden flag. Chartsheets are refused. |
| R1-9 | Slice 3 file types | xlsx and pdf only. csv, docx, xml and json are refused (`unsupported_type`) until their locator kinds exist. The milestone's "deeply nested JSON" hostile test becomes "refused before parsing" until a JSON parser exists. |
| R1-10 | D3 storage | Milestone 1 reviewer login is one static bearer token (`SecretStr`, constant-time compare, never logged, off by default) mapped to one human reviewer. Claim evidence is stored as an array of locator ids on the claim row. Every table is append-only, actors and catalogue included. |
| R2 | Gate answers | pypdfium2 approved as an exact-name licence exception: notices for FreeType (FTL) and IJG in `NOTICE`; no musl wheels. MIT-CMU was OSI-approved on 2024-09-20 (OSI license-review list archive). Slice 4 may start on the xlsx path, with PDF rule extraction added after Slice 3 PR B. Decision 0006 is accepted for Milestone 1; session-bound reviewers are a G-REAL requirement. |

## Consequences

- The oracle author applies R1-3 to R1-7 when deriving expected results and building the mutated fixtures.
- Slice 3 implements R1-8 and R1-9; Slice 5 storage follows R1-10.
- `NOTICE` gains the FreeType and IJG notices when pypdfium2 is added; the dependency is pinned to non-musl wheels.
- Decision 0006 status is updated to accepted for Milestone 1.

## Tests

- Slice 3: date cell yields ISO-8601 text with `value_type` "date"; merged range yields only its anchor cell; hidden row kept and flagged; chartsheet refused; csv, docx, xml and json refused as `unsupported_type` before parsing.
- Slice 3/4: M08 keeps the R06 relationship and records the unknown-profile boundary for `ET-HOURLY`, with no `unknown_profile` entry for it.
- Slice 5: append-only enforced on every table, actors and catalogue included; bearer token disabled by default, compared in constant time, never logged.
