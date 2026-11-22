# Decision 0003: domain model clarifications (Slice 1)

Status: **approved by the owner, 2026-11-22.** Answers the questions raised while planning and building the Slice 1 domain model (`backend/app/domain/`). Applies `docs/architecture/relationship-model.md` rev 2.1 (D3) and decisions 0001 and 0002. Q7, Q10, Q11 and Q13 can change expected oracle results, which is why the owner decided them.

## Decisions

| # | Question | Decision |
|---|---|---|
| Q7 | Entities with profile `unknown` | A relationship may join a known-profile entity and an `unknown` one. It is typed against the known side's catalogue, and the `unknown` entity is treated as snapshot-scoped. A relationship with **two** `unknown` ends is rejected by the model (an invariant). **Ingestion must never trigger that rejection:** where it would produce such a relationship, it records a not-modelled entry instead, `UnresolvedReference(reason="unknown_profile")`. |
| Q10 | Attribute conflicts | Versions superseded by lineage are excluded. An attribute present in one authoritative version only is not a conflict. A disagreement on a display-only attribute is not a conflict. **Numbers are `Decimal` parsed from the source cell text, never float**: `"37.5"` equals a cell value of `37.5`, `"0.30"` equals `"0.3"`, and `0.1 + 0.2` compares exactly as `0.3`. A boolean never equals a number. |
| Q11 | Documentary-only conflict | Raised when the relationship is scoped, its state is accepted or unreviewed, every live present claim in S is unscoped and at least one is `explicit_source`, and its stored source has an EntityVersion in S from a version that is not superseded. Accepted edges get the flag but keep their tier (decision 0002, item 1). |
| Q12 | Accepted edge with only absent claims | Polarity conflict: the human verdict is the "present" side. |
| Q13a | Cardinality across `same_as` (**owner overrode the recommendation**) | Cardinality counts **distinct targets after collapsing accepted `same_as` clusters**. Unreviewed, rejected and superseded `same_as` never collapse. So `S uses A`, `S uses B` with accepted `A same_as B` is no cardinality conflict; with unreviewed `A same_as B` it is. |
| Q13b | Identity conflict | Only a **rejected** `same_as` inside an accepted cluster is an identity conflict. A superseded one is a correction, not a denial. |
| Q14 | `SUCCESSOR_EXCLUDED` | Raised only when the successor is rejected or superseded, in the same snapshot context. An `unsupported` successor raises no flag. |

Decided by the team under the reversible-decision rule (recorded in PR #22): two locator kinds only (`xlsx_cell`, `pdf_word_bbox`); no `file` on a locator (it binds to a content-hashed DocumentVersion); no confidence on `explicit_source` claims; mixed-scope locators rejected; lineage declared by a human; supersession and lineage cycle checks deferred to the Slice 5 trigger; attributes stored as name, value and locator; key normalisation is `str.strip()` in Python only.

## Consequences

- The oracle author applies Q7, Q10, Q11 and Q13 when deriving expected results. Q13a means a cluster of accepted aliases counts as one target.
- Attribute values in fixtures and ingestion are read as text and converted with `number_from_cell_text`. A reader that returns a float uses `number_from_cell_value` (`Decimal(repr(v))`). Floats are rejected by the model.

## Tests

- Slice 1 (this change): two-`unknown` relationship rejected; `unknown_profile` entry valid in place of a relationship; Decimal equality cases above, float rejected, `NaN` rejected; cardinality with accepted, unreviewed and rejected `same_as`.
- **Slice 3/4 (required acceptance test):** ingesting a synthetic file whose counterpart entity has profile `unknown` succeeds and yields exactly one `unknown_profile` not-modelled entry and no relationship. The Slice 2 generator produces that fixture.
