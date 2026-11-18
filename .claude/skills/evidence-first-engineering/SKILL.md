---
name: evidence-first-engineering
description: Provenance and relationship-status rules for this repo's data pipeline. Use whenever you design, write or review code for document ingestion, parsing (PDF, Word, Excel, CSV), the canonical intermediate representation, entity or relationship extraction, LLM-assisted extraction, the graph store, review/approval flows, or any model, table or API that holds extracted entities or relationships, even for a "quick" parser or fixture.
---

# Evidence-first engineering

The workbench is only useful if an engineer can click any fact and see where it came from. Every shortcut that drops provenance turns the graph into an opinion. These rules keep the chain from source byte to graph edge intact.

## Provenance on every extracted thing

Every entity and relationship carries at least one evidence reference. Model it as a required, typed field (Pydantic), not an optional dict, so missing provenance fails validation instead of shipping.

An evidence reference holds:

- `document_id` and the source file's `sha256` (so a re-uploaded, changed file is a different source)
- original file name and detected `product_profile`
- the most precise location the format allows: `page` (+ bbox if known) for PDF; `sheet`, `row`, `column`/`cell` for spreadsheets; `section`/`paragraph` for documents; line for text/CSV
- the verbatim snippet or cell value the claim rests on
- `extractor` name and version, and extraction timestamp

If a location is unknown, store `null` explicitly; never guess a page or row. Transformations (IR building, normalisation, merging duplicates) carry evidence forward; a merged entity keeps the union of its sources.

## Relationship status

> **Pending decision D3:** `docs/architecture/relationship-model.md` proposes replacing the single status below with a separate evidence basis per claim (explicit source, deterministic rule, LLM suggestion), a review state (unreviewed, accepted, rejected, superseded) and immutable locators. Once D3 is approved, that document governs, and the labels below become derived display labels. The LLM-boundary rules in this skill apply either way.

Each relationship has exactly one status:

| Status | Meaning | Required |
|---|---|---|
| `observed` | Directly stated by a source (a cell names the referenced object, a document says X uses Y) | evidence reference(s) |
| `inferred` | Derived by a rule or an LLM, not stated verbatim | evidence references, `method` (rule id or model + prompt version), `confidence` 0–1, short rationale |
| `confirmed` | A named human reviewed and accepted it | reviewer, timestamp, note, plus the original evidence |

Why `observed` and `confirmed` differ: observed means the document says it; confirmed means a person vouches it is true in this configuration. Documents can be stale.

## The LLM boundary

LLMs help with extraction, explanation and suggestions. They are never the authority.

- Anything an LLM produces enters as `inferred` (or as a candidate awaiting review), never `observed` or `confirmed`, whatever confidence it reports.
- The only path to `confirmed` is an explicit, recorded human action. No code path, batch job, threshold or "auto-accept above 0.9" may promote status.
- LLM output must point at evidence that exists in our store; reject outputs that cite locations we cannot resolve.
- Store the model id and prompt version with inferred relationships so results are reproducible and auditable.

## Tests that guard the rules

When you add or change these models/flows, include tests that fail if:

- an entity or relationship validates without evidence
- an `inferred` relationship validates without confidence or method
- any non-human code path produces `confirmed`
- a transformation drops evidence from its inputs

Use synthetic documents only.
