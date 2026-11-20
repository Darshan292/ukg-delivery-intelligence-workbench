---
name: evidence-first-engineering
description: Provenance, claim and review rules for this repo's data pipeline. Use whenever you design, write or review code for document ingestion, parsing (PDF, Word, Excel, CSV, XML, JSON), the canonical intermediate representation, entity identity, snapshots, entity or relationship extraction, LLM-assisted extraction, the graph store, review/approval flows, or any model, table or API that holds extracted entities, claims, evidence or relationships, even for a "quick" parser or fixture.
---

# Evidence-first engineering

The workbench is only useful if an engineer can click any fact and see where it came from, and trust that no machine decided it was true. These rules keep the chain intact from source byte to graph edge.

**Authoritative model:** `docs/architecture/relationship-model.md` (rev 2). It is binding (decision D3 approved 2026-11-20). This skill states the rules; the document has the schema, the options considered and the derivation details. If the two ever disagree, fix the disagreement. Do not pick one silently.

## Core concepts

- **Entity:** a stable identity (`product_profile`, `entity_type`, `natural_key`). Never physically merged or rewritten.
- **EntityVersion:** an entity's attributes as one document version states them. Snapshot diffs compare these.
- **Relationship:** a typed edge between two entities (plus `qualifier` where the type needs it). It carries no scope and no status column.
- **Claim:** one way we came to know an edge. It has a basis, method, polarity (`present`/`absent`), scope and ≥1 immutable evidence locator.
- **ReviewEvent:** an append-only human verdict on a claim or on a relationship.
- **Snapshot:** one configuration capture (profile, environment, label, time). Before/after and dev/prod are both pairs of snapshots.

Everything else (effective state, display labels, conflicts, edge tier) is **derived** by deterministic code and never stored.

## Evidence locators

Every claim and every EntityVersion points to ≥1 locator. A locator is **immutable** and points at a **content-hashed document version** (sha256), never at a file name. Re-uploading a changed file creates a new version, and old locators keep resolving.

| Source | Locator kind | Locator fields |
|---|---|---|
| Spreadsheet | `xlsx_cell` | sheet, row, column/cell (formula text and cached value read separately) |
| PDF | `pdf_bbox` | page, x0, top, x1, bottom (pdfplumber word boxes) |
| Word document | `docx_paragraph` | section/paragraph index |
| CSV | `csv_row` | row (and column) |
| XML | `xml_xpath` | an absolute XPath to the element or attribute, parsed with defusedxml |
| JSON | `json_pointer` | an RFC 6901 JSON Pointer |

Each locator also stores the verbatim snippet or value, and the extractor name, version and extraction time. If a location is unknown, store `null` explicitly; never guess a page, row or path. **A locator must resolve:** reopening the source at the locator returns the stored snippet. Transformations carry evidence forward. Nothing merges entities; identity goes through `same_as`.

## Evidence basis (on each claim)

| Basis | Produced by | Must carry |
|---|---|---|
| `explicit_source` | A deterministic parser reading an explicit reference | extractor@version |
| `deterministic_rule` | A versioned rule (ID mention, value match) | rule id@version, confidence |
| `llm_suggestion` | An LLM (Milestone 2 or later; **none in Milestone 1**) | model id, prompt version, confidence, a span verified to exist in the source |

Many claims may support one relationship; a claim is deduplicated on (relationship, basis, method, polarity, locator set). **Basis strength** is the strongest live, present claim: explicit > rule > LLM. Confidences are never summed or combined.

## Review: two targets, humans only

- **Claim verdicts** (`rejected`, `reinstated`) judge whether a source is still valid evidence. Rejecting one stale source leaves the other claims live.
- **Relationship verdicts** (`accepted`, `rejected`, `superseded` with a required successor) judge whether the link is true **in a snapshot**. Acceptance never carries over to another snapshot automatically.
- A claim is **superseded** only through document lineage, when a human declares that a new upload replaces the old version. Ingestion never changes a verdict. An accepted edge that loses all evidence keeps its verdict and is flagged `SUPPORT LOST`.
- Effective state per (relationship, snapshot) is `accepted`, `rejected`, `superseded`, `unreviewed`, or `unsupported` (no live evidence and no verdict). `unsupported` is not `rejected`.
- OBSERVED, INFERRED and CONFIRMED are **derived display labels only**: unreviewed explicit, unreviewed rule or LLM, and accepted. Never store them as a status.

## The machine boundary

LLMs and rules propose; only a named human decides.

- No code path, batch job, threshold or "auto-accept above 0.9" creates any ReviewEvent or lineage declaration. This is enforced in three layers: the database (only human actors with the reviewer role may insert review events; the ingestion role has no insert privilege; append-only tables), the API (human session only; the actor comes from the session, never from the request body), and tests.
- LLM output must cite locators that exist in our store; reject outputs that cite locations we cannot resolve.
- Conflicts (polarity, cardinality, documentary-only, identity, attribute value) are derived flags. They are surfaced, never resolved silently, and they cap affected paths at *possible*.
- `same_as` is how identity works, without merging. An unreviewed `same_as` caps paths at *possible*, even when its basis is explicit; a rejected one is never crossed.

## Tests that guard the rules

When you add or change these models or flows, include tests that fail if:

- a claim or entity version validates without a resolvable locator;
- a rule or LLM claim validates without method and confidence;
- a non-human actor can insert any review event or lineage declaration (test at the database, not only the API);
- re-ingestion changes a verdict or deletes or rewrites an entity, claim or locator;
- rejecting one claim invalidates other live claims on the same relationship;
- acceptance in one snapshot changes state in another;
- a conflict disappears without an evidence or verdict change.

Use synthetic documents only (`product_profile = synthetic`; see `ukg-domain-guardrails`).
