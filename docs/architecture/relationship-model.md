# Proposed canonical relationship model

Status: **proposal, awaiting approval (decision D3 in `docs/decisions-for-approval.md`). Not implemented.**

## Problem with a single status field

The current rule gives each relationship one status: OBSERVED, INFERRED or CONFIRMED. That single field mixes two independent questions:

1. **How do we know?** A document states it, a deterministic rule derived it, or an LLM suggested it.
2. **Has a human checked it, and what did they decide?**

Mixing them loses information that matters in this domain:

- A relationship stated in a stale design workbook is "explicit" but may be **wrong**. A reviewer must be able to reject it without erasing the fact that a document said it.
- An LLM suggestion that a human accepts should stay traceable to its LLM origin. "CONFIRMED" alone hides that.
- One relationship is often supported by several sources: a workbook cell **and** a design-document sentence **and** a rule match. A single status plus a single evidence reference cannot hold that.
- When a document is re-uploaded in a new version, earlier claims need to be **superseded**, not overwritten or deleted.

## Proposed model: three separate concerns

```
Relationship (edge identity)          Claim (one per way we came to know it)        EvidenceLocator (immutable)
──────────────────────────────        ───────────────────────────────────────        ───────────────────────────
id                                    id                                             id
type            ── catalogue ──┐      relationship_id ──► Relationship               document_version_id ──► DocumentVersion (sha256)
source_entity_id               │      basis: explicit_source | deterministic_rule    kind: xlsx_cell | pdf_bbox | docx_paragraph |
target_entity_id               │             | llm_suggestion                              csv_row | xml_xpath | json_pointer
product_profile                │      method: extractor@version | rule_id@version    locator: {sheet,row,col} | {page,x0,top,x1,bottom} | …
created_at                     │             | model_id + prompt_version             snippet (verbatim text/value)
                               │      confidence: 0–1 (required unless explicit)     extractor@version, extracted_at
review_state (derived,         │      evidence: 1..n EvidenceLocator ids             (append-only; never updated)
  see ReviewEvent)             │      created_at
                               │      superseded_by_claim_id (nullable)
                               │
ReviewEvent (append-only)      │      RelationshipType catalogue (see impact-propagation.md)
──────────────────────────     │      ─────────────────────────────────────────────────────
id, relationship_id            └────► name, allowed source/target entity types,
from_state, to_state                  propagation rule, version
actor_id ──► Actor (kind = human only for accept/reject)
reason (required for reject/supersede)
at
```

### 1. Evidence basis, on each Claim
| Basis | Produced by | Must carry |
|---|---|---|
| `explicit_source` | A deterministic parser reading an explicit reference (for example a cell that names another object's ID) | ≥1 locator; extractor and version |
| `deterministic_rule` | A versioned rule (for example an exact ID mentioned in PDF text, or a value match in a test's expected result) | ≥1 locator; rule id and version; confidence |
| `llm_suggestion` | An LLM proposal (Milestone 2 or later) | ≥1 locator whose snippet is **verified to exist** in the source; model id; prompt version; confidence |

A relationship's **basis strength** is derived as the strongest basis among its live (non-superseded) claims: explicit > rule > LLM. Confidence on a rule or LLM claim never changes review state.

### 2. Review state, on the Relationship (derived from ReviewEvents)
| State | Meaning |
|---|---|
| `unreviewed` | Default for every new relationship, whatever its basis |
| `accepted` | A named human reviewed the evidence and accepted the relationship as true **for this configuration** |
| `rejected` | A named human judged it false or stale. It is kept for audit and excluded from traversal |
| `superseded` | Replaced by a newer relationship, because a document version changed or an edge was corrected. Links to its successor; excluded from traversal |

Allowed transitions: unreviewed → accepted | rejected | superseded; accepted → rejected | superseded; rejected → accepted (a human changing their mind, with a reason). Every transition is a new ReviewEvent row. Rows are never updated.

### 3. Source evidence: immutable locators
- A locator points at a **document version** (content hash), not a file name. Re-uploading a changed file creates a new version, and old locators stay valid.
- Locators are append-only. Corrections create new claims and supersede old ones.
- Every locator must resolve: reopening the source at that locator returns the stored snippet. This is a Milestone 1 acceptance criterion.

## "Only a human can accept": enforced in three layers
1. **Database:**
   - `ReviewEvent.actor_id` references an `Actor` table with `kind ∈ {human, service}`.
   - A constraint trigger rejects any event with `to_state IN ('accepted','rejected')` unless the actor is `kind = 'human'` with the reviewer role.
   - The ingestion and extraction database role has **no INSERT privilege** on `review_events` at all.
2. **API:** the review endpoint requires an authenticated human session (no service tokens) and writes the actor from the session, never from the request body.
3. **Tests:**
   - A direct SQL insert of an `accepted` event by a service actor fails.
   - An LLM or rule claim with confidence 1.0 still yields `unreviewed`.
   - Re-ingesting a document never changes an `accepted` relationship's state silently: it adds claims, and a human decides whether to supersede.

## Mapping to the old labels (for the UI and reports)

The old words survive as **derived display labels**, not stored fields:

| Display label | Derived when |
|---|---|
| CONFIRMED | review_state = accepted |
| OBSERVED | review_state = unreviewed and basis strength = explicit_source |
| INFERRED | review_state = unreviewed and basis strength ∈ {deterministic_rule, llm_suggestion} |
| (hidden, auditable) | rejected or superseded |

## How impact tiers use it
- **Established edge:** review_state = accepted, **or** (unreviewed **and** basis strength = explicit_source).
- **Possible edge:** unreviewed with basis strength = rule or LLM. Report the weakest such edge's method and confidence.
- **Excluded:** rejected or superseded.

"Established" means documented or human-accepted. It does **not** mean verified against UKG runtime behaviour.

## Open questions for approval
- Should engineers be able to **assert** a relationship with no document (basis `engineer_assertion`, with a required written justification as its evidence)? Recommended: yes, but treated as possible until a **second** human accepts it.
- Is a single reviewer enough to accept, or do payroll-affecting edge types need two-person review? Recommended for Milestone 1: one reviewer, recorded. Revisit with practitioners.
- Entity resolution (two names for the same object): treat as a relationship type `same_as` under the same claim and review model, instead of merging silently.
